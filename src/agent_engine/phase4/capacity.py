"""Sprint calendar, availability and Monte Carlo velocity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from agent_engine.phase4.contracts import ProjectSettings
from agent_engine.phase4.calendars import unavailable_days, utc_today

SAMPLES = 10_000
COLD_START_SPRINTS = 3
COLD_START_LOAD = 0.7


@dataclass
class SprintWindow:
    index: int              # 1-based position in this plan
    number: int             # absolute sprint number since first_sprint_start
    start: date
    end: date
    person_days: float = 0.0
    person_hours: float = 0.0
    hours_by_member: dict[str, float] = field(default_factory=dict)
    cap_p50: float = 0.0
    cap_p85: float = 0.0
    reserved: float = 0.0
    active: bool = False


def sprint_windows(project: ProjectSettings, today: date | None = None) -> list[SprintWindow]:
    cal = project.calendar
    today = today or utc_today()
    L = cal.sprint_length_days
    n = 0
    start = cal.first_sprint_start
    while start + timedelta(days=L - 1) < today:          # skip finished sprints
        start += timedelta(days=L)
        n += 1
    out = []
    for i in range(cal.planning_horizon_sprints):
        s = start + timedelta(days=i * L)
        out.append(SprintWindow(index=i + 1, number=n + i + 1, start=s, end=s + timedelta(days=L - 1),
                                active=(s <= today)))
    return out


def working_days(start: date, end: date, weekdays: list[int], excluded: set[date]) -> list[date]:
    d, out = start, []
    while d <= end:
        if d.weekday() in weekdays and d not in excluded:
            out.append(d)
        d += timedelta(days=1)
    return out


def fill_availability(project: ProjectSettings, windows: list[SprintWindow]) -> None:
    cal = project.calendar
    if not windows:
        return
    ids = [m.calendar_id for m in project.team if m.calendar_id]
    ooo = unavailable_days(ids, windows[0].start, windows[-1].end)
    for w in windows:
        total_days = total_hours = 0.0
        for m in project.team:
            excluded = set(cal.holidays) | set(m.pto_days) | ooo.get(m.calendar_id or "", set())
            days = len(working_days(w.start, w.end, cal.working_weekdays, excluded))
            frac = m.allocation_pct / 100
            hours = max(0.0, days * m.hours_per_day * frac - cal.ceremony_hours_per_sprint * frac)
            w.hours_by_member[m.member_id] = hours
            total_hours += hours
            total_days += hours / m.hours_per_day if m.hours_per_day else 0
        w.person_days, w.person_hours = round(total_days, 2), round(total_hours, 2)


def history_rates(history: list[dict]) -> list[float]:
    rates = []
    for h in history:
        pd = h.get("available_person_days")
        if pd and pd > 0:
            rates.append(h["completed_points"] / pd)
    return rates


def monte_carlo_capacity(rates: list[float], person_days: float, rng: np.random.Generator) -> tuple[float, float]:
    """P50 = median; P85 = 15th percentile (points completed with 85% probability)."""
    sample = rng.choice(np.asarray(rates), size=SAMPLES, replace=True) * person_days
    return float(np.percentile(sample, 50)), float(np.percentile(sample, 15))


def fill_capacity(project: ProjectSettings, windows: list[SprintWindow], history: list[dict],
                  seed: int = 7) -> list[str]:
    """Sets cap_p50 / cap_p85 / reserved per window. Returns assumptions for the plan."""
    assumptions: list[str] = []
    rng = np.random.default_rng(seed)
    rates = history_rates(history)
    if len(history) >= COLD_START_SPRINTS and not rates:
        # history without availability: assume the full team was present in those sprints
        L = project.calendar.sprint_length_days
        days_per_sprint = len(working_days(date(2024, 1, 1), date(2024, 1, 1) + timedelta(days=L - 1),
                                           project.calendar.working_weekdays, set()))
        full_pd = sum(days_per_sprint * m.allocation_pct / 100 for m in project.team)
        rates = [h["completed_points"] / full_pd for h in history] if full_pd else []
        assumptions.append("Past sprint availability unknown; assumed the full team was present.")
    cold = len(rates) < COLD_START_SPRINTS
    if cold:
        assumptions.append(f"Cold start: fewer than {COLD_START_SPRINTS} closed sprints with history; capacity = "
                           f"person-hours ÷ {project.hours_per_story_point} h/SP × {COLD_START_LOAD} (low confidence).")
    else:
        assumptions.append(f"Capacity from Monte Carlo over {len(rates)} past sprints ({SAMPLES} samples); "
                           "P85 = points finished with 85% probability.")
    pct = project.maintenance_capacity_pct / 100
    for w in windows:
        if cold:
            p50 = w.person_hours / project.hours_per_story_point * COLD_START_LOAD
            p85 = p50 * 0.8
        else:
            p50, p85 = monte_carlo_capacity(rates, w.person_days, rng)
        w.reserved = round(p50 * pct, 1)
        w.cap_p50 = round(p50 * (1 - pct), 1)
        w.cap_p85 = round(p85 * (1 - pct), 1)
    if pct:
        assumptions.append(f"{project.maintenance_capacity_pct}% of capacity reserved for maintenance work.")
    return assumptions


def forecast(points_planned: float, windows: list[SprintWindow], history: list[dict], scope_growth: float = 1.1,
             seed: int = 11) -> tuple[int, int]:
    """Sprint index (1-based, may exceed the horizon) by which the planned scope finishes at P50/P85."""
    rng = np.random.default_rng(seed)
    rates = history_rates(history)
    caps = [w.cap_p50 for w in windows] or [1.0]
    finish = []
    for _ in range(2000):
        remaining = points_planned * scope_growth
        k = 0
        while remaining > 0 and k < 60:
            pd = windows[min(k, len(windows) - 1)].person_days
            cap = float(rng.choice(rates)) * pd if rates else caps[min(k, len(caps) - 1)] * rng.uniform(0.7, 1.1)
            remaining -= max(cap, 0.1)
            k += 1
        finish.append(k)
    return int(np.percentile(finish, 50)), int(np.percentile(finish, 85))
