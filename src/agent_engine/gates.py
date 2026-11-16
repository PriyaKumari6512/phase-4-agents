"""Human approval gates. A gate (defined in gates.toml) names the project
files a human approves together, e.g. G1 = the scope documents. A decision
is recorded in outputs/<project>/gates/:

- history.jsonl: every decision, one JSON object per line, never rewritten.
- <gate>.approved.json: exists only while the gate is approved, and pins the
  exact version (sha256) of every file it approved.

An agent that must not run before a gate lists `gates/<gate>.approved.json`
as an [input]: the engine's missing-input check then blocks it until the gate
is approved, and `stale_approvals` blocks it again if an approved file has
changed since. Agents can read gates/ but never write it (guardrails.py).
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agent_engine.config import GATES_DIRNAME, GATES_FILE
from agent_engine.history import file_digest

DECISIONS = ("approved", "changes_requested", "rejected")
HISTORY_FILENAME = "history.jsonl"
APPROVED_SUFFIX = ".approved.json"
_GATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
# Same rule as agent.toml's [input] / [output] files: a path inside the project folder.
_FILE_RE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*$")
_GATE_KEYS = {"description", "files"}


@dataclass(frozen=True)
class Gate:
    name: str
    description: str
    files: list[str]

    @property
    def approval_file(self) -> str:
        """Relative to the project folder; what a gated agent lists as an [input]."""
        return f"{GATES_DIRNAME}/{self.name}{APPROVED_SUFFIX}"


def load_gates(path: Path | None = None) -> dict[str, Gate]:
    """Reads and validates gates.toml. No file means no gates."""
    path = path or GATES_FILE
    if not path.is_file():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    gates, problems = {}, []
    for name, table in data.items():
        if not _GATE_NAME_RE.fullmatch(name) or not isinstance(table, dict):
            problems.append(f"[{name}] must be a gate table named like G1 or G3A")
            continue
        problems += [f"unknown key {k!r} in [{name}]" for k in table if k not in _GATE_KEYS]
        files = table.get("files", [])
        if not files:
            problems.append(f"[{name}] needs files = [...], the project files this gate approves")
        problems += [
            f"[{name}] file {f!r} must be a path inside the project folder, like 'scope/scope.md'"
            for f in files if not isinstance(f, str) or not _FILE_RE.fullmatch(f) or ".." in f.split("/")
        ]
        gates[name] = Gate(name=name, description=table.get("description", ""), files=list(files))
    if problems:
        raise ValueError(f"invalid gates file {path}: " + "; ".join(problems))
    return gates


def record_decision(
    project_dir: Path,
    gate: Gate,
    decision: str,
    approver: dict,
    submitted_by: dict,
    comment: str = "",
) -> dict:
    """Appends the decision to gates/history.jsonl and writes (approved) or
    removes (changes requested, rejected) gates/<gate>.approved.json.
    Refuses an approver who also submitted the work (maker-checker).
    """
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {', '.join(DECISIONS)}, got {decision!r}")
    if not approver.get("name") or not submitted_by.get("name"):
        raise ValueError("both the approver and the person who submitted the work must be named")
    if _same_person(approver, submitted_by):
        raise ValueError(f"{approver['name']} submitted this work and can't also approve it (maker-checker)")
    missing = [f for f in gate.files if not (project_dir / f).is_file()]
    if decision == "approved" and missing:
        raise ValueError(f"can't approve {gate.name}: {', '.join(missing)} doesn't exist yet")

    record = {
        "gate": gate.name,
        "project": project_dir.name,
        "decision": decision,
        "approver": approver,
        "submitted_by": submitted_by,
        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comment": comment,
        "artifacts": {f: file_digest(project_dir / f) for f in gate.files if f not in missing},
    }
    gates_dir = project_dir / GATES_DIRNAME
    gates_dir.mkdir(parents=True, exist_ok=True)
    with (gates_dir / HISTORY_FILENAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    approval = project_dir / gate.approval_file
    if decision == "approved":
        approval.write_text(json.dumps(record, indent=2), encoding="utf-8")
    else:
        approval.unlink(missing_ok=True)
    return record


def _same_person(a: dict, b: dict) -> bool:
    if a.get("id") and b.get("id"):
        return a["id"] == b["id"]
    return a["name"].strip().casefold() == b["name"].strip().casefold()


def stale_approvals(project_dir: Path, input_files: list[str]) -> list[str]:
    """For each gates/<gate>.approved.json among `input_files`: the approved
    files that have changed or gone since the approval. Empty = all hold.
    """
    problems = []
    for f in input_files:
        if not (f.startswith(f"{GATES_DIRNAME}/") and f.endswith(APPROVED_SUFFIX) and (project_dir / f).is_file()):
            continue
        record = json.loads((project_dir / f).read_text(encoding="utf-8"))
        for artifact, digest in record.get("artifacts", {}).items():
            path = project_dir / artifact
            if not path.is_file():
                problems.append(f"{record['gate']} approved {artifact}, which no longer exists")
            elif file_digest(path) != digest:
                problems.append(f"{artifact} changed after {record['gate']} was approved on {record['decided_at']}")
    return problems
