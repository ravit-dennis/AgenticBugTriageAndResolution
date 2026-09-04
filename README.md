# Agentic Bug Triage and Resolution

A bounded agentic workflow that receives GitHub bug issues, gathers targeted repository context, reproduces the failure, diagnoses and classifies it, implements safe repairs, validates the exact reproduction, and opens a reviewable pull request or escalates to a human.

The implementation emphasizes:

- Haiku-first model routing with bounded Sonnet escalation
- Reproduction before repair and failing-before/passing-after evidence
- Explicit risk, confidence, patch-size, retry, and cost gates
- Compact stage-specific context rather than whole-repository prompts
- SQLite-backed run history, searchable episodic memory, and metrics
- GitHub issues and pull requests as the developer-facing workflow

Submission material:

- [`docs/SUBMISSION.md`](docs/SUBMISSION.md) — required 1–2 page write-up
- [`docs/RESULTS.md`](docs/RESULTS.md) — measured runs, tokens, cost, and memory
- [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) — clean-checkout and live demo steps
- [`docs/VIDEO_WALKTHROUGH.md`](docs/VIDEO_WALKTHROUGH.md) — timed 5–10 minute script
- [`docs/architecture.excalidraw`](docs/architecture.excalidraw) — editable architecture diagram
- [`PLAN.md`](PLAN.md) — complete implementation and evaluation plan

## Repository layout

| Path | Purpose |
|---|---|
| `src/agentic_triage/` | Python agent state machine, policies, persistence, budgets, and safe tools |
| `tests/` | Agent unit and integration-style workflow tests |
| `target-app/` | MIT-licensed React/Express/Sequelize RealWorld application used for bug demonstrations |
| `demo/` | Repeatable bug patches and offline GitHub event fixtures |
| `docs/` | Submission brief, measured evidence, architecture, runbook, and video script |

## Agent development

Requirements: Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

The deterministic core and mocked tests do not require an Anthropic API key.

## Hosted GitHub workflow

The complete hosted workflow starts only when the repository owner adds the
`agent:triage` label to an issue. Configure these encrypted repository Actions
secrets:

- `ANTHROPIC_API_KEY`
- `AGENT_GITHUB_TOKEN`, using a repository-scoped fine-grained token with
  Contents, Issues, and Pull requests read/write

The workflow uses Haiku by default, enforces a $0.25 run limit, strips secrets
from test subprocess environments, restricts edits to `target-app`, reruns the
exact reproduction plus the complete target-app test suite, and opens a
reviewable PR or posts a human escalation. It never merges.

For seeded demonstrations, include a trusted metadata line in the issue:

```text
Agent base branch: `demo/replay-backend-bug`
```

See [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) for the complete procedure.

## Target application

Requirements: Node.js 18.11 or newer.

```powershell
Set-Location target-app
npm install
npm test -- --run
npm run build -w frontend
npm run start -w backend
```

The backend uses SQLite by default and creates `target-app\backend\data\development.sqlite`. PostgreSQL remains available through the environment variables in `target-app\backend\.env.example`.

The imported application and upstream attribution are documented in [`target-app\UPSTREAM.md`](target-app/UPSTREAM.md).
