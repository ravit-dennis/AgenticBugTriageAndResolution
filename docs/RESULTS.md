# Measured Results

The figures below come from the persisted Anthropic usage returned by the API
and the timestamps in `data/backend-run.db`. The database is intentionally
ignored because it contains run evidence and local state; this document is the
sanitized, reviewable record.

| Metric | Backend pagination | Frontend settings |
|---|---:|---:|
| Outcome | Validated repair | Validated repair |
| End-to-end elapsed time | 53.8 seconds | 38.0 seconds |
| Repair attempts | 1 | 1 |
| Models used | Haiku only | Haiku only |
| Input tokens | 5,895 | 10,965 |
| Output tokens | 663 | 694 |
| Model calls | 3 | 3 |
| Estimated model cost | $0.009210 | $0.014435 |
| Context files | 2 | 2 |
| Prior memory IDs | None | `[1]` |
| Exact reproduction after repair | Passed | Passed |

## Per-stage model usage

### Backend pagination

| Stage | Model | Input | Output | Cost |
|---|---|---:|---:|---:|
| Context search planning | Haiku | 279 | 45 | $0.000504 |
| Root-cause diagnosis | Haiku | 2,859 | 177 | $0.003744 |
| Repair | Haiku | 2,757 | 441 | $0.004962 |

### Frontend settings

| Stage | Model | Input | Output | Cost |
|---|---|---:|---:|---:|
| Context search planning | Haiku | 296 | 52 | $0.000556 |
| Root-cause diagnosis | Haiku | 5,484 | 200 | $0.006484 |
| Repair | Haiku | 5,185 | 442 | $0.007395 |

## What the results demonstrate

- Both bugs completed the failing-before/passing-after repair loop.
- The agent selected only the regression test and adjacent implementation file
  in each successful run rather than sending the repository to the model.
- The frontend run retrieved memory episode `1`, created by the backend run,
  and finished faster while still revalidating the current source and tests.
- Both successful repairs cost less than two cents and stayed far below the
  hosted limit of $0.25 per run.
- The agent created localized one-file repairs and did not merge its own pull
  requests.

## Hosted GitHub evidence

After the local development runs, the complete issue-triggered workflow was
executed on clean GitHub-hosted Ubuntu runners.

### Final recording evidence

| Issue | Outcome | Elapsed | Input | Output | Cost | Publication |
|---|---|---:|---:|---:|---:|---|
| `ravit-dennis/AgenticBugTriageAndResolution#33` | Backend repair | 18.467s | 6,083 | 481 | $0.008488 | PR #36 |
| `ravit-dennis/AgenticBugTriageAndResolution#34` | Frontend repair | 22.222s | 10,626 | 690 | $0.014076 | PR #37 |
| `ravit-dennis/AgenticBugTriageAndResolution#35` | Approval requested | 9.527s | 3,451 | 279 | $0.004846 | No branch or PR |
| `ravit-dennis/AgenticBugTriageAndResolution#35` | Approved Sonnet repair | 23.684s | 7,326 | 953 | $0.019317 | Draft PR #38 |

Hosted workflow runs:

- Backend: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892693454
- Frontend: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892695157
- HITL diagnosis: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892696955
- Approved draft repair: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33892851889

The backend and frontend runs used Haiku only, selected two context files, made
one repair attempt, passed the unchanged reproduction plus the complete
target-app suite, and produced one-file PRs. The cross-layer pagination run
used Haiku to reproduce and diagnose the contract mismatch, classified the
change as medium risk at 99% confidence, and stopped before editing. Its issue
comment exposed retry, read-only investigation, bounded draft approval, and
decline actions with exact evidence and workflow links.

After a maintainer applied `agent:approve-draft`, the workflow resumed from a
fresh trusted checkout. Haiku repeated bounded context and diagnosis work,
Sonnet performed the one permitted cross-layer repair, and the unchanged
reproduction plus full target-app suite passed. The run changed only
`target-app/frontend/src/services/getArticles.js` and opened draft PR #38; the
agent did not merge it. Approval still cannot bypass failed reproduction, high
risk, security sensitivity, destructive behavior, or migrations.

The intentionally untouched recording issues are #13 for backend repair, #14
for frontend repair, and #29 for the cross-layer HITL/Sonnet flow.

## Development spend

Seven persisted local workflow attempts, including failed and escalated
development runs, recorded $0.116006. The initial API connectivity check cost
$0.000128. The original hosted demonstrations and subsequent refreshed,
decision-ready, and Sonnet evidence runs bring the measured total to $0.237498.
The Anthropic billing console remains authoritative for any request not
represented by these records.

## Business and operational metrics

The primary business metric is median engineer time from a qualified bug report
to a validated repair candidate. Supporting production metrics should include:

- reproduction success rate;
- autonomous validated-repair rate;
- first-patch success rate;
- human escalation rate and acceptance;
- cost per validated repair;
- escaped regression rate;
- developer PR acceptance and rework;
- context files, tokens, and memory-hit rate.

Two seeded bugs prove feasibility, not a statistically meaningful production
baseline. A production pilot should compare these metrics against a manual
triage cohort over several weeks.
