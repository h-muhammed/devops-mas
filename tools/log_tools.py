from pathlib import Path


def read_log_file(file_path: str) -> str:
    """
    Reads a local log file and returns its content.

    Args:
        file_path: Path to the log file.

    Returns:
        Log file content as a string.

    Raises:
        FileNotFoundError: If the log file does not exist.
        ValueError: If the file is empty.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError("Log file is empty")

    return content
