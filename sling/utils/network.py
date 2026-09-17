"""Network utilities including rate limiting."""

import asyncio
from asyncio_throttle import Throttler
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for network operations."""

    def __init__(self, rate: float, burst: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            rate: Requests per second
            burst: Maximum burst size (defaults to rate)
        """
        self.throttler = Throttler(rate_limit=rate, burst=burst or int(rate))

    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        await self.throttler.acquire()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


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