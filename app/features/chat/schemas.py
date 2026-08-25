from pydantic import BaseModel, Field

from app.application.context.result import ContextResult
from app.domain.llm import LLMResponse


class ChatRequest(BaseModel):
    message: str = Field(max_length=1000, min_length=3, description="User prompt")
    conversation_id: int | None = Field(
        default=None,
        description="Conversation ID for the chat. If not provided, a new conversation will be created.",
    )
    model: str | None = Field(
        default=None,
        description="Model to use. If not provided, the default model is used.",
    )


class ChatResponse(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation")
    data: LLMResponse = Field(..., description="Response from the LLM")
    context_result: ContextResult
