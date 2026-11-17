"""The Phase 4 file contracts: what each agent reads and writes under outputs/<project>/.

  phase4/project.json      ProjectSettings   (human: team, calendar, DoD, tracker, repos, deadlines)
  phase4/history.json      History           (optional: resolved tickets + closed sprints)
  backlog/backlog.json     Backlog           (Agent 1 Task Breakdown)
  sprint/sprint-plan.json  SprintPlan        (Agent 2 Sprint Planning)
  allocation/assignments.json AssignmentPlan (Agent 3 Work Allocation)
  infra/intent.json        InfraIntent       (Agent 4 Infra & Pipeline)
  infra/manifest.json      InfraManifest     (Agent 4)
  infra/checks.json        list[CheckResult] (Agent 4)

Every model rejects unknown fields, so a typo fails loudly instead of being dropped.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True, allow_inf_nan=False)


# ============================================================================ project settings (input)
class TrackerKind(StrEnum):
    JIRA = "jira"
    LINEAR = "linear"
    GITHUB = "github"
    LOCAL = "local"  # files under outputs/<project>/tracker/ (demos, tests, no tracker account)


class TeamMember(Strict):
    member_id: str
    display_name: str
    email: str
    tracker_account_id: str
    github_login: str | None = None
    role: str
    allocation_pct: int = Field(default=100, ge=0, le=100)
    hours_per_day: float = Field(default=6.0, gt=0, le=24)
    declared_skills: list[str] = []
    timezone: str = "UTC"
    calendar_id: str | None = None
    wip_limit: int = Field(default=3, ge=1)
    can_review: bool = True
    learning_goals: list[str] = []
    pto_days: list[date] = []


class AIAgentWorker(Strict):
    agent_id: str
    provider: Literal["copilot_cloud_agent", "claude_code_action"]
    skills: list[str]
    max_concurrent_tasks: int = Field(default=3, ge=1)
    max_task_hours: float = Field(default=4.0, gt=0)
    enabled: bool = True


class SprintCalendar(Strict):
    sprint_length_days: int = Field(default=14, ge=1, le=366)
    first_sprint_start: date
    planning_horizon_sprints: int = Field(default=4, ge=1, le=12)
    working_weekdays: list[int] = [0, 1, 2, 3, 4]
    holidays: list[date] = []
    ceremony_hours_per_sprint: float = Field(default=6.0, ge=0)

    @model_validator(mode="after")
    def _weekdays(self):
        if not self.working_weekdays or any(d not in range(7) for d in self.working_weekdays):
            raise ValueError("working_weekdays must contain days 0..6")
        if len(set(self.working_weekdays)) != len(self.working_weekdays):
            raise ValueError("working_weekdays must be unique")
        return self


class TrackerConfig(Strict):
    kind: TrackerKind = TrackerKind.LOCAL
    jira_base_url: str | None = None
    jira_project_key: str | None = None
    jira_board_id: int | None = None
    linear_team_id: str | None = None
    github_owner: str | None = None
    github_repo: str | None = None
    github_project_number: int | None = None

    @model_validator(mode="after")
    def _required_per_kind(self) -> "TrackerConfig":
        need = {
            TrackerKind.JIRA: ["jira_base_url", "jira_project_key", "jira_board_id"],
            TrackerKind.LINEAR: ["linear_team_id"],
            TrackerKind.GITHUB: ["github_owner", "github_repo"],
            TrackerKind.LOCAL: [],
        }[self.kind]
        missing = [f for f in need if getattr(self, f) in (None, "")]
        if missing:
            raise ValueError(f"tracker kind {self.kind.value} requires {missing}")
        return self


class Deadline(Strict):
    ref_id: str
    name: str
    due_date: date
    requirement_ids: list[str]  # ids from prd.md (FR-1, US-2, ...)
    hard: bool = False


class ReleaseDeadline(Strict):
    """A roadmap release's deadline when the tracker version has no release date (the tracker date wins)."""

    release: str                # tracker version name, e.g. MVP
    due_date: date
    hard: bool = False          # also applies when the date comes from the tracker


