# Agentic Bug Triage and Resolution - Final Implementation Plan and Record

## 1. Goal

The implemented system responds to qualified GitHub bug issues, gathers bounded
repository context, reproduces the reported behavior, diagnoses and classifies
the root cause, repairs safe defects, validates the unchanged reproduction, and
either opens a reviewable pull request or requests a decision from a maintainer.

The delivered submission is aligned to the assignment's evaluation criteria:

1. End-to-end functionality
2. Appropriate autonomy
3. Useful human-in-the-loop controls
4. Measurable engineering and business outcomes
5. Effective context and memory management
6. Developer-friendly output and operational taste

## 2. Decisions

### Target application

The target application is
[`TonyMckes/conduit-realworld-example-app`](https://github.com/TonyMckes/conduit-realworld-example-app),
imported under `target-app/` with its MIT license and upstream attribution.

Why:

- It is an established open-source RealWorld application rather than a toy built for this task.
- It contains a React frontend, Express backend, and Sequelize data layer.
- SQLite is the zero-provisioning development and demonstration database;
  PostgreSQL remains supported through environment configuration.
- It is materially smaller and faster to understand than Vikunja, improving the chance of a polished 48-hour submission.
- Its JavaScript stack allows one test/tooling ecosystem across the target application while keeping the agent implementation separate.

### Agent implementation

The agent uses Python, the Anthropic SDK, Pydantic models, and an explicit typed
state machine rather than a large orchestration framework.

Why:

- State transitions, retry limits, autonomy gates, and escalation decisions remain visible and testable.
- The implementation has fewer framework-specific abstractions for reviewers to learn.
- Model usage and token cost can be controlled at every call.
- The architecture demonstrates engineering judgment rather than delegating core behavior to a framework.

### Model policy

- **Haiku:** default model for issue parsing, repository summarization, test interpretation, patch review, development runs, and automated tests.
- **Sonnet:** escalation for ambiguous root-cause analysis, failed repair attempts, cross-layer bugs, or low-confidence plans.
- **Opus:** disabled by default and available only for explicitly defined exceptional escalation.
- Never store the API key in the repository. Read it from `ANTHROPIC_API_KEY` through local environment configuration or GitHub Actions secrets.

### Scope guardrails and non-goals

- Build one explicit agent workflow, not a swarm of collaborating agents.
- Do not add Slack unless every required GitHub workflow, test, metric, and submission artifact is complete.
- Do not add a vector database; SQLite FTS5 is sufficient for the demonstrated memory requirements.
- Do not allow the agent to merge its own pull requests.
- Do not optimize for broad autonomous coding. Optimize for reliable, bounded repair of reproducible bugs.
- Prefer deterministic repository tools and tests over model calls whenever they can answer the question.

## 3. Delivered Architecture

```text
GitHub issue receives a trusted action label
          |
          v
GitHub Actions workflow
          |
          v
Python agent orchestrator
  1. Intake and normalize issue
  2. Prepare isolated workspace
  3. Inspect repository context
  4. Reproduce the bug
  5. Diagnose root cause
  6. Classify severity/confidence/risk
  7. Select autonomy path
  8. Plan and implement repair
  9. Run targeted and regression tests
 10. Review patch and evidence
 11. Open PR or request human input
          |
          +--> SQLite run/memory/metrics store
          +--> GitHub comments, labels, checks, and PR
```

### Core modules

| Module | Responsibility |
|---|---|
| `orchestrator` | Typed workflow states, transitions, bounded retries, and terminal outcomes |
| `github` | Issue intake, comments, labels, branches, checks, and pull requests |
| `workspace` | Isolated checkout/worktree creation and command execution |
| `context` | Repository map, deterministic search, file selection, and prompt context assembly |
| `reproduction` | Convert issue evidence into reproducible commands or tests |
| `diagnosis` | Root-cause hypothesis, affected surface, and confidence assessment |
| `risk` | Severity, blast radius, security/data risk, and autonomy decision |
| `repair` | Patch planning, editing, targeted testing, and bounded iteration |
| `models` | Haiku-first routing, escalation policy, structured responses, and budget enforcement |
| `memory` | Persist and retrieve prior bug symptoms, code areas, fixes, tests, and outcomes |
| `metrics` | Timing, success, cost, intervention, retries, and outcome reporting |

All model responses that drive actions use validated structured schemas.
Invalid responses produce a visible failed state or bounded retry rather than a
silent fallback.

### Agent tool contracts

The implementation exposes a small, auditable tool surface rather than placing
the repository into prompts:

| Tool | Contract |
|---|---|
| `search_code(query, paths?, limit?)` | Search tracked source and test files while excluding generated/build/vendor content |
| `read_file(path, start_line, end_line)` | Read a bounded range from an allowed repository file |
| `run_command(command, timeout)` | Run an allowlisted, non-interactive command in the isolated workspace |
| `run_tests(targets)` | Run the smallest relevant existing test targets and capture structured results |
| `git_diff()` | Return the current patch and changed-file summary |
| `apply_patch(patch)` | Apply a bounded patch only inside the isolated workspace |
| `create_pr(metadata)` | Create a GitHub pull request after policy and validation gates pass |

The operating instruction is: search first, read only relevant ranges, edit narrowly, inspect the diff, and prove the repair with tests.

### Compact stage state

The agent persists a structured state object instead of repeatedly resending
the full conversation:

```json
{
  "run_id": "...",
  "issue": {},
  "reproduction": null,
  "suspected_files": [],
  "root_cause": null,
  "severity": null,
  "risk": null,
  "confidence": 0,
  "repair_attempt": 0,
  "validation": null,
  "budget": {},
  "human_action": "agent:triage"
}
```

Each model call receives only the state fields, code ranges, command summaries, and prior memories required for that stage. Full logs remain artifacts and are summarized once rather than repeatedly entering model context.

## 4. Agent Workflow

### 4.1 Intake

- A trusted collaborator with Triage-or-higher permission starts a run by
  applying `agent:triage`.
- After escalation, one-shot labels select `agent:retry`,
  `agent:investigation-only`, `agent:approve-draft`, or `agent:declined`.
- Capture title, description, reproduction steps, expected behavior, actual behavior, logs, environment, and attachments.
- Validate minimum information and post a concise request for missing blocking evidence.
- Add a run identifier and `agent:running` label to prevent duplicate work.

### 4.2 Repository understanding

- Build a deterministic repository map from files, manifests, test configuration, routes, components, database models, and recent relevant changes.
- Use inexpensive lexical search and dependency/import relationships before sending content to a model.
- Provide the model only the smallest relevant code slices, test files, configuration, and prior memories.
- Record why each file entered the context so retrieval behavior is explainable.

### 4.3 Reproduction

- Use the target application's local SQLite configuration, with no provisioned
  database service required for the demonstrated bugs.
- Accept only exact allowlisted npm/Vitest reproduction commands for test files
  under `target-app`.
- Translate issue steps into a failing automated test whenever feasible.
- Prefer a test that fails on the buggy revision and passes after the repair.
- If automated reproduction is impossible, capture command output, logs, screenshots, or API evidence and lower confidence.
- Do not proceed to autonomous repair when the agent cannot reproduce the issue unless a low-risk static defect is exceptionally clear.
- Persist the exact reproduction command, inputs, environment assumptions, expected result, observed result, and relevant output fingerprint.

### 4.4 Diagnosis and triage

Produce a structured triage result containing:

- Reproduction status and evidence
- Root-cause hypothesis and supporting code locations
- Severity: critical, high, medium, or low
- User and business impact
- Affected frontend/backend/database surfaces
- Confidence score
- Proposed owner/labels
- Change risk and recommended autonomy level

Post a concise GitHub issue comment with the exact command, bounded observed
output, expected behavior, output fingerprint, diagnosis, supporting files,
safety flags, cost, workflow/artifact link, and next actions rather than raw
chain-of-thought or unbounded logs.

### 4.5 Autonomy and human-in-the-loop

| Risk/confidence | Behavior |
|---|---|
| Low risk and high confidence | Implement, test, and open a ready-for-review PR |
| Medium risk or medium confidence | Stop before editing and request explicit approval for one draft repair |
| High risk, low confidence, security-sensitive, migration-related, or destructive | Stop before editing and request human approval with options |
| Reproduction or validation fails after bounded retries | Escalate with evidence, hypotheses tried, and the smallest useful next action |

Escalation comments present decision labels for retry, read-only investigation,
bounded draft approval, or decline. `agent:investigation-only` never edits.
`agent:declined` records the decision without an Anthropic call or target-app
command. Draft approval cannot override failed reproduction, high risk,
security sensitivity, destructive behavior, or migration requirements, and any
approved repair is opened as a GitHub draft PR. The agent never merges its own
PR.

### 4.6 Repair

- Create a dedicated branch tied to the issue and run ID.
- Generate a minimal repair plan before editing.
- Change only files supported by the diagnosis.
- Add or update a regression test.
- Run the smallest relevant tests first, then the required broader checks.
- Rerun the exact pre-fix reproduction after the patch; changing the reproduction requires a recorded explanation and human-visible evidence.
- Allow a small bounded number of repair iterations.
- Reject patches that exceed configured file/change limits without human approval.

### 4.7 Pull request

Generated pull requests include:

- Linked issue
- Reproduction evidence
- Root cause
- Repair summary
- Regression test
- Commands and results
- Risk assessment
- Model/cost summary without secrets
- Human review focus
- Rollback guidance where applicable

## 5. Context and Memory Strategy

Use a local SQLite database with FTS5 rather than a paid vector service.

### Short-term run context

- Current issue and normalized evidence
- Selected repository files and relevance reasons
- Commands, outputs, hypotheses, edits, and tests
- State transitions, retry counts, and token/cost budget

### Long-term episodic memory

For completed local runs, the system stores:

- Symptom and normalized issue summary
- Reproduction method
- Root cause and affected code areas
- Successful and failed hypotheses
- Patch summary and regression tests
- Final outcome, review feedback, and time/cost metrics

Before diagnosing a new issue, the agent retrieves prior memories using FTS5
over symptoms, components, errors, routes, and file paths. Prior knowledge is
supporting context and is revalidated against the current revision. Hosted
GitHub jobs currently use ephemeral SQLite; durable hosted memory is part of
the one-month roadmap.

### Demonstrating learning

The frontend demonstration retrieved memory episode `1` from the earlier
backend run while still searching and validating the current source. The
evidence records:

- Which prior memory was retrieved
- How it reduced context discovery or model calls
- Whether time-to-diagnosis and cost improved
- Why the prior conclusion was revalidated rather than blindly trusted

## 6. Model Routing and Cost Control

### Default routing

Each model task has:

- A purpose-specific prompt
- A strict response schema
- A maximum token allowance
- A retry limit
- A permitted model tier

### Escalation triggers

Escalate from Haiku to Sonnet only when one or more are true:

- Root-cause confidence remains below the configured threshold
- The bug crosses frontend/backend/database boundaries
- Two materially different hypotheses remain plausible
- A repair attempt fails and new reasoning is required
- The proposed patch exceeds the low-risk change boundary

Opus requires an explicit configuration flag and a recorded reason.

### Budget controls

- Per-run dollar/token budget
- Per-stage call and token limits
- Cached deterministic repository summaries keyed by commit SHA
- No repeated model call with unchanged inputs
- Truncated command output with full logs stored as artifacts
- Run-level model/cost metrics included in the final report
- Immediate stop and escalation when the budget is exhausted

### Initial bounded-autonomy limits

Store these as configurable defaults rather than scattering constants through the code:

| Limit | Initial default |
|---|---:|
| Code searches per diagnosis cycle | 8 |
| Distinct source/test files read per diagnosis cycle | 12 |
| Repair attempts | 2 |
| Sonnet escalations per run | 1 |
| Opus escalations per run | 0 |
| Input context per model call | 20,000 tokens |
| Output per model call | 2,000 tokens |
| Changed files before approval is required | 6 |
| Changed lines before approval is required | 400 |
| Hosted model cost per run | $0.25 |

Model-generated edits are restricted to target-application implementation
files. Tests, package manifests, lockfiles, workflows, and test configuration
cannot be modified by the model. The hosted report records every model tier,
token count, cost, attempt, selected context, changed file, human action, and
publication outcome.

## 7. GitHub Integration

Use this repository, `ravit-dennis/AgenticBugTriageAndResolution`, for the submission, issue tracking, seeded bug demonstrations, and generated repair PRs.

Delivered GitHub assets and controls:

- Issue-label-triggered GitHub Actions workflow
- Trusted maintainer activation through GitHub label permissions
- Running, resolved, failed, escalation, retry, investigation, approval, and
  decline labels
- Stable issue branches and linked pull requests
- Evidence-rich marker-based issue comments
- Seven-day sanitized run-report artifacts
- Exact trusted base-branch allowlist for `main` and seeded demo branches
- No persisted checkout credentials, force-pushes, or self-merge
- Secret-free test subprocesses and isolated Git global/system configuration
  during authenticated pushes
- Safe handling for existing branches, existing PRs, partial publication, and
  duplicate delivery

## 8. Seeded Demonstration Bugs

The repository contains two realistic, independently reproducible localized
defects and one cross-layer HITL scenario:

### Backend bug

The backend pagination bug applies the requested offset incorrectly. It is
reproduced by `backend/helper/pagination.test.js`, repaired in one source file,
and validated by the unchanged reproduction plus the complete target-app suite.

### Frontend bug

The frontend settings form fails to restore submission state after a rejected
request. It is reproduced by the component test, repaired with a localized
state reset, and validated by the unchanged reproduction and full suite.

The primary HITL issue reproduces a frontend/backend pagination contract
mismatch. The agent correctly stops before editing because the repair is
cross-layer, presents four explicit maintainer choices, and resumes only after
`agent:approve-draft`. The approved repair uses one Sonnet escalation, passes
the unchanged reproduction and full suite, and opens a draft PR. A separate
production-only destructive scenario proves that hard safety blockers cannot
be overridden. Repeatable seeded and replay branches preserve all scenarios.

## 9. Testing Strategy

### Agent unit tests

- 85 Python tests cover workflow transitions, terminal outcomes, model routing,
  budget enforcement, response validation, context limits, memory, command and
  edit policy, GitHub integration, publication safety, and HITL decisions.
- Approval tests prove medium-risk work pauses before editing, approved work
  remains draft-only, investigation never repairs, decline avoids model spend,
  and hard safety blockers cannot be overridden.

### Agent integration tests

- Mock Anthropic responses through complete workflow paths
- Mock GitHub issue/comment/branch/PR interactions
- Temporary Git repositories for patch and branch behavior
- Successful repair, escalation, failed reproduction, failed tests, and exhausted-budget scenarios

### Target application tests

- 15 frontend and backend tests pass.
- Each seeded defect has deterministic failing-before/passing-after evidence.
- The frontend production build passes.

### End-to-end tests

- Hosted backend issue to validated PR
- Hosted frontend issue to validated PR
- Hosted high-risk issue to evidence-rich human escalation
- Hosted `agent:retry` decision with zero changed files and no branch
- Hosted cross-layer stop, explicit approval, Sonnet repair, and draft PR
- Duplicate and existing-PR behavior without duplicate publication
- Memory from bug 1 retrieved and measured during bug 2

## 10. Measurement

Track per run:

| Metric | Purpose |
|---|---|
| Time to first triage | Measures reduction in engineer waiting time |
| Time to reproduced failure | Measures issue quality and agent effectiveness |
| Time to diagnosis | Measures context retrieval quality |
| Time to validated PR | Primary cycle-time outcome |
| Autonomous completion rate | Measures useful autonomy |
| Human intervention rate | Measures escalation quality |
| Reproduction success rate | Leading indicator of repair reliability |
| First-patch success rate | Measures diagnosis/repair quality |
| Test pass and regression escape rate | Measures safety |
| Model calls, tokens, and estimated cost | Measures economic efficiency |
| Context files/tokens and memory hits | Measures context/memory effectiveness |
| Developer acceptance/rework | Measures whether output is genuinely useful |

Primary business metric: reduce median engineer time spent from bug intake to a validated repair candidate without increasing escaped regressions.

## 11. Delivery Record

### Original 48-hour allocation and outcome

| Timebox | Outcome |
|---|---|
| Hours 0-6 | Imported and ran the licensed target app; selected deterministic backend and frontend defects |
| Hours 6-16 | Implemented typed state, safe tools, SQLite persistence, Anthropic adapter, and core tests |
| Hours 16-26 | Completed the backend failing-before/passing-after repair loop |
| Hours 26-34 | Completed the frontend loop and demonstrated memory retrieval |
| Hours 34-40 | Added and hardened GitHub issue-to-PR automation, metrics, budgets, and HITL controls |
| Hours 40-48 | Completed hosted demonstrations, CI, security review, runbook, architecture, write-up, and video script |

All six phases are complete. Optional Slack integration was intentionally
excluded so effort remained focused on the required GitHub workflow,
reproducibility, safety, measurement, and demonstration quality.

## 12. Evaluation Coverage

| Evaluation area | Delivered evidence |
|---|---|
| Functionality | Final backend issue #33 produced PR #36; final frontend issue #34 produced PR #37 |
| Autonomy | Reproduction-first low-risk repair, two-attempt limit, patch limits, and no self-merge |
| Human-in-the-loop | Issue #35 shows stop-before-edit evidence, explicit approval, Haiku-to-Sonnet continuation, and draft PR #38; issue #6 proves non-overridable safety gates |
| Measurement | Sanitized reports record elapsed time, model tiers, tokens, cost, attempts, context, memory, actions, and publication |
| Context and memory | Bounded search/read context and retrieval of local memory episode `1` during the frontend run |
| Taste | Localized one-file repairs, exact validation evidence, concise GitHub UX, clear recovery states, and $0.25 run cap |

## 13. Measured Final Evidence

| Hosted issue | Outcome | Elapsed | Input | Output | Cost | Publication |
|---|---|---:|---:|---:|---:|---|
| `ravit-dennis/AgenticBugTriageAndResolution#33` | Backend repair | 18.467s | 6,083 | 481 | $0.008488 | PR #36 |
| `ravit-dennis/AgenticBugTriageAndResolution#34` | Frontend repair | 22.222s | 10,626 | 690 | $0.014076 | PR #37 |
| `ravit-dennis/AgenticBugTriageAndResolution#35` | Approval requested | 9.527s | 3,451 | 279 | $0.004846 | No branch or PR |
| `ravit-dennis/AgenticBugTriageAndResolution#35` | Approved Sonnet repair | 23.684s | 7,326 | 953 | $0.019317 | Draft PR #38 |

The two localized repairs used Haiku only, required one repair attempt, changed
one implementation file each, and passed the unchanged reproduction plus the
complete target-app suite. The approved cross-layer repair used Haiku and one
Sonnet escalation, changed one implementation file, passed both validation
levels, and remained a draft PR. The final repository passes 85 Python tests,
all target-app tests, and the frontend production build. Total measured
Anthropic spend, including development, connectivity, and all refreshed hosted
runs, is $0.237498.

## 14. Definition of Done

- [x] A fresh GitHub bug issue can trigger the workflow.
- [x] The agent can reproduce, diagnose, classify, and route the issue.
- [x] A safe bug produces a tested PR with a regression test.
- [x] A risky or uncertain bug stops at a clear human decision point.
- [x] Backend and frontend seeded bugs are demonstrated end to end.
- [x] Haiku is the default and escalation/cost decisions are visible.
- [x] Context and memory inform the second run with measured evidence.
- [x] Tests cover success, failure, retry, budget, idempotency, publication
  safety, and all HITL paths.
- [x] Setup and replay instructions work from a clean checkout.
- [x] The repository contains the required submission brief, architecture,
  results, runbook, and video walkthrough.

## 15. One-Month Product Roadmap

### Installable GitHub App

- Move execution outside the target repository into an installable GitHub App.
- Use least-privilege repository permissions and short-lived installation
  tokens instead of personal access tokens.
- Add a hosted control plane for webhook verification, maintainer
  authorization, queues, checks, quotas, auditing, and tenant isolation.

### Safe support for many repositories

- Discover languages, package managers, test frameworks, services, ownership,
  and application boundaries during onboarding.
- Require a reviewed repository profile defining trusted setup, reproduction,
  test, and build commands; editable paths; required services; secrets; network
  policy; and risk rules.
- Add normalized stack adapters for Node.js, Python, Go, Java, and .NET.
- Pilot on a larger application such as Vikunja without assuming arbitrary
  repositories are safe to execute without onboarding.

### Isolated reproduction and validation

- Run every investigation in a fresh ephemeral container or short-lived VM
  created from a trusted base image.
- Start profile-declared dependencies such as PostgreSQL and Redis, including
  reviewed Docker Compose or dev-container definitions for multi-service apps.
- Enforce CPU, memory, timeout, filesystem, process, and network-egress limits.
- Inject only stage-specific short-lived secrets, retain sanitized evidence,
  and destroy the environment after every run.
- Keep GitHub credentials and the control plane outside untrusted target code.

### Durable production operation

- Replace ephemeral artifacts and local SQLite with tenant-isolated workflow,
  evidence, metrics, and versioned memory services.
- Combine lexical, symbol, dependency, ownership, and change-history retrieval.
- Add CODEOWNERS routing, branch protection, configurable approvals, deployment
  and rollback evidence, cost quotas, kill switches, and operational
  observability.
- Calibrate autonomy thresholds from accepted, edited, and rejected PRs in a
  controlled pilot and evaluate time, quality, security, and cost against a
  manual-triage cohort.
- Keep GitHub as the system of record; add Slack or Teams only as optional
  notification surfaces.
