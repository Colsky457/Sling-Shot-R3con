"""Network utilities including rate limiting."""

import asyncio
import contextlib


class RateLimiter:
    """Token bucket rate limiter backed by asyncio.Semaphore.

    Up to ``burst`` requests may proceed concurrently; a background
    refill loop replenishes semaphore permits at ``rate`` per second so
    that the steady-state rate never exceeds ``rate`` while still
    allowing short bursts.
    """

    def __init__(self, rate: float, burst: int | None = None):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Maximum burst size (defaults to rate)
        """
        self.rate = rate
        self.burst = burst or int(rate)
        self._semaphore = asyncio.Semaphore(self.burst)
        self._available = self.burst
        self._lock = asyncio.Lock()
        self._refill_task: asyncio.Task[None] | None = None

    async def _refill_loop(self) -> None:
        """Replenish permits at the configured rate."""
        interval = 1.0 / self.rate
        try:
            while True:
                await asyncio.sleep(interval)
                async with self._lock:
                    if self._available < self.burst:
                        self._available += 1
                        self._semaphore.release()
        except asyncio.CancelledError:
            return

    def _ensure_running(self) -> None:
        """Start the refill loop if it is not already running."""
        if self._refill_task is None or self._refill_task.done():
            self._refill_task = asyncio.create_task(self._refill_loop())

    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        self._ensure_running()
        await self._semaphore.acquire()
        async with self._lock:
            self._available -= 1

    async def close(self) -> None:
        """Cancel the background refill loop."""
        task = self._refill_task
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._refill_task = None

    def __enter__(self) -> "RateLimiter":
        return self

    def __exit__(self, *args: object) -> None:
        if self._refill_task is not None and not self._refill_task.done():
            self._refill_task.cancel()


class ConnectionPool:
    """Simple connection pool for HTTP clients."""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self._semaphore = asyncio.Semaphore(max_connections)
    
    async def acquire(self) -> None:
        await self._semaphore.acquire()
    
    def release(self) -> None:
        self._semaphore.release()
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, *args):
        self.release()