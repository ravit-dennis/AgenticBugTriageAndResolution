from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from dotenv import load_dotenv

from agentic_triage.budget import BudgetTracker
from agentic_triage.config import AgentSettings
from agentic_triage.events import GitHubIssueEvent, evaluate_intake
from agentic_triage.github import GitHubClient
from agentic_triage.live_handlers import LocalWorkflowHandlers
from agentic_triage.model_gateway import AnthropicGateway
from agentic_triage.models import AgentRunState
from agentic_triage.orchestrator import Orchestrator
from agentic_triage.persistence import SQLiteRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-triage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    intake = subparsers.add_parser("intake")
    intake.add_argument("--event", required=True, type=Path)
    intake.add_argument("--database", type=Path, default=Path("data/agent.db"))
    intake.add_argument("--commit-sha")
    intake.add_argument("--no-github", action="store_true")
    run = subparsers.add_parser("run-local")
    run.add_argument("--event", required=True, type=Path)
    run.add_argument("--database", type=Path, default=Path("data/agent.db"))
    run.add_argument("--commit-sha")
    return parser


def current_commit_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return completed.stdout.strip()


def run_intake(args: argparse.Namespace) -> int:
    event = GitHubIssueEvent.model_validate_json(
        args.event.read_text(encoding="utf-8")
    )
    issue = event.to_issue()
    intake = evaluate_intake(event)
    commit_sha = args.commit_sha or os.getenv("GITHUB_SHA") or current_commit_sha()
    run_id = str(
        uuid5(
            NAMESPACE_URL,
            f"https://github.com/{event.repository_full_name}/issues/"
            f"{issue.number}@{commit_sha}",
        )
    )
    state = AgentRunState(
        run_id=run_id,
        issue=issue,
        commit_sha=commit_sha,
    )
    state.metadata["intake"] = intake.model_dump()
    repository = SQLiteRepository(args.database)
    repository.save_run(state)

    if not args.no_github:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required unless --no-github is used")
        github = GitHubClient(
            repository=event.repository_full_name,
            token=token,
        )
        marker = f"agentic-triage-run:{run_id}"
        if intake.accepted:
            github.add_labels(issue.number, ["agent:running"])
            body = (
                "## Agentic triage accepted\n\n"
                f"**Run ID:** `{run_id}`\n\n"
                "The issue passed intake validation. Repository context, "
                "reproduction, and diagnosis are the next stages."
            )
        else:
            github.add_labels(issue.number, ["agent:needs-information"])
            reasons = "\n".join(f"- {reason}" for reason in intake.reasons)
            body = (
                "## Agentic triage needs information\n\n"
                f"**Run ID:** `{run_id}`\n\n"
                f"{reasons}"
            )
        github.upsert_issue_comment(
            issue.number,
            marker=marker,
            body=body,
        )

    print(
        json.dumps(
            {
                "run_id": run_id,
                "issue_number": issue.number,
                "accepted": intake.accepted,
                "reasons": intake.reasons,
            }
        )
    )
    return 0 if intake.accepted else 2


def run_local(args: argparse.Namespace) -> int:
    event = GitHubIssueEvent.model_validate_json(
        args.event.read_text(encoding="utf-8")
    )
    intake = evaluate_intake(event)
    if not intake.accepted:
        raise ValueError(f"Issue failed intake: {', '.join(intake.reasons)}")
    issue = event.to_issue()
    commit_sha = args.commit_sha or os.getenv("GITHUB_SHA") or current_commit_sha()
    run_id = str(
        uuid5(
            NAMESPACE_URL,
            f"https://github.com/{event.repository_full_name}/issues/"
            f"{issue.number}@{commit_sha}",
        )
    )
    state = AgentRunState(
        run_id=run_id,
        issue=issue,
        commit_sha=commit_sha,
    )
    settings = AgentSettings()
    repository = SQLiteRepository(args.database)
    budget = BudgetTracker(max_cost_usd=settings.limits.max_run_cost_usd)
    handlers = LocalWorkflowHandlers(
        root=Path.cwd(),
        gateway=AnthropicGateway(settings=settings, budget=budget),
        repository=repository,
        settings=settings,
    )
    result = Orchestrator(handlers, repository, settings).run(state)
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "stage": result.stage.value,
                "autonomy_action": (
                    result.autonomy_action.value
                    if result.autonomy_action
                    else None
                ),
                "repair_attempts": result.repair_attempts,
                "cost_usd": round(budget.spent_usd, 6),
                "changed_files": (
                    result.repair.changed_files if result.repair else []
                ),
            }
        )
    )
    return 0 if result.stage.value == "completed" else 2


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    try:
        if args.command == "intake":
            raise SystemExit(run_intake(args))
        if args.command == "run-local":
            raise SystemExit(run_local(args))
    except Exception as error:
        print(f"agentic-triage failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
