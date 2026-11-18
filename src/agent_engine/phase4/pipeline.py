"""One ENV-configured entry point for generation, review, gates and publication."""
from __future__ import annotations

import os

from agent_engine import config, perf
from agent_engine.phase4 import files, orchestrator
from agent_engine.phase4.contracts import ProjectSettings, TrackerKind
from agent_engine.phase4.settings import get_pipeline_settings, get_settings, get_jira_options
from agent_engine.phase4.trackers.base import TrackerError


def configure_environment() -> None:
    """Apply defaults before diagnostics initializes and child processes spawn.

    Existing commands retain their defaults. Explicit ENV choices take precedence.
    """
    settings = get_pipeline_settings()
    os.environ.setdefault("AGENT_ENGINE_PERF", "1" if settings.diagnostics else "0")
    os.environ.setdefault("AGENT_ENGINE_PERF_MODE", "publication")
    os.environ.setdefault("PHASE4_IAC_CHECK_CONCURRENCY", str(settings.scanner_concurrency))


def run(out=print) -> int:
    try:
        options = get_pipeline_settings()
        if not options.project:
            raise ValueError("Set PHASE4_PROJECT_NAME in .env to your existing outputs/<project> folder name")
        root = files.project_dir(options.project)
        for rel in (files.PROJECT_SETTINGS, files.PRD, files.ARCHITECTURE):
            if not files.exists(options.project, rel):
                raise ValueError(f"Required input is missing: {root / rel}")
        settings = files.read_json(options.project, files.PROJECT_SETTINGS, ProjectSettings)
        integrations = get_settings()
        if options.publish:
            if blocked := perf.publication_blocked():
                raise ValueError(blocked + "; set AGENT_ENGINE_PERF_MODE=publication in .env")
            if integrations.phase4_pr_mode == "github" and not integrations.github_token:
                raise ValueError("PHASE4_PR_MODE=github requires GITHUB_TOKEN")
            if (settings.tracker.kind == TrackerKind.LOCAL and integrations.jira_email and integrations.jira_api_token
                    and os.environ.get("PHASE4_TRACKER", "").strip() != "local"):
                raise ValueError("Jira credentials are present but the destination is local; set PHASE4_TRACKER=jira "
                                 "and JIRA_BASE_URL/JIRA_PROJECT_KEY/JIRA_BOARD_ID, or explicitly PHASE4_TRACKER=local")
        config.resolve_model_tiers()  # Fail before any generation if model configuration is absent.
        if options.publish and settings.tracker.kind == TrackerKind.JIRA:
            get_jira_options()  # Validate limits and optional field mappings before connecting.
            from agent_engine.phase4.trackers.jira import JiraTracker
            tracker = JiraTracker(settings.tracker)
            try:
                out("Jira preflight: " + str(tracker.preflight({member.member_id: member.tracker_account_id for member in settings.team})))
            finally:
                tracker.close()
        if options.auto_approve_for_testing:
            out("TEST MODE: successful automated reviews authorize gates/publication; these are not human sign-offs.")
        return orchestrator.orchestrate(
            options.project, sprint=options.sprint, test_approve=options.auto_approve_for_testing,
            publish=options.publish, parallel_independent=options.parallel,
            verified_test_approval=options.auto_approve_for_testing, out=out, resume=options.resume,
        )
    except (ValueError, OSError, TrackerError, RuntimeError) as exc:
        out(f"ERROR: {exc}")
        out("Completed stage outputs and acknowledged publishing IDs are retained. Fix the cause and run the same command again.")
        return orchestrator.FAILED
