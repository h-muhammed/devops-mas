"""Fix Agent: proposes safe remediation plans only (no production changes)."""

import json
from typing import Any

from agents.llm_utils import assistant_text, default_json_llm, parse_llm_json

_llm = default_json_llm()

FIX_AGENT_PROMPT = """
You are a DevOps Fix Planning Agent.

Inputs you receive:
- A stated root cause (may be provisional)
- An incident report (structured JSON or plain summary)

Your task:
1. Choose ONE primary remediation strategy: "rollback", "config_fix", or "patch".
   - rollback: revert deployment, release, or infra change
   - config_fix: environment variables, feature flags, quotas, secrets rotation plan,
     connectivity (DNS/firewall/URLs), resource limits — without code changes
   - patch: application or dependency code/config-as-code change requiring a build or PR
2. Explain briefly why that strategy fits versus the alternatives.
3. Produce a step-by-step remediation plan that is SAFE FOR REVIEW: nothing runs automatically.

Hard constraints:
- You MUST NOT instruct anyone to execute destructive or irreversible actions without
  explicit human approval steps called out in the plan.
- Every shell/command line must be framed as a RECOMMENDATION to review and run manually
  (or in staging first). Prefer dry-run flags where they exist (e.g. terraform plan,
  kubectl apply --dry-run=client, helm template).
- Do not claim production was changed. Output is advisory only.
- If information is missing, say what to verify before acting; do not invent facts.

Return ONLY valid JSON matching this shape:
{
  "primary_strategy": "rollback | config_fix | patch",
  "strategy_rationale": "string",
  "alternatives_considered": ["string"],
  "risk_level": "LOW | MEDIUM | HIGH",
  "requires_change_freeze_or_approval": true,
  "pre_execution_checks": [
    { "check": "string", "how_to_verify": "string" }
  ],
  "remediation_steps": [
    {
      "step": 1,
      "phase": "prepare | execute | validate | communicate",
      "action": "short title",
      "details": "what to do and why",
      "recommended_commands": [
        {
          "intent": "what this checks or previews",
          "command": "example command with safe flags where applicable",
          "notes": "staging first / read-only / requires approval"
        }
      ],
      "success_criteria": "string"
    }
  ],
  "rollback_plan_if_fix_fails": ["string"],
  "documentation_snippets": ["each entry plain text: link or doc title/section only"],
  "disclaimer": "string stating output is recommendations only and must be validated"
}
"""


def run_fix_agent(
    root_cause: str,
    incident_report: dict[str, Any] | str,
    *,
    extra_context: str | None = None,
) -> dict[str, Any]:
    """
    Produce a remediation plan from root cause + incident report.

    Does not touch production; returns structured recommendations only.

    Args:
        root_cause: Known or suspected root cause text.
        incident_report: Incident payload (dict will be serialized as JSON).
        extra_context: Optional constraints (e.g. cluster name, policy notes).

    Returns:
        Parsed remediation plan dict from the model.
    """
    if isinstance(incident_report, dict):
        report_blob = json.dumps(incident_report, indent=2)
    else:
        report_blob = str(incident_report)

    parts = [
        FIX_AGENT_PROMPT.strip(),
        "",
        "---",
        "ROOT_CAUSE:",
        root_cause.strip(),
        "",
        "INCIDENT_REPORT:",
        report_blob,
    ]
    if extra_context:
        parts.extend(["", "ADDITIONAL_CONTEXT:", extra_context.strip()])

    response = _llm.invoke("\n".join(parts))
    text = assistant_text(response)
    return parse_llm_json(text)
