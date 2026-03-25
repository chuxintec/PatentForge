# OpenCode 项目级智能体配置说明（PatentForge 当前版本）

本文面向团队同事，说明本项目现在如何通过 `opencode.json` 配置项目级智能体，以及这套配置为什么适合 PatentForge。

---

## 一、当前项目采用的智能体架构

当前项目不是“两个主智能体并列工作”，而是采用 **1 个编排智能体 + 2 个业务子智能体** 的结构：

1. `patentforge-orchestrator`
   - 默认入口智能体
   - 负责组织整体流程
   - 模型：`chuxin-ai/gpt-5.4`

2. `code-writer`
   - 负责根据设计说明书生成代码
   - 模型：`chuxin-ai/MiniMax-M2.5`

3. `code-reviewer`
   - 负责审核设计说明书和源码
   - 模型：`chuxin-ai/qwen3.5-plus`

此外还保留了两个内置工作流角色：

- `build`：禁用
- `plan`：禁用

当前默认入口不再是 writer，而是 orchestrator。这样可以实现：

> code-writer 写完代码后，code-reviewer 自动审核。

---

## 二、当前项目的 opencode.json

```json
{
    "$schema": "https://opencode.ai/config.json",
    "default_agent": "patentforge-orchestrator",
    "agent": {
        "build": {
            "mode": "subagent",
            "disabled": true
        },
        "plan": {
            "mode": "subagent",
            "disabled": true
        },
        "patentforge-orchestrator": {
            "description": "Orchestrate code writing and review for PatentForge",
            "mode": "primary",
            "model": "chuxin-ai/gpt-5.4",
            "prompt": "{file:./agent/orchestrator.md}",
            "tools": {
                "write": true,
                "edit": true,
                "bash": true
            }
        },
        "code-writer": {
            "description": "Write code for the project",
            "mode": "subagent",
            "model": "chuxin-ai/MiniMax-M2.5",
            "prompt": "{file:./agent/programmer.md}",
            "tools": {
                "write": true,
                "edit": true,
                "bash": true
            }
        },
        "code-reviewer": {
            "description": "Review generated code and design materials",
            "mode": "subagent",
            "model": "chuxin-ai/qwen3.5-plus",
            "prompt": "{file:./agent/reviewer.md}",
            "tools": {
                "write": false,
                "edit": false
            }
        }
    }
}
```

---

## 三、如何配置项目级别智能体

### 1. 在仓库根目录放置 `opencode.json`

项目级配置文件必须放在仓库根目录：

```bash
opencode.json
```

只要 OpenCode 进入该仓库，它就会读取这份配置，用它确定：

- 默认入口智能体是谁
- 当前项目定义了哪些角色
- 每个角色使用什么模型
- 每个角色加载哪个 prompt 文件
- 每个角色拥有哪些工具权限

---

### 2. 用 `agent` 字段声明角色

典型结构：

```json
{
  "agent": {
    "patentforge-orchestrator": { ... },
    "code-writer": { ... },
    "code-reviewer": { ... }
  }
}
```

`agent` 下的每一个 key 都是角色名。

本项目里的角色分为两类：

- 主角色：`patentforge-orchestrator`
- 子角色：`code-writer`、`code-reviewer`、`build`、`plan`

---

### 3. 将角色规则写入独立 prompt 文件

当前项目采用“JSON 挂角色，Markdown 写规则”的方式。

角色 prompt 文件如下：

- `agent/orchestrator.md`
- `agent/programmer.md`
- `agent/reviewer.md`

例如：

```json
"prompt": "{file:./agent/orchestrator.md}"
```

这样做的优点：

- prompt 更长时更容易维护
- 改规则时不需要频繁改 JSON
- 角色边界更清晰
- 便于多人协作和版本管理

---

## 四、每个参数的意义是什么

### 1. `$schema`

```json
"$schema": "https://opencode.ai/config.json"
```

作用：

- 声明这是 OpenCode 的标准配置文件
- 方便编辑器做 schema 校验和自动补全

---

### 2. `default_agent`

```json
"default_agent": "patentforge-orchestrator"
```

作用：

- 指定默认入口智能体
- 用户不显式切换角色时，默认进入这个角色

本项目里之所以选择 orchestrator 作为默认入口，是因为它要负责自动串联“写代码 → 审核”流程。

---

### 3. `description`

示例：

```json
"description": "Orchestrate code writing and review for PatentForge"
```

作用：

- 用一句话描述该角色的职责
- 便于团队成员快速理解它是干什么的

---

### 4. `mode`

当前项目中有两种：

#### `mode: "primary"`

表示主智能体。

特点：

- 直接面向用户
- 可以作为默认入口
- 通常承担流程总控职责

本项目里：

- `patentforge-orchestrator` 是 primary

#### `mode: "subagent"`

表示子智能体。

特点：

- 更适合被主智能体调度
- 不直接承担完整工作流
- 更专注于单一职责

本项目里：

- `code-writer`
- `code-reviewer`
- `build`
- `plan`

都是 subagent。

---

### 5. `disabled`

示例：

```json
"disabled": true
```

作用：

- 控制该角色是否启用

当前项目里：

- `build.disabled = true`
- `plan.disabled = true`

含义：

- 当前不让 build / plan 参与工作流
- 避免它们干扰 orchestrator 主流程

---

### 6. `model`

作用：

- 指定角色绑定的模型

当前项目模型分配如下：

