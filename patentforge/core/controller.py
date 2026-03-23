from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from patentforge.agents.reviewer_agent import ReviewerAgent
from patentforge.agents.writer_agent import WriterAgent
from patentforge.core.loop_engine import LoopEngine
from patentforge.core.state import LoopResult
from patentforge.llm.client import create_client
from patentforge.utils.code_style import normalize_code_type
from patentforge.utils.prompt_loader import repo_root


@dataclass(slots=True)
class ForgeConfig:
    design_spec: str
    max_iter: int = 5
    output_dir: Path = field(default_factory=lambda: repo_root() / "test_cases" / "outputs")
    output_name: str = "sheji"
    log_file: Path | None = None
    provider: str = "auto"
    api_key: str | None = None
    base_url: str | None = None
    code_type: str = "typescript"
    min_code_lines: int = 3500
    max_code_lines: int = 4000
    writer_model: str = "MiniMax-M2.7"
    reviewer_model: str = "qwen3.5-plus"
    writer_prompt_path: Path = field(
        default_factory=lambda: repo_root() / "prompts" / "writer.md"
    )
    reviewer_prompt_path: Path = field(
        default_factory=lambda: repo_root() / "prompts" / "reviewer.md"
    )


class PatentForgeController:
    def __init__(self, config: ForgeConfig) -> None:
        self.config = config
        self.code_type = normalize_code_type(config.code_type)
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
            output_name=config.output_name,
            code_type=self.code_type,
            min_code_lines=config.min_code_lines,
            max_code_lines=config.max_code_lines,
            log_file=config.log_file,
        )

    def run(self) -> LoopResult:
        return self.engine.run(self.config.design_spec)
