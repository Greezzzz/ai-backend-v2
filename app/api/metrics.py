from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.dependencies.auth import require_api_key

router = APIRouter()


@router.get("/metrics", dependencies=[Depends(require_api_key)])
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )