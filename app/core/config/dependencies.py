import redis.asyncio as redis
from fastapi import Request

from app.core.resources import Resources


def get_resources(
        request: Request
) -> Resources:
    return request.app.state.resources


def get_redis(
        request: Request
) -> redis.Redis:
    return request.app.state.redis