from __future__ import annotations

from patentforge.agents.base import AgentBase
from patentforge.utils.prompt_loader import build_writer_user_prompt


class WriterAgent(AgentBase):
    def run(
        self,
        design_spec: str,
        code_type: str,
        output_name: str,
        min_code_lines: int,
        max_code_lines: int,
        draft: str = "",
        feedback: str = "",
        issues: list[str] | None = None,
        iteration: int = 0,
        max_iter: int = 5,
    ) -> str:
        user_prompt = build_writer_user_prompt(
            design_spec=design_spec,
            code_type=code_type,
            output_name=output_name,
            min_code_lines=min_code_lines,
            max_code_lines=max_code_lines,
            draft=draft,
            feedback=feedback,
            issues=issues or [],
            iteration=iteration,
            max_iter=max_iter,
        )
        output = self.client.generate(self.model, self.system_prompt, user_prompt)
        cleaned = output.strip()
        if not cleaned:
            raise RuntimeError("Writer agent returned an empty response")
        return cleaned
