"""Skill taxonomy: Agents 1 and 3 may only use the tags in data/skills.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

TAXONOMY_FILE = Path(__file__).resolve().parent / "data" / "skills.yaml"


@lru_cache
def taxonomy() -> dict[str, dict]:
    return yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))["skills"]


def tags() -> list[str]:
    return sorted(taxonomy())


def normalize(tag: str) -> str | None:
    """Map a free-form skill word to a taxonomy tag (exact tag, then alias match)."""
    t = tag.strip().lower()
    tax = taxonomy()
    if t in tax:
        return t
    for name, spec in tax.items():
        if t in [a.lower() for a in spec.get("aliases", [])]:
            return name
    for name, spec in tax.items():
        if any(a.lower() in t for a in spec.get("aliases", []) if len(a) > 3):
            return name
    return None


def from_text(text: str, limit: int = 4) -> list[str]:
    """Heuristic tags for a piece of text (used by mocks and as a fallback)."""
    low = f" {text.lower()} "
    hits: list[tuple[int, str]] = []
    for name, spec in taxonomy().items():
        score = sum(low.count(f" {a.lower()}") for a in spec.get("aliases", []))
        score += sum(2 for p in spec.get("paths", []) if p and p.lower() in low)
        if score:
            hits.append((score, name))
    return [n for _, n in sorted(hits, key=lambda x: (-x[0], x[1]))[:limit]]


def from_path(path: str) -> list[str]:
    p = path.lower()
    return [name for name, spec in taxonomy().items() if any(frag and frag.lower() in p for frag in spec.get("paths", []))]
