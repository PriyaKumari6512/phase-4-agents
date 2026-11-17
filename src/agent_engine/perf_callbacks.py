"""LangChain callbacks and httpx transport hooks that turn one agent pass into diagnostic spans.

* ``PerfCallbackHandler``: one span per logical model call (``on_chat_model_start`` .. ``on_llm_end``), per
  tool call, and per helper (the deepagents ``task`` tool). Parentage follows LangChain's own run tree
  (``parent_run_id``), so model and tool calls made inside a helper land under that helper's span even when
  several helpers run at once. ``run_inline = True``: the handler runs in the caller's task/thread, which is
  what lets ``on_tool_start`` hand its span to the tool body (a synchronous tool runs in a worker thread
  started with a copy of that context) and lets the transport hook see which model call an HTTP attempt
  belongs to.
* ``install_transport_hooks``: httpx event hooks on a chat model's own SDK clients. The provider SDKs retry
  inside one ``ainvoke`` (``max_retries``) without telling LangChain; each HTTP attempt shows up here, with
  the SDK's ``x-stainless-retry-count`` header when it sends one.

Usage is read from each call's own ``usage_metadata`` exactly once per run id; a field the provider did not
report is recorded as null, never as 0.
"""

from __future__ import annotations

import threading
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from agent_engine import perf

_SAFE_INVOCATION_KEYS = ("temperature", "max_tokens", "max_output_tokens", "effort", "reasoning", "reasoning_effort",
                         "thinking", "stream", "streaming", "max_retries", "timeout", "verbosity", "_type")
HELPER_TOOL = "task"


def _small(value: Any) -> Any:
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:120]


def _content_text(output: Any) -> str | None:
    """Text of a tool result (ToolMessage, Command with messages, or plain string), for size and ERROR checks."""
    content = getattr(output, "content", None)
    if content is None and hasattr(output, "update"):
        update = getattr(output, "update", None) or {}
        msgs = update.get("messages") if isinstance(update, dict) else None
        if msgs:
            content = getattr(msgs[-1], "content", None)
    if content is None and isinstance(output, str):
        content = output
    if isinstance(content, list):
        content = "".join(b if isinstance(b, str) else str(b.get("text", "")) for b in content
                          if isinstance(b, (str, dict)))
    return content if isinstance(content, str) else None


def _usage(response: Any) -> tuple[dict, dict]:
    """(usage, response facts) from an LLMResult: provider-reported token fields only."""
    usage: dict = {}
    facts: dict = {}
    for gen_list in getattr(response, "generations", None) or []:
        for gen in gen_list or []:
            msg = getattr(gen, "message", None)
            meta = getattr(msg, "usage_metadata", None) if msg is not None else None
            if meta:
                usage = dict(meta)
            rmeta = getattr(msg, "response_metadata", None) or {}
            info = getattr(gen, "generation_info", None) or {}
            reason = rmeta.get("stop_reason") or rmeta.get("finish_reason") or info.get("finish_reason")
            if reason:
                facts["finish_reason"] = _small(reason)
            model = rmeta.get("model_name") or rmeta.get("model")
            if model:
                facts["response_model"] = _small(model)
    out = {"usage_reported": bool(usage)}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        out[key] = usage.get(key) if usage else None
    in_details = (usage.get("input_token_details") or {}) if usage else {}
    out_details = (usage.get("output_token_details") or {}) if usage else {}
    out["cache_read_tokens"] = in_details.get("cache_read")
    out["cache_creation_tokens"] = in_details.get("cache_creation")
    out["reasoning_tokens"] = out_details.get("reasoning")
    return out, facts


