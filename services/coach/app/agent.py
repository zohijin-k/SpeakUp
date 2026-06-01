"""Real-time agent feedback — short, scenario-aware nudges per trigger.

This is the L2-style live coach: the browser fires off small trigger events
(silence ≥5s, gaze drift ≥5s, filler-burst, etc.) and we synthesize a single
short Korean sentence per fire. The browser handles rate-limiting and dedup;
this endpoint only does the prompt + LLM call.

Why a separate module from llm.py: the comprehensive evaluator deals with a
huge structured SessionBundle and a strict response_schema. Here we want the
opposite — tiny payload, ~50-token freeform text, sub-2s latency.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


TriggerKind = Literal[
    "silence",
    "gaze",
    "smile_absence",
    "motion_absence",
    "filler",
    "speech_rate",
    "content",
]


class MultimodalContext(BaseModel):
    """Snapshot of the user's recent behavior across modalities.

    Always sent alongside every trigger so the LLM judges a moment as a whole
    person, not a single isolated signal. The agent's value proposition is
    *exactly* this multimodal fusion — language + gaze + expression + gesture
    + prosody as a joint judgment, not separate red flags.
    """

    # ── Verbal (STT) — structured: previous utterances vs current utterance ──
    # Why two fields instead of one big string: when a "content" trigger fires
    # we want the LLM to *coach the latest sentence only*, not whatever it
    # finds interesting in the back-context. Keeping them separate also lets
    # us label "이 발화 평가 / 이전은 맥락" explicitly in the prompt.
    #
    # `recent_transcript` is kept for back-compat (older clients send only
    # this). New clients populate the structured pair below.
    recent_transcript: str = ""
    previous_utterances: List[str] = Field(default_factory=list)
    current_utterance: str = ""
    # Words-per-minute over the last ~30s window, computed in the browser.
    wpm: Optional[float] = None
    # Total filler hits this session and the most recent few.
    filler_count_total: int = 0
    recent_fillers: List[str] = Field(default_factory=list)

    # ── Nonverbal (vision, smoothed averages of last ~3s) ──
    # All optional so the browser can omit a signal it doesn't have yet.
    gaze_fixation_ratio_avg: Optional[float] = None  # 0..1; high = locked on
    head_yaw_deg_avg: Optional[float] = None         # +left / -right (degrees)
    smile_intensity_avg: Optional[float] = None      # 0..1; 0 = neutral
    expression_change_rate_avg: Optional[float] = None  # 0..high; 0 = frozen face
    hand_velocity_max_avg: Optional[float] = None    # 0..high; 0 = hands still
    posture_sway_avg: Optional[float] = None         # 0..high; high = restless

    # ── Audio / prosody ──
    current_silence_seconds: Optional[float] = None  # ongoing silence run

    # ── Session position ──
    session_elapsed_s: Optional[float] = None        # how far into the practice we are


class AgentTriggerRequest(BaseModel):
    kind: TriggerKind
    scenario: str = "presentation"
    # 세션명 — 대화 상황 그 자체 (예: "졸업논문 발표", "구글 면접 1차"). 빈 문자열이면
    # scenario rubric 톤만 사용.
    situation: str = ""
    focus_goals: List[str] = Field(default_factory=list)
    # 트리거별 측정값 (silence_seconds, gaze_off_seconds, filler_count 등).
    payload: Dict[str, Any] = Field(default_factory=dict)
    # 멀티모달 스냅샷 — 언어 + 비언어를 통합 판단하라고 LLM에 같이 던진다.
    context: MultimodalContext = Field(default_factory=MultimodalContext)
    # 직전 발화 — context.recent_transcript와 같음 (호환용). 새 코드에서는 context 사용.
    recent_transcript: str = ""


class AgentFeedbackResponse(BaseModel):
    # LLM이 굳이 응답 안 줄 수도 있음 (content 트리거에서 평이한 발화면 null).
    message: Optional[str] = None
    tone: Optional[Literal["praise", "nudge", "critique"]] = None


_FEEDBACK_SCHEMA_HINT = (
    '응답 형식(JSON): {"message": "한 줄 피드백 또는 null", '
    '"tone": "praise|nudge|critique 또는 null"}'
)


def _trigger_brief(req: AgentTriggerRequest) -> str:
    """One-liner describing what just happened, in Korean, for the user prompt."""
    p = req.payload
    if req.kind == "silence":
        sec = float(p.get("silence_seconds", 0))
        return f"사용자가 약 {sec:.1f}초간 침묵하고 있습니다."
    if req.kind == "gaze":
        sec = float(p.get("gaze_off_seconds", 0))
        return f"사용자가 약 {sec:.1f}초간 정면(청자 쪽)을 보지 않고 있습니다."
    if req.kind == "smile_absence":
        return "최근 5초간 사용자의 얼굴에서 미소가 한 번도 감지되지 않았습니다 (무표정 지속)."
    if req.kind == "motion_absence":
        return "최근 5초간 사용자의 몸이 거의 움직이지 않았습니다 (제스처/자세 변화 없음)."
    if req.kind == "filler":
        n = int(p.get("filler_count", 0))
        recent = p.get("recent_fillers") or []
        recent_str = ", ".join(recent[-5:]) if recent else "(예시 없음)"
        return f"세션 누적 필러 사용이 {n}회에 도달했습니다 (최근: {recent_str})."
    if req.kind == "speech_rate":
        wpm = float(p.get("wpm", 0))
        return f"최근 1분 기준 말 속도가 약 {wpm:.0f} WPM입니다."
    if req.kind == "content":
        return f'사용자가 방금 다음과 같이 말했습니다: "{req.recent_transcript.strip()}"'
    return f"트리거: {req.kind}"


def _trigger_directive(kind: TriggerKind) -> str:
    """What the LLM should *do* for this kind. Keeps the model focused."""
    if kind == "silence":
        return "침묵이 의도된 강조인지 단순 멈춤인지는 알 수 없으니, 자연스럽게 흐름을 다시 잡으라고 한 줄로 권유."
    if kind == "gaze":
        return "청자(카메라/대화 상대)와의 시선 연결을 한 줄로 권유."
    if kind == "smile_absence":
        return "표정이 굳어있다는 점을 부드럽게 환기. 상황에 맞으면 미소를, 진지한 상황이면 다른 표정 변화를 권유."
    if kind == "motion_absence":
        return "몸이 너무 정지해 있다는 점을 짧게 환기. 자연스러운 손짓이나 자세 변화를 권유."
    if kind == "filler":
        return "필러가 누적되고 있음을 부담스럽지 않게 알리고, 잠깐 호흡 또는 짧은 쉼을 권유."
    if kind == "speech_rate":
        return "말 속도가 너무 빠르거나 너무 느린지 판단해 짧게 조정 권유."
    if kind == "content":
        return (
            "방금 발화가 이 상황(situation)에 적절한지 판단. 매우 좋으면 짧은 칭찬, "
            "어휘/말투/구성에 분명한 개선점이 있으면 한 줄 지적. 둘 다 아니면 message를 null로."
        )
    return "상황에 맞게 한 줄로 반응."


def _system_prompt(req: AgentTriggerRequest) -> str:
    situation_line = (
        f"이번 세션의 대화 상황: '{req.situation}'"
        if req.situation.strip()
        else f"이번 세션의 시나리오 카테고리: {req.scenario}"
    )
    focus_line = (
        f"사용자가 특히 신경 쓰는 항목: {', '.join(req.focus_goals)}"
        if req.focus_goals
        else "특별히 명시된 포커스는 없음."
    )
    return (
        "당신은 한국어 실시간 발화 코치입니다. "
        "사용자가 연습 중인 상황(situation)을 잘 알고, 매 순간 함께 받는 "
        "멀티모달 컨텍스트 — 직전 발화 흐름(언어) + 시선/표정/제스처/말속도/침묵 "
        "(비언어) — 을 종합적으로 보면서 코칭하는 옆 코치입니다.\n"
        f"{situation_line}\n{focus_line}\n"
        "발화 컨텍스트 구조 (중요):\n"
        "- '직전 발화'는 흐름 파악용 맥락일 뿐 — 이미 지나간 문장이라 절대 코칭 대상 아님.\n"
        "- '가장 최근 발화'는 방금 막 끝난 한 문장 — content 트리거에서는 이 한 줄만 평가 대상.\n"
        "- 다른 트리거(silence/gaze/...)에서는 발화가 평가 대상이 아니라, 비언어 신호가 주된 평가 대상.\n"
        "핵심 원칙:\n"
        "- 트리거는 '지금 주목할 단서'일 뿐, 항상 멀티모달 컨텍스트와 함께 판단할 것.\n"
        "  예: 침묵 트리거여도 최근 발화가 좋은 호흡 마무리였다면 칭찬할 수도 있고, "
        "    표정이 어둡고 시선까지 흔들리면 묶어서 짚을 수도 있다.\n"
        "- 상황(situation)에 맞는 어휘/톤으로 말할 것 (논문 발표=학술 청중, 면접=면접관, "
        "  소개팅=상대 1명 등).\n"
        "- 한 신호만 보고 단정하지 말 것. 비언어 컨텍스트가 정상이면 침묵 한 번을 "
        "  굳이 지적하지 않아도 됨.\n"
        "- 직전 발화에 대해 뒤늦게 코멘트하지 말 것. 평가는 항상 '지금 이 시점'의 트리거나 "
        "  '가장 최근 발화'에 대해서.\n"
        "응답 규칙:\n"
        "- 반드시 한 문장, 30자 이내, 한국어 반말체, 따뜻한 톤.\n"
        "- 자명한 사실 나열 금지. '~좀 어때?', '~해보자' 같은 코치 톤.\n"
        "- 굳이 말할 필요 없으면 message를 null로.\n"
        f"{_FEEDBACK_SCHEMA_HINT}"
    )


def _format_context(ctx: "MultimodalContext") -> str:
    """Render the multimodal snapshot for the user prompt. Skip empty fields so
    the model doesn't fixate on zero values that just mean 'we didn't measure
    that this tick'."""
    lines = []
    # Verbal — structured pair takes priority. Fall back to recent_transcript
    # only when the client didn't fill the structured fields (old clients).
    if ctx.previous_utterances or ctx.current_utterance:
        if ctx.previous_utterances:
            prev_lines = "\n".join(f'    · "{u.strip()[:200]}"' for u in ctx.previous_utterances)
            lines.append(f"- 직전 발화 (맥락 참고용, 평가 대상 X):\n{prev_lines}")
        if ctx.current_utterance:
            lines.append(f'- 가장 최근 발화 (있다면 이 한 줄을 평가 대상으로): "{ctx.current_utterance.strip()[:240]}"')
    elif ctx.recent_transcript.strip():
        lines.append(f'- 최근 발화: "{ctx.recent_transcript.strip()[:240]}"')
    if ctx.wpm is not None:
        lines.append(f"- 최근 말 속도: {ctx.wpm:.0f} WPM")
    if ctx.filler_count_total > 0:
        recent = ", ".join(ctx.recent_fillers[-5:]) if ctx.recent_fillers else "-"
        lines.append(f"- 누적 필러: {ctx.filler_count_total}회 (최근: {recent})")
    # Nonverbal — gaze
    if ctx.gaze_fixation_ratio_avg is not None or ctx.head_yaw_deg_avg is not None:
        gaze_bits = []
        if ctx.gaze_fixation_ratio_avg is not None:
            gaze_bits.append(f"정면응시비율 {ctx.gaze_fixation_ratio_avg:.2f}")
        if ctx.head_yaw_deg_avg is not None:
            gaze_bits.append(f"고개 yaw {ctx.head_yaw_deg_avg:+.0f}°")
        lines.append("- 시선: " + ", ".join(gaze_bits))
    # Nonverbal — face
    if ctx.smile_intensity_avg is not None or ctx.expression_change_rate_avg is not None:
        face_bits = []
        if ctx.smile_intensity_avg is not None:
            face_bits.append(f"미소 강도 {ctx.smile_intensity_avg:.2f}")
        if ctx.expression_change_rate_avg is not None:
            face_bits.append(f"표정 변화 {ctx.expression_change_rate_avg:.2f}")
        lines.append("- 표정: " + ", ".join(face_bits))
    # Nonverbal — body
    if ctx.hand_velocity_max_avg is not None or ctx.posture_sway_avg is not None:
        body_bits = []
        if ctx.hand_velocity_max_avg is not None:
            body_bits.append(f"손 움직임 {ctx.hand_velocity_max_avg:.2f}")
        if ctx.posture_sway_avg is not None:
            body_bits.append(f"자세 흔들림 {ctx.posture_sway_avg:.2f}")
        lines.append("- 제스처/자세: " + ", ".join(body_bits))
    # Audio
    if ctx.current_silence_seconds is not None and ctx.current_silence_seconds > 0.5:
        lines.append(f"- 현재 침묵: {ctx.current_silence_seconds:.1f}초 진행 중")
    # Session position
    if ctx.session_elapsed_s is not None:
        lines.append(f"- 세션 시작 후 경과: {ctx.session_elapsed_s:.0f}초")
    return "\n".join(lines) if lines else "(추가 컨텍스트 없음)"


