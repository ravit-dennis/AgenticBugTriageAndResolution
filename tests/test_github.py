import httpx

import agentic_triage.github as github_module
from agentic_triage.github import GitHubClient


def test_default_client_uses_supplied_token(monkeypatch) -> None:
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(github_module.httpx, "Client", FakeClient)

    GitHubClient(repository="example/repo", token="test-token")

    assert captured["headers"]["Authorization"] == "Bearer test-token"


def test_upsert_comment_updates_existing_marker() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json=[{"id": 99, "body": "<!-- run:1 -->\nOld"}],
            )
        return httpx.Response(200, json={"id": 99})

    client = GitHubClient(
        repository="example/repo",
        token="test-token",
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://api.github.test",
        ),
    )

    client.upsert_issue_comment(12, marker="run:1", body="New")

    assert [request.method for request in requests] == ["GET", "PATCH"]
    assert requests[1].url.path.endswith("/issues/comments/99")


def test_create_pull_request_sends_draft_policy() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(201, json={"number": 7, "html_url": "https://pr"})

    client = GitHubClient(
        repository="example/repo",
        token="test-token",
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://api.github.test",
        ),
    )

    pull_request = client.create_pull_request(
        title="Fix article filter",
        head="agent/fix-12",
        base="main",
        body="Evidence",
        draft=True,
    )

    assert pull_request["number"] == 7
    assert b'"draft":true' in captured["request"].content
