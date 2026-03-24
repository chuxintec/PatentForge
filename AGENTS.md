# AGENTS.md - PatentForge Agent 工作指南

本文档为在 PatentForge 仓库中工作的 AI Agent 提供开发规范和操作指引。

---

## 一、项目概述

PatentForge 是一个基于 Codex 的双 Agent 软著自动生成系统：
- **Code-Writer**：根据设计说明书生成软著源代码
- **Code-Reviewer**：审核设计说明书和源代码，输出结构化结论

### 核心技术栈
- **语言**：TypeScript / Golang
- **模型**：MiniMax-M2.7 (Writer), qwen3.5-plus (Reviewer)
- **配置**：opencode.json

---

## 二、输入输出规范

### 2.1 输入目录
- **目录**：`test_cases/`
- **设计说明书**：直接放在 `test_cases/` 目录下，如 `test_cases/sheji.md`

### 2.2 输出目录
- **目录**：`test_cases/outputs/`
- **代码文件**：Code-Writer 必须将生成的源代码写入 `test_cases/outputs/` 目录
- **审核结论**：Code-Reviewer 必须将审核报告写入 `test_cases/outputs/` 目录
- **日志文件**：`test_cases/outputs/patentforge.log`, `test_cases/outputs/logs.json`

### 2.3 输出文件名规范
- TypeScript 源码：`<设计说明书名称>.ts`（如 `sheji.ts`）
- Golang 源码：`<设计说明书名称>.go`（如 `sheji.go`）
- 审核报告：`<设计说明书名称>_audit_report.md`（如 `sheji_audit_report.md`）

---

## 三、运行命令

### 3.1 基础运行
```bash
# 默认运行（读取 test_cases/sheji.md）
python -m patentforge --design-file test_cases/sheji.md --provider openai --code-type typescript

# 完整参数示例
python -m patentforge \
  --design-file test_cases/sheji.md \
  --provider openai \
  --code-type typescript \
  --min-lines 3500 \
  --max-lines 4000 \
  --output-name sheji \
  --writer-model MiniMax-M2.7 \
  --reviewer-model qwen3.5-plus
```

### 3.2 常用参数
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--design-file` | 设计说明书路径 | 必填 |
| `--provider` | LLM 提供商 | auto |
| `--code-type` | 代码类型 | typescript |
| `--min-lines` | 最小行数 | 3500 |
| `--max-lines` | 最大行数 | 4000 |
| `--output-name` | 输出文件名 | 自动推断 |
| `--max-iter` | 最大迭代次数 | 5 |

### 3.3 环境变量
```bash
# 配置 API
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://ai-model.chuxinhudong.com/v1"

# 配置模型
export PATENTFORGE_WRITER_MODEL="MiniMax-M2.7"
export PATENTFORGE_REVIEWER_MODEL="qwen3.5-plus"
```

---

## 四、代码风格规范

### 4.1 总体原则
1. **业务优先**：围绕真实业务功能展开，不堆砌空架构
2. **真实实现**：禁止空实现、假实现、占位实现
3. **单文件结构**：所有代码必须写入单一文件
4. **调用链完整**：入口 → 配置读取 → 业务处理 → 输出结果

### 4.2 命名规范
- **类名**：PascalCase（如 `ConfigManager`）
- **函数名**：camelCase（如 `loadConfig`）
- **常量**：UPPER_SNAKE_CASE
- **文件命名**：kebab-case（如 `sheji.ts`）

### 4.3 类型定义
- 优先使用 TypeScript 原生类型
- 避免过度抽象的 interface / enum
- 尽量使用 `type` 代替简单枚举

### 4.4 注释规范
- 使用英文 Section 标记分区（如 `// Section: Type Definitions`）
- 避免批量中文 JSDoc
- 关键逻辑添加必要注释

### 4.5 错误处理
- 使用 try-catch 捕获关键异常
- 提供有意义的错误信息
- 记录日志而非静默吞掉错误

### 4.6 禁止的高风险写法
```
❌ Math.random() 作为业务逻辑
❌ return true/false 空实现
❌ 大量 interface/enum 堆砌
❌ 每个类都使用单例模式
❌ 过度统一的代码风格
❌ 纯模板化的注释结构
```

---

## 五、Agent 工作流程

### 5.1 Code-Writer 工作规范
1. 读取 `test_cases/` 下的设计说明书
2. 根据设计说明书生成单文件源码
3. 代码必须：
   - 包含真实业务逻辑
   - 体现设计说明书中的模块
   - 行数落在目标范围内（3500-4000）
4. 输出到 `test_cases/outputs/<name>.ts` 或 `.go`

### 5.2 Code-Reviewer 工作规范
1. 读取设计说明书和生成的代码
2. 从两个维度审核：
   - AI 生成痕迹
   - 软著审核风险
3. 输出结构化审核结论
4. 审核报告必须写入 `test_cases/outputs/<name>_audit_report.md`

### 5.3 迭代流程
```
Writer 生成代码 → Reviewer 审核 → 反馈 → Writer 优化 → ... → 通过或达到最大迭代次数
```

---

## 六、现有 Agent 规范文件

### 6.1 核心规范
| 文件 | 说明 |
|------|------|
| `agent/programmer.md` | Code-Writer 系统提示 |
| `agent/reviewer.md` | Code-Reviewer 系统提示 |
| `opencode.json` | OpenCode Agent 配置 |

### 6.2 输出示例
- 源码：`test_cases/outputs/sheji.ts`
- 审核报告：`test_cases/outputs/sheji_audit_report.md`
- 运行日志：`test_cases/outputs/patentforge.log`
- 结构化日志：`test_cases/outputs/logs.json`

---

## 七、常见问题处理

### 7.1 行数不足
- 检查是否包含足够的业务逻辑
- 避免空函数、无效注释占用行数
- 补充真实实现代码

### 7.2 AI 痕迹过重
- 减少批量重复的代码结构
- 避免所有类使用相同单例模式
- 删除模板化的中文注释
- 使用真实的配置判定替代 Math.random()

### 7.3 审核不通过
- 优先修改必改项（P0）
- 检查是否与设计说明书一致
- 确保调用链完整

---

*本文档最后更新：2026-03-24*
*适用版本：PatentForge v1.0.0*
