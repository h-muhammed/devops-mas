"""Release Agent: final gate — APPROVE, BLOCK, or ROLLBACK_REQUIRED from incident + RCA + fix plan."""

import json
from typing import Any

from agents.llm_utils import assistant_text, default_json_llm, parse_llm_json
from tools.release_tools import (
    build_release_bundle,
    coerce_str_list,
    normalize_release_decision,
)

_llm = default_json_llm()

RELEASE_AGENT_PROMPT = """
You are the Release Gate Agent — the final decision-maker before a change or recovery proceeds.

You receive three structured JSON documents in one bundle:
1) incident_report — from log analysis (severity, summary, patterns, etc.)
2) rca — root cause analysis (root_cause, confidence, reasoning)
3) fix_plan — remediation recommendations only (strategy, risk_level, steps, disclaimers)

Your job:
- Decide ONE release disposition: APPROVE, BLOCK, or ROLLBACK_REQUIRED.
- APPROVE: safe to proceed with the fix plan after normal checks; residual risk acceptable.
- BLOCK: do not proceed — missing verification, contradictory inputs, unacceptable risk,
  or the plan is not safe until human review resolves blockers (not necessarily rollback).
- ROLLBACK_REQUIRED: continuing forward deployment or the proposed fix path is unsafe;
  explicitly require rollback / revert-first posture before any new rollout.

Rules:
- Ground every conclusion in the three inputs; flag contradictions (e.g. CRITICAL severity
  with low-confidence RCA and vague plan → lean BLOCK or ROLLBACK_REQUIRED).
- Never claim production was changed. You only output a disposition and rationale.
- If primary_strategy in fix_plan is "rollback", strongly consider ROLLBACK_REQUIRED or
  APPROVE **only** if the plan clearly describes a controlled rollback path and post-checks,
  else BLOCK until clarified.
- Return ONLY valid JSON with exactly these keys:
  decision, summary, rationale, blockers_or_gates, suggested_actions

Required JSON shape:
{
  "decision": "APPROVE | BLOCK | ROLLBACK_REQUIRED",
  "summary": "one short paragraph",
  "rationale": ["short bullet strings tied to incident / rca / fix_plan"],
  "blockers_or_gates": ["what must pass before releasing; empty if none"],
  "suggested_actions": ["concrete next steps for humans"]
}

rationale must be a non-empty array of short strings.
"""


def _normalize_release_output(data: dict[str, Any]) -> dict[str, Any]:
    decision = normalize_release_decision(data.get("decision"))
    summary = str(data.get("summary", "")).strip()
    if not summary:
        summary = "No summary provided; see rationale."

    rationale = coerce_str_list(data.get("rationale"))
    if not rationale:
        rationale = [
            "Insufficient rationale returned; defaulting to conservative disposition.",
        ]

    blockers = coerce_str_list(data.get("blockers_or_gates"))
    actions = coerce_str_list(data.get("suggested_actions"))
    if not actions:
        actions = [
            "Review incident report, RCA, and fix plan with on-call and release owner.",
        ]

    return {
        "decision": decision,
        "summary": summary,
        "rationale": rationale,
        "blockers_or_gates": blockers,
        "suggested_actions": actions,
    }


def run_release_agent(
    incident_report: dict[str, Any],
    rca: dict[str, Any],
    fix_plan: dict[str, Any],
) -> dict[str, Any]:
    """
    Produce a release disposition from incident report, RCA, and fix plan.

    Returns:
        dict with keys: decision, summary, rationale, blockers_or_gates, suggested_actions.
    """
    bundle = build_release_bundle(incident_report, rca, fix_plan)
    user_content = (
        f"{RELEASE_AGENT_PROMPT.strip()}\n\nRelease bundle (JSON):\n"
        f"{json.dumps(bundle, indent=2, default=str)}"
    )
    response = _llm.invoke(user_content)
    text = assistant_text(response)
    parsed = parse_llm_json(text)
    if not isinstance(parsed, dict):
        raise TypeError("Release agent model output must be a JSON object")
    return _normalize_release_output(parsed)
