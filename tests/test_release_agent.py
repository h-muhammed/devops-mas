"""Tests for release tools and Release Agent (LLM mocked)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.release_agent import _normalize_release_output, run_release_agent
from tools.release_tools import (
    build_release_bundle,
    normalize_release_decision,
)


def test_build_release_bundle_ok() -> None:
    bundle = build_release_bundle(
        {"incident_detected": True},
        {"root_cause": "x"},
        {"primary_strategy": "config_fix"},
    )
    assert bundle["incident_report"]["incident_detected"] is True
    assert bundle["rca"]["root_cause"] == "x"
    assert bundle["fix_plan"]["primary_strategy"] == "config_fix"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("APPROVE", "APPROVE"),
        ("approve", "APPROVE"),
        ("BLOCK", "BLOCK"),
        ("ROLLBACK_REQUIRED", "ROLLBACK_REQUIRED"),
        ("rollback required", "ROLLBACK_REQUIRED"),
        ("nonsense", "BLOCK"),
        (None, "BLOCK"),
    ],
)
def test_normalize_release_decision(raw: object, expected: str) -> None:
    assert normalize_release_decision(raw) == expected


def test_build_release_bundle_type_errors() -> None:
    with pytest.raises(TypeError):
        build_release_bundle({}, {}, "not a dict")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        build_release_bundle({}, "x", {})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        build_release_bundle("x", {}, {})  # type: ignore[arg-type]


def test_normalize_release_output_fills_defaults() -> None:
    out = _normalize_release_output({})
    assert out["decision"] == "BLOCK"
    assert out["summary"]
    assert out["rationale"]
    assert out["suggested_actions"]


def test_run_release_agent_uses_llm_and_parses_json() -> None:
    fake_json = {
        "decision": "APPROVE",
        "summary": "Low risk; plan is complete.",
        "rationale": ["Severity LOW", "Plan has dry-runs"],
        "blockers_or_gates": [],
        "suggested_actions": ["Run in staging"],
    }
    fake_message = MagicMock()
    fake_message.content = json.dumps(fake_json)

    with patch("agents.release_agent._llm") as mock_llm:
        mock_llm.invoke.return_value = fake_message
        result = run_release_agent(
            {"severity": "LOW", "incident_detected": True},
            {"root_cause": "quota", "confidence": 0.8},
            {"risk_level": "LOW", "primary_strategy": "config_fix"},
        )

    mock_llm.invoke.assert_called_once()
    call_arg = mock_llm.invoke.call_args[0][0]
    assert "Release bundle (JSON):" in call_arg
    assert "quota" in call_arg

    assert result["decision"] == "APPROVE"
    assert result["summary"] == "Low risk; plan is complete."
    assert "Severity LOW" in result["rationale"]
