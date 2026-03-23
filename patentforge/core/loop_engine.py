from __future__ import annotations

import json
from pathlib import Path

from patentforge.agents.reviewer_agent import ReviewerAgent
from patentforge.agents.writer_agent import WriterAgent
from patentforge.core.state import LoopResult, LoopState, ReviewResult


class LoopEngine:
    def __init__(
        self,
        writer: WriterAgent,
        reviewer: ReviewerAgent,
        max_iter: int = 5,
        output_dir: str | Path = "outputs",
    ) -> None:
        self.writer = writer
        self.reviewer = reviewer
        self.max_iter = max(1, int(max_iter))
        self.output_dir = Path(output_dir)

    def run(self, project_brief: str) -> LoopResult:
        state = LoopState(project_brief=project_brief)
        last_review = ReviewResult(
            passed=False,
            issues=["未开始审查"],
            feedback="未执行审核。",
            raw_text="",
        )
        final_draft = ""

        for _ in range(self.max_iter):
            state.status = "writing"
            draft = self.writer.run(
                project_brief=state.project_brief,
                draft=state.draft,
                feedback=state.feedback,
                iteration=state.iteration,
                max_iter=self.max_iter,
            )

            state.status = "reviewing"
            review = self.reviewer.run(
                project_brief=state.project_brief,
                draft=draft,
                iteration=state.iteration,
                max_iter=self.max_iter,
            )

            state.logs.append(
                {
                    "iteration": state.iteration + 1,
                    "status": state.status,
                    "draft": draft,
                    "review": review.to_dict(),
                }
            )

            state.draft = draft
            state.feedback = review.feedback
            state.iteration += 1
            final_draft = draft
            last_review = review

            if review.passed:
                state.status = "done"
                self._persist(state, final_draft)
                return LoopResult(
                    passed=True,
                    final_draft=final_draft,
                    review=last_review,
                    state=state,
                    output_dir=self.output_dir,
                )

            state.status = "refining"

        state.status = "done"
        self._persist(state, final_draft)
        return LoopResult(
            passed=False,
            final_draft=final_draft,
            review=last_review,
            state=state,
            output_dir=self.output_dir,
        )

    def _persist(self, state: LoopState, final_draft: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "final.md").write_text(
            final_draft.rstrip() + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "logs.json").write_text(
            json.dumps(
                {
                    "project_brief": state.project_brief,
                    "status": state.status,
                    "iterations": state.logs,
                    "final_iteration": state.iteration,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
