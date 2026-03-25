# AGENTS.md - PatentForge Agent 工作指南

本文档为在 PatentForge 仓库中工作的 AI Agent 提供开发规范、目录约束与角色协作说明。

---

## 一、项目概述

PatentForge 当前采用 **编排智能体 + Writer + Reviewer** 的协作架构：

- **Orchestrator**：负责流程编排与结果落盘
- **Code-Writer**：根据设计说明书生成软著源代码
- **Code-Reviewer**：审核设计说明书和源代码，输出结构化结论

### 核心技术栈
- **语言**：TypeScript / Golang
- **模型**：gpt-5.4 (Orchestrator), MiniMax-M2.5 (Writer), qwen3.5-plus (Reviewer)
- **配置文件**：`opencode.json`
- **角色规则**：`agent/orchestrator.md`, `agent/programmer.md`, `agent/reviewer.md`

---

## 二、输入输出规范

### 2.1 输入目录
- **目录**：`test_cases/`
- **设计说明书**：直接放在 `test_cases/` 下，如 `test_cases/sheji.md`

### 2.2 输出目录
- **目录**：`test_cases/outputs/`
- **代码文件**：Code-Writer 生成的源代码必须写入该目录
- **审核结论**：Code-Reviewer 产出的审核内容必须最终写入该目录
- **日志文件**：`test_cases/outputs/patentforge.log`, `test_cases/outputs/logs.json`

### 2.3 输出文件名规范
- TypeScript 源码：`<设计说明书名称>.ts`
- Golang 源码：`<设计说明书名称>.go`
- 审核报告：`<设计说明书名称>_audit_report.md`

示例：
- `test_cases/outputs/sheji.ts`
- `test_cases/outputs/sheji.go`
- `test_cases/outputs/sheji_audit_report.md`

---

## 三、角色协作规则

### 3.1 Orchestrator 工作规则
1. 默认入口角色是 `orchestrator`
2. 它负责识别任务类型：生成 / 审核 / 修订
3. 它先调度 `code-writer`，再调度 `code-reviewer`
4. 审核报告由 orchestrator 负责写入 `test_cases/outputs/`
5. 如 reviewer 给出高优先级问题，可再调度 writer 修订

### 3.2 Code-Writer 工作规则
1. 读取 `test_cases/` 下设计说明书
2. 生成单文件源码
3. 代码必须与设计说明书一致
4. 代码必须落盘到 `test_cases/outputs/`
5. 如收到审核反馈，应在原文件上继续修订

### 3.3 Code-Reviewer 工作规则
1. 审核设计说明书与代码的一致性
2. 识别 AI 生成痕迹与软著审核风险
3. 输出结构化审核结论
4. Reviewer 自身不直接改代码、不直接写最终报告文件

---

## 四、标准执行流程

### 4.1 代码生成 + 自动审核
```text
用户任务
  ↓
orchestrator
  ↓
读取 test_cases/*.md
  ↓
code-writer 生成代码
  ↓
代码落盘到 test_cases/outputs/
  ↓
code-reviewer 自动审核
  ↓
orchestrator 将审核报告落盘到 test_cases/outputs/
```

### 4.2 根据审核意见修订
```text
读取审核报告
  ↓
code-writer 修改既有代码
  ↓
code-reviewer 复审
  ↓
更新审核报告
```

默认最多进行 1 轮生成 + 1 轮审核；如有必要，可再进行 1 轮修订。

---

## 五、运行命令

### 5.1 典型运行
```bash
python -m patentforge       --design-file test_cases/sheji.md       --provider openai       --code-type typescript       --min-lines 3500       --max-lines 4000       --output-name sheji
```

### 5.2 常用参数
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--design-file` | 设计说明书路径 | 必填 |
| `--provider` | LLM 提供商 | auto |
| `--code-type` | 代码类型 | typescript |
| `--min-lines` | 最小行数 | 3500 |
| `--max-lines` | 最大行数 | 4000 |
| `--output-name` | 输出文件基础名 | 自动推断 |
| `--max-iter` | 最大迭代次数 | 5 |

### 5.3 环境变量
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://ai-model.chuxinhudong.com/v1"
export PATENTFORGE_ORCHESTRATOR_MODEL="gpt-5.4"
export PATENTFORGE_WRITER_MODEL="MiniMax-M2.5"
export PATENTFORGE_REVIEWER_MODEL="qwen3.5-plus"
```

---

## 六、代码风格规范

### 6.1 总体原则
1. **业务优先**：围绕真实业务处理展开，不堆砌空壳架构
2. **真实实现**：禁止空实现、假实现、占位实现
3. **单文件优先**：软著源码按任务要求保持单文件结构
4. **调用链完整**：入口 → 配置读取 → 业务处理 → 输出结果
5. **与设计一致**：代码必须能和设计说明书相互印证

### 6.2 命名规范
- **类名**：PascalCase，如 `ConfigManager`
- **函数名**：camelCase，如 `loadConfig`
- **常量**：UPPER_SNAKE_CASE
- **文件名**：按任务输出名生成，如 `sheji.ts`

### 6.3 类型与结构
- 优先使用清晰、必要的类型定义
- 避免 interface / enum / manager 泛滥
- 不要为了“显得专业”而过度抽象
- 同一文件内可分 Section，但不要拆成多文件产物

### 6.4 注释规范
- 使用英文 Section 标记大区块，如 `// Section: Runtime Environment`
- 避免批量中文 JSDoc 注释
- 注释只解释关键逻辑，不解释显然语句

### 6.5 错误处理
- 关键路径必须使用 try-catch
- 给出具体错误信息，不要静默吞错
- 记录日志，便于 reviewer 识别调用链和运行痕迹

### 6.6 禁止的高风险写法
```text
❌ Math.random() 作为核心业务判定
❌ return true / return false 充当真实实现
❌ 大量 mock / fake / placeholder 逻辑
❌ 每个类都使用相同单例模板
❌ 架构很漂亮，但没有真实业务细节
❌ 仅输出到对话，不落盘到 test_cases/outputs/
```

---

## 七、Reviewer 审核重点

Reviewer 不是简单判断“像不像 AI”，而是同时看：

1. 是否存在明显 AI 痕迹
2. 是否存在软著审核风险
3. 是否满足单文件、代码类型、行数范围要求
4. 是否存在空实现、假实现、占位实现
5. 是否与设计说明书相互印证

审核输出必须是结构化结论，最终落盘到 `test_cases/outputs/`。

---

## 八、项目文档与配置文件

关键文件如下：

- `opencode.json`：项目级智能体配置
- `agent/orchestrator.md`：编排智能体规则
- `agent/programmer.md`：Writer 规则
- `agent/reviewer.md`：Reviewer 规则
- `docs/opencode-project-agents-guide.md`：给团队同事的配置说明
- `docs/patentforge-agent-architecture.md`：项目级架构设计文档

---

## 九、常见问题处理

### 9.1 writer 写完后没有自动审核
检查：
- `default_agent` 是否是 `orchestrator`
- `code-writer` / `code-reviewer` 是否已改为 `subagent`
- `agent/orchestrator.md` 是否存在且流程说明正确

### 9.2 reviewer 结果没有落盘
检查：
- 是否由 orchestrator 执行最终落盘
- 输出文件名是否符合 `<name>_audit_report.md`
- 输出目录是否为 `test_cases/outputs/`

### 9.3 审核不通过
优先处理：
- 行数是否达标
- 是否存在假实现 / 占位实现
- 是否与设计说明书不一致
- 是否模板痕迹过重

---

*本文档最后更新：2026-03-25*
*适用版本：PatentForge 编排式三智能体架构*
