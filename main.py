import json
import sys

from agents.fix_agent import run_fix_agent
from agents.log_agent import run_log_agent


def main() -> None:
    log_path = (
        sys.argv[1] if len(sys.argv) > 1 else "data/sample_logs/failed_deployment.log"
    )
    root_cause = (
        sys.argv[2]
        if len(sys.argv) > 2
        else (
            "Suspected misconfiguration or outage matching the incident report; "
            "confirm against infra and recent changes before remediation."
        )
    )

    incident = run_log_agent(log_path)
    print("--- Incident report ---")
    print(json.dumps(incident, indent=2))

    plan = run_fix_agent(root_cause=root_cause, incident_report=incident)
    print("\n--- Fix plan (recommendations only; not applied) ---")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
