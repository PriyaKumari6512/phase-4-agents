"""`agent-engine phase4 ...` commands (no model calls):

  init           copy an example project's inputs (prd.md, architecture.md, phase4/*.json) into outputs/<project>/
  import-stories read the approved stories (phase4/stories.json) and closed sprints (phase4/history.json) from Jira, read-only
  publish        push a gate-approved file to the tracker / GitHub (backlog, sprint, assignments, infra)
  mine-profiles  skill and code-ownership evidence from a git clone -> phase4/skill-profiles.json
  schemas        write the JSON Schemas of every Phase 4 file contract
  orchestrate    run the four agents when they are needed, stop at human gates (see orchestrator.py)
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from agent_engine import config
from agent_engine.phase4 import contracts, files

EXAMPLES_DIR = config.ASSETS_ROOT / "examples" / "phase4"
SCHEMAS = {
    "project.schema.json": contracts.ProjectSettings, "history.schema.json": contracts.History,
    "stories.schema.json": contracts.StorySnapshot,
    "backlog.schema.json": contracts.Backlog,
    "sprint-plan.schema.json": contracts.SprintPlan, "assignments.schema.json": contracts.AssignmentPlan,
    "infra-intent.schema.json": contracts.InfraIntent, "infra-manifest.schema.json": contracts.InfraManifest,
}


def add_parser(sub) -> None:
    p4 = sub.add_parser("phase4", help="Phase 4 helpers: init an example, publish after a gate, mine profiles, schemas.")
    s = p4.add_subparsers(dest="phase4_command", required=True)
    i = s.add_parser("init", help="Copy an example project's inputs into outputs/<project>/.")
    i.add_argument("--project-name", required=True)
    i.add_argument("--example", default="taskflow", help=f"Folder under {EXAMPLES_DIR}.")
    i.add_argument("--force", action="store_true", help="Overwrite files that already exist.")
    st = s.add_parser("import-stories", help="Read approved stories from Jira (read-only) into phase4/stories.json.")
    st.add_argument("--project-name", required=True)
    p = s.add_parser("publish", help="Publish a gate-approved file (refuses unless its gate is approved).")
    p.add_argument("what", choices=["backlog", "sprint", "assignments", "infra"])
    p.add_argument("--project-name", required=True)
    m = s.add_parser("mine-profiles", help="Mine a git clone for skill and code-ownership evidence.")
    m.add_argument("--project-name", required=True)
    m.add_argument("--repo", required=True, help="Path to a local clone.")
    m.add_argument("--name", required=True, help="Repository name, e.g. acme/taskflow-api.")
    m.add_argument("--months", type=int, default=12)
    o = s.add_parser("orchestrate", help="Run the agents that are needed, in order, and stop at the human gates.")
    o.add_argument("--project-name", required=True)
    o.add_argument("--sprint", type=int, default=1, help="Sprint Work Allocation assigns (default 1).")
    o.add_argument("--plan", action="store_true", help="Only show what would run; no model calls.")
    o.add_argument("--parallel-independent", action="store_true",
                   help="Overlap Task Breakdown and Infra in isolated workspaces when both need to run.")
    o.add_argument("--test-approve", action="store_true",
                   help="TEST ONLY: approve the gates itself (recorded as an automated test approval, not a human sign-off).")
    o.add_argument("--publish", action="store_true", help="When everything is approved, run phase4 publish for all four.")
    recover = s.add_parser("recover-parallel", help="Merge retained child results without rerunning writers.")
    recover.add_argument("--project-name", required=True)
    recover.add_argument("--session", required=True, help="Retained directory under the configured logs/parallel.")
    recover.add_argument("--sprint", type=int, default=1)
    sc = s.add_parser("schemas", help="Write JSON Schemas of the Phase 4 files.")
    sc.add_argument("--out", default="schemas")
    for name in ("check-ci", "reconcile"):
        command = s.add_parser(name, help="Refresh read-only operational CI / coding-agent outcome evidence.")
        command.add_argument("--project-name", required=True)


def run(args: argparse.Namespace) -> int:
    try:
        if args.phase4_command == "recover-parallel":
            from agent_engine.phase4.parallel_stages import recover_session, acknowledge
            from agent_engine.phase4.orchestrator import record_parallel_results
            from agent_engine.runtime import project_lock
            root = files.project_dir(args.project_name)
            with project_lock(root, "orchestrator"), project_lock(root):
                result = recover_session(root, Path(args.session))
                record_parallel_results(root, result, args.sprint)
                acknowledge(root)
            print(json.dumps(result, indent=2))
            return 0  # recovery succeeded; partial stage results still need review
        if args.phase4_command in ("check-ci", "reconcile"):
            from agent_engine.phase4 import readiness
            from agent_engine.runtime import project_lock
            with project_lock(files.project_dir(args.project_name)):
                fn = readiness.check_ci if args.phase4_command == "check-ci" else readiness.reconcile
                print(json.dumps(fn(args.project_name), indent=2))
            return 0
        if args.phase4_command == "init":
            return _init(args.project_name, args.example, args.force)
        if args.phase4_command == "import-stories":
            from agent_engine.phase4.story_import import import_history, import_stories
            from agent_engine.runtime import project_lock
            with project_lock(files.project_dir(args.project_name)):
                print(json.dumps({**import_stories(args.project_name),
                                  "velocity": import_history(args.project_name)}, indent=2))
            return 0
        if args.phase4_command == "publish":
            from agent_engine import perf
            from agent_engine.phase4.publish import PUBLISHERS

            blocked = perf.publication_blocked()
            if blocked:
                print(f"ERROR: {blocked}")
                return 1
            with perf.span("publish", args.what, project=args.project_name):
                print(json.dumps(PUBLISHERS[args.what](args.project_name), indent=2, default=str))
            return 0
        if args.phase4_command == "mine-profiles":
            from agent_engine.phase4.profiles import mine_repo
            print(json.dumps(mine_repo(args.project_name, Path(args.repo), args.name, args.months), indent=2))
            return 0
        if args.phase4_command == "orchestrate":
            from agent_engine.phase4.orchestrator import orchestrate
            return orchestrate(args.project_name, args.sprint, args.test_approve, args.publish, args.plan,
                               parallel_independent=getattr(args, "parallel_independent", False))
        if args.phase4_command == "schemas":
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            for name, model in SCHEMAS.items():
                (out / name).write_text(json.dumps(model.model_json_schema(), indent=2), encoding="utf-8")
            print(f"wrote {len(SCHEMAS)} schemas to {out}")
            return 0
    except Exception as e:  # noqa: BLE001  (CLI: report, don't trace)
        print(f"ERROR: {e}")
        return 1
    return 1


def _init(project: str, example: str, force: bool) -> int:
    if not files.PROJECT_RE.fullmatch(project):
        print(f"ERROR: invalid --project-name {project!r} (use a-z, 0-9 and -)")
        return 1
    src = EXAMPLES_DIR / example
    if not src.is_dir():
        print(f"ERROR: no example {example!r} in {EXAMPLES_DIR} (have: {', '.join(p.name for p in EXAMPLES_DIR.iterdir())})")
        return 1
    dst = Path(config.OUTPUTS_DIR) / project
    copied, kept = [], []
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = f.relative_to(src)
        target = dst / rel
        if target.exists() and not force:
            kept.append(rel.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, target)
        copied.append(rel.as_posix())
    print(f"Project folder: {dst}")
    for c in copied:
        print(f"  copied  {c}")
    for k in kept:
        print(f"  kept    {k} (exists; --force to overwrite)")
    return 0
