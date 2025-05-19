import os
import redis

def get_redis_client():
    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "redis"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        password=os.environ.get("REDIS_PASSWORD", None),
        decode_responses=True
    )

def enqueue_data(queue_name, data):
    client = get_redis_client()
    client.lpush(queue_name, data)