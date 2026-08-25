from prometheus_client import Counter, Histogram

http_request_total = Counter(
    "http_request_total",
    "Total number of HTTP Requests",
    [
        "method",
        "path",
        "status_code"
    ]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP Request duration in seconds",
    [
        "method",
        "path"
    ]
)