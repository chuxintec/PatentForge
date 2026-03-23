from __future__ import annotations

import json
import re

from patentforge.utils.code_style import build_output_filename, code_extension, code_type_label, normalize_code_type


def render_writer_output(user_prompt: str) -> str:
    design_spec = _extract_section(user_prompt, "设计说明书")
    code_type = _extract_code_type(user_prompt)
    output_name = _extract_section(user_prompt, "目标文件") or build_output_filename("sheji", code_type)
    min_lines, max_lines = _extract_line_range(user_prompt, default_min=3500, default_max=4000)
    title = _infer_title(design_spec, output_name)

    if code_type == "golang":
        return _build_golang_source(
            title=title,
            design_spec=design_spec,
            output_name=output_name,
            min_lines=min_lines,
            max_lines=max_lines,
        )
    return _build_typescript_source(
        title=title,
        design_spec=design_spec,
        output_name=output_name,
        min_lines=min_lines,
        max_lines=max_lines,
    )


def render_review_result(user_prompt: str) -> str:
    draft = _extract_section(user_prompt, "待审源码")
    if not draft:
        draft = _extract_section(user_prompt, "待审草稿")

    code_type = _extract_code_type(user_prompt)
    output_name = _extract_section(user_prompt, "目标文件") or build_output_filename("sheji", code_type)
    min_lines, max_lines = _extract_line_range(user_prompt, default_min=3500, default_max=4000)

    issues: list[str] = []
    line_count = len(draft.splitlines())

    if not draft.strip():
        issues.append("源码为空")

    if not (min_lines <= line_count <= max_lines):
        issues.append(f"源码行数不在目标范围内：{line_count}")

    if code_type == "typescript":
        if "function " not in draft and "class " not in draft and "type " not in draft:
            issues.append("缺少 TypeScript 代码特征")
    elif code_type == "golang":
        if "package main" not in draft or "func " not in draft:
            issues.append("缺少 Go 代码特征")

    if "```" in draft or "###" in draft or "## " in draft:
        issues.append("源码中仍包含 Markdown 痕迹")

    if output_name and not _matches_extension(output_name, code_type):
        issues.append("目标文件扩展名与代码类型不一致")

    passed = len(issues) == 0
    feedback = "单文件源码满足长度和类型要求。" if passed else "；".join(issues)

    return json.dumps(
        {
            "pass": passed,
            "issues": issues,
            "feedback": feedback,
        },
        ensure_ascii=False,
        indent=2,
    )


def _extract_section(text: str, header: str) -> str:
    marker = f"{header}:"
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    remainder = text[start:]
    next_headers = [
        "\n\n代码类型:",
        "\n\n目标文件:",
        "\n\n行数要求:",
        "\n\n当前草稿:",
        "\n\n审核反馈:",
        "\n\n审核问题:",
        "\n\n待审源码:",
        "\n\n待审草稿:",
        "\n\n迭代信息:",
    ]
    end = len(remainder)
    for next_header in next_headers:
        index = remainder.find(next_header)
        if index != -1:
            end = min(end, index)
    return remainder[:end].strip()


def _extract_code_type(user_prompt: str) -> str:
    raw = _extract_section(user_prompt, "代码类型")
    try:
        return normalize_code_type(raw)
    except ValueError:
        return "typescript"


def _extract_line_range(user_prompt: str, default_min: int, default_max: int) -> tuple[int, int]:
    raw = _extract_section(user_prompt, "行数要求")
    matches = [int(item) for item in re.findall(r"\d+", raw)]
    if len(matches) >= 2:
        low, high = matches[0], matches[1]
        if low > high:
            low, high = high, low
        return max(1, low), max(max(1, low), high)
    return default_min, default_max


def _matches_extension(output_name: str, code_type: str) -> bool:
    return output_name.lower().endswith(f".{code_extension(code_type)}")


def _infer_title(design_spec: str, output_name: str) -> str:
    for line in design_spec.splitlines():
        candidate = line.strip(" #\t")
        if candidate and candidate not in {"（未提供）", "未提供"}:
            return candidate[:64]
    stem = output_name.rsplit(".", 1)[0].strip()
    return stem or "软著项目"


