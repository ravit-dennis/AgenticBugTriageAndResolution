from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agentic_triage.models import Issue


class GitHubIssueEvent(BaseModel):
    action: str
    issue: dict[str, Any]
    repository: dict[str, Any]

    def to_issue(self) -> Issue:
        labels = [
            label["name"] if isinstance(label, dict) else str(label)
            for label in self.issue.get("labels", [])
        ]
        return Issue(
            number=self.issue["number"],
            title=self.issue["title"],
            body=self.issue.get("body") or "",
            labels=labels,
            html_url=self.issue.get("html_url"),
        )

    @property
    def repository_full_name(self) -> str:
        return str(self.repository["full_name"])


class IntakeResult(BaseModel):
    accepted: bool
    reasons: list[str] = Field(default_factory=list)


def evaluate_intake(
    event: GitHubIssueEvent,
    *,
    required_label: str = "agent:triage",
) -> IntakeResult:
    issue = event.to_issue()
    reasons: list[str] = []
    if event.action not in {"opened", "reopened", "labeled"}:
        reasons.append(f"Unsupported issue action: {event.action}")
    if required_label not in issue.labels:
        reasons.append(f"Missing required label: {required_label}")
    if not issue.body.strip():
        reasons.append("Issue body is empty")
    return IntakeResult(accepted=not reasons, reasons=reasons)
