from prometheus_client import Counter

chat_messages_sent_total = Counter(
    "chat_messages_sent_total",
    "Total number of chat messages persisted",
    [
        "role",
    ]
)
