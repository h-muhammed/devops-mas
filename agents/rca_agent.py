import json
import re
from typing import Any

from langchain_core.messages.base import BaseMessage
from langchain_ollama import ChatOllama


llm = ChatOllama(model="phi3", temperature=0, format="json")


def _assistant_text(message: BaseMessage) -> str:
    """Flatten LangChain AIMessage content (string or content blocks) to plain text."""
    content: Any = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content)


def _parse_llm_json(text: str) -> dict[str, Any]:
    """Extract and parse JSON from model output (Ollama may wrap or prefix prose)."""
    raw = text.strip()
    if not raw:
        raise ValueError("LLM returned empty content; cannot parse JSON")

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise


RCA_AGENT_SYSTEM_PROMPT = """
You are a senior DevOps engineer performing Root Cause Analysis (RCA).

You receive ONLY a structured incident report as JSON (from a prior log analysis step).
You MUST NOT assume access to raw logs, servers, or tools. Every factual claim in your
reasoning must be traceable to the provided fields: incident_detected, service, severity,
error_patterns, and summary.

Rules:
- Infer the most plausible root cause from patterns and summary; label speculation clearly
  when the structured data is ambiguous.
- If incident_detected is false, state that no active incident was indicated, set confidence
  low, and keep reasoning tied to that fact.
- Do not propose remediation steps or commands (a separate agent handles fixes).
- Return ONLY valid JSON with exactly these keys: root_cause, affected_service, confidence, reasoning.

Required JSON shape:
{
  "root_cause": "concise explanation of the most likely cause",
  "affected_service": "service name from the report or unknown",
  "confidence": 0.0,
  "reasoning": [
    "Evidence: ... (grounded in provided fields)",
    "Inference: ... (explicit if interpretive)"
  ]
}

confidence must be a number from 0.0 to 1.0 reflecting how well the structured evidence supports the conclusion.
reasoning must be a non-empty array of short strings (bullet-style).
"""


def _incident_payload(log_agent_output: dict[str, Any]) -> dict[str, Any]:
    """Select only the fields the RCA agent is allowed to reason over."""
    return {
        "incident_detected": log_agent_output.get("incident_detected"),
        "service": log_agent_output.get("service"),
        "severity": log_agent_output.get("severity"),
        "error_patterns": log_agent_output.get("error_patterns"),
        "summary": log_agent_output.get("summary"),
    }


def _normalize_rca_output(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure pipeline-safe JSON matching the contract."""
    reasoning_raw = data.get("reasoning", [])
    if isinstance(reasoning_raw, str):
        reasoning: list[str] = [reasoning_raw] if reasoning_raw.strip() else []
    elif isinstance(reasoning_raw, list):
        reasoning = [str(x).strip() for x in reasoning_raw if str(x).strip()]
    else:
        reasoning = [str(reasoning_raw).strip()] if reasoning_raw is not None else []

    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    root_cause = str(data.get("root_cause", "")).strip()
    if not root_cause:
        root_cause = "Unable to determine root cause from the structured incident data."

    affected = str(data.get("affected_service", "")).strip()
    if not affected:
        affected = "unknown"

    if not reasoning:
        reasoning = [
            "No discrete reasoning steps were returned; conclusion is based on the aggregated incident summary only.",
        ]

    return {
        "root_cause": root_cause,
        "affected_service": affected,
        "confidence": conf,
        "reasoning": reasoning,
    }


def run_rca_agent(log_agent_output: dict[str, Any]) -> dict[str, Any]:
    """
    Run Root Cause Analysis on structured output from the Log Analysis Agent.

    Args:
        log_agent_output: Dictionary containing at least incident_detected, service, severity,
            error_patterns, and summary (as produced by run_log_agent).

    Returns:
        Structured RCA result: root_cause, affected_service, confidence, reasoning.
    """
    if not isinstance(log_agent_output, dict):
        raise TypeError("log_agent_output must be a dict")

    payload = _incident_payload(log_agent_output)
    user_content = (
        f"{RCA_AGENT_SYSTEM_PROMPT}\n\nStructured incident report (JSON):\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )

    response = llm.invoke(user_content)
    text = _assistant_text(response)
    parsed = _parse_llm_json(text)
    return _normalize_rca_output(parsed)
