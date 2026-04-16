import json
from dataclasses import dataclass

import redis

from enterprise_mcp.config import settings
from enterprise_mcp.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class CacheClient:
    client: redis.Redis | None

    @classmethod
    def from_settings(cls) -> "CacheClient":
        try:
            redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            redis_client.ping()
            return cls(client=redis_client)
        except Exception:
            logger.warning("redis unavailable, cache disabled")
            return cls(client=None)

    def get_json(self, key: str) -> dict | None:
        if not self.client:
            return None
        value = self.client.get(key)
        if value is None:
            return None
        return json.loads(value)

    def set_json(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        if not self.client:
            return
        ttl = ttl_seconds or settings.cache_ttl_seconds
        self.client.setex(key, ttl, json.dumps(value))

    def delete(self, *keys: str) -> None:
        if not self.client or not keys:
            return
        self.client.delete(*keys)


cache_client = CacheClient.from_settings()
