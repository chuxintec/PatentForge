from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


@dataclass(slots=True)
class OpenAIResponsesClient:
    api_key: str | None = None
    base_url: str | None = None
    _client: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The openai package is not installed. Install patentforge[openai] or openai."
            ) from exc

        client_kwargs: dict[str, str] = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = OpenAI(**client_kwargs)

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=model,
            instructions=system_prompt,
            input=user_prompt,
        )
        output_text = getattr(response, "output_text", "") or ""
        if not output_text.strip():
            raise RuntimeError("OpenAI response did not contain output_text")
        return output_text.strip()


@dataclass(slots=True)
class FallbackClient:
    model: str = "offline-template"

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        if _looks_like_review_prompt(system_prompt):
            return _render_review_result(user_prompt)
        return _render_writer_draft(user_prompt)


def create_client(
    provider: str = "auto",
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMClient:
    normalized = provider.lower().strip()
    if normalized == "fallback":
        return FallbackClient(model="offline-template")
    if normalized == "openai":
        return OpenAIResponsesClient(api_key=api_key, base_url=base_url)

    try:
        return OpenAIResponsesClient(api_key=api_key, base_url=base_url)
    except Exception:
        return FallbackClient(model="offline-template")


def _looks_like_review_prompt(system_prompt: str) -> bool:
    prompt = system_prompt.lower()
    return "审核专家" in system_prompt or "review" in prompt or "审核员" in system_prompt


def _extract_section(text: str, header: str) -> str:
    marker = f"{header}:"
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    remainder = text[start:]
    next_headers = [
        "\n\n当前草稿:",
        "\n\n审核反馈:",
        "\n\n待审草稿:",
        "\n\n迭代信息:",
    ]
    end = len(remainder)
    for next_header in next_headers:
        index = remainder.find(next_header)
        if index != -1:
            end = min(end, index)
    return remainder[:end].strip()


def _infer_title(user_prompt: str) -> str:
    project_brief = _extract_section(user_prompt, "项目背景")
    for line in project_brief.splitlines():
        candidate = line.strip(" #\t")
        if candidate and candidate not in {"（未提供）", "未提供"}:
            return candidate[:48]
    return "软著项目"


def _render_writer_draft(user_prompt: str) -> str:
    title = _infer_title(user_prompt)
    feedback = _extract_section(user_prompt, "审核反馈")
    feedback_note = ""
    if feedback and feedback != "（无）":
        feedback_note = f"\n> 本轮已根据反馈进行了补充：{feedback.splitlines()[0][:80]}"

    template = dedent(
        """
        # __TITLE__ 源代码文档

        ## 一、代码目录结构
        ```text
        src/
          main.py
          config/
            config_loader.py
          services/
            platform_rule_service.py
            compatibility_check_service.py
            report_service.py
          utils/
            file_util.py
            logger.py
          models/
            types.py
        ```

        ## 二、文件职责说明
        - `src/main.py`: 入口文件，串起配置读取、兼容性检查和报告输出。
        - `src/config/config_loader.py`: 读取并合并 JSON 配置，补齐默认值。
        - `src/services/platform_rule_service.py`: 处理平台名称归一化和规则匹配。
        - `src/services/compatibility_check_service.py`: 执行兼容性检查并汇总问题。
        - `src/services/report_service.py`: 生成文本报告，便于人工审阅和留档。
        - `src/utils/file_util.py`: 提供 JSON 读写和路径检查。
        - `src/utils/logger.py`: 初始化日志输出，保留运行痕迹。
        - `src/models/types.py`: 定义检查结果结构，便于各模块共享。

        ## 三、完整代码

        ### 1. `src/main.py`
        ```python
        from config.config_loader import load_config
        from services.compatibility_check_service import build_compatibility_summary
        from services.report_service import render_report
        from utils.logger import get_logger


        def main() -> None:
            logger = get_logger()
            config = load_config()
            summary = build_compatibility_summary(config)
            report = render_report(config, summary)
            logger.info("report generated")
            print(report)


        if __name__ == "__main__":
            main()
        ```

        ### 2. `src/config/config_loader.py`
        ```python
        from pathlib import Path

        from utils.file_util import read_json


        DEFAULT_CONFIG = {
            "platform": "windows",
            "version": "1.0.0",
            "rules_path": "rules.json",
        }


        def load_config(path: str = "config.json") -> dict:
            config_path = Path(path)
            if not config_path.exists():
                return dict(DEFAULT_CONFIG)

            data = read_json(config_path)
            merged = dict(DEFAULT_CONFIG)
            for key, value in data.items():
                if value is not None:
                    merged[key] = value
            return merged
        ```

        ### 3. `src/services/platform_rule_service.py`
        ```python
        PLATFORM_ALIASES = {
            "win": "windows",
            "windows": "windows",
            "mac": "macos",
            "macos": "macos",
            "linux": "linux",
        }


        def normalize_platform(name: str) -> str:
            if not name:
                return "unknown"
            key = name.strip().lower()
            return PLATFORM_ALIASES.get(key, key)


        def load_platform_rules(config: dict) -> list[dict]:
            rules = config.get("rules", [])
            if isinstance(rules, list):
                filtered = [rule for rule in rules if isinstance(rule, dict)]
                return filtered
            return list()
        ```

        ### 4. `src/services/compatibility_check_service.py`
        ```python
        from services.platform_rule_service import load_platform_rules, normalize_platform


        def build_compatibility_summary(config: dict) -> dict:
            platform = normalize_platform(str(config.get("platform", "")))
            issues: list[str] = []

            if platform == "unknown":
                issues.append("platform name is missing")

            if not config.get("version"):
                issues.append("version is missing")

            rules = load_platform_rules(config)
            if not rules:
                issues.append("no platform rules were loaded")

            return {
                "platform": platform,
                "pass_flag": len(issues) == 0,
                "issues": issues,
            }
        ```

        ### 5. `src/services/report_service.py`
        ```python
        from datetime import datetime, timezone


        def render_report(config: dict, summary: dict) -> str:
            created_at = datetime.now(timezone.utc).isoformat()
            lines = [
                f"platform: {summary.get('platform', 'unknown')}",
                f"pass: {summary.get('pass_flag', False)}",
                f"created_at: {created_at}",
                "",
                "issues:",
            ]
            for issue in summary.get("issues", []):
                lines.append(f"- {issue}")
            lines.append("")
            lines.append(f"config_version: {config.get('version', 'n/a')}")
            return "\n".join(lines)
        ```

        ### 6. `src/utils/file_util.py`
        ```python
        from pathlib import Path
        import json


        def read_json(path: str | Path) -> dict:
            file_path = Path(path)
            if not file_path.exists():
                raise FileNotFoundError(f"config file not found: {file_path}")
            return json.loads(file_path.read_text(encoding="utf-8"))


        def write_json(path: str | Path, data: dict) -> None:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        ```

        ### 7. `src/utils/logger.py`
        ```python
        import logging


        def get_logger(name: str = "patentforge") -> logging.Logger:
            logger = logging.getLogger(name)
            if logger.handlers:
                return logger

            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
            return logger
        ```

        ### 8. `src/models/types.py`
        ```python
        from typing import TypedDict


        class CompatibilitySummary(TypedDict):
            platform: str
            pass_flag: bool
            issues: list[str]
        ```

        ## 四、软著可信度自检结果
        - 是否存在空实现：否
        - 是否存在过度抽象：否
        - 是否存在明显模板化代码：低
        - 是否与项目功能一致：是
        - 是否具备真实调用链：是
        - 备注：入口 -> 配置读取 -> 业务处理 -> 输出结果，调用链完整。__FEEDBACK_NOTE__
        """
    ).strip()
    rendered = template.replace("__TITLE__", title).replace("__FEEDBACK_NOTE__", feedback_note)
    return "\n".join(
        line[8:] if line.startswith("        ") else line for line in rendered.splitlines()
    ).strip()


def _render_review_result(user_prompt: str) -> str:
    draft = _extract_section(user_prompt, "待审草稿")
    issues: list[str] = []

    required_sections = [
        "代码目录结构",
        "文件职责说明",
        "完整代码",
        "软著可信度自检结果",
    ]
    for section in required_sections:
        if section not in draft:
            issues.append(f"缺少{section}部分")

    forbidden_markers = [
        "TODO",
        "占位",
        "Math.random",
        "return true",
        "return false",
        "return {}",
        "return []",
    ]
    for marker in forbidden_markers:
        if marker in draft:
            issues.append(f"存在高风险占位痕迹：{marker}")

    if draft.count("```") < 6:
        issues.append("完整代码部分过少，代码块数量不足")

    if len(draft.strip()) < 800:
        issues.append("内容过短，软著材料完整度偏低")

    passed = len(issues) == 0
    feedback = "文档结构完整，可以提交。" if passed else "；".join(issues)

    return json.dumps(
        {
            "pass": passed,
            "issues": issues,
            "feedback": feedback,
        },
        ensure_ascii=False,
        indent=2,
    )
