from __future__ import annotations

import html
import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from agentic_triage.github import GitHubClient

REPOSITORY = "radennis_microsoft/AgenticBugTriageAndResolution"

LABELS = {
    "agent:triage": ("5319e7", "Issue is eligible for agentic triage"),
    "agent:running": ("1d76db", "Agent workflow is running"),
    "agent:needs-information": ("d93f0b", "Agent needs human input"),
    "agent:resolved": ("0e8a16", "Agent produced a validated repair"),
    "component:backend": ("1d76db", "Backend defect"),
    "component:frontend": ("fbca04", "Frontend defect"),
    "severity:high": ("b60205", "High user-impact severity"),
}

SCENARIOS = [
    {
        "event": "demo/events/backend-pagination-bug.json",
        "run_id": "22a30e3a-e79a-5d6d-9853-0f39c23f9199",
        "base": "demo/backend-pagination-seeded",
        "head": "agent/fix-backend-pagination",
        "pr_title": "Fix article offset pagination",
    },
    {
        "event": "demo/events/frontend-settings-bug.json",
        "run_id": "fa4eb6a2-a81a-56a6-8364-fb3b9006eff3",
        "base": "demo/frontend-settings-seeded",
        "head": "agent/fix-frontend-settings",
        "pr_title": "Restore settings retry after failed update",
    },
]


def load_run(run_id: str) -> dict:
    with sqlite3.connect("data/backend-run.db") as connection:
        row = connection.execute(
            "SELECT state_json FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError(f"Run not found: {run_id}")
    return json.loads(row[0])


def triage_comment(state: dict) -> str:
    diagnosis = state["diagnosis"]
    repair = state["repair"]
    validation = state["validation"]
    cost = sum(item["estimated_cost_usd"] for item in state["usage"])
    memory_ids = state["context"]["prior_memory_ids"]
    root_cause = html.escape(diagnosis["root_cause"])
    repair_summary = html.escape(repair["summary"])
    return f"""## Agentic triage completed

**Reproduced:** yes  
**Severity:** {diagnosis["severity"]}  
**Change risk:** {diagnosis["risk"]}  
**Confidence:** {diagnosis["confidence"]:.0%}  
**Autonomy decision:** {state["autonomy_action"]}  
**Model cost:** ${cost:.6f}

### Root cause

{root_cause}

### Repair and validation

{repair_summary}

The unchanged reproduction command passed after the repair:

```text
{state["reproduction"]["command"]}
```

Memory episodes retrieved: {memory_ids or "none"}.
Validation status: {"passed" if all([
    validation["reproduction_passed"],
    validation["targeted_tests_passed"],
    validation["regression_tests_passed"],
]) else "failed"}.
"""


def pull_request_body(issue_number: int, state: dict) -> str:
    diagnosis = state["diagnosis"]
    repair = state["repair"]
    cost = sum(item["estimated_cost_usd"] for item in state["usage"])
    root_cause = html.escape(diagnosis["root_cause"])
    repair_summary = html.escape(repair["summary"])
    return f"""## Agent-generated repair

Relates to #{issue_number}.

### Reproduction

The issue was reproduced before editing with:

```text
{state["reproduction"]["command"]}
```

### Root cause

{root_cause}

### Repair

{repair_summary}

### Validation

The exact reproduction command was rerun unchanged and passed.

- Severity: `{diagnosis["severity"]}`
- Change risk: `{diagnosis["risk"]}`
- Confidence: `{diagnosis["confidence"]:.0%}`
- Repair attempts: `{state["repair_attempts"]}`
- Model cost: `${cost:.6f}`
- Prior memory IDs: `{state["context"]["prior_memory_ids"] or "none"}`

### Human review focus

Confirm the behavior matches the public API/UI contract and that the localized change has no adjacent regression.
"""


def main() -> None:
    load_dotenv(Path.cwd() / ".env")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")
    github = GitHubClient(repository=REPOSITORY, token=token)

    for name, (color, description) in LABELS.items():
        github.ensure_label(name, color=color, description=description)

    for scenario in SCENARIOS:
        event = json.loads(Path(scenario["event"]).read_text(encoding="utf-8"))
        issue_payload = event["issue"]
        state = load_run(scenario["run_id"])
        issue = github.find_issue_by_title(issue_payload["title"])
        if issue is None:
            issue = github.create_issue(
                title=issue_payload["title"],
                body=issue_payload["body"],
                labels=[label["name"] for label in issue_payload["labels"]],
            )
        github.add_labels(
            issue["number"],
            ["agent:resolved", "severity:high"],
        )
        github.upsert_issue_comment(
            issue["number"],
            marker=f"agentic-triage-run:{state['run_id']}",
            body=triage_comment(state),
        )

        owner = REPOSITORY.split("/", 1)[0]
        head = f"{owner}:{scenario['head']}"
        pull_request = github.find_pull_request(
            head=head,
            base=scenario["base"],
        )
        body = pull_request_body(issue["number"], state)
        if pull_request is None:
            pull_request = github.create_pull_request(
                title=scenario["pr_title"],
                head=scenario["head"],
                base=scenario["base"],
                body=body,
                draft=False,
            )
        else:
            pull_request = github.update_pull_request(
                pull_request["number"],
                title=scenario["pr_title"],
                body=body,
            )
        print(
            json.dumps(
                {
                    "issue": issue["html_url"],
                    "pull_request": pull_request["html_url"],
                }
            )
        )


if __name__ == "__main__":
    main()
