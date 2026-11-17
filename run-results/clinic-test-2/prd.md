# TaskFlow — Product Requirements Document

## 1. Overview

Small teams (5–30 people) track their work across spreadsheets, chat threads and email. Work gets lost, nobody
knows what is due, and managers cannot see progress without asking. TaskFlow is a web app where a team plans and
tracks tasks on a shared board, gets notified about the work that matters to them, and sees progress at a glance.
Pilot customers need a beta by mid-December 2026.

## 2. Goals and non-goals

Goals:
- G1: A team can move all its day-to-day task tracking into TaskFlow within one week of signing up.
- G2: No assigned task is missed: assignees learn about new assignments within minutes.
- G3: Managers can answer "are we on track?" without a status meeting.

Non-goals (this release): mobile apps, time tracking, integrations with other trackers, billing.

## 3. Users and personas

- **Team member**: creates and updates tasks, comments, needs to know what is assigned to them and what is due.
- **Team manager**: plans the board, assigns work, needs progress and exportable data.

## 4. User stories

- **US-1** (Must): As a team member, I want to create tasks with a title, description, due date and assignee so
  that all work is in one place.
  - Given I am on a board, When I create a task with a title, Then it appears in the "To do" column.
  - Given a task, When I set a due date and an assignee, Then both are shown on the task card.
- **US-2** (Must): As a team member, I want to move tasks across the columns To do, Doing and Done so that
  everyone sees the current state.
  - Given a task in "To do", When I drag it to "Doing", Then all board viewers see it in "Doing" within 5 seconds.
- **US-3** (Should): As a team member, I want to comment on tasks and mention teammates so that discussions stay
  with the work.
  - Given a task, When I post a comment mentioning @alice, Then Alice receives a notification.
- **US-4** (Must): As a team member, I want to search tasks so that I can find any task quickly.
  - Given 10,000 tasks, When I search by a word in the title, Then results appear in under 300 ms (p95).
- **US-5** (Must): As an assignee, I want an email when a task is assigned to me so that I never miss new work.
  - Given a task, When it is assigned to me, Then I receive one email within 1 minute.
- **US-6** (Should): As a team member, I want a daily digest of tasks due tomorrow so that I can plan my day.
  - Given tasks due tomorrow assigned to me, When the daily digest runs at 08:00 in my time zone, Then I receive
    one email listing them.
- **US-7** (Could): As a team member, I want to choose which notifications I get and how often, so that I am not
  overwhelmed.
- **US-8** (Should): As a manager, I want a burndown chart per board so that I can see whether we will finish on
  time.
  - Given a board with a sprint, When I open the report, Then I see remaining points per day for the sprint.
- **US-9** (Could): As a manager, I want to export board data as CSV so that I can analyse it elsewhere.
  - Given a board, When I click Export, Then I download a CSV with one row per task and all task fields.

## 5. Functional requirements

- **FR-1**: Users can create, view, edit and delete tasks with title, description, due date and assignee. (US-1)
- **FR-2**: Boards have three columns (To do, Doing, Done); users move tasks between them and every viewer sees
  the change within 5 seconds. (US-2)
- **FR-3**: Users can comment on tasks and mention teammates with @name; a mention notifies the teammate. (US-3)
- **FR-4**: Full-text search over task titles and descriptions of the user's boards. (US-4)
- **FR-5**: An email is sent to the assignee within 1 minute of an assignment. (US-5)
- **FR-6**: A daily digest email of tasks due tomorrow, sent at 08:00 in the user's time zone. (US-6)
- **FR-7**: Per-user notification preferences: channel and frequency. (US-7)
- **FR-8**: Burndown chart per board showing remaining story points per day of the current sprint. (US-8)
- **FR-9**: CSV export of a board: one row per task with all task fields. (US-9)

## 6. Non-functional requirements

- **NFR-1** Performance: search p95 under 300 ms for 10,000 tasks; board updates visible within 5 seconds.
- **NFR-2** Availability: 99.5% monthly for the web app and API.
- **NFR-3** Security & privacy: only board members can see a board's tasks; task data is confidential.
- **NFR-4** Accessibility: board and task forms usable with keyboard only (WCAG 2.1 AA).

## 7. Assumptions and open questions

- Assumption: email is the only notification channel in this release.
- Open question: which channels besides email should FR-7 offer, and which frequencies (immediate, hourly,
  daily)? The client has not decided.
- Open question: is "Done" the only column that counts toward the burndown?