def _user_prompt(req: AgentTriggerRequest) -> str:
    ctx = req.context
    # Back-compat: older clients only sent recent_transcript at the top level.
    if not ctx.recent_transcript and req.recent_transcript:
        ctx = ctx.model_copy(update={"recent_transcript": req.recent_transcript})

    return (
        f"[트리거] {_trigger_brief(req)}\n"
        f"[지시] {_trigger_directive(req.kind)}\n"
        f"[멀티모달 컨텍스트]\n{_format_context(ctx)}\n"
        "위 컨텍스트를 함께 보고 한 줄 코칭을 결정해줘. 트리거 하나만 보지 말 것."
    )


def _generate_with_gemini(req: AgentTriggerRequest) -> AgentFeedbackResponse:
    from google.genai import types  # type: ignore

    from .llm import _get_gemini, GEMINI_MODEL  # reuse the existing singleton

    if not os.environ.get("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY not set")

    client = _get_gemini()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=_user_prompt(req),
        config=types.GenerateContentConfig(
            system_instruction=_system_prompt(req),
            response_mime_type="application/json",
            response_schema=AgentFeedbackResponse,
            temperature=0.7,
            max_output_tokens=120,
        ),
    )
    parsed: Optional[AgentFeedbackResponse] = response.parsed  # type: ignore[attr-defined]
    if parsed is None:
        parsed = AgentFeedbackResponse.model_validate_json(response.text)
    return parsed


