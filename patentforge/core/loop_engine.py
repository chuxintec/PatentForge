from __future__ import annotations

import json
import logging
from pathlib import Path

from patentforge.agents.reviewer_agent import ReviewerAgent
from patentforge.agents.writer_agent import WriterAgent
from patentforge.core.state import LoopResult, LoopState, ReviewResult
from patentforge.utils.code_style import build_output_filename, normalize_code_type


class LoopEngine:
    def __init__(
        self,
        writer: WriterAgent,
        reviewer: ReviewerAgent,
        max_iter: int = 5,
        output_dir: str | Path = "outputs",
        output_name: str = "sheji",
        code_type: str = "typescript",
        min_code_lines: int = 3500,
        max_code_lines: int = 4000,
        log_file: str | Path | None = None,
    ) -> None:
        self.writer = writer
        self.reviewer = reviewer
        self.max_iter = max(1, int(max_iter))
        self.output_dir = Path(output_dir)
        self.output_name = output_name
        self.code_type = normalize_code_type(code_type)
        self.min_code_lines = max(1, int(min_code_lines))
        self.max_code_lines = max(self.min_code_lines, int(max_code_lines))
        self.log_file = Path(log_file).expanduser().resolve() if log_file else None
        self.logger = logging.getLogger("patentforge")

    def run(self, design_spec: str) -> LoopResult:
        state = LoopState(design_spec=design_spec)
        self.logger.info(
            "Loop start: design_spec_chars=%s output=%s code_type=%s line_range=%s-%s max_iter=%s",
            len(design_spec or ""),
            self.output_name,
            self.code_type,
            self.min_code_lines,
            self.max_code_lines,
            self.max_iter,
        )
        last_review = ReviewResult(
            passed=False,
            issues=[],
            feedback="未执行审核。",
            raw_text="",
        )
        final_draft = ""
        output_path = self.output_dir / build_output_filename(self.output_name, self.code_type)

        for _ in range(self.max_iter):
            round_no = state.iteration + 1
            self.logger.info("Round %s/%s: writer started", round_no, self.max_iter)
            state.status = "writing"
            try:
                draft = self.writer.run(
                    design_spec=state.design_spec,
                    code_type=self.code_type,
                    output_name=output_path.name,
                    min_code_lines=self.min_code_lines,
                    max_code_lines=self.max_code_lines,
                    draft=state.draft,
                    feedback=state.feedback,
                    issues=last_review.issues,
                    iteration=state.iteration,
                    max_iter=self.max_iter,
                )
            except Exception:
                self.logger.exception("Round %s/%s: writer failed", round_no, self.max_iter)
                raise
            self.logger.info(
                "Round %s/%s: writer finished draft_chars=%s draft_lines=%s",
                round_no,
                self.max_iter,
                len(draft),
                len(draft.splitlines()),
            )

            self.logger.info("Round %s/%s: reviewer started", round_no, self.max_iter)
            state.status = "reviewing"
            try:
                review = self.reviewer.run(
                    design_spec=state.design_spec,
                    code_type=self.code_type,
                    output_name=output_path.name,
                    min_code_lines=self.min_code_lines,
                    max_code_lines=self.max_code_lines,
                    draft=draft,
                    iteration=state.iteration,
                    max_iter=self.max_iter,
                )
            except Exception:
                self.logger.exception("Round %s/%s: reviewer failed", round_no, self.max_iter)
                raise
            self.logger.info(
                "Round %s/%s: reviewer finished passed=%s issues=%s feedback=%s",
                round_no,
                self.max_iter,
                review.passed,
                len(review.issues),
                review.feedback or "（无）",
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
                self._persist(state, final_draft, output_path)
                self.logger.info("Loop finished after round %s: PASS", round_no)
                return LoopResult(
                    passed=True,
                    final_draft=final_draft,
                    review=last_review,
                    state=state,
                    output_dir=self.output_dir,
                    output_path=output_path,
                    log_file=self.log_file,
                )

            state.status = "refining"
            self.logger.info("Round %s/%s: feedback applied, continue to next round", round_no, self.max_iter)

        state.status = "done"
        self._persist(state, final_draft, output_path)
        self.logger.info("Loop finished after max rounds: STOPPED")
        return LoopResult(
            passed=False,
            final_draft=final_draft,
            review=last_review,
            state=state,
            output_dir=self.output_dir,
            output_path=output_path,
            log_file=self.log_file,
        )

    def _persist(self, state: LoopState, final_draft: str, output_path: Path) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        legacy_output = self.output_dir / "final.md"
        if legacy_output.exists() and legacy_output != output_path:
            legacy_output.unlink()
        output_path.write_text(
            final_draft.rstrip() + "\n",
            encoding="utf-8",
        )
        self.logger.info("Saved code file: %s", output_path)
        (self.output_dir / "logs.json").write_text(
            json.dumps(
                {
                    "design_spec": state.design_spec,
                    "code_type": self.code_type,
                    "output_name": output_path.name,
                    "log_file": str(self.log_file) if self.log_file else None,
                    "line_range": {
                        "min": self.min_code_lines,
                        "max": self.max_code_lines,
                    },
                    "status": state.status,
                    "iterations": state.logs,
                    "final_iteration": state.iteration,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.logger.info("Saved structured log: %s", self.output_dir / "logs.json")
