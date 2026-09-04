from __future__ import annotations

import argparse
import html
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
from agentic_triage.hosted import (
    agent_branch_name,
    extract_base_branch,
    prepare_agent_branch,
)
from agentic_triage.hosted_handlers import GitHubWorkflowHandlers
from agentic_triage.live_handlers import LocalWorkflowHandlers
from agentic_triage.model_gateway import AnthropicGateway
from agentic_triage.models import AgentRunState, Stage
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
    hosted = subparsers.add_parser("run-github")
    hosted.add_argument("--event", required=True, type=Path)
    hosted.add_argument("--database", type=Path, default=Path("data/agent.db"))
    hosted.add_argument(
        "--report",
        type=Path,
        default=Path("data/run-report.json"),
    )
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
    settings = settings_from_environment()
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


def settings_from_environment() -> AgentSettings:
    settings = AgentSettings()
    configured_cost = os.environ.get("AGENT_MAX_RUN_COST_USD")
    if configured_cost:
        settings.limits.max_run_cost_usd = float(configured_cost)
    return settings


def run_github(args: argparse.Namespace) -> int:
    event = GitHubIssueEvent.model_validate_json(
        args.event.read_text(encoding="utf-8")
    )
    intake = evaluate_intake(event)
    if not intake.accepted:
        raise ValueError(f"Issue failed intake: {', '.join(intake.reasons)}")

    token = os.environ.get("AGENT_GITHUB_TOKEN")
    if not token:
        raise RuntimeError("AGENT_GITHUB_TOKEN is required")

    issue = event.to_issue()
    commit_sha = os.environ.get("GITHUB_SHA") or current_commit_sha()
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
    settings = settings_from_environment()
    repository = SQLiteRepository(args.database)
    budget = BudgetTracker(max_cost_usd=settings.limits.max_run_cost_usd)
    github = GitHubClient(
        repository=event.repository_full_name,
        token=token,
    )
    for name, color, description in (
        ("agent:running", "1d76db", "Agent workflow is running"),
        ("agent:resolved", "0e8a16", "Agent produced a validated repair"),
        (
            "agent:needs-information",
            "d93f0b",
            "Agent stopped for a human decision",
        ),
        ("agent:failed", "b60205", "Agent workflow failed safely"),
    ):
        github.ensure_label(name, color=color, description=description)
    github.remove_label(issue.number, "agent:failed")
    github.remove_label(issue.number, "agent:needs-information")

    try:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is required")
        base_branch = extract_base_branch(issue.body)
        head_branch = agent_branch_name(issue.number)
        owner = event.repository_full_name.split("/", 1)[0]
        existing_pull_request = github.find_pull_request(
            head=f"{owner}:{head_branch}",
            base=base_branch,
        )
        if existing_pull_request is not None:
            if existing_pull_request.get("state") != "open":
                raise RuntimeError(
                    "A closed pull request already exists for this issue branch"
                )
            state.transition(
                Stage.COMPLETED,
                "An open repair pull request already exists",
            )
            state.metadata["publication"] = {
                "mode": "github",
                "status": "pull_request_created",
                "pull_request_number": existing_pull_request["number"],
                "pull_request_url": existing_pull_request["html_url"],
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
            repository.save_run(state)
            github.upsert_issue_comment(
                issue.number,
                marker=f"agentic-triage-run:{state.run_id}",
                body=(
                    "## Agentic triage already completed\n\n"
                    "An open repair pull request already exists for this issue: "
                    f"{existing_pull_request['html_url']}\n\n"
                    "The workflow did not execute repository commands or spend "
                    "additional model budget."
                ),
            )
            write_run_report(args.report, state, budget.spent_usd)
            print(args.report.read_text(encoding="utf-8"))
            return 0
        head_branch = prepare_agent_branch(
            Path.cwd(),
            base_branch=base_branch,
            issue_number=issue.number,
        )
        state.commit_sha = current_commit_sha()
        state.run_id = str(
            uuid5(
                NAMESPACE_URL,
                f"https://github.com/{event.repository_full_name}/issues/"
                f"{issue.number}@{state.commit_sha}",
            )
        )
        state.metadata.update(
            {
                "base_branch": base_branch,
                "head_branch": head_branch,
                "mode": "github",
            }
        )
    except Exception as error:
        state.transition(Stage.FAILED, f"{type(error).__name__}: {error}")
        repository.save_run(state)
        write_run_report(args.report, state, budget.spent_usd)
        try:
            report_preflight_failure(github, state, error)
        except Exception as reporting_error:
            print(
                "GitHub failure reporting also failed: "
                f"{type(reporting_error).__name__}: {reporting_error}",
                file=sys.stderr,
            )
        raise

    handlers = GitHubWorkflowHandlers(
        root=Path.cwd(),
        gateway=AnthropicGateway(settings=settings, budget=budget),
        repository=repository,
        settings=settings,
        github=github,
        github_token=token,
        repository_name=event.repository_full_name,
        base_branch=base_branch,
        head_branch=head_branch,
    )
    try:
        result = Orchestrator(handlers, repository, settings).run(state)
    except Exception as error:
        write_run_report(args.report, state, budget.spent_usd)
        try:
            handlers.report_failure(state, error)
        except Exception as reporting_error:
            print(
                "GitHub failure reporting also failed: "
                f"{type(reporting_error).__name__}: {reporting_error}",
                file=sys.stderr,
            )
        raise

    write_run_report(args.report, result, budget.spent_usd)
    print(args.report.read_text(encoding="utf-8"))
    return 0 if result.stage in {Stage.COMPLETED, Stage.ESCALATED} else 2


def report_preflight_failure(
    github: GitHubClient,
    state: AgentRunState,
    error: Exception,
) -> None:
    github.add_labels(state.issue.number, ["agent:failed"])
    github.upsert_issue_comment(
        state.issue.number,
        marker=f"agentic-triage-run:{state.run_id}",
        body=(
            "## Agentic triage failed safely\n\n"
            f"**Run ID:** `{state.run_id}`  \n"
            f"**Stage:** `{state.stage.value}`\n\n"
            "No repository command or repair branch was published. "
            "Preflight stopped with:\n\n"
            f"> {html.escape(type(error).__name__)}: "
            f"{html.escape(str(error))}"
        ),
    )


def write_run_report(
    path: Path,
    state: AgentRunState,
    cost_usd: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": state.run_id,
                "issue_number": state.issue.number,
                "stage": state.stage.value,
                "autonomy_action": (
                    state.autonomy_action.value
                    if state.autonomy_action
                    else None
                ),
                "repair_attempts": state.repair_attempts,
                "sonnet_escalations": state.sonnet_escalations,
                "cost_usd": round(cost_usd, 6),
                "input_tokens": sum(item.input_tokens for item in state.usage),
                "output_tokens": sum(item.output_tokens for item in state.usage),
                "models": sorted({item.model.value for item in state.usage}),
                "elapsed_seconds": round(
                    (state.updated_at - state.created_at).total_seconds(),
                    3,
                ),
                "context_files": len(state.context.files),
                "changed_files": (
                    state.repair.changed_files if state.repair else []
                ),
                "prior_memory_ids": state.context.prior_memory_ids,
                "publication": state.metadata.get("publication"),
                "escalation_reason": state.metadata.get("escalation_reason"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    try:
        if args.command == "intake":
            raise SystemExit(run_intake(args))
        if args.command == "run-local":
            raise SystemExit(run_local(args))
        if args.command == "run-github":
            raise SystemExit(run_github(args))
    except Exception as error:
        print(f"agentic-triage failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
