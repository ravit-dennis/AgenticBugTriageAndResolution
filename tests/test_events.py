from agentic_triage.events import GitHubIssueEvent, evaluate_intake


def event(*, body: str = "Steps", labels=None, action: str = "opened"):
    return GitHubIssueEvent(
        action=action,
        issue={
            "number": 12,
            "title": "Broken article filter",
            "body": body,
            "labels": labels if labels is not None else [{"name": "agent:triage"}],
            "html_url": "https://github.com/example/repo/issues/12",
        },
        repository={"full_name": "example/repo"},
    )


def test_accepts_labeled_issue_with_body() -> None:
    result = evaluate_intake(event())

    assert result.accepted
    assert not result.reasons


def test_rejects_missing_label_and_empty_body() -> None:
    result = evaluate_intake(event(body="", labels=[]))

    assert not result.accepted
    assert "Missing required label: agent:triage" in result.reasons
    assert "Issue body is empty" in result.reasons
