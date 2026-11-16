"""Two global log files kept deliberately separate: app.log (this package's
own code) and deepagent.log (the agent's step-by-step transcript plus every
propagating framework logger).

Each job additionally gets its own log, starting in LOGS_DIR/jobs/ and
relocating in real time into outputs/<project>/logs/ once the project
directory is known (notify_job_log_path, called from
guardrails.OutputsOnlyGuardMiddleware) — so a mid-run crash still leaves the
log inside the project, not stranded in the scratch folder. It mirrors
deepagent.log ONLY: the job handler attaches to the root logger plus
TRANSCRIPT_LOGGER_NAME directly (which sets propagate=False, so root alone
wouldn't see it) — never to APP_LOGGER_NAME, so this package's own log lines
stay out of the per-project file.

Call configure_logging() once, at CLI startup, before building the agent.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from pathlib import Path

from agent_engine.config import (
    APP_LOG_FILENAME,
    APP_LOG_FORMAT,
    APP_LOGGER_NAME,
    DEEPAGENT_LOG_FILENAME,
    DEFAULT_LOG_LEVEL,
    JOB_ID_RANDOM_SUFFIX_LENGTH,
    JOB_ID_TIME_FORMAT,
    JOB_LOGS_SUBDIR_NAME,
    LOG_FORMAT,
    LOGS_DIR,
    OUTPUTS_DIR,
    OUTPUTS_VIRTUAL_PREFIX,
    PROJECT_LOGS_SUBDIR_NAME,
    TRANSCRIPT_LOGGER_NAME,
)

logger = logging.getLogger(__name__)

_LOG_FORMAT = logging.Formatter(LOG_FORMAT)

# app.log is global and shared across jobs, so each record is stamped with
# the job id active when it was logged.
_APP_LOG_FORMAT = logging.Formatter(APP_LOG_FORMAT)

_PROJECT_PATH_RE = re.compile(rf"^{re.escape(OUTPUTS_VIRTUAL_PREFIX)}([A-Za-z0-9._-]+)/")


class _JobIdFilter(logging.Filter):
    """Stamps every app.log record with the active job's id, or "-" if none."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = _active_job.job_id if _active_job is not None else "-"
        return True


def configure_logging(level: int = DEFAULT_LOG_LEVEL) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    app_handler = logging.FileHandler(LOGS_DIR / APP_LOG_FILENAME, encoding="utf-8")
    app_handler.setFormatter(_APP_LOG_FORMAT)
    app_handler.addFilter(_JobIdFilter())
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.setLevel(level)
    app_logger.addHandler(app_handler)
    app_logger.propagate = False

    deepagent_handler = logging.FileHandler(LOGS_DIR / DEEPAGENT_LOG_FILENAME, encoding="utf-8")
    deepagent_handler.setFormatter(_LOG_FORMAT)

    transcript_logger = logging.getLogger(TRANSCRIPT_LOGGER_NAME)
    transcript_logger.setLevel(level)
    transcript_logger.addHandler(deepagent_handler)
    transcript_logger.propagate = False

    # Everything else falls through to the root logger -> deepagent.log.
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(deepagent_handler)


def new_job_id() -> str:
    """Timestamp-prefixed so job logs sort chronologically on disk."""
    return f"{time.strftime(JOB_ID_TIME_FORMAT)}-{uuid.uuid4().hex[:JOB_ID_RANDOM_SUFFIX_LENGTH]}"


class _ActiveJob:
    """State for the one job this process runs. `lock` guards relocation
    against two concurrent tool calls discovering the project path at once.
    """

    __slots__ = ("job_id", "handler", "path", "project_dir", "relocated", "lock")

    def __init__(self, job_id: str, handler: logging.Handler, path: Path) -> None:
        self.job_id = job_id
        self.handler = handler
        self.path = path
        self.project_dir: Path | None = None
        self.relocated = False
        self.lock = threading.Lock()


_active_job: _ActiveJob | None = None


