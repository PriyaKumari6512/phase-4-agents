"""Langfuse tracing setup, shared by every agent invocation this package
makes — one place to build the callback handler and flush it.
"""

from __future__ import annotations

import logging
import os

from agent_engine.config import LANGFUSE_HOST_DEFAULT

logger = logging.getLogger(__name__)


def build_langfuse_handler() -> object | None:
    """None if Langfuse isn't configured or reachable — tracing is a
    nice-to-have, never a reason to fail the run.
    """
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        logger.info("LANGFUSE_PUBLIC_KEY not set; running without Langfuse tracing")
        return None
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception:
        logger.exception("failed to initialize Langfuse; running without tracing")
        return None


def flush_langfuse(handler: object | None) -> str | None:
    """Flushes the client so traces are sent before the process/step moves
    on, and returns the host they were sent to (for callers that want to
    surface it), or None if `handler` is None (tracing wasn't configured).
    """
    if handler is None:
        return None
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception:
        logger.exception("failed to flush Langfuse client")
    return os.environ.get("LANGFUSE_HOST", LANGFUSE_HOST_DEFAULT)


__all__ = ["build_langfuse_handler", "flush_langfuse"]
