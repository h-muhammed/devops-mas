"""Deterministic helpers for preparing and validating release-gate payloads."""

from typing import Any

VALID_DECISIONS = frozenset({"APPROVE", "BLOCK", "ROLLBACK_REQUIRED"})


def build_release_bundle(
    incident_report: dict[str, Any],
    rca: dict[str, Any],
    fix_plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Combine incident, RCA, and fix plan into one JSON-serializable document for the agent.

    Raises:
        TypeError: If any input is not a dict.
    """
    if not isinstance(incident_report, dict):
        raise TypeError("incident_report must be a dict")
    if not isinstance(rca, dict):
        raise TypeError("rca must be a dict")
    if not isinstance(fix_plan, dict):
        raise TypeError("fix_plan must be a dict")
    return {
        "incident_report": incident_report,
        "rca": rca,
        "fix_plan": fix_plan,
    }


def normalize_release_decision(raw: Any) -> str:
    """Map model output to APPROVE, BLOCK, or ROLLBACK_REQUIRED (default: BLOCK)."""
    if raw is None:
        return "BLOCK"
    s = str(raw).strip().upper().replace(" ", "_").replace("-", "_")
    if s == "ROLLBACKREQUIRED":
        s = "ROLLBACK_REQUIRED"
    if s in VALID_DECISIONS:
        return s
    if "ROLLBACK" in s and "REQUIRED" in s:
        return "ROLLBACK_REQUIRED"
    if s == "APPROVE" or s == "APPROVED":
        return "APPROVE"
    if s == "BLOCK" or s == "BLOCKED" or s == "DENY" or s == "REJECT":
        return "BLOCK"
    return "BLOCK"


def coerce_str_list(raw: Any) -> list[str]:
    """Normalize a JSON field to a non-empty list of strings (fallback: single placeholder)."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if str(x).strip()]
        return out
    text = str(raw).strip()
    return [text] if text else []
