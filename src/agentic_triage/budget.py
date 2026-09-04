from __future__ import annotations

from dataclasses import dataclass, field

from agentic_triage.models import UsageRecord


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class BudgetTracker:
    max_cost_usd: float
    records: list[UsageRecord] = field(default_factory=list)

    @property
    def spent_usd(self) -> float:
        return sum(record.estimated_cost_usd for record in self.records)

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_cost_usd - self.spent_usd)

    def record(self, usage: UsageRecord) -> None:
        projected = self.spent_usd + usage.estimated_cost_usd
        if projected > self.max_cost_usd:
            raise BudgetExceededError(
                f"Run budget exceeded: ${projected:.4f} > ${self.max_cost_usd:.4f}"
            )
        self.records.append(usage)
