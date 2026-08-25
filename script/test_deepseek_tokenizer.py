from transformers import AutoTokenizer

from app.infrastructure.tokenizer.deepseek.v4.encoding_dsv4 import encode_messages

MODEL_NAME = "deepseek-ai/DeepSeek-V4-Flash"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# messages = [
#     {
#         "role": "user",
#         "content": "Halo, aku Udinxxx",
#     },
#     {
#         "role": "assistant",
#         "content": (
#             "Halo Udinxxx! Senang berkenalan denganmu. 😊\n\n"
#             "Ada yang bisa aku bantu hari ini?"
#         ),
#     },
#     {
#         "role": "user",
#         "content": "siapa namaku tadi?",
#     },
# ]

messages = [{"role": "user", "content": "Hello"}]

raw_tokens = len(tokenizer.encode("".join(message["content"] for message in messages)))

chat_prompt = encode_messages(
    messages,
    thinking_mode="chat",
)

chat_tokens = len(tokenizer.encode(chat_prompt))

thinking_prompt = encode_messages(
    messages,
    thinking_mode="thinking",
)

thinking_tokens = len(tokenizer.encode(thinking_prompt))

print("raw      :", raw_tokens)
print("chat     :", chat_tokens)
print("thinking :", thinking_tokens)
