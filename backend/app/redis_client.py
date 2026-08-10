import redis.asyncio as redis
from app.config import settings

try:
    redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    redis_client = redis.Redis(connection_pool=redis_pool)
except Exception:
    redis_pool = None
    redis_client = None


def get_redis():
    return redis_client
