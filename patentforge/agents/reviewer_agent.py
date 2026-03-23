from __future__ import annotations

import json
import re

from patentforge.agents.base import AgentBase
from patentforge.core.state import ReviewResult
from patentforge.utils.prompt_loader import build_reviewer_user_prompt


class ReviewerAgent(AgentBase):
    def run(
        self,
        project_brief: str,
        draft: str,
        iteration: int = 0,
        max_iter: int = 5,
    ) -> ReviewResult:
        user_prompt = build_reviewer_user_prompt(
            project_brief=project_brief,
            draft=draft,
            iteration=iteration,
            max_iter=max_iter,
        )
        raw_text = self.client.generate(self.model, self.system_prompt, user_prompt)
        return parse_review_result(raw_text)


def parse_review_result(raw_text: str) -> ReviewResult:
    text = raw_text.strip()
    candidate = text

    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        candidate = fenced[0].strip()

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.S)
        if not match:
            return ReviewResult(
                passed=False,
                issues=["审核结果无法解析为 JSON"],
                feedback="Reviewer did not return parseable JSON.",
                raw_text=raw_text,
            )
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return ReviewResult(
                passed=False,
                issues=["审核结果 JSON 解析失败"],
                feedback="Reviewer output looked like JSON but could not be decoded.",
                raw_text=raw_text,
            )

    passed = bool(data.get("pass", data.get("passed", False)))
    issues = data.get("issues") or []
    if isinstance(issues, str):
        issues = [issues]

    normalized_issues = [str(item) for item in issues if str(item).strip()]
    feedback = str(data.get("feedback", "")).strip()
    if not feedback and not passed:
        feedback = "需要补充有效的审核反馈。"

    return ReviewResult(
        passed=passed,
        issues=normalized_issues,
        feedback=feedback,
        raw_text=raw_text,
    )
