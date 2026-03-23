from __future__ import annotations

from patentforge.agents.base import AgentBase
from patentforge.utils.prompt_loader import build_writer_user_prompt


class WriterAgent(AgentBase):
    def run(
        self,
        project_brief: str,
        draft: str = "",
        feedback: str = "",
        iteration: int = 0,
        max_iter: int = 5,
    ) -> str:
        user_prompt = build_writer_user_prompt(
            project_brief=project_brief,
            draft=draft,
            feedback=feedback,
            iteration=iteration,
            max_iter=max_iter,
        )
        output = self.client.generate(self.model, self.system_prompt, user_prompt)
        cleaned = output.strip()
        if not cleaned:
            raise RuntimeError("Writer agent returned an empty response")
        return cleaned
