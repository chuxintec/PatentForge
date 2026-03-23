from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LoopState:
    project_brief: str
    draft: str = ""
    feedback: str = ""
    iteration: int = 0
    status: str = "init"
    logs: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ReviewResult:
    passed: bool
    issues: list[str]
    feedback: str
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass": self.passed,
            "issues": list(self.issues),
            "feedback": self.feedback,
            "raw_text": self.raw_text,
        }


@dataclass(slots=True)
class LoopResult:
    passed: bool
    final_draft: str
    review: ReviewResult
    state: LoopState
    output_dir: Path

    def summary(self) -> str:
        status = "PASS" if self.passed else "STOPPED"
        lines = [
            f"Result: {status}",
            f"Iterations: {self.state.iteration}",
            f"Output: {self.output_dir / 'final.md'}",
        ]
        if self.review.feedback:
            lines.append(f"Feedback: {self.review.feedback}")
        return "\n".join(lines)
