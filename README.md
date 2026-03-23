# PatentForge：Codex Agent 执行文档（中文）

---

## 一、项目目标

构建一个基于 Codex 的多 Agent 系统，实现：

**软著自动生成 + 自动审核 + 自动迭代优化**

系统采用 **双 Agent 闭环架构**：

Writer Agent → Reviewer Agent → Feedback → Writer → ... → PASS

---

## 二、系统核心能力

### 1. 自动写作

* 根据输入生成完整软著文档

### 2. 自动审核

* 对文档进行结构化审核
* 输出问题与修改建议

### 3. 自动闭环优化

* 根据审核反馈自动修改
* 多轮迭代直到通过

---

## 三、核心架构设计

系统采用 Agent Loop 架构：

用户输入
↓
Writer Agent
↓
Reviewer Agent
↓
反馈
↓
是否通过？
├ 是 → 输出最终文档
└ 否 → 返回 Writer 继续优化

---

## 四、项目结构（建议）

```
patentforge/
├── core/
│   ├── loop_engine.py
│   ├── state.py
│   └── controller.py
│
├── agents/
│   ├── writer_agent.py
│   └── reviewer_agent.py
│
├── prompts/
│   ├── writer.md
│   └── reviewer.md
│
├── llm/
│   └── client.py
│
├── .env.example
│
├── test_cases/
│   ├── outputs/
│   │   ├── sheji.ts
│   │   └── logs.json
│   └── 游戏跨平台运行适配管理系统/
│       ├── 设计说明书.md
│       ├── 源代码.ts
│       └── 审核结果.md
│
└── README.md
```

---

## 五、核心数据结构

```
{
  "design_spec": "",
  "code_type": "typescript",
  "output_name": "sheji",
  "min_code_lines": 3500,
  "max_code_lines": 4000,
  "draft": "",
  "feedback": "",
  "iteration": 0,
  "status": "init | writing | reviewing | refining | done"
}
```

---

## 六、核心执行流程

INIT
↓
WRITE
↓
REVIEW
↓
IF PASS → DONE
IF FAIL → REFINE → WRITE

---

## 七、Loop Engine 示例（核心代码）

```python
class LoopEngine:

    def __init__(self, writer, reviewer, max_iter=5, code_type="typescript"):
        self.writer = writer
        self.reviewer = reviewer
        self.max_iter = max_iter
        self.code_type = code_type
        self.state = {
            "design_spec": "",
            "output_name": "sheji",
            "draft": "",
            "feedback": "",
            "iteration": 0,
            "status": "init"
        }

    def run(self, design_spec):
        self.state["design_spec"] = design_spec

        while self.state["iteration"] < self.max_iter:

            # 写作阶段
            self.state["status"] = "writing"
            draft = self.writer.run(
                design_spec=self.state["design_spec"],
                code_type=self.code_type,
                output_name=self.state["output_name"],
                draft=self.state["draft"],
                feedback=self.state["feedback"],
                min_code_lines=3500,
                max_code_lines=4000
            )

            # 审核阶段
            self.state["status"] = "reviewing"
            review = self.reviewer.run(
                design_spec=self.state["design_spec"],
                code_type=self.code_type,
                output_name=self.state["output_name"],
                draft=draft
            )

            # 判断结果
            if review["pass"]:
                self.state["status"] = "done"
                return draft

            # 反馈更新
            self.state["feedback"] = review["feedback"]
            self.state["draft"] = draft
            self.state["iteration"] += 1

        return self.state["draft"]
```

---

## 八、Agent 设计

### Writer Agent

职责：

* 根据设计说明书生成源代码
* 根据审核反馈优化源代码

输入：

* design_spec
* code_type
* output_name
* min_code_lines
* max_code_lines
* draft
* feedback

输出：

* 新版本源代码

---

### Reviewer Agent

职责：

* 审核设计说明书和源代码
* 输出结构化结果

输入：

* design_spec
* code_type
* output_name
* min_code_lines
* max_code_lines
* draft

输出格式：

```
{
  "pass": true/false,
  "issues": [],
  "feedback": ""
}
```

---

## 九、Prompt 设计

### writer.md（节选）

