from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 35.0


class ProviderResponseError(ValueError):
    """Raised when a provider response cannot be used safely."""


def _compact_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Send evidence summaries only; never ship raw telemetry rows to the LLM."""
    return {
        "session_id": analysis.get("session_id"),
        "source_type": analysis.get("source_type"),
        "sample_count": analysis.get("sample_count"),
        "quality_score": analysis.get("quality_score"),
        "health_score": analysis.get("health_score"),
        "risk": analysis.get("risk"),
        "anomaly_regions": [
            {
                "start_time": region.get("start_time"),
                "end_time": region.get("end_time"),
                "score": region.get("score"),
                "top_signals": region.get("top_signals", [])[:5],
            }
            for region in analysis.get("anomaly_regions", [])[:8]
        ],
        "hypotheses": [
            {
                "name": hypothesis.get("name"),
                "subsystem": hypothesis.get("subsystem"),
                "severity": hypothesis.get("severity"),
                "confidence": hypothesis.get("confidence"),
                "evidence": [
                    evidence.get("observation")
                    for evidence in hypothesis.get("evidence", [])[:6]
                ],
                "contradictions": [
                    evidence.get("observation")
                    for evidence in hypothesis.get("contradictions", [])[:4]
                ],
                "recommended_action": hypothesis.get("recommended_action"),
                "blocked_claims": hypothesis.get("blocked_claims", [])[:8],
            }
            for hypothesis in analysis.get("hypotheses", [])[:3]
        ],
        "limitations": analysis.get("limitations", [])[:6],
        "metrics": analysis.get("metrics", {}),
        "model": {
            key: value
            for key, value in (analysis.get("model") or {}).items()
            if key
            in {
                "name",
                "version",
                "status",
                "runtime_mode",
                "capability_signals",
                "feature_count",
                "threshold",
                "artifact_sha256",
            }
        },
    }


def provider_status() -> dict[str, Any]:
    """Expose routing readiness without ever returning a secret."""
    return {
        "configured": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
        "gateway": "openrouter",
        "fast_model": os.getenv("OCTANE_AI_FAST_MODEL", ""),
        "deep_model": os.getenv("OCTANE_AI_DEEP_MODEL", ""),
        "timeout_seconds": _timeout_seconds(),
        "raw_telemetry_shared": False,
        "fallback_available": True,
    }


def _timeout_seconds() -> float:
    try:
        return min(
            max(float(os.getenv("OCTANE_AI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)), 20.0),
            240.0,
        )
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _fallback(analysis: dict[str, Any], reason: str, reason_code: str) -> dict[str, Any]:
    hypothesis = (analysis.get("hypotheses") or [{}])[0]
    name = hypothesis.get("name") or "No retained component hypothesis"
    confidence = hypothesis.get("confidence")
    confidence_text = (
        f"{round(confidence * 100)}%"
        if isinstance(confidence, (int, float))
        else "not assigned"
    )
    action = hypothesis.get("recommended_action") or (
        "Review the highlighted anomaly regions and compare them with a known baseline."
    )
    caveats = analysis.get("limitations", [])[:3]
    if not caveats:
        caveats = ["This is telemetry screening evidence, not a confirmed component diagnosis."]
    return {
        "status": "deterministic_fallback",
        "provider": "local",
        "model": "sentinel-evidence-template",
        "mode": "deterministic",
        "executive_summary": (
            f"Sentinel screened this session at {analysis.get('health_score', '—')}/100 health with "
            f"{str(analysis.get('risk', 'unknown')).upper()} risk. The leading evidence-backed hypothesis is "
            f"'{name}' with confidence {confidence_text}."
        ),
        "inspection_steps": [action],
        "caveats": caveats,
        "reason": reason,
        "reason_code": reason_code,
    }


def _message_text(body: Any) -> str:
    if not isinstance(body, dict):
        raise ProviderResponseError("Provider returned a non-object response.")
    if body.get("error"):
        raise ProviderResponseError("Provider returned an error object.")

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderResponseError("Provider response did not contain a completion choice.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ProviderResponseError("Provider response did not contain a message object.")

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        joined = "\n".join(part.strip() for part in parts if part.strip())
        if joined:
            return joined

    # Some reasoning models expose structured output in a reasoning field.
    for key in ("reasoning_content", "reasoning"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ProviderResponseError("Provider message did not contain usable text.")


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise ProviderResponseError("Provider text did not contain a JSON object.")
        try:
            parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("Provider JSON could not be parsed.") from exc
    if not isinstance(parsed, dict):
        raise ProviderResponseError("Provider JSON was not an object.")
    return parsed


def _bounded_strings(value: Any, limit: int, item_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:item_limit] for item in value[:limit] if str(item).strip()]


def _validated_output(parsed: dict[str, Any], model: str, mode: str) -> dict[str, Any]:
    summary = str(parsed.get("executive_summary", "")).strip()[:1600]
    steps = _bounded_strings(parsed.get("inspection_steps"), 4, 500)
    caveats = _bounded_strings(parsed.get("caveats"), 4, 500)
    if not summary or not steps or not caveats:
        raise ProviderResponseError("Provider JSON omitted required explanation fields.")

    # Unsupported component actions are not allowed in the actionable part of an AI answer.
    actionable = f"{summary} {' '.join(steps)}".lower()
    prohibited_actions = (
        "replace the injector",
        "injector failure",
        "ignition timing fault",
        "ecu fault code",
        "dtc confirms",
        "afr confirms",
        "ethanol content is",
        "fuel pump failure",
    )
    if any(term in actionable for term in prohibited_actions):
        raise ProviderResponseError("Provider crossed an unsupported component-claim boundary.")

    return {
        "status": "ai_generated",
        "provider": "openrouter",
        "model": model,
        "mode": mode,
        "executive_summary": summary,
        "inspection_steps": steps,
        "caveats": caveats,
        "reason": None,
        "reason_code": None,
    }


async def explain_analysis(analysis: dict[str, Any], mode: str = "fast") -> dict[str, Any]:
    if mode == "local":
        return _fallback(
            analysis,
            "Instant local explanation selected; no cloud request was made.",
            "local_mode_requested",
        )

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return _fallback(
            analysis,
            "No cloud key is configured; the local evidence summary was used.",
            "provider_not_configured",
        )

    fast_model = os.getenv("OCTANE_AI_FAST_MODEL", "")
    deep_model = os.getenv("OCTANE_AI_DEEP_MODEL", "")
    model = deep_model if mode == "deep" else fast_model
    if not model:
        return _fallback(analysis, "Configure an explicit provider model identifier.", "model_not_configured")
    evidence = _compact_analysis(analysis)
    system_prompt = (
        "You are the explanation layer for OctaneOS Sentinel, an automotive telemetry screening system. "
        "You must never invent sensor values, DTCs, component failures, AFR, injector condition, ignition timing, "
        "ethanol percentage, or Yamaha R15 validation that is not explicitly present in the supplied evidence. "
        "The anomaly model detects statistical deviation, not failed components. "
        "Treat blocked claims and limitations as hard boundaries. "
        "Return only one JSON object with exactly these keys: executive_summary (string), "
        "inspection_steps (array of 1-4 strings), caveats (array of 1-4 strings). "
        "Use cautious engineering language such as possible, screening, compare, inspect, and verify."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Explain this structured Sentinel evidence:\n"
                + json.dumps(evidence, separators=(",", ":"), allow_nan=False),
            },
        ],
        "temperature": 0.1,
        "max_tokens": 700,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OCTANE_APP_URL", "http://localhost:5173"),
        "X-Title": "OctaneOS Sentinel",
    }

    timeout_seconds = _timeout_seconds()
    timeout = httpx.Timeout(timeout_seconds, connect=min(15.0, timeout_seconds))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        content = _message_text(body)
        parsed = _parse_json_object(content)
        return _validated_output(parsed, model, mode)
    except httpx.TimeoutException:
        return _fallback(
            analysis,
            f"The cloud explanation exceeded the {timeout_seconds:.0f}-second limit; local evidence remained available.",
            "provider_timeout",
        )
    except httpx.HTTPStatusError as exc:
        return _fallback(
            analysis,
            f"The cloud explanation service returned HTTP {exc.response.status_code}; local evidence remained available.",
            "provider_http_error",
        )
    except (ProviderResponseError, json.JSONDecodeError):
        return _fallback(
            analysis,
            "The cloud response failed Sentinel's structure or safety validation; the local evidence summary was used.",
            "provider_response_invalid",
        )
    except Exception:
        return _fallback(
            analysis,
            "The cloud explanation was unavailable; the local evidence summary was used.",
            "provider_unavailable",
        )
