"""Minimal Markdown -> Atlassian Document Format converter.

Supports headings, paragraphs, bullet/numbered lists, fenced code, inline code, bold and links.
Anything else becomes a plain paragraph.
"""
from __future__ import annotations

import re

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_TOKEN = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def _inline(text: str) -> list[dict]:
    nodes: list[dict] = []
    for part in _TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            nodes.append({"type": "text", "text": part[2:-2], "marks": [{"type": "strong"}]})
        elif part.startswith("`") and part.endswith("`"):
            nodes.append({"type": "text", "text": part[1:-1], "marks": [{"type": "code"}]})
        elif m := _LINK.fullmatch(part):
            nodes.append({"type": "text", "text": m.group(1), "marks": [{"type": "link", "attrs": {"href": m.group(2)}}]})
        else:
            nodes.append({"type": "text", "text": part})
    return nodes or [{"type": "text", "text": " "}]


def markdown_to_adf(md: str) -> dict:
    content: list[dict] = []
    lines = (md or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            content.append({"type": "codeBlock", "content": [{"type": "text", "text": "\n".join(buf) or " "}]})
            i += 1
            continue
        if m := re.match(r"^(#{1,6})\s+(.*)$", line):
            content.append({"type": "heading", "attrs": {"level": len(m.group(1))}, "content": _inline(m.group(2))})
            i += 1
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.", line))
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                text = re.sub(r"^\s*([-*]|\d+\.)\s+(\[[ xX]\]\s+)?", "", lines[i])
                items.append({"type": "listItem", "content": [{"type": "paragraph", "content": _inline(text)}]})
                i += 1
            content.append({"type": "orderedList" if ordered else "bulletList", "content": items})
            continue
        if line.strip():
            content.append({"type": "paragraph", "content": _inline(line.strip())})
        i += 1
    return {"type": "doc", "version": 1, "content": content or [{"type": "paragraph", "content": [{"type": "text", "text": " "}]}]}


def adf_to_text(adf: dict | None) -> str:
    """Flatten ADF to text (used to compare current values for human-edit detection)."""
    if not adf:
        return ""
    out: list[str] = []

    def walk(node: dict) -> None:
        if node.get("type") == "text":
            out.append(node.get("text", ""))
        for child in node.get("content", []) or []:
            walk(child)
        if node.get("type") in ("paragraph", "heading", "listItem", "codeBlock"):
            out.append("\n")

    walk(adf)
    return "".join(out).strip()
