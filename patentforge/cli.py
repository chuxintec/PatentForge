from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from patentforge.core.controller import ForgeConfig, PatentForgeController
from patentforge.utils.prompt_loader import repo_root


DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ai-model.chuxinhudong.com/v1")
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_WRITER_MODEL = os.getenv("PATENTFORGE_WRITER_MODEL", "MiniMax-M2.7")
DEFAULT_REVIEWER_MODEL = os.getenv("PATENTFORGE_REVIEWER_MODEL", "qwen3.5-plus")


def _load_brief(args: argparse.Namespace) -> str:
    if args.brief:
        return args.brief.strip()
    if args.brief_file:
        return args.brief_file.read_text(encoding="utf-8").strip()
    if sys.stdin.isatty():
        raise SystemExit("Provide --brief, --brief-file, or pipe the brief via stdin.")
    return sys.stdin.read().strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PatentForge dual-agent loop")
    parser.add_argument("--brief", help="Project brief text")
    parser.add_argument("--brief-file", type=Path, help="Path to a brief file")
    parser.add_argument(
        "--writer-prompt",
        type=Path,
        default=repo_root() / "程序员Agent.md",
        help="Path to the writer prompt file",
    )
    parser.add_argument(
        "--reviewer-prompt",
        type=Path,
        default=repo_root() / "软著审核员Agent.md",
        help="Path to the reviewer prompt file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for final.md and logs.json",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=5,
        help="Maximum loop iterations",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "openai", "fallback"],
        default="auto",
        help="LLM provider selection",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--api-key",
        default=DEFAULT_API_KEY,
        help="API key for the OpenAI-compatible provider",
    )
    parser.add_argument(
        "--writer-model",
        default=DEFAULT_WRITER_MODEL,
        help="Model name used by the Writer agent",
    )
    parser.add_argument(
        "--reviewer-model",
        default=DEFAULT_REVIEWER_MODEL,
        help="Model name used by the Reviewer agent",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_brief = _load_brief(args)

    config = ForgeConfig(
        project_brief=project_brief,
        max_iter=args.max_iter,
        output_dir=args.output_dir,
        provider=args.provider,
        api_key=args.api_key,
        base_url=args.base_url,
        writer_model=args.writer_model,
        reviewer_model=args.reviewer_model,
        writer_prompt_path=args.writer_prompt,
        reviewer_prompt_path=args.reviewer_prompt,
    )

    result = PatentForgeController(config).run()
    print(result.summary())
    print(f"Final draft: {config.output_dir / 'final.md'}")
    print(f"Logs: {config.output_dir / 'logs.json'}")
    if not result.passed and result.review.feedback:
        print(f"Last feedback: {result.review.feedback}")
    return 0 if result.passed else 1
