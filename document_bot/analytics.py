import hashlib
import json
import logging
import os
import time
from typing import Optional, Dict, Any

from document_bot.metrics_prom import LLM_LAT_MS

ENABLED = os.getenv("ANALYTICS_ENABLED", "True") == "True"
log = logging.getLogger("analytics")


def _safe(session_key: Optional[str]) -> str:
    """Hash session/user id so we never log raw identifiers."""
    if not session_key:
        return "anon"
    return hashlib.sha256(session_key.encode()).hexdigest()[:12]


def debug(event: str, props: Dict[str, Any]) -> None:
    if not ENABLED:
        return
    log.debug(json.dumps({"event": event, **props}))


def emit(event: str, props: Dict[str, Any]) -> None:
    if not ENABLED:
        return
    log.info(json.dumps({"event": event, **props}))


def error(event: str, props: Dict[str, Any]) -> None:
    if not ENABLED:
        return
    log.error(json.dumps({"event": event, **props}))


def time_block():
    """Context manager to measure elapsed ms."""
    t0 = time.perf_counter()

    def finish(extra: Dict[str, Any] = None) -> Dict[str, Any]:
        dt = (time.perf_counter() - t0) * 1000.0
        return {"duration_ms": round(dt, 2), **(extra or {})}

    return t0, finish


def record_llm_call(model: str, ok: bool, duration_ms: float,
                    tokens: Optional[Dict[str, int]] = None,
                    meta: Optional[Dict[str, Any]] = None):
    LLM_LAT_MS.observe(duration_ms)
    emit("llm_call", {
        "model": model,
        "ok": ok,
        "duration_ms": round(duration_ms, 2),
        **({"tokens": tokens} if tokens else {}),
        **(meta or {})
    })
