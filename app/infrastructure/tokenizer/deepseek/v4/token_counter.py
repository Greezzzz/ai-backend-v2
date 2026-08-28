from transformers import AutoTokenizer

from app.domain.llm import ChatMessage
from app.infrastructure.tokenizer.deepseek.v4.encoding_dsv4 import encode_messages


class DeepSeekV4TokenCounter:
    def __init__(
        self,
        model: str = "deepseek-ai/DeepSeek-V4-Flash",
        token_correction: int = 0,
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.token_correction = token_correction

    def count_messages(self, message: list[ChatMessage]) -> int:

        payload = [{"role": msg.role, "content": msg.content} for msg in message]

        prompt = encode_messages(
            payload,
            thinking_mode="chat",
        )

        tokens = self.tokenizer.encode(prompt)

        # Tokenizer lokal selalu undercount 79 token dari aktual input token
        # provider (konstan per request). Koreksi ini bikin estimasi mendekati
        # hitungan server, supaya budget context tidak over-allocate.
        return len(tokens) + self.token_correction
