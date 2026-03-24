# OpenCode 项目级智能体配置说明（PatentForge 示例）

本文基于本项目根目录下的 `opencode.json` 进行整理，适合分享给团队同事，帮助大家快速理解：

1. 如何在项目里配置 OpenCode 智能体
2. 每个参数的含义是什么
3. 项目级智能体可以完成哪些特定工作

---

## 一、什么是项目级别智能体

项目级别智能体，指的是在**某个仓库根目录**下通过 `opencode.json` 定义的智能体配置。

它和“全局默认 AI 助手”不同，项目级智能体会天然绑定当前仓库的上下文，例如：

- 当前目录结构
- 当前项目约定
- prompt 文件
- 输出目录
- 可用工具权限
- 业务角色分工

简单理解：

> 不是让 AI 在任何项目里都用同一种方式工作，而是让 AI 在当前仓库里扮演已经定义好的具体角色。

在 PatentForge 这个项目里，核心角色就是两个：

- `code-writer`：负责根据设计说明书生成代码
- `code-reviewer`：负责审核设计说明书和代码

此外还出现了两个内置工作流角色：

- `build`
- `plan`

其中 `build` 当前禁用，`plan` 当前启用。

---

## 二、本项目当前的 opencode.json

项目根目录中的配置如下：

```json
{
    "$schema": "https://opencode.ai/config.json",
    "default_agent": "code-writer",
    "agent": {
        "build": {
            "mode": "subagent",
            "disabled": true
        },
        "plan": {
            "mode": "subagent",
            "disabled": false
        },
        "code-writer": {
            "description": "write code for the project",
            "mode": "primary",
            "model": "chuxin-ai/MiniMax-M2.7",
            "prompt": "{file:./agent/programmer.md}",
            "tools": {
                "write": true,
                "edit": true,
                "bash": true
            }
        },
        "code-reviewer": {
            "description": "Reviews code for best practices and potential issues",
            "mode": "primary",
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

### 1. 在项目根目录放置 opencode.json

项目级智能体的入口文件就是：

```bash
opencode.json
```

OpenCode 进入当前仓库后，会读取这个文件，用它来识别：

- 默认使用哪个智能体
- 当前项目有哪些智能体
- 每个智能体绑定哪个模型
- 每个智能体加载哪个 prompt
- 每个智能体拥有哪些工具权限

---

### 2. 用 agent 字段声明角色

典型结构如下：

```json
{
  "agent": {
    "code-writer": { ... },
    "code-reviewer": { ... }
  }
}
```

`agent` 下的每个 key 都是一个角色名。

在本项目里包括：

- `build`
- `plan`
- `code-writer`
- `code-reviewer`

其中前两个更像工作流辅助角色，后两个是业务主角色。

---

### 3. 将角色规则写入独立 prompt 文件

本项目没有把 prompt 直接写在 `opencode.json` 里，而是通过文件引用：

- `agent/programmer.md`
- `agent/reviewer.md`

例如：

```json
"prompt": "{file:./agent/programmer.md}"
```

表示让该智能体加载 `agent/programmer.md` 作为系统角色规则。

这种做法的好处：

- prompt 长时更容易维护
- 规则变化时不需要频繁改 JSON
- 便于多人协作和版本管理
- 智能体职责边界更清楚

---

## 四、顶层参数说明

### 1. $schema

```json
"$schema": "https://opencode.ai/config.json"
```

作用：

- 指定配置文件遵循的 schema
- 方便编辑器自动提示和校验
- 方便团队成员识别这是一份 OpenCode 标准配置

简单说，它是“这份 JSON 按什么规则解释”的声明。

---

### 2. default_agent

```json
"default_agent": "code-writer"
```

作用：

- 指定默认角色
- 当用户没有显式切换 agent 时，优先使用它

本项目里默认是 `code-writer`，因为这个仓库的主任务是：

- 读取设计说明书
- 生成软著源码

如果未来项目重心变成“审核优先”，也可以把它改成 `code-reviewer`。

---

## 五、agent 下各角色参数说明

下面按角色配置字段逐项解释。

### 1. description

示例：

```json
"description": "write code for the project"
```

作用：

- 用一句话描述该智能体做什么
- 便于团队和系统识别角色定位

建议写法：

- 简洁
- 面向职责
- 不要写得太空泛

---

### 2. mode

本项目中有两种：

#### `mode: "primary"`

表示这是主智能体。

特点：

- 可以直接面向用户工作
- 可以被设置为默认角色
- 通常承担核心业务任务

本项目的主智能体：

- `code-writer`
- `code-reviewer`

#### `mode: "subagent"`

表示这是子智能体。

特点：

- 更适合做工作流中的辅助角色
- 通常不直接承担完整主任务
- 可用于规划、构建、子步骤拆解

本项目中的子智能体：

- `build`
- `plan`

---

### 3. disabled

示例：

```json
"disabled": true
```

作用：

- 控制该智能体是否启用

本项目里：

- `build.disabled = true`
- `plan.disabled = false`

含义：

- `build` 当前不参与执行
- `plan` 当前允许参与任务规划

注意：

有些 UI 或 trace 里即便 disabled，也可能仍显示节点名称；这不一定表示它真的执行了。

---

### 4. model

示例：

```json
"model": "chuxin-ai/MiniMax-M2.7"
```

作用：

- 指定该角色绑定的模型

本项目的配置思路是：

- `code-writer` 用 `MiniMax-M2.7`
- `code-reviewer` 用 `qwen3.5-plus`

这体现了一个很好的实践：

> 不同角色可以绑定不同模型，而不是整个项目只固定一个模型。

这样做的好处：

- 写代码和审代码分工更明确
- 生成和审核的偏差更小
- 更接近真实团队里的“双人协作”流程

---

### 5. prompt

示例：

```json
"prompt": "{file:./agent/programmer.md}"
```

作用：

- 指定该智能体的角色规则文件

本项目中：

#### code-writer 的 prompt

```bash
agent/programmer.md
```

它规定了 Writer 要：

- 按软著场景写单文件源码
- 围绕设计说明书真实实现业务逻辑
- 避免 AI 痕迹
- 避免空实现和模板代码
- 输出必须落盘

#### code-reviewer 的 prompt

```bash
agent/reviewer.md
```

它规定了 Reviewer 要：

- 审核设计说明书和源代码
- 区分 AI 痕迹与软著审核风险
- 输出结构化审核结论
- 给出明确修改建议

可以理解为：

- `opencode.json` 负责定义“这个角色是谁”
- `prompt` 文件负责定义“这个角色具体怎么工作”

---

### 6. tools

作用：

- 控制该智能体能调用哪些工具

本项目中有三个常见工具开关：

- `write`
- `edit`
- `bash`

#### write

```json
"write": true
```

表示允许新建或覆盖写文件。

对于 `code-writer` 来说，这是必须的，因为本项目要求：

- Code-Writer 写的代码必须落盘到 `test_cases/outputs/`

---

#### edit

```json
"edit": true
```

表示允许修改已有文件。

这个权限适合：

- 根据 reviewer 意见持续修订代码
- 在已有源码上做增量修改

---

#### bash

```json
"bash": true
```

表示允许执行命令行操作。

适合用于：

- 查看文件行数
- 检查目录结构
- 运行脚本
- 读取日志
- 做简单验证

在本项目里，bash 更适合作为辅助工具，而不是核心生成手段。

---

## 六、本项目两个主智能体分别能做什么

### 1. code-writer

配置如下：

```json
"code-writer": {
  "description": "write code for the project",
  "mode": "primary",
  "model": "chuxin-ai/MiniMax-M2.7",
  "prompt": "{file:./agent/programmer.md}",
  "tools": {
    "write": true,
    "edit": true,
    "bash": true
  }
}
```

#### 这个角色的特定工作

1. **读取设计说明书并生成代码**
   - 输入通常来自 `test_cases/`
   - 如：`test_cases/sheji.md`

2. **按软著要求生成单文件源码**
   - TypeScript：`test_cases/outputs/sheji.ts`
   - Golang：`test_cases/outputs/sheji.go`

3. **保证代码更像真实项目代码**
   - 不是展示型 demo
   - 不是纯架构样板
   - 要有真实业务逻辑、配置处理、日志、异常处理、调用链

4. **根据审核意见继续修订代码**
   - 因为它有 `edit: true`
   - 能在原文件基础上迭代修改

5. **把代码结果直接落盘**
   - 这是当前项目最重要的要求之一

---

### 2. code-reviewer

配置如下：

```json
"code-reviewer": {
  "description": "Reviews code for best practices and potential issues",
  "mode": "primary",
  "model": "chuxin-ai/qwen3.5-plus",
  "prompt": "{file:./agent/reviewer.md}",
  "tools": {
    "write": false,
    "edit": false
  }
}
```

#### 这个角色的特定工作

1. **审核设计说明书与代码是否一致**
   - 软件名称是否一致
   - 模块划分是否一致
   - 代码是否真的实现了设计说明书内容

2. **识别 AI 生成痕迹**
   - 模板化结构
   - 空实现
   - 假实现
   - interface / manager / adapter 泛滥
   - 过度工整、像教材

3. **评估软著审核风险**
   - 是否容易被质疑真实性
   - 是否可能被打回或要求补正
   - 哪些问题优先级最高

4. **输出结构化审核结论**
   - 当前项目要求审核结论最终落盘到 `test_cases/outputs/`
   - 典型文件名：`test_cases/outputs/sheji_audit_report.md`

虽然当前 reviewer 没有开启 `write` / `edit`，但项目流程层面，审核结果仍然应该被保存到输出目录中。

---

## 七、内置子智能体能做什么

### 1. build

当前配置：

```json
"build": {
  "mode": "subagent",
  "disabled": true
}
```

说明：

- 当前禁用
- 不参与当前项目的主要工作流

适合未来扩展的事情：

- 构建代码产物
- 运行构建检查
- 输出编译相关结果

但当前项目不是典型“工程构建型仓库”，而是“软著代码生成 + 审核型仓库”，所以禁用是合理的。

---

### 2. plan

当前配置：

```json
"plan": {
  "mode": "subagent",
  "disabled": false
}
```

说明：

- 当前启用
- 适合做任务拆解与前置规划

适合完成的工作：

- 阅读设计说明书后先拆模块
- 规划代码结构和实现顺序
- 根据 reviewer 反馈先形成修订计划

对于长设计说明书、多轮迭代场景，这个角色会很有价值。

---

## 八、这套项目级智能体配置的实际价值

### 1. 明确角色分工

- Writer 负责写
- Reviewer 负责审
- Plan 负责拆解任务

这比“一个大而全的通用助手”更稳定。

---

### 2. 支持不同角色使用不同模型

例如本项目：

- 生成代码用 `MiniMax-M2.7`
- 审核用 `qwen3.5-plus`

这让模型使用更贴近角色特长。

---

### 3. Prompt 可以独立维护

通过独立的：

- `agent/programmer.md`
- `agent/reviewer.md`

团队可以分别维护不同角色的规则，而不用反复改 JSON 主结构。

---

### 4. 工具权限清晰

例如：

- Writer 可以写、改、执行 bash
- Reviewer 不能直接改文件

这种权限边界很适合团队协作，避免角色越权。

---

### 5. 非常适合项目工作流固化

尤其是像 PatentForge 这种流程固定的项目：

1. 读取设计说明书
2. 生成单文件源码
3. 审核生成结果
4. 再次修订
5. 落盘输出

项目级智能体能把这个流程稳定下来。

---

## 九、结合本项目的输入输出约定

为了让同事更容易照着复用，这里特别强调本项目的目录规则。

### 输入目录

```bash
test_cases/
```

典型输入：

```bash
test_cases/sheji.md
```

### 输出目录

```bash
test_cases/outputs/
```

必须遵守的约定：

1. **Code-Writer 写的代码必须落盘到该目录**
   - 例如：`test_cases/outputs/sheji.ts`
   - 或：`test_cases/outputs/sheji.go`

2. **Code-Reviewer 审核的结论也必须落盘到该目录**
   - 例如：`test_cases/outputs/sheji_audit_report.md`

3. 日志也放在该目录
   - `test_cases/outputs/patentforge.log`
   - `test_cases/outputs/logs.json`

---

## 十、推荐给同事的最小配置模板

如果你的同事想在其他项目里复用类似做法，可以从下面这个最小模板开始：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "code-writer",
  "agent": {
    "code-writer": {
      "description": "write code for the project",
      "mode": "primary",
      "model": "your-writer-model",
      "prompt": "{file:./agent/programmer.md}",
      "tools": {
        "write": true,
        "edit": true,
        "bash": true
      }
    },
    "code-reviewer": {
      "description": "review generated code and docs",
      "mode": "primary",
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

然后再根据项目性质去决定是否增加：

- `plan`
- `build`
- `test`
- `doc-writer`

---

## 十一、给同事的落地建议

如果团队要推广这种配置方式，建议按以下顺序推进：

1. **先定义角色，不要先追求复杂工作流**
   - 至少拆成 Writer 和 Reviewer 两个角色

2. **先把 prompt 文件写清楚**
   - JSON 只是挂载角色
   - 真正决定质量的是 prompt

3. **先统一输入输出目录**
   - 否则不同人使用时产物容易乱

4. **先限制工具权限，再逐步放开**
   - 比如 reviewer 先不开放 edit/write

5. **优先让角色职责稳定，而不是追求角色数量**
   - 两个清晰角色，通常比五个职责模糊角色更实用

---

## 十二、一句话总结

你当前这份 `opencode.json` 的本质，是在 PatentForge 仓库里定义了一套 **“写代码 + 审代码 + 可规划”的项目级智能体协作机制**：

- `code-writer` 负责根据设计说明书生成并落盘源码
- `code-reviewer` 负责审核源码和文档，输出审核意见
- `plan` 可辅助任务拆解
- 所有行为都受项目 prompt、工具权限和输入输出目录规则约束

这是一种很适合团队内部复用和分享的项目级 AI 协作配置方式。
