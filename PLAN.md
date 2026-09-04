# Agentic Bug Triage and Resolution - Implementation Plan

## 1. Goal

Build a working agentic workflow that responds to GitHub bug issues, reproduces the reported behavior, finds the relevant code, diagnoses the root cause, classifies severity and risk, implements a safe fix, runs validation, and opens a pull request with evidence.

The submission will optimize for the evaluation criteria in the assignment:

1. End-to-end functionality
2. Appropriate autonomy
3. Useful human-in-the-loop controls
4. Measurable engineering and business outcomes
5. Effective context and memory management
6. Developer-friendly output and operational taste

## 2. Decisions

### Target application

Use [`TonyMckes/conduit-realworld-example-app`](https://github.com/TonyMckes/conduit-realworld-example-app) as the target application and import it into this repository under `target-app/`.

Why:

- It is an established open-source RealWorld application rather than a toy built for this task.
- It contains a React frontend, Express backend, Sequelize data layer, and PostgreSQL database.
- It is materially smaller and faster to understand than Vikunja, improving the chance of a polished 48-hour submission.
- Its JavaScript stack allows one test/tooling ecosystem across the target application while keeping the agent implementation separate.

Before importing it, confirm its license and preserve the upstream attribution and license files.

### Agent implementation

Use Python, the Anthropic SDK, Pydantic models, and an explicit typed state machine rather than a large orchestration framework.

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

## 3. Proposed Architecture

```text
GitHub issue opened/labeled
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

All model responses that drive actions will use validated structured schemas. Invalid responses will produce a visible failed state or bounded retry rather than a silent fallback.

### Agent tool contracts

Expose a small, auditable tool surface rather than placing the repository into prompts:

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

Persist a structured state object instead of repeatedly resending the full conversation:

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
  "budget": {}
}
```

Each model call receives only the state fields, code ranges, command summaries, and prior memories required for that stage. Full logs remain artifacts and are summarized once rather than repeatedly entering model context.

## 4. Agent Workflow

### 4.1 Intake

- Trigger only for issues labeled `agent:triage` or created from the provided bug template.
- Capture title, description, reproduction steps, expected behavior, actual behavior, logs, environment, and attachments.
- Validate minimum information and post a concise request for missing blocking evidence.
- Add a run identifier and `agent:running` label to prevent duplicate work.

### 4.2 Repository understanding

- Build a deterministic repository map from files, manifests, test configuration, routes, components, database models, and recent relevant changes.
- Use inexpensive lexical search and dependency/import relationships before sending content to a model.
- Provide the model only the smallest relevant code slices, test files, configuration, and prior memories.
- Record why each file entered the context so retrieval behavior is explainable.

### 4.3 Reproduction

- Start the target app and required PostgreSQL service through Docker Compose.
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

Post a concise GitHub issue comment with evidence and next action rather than raw chain-of-thought or noisy logs.

### 4.5 Autonomy and human-in-the-loop

| Risk/confidence | Behavior |
|---|---|
| Low risk and high confidence | Implement, test, and open a ready-for-review PR |
| Medium risk or medium confidence | Stop before editing and request explicit approval for one draft repair |
| High risk, low confidence, security-sensitive, migration-related, or destructive | Stop before editing and request human approval with options |
| Reproduction or validation fails after bounded retries | Escalate with evidence, hypotheses tried, and the smallest useful next action |

Escalation comments present decision labels for retry, read-only investigation,
bounded draft approval, or decline. Draft approval cannot override failed
reproduction, high risk, security sensitivity, destructive behavior, or
migration requirements. The agent will never merge its own PR. GitHub branch
protection and required checks remain the final control.

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

The generated PR will include:

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

For completed runs, store:

- Symptom and normalized issue summary
- Reproduction method
- Root cause and affected code areas
- Successful and failed hypotheses
- Patch summary and regression tests
- Final outcome, review feedback, and time/cost metrics

Before diagnosing a new issue, retrieve prior memories using FTS over symptoms, components, errors, routes, and file paths. Reuse prior knowledge only as supporting context; verify it against the current revision before acting.

### Demonstrating learning

The second seeded bug will deliberately overlap a component, test pattern, or repository area learned during the first run. The demo will show:

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

Tests, generated snapshots, and lockfile changes will be reported separately when evaluating patch size. Limits can be overridden through reviewed configuration, and every override will be recorded in the run report.

## 7. GitHub Integration

Use this repository, `ravit-dennis/AgenticBugTriageAndResolution`, for the submission, issue tracking, seeded bug demonstrations, and generated repair PRs.

Planned GitHub assets:

- Bug report issue form with reproducibility fields
- Labels for agent state, severity, confidence, risk, component, and escalation
- GitHub Actions issue trigger
- Manual `workflow_dispatch` trigger for repeatable demos
- Check summaries and uploaded diagnostic artifacts
- Issue comments for state changes and human approvals
- Generated branches and pull requests linked to issues
- Branch protection guidance so the agent cannot self-merge

Live GitHub write operations will be tested first against dedicated demo issues and branches.

## 8. Seeded Demonstration Bugs

Introduce at least two realistic, independently reproducible defects:

### Backend bug

A data-validation, authorization, query, or API behavior defect that:

- Produces a clear failing API/integration test
- Requires tracing from route/controller to service/model/database behavior
- Is safe for the agent to fix autonomously

### Frontend bug

A state, rendering, form-validation, routing, or API-integration defect that:

- Produces a clear failing component or end-to-end test
- Requires identifying the responsible component and state/data flow
- Is safe for the agent to fix autonomously or through a draft PR

Keep bug-introduction patches/scripts separate and repeatable so the demo can reset and replay both scenarios. Do not rely on undocumented manual corruption of the repository.

## 9. Testing Strategy

### Agent unit tests

- Workflow transitions and terminal outcomes
- Severity/risk/autonomy policy
- Haiku/Sonnet/Opus routing rules
- Token and dollar budget enforcement
- Structured model response validation
- Context selection and truncation
- Memory write/retrieval and commit-SHA validation
- Command allowlist, timeouts, and output limits
- GitHub event parsing and idempotency

### Agent integration tests

- Mock Anthropic responses through complete workflow paths
- Mock GitHub issue/comment/branch/PR interactions
- Temporary Git repositories for patch and branch behavior
- Successful repair, escalation, failed reproduction, failed tests, and exhausted-budget scenarios

### Target application tests

- Existing frontend and backend tests remain green
- One regression test per seeded bug
- Failing-before/passing-after evidence
- API/integration and frontend component or end-to-end coverage

### End-to-end tests

- GitHub issue to triage comment
- Issue to autonomous low-risk repair PR
- Issue to human-approval escalation
- Repeated webhook/event delivery does not create duplicate runs or PRs
- Memory from bug 1 is retrieved and measured during bug 2

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

## 11. Delivery Phases

### 48-hour allocation

| Timebox | Outcome |
|---|---|
| Hours 0-6 | Target app runs locally; license, setup, tests, and bug candidates are understood |
| Hours 6-16 | Typed workflow, safe tools, persistence, model adapter, and core tests work locally |
| Hours 16-26 | First seeded bug completes the failing-before/passing-after repair loop |
| Hours 26-34 | Workflow is generalized for the second bug; memory reuse is demonstrated |
| Hours 34-40 | GitHub issue/PR integration, HITL gates, metrics, and failure paths are complete |
| Hours 40-48 | Clean-checkout rehearsal, documentation, write-up, video preparation, and contingency buffer |

If the schedule slips, preserve the working end-to-end workflow, tests, GitHub integration, metrics, and video. Cut optional integrations and architectural expansion first.

### Phase 1 - Foundation

- Import and run the target application
- Preserve license and upstream attribution
- Establish Docker-based local environment
- Inventory existing tests and commands
- Add Python project structure, configuration, and baseline CI
- Define workflow state and structured domain models

### Phase 2 - Deterministic agent core

- Implement GitHub event parsing and idempotent run creation
- Implement isolated workspace and safe command runner
- Implement repository mapping and lexical context retrieval
- Implement state machine, run persistence, logs, and metrics
- Add unit and integration tests

### Phase 3 - LLM reasoning and controls

- Integrate Anthropic through a testable adapter
- Add structured Haiku prompts and response validation
- Add Sonnet escalation and disabled-by-default Opus path
- Enforce budget, retry, patch-size, and risk limits
- Add memory write/retrieval

### Phase 4 - Repair and GitHub workflow

- Implement reproduction, diagnosis, repair, and validation stages
- Add issue comments, labels, branches, checks, artifacts, and PR creation
- Add approval/escalation mechanism
- Add GitHub Actions trigger and manual demo workflow

### Phase 5 - Seeded bugs and end-to-end proof

- Introduce repeatable backend bug
- Create GitHub issue and run the complete workflow
- Preserve generated triage evidence and repair PR
- Introduce repeatable frontend bug with a memory overlap
- Run the workflow and compare time/cost/context metrics
- Add an explicit high-risk escalation demonstration

### Phase 6 - Submission polish

- Harden setup instructions and one-command demo path
- Add architecture diagram and operational runbook
- Prepare 1-2 page write-up:
  - What was built
  - Architecture and design decisions
  - Autonomy and safety choices
  - Measurement and observed results
  - What would change with one month
- Prepare a 5-10 minute live walkthrough script
- Rehearse from a clean checkout with a fresh issue

## 12. Evaluation Coverage

| Evaluation area | Evidence to provide |
|---|---|
| Functionality | Two live issue-to-triage-to-repair-PR demonstrations |
| Autonomy | Policy-driven low-risk automatic repair and bounded retries |
| Human-in-the-loop | Draft PR/approval gates and explicit high-risk escalation |
| Measurement | Run dashboard/report with time, success, memory, and cost metrics |
| Context and memory | Explainable retrieval plus bug 1 to bug 2 improvement |
| Taste | Concise issue comments, review-ready PRs, low notification noise, clear failure states |

## 13. Definition of Done

- A fresh GitHub bug issue can trigger the workflow.
- The agent can reproduce, diagnose, classify, and route the issue.
- A safe bug produces a tested PR with a regression test.
- A risky or uncertain bug stops at a clear human decision point.
- Backend and frontend seeded bugs are demonstrated end to end.
- Haiku is the default and escalation/cost decisions are visible.
- Context and memory improve or inform the second run with measured evidence.
- Tests cover success, failure, retry, budget, idempotency, and escalation paths.
- Setup and demo work from a clean checkout without undocumented steps.
- The repository contains the short write-up and video walkthrough guidance required by the assignment.

## 14. Inputs Needed During Implementation

- The Anthropic API key only when live model integration begins; it will be configured as `ANTHROPIC_API_KEY` and never written to a tracked file.
- GitHub authentication with permission to create labels, comments, branches, and pull requests in this repository.