class ProjectSettings(Strict):
    schema_version: str = SCHEMA_VERSION
    project_name: str
    tracker: TrackerConfig = TrackerConfig()
    code_repos: list[str] = []
    infra_repo: str = ""
    team: list[TeamMember]
    ai_agents: list[AIAgentWorker] = []
    calendar: SprintCalendar
    definition_of_done: list[str]
    story_point_scale: list[int] = [1, 2, 3, 5, 8, 13]
    hours_per_story_point: float = Field(default=6.0, gt=0)
    maintenance_capacity_pct: int = Field(default=20, ge=0, le=60)
    max_story_points_per_story: int = Field(default=13, ge=1)
    deadlines: list[Deadline] = []
    release_deadlines: list[ReleaseDeadline] = []   # fallback dates for roadmap releases without a tracker date
    # AI agents get work only after this many recorded outcomes (phase4/agent-outcomes.json); before that they
    # run in shadow mode. 0 trusts them from the start.
    human_only_components: list[str] = []
    ai_min_recorded_outcomes: int = Field(default=20, ge=0)

    @model_validator(mode="after")
    def _unique_and_positive(self):
        groups = [[m.member_id for m in self.team] + [a.agent_id for a in self.ai_agents],
                  [d.ref_id for d in self.deadlines], self.code_repos]
        for ids in groups:
            if any(not x for x in ids) or len(ids) != len(set(ids)):
                raise ValueError("worker, deadline and repository identifiers must be nonempty and unique")
        if not self.team:
            raise ValueError("team must not be empty")
        if not self.story_point_scale or any(x <= 0 for x in self.story_point_scale):
            raise ValueError("story_point_scale must contain positive integers")
        if self.story_point_scale != sorted(set(self.story_point_scale)):
            raise ValueError("story_point_scale must be sorted and unique")
        return self


class HistoryTicket(Strict):
    key: str
    title: str
    body: str = ""
    story_points: float | None = None
    hours: float | None = None
    resolved_at: date | None = None
    assignee: str | None = None        # member_id
    skills: list[str] = []


class HistorySprint(Strict):
    name: str
    start: date
    end: date
    completed_points: float
    available_person_days: float | None = None


class History(Strict):
    source: Literal["manual", "jira"] = "manual"   # jira = refreshed from the tracker; a manual file is never overwritten
    tickets: list[HistoryTicket] = []
    sprints: list[HistorySprint] = []


# ============================================================================ approved stories (input)
class Release(Strict):
    """One roadmap release (a Jira version), in roadmap order."""

    name: str
    order: int                                 # 1 = first release on the roadmap
    release_date: date | None = None           # from the tracker; project.json release_dates is the fallback
    released: bool = False


class ImportedCriterion(Strict):
    ac_id: str                 # as written in the tracker (US-001.AC1), or <KEY>.AC<n> when unnumbered
    text: str


class ImportedStory(Strict):
    """One approved story exactly as the tracker holds it. Task Breakdown splits it; it never rewrites it."""

    key: str                                   # tracker key, e.g. GR-9
    issue_id: str
    summary: str
    statement: str = ""                        # "As ..., I want ... so that ..."
    acceptance_criteria: list[ImportedCriterion] = []
    notes: str = ""
    traceability: str = ""
    description_md: str = ""                   # the whole description as text, for anything not parsed above
    labels: list[str] = []
    requirement_ids: list[str] = []            # US-/FR-/NFR-/DS- ids from labels and traceability
    persona_ids: list[str] = []
    moscow: Literal["must", "should", "could", "wont"] | None = None
    priority: str | None = None                # tracker priority name, kept as-is
    fix_versions: list[str] = []
    components: list[str] = []
    epic_key: str | None = None
    story_points: float | None = None          # set upstream (Phase 2); Task Breakdown does not overwrite it
    rank: str | None = None                    # tracker backlog order (Jira LexoRank: sorts as text)
    blocks: list[str] = []                     # keys of stories this story blocks
    status: str = ""
    approval: str | None = None                # the approval line found in the description


class ImportedEpic(Strict):
    key: str
    issue_id: str
    summary: str
    description_md: str = ""
    labels: list[str] = []
    requirement_ids: list[str] = []


class StoryExclusion(Strict):
    key: str
    summary: str = ""
    reason: str


