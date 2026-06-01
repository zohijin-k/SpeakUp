"""Coach service — L1 rule engine + L3 LLM comprehensive evaluation.

LLM provider is selected via LLM_PROVIDER env var (gemini | claude). See llm.py.
"""

from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from packages.schema import (
    SignalWindow,
    SessionBundle,
    ComprehensiveReport,
    LiveHudResponse,
)
from .rules import evaluate as evaluate_window
from .llm import generate, provider_info

app = FastAPI(title="Presentation Coach")


@app.get("/healthz")
async def healthz():
    return {"ok": True, **provider_info()}


@app.post("/live", response_model=LiveHudResponse)
async def live(window: SignalWindow):
    """L1 — rule-based per-5s-window HUD signals. No LLM."""
    return evaluate_window(window)


@app.post("/comprehensive", response_model=ComprehensiveReport)
async def comprehensive(bundle: SessionBundle):
    """L3 — LLM-based structured evaluation of the entire session."""
    started = time.perf_counter()
    print(
        "[coach/comprehensive] start "
        f"session={bundle.session_id} duration={bundle.duration_s:.1f}s "
        f"events={len(bundle.events)} moments={len(bundle.annotated_moments)} "
        f"stt={len(bundle.stt_segments)}",
        flush=True,
    )
    try:
        report = generate(bundle)
        elapsed = time.perf_counter() - started
        print(
            f"[coach/comprehensive] done session={bundle.session_id} elapsed={elapsed:.1f}s",
            flush=True,
        )
        return report
    except Exception as e:
        elapsed = time.perf_counter() - started
        print(
            f"[coach/comprehensive] failed session={bundle.session_id} elapsed={elapsed:.1f}s error={type(e).__name__}: {e}",
            flush=True,
        )
        return JSONResponse(
            {
                "error": f"LLM call failed: {type(e).__name__}: {e}",
                "duration_s": bundle.duration_s,
                "event_count": len(bundle.events),
                "stt_segment_count": len(bundle.stt_segments),
                "elapsed_s": round(elapsed, 1),
            },
            status_code=502,
        )
