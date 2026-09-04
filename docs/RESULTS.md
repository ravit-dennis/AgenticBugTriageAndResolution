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

| Issue | Outcome | Elapsed | Input | Output | Cost | Publication |
|---|---|---:|---:|---:|---:|---|
| `ravit-dennis/AgenticBugTriageAndResolution#7` | Completed | 19.246s | 6,103 | 493 | $0.008568 | PR #10 |
| `ravit-dennis/AgenticBugTriageAndResolution#8` | Completed | 19.997s | 10,599 | 732 | $0.014259 | PR #11 |
| `ravit-dennis/AgenticBugTriageAndResolution#6` | Human escalation | 8.936s | 1,913 | 228 | $0.003053 | No branch or PR |

Hosted workflow runs:

- Backend: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33881688029
- Frontend: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33881840872
- HITL: https://github.com/ravit-dennis/AgenticBugTriageAndResolution/actions/runs/33881992652

The backend and frontend runs used Haiku only, selected two context files, made
one repair attempt, passed the unchanged reproduction plus all 15 target-app
tests, and produced one-file PRs. The HITL run classified the production-only
report as high risk with 35% confidence and stopped before repair.

The subsequent HITL enhancement makes the issue comment decision-ready: it
shows bounded reproduction output, diagnosis and supporting files, explicit
safety flags, model cost, a workflow-run link, and one-shot labels for retry,
read-only investigation, bounded draft approval, or decline. Medium-risk draft
candidates now stop before editing. Approval cannot bypass failed reproduction,
high risk, security sensitivity, destructive behavior, or migrations.

## Development spend

Seven persisted local workflow attempts, including failed and escalated
development runs, recorded $0.116006. The initial API connectivity check cost
$0.000128. The three hosted demonstrations added $0.025880, producing a measured
total of $0.142014. The Anthropic billing console remains authoritative for any
request not represented by these records.

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