class StorySnapshot(Strict):
    """phase4/stories.json: the approved stories Task Breakdown works from.

    Content only (no timestamps), so an unchanged tracker produces identical bytes and does not re-run the agent.
    """

    schema_version: str = SCHEMA_VERSION
    project: str
    source: Literal["jira", "file"]
    site: str = ""
    project_key: str = ""
    jql: str = ""
    story_points_field: str | None = None
    approval_marker: str = ""
    releases: list[Release] = []               # the roadmap: tracker versions in order
    epics: list[ImportedEpic] = []
    stories: list[ImportedStory]
    excluded: list[StoryExclusion] = []

    @model_validator(mode="after")
    def _unique(self):
        keys = [s.key for s in self.stories]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate story keys")
        if not self.stories:
            raise ValueError("no approved stories")
        epic_keys = [e.key for e in self.epics]
        if len(epic_keys) != len(set(epic_keys)):
            raise ValueError("duplicate epic keys")
        return self


# ============================================================================ Agent 1: backlog
ItemLevel = Literal["epic", "story", "task"]
ItemType = Literal["feature", "test", "infra", "ui", "chore", "spike", "docs"]


class SourceRef(Strict):
    req_id: str
    source: Literal["prd", "story", "figma", "arch", "clarification"]
    anchor: str = ""


class AcceptanceCriterion(Strict):
    ac_id: str
    format: Literal["gherkin", "ears"]
    text: str


class Dependency(Strict):
    on_id: str
    reason: str
    confidence: float = Field(ge=0, le=1)
    origin: Literal["llm", "human"]      # human = set by a person or the tracker (e.g. a Jira "blocks" link)


class Estimate(Strict):
    story_points: int | None = None  # stories
    hours: float | None = None       # tasks
    complexity: int = Field(ge=1, le=10)
    confidence: Literal["low", "medium", "high"]
    method: Literal["analogy", "llm", "median_fallback", "human", "rollup"]
    reference_ticket_ids: list[str] = []
    rationale: str = ""


class UserStory(Strict):
    as_a: str
    i_want: str
    so_that: str


class WorkItem(Strict):
    item_id: str
    level: ItemLevel
    parent_id: str | None = None
    title: str
    description_md: str = ""
    type: ItemType = "feature"
    discipline: Literal["FE", "BE", "DB", "DevOps", "QA"] | None = None   # tasks: which part of the stack
    release: str | None = None           # stories: the roadmap release (fix version) it belongs to
    rank: str | None = None              # stories: approved backlog order from the tracker (sorts as text)
    priority: Literal["P1", "P2", "P3"] = "P2"
    moscow: Literal["must", "should", "could", "wont"] = "should"
    user_story: UserStory | None = None
    acceptance_criteria: list[AcceptanceCriterion] = []
    definition_of_done: list[str] = []
    file_paths: list[str] = []
    components: list[str] = []
    repo: str | None = None
    parallel: bool = False
    dependencies: list[Dependency] = []
    estimate: Estimate | None = None
    skills_required: list[str] = []
    ai_eligible: bool = False
    ai_eligibility_reason: str = ""
    source_refs: list[SourceRef] = []
    open_questions: list[str] = []
    deferred_criteria: list[str] = []    # stories: acceptance criteria a gate reviewer decided not to build now


class Feature(Strict):
    """One epic of the approved stories (the tracker epic, or NO-EPIC for stories without one)."""

    feature_key: str                     # F01, F02, ...
    feature_dir: str                     # specs/001-short-name
    title: str
    summary: str
    requirement_ids: list[str] = []      # PRD ids this feature covers (FR-1, US-2, ...)
    component_ids: list[str] = []        # architecture components it touches
    repo: str | None = None              # code repository the work lands in


class FeatureList(Strict):
    features: list[Feature]


class ValidationIssue(Strict):
    rule: str
    severity: Literal["blocking", "warning"]
    item_ids: list[str] = []
    message: str


