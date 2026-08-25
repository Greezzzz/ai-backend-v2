from fastapi import Request

from app.core.resources import Resources

def get_resources(
        request: Request
) -> Resources:
    return request.app.state.resources