def _generate_with_jeonbuk(req: AgentTriggerRequest) -> AgentFeedbackResponse:
    """Jeonbuk student-API path (OpenAI-compatible). Uses the same _jeonbuk_chat
    helper as the comprehensive evaluator so we share the singleton + the
    json_object fallback for gateways that don't support response_format."""
    from .llm import _jeonbuk_chat

    if not os.environ.get("JEONBUK_API_KEY"):
        raise RuntimeError("JEONBUK_API_KEY not set")

    # We can't pass a Pydantic response_schema through the OpenAI-compat layer,
    # so we lean on a strict JSON contract in the prompt + Pydantic validation
    # on the way out. The contract here mirrors AgentFeedbackResponse.
    json_contract = (
        '\n\n반드시 다음 JSON 형식으로만 응답하세요. Markdown 금지:\n'
        '{"message": "한 줄 코칭 한국어 텍스트 또는 null", '
        '"tone": "praise" | "nudge" | "critique" | null}'
    )
    response = _jeonbuk_chat(
        [
            {"role": "system", "content": _system_prompt(req)},
            {"role": "user", "content": _user_prompt(req) + json_contract},
        ],
        temperature=0.7,
    )
    raw = response.choices[0].message.content or ""
    return AgentFeedbackResponse.model_validate_json(raw)


def generate_agent_feedback(req: AgentTriggerRequest) -> AgentFeedbackResponse:
    """Provider-routed agent feedback. Caller wraps in try/except."""
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower().strip()
    if provider == "jeonbuk":
        result = _generate_with_jeonbuk(req)
    else:
        result = _generate_with_gemini(req)
    # Trim — models occasionally return "  하세요. " with trailing whitespace.
    if result.message is not None:
        result.message = result.message.strip() or None
    return result