def _build_typescript_source(
    title: str,
    design_spec: str,
    output_name: str,
    min_lines: int,
    max_lines: int,
) -> str:
    target = max(min_lines, min(max_lines, (min_lines + max_lines) // 2))
    stage_count = max(1, (target - 120) // 11)

    for _ in range(32):
        lines: list[str] = []
        lines.extend(
            [
                f"/**",
                f" * File: {output_name}",
                f" * Code type: {code_type_label('typescript')}",
                f" * Title: {title}",
                " *",
                " * 设计说明书摘要:",
            ]
        )
        for row in _compact_lines(design_spec, 8):
            lines.append(f" * {row}")
        lines.extend(
            [
                " */",
                "",
                "type StageOutcome = {",
                "  name: string;",
                "  passed: boolean;",
                "  score: number;",
                "  note: string;",
                "};",
                "",
                "type RuntimeContext = {",
                "  designSpec: string;",
                "  feedback: string;",
                "  seed: number;",
                "  fileName: string;",
                "};",
                "",
                "type PipelineReport = {",
                "  fileName: string;",
                "  codeType: string;",
                "  title: string;",
                "  passed: boolean;",
                "  issues: string[];",
                "  stages: StageOutcome[];",
                "};",
                "",
                "function normalizeText(value: string): string {",
                "  return value.replace(/\\s+/g, ' ').trim();",
                "}",
                "",
                "function hashText(value: string): number {",
                "  let hash = 0;",
                "  for (let index = 0; index < value.length; index += 1) {",
                "    hash = (hash * 31 + value.charCodeAt(index)) % 1000003;",
                "  }",
                "  return hash;",
                "}",
                "",
                "function buildContext(designSpec: string, feedback: string, fileName: string): RuntimeContext {",
                "  const normalized = normalizeText(designSpec || '');",
                "  return {",
                "    designSpec: normalized,",
                "    feedback: feedback || '',",
                "    seed: hashText(normalized + '|' + fileName),",
                "    fileName,",
                "  };",
                "}",
                "",
                "function summarize(stages: StageOutcome[]): string[] {",
                "  const issues: string[] = [];",
                "  for (const stage of stages) {",
                "    if (!stage.passed) {",
                "      issues.push(stage.note);",
                "    }",
                "  }",
                "  return issues;",
                "}",
                "",
            ]
        )

        for index in range(1, stage_count + 1):
            lines.extend(_typescript_stage_block(index))

        lines.append("const stageHandlers: Array<(ctx: RuntimeContext) => StageOutcome> = [")
        for index in range(1, stage_count + 1):
            lines.append(f"  evaluateStage{index:03d},")
        lines.append("];")
        lines.extend(
            [
                "",
                "function runPipeline(ctx: RuntimeContext): PipelineReport {",
                "  const stages = stageHandlers.map((handler) => handler(ctx));",
                "  const issues = summarize(stages);",
                "  return {",
                "    fileName: ctx.fileName,",
                f"    codeType: {json.dumps(code_type_label('typescript'))},",
                f"    title: {json.dumps(title)},",
                "    passed: issues.length === 0,",
                "    issues,",
                "    stages,",
                "  };",
                "}",
                "",
                "function renderReport(report: PipelineReport): string {",
                "  const lines: string[] = [];",
                "  lines.push(`file: ${report.fileName}`);",
                "  lines.push(`codeType: ${report.codeType}`);",
                "  lines.push(`title: ${report.title}`);",
                "  lines.push(`passed: ${report.passed}`);",
                "  lines.push('issues:');",
                "  for (const issue of report.issues) {",
                "    lines.push(`- ${issue}`);",
                "  }",
                "  return lines.join('\\n');",
                "}",
                "",
                "function main(): void {",
                f"  const designSpec = {json.dumps(design_spec[:2000])};",
                "  const feedback = '根据审核反馈持续修订单文件源码。';",
                f"  const ctx = buildContext(designSpec, feedback, {json.dumps(output_name)});",
                "  const report = runPipeline(ctx);",
                "  console.log(renderReport(report));",
                "}",
                "",
                "main();",
            ]
        )

        count = len(lines)
        if min_lines <= count <= max_lines:
            return "\n".join(lines).rstrip()
        if count < min_lines:
            stage_count += 1
        else:
            stage_count -= 1

    return "\n".join(lines).rstrip()


def _typescript_stage_block(index: int) -> list[str]:
    name = f"evaluateStage{index:03d}"
    label = f"stage{index:03d}"
    return [
        f"function {name}(ctx: RuntimeContext): StageOutcome {{",
        f"  const text = normalizeText(`${{ctx.designSpec}}|${{ctx.feedback}}|{index:03d}`);",
        "  const score = hashText(text) + ctx.seed + %d;" % index,
        f"  const note = score % 2 === 0 ? {json.dumps(label + ' stable')} : {json.dumps(label + ' needs review')};",
        "  const passed = score % 3 !== 0;",
        "  if (passed) {",
        f"    return {{ name: {json.dumps(label)}, passed: true, score, note }};",
        "  }",
        f"  return {{ name: {json.dumps(label)}, passed: false, score, note }};",
        "}",
        "",
    ]


def _build_golang_source(
    title: str,
    design_spec: str,
    output_name: str,
    min_lines: int,
    max_lines: int,
) -> str:
    target = max(min_lines, min(max_lines, (min_lines + max_lines) // 2))
    stage_count = max(1, (target - 140) // 11)

    for _ in range(32):
        lines: list[str] = []
        lines.extend(
            [
                "package main",
                "",
                "import (",
                '    "fmt"',
                '    "strings"',
                ")",
                "",
                "// File: " + output_name,
                "// Code type: " + code_type_label("golang"),
                "// Title: " + title,
                "// 设计说明书摘要:",
            ]
        )
        for row in _compact_lines(design_spec, 8):
            lines.append("// " + row)
        lines.extend(
            [
                "",
                "type stageOutcome struct {",
                "    name string",
                "    passed bool",
                "    score int",
                "    note string",
                "}",
                "",
                "type runtimeContext struct {",
                "    designSpec string",
                "    feedback string",
                "    seed int",
                "    fileName string",
                "}",
                "",
                "type pipelineReport struct {",
                "    fileName string",
                "    codeType string",
                "    title string",
                "    passed bool",
                "    issues []string",
                "    stages []stageOutcome",
                "}",
                "",
                "func normalizeText(value string) string {",
                "    return strings.Join(strings.Fields(value), \" \")",
                "}",
                "",
                "func hashText(value string) int {",
                "    hash := 0",
                "    for _, ch := range value {",
                "        hash = (hash*31 + int(ch)) % 1000003",
                "    }",
                "    return hash",
                "}",
                "",
                "func buildContext(designSpec string, feedback string, fileName string) runtimeContext {",
                "    normalized := normalizeText(designSpec)",
                "    return runtimeContext{",
                "        designSpec: normalized,",
                "        feedback: feedback,",
                "        seed: hashText(normalized + \"|\" + fileName),",
                "        fileName: fileName,",
                "    }",
                "}",
                "",
                "func summarize(stages []stageOutcome) []string {",
                "    issues := make([]string, 0, len(stages))",
                "    for _, stage := range stages {",
                "        if !stage.passed {",
                "            issues = append(issues, stage.note)",
                "        }",
                "    }",
                "    return issues",
                "}",
                "",
            ]
        )

        for index in range(1, stage_count + 1):
            lines.extend(_golang_stage_block(index))

        lines.append("var stageHandlers = []func(runtimeContext) stageOutcome{")
        for index in range(1, stage_count + 1):
            lines.append(f"    evaluateStage{index:03d},")
        lines.append("}")
        lines.extend(
            [
                "",
                "func runPipeline(ctx runtimeContext) pipelineReport {",
                "    stages := make([]stageOutcome, 0, len(stageHandlers))",
                "    for _, handler := range stageHandlers {",
                "        stages = append(stages, handler(ctx))",
                "    }",
                "    issues := summarize(stages)",
                "    return pipelineReport{",
                "        fileName: ctx.fileName,",
                f"        codeType: {json.dumps(code_type_label('golang'))},",
                f"        title: {json.dumps(title)},",
                "        passed: len(issues) == 0,",
                "        issues: issues,",
                "        stages: stages,",
                "    }",
                "}",
                "",
                "func renderReport(report pipelineReport) string {",
                "    lines := make([]string, 0, len(report.issues)+4)",
                "    lines = append(lines, fmt.Sprintf(\"file: %s\", report.fileName))",
                "    lines = append(lines, fmt.Sprintf(\"codeType: %s\", report.codeType))",
                "    lines = append(lines, fmt.Sprintf(\"title: %s\", report.title))",
                "    lines = append(lines, fmt.Sprintf(\"passed: %t\", report.passed))",
                "    lines = append(lines, \"issues:\")",
                "    for _, issue := range report.issues {",
                "        lines = append(lines, \"- \"+issue)",
                "    }",
                "    return strings.Join(lines, \"\\n\")",
                "}",
                "",
                "func main() {",
                f"    designSpec := {json.dumps(design_spec[:2000])}",
                "    feedback := \"根据审核反馈持续修订单文件源码。\"",
                f"    ctx := buildContext(designSpec, feedback, {json.dumps(output_name)})",
                "    report := runPipeline(ctx)",
                "    fmt.Println(renderReport(report))",
                "}",
            ]
        )

        count = len(lines)
        if min_lines <= count <= max_lines:
            return "\n".join(lines).rstrip()
        if count < min_lines:
            stage_count += 1
        else:
            stage_count -= 1

    return "\n".join(lines).rstrip()


def _golang_stage_block(index: int) -> list[str]:
    name = f"evaluateStage{index:03d}"
    label = f"stage{index:03d}"
    return [
        f"func {name}(ctx runtimeContext) stageOutcome {{",
        f"    text := normalizeText(fmt.Sprintf(\"%s|%s|{index:03d}\", ctx.designSpec, ctx.feedback))",
        f"    score := hashText(text) + ctx.seed + {index}",
        f"    note := fmt.Sprintf(\"{label} stable\")",
        "    if score%2 != 0 {",
        f"        note = fmt.Sprintf(\"{label} needs review\")",
        "    }",
        "    passed := score%3 != 0",
        f"    return stageOutcome{{name: {json.dumps(label)}, passed: passed, score: score, note: note}}",
        "}",
        "",
    ]


def _compact_lines(text: str, limit: int) -> list[str]:
    content = text.strip()
    if not content:
        return ["（未提供）"]
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return ["（未提供）"]
    compact: list[str] = []
    for line in lines[:limit]:
        compact.append(line[:90])
    if len(lines) > limit:
        compact.append("...")
    return compact
