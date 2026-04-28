from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis

from app.config import CACHE_TTL_SECONDS, REDIS_PREFIX, REDIS_URL


logger = logging.getLogger(__name__)
_cache_client: Optional[redis.Redis] = None


def _key(name: str) -> str:
    return f"{REDIS_PREFIX}{name}"


def get_cache_client() -> Optional[redis.Redis]:
    global _cache_client
    if _cache_client is None:
        _cache_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _cache_client


def get_json(key: str) -> Any:
    client = get_cache_client()
    if client is None:
        return None
    try:
        raw = client.get(_key(key))
        return json.loads(raw) if raw else None
    except redis.RedisError as exc:
        logger.warning("Redis get failed for %s: %s", key, exc)
        return None


def set_json(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS):
    client = get_cache_client()
    if client is None:
        return
    try:
        client.set(_key(key), json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
    except redis.RedisError as exc:
        logger.warning("Redis set failed for %s: %s", key, exc)


def delete_keys(*keys: str):
    if not keys:
        return
    client = get_cache_client()
    if client is None:
        return
    try:
        prefixed = [_key(key) for key in keys]
        client.delete(*prefixed)
    except redis.RedisError as exc:
        logger.warning("Redis delete failed for %s: %s", keys, exc)


def delete_pattern(pattern: str):
    client = get_cache_client()
    if client is None:
        return
    try:
        keys = list(client.scan_iter(match=_key(pattern), count=200))
        if keys:
            client.delete(*keys)
    except redis.RedisError as exc:
        logger.warning("Redis delete pattern failed for %s: %s", pattern, exc)


def clear_cache():
    delete_pattern("*")


def cache_stats() -> dict:
    client = get_cache_client()
    if client is None:
        return {"enabled": False, "prefix": REDIS_PREFIX, "total": 0}
    try:
        total = sum(1 for _ in client.scan_iter(match=_key("*"), count=200))
        return {"enabled": True, "prefix": REDIS_PREFIX, "total": total}
    except redis.RedisError as exc:
        logger.warning("Redis stats failed: %s", exc)
        return {"enabled": False, "prefix": REDIS_PREFIX, "total": 0, "error": str(exc)}
