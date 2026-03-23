from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from patentforge.agents.reviewer_agent import ReviewerAgent
from patentforge.agents.writer_agent import WriterAgent
from patentforge.core.loop_engine import LoopEngine
from patentforge.core.state import LoopResult
from patentforge.llm.client import create_client
from patentforge.utils.prompt_loader import repo_root


@dataclass(slots=True)
class ForgeConfig:
    project_brief: str
    max_iter: int = 5
    output_dir: Path = field(default_factory=lambda: Path("outputs"))
    provider: str = "auto"
    api_key: str | None = None
    base_url: str | None = None
    writer_model: str = "MiniMax-M2.7"
    reviewer_model: str = "qwen3.5-plus"
    writer_prompt_path: Path = field(
        default_factory=lambda: repo_root() / "程序员Agent.md"
    )
    reviewer_prompt_path: Path = field(
        default_factory=lambda: repo_root() / "软著审核员Agent.md"
    )


class PatentForgeController:
    def __init__(self, config: ForgeConfig) -> None:
        self.config = config
        client = create_client(
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.writer = WriterAgent(client, config.writer_prompt_path, config.writer_model)
        self.reviewer = ReviewerAgent(
            client,
            config.reviewer_prompt_path,
            config.reviewer_model,
        )
        self.engine = LoopEngine(
            self.writer,
            self.reviewer,
            max_iter=config.max_iter,
            output_dir=config.output_dir,
        )

    def run(self) -> LoopResult:
        return self.engine.run(self.config.project_brief)
