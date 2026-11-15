import pytest

from app.services.ai_explainer import (
    ProviderResponseError,
    _compact_analysis,
    _message_text,
    _parse_json_object,
    _validated_output,
    provider_status,
)


def valid_explanation():
    return {
        "executive_summary": "A behavioural deviation should be reviewed.",
        "inspection_steps": ["Compare the highlighted window with the reference."],
        "caveats": ["This is screening evidence only."],
    }


def test_compact_analysis_never_includes_raw_telemetry():
    compact = _compact_analysis(
        {
            "session_id": "DEMO",
            "telemetry": [{"rpm": 9999}],
            "hypotheses": [],
            "anomaly_regions": [],
        }
    )
    assert "telemetry" not in compact
    assert "9999" not in str(compact)


def test_message_text_accepts_content_parts_and_reasoning_text():
    parts = {
        "choices": [
            {"message": {"content": [{"type": "text", "text": "{\"ok\":true}"}]}}
        ]
    }
    reasoning = {
        "choices": [
            {"message": {"content": None, "reasoning_content": "{\"ok\":true}"}}
        ]
    }
    assert _message_text(parts) == '{"ok":true}'
    assert _message_text(reasoning) == '{"ok":true}'


def test_json_parser_accepts_fence_and_leading_copy():
    fenced = "console_block_json\n{\"executive_summary\":\"ok\"}\nconsole_block_end"
    leading = "Result follows: {\"executive_summary\":\"ok\"} trailing"
    fenced = fenced.replace("console_block_json", "```json").replace(
        "console_block_end", "```"
    )
    assert _parse_json_object(fenced)["executive_summary"] == "ok"
    assert _parse_json_object(leading)["executive_summary"] == "ok"


def test_provider_output_requires_all_fields():
    with pytest.raises(ProviderResponseError):
        _validated_output({"executive_summary": "only one field"}, "model", "fast")


def test_provider_output_blocks_unsupported_component_action():
    payload = valid_explanation()
    payload["inspection_steps"] = ["Replace the injector immediately."]
    with pytest.raises(ProviderResponseError):
        _validated_output(payload, "model", "fast")


def test_provider_status_never_exposes_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-value")
    status = provider_status()
    assert status["configured"] is True
    assert "api_key" not in status
    assert "secret-value" not in str(status)
