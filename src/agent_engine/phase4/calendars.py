"""Availability from calendars: Google freeBusy and Microsoft Graph getSchedule.

Only out-of-office / full-day busy blocks reduce available days. Event subjects are never read or stored.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone

import httpx
import jwt

from agent_engine import perf
from agent_engine.phase4.settings import get_settings

log = logging.getLogger(__name__)


def _google_token() -> str:
    sa = json.loads(get_settings().google_sa_json)
    now = int(time.time())
    assertion = jwt.encode({"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/calendar.freebusy",
                            "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600},
                           sa["private_key"], algorithm="RS256")
    with perf.http_span("google_calendar", "token", "POST", "https://oauth2.googleapis.com/token") as sp:
        r = httpx.post("https://oauth2.googleapis.com/token", timeout=20,
                       data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
        perf.http_result(sp, r)
        r.raise_for_status()
    return r.json()["access_token"]


def google_unavailable_days(calendar_ids: list[str], start: date, end: date) -> dict[str, set[date]]:
    token = _google_token()
    out: dict[str, set[date]] = {c: set() for c in calendar_ids}
    for i in range(0, len(calendar_ids), 50):                        # max 50 calendars per call
        body = {"timeMin": f"{start.isoformat()}T00:00:00Z", "timeMax": f"{(end + timedelta(days=1)).isoformat()}T00:00:00Z",
                "items": [{"id": c} for c in calendar_ids[i:i + 50]]}
        with perf.http_span("google_calendar", "freebusy", "POST", "https://www.googleapis.com/calendar/v3/freeBusy",
                            calendars=len(body["items"])) as sp:
            r = httpx.post("https://www.googleapis.com/calendar/v3/freeBusy", json=body, timeout=30,
                           headers={"Authorization": f"Bearer {token}"})
            perf.http_result(sp, r)
            r.raise_for_status()
        for cid, cal in r.json().get("calendars", {}).items():
            for b in cal.get("busy", []):
                s = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
                if (e - s) >= timedelta(hours=20):                    # full-day blocks only
                    d = s.date()
                    while d < e.date() or d == s.date():
                        out[cid].add(d)
                        d += timedelta(days=1)
    return out


def _graph_token() -> str:
    s = get_settings()
    with perf.http_span("ms_graph", "token", "POST", "https://login.microsoftonline.com/") as sp:
        r = httpx.post(f"https://login.microsoftonline.com/{s.ms_graph_tenant_id}/oauth2/v2.0/token", timeout=20,
                       data={"client_id": s.ms_graph_client_id, "client_secret": s.ms_graph_client_secret,
                             "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"})
        perf.http_result(sp, r)
        r.raise_for_status()
    return r.json()["access_token"]


def graph_unavailable_days(emails: list[str], start: date, end: date, organizer: str) -> dict[str, set[date]]:
    token = _graph_token()
    body = {"schedules": emails,
            "startTime": {"dateTime": f"{start.isoformat()}T00:00:00", "timeZone": "UTC"},
            "endTime": {"dateTime": f"{(end + timedelta(days=1)).isoformat()}T00:00:00", "timeZone": "UTC"},
            "availabilityViewInterval": 1440}
    with perf.http_span("ms_graph", "get_schedule", "POST", "https://graph.microsoft.com/", calendars=len(emails)) as sp:
        r = httpx.post(f"https://graph.microsoft.com/v1.0/users/{organizer}/calendar/getSchedule", json=body, timeout=30,
                       headers={"Authorization": f"Bearer {token}"})
        perf.http_result(sp, r)
        r.raise_for_status()
    out: dict[str, set[date]] = {}
    for sch in r.json().get("value", []):
        days = set()
        view = sch.get("availabilityView", "")
        for k, ch in enumerate(view):         # one char per day: 3 = out of office
            if ch == "3":
                days.add(start + timedelta(days=k))
        out[sch["scheduleId"]] = days          # scheduleItems (with subjects) are deliberately ignored
    return out


def unavailable_days(calendar_ids: list[str], start: date, end: date) -> dict[str, set[date]]:
    """Best-effort: returns {} when no calendar integration is configured or it fails."""
    s = get_settings()
    if not calendar_ids:
        perf.event("calendar", "skipped", reason="no calendar ids in phase4/project.json")
        return {}
    try:
        if s.google_sa_json:
            return google_unavailable_days(calendar_ids, start, end)
        if s.ms_graph_client_id:
            return graph_unavailable_days(calendar_ids, start, end, calendar_ids[0])
        perf.event("calendar", "skipped", reason="no calendar integration configured", calendars=len(calendar_ids))
    except Exception as exc:  # calendars must never block planning
        log.warning("calendar availability unavailable: %s", exc)
        perf.event("calendar", "failed_best_effort", error_category=perf.classify_error(exc),
                   error=perf.error_summary(exc))
    return {}


def utc_today() -> date:
    return datetime.now(timezone.utc).date()
