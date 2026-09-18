"""Tests for PipelineOrchestrator DAG ordering and retry logic."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sling.pipeline import (
    PipelineOrchestrator,
    PipelineStep,
    ScanContext,
    StepResult,
)
from sling.state import StateManager, StepStatus


class MockStep(PipelineStep):
    """Mock pipeline step for testing orchestrator behavior."""

    name = "mock"
    dependencies = []
    max_retries = 3
    retry_delay = 0.01

    def __init__(self, name="mock", dependencies=None, max_retries=3, retry_delay=0.01, execute_fn=None):
        self._name = name
        self._dependencies = dependencies or []
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._execute_fn = execute_fn
        super().__init__()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def dependencies(self):
        return self._dependencies

    @dependencies.setter
    def dependencies(self, value):
        self._dependencies = value

    @property
    def max_retries(self):
        return self._max_retries

    @max_retries.setter
    def max_retries(self, value):
        self._max_retries = value

    @property
    def retry_delay(self):
        return self._retry_delay

    @retry_delay.setter
    def retry_delay(self, value):
        self._retry_delay = value

    async def execute(self, context: ScanContext) -> StepResult:
        if self._execute_fn:
            return await self._execute_fn(context)
        return StepResult(success=True)

    def get_output_paths(self, context: ScanContext) -> list:
        return []


class TestPipelineOrchestratorDAG:
    """Tests for DAG-based dependency resolution."""

    def test_single_step_no_dependencies(self):
        """Single step with no dependencies should execute in its own level."""
        step = MockStep(name="dns")
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        order = orchestrator._get_execution_order()
        assert len(order) == 1
        assert order[0] == ["dns"]

    def test_two_independent_steps_same_level(self):
        """Two independent steps should be in the same execution level."""
        step_a = MockStep(name="dns", dependencies=[])
        step_b = MockStep(name="port", dependencies=[])
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step_a, step_b], config, state)
        order = orchestrator._get_execution_order()
        assert len(order) == 1
        assert set(order[0]) == {"dns", "port"}

    def test_dependent_steps_different_levels(self):
        """Step B depends on A, so A must execute before B."""
        step_a = MockStep(name="dns", dependencies=[])
        step_b = MockStep(name="port", dependencies=["dns"])
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step_a, step_b], config, state)
        order = orchestrator._get_execution_order()
        assert len(order) == 2
        assert order[0] == ["dns"]
        assert order[1] == ["port"]

    def test_chain_dependencies(self):
        """A -> B -> C chain should produce 3 levels."""
        step_a = MockStep(name="dns", dependencies=[])
        step_b = MockStep(name="port", dependencies=["dns"])
        step_c = MockStep(name="crawl", dependencies=["port"])
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step_a, step_b, step_c], config, state)
        order = orchestrator._get_execution_order()
        assert len(order) == 3
        assert order[0] == ["dns"]
        assert order[1] == ["port"]
        assert order[2] == ["crawl"]

    def test_diamond_dependency(self):
        """Diamond: B and C depend on A; D depends on B and C."""
        step_a = MockStep(name="dns", dependencies=[])
        step_b = MockStep(name="port", dependencies=["dns"])
        step_c = MockStep(name="crawl", dependencies=["dns"])
        step_d = MockStep(name="final", dependencies=["port", "crawl"])
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step_a, step_b, step_c, step_d], config, state)
        order = orchestrator._get_execution_order()
        assert len(order) == 3
        assert order[0] == ["dns"]
        assert set(order[1]) == {"port", "crawl"}
        assert order[2] == ["final"]

    def test_circular_dependency_raises(self):
        """Circular dependency should raise ValueError."""
        step_a = MockStep(name="a", dependencies=["b"])
        step_b = MockStep(name="b", dependencies=["a"])
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator = PipelineOrchestrator([step_a, step_b], config, state)
            orchestrator._get_execution_order()

    def test_unknown_dependency_raises(self):
        """Dependency on unknown step should raise ValueError."""
        step = MockStep(name="port", dependencies=["nonexistent"])
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        with pytest.raises(ValueError, match="unknown step"):
            orchestrator = PipelineOrchestrator([step], config, state)

    def test_multiple_steps_in_first_level(self):
        """Multiple steps with no dependencies share level 0."""
        steps = [
            MockStep(name="a", dependencies=[]),
            MockStep(name="b", dependencies=[]),
            MockStep(name="c", dependencies=["a", "b"]),
        ]
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator(steps, config, state)
        order = orchestrator._get_execution_order()
        assert len(order) == 2
        assert set(order[0]) == {"a", "b"}
        assert order[1] == ["c"]


class TestPipelineOrchestratorRetry:
    """Tests for retry logic in pipeline execution."""

    @pytest.mark.asyncio
    async def test_step_succeeds_on_first_attempt(self):
        """Step that succeeds immediately should not retry."""
        execute_fn = AsyncMock(return_value=StepResult(success=True, output_paths=[Path("/tmp/out.txt")]))
        step = MockStep(name="dns", max_retries=3, retry_delay=0.01, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        results = await orchestrator.execute(context)
        assert execute_fn.call_count == 1
        assert "dns" in results
        assert results["dns"].success is True

    @pytest.mark.asyncio
    async def test_step_succeeds_after_retry(self):
        """Step that fails then succeeds should retry and eventually succeed."""
        # Fail twice, then succeed
        execute_fn = AsyncMock(side_effect=[
            StepResult(success=False, error="attempt 1"),
            StepResult(success=False, error="attempt 2"),
            StepResult(success=True, output_paths=[Path("/tmp/out.txt")]),
        ])
        step = MockStep(name="dns", max_retries=3, retry_delay=0.01, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        results = await orchestrator.execute(context)
        assert execute_fn.call_count == 3
        assert results["dns"].success is True

    @pytest.mark.asyncio
    async def test_step_fails_after_max_retries(self):
        """Step that always fails should return failure after max retries."""
        execute_fn = AsyncMock(return_value=StepResult(success=False, error="always fails"))
        step = MockStep(name="dns", max_retries=2, retry_delay=0.01, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        with pytest.raises(RuntimeError, match="Max retries exceeded"):
            await orchestrator.execute(context)
        assert execute_fn.call_count == 3  # max_retries + 1 = 3 attempts
        state.update_step_status.assert_called()

    @pytest.mark.asyncio
    async def test_retry_increments_state(self):
        """Retry attempts should increment retry count in state."""
        execute_fn = AsyncMock(side_effect=[
            StepResult(success=False, error="fail"),
            StepResult(success=True),
        ])
        step = MockStep(name="dns", max_retries=3, retry_delay=0.01, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        await orchestrator.execute(context)
        assert state.increment_step_retry.call_count == 1

    @pytest.mark.asyncio
    async def test_step_exception_is_propagated(self):
        """Exceptions from step execution should propagate after retries exhausted."""
        async def raising_execute(context):
            raise RuntimeError("critical failure")

        step = MockStep(name="dns", max_retries=2, retry_delay=0.01, execute_fn=raising_execute)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        with pytest.raises(RuntimeError, match="critical failure"):
            await orchestrator.execute(context)

    @pytest.mark.asyncio
    async def test_retry_delay_exponential_backoff(self):
        """Retry delays should follow exponential backoff."""
        execute_fn = AsyncMock(side_effect=[
            StepResult(success=False, error="fail 1"),
            StepResult(success=False, error="fail 2"),
            StepResult(success=True),
        ])
        step = MockStep(name="dns", max_retries=3, retry_delay=0.01, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await orchestrator.execute(context)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(0.01)
            mock_sleep.assert_any_call(0.02)


class TestPipelineOrchestratorStepFailurePropagation:
    """Tests for step failure propagation in pipeline execution."""

    @pytest.mark.asyncio
    async def test_failed_step_updates_state_to_failed(self):
        """Failed step should update state to FAILED."""
        execute_fn = AsyncMock(return_value=StepResult(success=False, error="step failed"))
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        with pytest.raises(RuntimeError):
            await orchestrator.execute(context)
        state.update_step_status.assert_called()
        failed_calls = [
            call for call in state.update_step_status.call_args_list
            if len(call.args) >= 3 and call.args[2] == StepStatus.FAILED
        ]
        assert len(failed_calls) > 0

    @pytest.mark.asyncio
    async def test_successful_step_updates_state_to_completed(self):
        """Successful step should update state to COMPLETED."""
        execute_fn = AsyncMock(return_value=StepResult(success=True, output_paths=[Path("/tmp/out.txt")]))
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        results = await orchestrator.execute(context)
        assert results["dns"].success is True
        state.update_step_status.assert_called()

    @pytest.mark.asyncio
    async def test_failed_step_records_artifacts_empty_on_failure(self):
        """Failed steps should not record artifacts."""
        execute_fn = AsyncMock(return_value=StepResult(success=False, error="fail"))
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        with pytest.raises(RuntimeError):
            await orchestrator.execute(context)
        state.add_artifact.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_step_records_artifacts(self):
        """Successful steps should record artifacts."""
        execute_fn = AsyncMock(
            return_value=StepResult(
                success=True,
                output_paths=[Path("/tmp/out.txt")],
                artifacts={"subdomains": 50},
            )
        )
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        results = await orchestrator.execute(context)
        assert results["dns"].artifacts == {"subdomains": 50}
        state.add_artifact.assert_called()

    @pytest.mark.asyncio
    async def test_step_run_status_set_before_execution(self):
        """Step status should be set to RUNNING before execution."""
        execute_fn = AsyncMock(return_value=StepResult(success=True))
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        await orchestrator.execute(context)
        state.update_step_status.assert_any_call(
            "abc12345", "dns", StepStatus.RUNNING
        )


class TestPipelineOrchestratorResume:
    """Tests for resume functionality."""

    @pytest.mark.asyncio
    async def test_resume_skips_completed_steps(self):
        """Resume should skip steps that are already completed."""
        execute_fn = AsyncMock(return_value=StepResult(success=True))
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        state.can_resume_step.return_value = True
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        results = await orchestrator.execute(context, resume=True)
        assert state.can_resume_step.called
        assert execute_fn.call_count == 0
        assert results["dns"].success is True

    @pytest.mark.asyncio
    async def test_resume_executes_incomplete_steps(self):
        """Resume should execute steps that are not completed."""
        execute_fn = AsyncMock(return_value=StepResult(success=True))
        step = MockStep(name="dns", max_retries=0, retry_delay=0, execute_fn=execute_fn)
        state = MagicMock(spec=StateManager)
        state.can_resume_step.return_value = False
        config = MagicMock()
        orchestrator = PipelineOrchestrator([step], config, state)
        context = ScanContext(
            scan_id="abc12345",
            domain="example.com",
            scan_dir=Path("/tmp/scans"),
            config=config,
            state=state,
        )
        results = await orchestrator.execute(context, resume=True)
        assert execute_fn.call_count == 1
        assert results["dns"].success is True
