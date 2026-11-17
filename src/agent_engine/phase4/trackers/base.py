"""Tracker adapter interface + shared HTTP behaviour."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from agent_engine import perf

log = logging.getLogger(__name__)


def _operation(method: str) -> str:
    return {"GET": "read", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}.get(
        method.upper(), method.lower())


@dataclass
class ExtObj:
    id: str
    key: str | None = None


class TrackerError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    @property
    def rejected(self) -> bool:
        """Definite rejection, unlike a timeout/5xx that may follow a committed write."""
        return self.status_code in (400, 401, 403, 404, 405, 413, 422, 429)


class TrackerAdapter:
    """Payloads use a tracker-neutral shape:
    {level, title, body_md, labels, parent_id, story_points, hours, _marker}
    """

    kind = "base"
    system = "base"

    def prepare(self) -> None:
        """Resolve shared metadata before a publisher starts worker threads."""

    def close(self) -> None:
        if http := getattr(self, "http", None):
            http.close()

    # backlog
    def create(self, payload: dict) -> ExtObj: raise NotImplementedError
    def update(self, external_id: str, fields: dict) -> None: raise NotImplementedError
    def get_fields(self, external_id: str) -> dict: raise NotImplementedError
    def set_field_if_empty(self, external_id: str, field: str, value) -> bool: raise NotImplementedError
    def find_by_marker(self, marker: str, level: str | None = None) -> ExtObj | None: raise NotImplementedError
    def add_blocks(self, blocker_id: str, blocked_id: str) -> None: raise NotImplementedError
    def remove_blocks(self, blocker_id: str, blocked_id: str) -> None: raise NotImplementedError
    def reopen_item(self, issue_id: str) -> None: raise NotImplementedError
    def blocks_of(self, issue_id: str) -> list[str]: raise NotImplementedError  # ids this issue blocks
    def add_comment(self, issue_id: str, text: str) -> None: raise NotImplementedError
    def item_done(self, issue_id: str) -> bool: raise NotImplementedError
    def close_item(self, issue_id: str, reason: str) -> None: raise NotImplementedError
    # sprints
    def create_sprint(self, name: str, start: date, end: date, goal: str) -> ExtObj: raise NotImplementedError
    def board_sprints(self) -> list[dict]: return []          # existing future/active sprints, for reuse
    def update_sprint(self, sprint_id: str, fields: dict) -> None: raise NotImplementedError
    def move_to_sprint(self, sprint_id: str, issue_ids: list[str]) -> None: raise NotImplementedError
    def move_to_backlog(self, issue_ids: list[str]) -> None: raise NotImplementedError
    # people
    def assign(self, issue_id: str, account_id: str | None) -> None: raise NotImplementedError
    # history
    def closed_sprints(self, limit: int = 12) -> list[dict]: raise NotImplementedError
    def resolved_tickets(self, since: date) -> list[dict]: raise NotImplementedError
    def open_work(self) -> list[dict]:
        """Open assigned items: [{account, issue_id, points, hours}] (used to deduct committed work from capacity)."""
        return []


class HttpClient:
    """httpx wrapper: retries 429/5xx honouring Retry-After, throttles creates (~1 req/s)."""

    def __init__(self, base_url: str, headers: dict[str, str], *, auth: Any = None,
                 min_write_interval_s: float = 1.0, max_retries: int = 5, timeout: float = 30.0,
                 retry_rejected_posts: bool = False,
                 transport: httpx.BaseTransport | None = None) -> None:
        self.client = httpx.Client(base_url=base_url, headers=headers, auth=auth, timeout=timeout,
                                   transport=transport)
        self.min_write_interval_s = min_write_interval_s
        self.max_retries = max_retries
        self._last_write = 0.0
        self._rate_lock = threading.Lock()
        self._cooldown_until = 0.0
        self.retry_rejected_posts = retry_rejected_posts

    def _wait_for_slot(self, method: str) -> float:
        started = time.monotonic()
        # Reserve a request start under one lock. Waiting threads recheck a
        # shared 429 cooldown instead of issuing a burst when it expires.
        while True:
            with self._rate_lock:
                now = time.monotonic()
                write = method.upper() in ("POST", "PUT", "PATCH", "DELETE")
                ready = max(self._cooldown_until, self._last_write + self.min_write_interval_s if write else 0)
                if ready <= now:
                    if write:
                        self._last_write = now
                    return time.monotonic() - started
            time.sleep(min(ready - now, 0.25))

    def request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        with perf.http_span("tracker", _operation(method), method.upper(), str(self.client.base_url).rstrip("/") + url,
                            include_path=True, max_retries=self.max_retries) as sp:
            throttle_s = 0.0
            delay = 1.0
            backoff_s = 0.0
            for attempt in range(self.max_retries + 1):
                throttle_s += self._wait_for_slot(method)
                try:
                    resp = self.client.request(method, url, **kw)
                except httpx.RequestError as exc:
                    raise TrackerError(f"{method} {url}: {type(exc).__name__}; remote write outcome may be unknown") from exc
                perf.event("http_attempt", "tracker.response", attempt=attempt + 1, status_code=resp.status_code)
                if resp.status_code in (429, 500, 502, 503, 504) or (
                        resp.status_code == 403 and "rate limit" in resp.text.lower()):
                    # Replaying an ambiguous create may duplicate an issue/comment/job.
                    # GraphQL queries are read-only even though transported as POST.
                    query = (kw.get("json") or {}).get("query", "") if isinstance(kw.get("json"), dict) else ""
                    safe_post = query.lstrip().startswith("query") or bool((kw.get("headers") or {}).get("Idempotency-Key"))
                    rejected = self.retry_rejected_posts and resp.status_code == 429
                    if method.upper() == "POST" and not (safe_post or rejected):
                        break
                    if attempt == self.max_retries:
                        break
                    ra = resp.headers.get("retry-after")
                    sleep_s = delay
                    if ra:
                        try:
                            sleep_s = max(0.0, float(ra))
                        except ValueError:
                            try:
                                sleep_s = max(0.0, (parsedate_to_datetime(ra) - datetime.now(timezone.utc)).total_seconds())
                            except (ValueError, TypeError, OverflowError):
                                pass
                    if sleep_s > 120:
                        # Never retry earlier than the server permits; return a
                        # resumable error instead of holding the process indefinitely.
                        break
                    log.warning("tracker %s %s -> %s; retrying in %.1fs", method, url, resp.status_code, sleep_s)
                    with self._rate_lock:
                        self._cooldown_until = max(self._cooldown_until, time.monotonic() + min(sleep_s, 120))
                    resp.close()
                    backoff_s += min(sleep_s, 120)
                    delay = min(delay * 2, 60)
                    continue
                break
            perf.http_result(sp, resp)
            sp.set(attempts=attempt + 1, throttle_wait_s=round(throttle_s, 3), retry_backoff_s=round(backoff_s, 3))
            if resp.status_code >= 400:
                raise TrackerError(f"{method} {url} -> {resp.status_code}: {resp.text[:500]}", status_code=resp.status_code)
            return resp

    def get(self, url: str, **kw: Any) -> httpx.Response: return self.request("GET", url, **kw)
    def close(self) -> None: self.client.close()
    def post(self, url: str, **kw: Any) -> httpx.Response: return self.request("POST", url, **kw)
    def put(self, url: str, **kw: Any) -> httpx.Response: return self.request("PUT", url, **kw)
    def patch(self, url: str, **kw: Any) -> httpx.Response: return self.request("PATCH", url, **kw)
    def delete(self, url: str, **kw: Any) -> httpx.Response: return self.request("DELETE", url, **kw)
