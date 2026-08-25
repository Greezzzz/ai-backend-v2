from prometheus_client import Counter

retry_attempts_total = Counter(
    "retry_attempts_total",
    "Total number of Retry Attempts",
    [
        "attempt",
        "operation",
    ]
)

retry_exhausted_total = Counter(
    "retry_exhausted_total",
    "Total number of Retry Exhausted",
    [
        "operation",
        "exception_type",
    ]
)