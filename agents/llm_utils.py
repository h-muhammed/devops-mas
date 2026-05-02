"""Shared helpers for Ollama-backed JSON agents."""

import json
import re
from typing import Any

from langchain_core.messages.base import BaseMessage
from langchain_ollama import ChatOllama


def default_json_llm() -> ChatOllama:
    return ChatOllama(model="phi3", temperature=0, format="json")


def assistant_text(message: BaseMessage) -> str:
    """Flatten LangChain message content (string or content blocks) to plain text."""
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


def parse_llm_json(text: str) -> dict[str, Any]:
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
