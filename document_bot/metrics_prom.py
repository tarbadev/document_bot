from prometheus_client import Histogram

LLM_LAT_MS = Histogram(
    "llm_latency_ms",
    "Latency of LLM calls (ms)",
    buckets=(50, 100, 200, 400, 800, 1600, 3200, 6400),
)

def observe_llm(ms: float) -> None:
    LLM_LAT_MS.observe(ms)
