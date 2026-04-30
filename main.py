from agents.log_agent import run_log_agent


if __name__ == "__main__":
    result = run_log_agent("data/sample_logs/failed_deployment.log")
    print(result)