```
你是软著源代码生成器。
根据设计说明书生成单文件源码。
默认代码类型是 TypeScript，目标行数 3500-4000 行。
只输出源码，不要解释，不要 Markdown，不要多文件。
有审核反馈时优先修正问题。
```

---

### reviewer.md（节选）

```
你是软著审核员。
审核设计说明书和单文件源码。
重点看一致性、单文件、代码类型、行数范围、真实调用链、空实现和模板痕迹。
只输出 JSON，字段必须包含 pass、issues、feedback。
```

---

## 十、终止条件

必须满足：

1. 审核通过（pass = true）
2. 或达到最大迭代次数（默认 5 次）

---

## 十一、日志记录（推荐）

```
{
  "iteration": 1,
  "draft": "...",
  "feedback": "...",
  "pass": false
}
```

用于：

* Debug
* 质量评估
* Prompt优化

---

## 十二、扩展方向

### 1. 多 Reviewer

* 技术审核
* 法律审核
* 表达审核

### 2. 打分系统

```
{
  "score": 85,
  "pass": false
}
```

### 3. 模板系统

* 不同类型软著模板

### 4. 知识库增强（RAG）

* 历史软著
* 行业规范

### 5. Web UI

* 可视化编辑
* 差异对比
* 审核流程

---

## 十三、系统本质

这是一个：

**自我优化的闭环 Agent 系统**

核心能力：

Loop（循环）

* State（状态）
* Prompt（策略）
* Feedback（反馈）

---

## 十四、Codex 使用方式

建议：

1. 将本 README 提供给 Codex
2. 分模块生成代码：

   * loop_engine
   * agents
   * prompts
3. 逐步完善系统

---

## 十五、一句话总结

本系统不是：

“AI写软著工具”

而是：

“AI自动优化文档系统”

---

## 十六、实现落地

仓库里已经补齐了可运行的 Python 实现。

运行方式：

```bash
python -m patentforge --design-file sheji.md --provider openai --code-type typescript
```

或者显式指定模型：

```bash
python -m patentforge \
  --design-file sheji.md \
  --provider openai \
  --code-type typescript \
  --min-lines 3500 \
  --max-lines 4000 \
  --log-file ./test_cases/outputs/patentforge.log \
  --writer-model MiniMax-M2.7 \
  --reviewer-model qwen3.5-plus
```

默认行为：

- Writer 读取 [`prompts/writer.md`](./prompts/writer.md)
- Reviewer 读取 [`prompts/reviewer.md`](./prompts/reviewer.md)
- 产物输出到 `test_cases/outputs/`，默认单文件代码名为 `sheji.ts`，另有 `logs.json`
- 运行过程会实时输出到控制台，同时写入 `test_cases/outputs/patentforge.log`
- API 配置优先从 `.env` 读取
- 默认 `baseURL`：`https://ai-model.chuxinhudong.com/v1`
- 默认代码类型：`typescript`
- 默认行数范围：`3500-4000`
- 默认日志级别：`INFO`
- Writer 模型：`MiniMax-M2.7`
- Reviewer 模型：`qwen3.5-plus`

如果要接 OpenAI API：

- 复制 [`.env.example`](./.env.example) 为 `.env`
- 在 `.env` 里填写 `OPENAI_API_KEY`
- 如需改地址，填写 `OPENAI_BASE_URL`
- 如需改代码类型，填写 `PATENTFORGE_CODE_TYPE`
- 如需改行数范围，填写 `PATENTFORGE_MIN_CODE_LINES` 和 `PATENTFORGE_MAX_CODE_LINES`
- 如需改日志级别，填写 `PATENTFORGE_LOG_LEVEL`
- 如需改模型，填写 `PATENTFORGE_WRITER_MODEL` 和 `PATENTFORGE_REVIEWER_MODEL`
- 如果安装了 `openai` 包，程序会优先使用官方 SDK；否则会自动走内置 HTTP 客户端
- 使用 `--provider openai`

程序会优先读取当前目录的 `.env`，再读取仓库根目录的 `.env`，已有的系统环境变量优先级更高。
如果远端模型响应较慢，可以设置 `PATENTFORGE_HTTP_TIMEOUT` 调整请求超时，单位秒。

离线调试可以直接使用：

```bash
python -m patentforge --design "你的设计说明书内容" --provider fallback
```

---
