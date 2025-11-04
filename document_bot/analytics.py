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


def record_validation_event(validator_name: str, question: str, passed: bool,
                            duration_ms: float, reason: Optional[str] = None,
                            user_id: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    emit("validation", {
        "validator": validator_name,
        "passed": passed,
        "duration_ms": round(duration_ms, 2),
        "question_length": len(question),
        **({"reason": reason} if reason else {}),
        **({"user_id": _safe(user_id)} if user_id else {}),
        **(meta or {})
    })


def record_question_attempt(user_id: Optional[str], flagged: bool,
                           validator_failed: Optional[str] = None,
                           is_recovery: bool = False):
    emit("question_attempt", {
        "user_id": _safe(user_id) if user_id else "anon",
        "flagged": flagged,
        "is_recovery": is_recovery,
        **({"validator_failed": validator_failed} if validator_failed else {})
    })
