"""Tracker adapter interface + shared HTTP behaviour."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
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
    pass


class TrackerAdapter:
    """Payloads use a tracker-neutral shape:
    {level, title, body_md, labels, parent_id, story_points, hours, _marker}
    """

    kind = "base"
    system = "base"

    # backlog
    def create(self, payload: dict) -> ExtObj: raise NotImplementedError
    def update(self, external_id: str, fields: dict) -> None: raise NotImplementedError
    def get_fields(self, external_id: str) -> dict: raise NotImplementedError
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
                 transport: httpx.BaseTransport | None = None) -> None:
        self.client = httpx.Client(base_url=base_url, headers=headers, auth=auth, timeout=timeout,
                                   transport=transport)
        self.min_write_interval_s = min_write_interval_s
        self.max_retries = max_retries
        self._last_write = 0.0

    def request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        with perf.http_span("tracker", _operation(method), method.upper(), str(self.client.base_url).rstrip("/") + url,
                            include_path=True, max_retries=self.max_retries) as sp:
            throttle_s = 0.0
            if method.upper() in ("POST", "PUT", "PATCH", "DELETE") and self.min_write_interval_s:
                wait = self._last_write + self.min_write_interval_s - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                    throttle_s = wait
                self._last_write = time.monotonic()
            delay = 1.0
            backoff_s = 0.0
            for attempt in range(self.max_retries + 1):
                resp = self.client.request(method, url, **kw)
                perf.event("http_attempt", "tracker.response", attempt=attempt + 1, status_code=resp.status_code)
                if resp.status_code in (429, 500, 502, 503, 504) or (
                        resp.status_code == 403 and "rate limit" in resp.text.lower()):
                    # Replaying an ambiguous create may duplicate an issue/comment/job.
                    # GraphQL queries are read-only even though transported as POST.
                    query = (kw.get("json") or {}).get("query", "") if isinstance(kw.get("json"), dict) else ""
                    safe_post = query.lstrip().startswith("query") or bool((kw.get("headers") or {}).get("Idempotency-Key"))
                    if method.upper() == "POST" and not safe_post:
                        break
                    if attempt == self.max_retries:
                        break
                    ra = resp.headers.get("retry-after")
                    sleep_s = float(ra) if ra and ra.replace(".", "", 1).isdigit() else delay
                    log.warning("tracker %s %s -> %s; retrying in %.1fs", method, url, resp.status_code, sleep_s)
                    time.sleep(min(sleep_s, 120))
                    backoff_s += min(sleep_s, 120)
                    delay = min(delay * 2, 60)
                    continue
                break
            perf.http_result(sp, resp)
            sp.set(attempts=attempt + 1, throttle_wait_s=round(throttle_s, 3), retry_backoff_s=round(backoff_s, 3))
            if resp.status_code >= 400:
                raise TrackerError(f"{method} {url} -> {resp.status_code}: {resp.text[:500]}")
            return resp

    def get(self, url: str, **kw: Any) -> httpx.Response: return self.request("GET", url, **kw)
    def close(self) -> None: self.client.close()
    def post(self, url: str, **kw: Any) -> httpx.Response: return self.request("POST", url, **kw)
    def put(self, url: str, **kw: Any) -> httpx.Response: return self.request("PUT", url, **kw)
    def patch(self, url: str, **kw: Any) -> httpx.Response: return self.request("PATCH", url, **kw)
    def delete(self, url: str, **kw: Any) -> httpx.Response: return self.request("DELETE", url, **kw)
