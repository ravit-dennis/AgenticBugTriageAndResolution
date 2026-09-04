from __future__ import annotations

import base64
import html
import os
import subprocess
import tempfile
from pathlib import Path

from agentic_triage.github import GitHubClient
from agentic_triage.live_handlers import LocalWorkflowHandlers
from agentic_triage.models import AgentRunState, AutonomyAction
from agentic_triage.tools import ToolPolicyError


class GitHubWorkflowHandlers(LocalWorkflowHandlers):
    def __init__(
        self,
        *,
        github: GitHubClient,
        github_token: str,
        repository_name: str,
        base_branch: str,
        head_branch: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.github = github
        self.github_token = github_token
        self.repository_name = repository_name
        self.base_branch = base_branch
        self.head_branch = head_branch
        self.expected_origin_urls = {
            f"https://github.com/{repository_name}",
            f"https://github.com/{repository_name}.git",
        }

    def publish(self, state: AgentRunState) -> None:
        super().publish(state)
        owner = self.repository_name.split("/", 1)[0]
        pull_request = self.github.find_pull_request(
            head=f"{owner}:{self.head_branch}",
            base=self.base_branch,
        )
        if pull_request is not None and pull_request.get("state") != "open":
            raise ToolPolicyError(
                "A closed pull request already exists for this issue branch"
            )

        self._commit_repair(state)
        self._push_repair()
        state.metadata["publication"] = {
            "mode": "github",
            "status": "branch_pushed",
            "head_branch": self.head_branch,
            "base_branch": self.base_branch,
        }
        self.repository.save_run(state)

        title = f"[Agent repair] {state.issue.title}"
        body = self._pull_request_body(state)
        if pull_request is None:
            pull_request = self.github.create_pull_request(
                title=title,
                head=self.head_branch,
                base=self.base_branch,
                body=body,
                draft=state.autonomy_action is AutonomyAction.DRAFT_PR,
            )
        else:
            pull_request = self.github.update_pull_request(
                pull_request["number"],
                title=title,
                body=body,
            )

        state.metadata["publication"] = {
            "mode": "github",
            "status": "pull_request_created",
            "pull_request_number": pull_request["number"],
            "pull_request_url": pull_request["html_url"],
            "head_branch": self.head_branch,
            "base_branch": self.base_branch,
        }
        self.repository.save_run(state)
        self.github.upsert_issue_comment(
            state.issue.number,
            marker=f"agentic-triage-run:{state.run_id}",
            body=self._completion_comment(state, pull_request["html_url"]),
        )
        self.github.remove_label(state.issue.number, "agent:running")
        self.github.remove_label(state.issue.number, "agent:needs-information")
        self.github.add_labels(state.issue.number, ["agent:resolved"])

    def escalate(self, state: AgentRunState, reason: str) -> None:
        super().escalate(state, reason)
        self.github.remove_label(state.issue.number, "agent:running")
        self.github.add_labels(
            state.issue.number,
            ["agent:needs-information"],
        )
        self.github.upsert_issue_comment(
            state.issue.number,
            marker=f"agentic-triage-run:{state.run_id}",
            body=self._escalation_comment(state, reason),
        )

    def report_failure(self, state: AgentRunState, error: Exception) -> None:
        self.github.remove_label(state.issue.number, "agent:running")
        self.github.add_labels(state.issue.number, ["agent:failed"])
        publication = state.metadata.get("publication") or {}
        status = publication.get("status")
        if status == "pull_request_created":
            remote_status = (
                "A repair PR was created before the later workflow failure: "
                f"{publication.get('pull_request_url')}."
            )
        elif status == "branch_pushed":
            remote_status = (
                "A repair branch was pushed before the later workflow failure: "
                f"`{publication.get('head_branch')}`."
            )
        else:
            remote_status = "No repair branch was published."
        self.github.upsert_issue_comment(
            state.issue.number,
            marker=f"agentic-triage-run:{state.run_id}",
            body=(
                "## Agentic triage failed safely\n\n"
                f"**Run ID:** `{state.run_id}`  \n"
                f"**Stage:** `{state.stage.value}`  \n"
                f"**Recorded model cost:** `${self._cost(state):.6f}`\n\n"
                f"{remote_status} The workflow stopped with:\n\n"
                f"> {html.escape(type(error).__name__)}: "
                f"{html.escape(str(error))}\n\n"
                "A maintainer should inspect the workflow log and either improve "
                "the reproduction evidence or rerun after correcting the failure."
            ),
        )

    def _commit_repair(self, state: AgentRunState) -> None:
        commands = [
            ["git", "config", "user.name", "agentic-triage[bot]"],
            [
                "git",
                "config",
                "user.email",
                "223556219+Copilot@users.noreply.github.com",
            ],
            ["git", "add", "--", "target-app"],
        ]
        for command in commands:
            result = self.tools.run_command(command)
            if result.return_code != 0:
                raise RuntimeError(result.stderr or f"{command[1]} failed")

        staged = self.tools.run_command(
            ["git", "--no-pager", "diff", "--cached", "--quiet", "--"]
        )
        if staged.return_code == 0:
            raise ToolPolicyError("Validated repair produced no staged changes")
        if staged.return_code != 1:
            raise RuntimeError(staged.stderr or "Unable to inspect staged changes")

        with tempfile.TemporaryDirectory() as hooks_path:
            commit = self.tools.run_command(
                [
                    "git",
                    "-c",
                    f"core.hooksPath={hooks_path}",
                    "commit",
                    "-m",
                    f"Fix issue #{state.issue.number} with agentic triage",
                ]
            )
        if commit.return_code != 0:
            raise RuntimeError(commit.stderr or "git commit failed")

    def _push_repair(self) -> None:
        basic = base64.b64encode(
            f"x-access-token:{self.github_token}".encode("utf-8")
        ).decode("ascii")
        with tempfile.TemporaryDirectory() as hooks_path:
            global_config = Path(hooks_path) / "global.gitconfig"
            global_config.write_text("", encoding="utf-8")
            base_environment = self.tools._safe_subprocess_environment()
            base_environment.update(
                {
                    "GIT_CONFIG_GLOBAL": str(global_config),
                    "GIT_CONFIG_NOSYSTEM": "1",
                }
            )
            push_urls = subprocess.run(
                ["git", "remote", "get-url", "--push", "--all", "origin"],
                cwd=self.root,
                env=base_environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                shell=False,
            )
            resolved_urls = [
                line.strip()
                for line in push_urls.stdout.splitlines()
                if line.strip()
            ]
            rewrites = subprocess.run(
                [
                    "git",
                    "config",
                    "--local",
                    "--get-regexp",
                    r"^url\..*\.(insteadOf|pushInsteadOf)$",
                ],
                cwd=self.root,
                env=base_environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                shell=False,
            )
            if (
                push_urls.returncode != 0
                or len(resolved_urls) != 1
                or resolved_urls[0] not in self.expected_origin_urls
                or rewrites.returncode == 0
            ):
                raise ToolPolicyError(
                    "Git push destination does not match the issue repository"
                )

            environment = dict(base_environment)
            environment.update(
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "http.extraHeader",
                    "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}",
                }
            )
            completed = subprocess.run(
                [
                    "git",
                    "-c",
                    f"core.hooksPath={hooks_path}",
                    "push",
                    resolved_urls[0],
                    f"HEAD:refs/heads/{self.head_branch}",
                ],
                cwd=self.root,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
                shell=False,
            )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout).replace(
                self.github_token,
                "[REDACTED]",
            )
            raise RuntimeError(f"git push failed: {message.strip()}")

    def _pull_request_body(self, state: AgentRunState) -> str:
        diagnosis = state.diagnosis
        repair = state.repair
        validation = state.validation
        if diagnosis is None or repair is None or validation is None:
            raise RuntimeError("Cannot publish an incomplete run")
        commands = "\n".join(
            f"- `{html.escape(command)}`" for command in validation.commands
        )
        return f"""## Agent-generated repair

Relates to #{state.issue.number}.

### Evidence

- Reproduced before editing: `{state.reproduction.reproduced if state.reproduction else False}`
- Severity: `{diagnosis.severity.value}`
- Change risk: `{diagnosis.risk.value}`
- Confidence: `{diagnosis.confidence:.0%}`
- Repair attempts: `{state.repair_attempts}`
- Model cost: `${self._cost(state):.6f}`
- Prior memory IDs: `{state.context.prior_memory_ids or "none"}`

### Root cause

{html.escape(diagnosis.root_cause)}

### Repair

{html.escape(repair.summary)}

### Validation

The exact failing reproduction was rerun unchanged, followed by the complete
target-application test suite.

{commands}

### Human review focus

Confirm the localized change matches the reported contract. This agent never
merges its own pull requests.
"""

    def _completion_comment(self, state: AgentRunState, pull_url: str) -> str:
        diagnosis = state.diagnosis
        reproduction = state.reproduction
        repair = state.repair
        validation = state.validation
        if (
            diagnosis is None
            or reproduction is None
            or repair is None
            or validation is None
        ):
            raise RuntimeError("Cannot report an incomplete published run")
        review_mode = (
            "draft PR requiring explicit approval"
            if state.autonomy_action is AutonomyAction.DRAFT_PR
            else "ready-for-review PR"
        )
        supporting_files = "\n".join(
            f"- `{html.escape(path)}`" for path in diagnosis.supporting_files
        ) or "- None identified"
        changed_files = "\n".join(
            f"- `{html.escape(path)}`" for path in repair.changed_files
        ) or "- None"
        commands = "\n".join(
            f"- `{html.escape(command)}`" for command in validation.commands
        ) or "- None"
        models = ", ".join(
            sorted({record.model.value for record in state.usage})
        ) or "none"
        return f"""## Agentic triage completed

**Run ID:** `{state.run_id}`  
**Repair PR:** {pull_url}  
**Review mode:** {review_mode}

### Reproduction

**Status:** Reproduced before editing  
**Command:** `{html.escape(reproduction.command)}`  
**Expected:** {html.escape(reproduction.expected)}  
**Output fingerprint:** `{reproduction.output_fingerprint}`

### Diagnosis

**Root cause:** {html.escape(diagnosis.root_cause)}

**Severity:** `{diagnosis.severity.value}`  
**Change risk:** `{diagnosis.risk.value}`  
**Confidence:** `{diagnosis.confidence:.0%}`

**Supporting files**

{supporting_files}

### Repair and validation

{html.escape(repair.summary)}

**Changed files:** `{len(repair.changed_files)}`  
**Changed lines:** `{repair.changed_lines}`

{changed_files}

The exact reproduction was rerun unchanged, followed by the complete
target-application test suite.

{commands}

### Economics and evidence

**Models used:** `{models}`  
**Repair attempts:** `{state.repair_attempts}`  
**Model cost:** `${self._cost(state):.6f}`

- [Open the GitHub Actions run]({self._workflow_url()})
- Artifact `{self._artifact_name(state.issue.number)}` contains the sanitized
  token, cost, context, human-action, and publication report.
- The agent did not merge the pull request; human review remains required.
"""

    def _escalation_comment(self, state: AgentRunState, reason: str) -> str:
        diagnosis = state.diagnosis
        reproduction = state.reproduction
        workflow_url = self._workflow_url()
        artifact_name = self._artifact_name(state.issue.number)
        supporting_files = (
            "\n".join(
                f"- `{html.escape(path)}`"
                for path in diagnosis.supporting_files
            )
            if diagnosis and diagnosis.supporting_files
            else "- None identified"
        )
        flags = []
        if diagnosis:
            if diagnosis.security_sensitive:
                flags.append("Security-sensitive")
            if diagnosis.migration_required:
                flags.append("Migration required")
            if diagnosis.destructive:
                flags.append("Potentially destructive")
            if diagnosis.cross_layer:
                flags.append("Cross-layer change")
        if reproduction and not reproduction.reproduced:
            flags.append("Reported failure not reproduced")
        safety_flags = "\n".join(f"- {flag}" for flag in flags) or "- None"

        observed = (
            self._bounded_evidence(reproduction.observed)
            if reproduction
            else "No reproduction evidence was captured."
        )
        draft_available = bool(
            reproduction
            and reproduction.reproduced
            and diagnosis
            and diagnosis.risk.value != "high"
            and not diagnosis.security_sensitive
            and not diagnosis.migration_required
            and not diagnosis.destructive
        )
        draft_option = (
            "3. Add `agent:approve-draft` to authorize one bounded draft "
            "repair. The agent still cannot merge it."
            if draft_available
            else "3. Draft repair approval is unavailable because the issue "
            "was not reproduced or has a non-overridable safety flag."
        )
        diagnosis_details = (
            f"**Root-cause hypothesis:** "
            f"{html.escape(diagnosis.root_cause)}\n\n"
            f"**Severity:** `{diagnosis.severity.value}`  \n"
            f"**Change risk:** `{diagnosis.risk.value}`  \n"
            f"**Confidence:** `{diagnosis.confidence:.0%}`"
            if diagnosis
            else "No diagnosis was produced."
        )
        reproduction_details = (
            f"**Status:** "
            f"{'Reproduced' if reproduction.reproduced else 'Not reproduced'}  \n"
            f"**Command:** `{html.escape(reproduction.command)}`  \n"
            f"**Expected:** {html.escape(reproduction.expected)}  \n"
            f"**Output fingerprint:** `{reproduction.output_fingerprint}`"
            if reproduction
            else "No reproduction was attempted."
        )
        return f"""## Human decision required

**Run ID:** `{state.run_id}`  
**Recorded model cost:** `${self._cost(state):.6f}`  
**Reason:** {html.escape(reason)}

### Reproduction

{reproduction_details}

<details>
<summary>Observed command output</summary>

```text
{observed}
```

</details>

### Diagnosis

{diagnosis_details}

**Supporting files**

{supporting_files}

**Safety flags**

{safety_flags}

### Evidence

- [Open the GitHub Actions run]({workflow_url})
- Artifact `{artifact_name}` on that page contains sanitized token, cost,
  context, attempt, and outcome metrics.
- No repair branch or pull request was published.

### Maintainer decision

1. Update the issue with better evidence, then add `agent:retry`.
2. Add `agent:investigation-only` for another read-only diagnosis pass.
{draft_option}
4. Add `agent:declined` to record that no further agent action is wanted.
"""

    @staticmethod
    def _bounded_evidence(value: str, limit: int = 1_500) -> str:
        normalized = value.replace("\x1b", "")
        return html.escape(normalized[-limit:].strip() or "(no command output)")

    @staticmethod
    def _workflow_url() -> str:
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        if repository and run_id:
            return f"{server}/{repository}/actions/runs/{run_id}"
        return server

    @staticmethod
    def _artifact_name(issue_number: int) -> str:
        run_id = os.environ.get("GITHUB_RUN_ID", "local")
        return f"agent-run-{issue_number}-{run_id}"

    @staticmethod
    def _cost(state: AgentRunState) -> float:
        return sum(record.estimated_cost_usd for record in state.usage)
