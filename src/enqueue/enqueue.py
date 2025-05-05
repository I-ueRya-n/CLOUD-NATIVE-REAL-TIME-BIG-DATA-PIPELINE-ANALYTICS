import logging
import json
from typing import Dict, Any, Optional
from flask import current_app, request, Request
import redis


def main() -> str:
    """ Redis message queue manager.

    BASED HEAVILY ON THE EXAMPLE GIVEN IN THE comp90024 GITHUB
    ALL CREDIT TO WRITERS
    LIKE, PRETTY MUCH COPIED
    BECAUSE IM TOO SCARED TO CHANGE IT

    Handles:
    - Gets the next incoming from the redis queue
    - Initializes of Redis client
    - Serializes JSON payload 
    - Adds to the Redis queue

    e.g.
    Topic: "oa_debate_people"
    Example payload:
        {
            "person": person_id,
            "house": house (senate or representatives)
        }

    Returns:
        Success message if successful, else error message

    Raises:
        redis.RedisError: For connection/operation failures
        JSONDecodeError: If invalid payload received
    """
    req: Request = request

    current_app.logger.info(
        f'Recieived queue request with headers: {req.headers}'
    )

    

    # Extract routing parameters
    topic: Optional[str] = req.headers.get('X-Fission-Params-Topic')
    json_data: Dict[str, Any] = req.get_json()
    
    # Initialize Redis client with type annotation
    redis_client: redis.StrictRedis = redis.StrictRedis(
        host='redis-headless.redis.svc.cluster.local',
        socket_connect_timeout=5,
        decode_responses=False
    )
    
    # Publish message to queue
    redis_client.lpush(
        topic,
        json.dumps(json_data).encode('utf-8')
    )
    
    # Structured logging with message metrics
    current_app.logger.info(
        f'Enqueued to {topic} topic - '
        f'Payload size: {len(json_data)} bytes'
    )
    
    return f'Enqueued to {topic} topic - Payload size: {len(json_data)} bytes'

