from datetime import datetime

from pydantic import BaseModel, Field

from app.application.context.result import ContextResult
from app.domain.llm import LLMResponse


class ChatRequest(BaseModel):
    message: str = Field(max_length=1000, min_length=3, description="User prompt")
    conversation_id: int | None = Field(
        default=None,
        description="Conversation ID for the chat. If not provided, a new conversation will be created.",
    )


class ChatResponse(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation")
    data: LLMResponse = Field(..., description="Response from the LLM")
    context_result: ContextResult


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    last_message: str | None = Field(
        default=None,
        description="Preview pesan terakhir dalam percakapan.",
    )


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    messages: list[MessageResponse]