| 角色 | 模型 | 作用 |
|------|------|------|
| patentforge-orchestrator | `chuxin-ai/gpt-5.4` | 负责总控与流程编排 |
| code-writer | `chuxin-ai/MiniMax-M2.5` | 负责生成代码 |
| code-reviewer | `chuxin-ai/qwen3.5-plus` | 负责审核代码与文档 |

这体现了一个项目级最佳实践：

> 不同角色可以绑定不同模型，而不是整个项目只有一个统一模型。

---

### 7. `prompt`

示例：

```json
"prompt": "{file:./agent/programmer.md}"
```

作用：

- 指定角色的规则说明文件

当前项目中：

- `orchestrator.md`：定义编排逻辑
- `programmer.md`：定义写代码规则
- `reviewer.md`：定义审核规则

可以理解为：

- `opencode.json` 决定“有哪些角色”
- `prompt` 文件决定“这些角色如何工作”

---

### 8. `tools`

作用：

- 控制角色可使用的工具权限

当前项目常见工具如下：

#### `write`

允许新建或覆盖写文件。

用途：

- Writer 生成代码时落盘
- Orchestrator 生成审核报告时落盘

#### `edit`

允许修改已有文件。

用途：

- Writer 根据审核意见做增量修订
- Orchestrator 在必要时协调修改既有结果

#### `bash`

允许执行命令行操作。

用途：

- 统计行数
- 检查输出文件
- 验证目录和文件状态

当前 reviewer 没有写权限，表示它是“只产出审核内容，不自己落盘文件”的角色。

---

## 五、当前项目级智能体能完成什么特定工作

### 1. patentforge-orchestrator 能做什么

这是当前项目的默认入口角色，负责：

1. 接收用户任务
2. 判断本轮任务是“生成代码”“审核代码”还是“根据审核意见修订”
3. 调用 `code-writer`
4. 调用 `code-reviewer`
5. 确保代码和审核报告都落盘到指定目录
6. 在必要时执行最多 1-2 轮修订

它解决的问题是：

> 让整个项目不再靠人工切换 writer / reviewer，而是自动完成完整流程。

---

### 2. code-writer 能做什么

作为子智能体，`code-writer` 专门负责：

1. 读取 `test_cases/` 下的设计说明书
2. 生成单文件源码
3. 代码输出到 `test_cases/outputs/`
4. 根据 reviewer 的反馈继续修订

典型输出：

- `test_cases/outputs/sheji.ts`
- `test_cases/outputs/sheji.go`

---

### 3. code-reviewer 能做什么

作为子智能体，`code-reviewer` 专门负责：

1. 审核设计说明书与代码的一致性
2. 判断 AI 生成痕迹
3. 判断软著审核风险
4. 输出结构化审核结论

由于 reviewer 没有 write / edit 权限，所以：

- 它负责“产出审核内容”
- 审核报告最终由 orchestrator 写入 `test_cases/outputs/`

典型输出目标文件：

- `test_cases/outputs/sheji_audit_report.md`

---

## 六、为什么要改成“编排智能体 + 子智能体”

如果只有两个 primary agent：

- `code-writer`
- `code-reviewer`

那么默认只能实现“分别调用它们”，而不适合稳定地自动串联。

改成 orchestrator 架构后，有几个明显好处：

1. **职责更清晰**
   - writer 只写
   - reviewer 只审
   - orchestrator 只负责编排

2. **自动流程更稳定**
   - 不需要人工切换角色
   - 更容易控制先后顺序

3. **方便后续扩展**
   - 以后可以加入测试、文档生成、补正说明等新角色

4. **更适合团队复用**
   - 同事进入项目后，默认只需要和 orchestrator 交互

---

## 七、当前项目的输入输出规则

### 输入目录

```bash
test_cases/
```

典型输入文件：

```bash
test_cases/sheji.md
```

### 输出目录

```bash
test_cases/outputs/
```

必须遵守的规则：

1. **Code-Writer 写的代码必须落盘到该目录**
2. **Code-Reviewer 的审核结论也必须落盘到该目录**
3. **日志和中间结果也优先放在该目录**

常见输出文件：

- `test_cases/outputs/sheji.ts`
- `test_cases/outputs/sheji.go`
- `test_cases/outputs/sheji_audit_report.md`
- `test_cases/outputs/patentforge.log`
- `test_cases/outputs/logs.json`

---

## 八、推荐给同事的最小参考模板

```json
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "project-orchestrator",
  "agent": {
    "project-orchestrator": {
      "description": "Coordinate writing and reviewing workflow",
      "mode": "primary",
      "model": "your-orchestrator-model",
      "prompt": "{file:./agent/orchestrator.md}",
      "tools": {
        "write": true,
        "edit": true,
        "bash": true
      }
    },
    "code-writer": {
      "description": "Write code for the project",
      "mode": "subagent",
      "model": "your-writer-model",
      "prompt": "{file:./agent/programmer.md}",
      "tools": {
        "write": true,
        "edit": true,
        "bash": true
      }
    },
    "code-reviewer": {
      "description": "Review generated code and docs",
      "mode": "subagent",
      "model": "your-reviewer-model",
      "prompt": "{file:./agent/reviewer.md}",
      "tools": {
        "write": false,
        "edit": false
      }
    }
  }
}
```

---

## 九、一句话总结

当前 PatentForge 的项目级 OpenCode 配置，本质上是：

> 用一个 `gpt-5.4` 编排智能体统一调度 `code-writer` 和 `code-reviewer`，实现“写代码后自动审核，并将代码与审核结论都落盘到 `test_cases/outputs/`”的工作流。
