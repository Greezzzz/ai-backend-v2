from functools import lru_cache

import tiktoken

from app.domain.llm import ChatMessage


class OpenAITokenCounter:
    """Token counter untuk model OpenAI-compatible via tiktoken.

    Memakai encoding resmi OpenAI: `o200k_base` untuk model GPT-4o/gpt-4.1
    (dan model modern lain), `cl100k_base` untuk gpt-3.5/gpt-4 lama.

    Catatan: tiktoken tidak butuh download model (berbeda dengan
    AutoTokenizer transformers) — encoding sudah dibundel di library.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        token_correction: int = 0,
    ):
        self._model = model
        self._encoding = self._resolve_encoding(model)
        self.token_correction = token_correction

    @staticmethod
    @lru_cache(maxsize=8)
    def _resolve_encoding(model: str) -> tiktoken.Encoding:
        """Pilih encoding tiktoken berdasarkan nama model.

        Prioritas: nama model eksplisit yang dikenal tiktoken, lalu fallback
        ke pola gpt-4o*/gpt-4.1* → o200k_base, sisanya cl100k_base.
        """
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            pass

        if "o200k" in model or "gpt-4o" in model or "gpt-4.1" in model:
            return tiktoken.get_encoding("o200k_base")

        return tiktoken.get_encoding("cl100k_base")

    def count_messages(self, messages: list[ChatMessage]) -> int:
        """Hitung token estimasi untuk list pesan (format chatml).

        Mengikuti konvensi resmi OpenAI: tiap pesan punya overhead
        `<|im_start|>{role}\n{content}<|im_end|>\n`, plus closing token.
        """
        per_message = 4  # <|im_start|>, role, <|im_end|>, \n
        tokens = 0

        for msg in messages:
            tokens += per_message
            tokens += len(self._encoding.encode(msg.content))
            if msg.role:
                tokens += 1

        tokens += 3  # priming <|im_start|>assistant

        return tokens + self.token_correction