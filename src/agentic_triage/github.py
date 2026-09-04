from __future__ import annotations

from typing import Any

import httpx


class GitHubAPIError(RuntimeError):
    pass


class GitHubClient:
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        client: httpx.Client | None = None,
    ) -> None:
        if repository.count("/") != 1:
            raise ValueError("Repository must use owner/name format")
        self.repository = repository
        self.client = client or httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "agentic-bug-triage",
            },
            timeout=30,
        )

    def add_labels(self, issue_number: int, labels: list[str]) -> None:
        self._request(
            "POST",
            f"/repos/{self.repository}/issues/{issue_number}/labels",
            json={"labels": labels},
        )

    def upsert_issue_comment(
        self,
        issue_number: int,
        *,
        marker: str,
        body: str,
    ) -> None:
        comments = self._request(
            "GET",
            f"/repos/{self.repository}/issues/{issue_number}/comments",
            params={"per_page": 100},
        )
        marked_body = f"<!-- {marker} -->\n{body}"
        for comment in comments:
            if marker in comment.get("body", ""):
                self._request(
                    "PATCH",
                    f"/repos/{self.repository}/issues/comments/{comment['id']}",
                    json={"body": marked_body},
                )
                return

        self._request(
            "POST",
            f"/repos/{self.repository}/issues/{issue_number}/comments",
            json={"body": marked_body},
        )

    def create_pull_request(
        self,
        *,
        title: str,
        head: str,
        base: str,
        body: str,
        draft: bool,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/repos/{self.repository}/pulls",
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft,
            },
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.client.request(method, path, **kwargs)
        if response.is_error:
            raise GitHubAPIError(
                f"GitHub API {method} {path} failed with "
                f"{response.status_code}: {response.text}"
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()
