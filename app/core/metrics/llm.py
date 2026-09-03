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

# Selisih estimasi tokenizer lokal vs usage aktual provider (aktual - estimasi).
# Positif = undercount (estimasi lebih kecil dari aktual), negatif = overcount.
# Histogram ini BISA negatif — untuk rata-rata (sum/count), jangan pakai
# histogram_quantile (Prometheus menganggap observasi >= 0).
llm_token_estimation_error = Histogram(
    "llm_token_estimation_error",
    "Estimation error of input tokens (actual - estimated)",
    [
        "model",
        "provider"
    ],
    buckets=[-512, -256, -128, -64, -32, 0, 32, 64, 128, 256, 512],
)

# Besar selisih (selalu >= 0): |aktual - estimasi|. Histogram non-negatif,
# jadi histogram_quantile p50/p95 valid untuk melihat "berapa besar bedanya".
llm_token_estimation_abs_error = Histogram(
    "llm_token_estimation_abs_error",
    "Absolute estimation error of input tokens |actual - estimated|",
    [
        "model",
        "provider"
    ],
    buckets=[0, 16, 32, 64, 128, 256, 512, 1024],
)