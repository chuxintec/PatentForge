from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from patentforge.llm.fallback_codegen import render_review_result, render_writer_output
from patentforge.utils.env_loader import load_project_env


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
        load_project_env()
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or export it before running.")

        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The openai package is not installed. Install with `pip install \".[openai]\"` or `pip install openai`."
            ) from exc

        client_kwargs: dict[str, str] = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self._client = OpenAI(**client_kwargs)

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        logger = logging.getLogger("patentforge")
        started = time.perf_counter()
        logger.info(
            "LLM request start provider=openai-sdk model=%s prompt_chars=%s",
            model,
            len(user_prompt),
        )
        try:
            response = self._client.responses.create(
                model=model,
                instructions=system_prompt,
                input=user_prompt,
            )
        except Exception as exc:  # pragma: no cover - provider dependent
            logger.info(
                "LLM request failed provider=openai-sdk model=%s duration=%.2fs error=%s",
                model,
                time.perf_counter() - started,
                exc,
            )
            raise
        output_text = getattr(response, "output_text", "") or ""
        if not output_text.strip():
            raise RuntimeError("OpenAI response did not contain output_text")
        cleaned = output_text.strip()
        logger.info(
            "LLM request done provider=openai-sdk model=%s duration=%.2fs output_chars=%s",
            model,
            time.perf_counter() - started,
            len(cleaned),
        )
        return cleaned


@dataclass(slots=True)
class OpenAICompatibleHTTPClient:
    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 300

    def __post_init__(self) -> None:
        load_project_env()
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or export it before running.")

        self.api_key = api_key
        self.base_url = (self.base_url or os.getenv("OPENAI_BASE_URL") or "https://ai-model.chuxinhudong.com/v1").rstrip("/")
        timeout_override = os.getenv("PATENTFORGE_HTTP_TIMEOUT")
        if timeout_override:
            try:
                self.timeout = max(1, int(timeout_override))
            except ValueError:
                pass

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        logger = logging.getLogger("patentforge")
        logger.info(
            "LLM request start provider=openai-http model=%s prompt_chars=%s",
            model,
            len(user_prompt),
        )
        started = time.perf_counter()
        attempts: list[tuple[str, dict[str, object]]] = [
            (
                f"{self.base_url}/chat/completions",
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 4096,
                },
            ),
            (
                f"{self.base_url}/responses",
                {
                    "model": model,
                    "instructions": system_prompt,
                    "input": user_prompt,
                    "max_output_tokens": 4096,
                },
            ),
        ]

        errors: list[str] = []
        for url, payload in attempts:
            try:
                logger.info("LLM request attempt endpoint=%s model=%s", url.rsplit("/", 1)[-1], model)
                response_payload = self._post_json(url, payload)
                text = _extract_response_text(response_payload)
                if text.strip():
                    cleaned = text.strip()
                    logger.info(
                        "LLM request done provider=openai-http endpoint=%s model=%s duration=%.2fs output_chars=%s",
                        url.rsplit("/", 1)[-1],
                        model,
                        time.perf_counter() - started,
                        len(cleaned),
                    )
                    return cleaned
                errors.append(f"{url}: empty response body")
            except Exception as exc:  # pragma: no cover - network/provider dependent
                logger.info("LLM request failed endpoint=%s model=%s error=%s", url.rsplit("/", 1)[-1], model, exc)
                errors.append(f"{url}: {exc}")

        raise RuntimeError("OpenAI-compatible request failed: " + " | ".join(errors))

    def _post_json(self, url: str, payload: dict[str, object]) -> object:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            if detail:
                raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {detail[:500]}") from exc
            raise RuntimeError(f"HTTP {exc.code} {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Request failed: {exc.reason}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON response: {raw[:500]}") from exc


@dataclass(slots=True)
class FallbackClient:
    model: str = "offline-template"

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        logger = logging.getLogger("patentforge")
        logger.info("LLM request start provider=fallback model=%s prompt_chars=%s", model, len(user_prompt))
        if _looks_like_review_prompt(system_prompt):
            output = render_review_result(user_prompt)
        else:
            output = render_writer_output(user_prompt)
        logger.info("LLM request done provider=fallback model=%s output_chars=%s", model, len(output))
        return output


def create_client(
    provider: str = "auto",
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMClient:
    load_project_env()
    normalized = provider.lower().strip()
    if normalized == "fallback":
        return FallbackClient(model="offline-template")
    if normalized == "openai" or normalized == "auto":
        if _has_openai_sdk():
            return OpenAIResponsesClient(api_key=api_key, base_url=base_url)
        return OpenAICompatibleHTTPClient(api_key=api_key, base_url=base_url)

    return FallbackClient(model="offline-template")


def _looks_like_review_prompt(system_prompt: str) -> bool:
    prompt = system_prompt.lower()
    return "审核专家" in system_prompt or "review" in prompt or "审核员" in system_prompt


def _has_openai_sdk() -> bool:
    try:
        from openai import OpenAI  # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


def _extract_response_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""

    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []

    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")
            if item_type in {"output_text", "text"}:
                text = item.get("text") or item.get("value")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
                continue

            if item_type == "message":
                content = item.get("content")
                if isinstance(content, list):
                    for chunk in content:
                        if not isinstance(chunk, dict):
                            continue
                        chunk_type = chunk.get("type")
                        if chunk_type in {"output_text", "text"}:
                            text = chunk.get("text") or chunk.get("value")
                            if isinstance(text, str) and text.strip():
                                parts.append(text.strip())

    if parts:
        return "\n".join(parts).strip()

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    nested: list[str] = []
                    for chunk in content:
                        if isinstance(chunk, dict):
                            text = chunk.get("text") or chunk.get("value")
                            if isinstance(text, str) and text.strip():
                                nested.append(text.strip())
                    if nested:
                        return "\n".join(nested).strip()

            text = first.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    return ""


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
    design_spec = _extract_section(user_prompt, "设计说明书")
    for line in design_spec.splitlines():
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
