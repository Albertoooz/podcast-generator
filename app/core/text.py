import re
from typing import Any

THINK_PATTERN = re.compile(r"<redacted_thinking>(.*?)</redacted_thinking>", re.DOTALL)


def parse_thinking_content(content: str) -> tuple[str, str]:
    if not isinstance(content, str):
        return "", str(content) if content is not None else ""
    if len(content) > 100000:
        return "", content
    thinking_matches = THINK_PATTERN.findall(content)
    if thinking_matches:
        thinking_content = "\n\n".join(m.strip() for m in thinking_matches)
        cleaned = THINK_PATTERN.sub("", content)
    else:
        thinking_content = ""
        cleaned = content
    cleaned = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned).strip()
    return thinking_content, cleaned


def clean_thinking_content(content: str) -> str:
    _, cleaned = parse_thinking_content(content)
    return cleaned


def extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    if content is None:
        return ""
    return str(content)
