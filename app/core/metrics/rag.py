from prometheus_client import Counter, Histogram

rag_documents_total = Counter(
    "rag_documents_total",
    "Total number of documents uploaded",
    [
        "model",
    ]
)

rag_chunks_total = Counter(
    "rag_chunks_total",
    "Total number of chunks embedded and stored",
)

rag_retrieval_duration_seconds = Histogram(
    "rag_retrieval_duration_seconds",
    "RAG retrieval duration in seconds (embed query + search)",
    [
        "top_k",
    ]
)

rag_retrieval_hits_total = Counter(
    "rag_retrieval_hits_total",
    "Total number of retrieved chunks (search returned results)",
)

rag_retrieval_misses_total = Counter(
    "rag_retrieval_misses_total",
    "Total number of retrievals that returned 0 chunks",
)
