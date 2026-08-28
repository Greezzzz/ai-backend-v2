from prometheus_client import Counter, Histogram

llm_request_total = Counter(
    "llm_request_total",
    "Total number of LLM Requests",
    [
        "model",
        "status",
        "provider"
    ]
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "Duration LLM Request in Seconds",
    [
        "model",
        "provider"
    ]
)

llm_input_tokens_total = Counter(
    "llm_input_tokens_total",
    "Total number of LLM Input Tokens",
    [
        "model",
        "provider"
    ]
)

llm_output_tokens_total = Counter(
    "llm_output_tokens_total",
    "Total number of LLM Output Tokens",
    [
        "model",
        "provider"
    ]
)

llm_error_total = Counter(
    "llm_error_total",
    "Total number of LLM Errors by type",
    [
        "error_type",
        "model",
        "provider"
    ]
)