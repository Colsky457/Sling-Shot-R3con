"""Base pipeline classes for Sling."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

from ..state import StepStatus
from ..logging import get_logger

logger = get_logger(__name__)


class StepResult:
    """Result of a pipeline step execution."""
    def __init__(
        self,
        success: bool,
        output_paths: List[Path] = None,
        artifacts: Dict[str, int] = None,
        error: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.success = success
        self.output_paths = output_paths or []
        self.artifacts = artifacts or {}
        self.error = error
        self.metadata = metadata or {}


class ScanContext:
    """Context passed to each pipeline step."""
    def __init__(
        self,
        scan_id: str,
        domain: str,
        scan_dir: Path,
        config: Any,
        state: Any
    ):
        self.scan_id = scan_id
        self.domain = domain
        self.scan_dir = scan_dir
        self.config = config
        self.state = state
        self.data: Dict[str, Any] = {}  # For passing data between steps


class PipelineStep(ABC):
    """Base class for all pipeline steps."""

    name: str = ""
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds, exponential backoff

    @abstractmethod
    async def execute(self, context: ScanContext) -> StepResult:
        """Execute the pipeline step."""
        pass

    @abstractmethod
    def get_output_paths(self, context: ScanContext) -> List[Path]:
        """Get expected output paths for this step."""
        pass

    def can_resume(self, context: ScanContext) -> bool:
        """Check if step can be resumed from previous run."""
        return context.state.can_resume_step(context.scan_id, self.name)


class PipelineOrchestrator:
    """Orchestrates pipeline execution with DAG-based dependency resolution."""

    def __init__(self, steps: List[PipelineStep], config: Any, state: Any):
        self.steps = {step.name: step for step in steps}
        self.config = config
        self.state = state
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """Validate that all dependencies exist."""
        step_names = set(self.steps.keys())
        for step in self.steps.values():
            for dep in step.dependencies:
                if dep not in step_names:
                    raise ValueError(f"Step '{step.name}' depends on unknown step '{dep}'")

    def _get_execution_order(self) -> List[List[str]]:
        """Get steps grouped by execution level (parallelizable groups)."""
        in_degree = {name: 0 for name in self.steps}
        dependents = {name: [] for name in self.steps}
        for step in self.steps.values():
            for dep in step.dependencies:
                in_degree[step.name] += 1
                dependents[dep].append(step.name)

        levels = []
        remaining = set(self.steps.keys())

        while remaining:
            current_level = [name for name in remaining if in_degree[name] == 0]
            if not current_level:
                raise ValueError("Circular dependency detected in pipeline")

            levels.append(current_level)
            for name in current_level:
                remaining.remove(name)
                for dependent in dependents[name]:
                    in_degree[dependent] -= 1

        return levels

    async def execute(self, context: ScanContext, resume: bool = False) -> Dict[str, StepResult]:
        """Execute all pipeline steps in dependency order."""
        results = {}
        execution_order = self._get_execution_order()

        for level in execution_order:
            # Execute steps in this level in parallel
            import asyncio
            tasks = []
            for step_name in level:
                step = self.steps[step_name]
                if resume and step.can_resume(context):
                    logger.info("step_skipped_resume", step=step_name, scan_id=context.scan_id)
                    results[step_name] = StepResult(success=True, output_paths=step.get_output_paths(context))
                    continue

                self.state.update_step_status(context.scan_id, step_name, StepStatus.RUNNING)
                task = asyncio.create_task(self._execute_step_with_retry(step, context))
                tasks.append((step_name, task))

            # Wait for all steps in this level
            for step_name, task in tasks:
                try:
                    result = await task
                    results[step_name] = result
                    if result.success:
                        self.state.update_step_status(
                            context.scan_id, step_name, StepStatus.COMPLETED,
                            output_path=str(result.output_paths[0]) if result.output_paths else None
                        )
                        # Record artifacts
                        for art_type, count in result.artifacts.items():
                            output_path = result.output_paths[0] if result.output_paths else ""
                            self.state.add_artifact(
                                context.scan_id, step_name, art_type,
                                str(output_path), count
                            )
                    else:
                        self.state.update_step_status(
                            context.scan_id, step_name, StepStatus.FAILED,
                            error=result.error
                        )
                        logger.error("step_failed", step=step_name, error=result.error)
                        raise RuntimeError(f"Step '{step_name}' failed: {result.error}")
                except Exception as e:
                    logger.error("step_exception", step=step_name, error=str(e))
                    self.state.update_step_status(
                        context.scan_id, step_name, StepStatus.FAILED,
                        error=str(e)
                    )
                    raise

        return results

    async def _execute_step_with_retry(self, step: PipelineStep, context: ScanContext) -> StepResult:
        """Execute a step with retry logic."""
        last_error = None
        for attempt in range(step.max_retries + 1):
            try:
                if attempt > 0:
                    delay = step.retry_delay * (2 ** (attempt - 1))
                    logger.info("step_retry", step=step.name, attempt=attempt, delay=delay)
                    import asyncio
                    await asyncio.sleep(delay)
                    self.state.increment_step_retry(context.scan_id, step.name)

                result = await step.execute(context)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.warning("step_attempt_failed", step=step.name, attempt=attempt, error=last_error)

        return StepResult(success=False, error=f"Max retries exceeded: {last_error}")