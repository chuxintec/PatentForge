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
│   ├── writer_prompt.txt
│   └── reviewer_prompt.txt
│
├── llm/
│   └── client.py
│
├── outputs/
│   ├── final.md
│   └── logs.json
│
└── README.md
```

---

## 五、核心数据结构

```
{
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

    def __init__(self, writer, reviewer, max_iter=5):
        self.writer = writer
        self.reviewer = reviewer
        self.max_iter = max_iter
        self.state = {
            "draft": "",
            "feedback": "",
            "iteration": 0,
            "status": "init"
        }

    def run(self):

        while self.state["iteration"] < self.max_iter:

            # 写作阶段
            self.state["status"] = "writing"
            draft = self.writer.run(
                draft=self.state["draft"],
                feedback=self.state["feedback"]
            )

            # 审核阶段
            self.state["status"] = "reviewing"
            review = self.reviewer.run(draft)

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

* 生成文档
* 根据反馈优化文档

输入：

* draft
* feedback

输出：

* 新版本文档

---

### Reviewer Agent

职责：

* 审核文档
* 输出结构化结果

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

### writer_prompt.txt

```
你是软著文档编写专家。

当前文档：
{{draft}}

审核反馈：
{{feedback}}

请根据反馈修改文档。

要求：
- 修复所有问题
- 保持结构完整
- 提高规范性和可读性

输出：完整文档
```

---

### reviewer_prompt.txt

```
你是软著审核专家。

请审核以下文档：

{{draft}}

输出 JSON：

{
  "pass": true/false,
  "issues": [...],
  "feedback": "详细修改建议"
}

审核标准：
- 结构完整
- 描述清晰
- 无明显逻辑错误
- 符合软著规范
```

---

## 十、终止条件

必须满足：

1. 审核通过（pass = true）
2. 或达到最大迭代次数（默认 5）

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
python -m patentforge --brief-file brief.md --provider openai
```

或者显式指定模型：

```bash
python -m patentforge \
  --brief-file brief.md \
  --provider openai \
  --writer-model MiniMax-M2.7 \
  --reviewer-model qwen3.5-plus
```

默认行为：

- Writer 读取 [`程序员Agent.md`](./程序员Agent.md)
- Reviewer 读取 [`软著审核员Agent.md`](./软著审核员Agent.md)
- 产物输出到 `outputs/`，包含 `final.md` 和 `logs.json`
- 默认 `baseURL`：`https://ai-model.chuxinhudong.com/v1`
- Writer 模型：`MiniMax-M2.7`
- Reviewer 模型：`qwen3.5-plus`

如果要接 OpenAI API：

- 设置 `OPENAI_API_KEY`
- 如需改地址，设置 `OPENAI_BASE_URL`
- 安装 `openai` 包
- 使用 `--provider openai`

离线调试可以直接使用：

```bash
python -m patentforge --brief "你的项目背景" --provider fallback
```

---
