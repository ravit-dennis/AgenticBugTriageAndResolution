# Agentic Bug Triage and Resolution

A bounded agentic workflow that receives GitHub bug issues, gathers targeted repository context, reproduces the failure, diagnoses and classifies it, implements safe repairs, validates the exact reproduction, and opens a reviewable pull request or escalates to a human.

The implementation emphasizes:

- Haiku-first model routing with bounded Sonnet escalation
- Reproduction before repair and failing-before/passing-after evidence
- Explicit risk, confidence, patch-size, retry, and cost gates
- Compact stage-specific context rather than whole-repository prompts
- SQLite-backed run history, searchable episodic memory, and metrics
- GitHub issues and pull requests as the developer-facing workflow

See [`PLAN.md`](PLAN.md) for the complete architecture and evaluation mapping.

## Repository layout

| Path | Purpose |
|---|---|
| `src/agentic_triage/` | Python agent state machine, policies, persistence, budgets, and safe tools |
| `tests/` | Agent unit and integration-style workflow tests |
| `target-app/` | MIT-licensed React/Express/Sequelize RealWorld application used for bug demonstrations |

## Agent development

Requirements: Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

The deterministic core and mocked tests do not require an Anthropic API key.

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
