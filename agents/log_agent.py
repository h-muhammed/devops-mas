import json
import re
from typing import Any

from langchain_core.messages.base import BaseMessage
from langchain_ollama import ChatOllama
from tools.log_tools import read_log_file


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


LOG_AGENT_PROMPT = """
You are a DevOps Incident Log Analysis Agent.

Your task:
- Analyze application or CI/CD logs
- Detect incidents
- Identify error patterns
- Classify severity as LOW, MEDIUM, HIGH, or CRITICAL
- Return ONLY valid JSON

Do not suggest fixes.
Do not perform root cause analysis.
Do not invent missing information.

Required JSON format:
{
  "incident_detected": true,
  "service": "service name or unknown",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "error_patterns": [],
  "summary": "short summary",
  "evidence": []
}
"""


def run_log_agent(file_path: str) -> dict:
    """
    Runs the Log Analysis Agent on a given log file.

    Args:
        file_path: Path to the log file.

    Returns:
        Structured incident analysis as a dictionary.
    """
    logs = read_log_file(file_path)

    response = llm.invoke(
        f"{LOG_AGENT_PROMPT}\n\nAnalyze these logs:\n{logs}"
    )
    text = _assistant_text(response)
    return _parse_llm_json(text)