def attach_job_log_handler(job_id: str) -> None:
    """Starts this job's log staged under LOGS_DIR/jobs/ until
    notify_job_log_path relocates it into the project's own logs/ folder.
    """
    global _active_job
    jobs_dir = LOGS_DIR / JOB_LOGS_SUBDIR_NAME
    jobs_dir.mkdir(parents=True, exist_ok=True)
    staging_path = jobs_dir / f"{job_id}.log"

    handler = logging.FileHandler(staging_path, encoding="utf-8")
    handler.setFormatter(_LOG_FORMAT)
    logging.getLogger().addHandler(handler)
    # deepagent.transcript has propagate=False, so it needs the handler
    # attached directly too, or the transcript would never reach this file.
    # APP_LOGGER_NAME is deliberately never attached here (see module docstring).
    logging.getLogger(TRANSCRIPT_LOGGER_NAME).addHandler(handler)

    _active_job = _ActiveJob(job_id, handler, staging_path)


def current_job_log_path() -> Path | None:
    """The staging path, or the relocated project path once known. None if
    no job is active.
    """
    return _active_job.path if _active_job is not None else None


def current_project_dir() -> Path | None:
    """The active job's project directory once discovered, else None."""
    return _active_job.project_dir if _active_job is not None else None


def detach_job_log_handler() -> None:
    global _active_job
    if _active_job is None:
        return
    logging.getLogger().removeHandler(_active_job.handler)
    logging.getLogger(TRANSCRIPT_LOGGER_NAME).removeHandler(_active_job.handler)
    _active_job.handler.close()
    _active_job = None


def notify_job_log_path(file_path: str) -> None:
    """Relocates the active job's log to its project's logs/ folder on the
    first call whose path names one; a no-op after that.

    Called from OutputsOnlyGuardMiddleware on every mutating filesystem call,
    on a graph with no handle_tool_errors (guardrails.py) -- an unguarded
    OSError here would crash the run. The new handler/file are prepared
    before the old one is touched, so a failure leaves logging on the old
    path instead of crashing or losing it.
    """
    job = _active_job
    if job is None or job.relocated:
        return
    match = _PROJECT_PATH_RE.match(file_path.strip().replace("\\", "/"))
    if not match:
        return

    with job.lock:
        if job.relocated:
            return

        old_handler = job.handler
        old_path = job.path

        try:
            project_logs_dir = OUTPUTS_DIR / match.group(1) / PROJECT_LOGS_SUBDIR_NAME
            project_logs_dir.mkdir(parents=True, exist_ok=True)
            new_path = project_logs_dir / f"{job.job_id}.log"

            old_content: str | None = None
            if old_path.exists():
                with old_path.open("r", encoding="utf-8") as src:
                    old_content = src.read()

            new_handler = logging.FileHandler(new_path, encoding="utf-8")
            new_handler.setFormatter(_LOG_FORMAT)
        except OSError:
            logger.exception(
                "job %s log relocation to %s failed; keeping log at %s", job.job_id, match.group(1), old_path
            )
            # Mark relocated so a non-transient failure isn't retried every call.
            job.relocated = True
            return

        # Only detach the old handler once the new one is confirmed usable.
        logging.getLogger().removeHandler(old_handler)
        logging.getLogger(TRANSCRIPT_LOGGER_NAME).removeHandler(old_handler)
        old_handler.close()

        if old_content is not None:
            # Append rather than move-and-clobber, in case new_path already
            # exists (e.g. a job_id collision, or a re-run reusing one).
            try:
                with new_path.open("a", encoding="utf-8") as dst:
                    dst.write(old_content)
                old_path.unlink()
            except OSError:
                logger.exception(
                    "job %s log relocated to %s but could not copy/remove old file %s",
                    job.job_id, new_path, old_path,
                )

        logging.getLogger().addHandler(new_handler)
        logging.getLogger(TRANSCRIPT_LOGGER_NAME).addHandler(new_handler)

        job.handler = new_handler
        job.path = new_path
        job.project_dir = OUTPUTS_DIR / match.group(1)
        job.relocated = True
        logger.info("job %s log relocated to %s", job.job_id, new_path)
