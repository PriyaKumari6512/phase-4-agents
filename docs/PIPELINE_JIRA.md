# Run the complete pipeline and publish to Jira

Keep your existing model credentials and Jira email/API token in the repository's `.env`.
Add the following values there. Replace the project folder and Jira destination with your actual values:

```dotenv
PHASE4_PROJECT_NAME=clinic-test-2
PHASE4_TRACKER=jira
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_PROJECT_KEY=YOURPROJECT
JIRA_BOARD_ID=123
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-existing-api-token
PHASE4_AUTO_APPROVE_FOR_TESTING=true
AGENT_ENGINE_PERF_MODE=publication
```

Then run from the repository root:

```bash
uv sync
uv run agent-engine pipeline
```

Approved stories are read from this Jira project before any generation (read-only; see "phase4/stories.json" in
[PHASE4.md](PHASE4.md) for `JIRA_STORY_JQL` and the related settings). Task Breakdown also needs the human approvals
of G3A and G3B (`agent-engine gate G3A|G3B ...`); `PHASE4_AUTO_APPROVE_FOR_TESTING` never approves those.

`JIRA_EMAIL` must be the account that owns `JIRA_API_TOKEN` on `JIRA_BASE_URL`.

`PHASE4_PROJECT_NAME` identifies an existing directory under `outputs/`. Its inputs must include
`prd.md`, `architecture.md`, and `phase4/project.json`. The project display name can differ from its folder name.
Existing project content (team, requirements, repositories, calendar and infrastructure choices) remains input data.
You do not need to edit project.json to select Jira: ENV overrides take precedence in the typed settings loader,
without rewriting that input file or invalidating its recorded byte hashes.

Jira credentials authenticate the client. They do not select the Jira site, project or board.
`PHASE4_TRACKER=jira` selects the destination; the other three Jira values identify it.
The board must support sprints (Scrum). This adapter targets Jira Cloud REST v3 and Agile REST 1.0.

## What runs automatically

The `pipeline` command enables full publication, parallel Task Breakdown/Infrastructure execution,
diagnostics, and two independent IaC scanner workers by default. Explicit ENV settings take precedence.
It follows stage dependencies, validates and reviews output, handles approval gates according to the flag,
and invokes infrastructure, backlog, sprint and assignment publication in dependency order.
Existing narrower CLI commands keep their previous defaults.

`PHASE4_AUTO_APPROVE_FOR_TESTING=true` bypasses manual gate approval **only after a successful current automated
review**. It permits those clearly marked test approvals to authorize publication. Jira writes are real;
this is not a dry run. An existing approval made by the old `--test-approve` command is not automatically trusted:
it is renewed after current review. Previously generated files without review evidence are reviewed in place.

Set this flag to `false` for human approval gates. Its code default is false. Genuine validation failures,
missing permissions or inputs, infeasible plans, rejected gates, and unresolved human decisions still stop the
affected path. They are never converted into successful checks. Completed outputs remain available for recovery.
An automated test approval is never represented as a human sign-off, and switching the flag off prevents it
from authorizing later publication.

If your `.env` explicitly sets `AGENT_ENGINE_PERF_MODE=generation`, change it to `publication`; the single command
does not silently override that publication guard. `AGENT_ENGINE_PERF=0` remains an explicit diagnostics opt-out.
It does not disable model validation.

Infrastructure/CI pull request publication still uses the existing configuration:
`PHASE4_PR_MODE=github` plus `GITHUB_TOKEN` publishes to the repositories in your project input;
`PHASE4_PR_MODE=local` (the existing default) writes reviewable PR bundles locally. Jira publication is independent
of that setting. Live AI code dispatch still requires the existing provider credentials, CI readiness evidence,
predecessor completion, planned start time and worker capacity. Automatic approval does not merge generated
GitHub PRs or waive those requirements. Services such as calendars, Timefold and tracing require their existing
credentials/setup if your project uses them; they are not made available merely by turning on a flag.

## Jira settings

All new operational settings are read at runtime in `src/agent_engine/phase4/settings.py`.
No per-stage command arguments are needed.

