from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies.auth import get_current_user
from app.core.exceptions.business import BusinessException
from app.core.exceptions.error_codes import ErrorCode
from app.features.auth.model import User
from app.features.chat.dependencies import get_chat_usecase
from app.features.chat.schemas import (
    ChatRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
)
from app.features.chat.usecase import ChatUseCase

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: User = Depends(get_current_user),
    usecase: ChatUseCase = Depends(get_chat_usecase),
):
    rows = await usecase.list_conversations(user_id=user.id)

    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                last_message=last_message,
            )
            for conversation, last_message in rows
        ]
    )


@router.get("/conversations/{id}", response_model=ConversationDetailResponse)
async def get_conversation(
    id: int,
    user: User = Depends(get_current_user),
    usecase: ChatUseCase = Depends(get_chat_usecase),
):
    conversation = await usecase.get_conversation_with_messages(
        id=id,
        user_id=user.id,
    )

    if conversation is None:
        raise BusinessException(
            message=f"Conversation with id {id} not found.",
            code=ErrorCode.CONVERSATION_NOT_FOUND,
            status_code=404,
        )

    return ConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ],
    )


@router.post("/conversations", response_model_exclude_none=True)
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    usecase: ChatUseCase = Depends(get_chat_usecase),
):
    answer = await usecase.chat(
        conversation_id=req.conversation_id,
        message=req.message,
        user_id=user.id,
    )

    return answer


@router.post("/stream")
async def stream_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    usecase: ChatUseCase = Depends(get_chat_usecase),
):
    return StreamingResponse(
        usecase.stream_chat(
            conversation_id=req.conversation_id,
            message=req.message,
            user_id=user.id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )