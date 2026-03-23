from __future__ import annotations

from pathlib import Path

from patentforge.utils.code_style import code_type_label


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
    design_spec: str,
    code_type: str,
    output_name: str,
    min_code_lines: int,
    max_code_lines: int,
    draft: str,
    feedback: str,
    issues: list[str],
    iteration: int,
    max_iter: int,
) -> str:
    issue_block = "\n".join(f"- {item}" for item in issues if str(item).strip()) or "- （无）"
    return f"""设计说明书:
{design_spec.strip() or "（未提供）"}

代码类型:
{code_type_label(code_type)}

目标文件:
{output_name}

行数要求:
{min_code_lines}-{max_code_lines} 行

当前草稿:
{draft.strip() or "（空）"}

审核反馈:
{feedback.strip() or "（无）"}

审核问题:
{issue_block}

迭代信息:
第 {iteration + 1}/{max_iter} 轮。

请只输出单文件源码，不要解释、不要 Markdown、不要多文件。"""


def build_reviewer_user_prompt(
    design_spec: str,
    code_type: str,
    output_name: str,
    min_code_lines: int,
    max_code_lines: int,
    draft: str,
    iteration: int,
    max_iter: int,
) -> str:
    return f"""设计说明书:
{design_spec.strip() or "（未提供）"}

代码类型:
{code_type_label(code_type)}

目标文件:
{output_name}

行数要求:
{min_code_lines}-{max_code_lines} 行

待审源码:
{draft.strip() or "（空）"}

迭代信息:
第 {iteration + 1}/{max_iter} 轮。

请严格按照你的系统提示词输出 JSON，字段必须包含 pass、issues、feedback。"""
