from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ToolPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str

    @property
    def output_fingerprint(self) -> str:
        content = f"{self.return_code}\n{self.stdout}\n{self.stderr}".encode()
        return hashlib.sha256(content).hexdigest()[:16]


class RepositoryTools:
    DEFAULT_ALLOWED_COMMANDS = frozenset(
        {
            "git",
            "npm",
            "npx",
            "node",
            "python",
            "pytest",
        }
    )

    def __init__(
        self,
        root: str | Path,
        *,
        allowed_commands: frozenset[str] | None = None,
        max_output_chars: int = 20_000,
    ) -> None:
        self.root = Path(root).resolve()
        commands = allowed_commands or self.DEFAULT_ALLOWED_COMMANDS
        self.allowed_commands = frozenset(
            Path(command).name.lower() for command in commands
        )
        self.max_output_chars = max_output_chars

    def read_file(self, relative_path: str, start_line: int, end_line: int) -> str:
        path = self._resolve(relative_path)
        if start_line < 1 or end_line < start_line:
            raise ToolPolicyError("Invalid line range")
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[start_line - 1 : end_line])

    def search_code(
        self,
        query: str,
        *,
        paths: tuple[str, ...] = (".",),
        limit: int = 50,
    ) -> list[str]:
        if not query or limit < 1:
            raise ToolPolicyError("Search query and positive limit are required")

        pattern = re.compile(query, re.IGNORECASE)
        matches: list[str] = []
        for relative_path in paths:
            base = self._resolve(relative_path)
            candidates = [base] if base.is_file() else base.rglob("*")
            for candidate in candidates:
                if len(matches) >= limit:
                    return matches
                if not candidate.is_file() or self._is_excluded(candidate):
                    continue
                try:
                    lines = candidate.read_text(encoding="utf-8").splitlines()
                except UnicodeDecodeError:
                    continue
                for line_number, line in enumerate(lines, 1):
                    if pattern.search(line):
                        relative = candidate.relative_to(self.root)
                        matches.append(f"{relative}:{line_number}:{line.strip()}")
                        if len(matches) >= limit:
                            return matches
        return matches

    def run_command(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 120,
    ) -> CommandResult:
        if not command:
            raise ToolPolicyError("Command is required")
        executable = Path(command[0]).name.lower()
        if executable not in self.allowed_commands:
            raise ToolPolicyError(f"Command is not allowlisted: {executable}")
        resolved_executable = shutil.which(command[0])
        if resolved_executable is None:
            raise FileNotFoundError(f"Command was not found: {command[0]}")

        completed = subprocess.run(
            [resolved_executable, *command[1:]],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        return CommandResult(
            command=tuple(command),
            return_code=completed.returncode,
            stdout=completed.stdout[-self.max_output_chars :],
            stderr=completed.stderr[-self.max_output_chars :],
        )

    def git_diff(self) -> str:
        result = self.run_command(["git", "--no-pager", "diff", "--"])
        if result.return_code != 0:
            raise RuntimeError(result.stderr or "git diff failed")
        return result.stdout

    def apply_patch(self, patch: str) -> None:
        if not patch.strip():
            raise ToolPolicyError("Patch is empty")
        changed_paths = self._patch_paths(patch)
        if not changed_paths:
            raise ToolPolicyError("Patch contains no file paths")
        for path in changed_paths:
            self._validate_patch_path(path)

        completed = subprocess.run(
            ["git", "apply", "--whitespace=error", "-"],
            cwd=self.root,
            input=patch,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            raise ToolPolicyError(
                f"Patch could not be applied: {completed.stderr.strip()}"
            )

    def _resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if path != self.root and self.root not in path.parents:
            raise ToolPolicyError("Path escapes repository root")
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def _is_excluded(self, path: Path) -> bool:
        excluded_parts = {
            ".git",
            ".pytest_cache",
            "__pycache__",
            "build",
            "coverage",
            "dist",
            "node_modules",
        }
        return any(part in excluded_parts for part in path.parts)

    @staticmethod
    def _patch_paths(patch: str) -> set[str]:
        paths: set[str] = set()
        for line in patch.splitlines():
            if line.startswith(("+++ b/", "--- a/")):
                paths.add(line[6:])
        return paths

    def _validate_patch_path(self, relative_path: str) -> None:
        if relative_path == "/dev/null":
            return
        path = (self.root / relative_path).resolve()
        if path != self.root and self.root not in path.parents:
            raise ToolPolicyError("Patch path escapes repository root")
