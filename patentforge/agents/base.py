from __future__ import annotations

from pathlib import Path

from patentforge.llm.client import LLMClient
from patentforge.utils.prompt_loader import load_prompt_text


class AgentBase:
    def __init__(self, client: LLMClient, prompt_path: str | Path, model: str) -> None:
        self.client = client
        self.prompt_path = Path(prompt_path)
        self.model = model
        self.system_prompt = load_prompt_text(self.prompt_path)