class Backlog(Strict):
    schema_version: str = SCHEMA_VERSION
    backlog_id: str
    version: int = 1
    project: str
    sources: dict[str, str]              # input file -> sha256 it was built from
    features: list[Feature]
    releases: list[Release] = []         # the roadmap, in order (from phase4/stories.json)
    items: list[WorkItem]
    coverage: dict[str, list[str]] = {}  # requirement id -> story ids
    story_waves: list[list[str]] = []
    critical_path: list[str] = []
    issues: list[ValidationIssue] = []
    generated_at: datetime

    @model_validator(mode="after")
    def _unique_items(self):
        ids = [i.item_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate backlog item IDs")
        return self

    def by_id(self) -> dict[str, WorkItem]:
        return {i.item_id: i for i in self.items}

    def stories(self) -> list[WorkItem]:
        return [i for i in self.items if i.level == "story"]

    def tasks_of(self, story_id: str) -> list[WorkItem]:
        return [i for i in self.items if i.level == "task" and i.parent_id == story_id]


# ============================================================================ Agent 2: sprint plan
class SprintSlot(Strict):
    sprint_index: int
    number: int
    name: str
    start: date
    end: date
    goal: str = ""
    story_ids: list[str]
    committed_points: int
    capacity_p50: float
    capacity_p85: float
    maintenance_reserved_points: float
    available_person_days: float


class Deferral(Strict):
    story_id: str
    reason_code: Literal["capacity", "dependency", "deadline_infeasible", "unestimated", "too_large",
                         "wont", "human_override", "beyond_horizon"]
    explanation: str


class Forecast(Strict):
    p50_last_sprint: int
    p85_last_sprint: int
    p50_date: date
    p85_date: date
    samples: int = 2000


class SolverReport(Strict):
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "MODEL_INVALID", "UNKNOWN"]
    objective: float | None = None
    best_bound: float | None = None
    wall_time_s: float
    conflicting_constraints: list[str] = []


class PlanOption(Strict):
    option_id: str
    summary: str
    changes: list[str]
    impact: str


class ReleasePlan(Strict):
    """When one roadmap release lands, from the placement and the velocity forecast."""

    release: str
    order: int
    due_date: date | None = None
    date_source: Literal["tracker", "project", "none"] = "none"
    hard: bool = False
    story_ids: list[str] = []
    points: float = 0
    deferred_story_ids: list[str] = []
    last_sprint_index: int | None = None     # last sprint of this plan holding one of its stories
    planned_finish: date | None = None       # end of that sprint (None if a story is deferred)
    p50_date: date | None = None             # velocity forecast of this release and all earlier ones
    p85_date: date | None = None
    status: Literal["on_track", "late", "incomplete", "no_deadline"] = "no_deadline"


class SprintPlan(Strict):
    schema_version: str = SCHEMA_VERSION
    plan_id: str
    version: int = 1
    project: str
    backlog_sha256: str
    settings_sha256: str | None = None
    as_of: date
    sprints: list[SprintSlot]
    deferred: list[Deferral]
    forecast: Forecast | None = None
    releases: list[ReleasePlan] = []         # the release plan, in roadmap order
    solver: SolverReport
    assumptions: list[str] = []
    options_if_infeasible: list[PlanOption] = []
    priority_order: list[str] = []           # stories in approved order: release -> MoSCoW -> tracker Rank
    priority: dict[str, float] = {}          # story -> weight per point (100 = first, 1 = last)
    pins: dict[str, int] = {}
    relaxations: list[str] = []
    summary_md: str = ""
    annotated: bool = False                  # goals + explanations written
    generated_at: datetime

    def sprint_of(self, story_id: str) -> int | None:
        for s in self.sprints:
            if story_id in s.story_ids:
                return s.sprint_index
        return None


# ============================================================================ Agent 3: assignments
class Assignment(Strict):
    task_id: str
    story_id: str
    sprint_index: int
    worker_id: str
    worker_kind: Literal["human", "ai_agent"]
    planned_start_minute: int
    planned_hours: float
    score_breakdown: dict[str, float]
    explanation: str = ""
    runner_up_worker_id: str | None = None
    pinned: bool = False


class Unassigned(Strict):
    task_id: str
    reason_code: Literal["no_skill_match", "capacity", "not_ai_eligible", "solver_unassigned", "blocked"]
    explanation: str


class EligibilityVerdict(Strict):
    eligible: bool
    reason: str
    shadow: bool = False


class AssignmentPlan(Strict):
    schema_version: str = SCHEMA_VERSION
    plan_id: str
    version: int = 1
    project: str
    sprint_plan_sha256: str
    settings_sha256: str | None = None
    sprint_index: int
    assignments: list[Assignment]
    unassigned: list[Unassigned]
    eligibility: dict[str, EligibilityVerdict] = {}
    workers: list[dict] = []                 # id, kind, capacity_hours, planned_hours
    solver_engine: Literal["timefold", "local_cpsat"] = "timefold"
    solver_status: str = ""
    solver_score: str = ""
    pins: dict[str, str] = {}
    vetoes: dict[str, list[str]] = {}
    block_ai: list[str] = []
    annotated: bool = False
    generated_at: datetime


