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
reporters cannot manage labels. After escalation, trusted collaborators choose
retry, read-only investigation, bounded draft approval, or decline through
one-shot labels. The workflow checks out a trusted branch, installs the
application, and invokes a typed Python state machine:

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
demo branches. GitHub's label permission boundary prevents arbitrary public
issue authors from running repository code with credentials.

## Architecture and design choices

I chose an explicit Python state machine instead of a multi-agent framework.
The workflow, retry policy, risk boundaries, and terminal states are visible in
ordinary code and can be tested without an LLM. Pydantic schemas validate all
model decisions that drive actions. Deterministic tools answer questions before
model calls, which reduces cost and makes the system easier to audit.

Haiku is the default for context planning, diagnosis, and localized repairs.
Sonnet is available only after a failed repair or when reasoning is genuinely
ambiguous or cross-layer. Opus is disabled. Each hosted run is capped at $0.25,
with bounded searches, files, output tokens, repair attempts, changed files,
and changed lines. The final automatic hosted repairs cost $0.008488 and
$0.014076. The approved cross-layer run cost $0.019317 and used exactly one
Sonnet escalation.

SQLite stores run state, model usage, and repair episodes. FTS5 retrieves prior
symptoms, root causes, fix patterns, and tests. The second demonstration
retrieved the first repair memory, but the agent still searched and validated
the current revision rather than trusting stale conclusions.

Autonomy is tied to evidence and implementation risk:

- high confidence plus a localized low-risk change can produce a ready-for-
  review PR;
- medium risk or confidence stops before editing until a maintainer explicitly
  approves one bounded draft repair;
- failed reproduction, low confidence, security sensitivity, destructive
  behavior, migrations, or high risk stops before publication and requests a
  human decision;
- validation or repair exhaustion also escalates with the attempts and evidence.

GitHub remains the developer interface. Escalation comments include the exact
reproduction command, bounded observed output, root-cause hypothesis,
supporting files, safety flags, cost, workflow link, and explicit decision
labels rather than raw logs or chain-of-thought. Retry and investigation remain
read-only until policy permits a repair. Draft approval cannot override failed
reproduction, high risk, security sensitivity, destructive behavior, or
migration requirements, and an approved repair is opened as a draft PR.
Sanitized run reports are retained briefly as Actions artifacts. The
demonstrated cross-run repair memory is local SQLite; a durable multi-run hosted
memory service is part of the one-month production plan.

## Results and measurement

Both seeded bugs were reproduced, diagnosed, repaired, and validated with one
repair attempt. The backend workflow completed in 53.8 seconds using 5,895
input and 663 output tokens. The frontend completed in 38.0 seconds using
10,965 input and 694 output tokens and retrieved memory episode `1`. Both
repairs changed one implementation file and passed the exact regression test.
The repository also passes 85 Python tests, 15 target-application tests, and the
frontend production build in GitHub Actions.

The final hosted demonstration processed three maintainer-approved issues on
clean Ubuntu runners. Backend issue #33 opened one-file repair PR #36 in 18.467
seconds for $0.008488. Frontend issue #34 opened one-file repair PR #37 in
22.222 seconds for $0.014076. Cross-layer issue #35 reproduced a pagination
contract mismatch, diagnosed it at 99% confidence, and stopped before editing
because the change crossed frontend and backend boundaries. Its decision-ready
comment showed the exact command and evidence, supporting files, safety flag,
cost, workflow artifact, and four explicit maintainer actions.

After the maintainer applied `agent:approve-draft`, issue #35 resumed in a fresh
hosted run. Haiku handled bounded context and diagnosis, Sonnet made the single
approved repair, the unchanged reproduction and full suite passed, and draft
PR #38 opened with one changed implementation file. The two-stage HITL flow
cost $0.024163 in total and retained human review and merge control.

The primary business metric is time from a qualified bug report to a validated
repair candidate without increasing escaped regressions. Supporting metrics are
reproduction rate, autonomous completion, first-patch success, escalation rate,
cost per repair, memory hits, developer acceptance, and rework. The current
demonstration proves the mechanism; a real pilot would compare these measures
against manual triage over several weeks.

## What I would build with one month

First, I would turn the demonstration into an installable GitHub App rather
than requiring the agent to live inside the target repository. A team could
install it on selected repositories, grant least-privilege Contents, Issues,
Pull requests, and Checks permissions, and activate it through issue labels or
commands. Short-lived GitHub App installation tokens would replace
repository-scoped personal tokens. A hosted control plane would validate
webhooks, authorize the requesting maintainer, queue runs, publish check
statuses, and keep each customer and repository isolated.

Second, I would add a repository onboarding and profile system so the workflow
can support applications beyond this JavaScript example, including a larger
application such as Vikunja. Automatic discovery would identify languages,
package managers, test frameworks, build commands, services, ownership files,
and likely application boundaries. A reviewed repository profile committed to
the target repository would then declare trusted setup, reproduction, test, and
build commands; editable paths; required services; secrets; network policy; and
risk rules. Stack adapters for Node.js, Python, Go, Java, and .NET would
normalize search, dependency restoration, test results, coverage, and patch
validation. This is how the product could support many repositories safely;
it would not blindly execute arbitrary commands in an unknown repository.

Third, every investigation would run in a fresh ephemeral container or
short-lived VM built from a trusted base image. The runner would clone only the
authorized revision, start declared dependencies such as PostgreSQL or Redis,
and reproduce the issue inside the same isolated environment used for
validation. It would enforce CPU, memory, time, filesystem, process, and
egress limits; inject only stage-specific short-lived secrets; capture
sanitized logs and screenshots; and destroy the environment after the run.
For multi-service applications, the profile could reference a reviewed Docker
Compose or dev-container definition. This would make realistic reproduction
possible without allowing untrusted repository code to run on the control
plane or with GitHub credentials.

Fourth, I would replace per-run artifacts and local SQLite with durable,
tenant-isolated services for workflow state, evidence, metrics, and versioned
repair memory. Retrieval would combine lexical, symbol, dependency, ownership,
and change-history signals and measure whether each memory improved time,
quality, or cost. The production workflow would add CODEOWNERS routing, branch
protection, deployment and rollback evidence, audit logs, configurable
approval points, cost quotas, kill switches, and an evaluation harness spanning
a larger labeled bug set. A controlled pilot would use accepted, edited, and
rejected PRs to calibrate autonomy thresholds by repository and component.
GitHub would remain the system of record, with Slack or Teams added only as a
notification surface. The objective would remain bounded economic value: the
largest reliable reduction in engineer resolution time at an acceptable
regression, security, and model-cost rate.
