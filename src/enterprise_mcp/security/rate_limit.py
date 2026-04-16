"""Request rate-limiting implementation.

The limiter uses Redis when available and falls back to an in-memory window
counter when Redis is unavailable.
"""

import threading
import time

import redis

from enterprise_mcp.config import settings
from enterprise_mcp.data.cache import cache_client


class RateLimiter:
    """Rate limiter with backend fallback behavior."""

    def __init__(self) -> None:
        """Initialize in-memory fallback state."""
        self._memory_lock = threading.Lock()
        self._memory_state: dict[str, tuple[int, float]] = {}

    def allow(self, key: str) -> bool:
        """Check whether a request key is allowed in the current window.

        Args:
            key: Rate-limit partition key.

        Returns:
            ``True`` when request is allowed, otherwise ``False``.
        """
        if cache_client.client:
            return self._allow_redis(cache_client.client, key)
        return self._allow_memory(key)

    def _allow_redis(self, client: redis.Redis, key: str) -> bool:
        """Evaluate request quota using Redis counters."""
        redis_key = f"ratelimit:{key}"
        current = int(client.incr(redis_key))
        if current == 1:
            client.expire(redis_key, settings.rate_limit_window_seconds)
        return current <= settings.rate_limit_requests_per_minute

    def _allow_memory(self, key: str) -> bool:
        """Evaluate request quota using in-process counters."""
        now = time.time()
        window = float(settings.rate_limit_window_seconds)

        with self._memory_lock:
            count, expires_at = self._memory_state.get(key, (0, now + window))
            if now >= expires_at:
                count = 0
                expires_at = now + window

            count += 1
            self._memory_state[key] = (count, expires_at)

        return count <= settings.rate_limit_requests_per_minute


rate_limiter = RateLimiter()
