# Agentic Bug Triage and Resolution

## What I built

I built a bounded autonomous engineering workflow that starts from a qualified
GitHub bug issue and produces either a validated repair pull request or a clear
human escalation. The target is an imported MIT-licensed RealWorld application
with a React frontend, Express/Sequelize backend, and SQLite development
database. Two deterministic bugs demonstrate the workflow: incorrect backend
offset pagination and a frontend settings button that remains unavailable after
a failed request.

A GitHub Actions workflow starts only when a trusted collaborator with
triage-or-higher permission applies the `agent:triage` label. Public issue
reporters cannot manage labels. The workflow checks out a trusted branch,
installs the application, and invokes a typed Python state machine:

`context → reproduce → diagnose → route → repair → validate → publish`

The agent must reproduce the failure before editing. It searches first, reads
bounded files, produces validated structured model responses, applies exact
unique text replacements, inspects the patch, reruns the unchanged
reproduction, and then runs the full target-application test suite. A successful
run commits to a stable issue branch and opens or updates a reviewable PR. It
never merges.

The repository tool surface is deliberately small: bounded search and file
reads, allowlisted commands, exact edits, test execution, and Git diff. Child
test processes receive a secret-free environment, edits are enforced under
`target-app`, and issue-selected branches are restricted to `main` or approved
demo branches. Owner-only label activation prevents arbitrary public issue
authors from running repository code with credentials.

## Architecture and design choices

I chose an explicit Python state machine instead of a multi-agent framework.
The workflow, retry policy, risk boundaries, and terminal states are visible in
ordinary code and can be tested without an LLM. Pydantic schemas validate all
model decisions that drive actions. Deterministic tools answer questions before
model calls, which reduces cost and makes the system easier to audit.

Haiku is the default for context planning, diagnosis, and the first repair.
Sonnet is available only after a failed repair or when reasoning is genuinely
ambiguous. Opus is disabled. Each hosted run is capped at $0.25, with bounded
searches, files, output tokens, repair attempts, changed files, and changed
lines. Actual successful runs cost $0.009210 and $0.014435.

SQLite stores run state, model usage, and repair episodes. FTS5 retrieves prior
symptoms, root causes, fix patterns, and tests. The second demonstration
retrieved the first repair memory, but the agent still searched and validated
the current revision rather than trusting stale conclusions.

Autonomy is tied to evidence and implementation risk:

- high confidence plus a localized low-risk change can produce a ready-for-
  review PR;
- medium risk or confidence produces a draft/review path;
- failed reproduction, low confidence, security sensitivity, destructive
  behavior, migrations, or high risk stops before publication and requests a
  human decision;
- validation or repair exhaustion also escalates with the attempts and evidence.

GitHub remains the developer interface. Comments contain concise reproduction,
diagnosis, cost, validation, and next-action information rather than raw logs or
chain-of-thought. Sanitized run reports are retained briefly as Actions
artifacts. The demonstrated cross-run repair memory is local SQLite; a durable
multi-run hosted memory service is part of the one-month production plan.

## Results and measurement

Both seeded bugs were reproduced, diagnosed, repaired, and validated with one
repair attempt. The backend workflow completed in 53.8 seconds using 5,895
input and 663 output tokens. The frontend completed in 38.0 seconds using
10,965 input and 694 output tokens and retrieved memory episode `1`. Both
repairs changed one implementation file and passed the exact regression test.
The repository also passes 71 Python tests, 15 target-application tests, and the
frontend production build in GitHub Actions.

The final hosted demonstration then processed three maintainer-approved issues on
clean Ubuntu runners. Backend issue #7 opened one-file repair PR #10 in 19.246
seconds for $0.008568. Frontend issue #8 opened one-file repair PR #11 in
19.997 seconds for $0.014259. The production-only data-loss report in issue #6
was not reproducible; the agent classified it high-risk at 35% confidence,
spent $0.003053, posted a human-decision request, and published no branch.

The primary business metric is time from a qualified bug report to a validated
repair candidate without increasing escaped regressions. Supporting metrics are
reproduction rate, autonomous completion, first-patch success, escalation rate,
cost per repair, memory hits, developer acceptance, and rework. The current
demonstration proves the mechanism; a real pilot would compare these measures
against manual triage over several weeks.

## What I would build with one month

First, I would run a controlled pilot on a larger repository and use accepted
and rejected PRs to calibrate confidence thresholds by component and risk
class. I would add isolated ephemeral containers, stronger command sandboxes,
dependency-aware code navigation, and test-impact selection while retaining the
same reproduction and human-approval gates.

Second, I would replace artifact/cache persistence with a durable service that
separates operational logs, sanitized evidence, and versioned repair memory.
Memory retrieval would combine lexical, symbol, ownership, and change-history
signals and measure whether each retrieved episode actually improved time,
quality, or cost.

Third, I would integrate branch protection, CODEOWNERS-based routing, deployment
and rollback evidence, observability, and an evaluation harness covering a
larger labeled bug set. I would add Slack only if teams requested it; GitHub
would remain the system of record. The strategic goal would not be maximum
autonomy. It would be the highest reliable reduction in engineer resolution
time at an acceptable regression and cost rate.
