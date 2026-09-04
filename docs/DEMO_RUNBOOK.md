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

Expected result: 71 Python tests, 15 target-application tests, and a successful
frontend build.

## Hosted GitHub demonstration

Prepared, intentionally unlabelled demonstrations:

- Backend: `ravit-dennis/AgenticBugTriageAndResolution#7`
- Frontend: `ravit-dennis/AgenticBugTriageAndResolution#8`
- Human escalation: `ravit-dennis/AgenticBugTriageAndResolution#6`

To run one:

1. Open the bug issue and confirm the exact test command is in backticks.
2. For a seeded replay, include one trusted metadata line:

   ```text
   Agent base branch: `demo/live-backend-bug`
   ```

3. Review the issue content as the repository owner.
4. Add the `agent:triage` label. Do not place this label on the issue template;
   adding it is the explicit approval to execute.
5. Open the Actions tab and select **Agentic bug intake and repair**.
6. Show the context, reproduction, diagnosis, validation, and sanitized report
   steps.
7. Return to the issue and show the updated status comment and generated PR.
8. In the PR, show the one-file diff, exact reproduction, full-suite validation,
   model cost, and human review focus.

The agent publishes a branch and PR but never merges it.

## Human-escalation demonstration

Use an issue that cannot be reproduced or that describes a security-sensitive,
destructive, migration-related, or low-confidence repair. Apply the label as
above. The expected result is:

- an `agent:needs-information` label;
- a **Human decision required** comment;
- reproduction/diagnosis evidence and recorded model cost;
- no published repair branch or PR.

## Local live replay

Live runs call Anthropic and modify the checked-out branch. Use a disposable
worktree:

```powershell
git worktree add ..\agent-demo demo/live-backend-bug
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
- Reapplying the triage label reuses the stable `agent/issue-N` branch and
  updates marker-based comments instead of creating duplicates.
- If a human has modified the agent branch, `--force-with-lease` prevents the
  workflow from silently overwriting the new remote commit.
