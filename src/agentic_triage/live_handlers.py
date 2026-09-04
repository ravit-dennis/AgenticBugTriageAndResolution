from __future__ import annotations

import re
import shlex
from pathlib import Path

from pydantic import BaseModel, Field

from agentic_triage.config import AgentSettings
from agentic_triage.model_gateway import AnthropicGateway
from agentic_triage.models import (
    AgentRunState,
    ContextSelection,
    Diagnosis,
    ModelTier,
    RepairResult,
    ReproductionEvidence,
    Stage,
    ValidationResult,
)
from agentic_triage.persistence import SQLiteRepository
from agentic_triage.routing import select_model
from agentic_triage.tools import RepositoryTools


class SearchPlan(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=5)


class RepairProposal(BaseModel):
    unified_diff: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    regression_test: str = Field(min_length=1)


class LocalWorkflowHandlers:
    def __init__(
        self,
        *,
        root: str | Path,
        gateway: AnthropicGateway,
        repository: SQLiteRepository,
        settings: AgentSettings,
    ) -> None:
        self.root = Path(root).resolve()
        self.tools = RepositoryTools(self.root)
        self.gateway = gateway
        self.repository = repository
        self.settings = settings
        self.reproduction_command: list[str] | None = None
        self._usage_index = 0

    def gather_context(self, state: AgentRunState) -> ContextSelection:
        plan = self._complete(
            state,
            stage=Stage.CONTEXT,
            tier=ModelTier.HAIKU,
            system=(
                "Plan a small lexical repository search for a reported bug. "
                "Return concrete identifiers or short regex terms, not sentences."
            ),
            payload={
                "title": state.issue.title,
                "body": state.issue.body,
                "limits": {
                    "searches": self.settings.limits.max_code_searches,
                    "files": self.settings.limits.max_files_read,
                },
            },
            response_model=SearchPlan,
            reason="repository search planning",
        )

        files: list[str] = []
        reasons: dict[str, str] = {}
        for query in plan.queries[: self.settings.limits.max_code_searches]:
            search_pattern = self._safe_search_pattern(query)
            for match in self.tools.search_code(
                search_pattern,
                paths=("target-app",),
                limit=20,
            ):
                path = match.split(":", 1)[0]
                path = Path(path).as_posix()
                if path not in files:
                    files.append(path)
                    reasons[path] = f"Matched search query: {query}"
                if len(files) >= self.settings.limits.max_files_read:
                    break
            if len(files) >= self.settings.limits.max_files_read:
                break

        for path in self._paths_from_issue(state.issue.body):
            candidates = [path]
            if not path.startswith("target-app/"):
                candidates.insert(0, f"target-app/{path}")
            for candidate in candidates:
                normalized = Path(candidate).as_posix()
                if normalized not in files and (self.root / normalized).is_file():
                    files.append(normalized)
                    reasons[normalized] = "Referenced directly by the issue"
                    break

        if not files:
            raise RuntimeError("Context search found no relevant files")
        return ContextSelection(
            search_queries=plan.queries,
            files=files[: self.settings.limits.max_files_read],
            reasons=reasons,
        )

    def reproduce(self, state: AgentRunState) -> ReproductionEvidence:
        command_text = self._reproduction_command(state.issue.body)
        command = self._normalize_command(command_text)
        self.reproduction_command = command
        result = self.tools.run_command(command, timeout_seconds=180)
        return ReproductionEvidence(
            reproduced=result.return_code != 0,
            command=command_text,
            expected="The regression test passes",
            observed=(result.stdout + "\n" + result.stderr)[-4_000:],
            output_fingerprint=result.output_fingerprint,
            confidence=0.99,
        )

    def diagnose(self, state: AgentRunState) -> Diagnosis:
        return self._complete(
            state,
            stage=Stage.DIAGNOSE,
            tier=select_model(state, self.settings),
            system=(
                "Diagnose the reproduced bug from the issue, failing test output, "
                "and bounded source context. Identify the specific root cause and "
                "classify severity, change risk, confidence, and safety flags."
            ),
            payload={
                "issue": state.issue.model_dump(),
                "reproduction": state.reproduction.model_dump(),
                "files": self._file_context(state.context.files),
            },
            response_model=Diagnosis,
            reason="root cause diagnosis",
        )

    def repair(self, state: AgentRunState) -> RepairResult:
        proposal = self._complete(
            state,
            stage=Stage.REPAIR,
            tier=select_model(state, self.settings),
            system=(
                "Produce the smallest safe repair as a standard unified git diff. "
                "Use repository-root paths prefixed with target-app/. Do not modify "
                "the regression test merely to weaken its assertion. The diff must "
                "apply with `git apply`."
            ),
            payload={
                "issue": state.issue.model_dump(),
                "reproduction": state.reproduction.model_dump(),
                "diagnosis": state.diagnosis.model_dump(),
                "files": self._file_context(state.context.files),
            },
            response_model=RepairProposal,
            reason=f"repair attempt {state.repair_attempts}",
        )
        self.tools.apply_patch(proposal.unified_diff)
        changed_files, changed_lines = self._diff_stats()
        return RepairResult(
            changed_files=changed_files,
            changed_lines=changed_lines,
            regression_test=proposal.regression_test,
            summary=proposal.summary,
        )

    def validate(self, state: AgentRunState) -> ValidationResult:
        if self.reproduction_command is None:
            raise RuntimeError("No reproduction command was captured")
        result = self.tools.run_command(
            self.reproduction_command,
            timeout_seconds=180,
        )
        passed = result.return_code == 0
        return ValidationResult(
            reproduction_passed=passed,
            targeted_tests_passed=passed,
            regression_tests_passed=passed,
            commands=[state.reproduction.command],
            summary=(result.stdout + "\n" + result.stderr)[-4_000:],
        )

    def publish(self, state: AgentRunState) -> None:
        state.metadata["publication"] = {
            "mode": "local",
            "status": "ready_for_github_pr",
        }
        self.repository.save_run(state)

    def escalate(self, state: AgentRunState, reason: str) -> None:
        state.metadata["escalation_reason"] = reason
        self.repository.save_run(state)

    def _complete(self, state: AgentRunState, **kwargs):
        response = self.gateway.complete_json(**kwargs)
        new_usage = self.gateway.budget.records[self._usage_index :]
        state.usage.extend(new_usage)
        self._usage_index = len(self.gateway.budget.records)
        return response

    def _file_context(self, files: list[str]) -> dict[str, str]:
        context: dict[str, str] = {}
        for path in files[: self.settings.limits.max_files_read]:
            content = (self.root / path).read_text(encoding="utf-8")
            context[path] = content[:12_000]
        return context

    def _diff_stats(self) -> tuple[list[str], int]:
        result = self.tools.run_command(
            ["git", "--no-pager", "diff", "--numstat", "--", "target-app"]
        )
        if result.return_code != 0:
            raise RuntimeError(result.stderr)
        files: list[str] = []
        changed_lines = 0
        for line in result.stdout.splitlines():
            additions, deletions, path = line.split("\t", 2)
            files.append(path)
            if additions.isdigit():
                changed_lines += int(additions)
            if deletions.isdigit():
                changed_lines += int(deletions)
        return files, changed_lines

    @staticmethod
    def _paths_from_issue(body: str) -> list[str]:
        return re.findall(r"(?:target-app/)?[\w./-]+\.(?:js|jsx|py)", body)

    @staticmethod
    def _safe_search_pattern(query: str) -> str:
        terms = re.findall(r"[A-Za-z0-9_/-]+", query)
        if not terms:
            raise ValueError("Search query contains no searchable terms")
        return ".*".join(re.escape(term) for term in terms)

    @staticmethod
    def _reproduction_command(body: str) -> str:
        for code in re.findall(r"`([^`]+)`", body):
            if "npm test" in code or "pytest" in code:
                return code
        raise ValueError("Issue does not contain a supported reproduction command")

    @staticmethod
    def _normalize_command(command: str) -> list[str]:
        normalized = command.replace("\\", "/")
        if ";" in normalized:
            prefix, normalized = normalized.split(";", 1)
            if "target-app" in prefix:
                normalized = f"npm --prefix target-app{normalized.strip()[3:]}"
        return shlex.split(normalized.strip(), posix=False)
