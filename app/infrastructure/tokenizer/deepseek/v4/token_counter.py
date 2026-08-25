from transformers import AutoTokenizer

from app.domain.llm import ChatMessage
from app.infrastructure.tokenizer.deepseek.v4.encoding_dsv4 import encode_messages


class DeepSeekV4TokenCounter:
    def __init__(self, model: str = "deepseek-ai/DeepSeek-V4-Flash"):
        self.tokenizer = AutoTokenizer.from_pretrained(model)

    def count_messages(self, message: list[ChatMessage]) -> int:

        payload = [{"role": msg.role, "content": msg.content} for msg in message]

        prompt = encode_messages(
            payload,
            thinking_mode="chat",
        )

        tokens = self.tokenizer.encode(prompt)

        return len(tokens)
