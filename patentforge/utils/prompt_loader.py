from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path, base: Path | None = None) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        local_candidate = candidate.resolve()
        if local_candidate.exists():
            return local_candidate
        candidate = (base or repo_root()) / candidate
    return candidate.resolve()


def load_prompt_text(path: str | Path) -> str:
    prompt_path = resolve_path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def build_writer_user_prompt(
    project_brief: str,
    draft: str,
    feedback: str,
    iteration: int,
    max_iter: int,
) -> str:
    return f"""项目背景:
{project_brief.strip() or "（未提供）"}

当前草稿:
{draft.strip() or "（空）"}

审核反馈:
{feedback.strip() or "（无）"}

迭代信息:
第 {iteration + 1}/{max_iter} 轮。

请根据你的系统提示词直接输出完整结果。"""


def build_reviewer_user_prompt(
    project_brief: str,
    draft: str,
    iteration: int,
    max_iter: int,
) -> str:
    return f"""项目背景:
{project_brief.strip() or "（未提供）"}

待审草稿:
{draft.strip() or "（空）"}

迭代信息:
第 {iteration + 1}/{max_iter} 轮。

请严格按照你的系统提示词输出 JSON，字段必须包含 pass、issues、feedback。"""
