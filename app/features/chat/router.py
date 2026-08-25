from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.features.chat.dependencies import get_chat_usecase
from app.features.chat.schemas import ChatRequest
from app.features.chat.usecase import ChatUseCase

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/conversations/{id}", response_model_exclude_none=True)
async def get_conversation(id: int, usecase: ChatUseCase = Depends(get_chat_usecase)):
    return await usecase.get_conversation(id=id)


@router.post("/conversations", response_model_exclude_none=True)
async def chat(req: ChatRequest, usecase: ChatUseCase = Depends(get_chat_usecase)):
    answer = await usecase.chat(
        conversation_id=req.conversation_id,
        message=req.message,
        model=req.model,
    )

    return answer
