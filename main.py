import json
import sys

from agents.fix_agent import run_fix_agent
from agents.log_agent import run_log_agent
from agents.rca_agent import run_rca_agent


def main() -> None:
    log_path = (
        sys.argv[1] if len(sys.argv) > 1 else "data/sample_logs/failed_deployment.log"
    )

    incident = run_log_agent(log_path)
    print("--- Incident report (log agent) ---")
    print(json.dumps(incident, indent=2))

    rca = run_rca_agent(incident)
    print("\n--- Root cause analysis (RCA agent) ---")
    print(json.dumps(rca, indent=2))

    plan = run_fix_agent(
        root_cause=rca["root_cause"],
        incident_report=incident,
        extra_context=json.dumps({"rca": rca}, indent=2),
    )
    print("\n--- Fix plan (fix agent; recommendations only; not applied) ---")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
