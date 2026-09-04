# Demo Runbook

## Prerequisites

- Python 3.11 or newer
- Node.js 18.11 or newer
- A personal GitHub repository with hosted runners enabled
- `ANTHROPIC_API_KEY` and `AGENT_GITHUB_TOKEN` configured as encrypted Actions
  secrets
- The fine-grained GitHub token scoped to this repository with Contents,
  Issues, and Pull requests read/write

Never commit `.env`, API keys, tokens, `data/*.db`, or generated run artifacts.

## Clean-checkout validation

```powershell
git clone https://github.com/ravit-dennis/AgenticBugTriageAndResolution.git
Set-Location AgenticBugTriageAndResolution
python -m pip install -e ".[dev]"
python -m pytest
Set-Location target-app
npm ci
npm test -- --run
npm run build -w frontend
```

Expected result: 85 Python tests, 15 target-application tests, and a successful
frontend build.

## Hosted GitHub demonstration

Completed hosted evidence:

- Backend: `ravit-dennis/AgenticBugTriageAndResolution#33` → PR #36
- Frontend: `ravit-dennis/AgenticBugTriageAndResolution#34` → PR #37
- HITL and approved Sonnet repair:
  `ravit-dennis/AgenticBugTriageAndResolution#35` → draft PR #38

Fresh, intentionally unlabelled video replays:

- Backend: `ravit-dennis/AgenticBugTriageAndResolution#13`
- Frontend: `ravit-dennis/AgenticBugTriageAndResolution#14`
- Cross-layer HITL/Sonnet:
  `ravit-dennis/AgenticBugTriageAndResolution#29`

To run one:

1. Open the bug issue and confirm the exact test command is in backticks.
2. For a seeded replay, include one trusted metadata line:

   ```text
   Agent base branch: `demo/replay-backend-bug`
   ```

3. Review the issue content as a trusted repository collaborator.
4. Add the `agent:triage` label. Do not place this label on the issue template;
   adding it is the explicit approval to execute.
5. Open the Actions tab and select **Agentic bug intake and repair**.
6. Show the context, reproduction, diagnosis, validation, and sanitized report
   steps.
7. Return to the issue and show the updated status comment and generated PR.
8. In the PR, show the one-file diff, exact reproduction, full-suite validation,
   model cost, and human review focus.

The agent publishes a branch and PR but never merges it.

## Resumable human-in-the-loop demonstration

Use untouched issue #29. It declares
`demo/replay-pagination-contract-bug` as its trusted base branch and reproduces
a real frontend/backend pagination contract mismatch.

1. Apply `agent:triage`.
2. Open the linked workflow and show bounded context selection, the failing
   reproduction, and Haiku diagnosis.
3. Return to the issue. The first run must stop before editing because the
   change is cross-layer and medium risk.
4. Review the **Human decision required** comment and its exact reproduction,
   output fingerprint, diagnosis, supporting files, safety flag, cost, and
   workflow/artifact links.
5. Apply `agent:approve-draft`.
6. Show the resumed workflow using Haiku and one Sonnet escalation.
7. Return to the issue and show the detailed completion report.
8. Open the generated draft PR and show the one-file
   `offset = page * limit` repair, unchanged reproduction, and complete-suite
   validation.

The first-stage expected result is:

- an `agent:needs-information` label;
- a **Human decision required** comment;
- reproduction/diagnosis evidence and recorded model cost;
- the exact reproduction command, bounded output, supporting files, safety
  flags, workflow-run link, and explicit decision options;
- no published repair branch or PR.

After approval, the expected result is a draft PR with one changed
implementation file. The agent removes the one-shot decision label, records
`agent:approve-draft` in the sanitized report, and leaves review and merge to a
human. The proven final evidence is issue #35 and draft PR #38.

After reviewing the evidence, a collaborator can apply exactly one decision
label:

| Label | Result |
|---|---|
| `agent:retry` | Rerun normal triage after the issue evidence is updated |
| `agent:investigation-only` | Gather context, reproduce, and diagnose without editing |
| `agent:approve-draft` | Permit one bounded draft repair when no hard safety blocker exists |
| `agent:declined` | Record the decision and stop without model spend or target-app commands |

`agent:approve-draft` cannot override failed reproduction, high risk, security
sensitivity, destructive behavior, or a migration requirement. An approved
repair is opened as a GitHub draft PR and still requires human review and merge.
Decision labels are removed after processing so the same action can be applied
again deliberately.

## Local live replay

Live runs call Anthropic and modify the checked-out branch. Use a disposable
worktree:

```powershell
git worktree add ..\agent-demo demo/replay-backend-bug
Set-Location ..\agent-demo
Copy-Item ..\AgenticBugTriageAndResolution\.env .env
python -m pip install -e ".[dev]"
npm ci --prefix target-app
$env:AGENT_MAX_RUN_COST_USD = "0.25"
agentic-triage run-local `
  --event demo\events\backend-pagination-bug.json `
  --database data\demo.db
```

The JSON output includes the terminal stage, autonomy action, repair attempts,
cost, and changed files. Inspect the exact patch with:

```powershell
git diff -- target-app
```

Remove the disposable worktree from the original checkout when finished:

```powershell
git worktree remove ..\agent-demo
```

## Inspecting cost and memory

The hosted workflow uploads `data/run-report.json` as a seven-day sanitized
artifact. It contains stage, model tiers, token totals, cost, attempts, changed
files, memory IDs, and publication outcome without raw issue bodies or logs.

Local SQLite state can be inspected with Python:

```powershell
@'
import json, sqlite3
db = sqlite3.connect("data/demo.db")
for run_id, state_json in db.execute("select run_id, state_json from runs"):
    state = json.loads(state_json)
    print(run_id, state["stage"], state["usage"])
'@ | python -
```

## Recovery

- A pre-publication failure posts an `agent:failed` comment and publishes no
  branch. A later API failure can leave a pushed branch or PR; the failure
  comment and sanitized report identify the furthest completed publication
  step.
- Add `agent:retry` after correcting issue evidence. Stable marker-based
  comments are updated instead of creating duplicates.
- If a human has modified the agent branch, `--force-with-lease` prevents the
  workflow from silently overwriting the new remote commit.
