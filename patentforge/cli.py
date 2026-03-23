from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from patentforge.core.controller import ForgeConfig, PatentForgeController
from patentforge.utils.code_style import default_output_name, normalize_code_type
from patentforge.utils.env_loader import load_project_env
from patentforge.utils.logging_setup import configure_logging
from patentforge.utils.prompt_loader import repo_root


DEFAULT_PROMPT_DIR = repo_root() / "prompts"
DEFAULT_OUTPUT_DIR = repo_root() / "test_cases" / "outputs"


def _load_design_text(args: argparse.Namespace) -> str:
    if args.design_text:
        return args.design_text.strip()
    if args.design_file:
        return args.design_file.read_text(encoding="utf-8").strip()
    if sys.stdin.isatty():
        raise SystemExit("Provide --design, --design-file, or pipe the design spec via stdin.")
    return sys.stdin.read().strip()


def build_parser() -> argparse.ArgumentParser:
    load_project_env()
    default_base_url = os.getenv("OPENAI_BASE_URL", "https://ai-model.chuxinhudong.com/v1")
    default_api_key = os.getenv("OPENAI_API_KEY")
    default_writer_model = os.getenv("PATENTFORGE_WRITER_MODEL", "MiniMax-M2.7")
    default_reviewer_model = os.getenv("PATENTFORGE_REVIEWER_MODEL", "qwen3.5-plus")
    default_code_type = os.getenv("PATENTFORGE_CODE_TYPE", "typescript")
    default_min_lines = int(os.getenv("PATENTFORGE_MIN_CODE_LINES", "3500"))
    default_max_lines = int(os.getenv("PATENTFORGE_MAX_CODE_LINES", "4000"))
    default_output_name_env = os.getenv("PATENTFORGE_OUTPUT_NAME")
    default_log_level = os.getenv("PATENTFORGE_LOG_LEVEL", "INFO")

    parser = argparse.ArgumentParser(description="PatentForge dual-agent loop")
    parser.add_argument("--design", "--brief", dest="design_text", help="Design specification text")
    parser.add_argument(
        "--design-file",
        "--brief-file",
        dest="design_file",
        type=Path,
        help="Path to a design specification file such as sheji.md",
    )
    parser.add_argument(
        "--writer-prompt",
        type=Path,
        default=DEFAULT_PROMPT_DIR / "writer.md",
        help="Path to the writer prompt file (default: prompts/writer.md)",
    )
    parser.add_argument(
        "--reviewer-prompt",
        type=Path,
        default=DEFAULT_PROMPT_DIR / "reviewer.md",
        help="Path to the reviewer prompt file (default: prompts/reviewer.md)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the generated code file and logs.json (default: test_cases/outputs)",
    )
    parser.add_argument(
        "--output-name",
        default=default_output_name_env,
        help="Base name of the generated code file; defaults to the design file stem",
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
        default=default_base_url,
        help="OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--code-type",
        default=default_code_type,
        help="Code type used by the Writer and Reviewer (typescript/ts or golang/go)",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=default_min_lines,
        help="Minimum expected code lines",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=default_max_lines,
        help="Maximum expected code lines",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to the live process log file (default: <output-dir>/patentforge.log)",
    )
    parser.add_argument(
        "--log-level",
        default=default_log_level,
        help="Log level for live process logs (default: INFO)",
    )
    parser.add_argument(
        "--api-key",
        default=default_api_key,
        help="API key for the OpenAI-compatible provider (.env or env var)",
    )
    parser.add_argument(
        "--writer-model",
        default=default_writer_model,
        help="Model name used by the Writer agent",
    )
    parser.add_argument(
        "--reviewer-model",
        default=default_reviewer_model,
        help="Model name used by the Reviewer agent",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    design_text = _load_design_text(args)
    try:
        code_type = normalize_code_type(args.code_type)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_name = args.output_name
    if not output_name:
        output_name = default_output_name(args.design_file)

    if args.min_lines > args.max_lines:
        raise SystemExit("--min-lines must be less than or equal to --max-lines")

    log_file = args.log_file or (args.output_dir / "patentforge.log")
    logger = configure_logging(log_file=log_file, level=args.log_level)
    logger.info(
        "Start PatentForge: code_type=%s output_name=%s max_iter=%s line_range=%s-%s provider=%s",
        code_type,
        output_name,
        args.max_iter,
        args.min_lines,
        args.max_lines,
        args.provider,
    )
    logger.info("Process log file: %s", Path(log_file).expanduser().resolve())
    logger.info("Structured log file: %s", (args.output_dir / "logs.json").expanduser().resolve())

    config = ForgeConfig(
        design_spec=design_text,
        max_iter=args.max_iter,
        output_dir=args.output_dir,
        output_name=output_name,
        provider=args.provider,
        api_key=args.api_key,
        base_url=args.base_url,
        code_type=code_type,
        min_code_lines=args.min_lines,
        max_code_lines=args.max_lines,
        log_file=Path(log_file),
        writer_model=args.writer_model,
        reviewer_model=args.reviewer_model,
        writer_prompt_path=args.writer_prompt,
        reviewer_prompt_path=args.reviewer_prompt,
    )

    try:
        result = PatentForgeController(config).run()
    except Exception:
        logger.exception("PatentForge run failed")
        return 1
    logger.info("Result: %s", "PASS" if result.passed else "STOPPED")
    logger.info("Iterations: %s", result.state.iteration)
    logger.info("Final code: %s", result.output_path)
    logger.info("Process log: %s", result.log_file or log_file)
    logger.info("Structured log: %s", config.output_dir / "logs.json")
    if not result.passed and result.review.feedback:
        logger.info("Last feedback: %s", result.review.feedback)
    return 0 if result.passed else 1