class PerfCallbackHandler(BaseCallbackHandler):
    run_inline = True
    raise_error = False

    def __init__(self, pass_span_id: str | None, tiers: dict[str, str] | None = None) -> None:
        self.pass_span_id = pass_span_id
        self.tiers = tiers or {}
        self._lock = threading.Lock()
        # run_id -> {"parent": run_id|None, "kind": chain|model|tool|helper, "span": Span|None, ...}
        self._runs: dict[UUID, dict] = {}

    # ------------------------------------------------------------------ tree
    def _ancestor_span(self, parent_run_id: UUID | None) -> tuple[str | None, str | None, str | None]:
        """(nearest ancestor span id, enclosing helper span id, helper type) walking up LangChain's run tree."""
        nearest = helper = helper_type = None
        run = parent_run_id
        for _ in range(500):
            if run is None:
                break
            rec = self._runs.get(run)
            if rec is None:
                break
            sp = rec.get("span")
            if sp is not None and nearest is None:
                nearest = sp.id
            if rec["kind"] == "helper" and helper is None:
                helper, helper_type = sp.id if sp is not None else None, rec.get("helper_type")
                break
            run = rec["parent"]
        return nearest or helper or self.pass_span_id, helper, helper_type

    def on_chain_start(self, serialized: dict | None, inputs: Any, *, run_id: UUID, parent_run_id: UUID | None = None,
                       **kwargs: Any) -> None:
        with self._lock:
            self._runs.setdefault(run_id, {"parent": parent_run_id, "kind": "chain", "span": None})

    def _drop_chain(self, run_id: UUID) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if rec is not None and rec["kind"] == "chain":
                del self._runs[run_id]

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._drop_chain(run_id)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._drop_chain(run_id)

    # ------------------------------------------------------------------ model calls
    def _model_start(self, serialized: dict | None, run_id: UUID, parent_run_id: UUID | None, metadata: dict | None,
                     kwargs: dict, message_count: int) -> None:
        with self._lock:
            existing = self._runs.get(run_id)
            if existing is not None and existing.get("span") is not None:
                return                                  # same call reported twice: count it once
            parent, helper, helper_type = self._ancestor_span(parent_run_id)
        metadata = metadata or {}
        inv = kwargs.get("invocation_params") or {}
        model = metadata.get("ls_model_name") or inv.get("model") or inv.get("model_name") or "?"
        provider = metadata.get("ls_provider") or inv.get("_type") or "?"
        tier = self.tiers.get(f"{provider}:{model}") or next(
            (t for spec, t in self.tiers.items() if spec.split(":", 1)[-1] == model), None)
        node = metadata.get("langgraph_node")
        attrs = {
            "model": _small(model), "provider": _small(provider), "tier": tier,
            "tuning": {k: _small(inv[k]) for k in _SAFE_INVOCATION_KEYS if k in inv},
            "streaming_requested": bool(inv.get("stream") or inv.get("streaming")),
            "messages": message_count, "graph_node": _small(node), "agent_name": _small(metadata.get("lc_agent_name")),
            "helper_span": helper, "helper_type": helper_type,
            "compaction": bool(node and "summar" in str(node).lower()),
        }
        sp = perf.start_span("model_call", str(model), parent=parent, attrs=attrs)
        token = perf.current_model_call.set(sp.id)
        with self._lock:
            self._runs[run_id] = {"parent": parent_run_id, "kind": "model", "span": sp, "token": token,
                                  "first_chunk": None, "chunks": 0}

    def on_chat_model_start(self, serialized: dict | None, messages: list, *, run_id: UUID,
                            parent_run_id: UUID | None = None, tags: list | None = None, metadata: dict | None = None,
                            **kwargs: Any) -> None:
        self._model_start(serialized, run_id, parent_run_id, metadata, kwargs, len(messages[0]) if messages else 0)

    def on_llm_start(self, serialized: dict | None, prompts: list, *, run_id: UUID, parent_run_id: UUID | None = None,
                     tags: list | None = None, metadata: dict | None = None, **kwargs: Any) -> None:
        self._model_start(serialized, run_id, parent_run_id, metadata, kwargs, len(prompts or []))

    def on_llm_new_token(self, token: str, *, run_id: UUID, **kwargs: Any) -> None:
        rec = self._runs.get(run_id)
        if rec is None or rec["kind"] != "model":
            return
        if rec["first_chunk"] is None:
            rec["first_chunk"] = time.perf_counter()
        rec["chunks"] += 1

    def _model_finish(self, run_id: UUID) -> dict | None:
        with self._lock:
            rec = self._runs.pop(run_id, None)
        if rec is None or rec["kind"] != "model":
            return None
        try:
            perf.current_model_call.reset(rec["token"])
        except (ValueError, RuntimeError):
            perf.current_model_call.set(None)
        return rec

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        rec = self._model_finish(run_id)
        if rec is None:
            return
        sp = rec["span"]
        usage, facts = _usage(response)
        ttft = (rec["first_chunk"] - sp.t0) if rec["first_chunk"] is not None and hasattr(sp, "t0") else None
        sp.end("ok", **usage, **facts, streamed_chunks=rec["chunks"],
               time_to_first_chunk_s=round(ttft, 4) if ttft is not None else None,
               ttft_visibility="observed" if ttft is not None else "not exposed (no streamed chunks)")

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        rec = self._model_finish(run_id)
        if rec is not None:
            rec["span"].fail(error, streamed_chunks=rec["chunks"])

    # ------------------------------------------------------------------ tools and helpers
    def on_tool_start(self, serialized: dict | None, input_str: str, *, run_id: UUID, parent_run_id: UUID | None = None,
                      tags: list | None = None, metadata: dict | None = None, inputs: dict | None = None,
                      **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name") or "?"
        with self._lock:
            if run_id in self._runs and self._runs[run_id].get("span") is not None:
                return
            parent, helper, helper_type = self._ancestor_span(parent_run_id)
        is_helper = name == HELPER_TOOL
        attrs: dict = {"tool": name, "input_chars": len(input_str) if isinstance(input_str, str) else None,
                       "helper_span": helper, "helper_type": helper_type}
        sub_type = None
        if is_helper and isinstance(inputs, dict):
            sub_type = _small(inputs.get("subagent_type"))
            attrs["subagent_type"] = sub_type
        sp = perf.start_span("helper" if is_helper else "tool", str(sub_type or name) if is_helper else name,
                             parent=parent, attrs=attrs)
        token = perf.activate(sp.id)   # deterministic spans inside the tool body nest under this span
        with self._lock:
            self._runs[run_id] = {"parent": parent_run_id, "kind": "helper" if is_helper else "tool", "span": sp,
                                  "token": token, "helper_type": sub_type, "fallback": parent}

    def _tool_finish(self, run_id: UUID) -> dict | None:
        with self._lock:
            rec = self._runs.pop(run_id, None)
        if rec is None or rec["kind"] not in ("tool", "helper"):
            return None
        perf.deactivate(rec["token"], rec.get("fallback"))
        return rec

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        rec = self._tool_finish(run_id)
        if rec is None:
            return
        text = _content_text(output)
        attrs = {"output_chars": len(text) if text is not None else None}
        if text is not None and text.lstrip().startswith("ERROR"):
            # Phase 4 tools catch exceptions and return "ERROR: ..." text: a normal return, a failed domain call.
            rec["span"].end("domain_error", error=text, error_category="tool_error_text", **attrs)
        else:
            rec["span"].end("ok", **attrs)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        rec = self._tool_finish(run_id)
        if rec is not None:
            rec["span"].fail(error)

    def open_runs(self) -> int:
        with self._lock:
            return sum(1 for r in self._runs.values() if r["kind"] != "chain")


# ============================================================================ transport hooks
_HOOKED = "_agent_engine_perf_hooked"
_pending: dict[int, tuple[float, str | None, int | None]] = {}
_pending_lock = threading.Lock()


def _on_request(request: Any) -> None:
    try:
        retry = request.headers.get("x-stainless-retry-count")
        attempt = int(retry) if retry is not None and str(retry).isdigit() else None
        call = perf.current_model_call.get()
        with _pending_lock:
            _pending[id(request)] = (time.perf_counter(), call, attempt)
        perf.event("http_attempt", "model.request", model_call=call, method=request.method,
                   sdk_retry_count=attempt, **perf.url_parts(str(request.url)))
    except Exception:  # noqa: BLE001
        pass


def _on_response(response: Any) -> None:
    try:
        with _pending_lock:
            t0, call, attempt = _pending.pop(id(response.request), (None, None, None))
        perf.event("http_attempt", "model.response", model_call=call or perf.current_model_call.get(),
                   status_code=response.status_code, sdk_retry_count=attempt,
                   elapsed_s=round(time.perf_counter() - t0, 4) if t0 is not None else None,
                   retry_after=response.headers.get("retry-after"), **perf.url_parts(str(response.request.url)))
    except Exception:  # noqa: BLE001
        pass


async def _aon_request(request: Any) -> None:
    _on_request(request)


async def _aon_response(response: Any) -> None:
    _on_response(response)


def _client_classes() -> tuple[tuple, tuple]:
    """(sync, async) client classes of httpx and httpx2: the installed anthropic/openai SDKs use httpx2."""
    sync, asyn = [], []
    for name in ("httpx", "httpx2"):
        try:
            mod = __import__(name)
        except ImportError:
            continue
        sync.append(mod.Client)
        asyn.append(mod.AsyncClient)
    return tuple(sync), tuple(asyn)


def install_transport_hooks(model: Any) -> str:
    """Adds request/response hooks to the HTTP clients a chat model's SDK uses. Returns 'installed' or why not."""
    if not perf.enabled():
        return "disabled"
    sync_classes, async_classes = _client_classes()
    if not sync_classes:
        return "unavailable: neither httpx nor httpx2 is installed"
    found = 0
    for chain in (("_client", "_client"), ("_async_client", "_client"), ("root_client", "_client"),
                  ("root_async_client", "_client")):
        obj = model
        try:
            for attr in chain:
                obj = getattr(obj, attr)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, sync_classes + async_classes):
            if getattr(obj, _HOOKED, False):
                found += 1
                continue
            is_async = isinstance(obj, async_classes)
            hooks = obj.event_hooks
            hooks.setdefault("request", []).append(_aon_request if is_async else _on_request)
            hooks.setdefault("response", []).append(_aon_response if is_async else _on_response)
            obj.event_hooks = hooks
            try:
                setattr(obj, _HOOKED, True)
            except Exception:  # noqa: BLE001
                pass
            found += 1
    return "installed" if found else f"unavailable: no httpx client found on {type(model).__name__}"