# ============================================================================ Agent 4: infra
CheckTool = Literal["tofu_fmt", "tofu_validate", "tofu_test", "tflint", "trivy", "checkov", "conftest",
                    "infracost", "actionlint", "helm_lint", "kubeconform", "gitleaks"]
Env = Literal["dev", "qa", "stg", "prod"]
Need = Literal["k8s_workload", "ecs_service", "public_endpoint", "postgres", "mysql", "redis", "queue", "object_storage",
               "container_registry", "cdn", "external"]


class Finding(Strict):
    rule_id: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    file: str | None = None
    message: str


CheckOutcome = Literal["passed", "findings", "tool_unavailable", "skipped", "timeout", "parse_error", "execution_error"]


class CheckResult(Strict):
    tool: CheckTool
    passed: bool
    skipped: bool = False    # tool unavailable here; never counted as passed
    summary: str
    findings: list[Finding] = []
    # What actually happened (sandbox.py). Optional so checks.json files written before it still load.
    outcome: CheckOutcome | None = None


class SecretRef(Strict):
    name: str
    store: Literal["aws_secrets_manager", "azure_key_vault", "gcp_secret_manager", "vault", "github_actions"]
    path: str


class InfraIntentComponent(Strict):
    component_id: str
    name: str
    kind: Literal["service", "frontend", "worker", "database", "cache", "queue", "object_storage", "cdn",
                  "external_api", "other"]
    needs: list[Need]
    size_class: Literal["small", "medium", "large"] = "small"
    public_endpoint: bool = False
    exposes_http: bool = False
    data_classification: Literal["public", "internal", "confidential", "restricted"] = "internal"
    runtime: str | None = None
    repo: str | None = None
    depends_on: list[str] = []
    secrets: list[str] = []   # extra secret env vars it needs (e.g. EMAIL_PROVIDER_API_KEY); references only
    source: str = ""          # where in architecture.md this component is described


class InfraIntent(Strict):
    cloud: Literal["aws", "azure", "gcp"]
    regions: list[str] = Field(min_length=1)
    environments: list[Env] = Field(default=["dev", "qa", "stg", "prod"], min_length=1)
    deploy_target: Literal["kubernetes", "ecs_fargate", "serverless", "vm"] = "kubernetes"
    components: list[InfraIntentComponent]
    slos: dict[str, str] = {}
    monthly_budget_usd: float | None = None
    notes: list[str] = []

    @model_validator(mode="after")
    def _unique_components(self):
        ids = [c.component_id for c in self.components]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("components must have unique IDs and must not be empty")
        if len(set(self.environments)) != len(self.environments) or len(set(self.regions)) != len(self.regions):
            raise ValueError("environments and regions must be unique")
        if any(not r or not all(ch.isalnum() or ch == '-' for ch in r) for r in self.regions):
            raise ValueError("invalid region")
        return self


class ManifestFile(Strict):
    path: str                                  # relative to infra/ (repo/... or ci/<owner__repo>/...)
    sha256: str
    origin: Literal["template", "module_call", "generated", "agent_edited"]
    template_ref: str | None = None
    rendered_sha256: str                       # what the catalog produced, to show agent edits


class InfraManifest(Strict):
    schema_version: str = SCHEMA_VERSION
    project: str
    intent_sha256: str
    source_hashes: dict[str, str] = {}
    infra_repo: str
    environments: list[Env]
    files: list[ManifestFile]
    ci_repos: list[str] = []
    secrets_refs: list[SecretRef] = []
    stateful_resources: list[str] = []
    gaps: list[str] = []
    checks_passed: bool = False
    checks_skipped: list[str] = []
    # Whether every check ran to completion here; checks_passed still counts skipped checks as not failing.
    validation_complete: bool | None = None
    checks_incomplete: list[str] = []          # "tool: outcome" for each check that did not complete
    risk_score: int = Field(default=0, ge=0, le=100)
    risk_reasons: list[str] = []
    generated_at: datetime
