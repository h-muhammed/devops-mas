from typing import Any

from agents.llm_utils import assistant_text, default_json_llm, parse_llm_json
from tools.log_tools import read_log_file


llm = default_json_llm()


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


def run_log_agent(file_path: str) -> dict[str, Any]:
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
    text = assistant_text(response)
    return parse_llm_json(text)
