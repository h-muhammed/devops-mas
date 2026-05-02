from pathlib import Path


def read_log_file(file_path: str) -> str:
    """
    Reads a local log file and returns its content.

    Args:
        file_path: Path to the log file.

    Returns:
        Log file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        return "[no output captured in log file]\n"

    return content