| ENV setting | Default | Purpose |
| --- | --- | --- |
| `JIRA_PUBLISH_CONCURRENCY` | `4` | Maximum independent Jira workers (1–16). Set 1 for serial publishing. |
| `JIRA_MIN_WRITE_INTERVAL_SECONDS` | `0.25` | Minimum spacing between request starts across workers; not a guaranteed throughput. |
| `JIRA_TIMEOUT_SECONDS` | `30` | HTTP timeout in seconds. |
| `JIRA_MAX_RETRIES` | `5` | Maximum bounded retries for supported HTTP errors. |
| `PHASE4_SPRINT_INDEX` | `1` | Sprint selected for allocation. |
| `PHASE4_WRITE_STORY_POINTS` | `never` | `if_empty` writes the backlog's story points onto approved Jira stories that have none (never overwrites). |
| `PHASE4_PUBLISH` | `true` | Publish after the stage/gate chain completes. |
| `PHASE4_PARALLEL_STAGES` | `true` | Run the verified independent first stages in isolated workspaces. |
| `PHASE4_IAC_CHECK_CONCURRENCY` | `2` on `pipeline` | Independent scanner workers; 1–4. |

The following values are needed only when your existing project/Jira setup needs them:

```dotenv
# Keys are member_id values already in your project, not display names or emails.
# Omit this if project.json already contains correct Jira account IDs.
JIRA_ACCOUNT_MAP='{"m-alice":"actual-jira-account-id","m-bob":"another-account-id"}'

# For localized/nonstandard type names; IDs must belong to the selected project.
# task is the Jira subtask type: pipeline tasks are children of stories.
JIRA_ISSUE_TYPE_IDS='{"epic":"10000","story":"10001","task":"10002"}'

# Required custom Jira create fields, keyed by pipeline level. Values use Jira REST field formats.
JIRA_CREATE_FIELDS='{"story":{"customfield_12345":{"id":"required-option-id"}}}'

# Optional override when board configuration does not identify the desired points field.
JIRA_STORY_POINTS_FIELD_ID=customfield_10016
```

Before generation, a read-only Jira preflight checks authentication, project/board access, relevant project
permissions, issue types, estimation field, additional required create fields, and assignability of configured team accounts.
It creates no test issues.
It cannot prove every future request will succeed: permissions or user availability can change,
and custom workflows or field contexts can add further constraints. Use an account permitted to create/edit/link
issues, assign the configured users, and manage sprints in the target project/board.

## Approved stories stay as they are

When the backlog was built from approved stories imported from this Jira project, publishing creates only the
tasks, as **sub-tasks of the existing stories** (labels `phase4` and `discipline-fe|be|db|devops|qa`, the estimate
at the top of the description because sub-task screens often have no time-tracking field), plus "blocks" links
between tasks. Epics and stories are never created, edited, linked or closed; their ids are recorded so sprint
publication can move them. Publishing refuses when the stories were imported from a different project.

## What publishes concurrently

- Epics publish concurrently, then stories, then tasks. Each parent wave must finish before child publication.
- Dependency links publish after issues exist; existing links are read back before creating missing ones.
- Independent sprint publications run concurrently. Conflicting story destinations are rejected before sprint writes.
- Sprints that already exist on the board are reused, not duplicated: same start date, an active sprint covering
  the planned start, same name, then undated future sprints (such as the one Jira creates with a new board) in
  order. Only an adopted sprint's empty dates and goal are filled; nothing is renamed or re-dated.
- Human assignments/comments for different tasks run concurrently. Changed Jira account mappings trigger reassignment.
- Local and other tracker adapters keep their serial execution. AI dispatch remains ordered because worker limits,
  predecessor checks and start-time constraints are shared.

The Jira HTTP client and publishing ledger are shared safely within each publishing phase. Every acknowledged
issue mapping is persisted atomically; workers finish before the client closes. The four publishing phases are
ordered because later phases consume earlier mappings. Increasing workers cannot bypass Jira's shared throttle
or server rate limits, so it does not imply a fourfold speedup.

## Recovery and result locations

Run the same command after fixing a failure. The existing durable stage recovery resumes compatible saved
generation/review work. Successful issue IDs remain in `outputs/<project>/publish/external-ids.json`.
Publisher summaries are written under `outputs/<project>/publish/` when that phase completes.
The ledger remains the recovery evidence if a phase fails before its summary is written.

Definite HTTP rejections such as 400/401/403/422/429 clear their pending create/comment/sprint record so a corrected
request can be attempted later. Jira POST retries are enabled for rejected 429 responses only; an ambiguous 5xx or
transport failure is not automatically replayed. Retry-After is respected with a shared cooldown. If the server
requires over 120 seconds, the call returns an error rather than retrying too early or waiting indefinitely.
After an ambiguous issue create, the existing marker search can adopt an issue that reached Jira. If a pending
operation still cannot be reconciled, publication stops instead of risking duplicates. This is durable recovery,
not a promise of exactly-once remote delivery.

The affected offline tests use fake tracker responses and validate concurrency, ordering, recovery, configuration,
and approval policy. They are not evidence of a successful live Jira/API/LLM run. Verify those integrations with
your actual environment using the single command above.
