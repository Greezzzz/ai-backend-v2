from fastapi import APIRouter

from app.api.metrics import router as metrics_router
from app.features.auth.router import router as auth_router
from app.features.chat.router import router as chat_router
from app.features.job.router import router as job_router
from app.features.rag.router import router as rag_router

# Router publik / root: hanya health check (dan metrics via API key)
root_router = APIRouter()

# Semua route di bawah prefix /api.
# Proteksi JWT dipasang per-sub-router (chat_router), sedangkan
# auth (register/login) sengaja publik.
api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(job_router)
api_router.include_router(rag_router)


@root_router.get("/health")
async def health():
    return {"status": "ok"}


# /metrics dilindungi API key (lihat app/api/metrics.py)
root_router.include_router(metrics_router)
