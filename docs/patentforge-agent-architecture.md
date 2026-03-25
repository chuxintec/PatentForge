# PatentForge 智能体协作架构设计

本文档说明当前项目的 OpenCode 智能体架构、角色职责、目录契约、自动化流程及设计取舍，作为项目级设计文档使用。

---

## 一、设计目标

当前架构的核心目标不是“单个 AI 完成所有事情”，而是通过职责清晰的多个角色构建稳定工作流：

1. 根据设计说明书生成软著源码
2. 生成后自动触发审核
3. 确保代码与审核报告都落盘到统一目录
4. 为后续多轮修订预留空间
5. 让团队成员只需要面对一个默认入口

---

## 二、总体架构

当前采用三角色结构：

- **orchestrator**：流程编排层
- **code-writer**：代码生成层
- **code-reviewer**：审核评估层

其中：

- `orchestrator` 是唯一 primary agent
- `code-writer` 与 `code-reviewer` 都是 subagent
- `build` / `plan` 当前均禁用，避免干扰主流程

---

## 三、角色职责划分

### 3.1 orchestrator

**模型**：`chuxin-ai/gpt-5.4`

**职责**：

1. 识别用户意图
2. 判断本轮是生成、审核还是修订任务
3. 调度 `code-writer`
4. 调度 `code-reviewer`
5. 负责将审核内容落盘
6. 控制是否进行下一轮修订

**为什么选择 gpt-5.4**：

- 更适合承担复杂流程编排
- 更适合理解上下文和执行顺序约束
- 在“调度多个角色”场景下比单纯生成模型更稳

---

### 3.2 code-writer

**模型**：`chuxin-ai/MiniMax-M2.5`

**职责**：

1. 读取设计说明书
2. 生成与设计一致的单文件源码
3. 将源码写入 `test_cases/outputs/`
4. 根据 reviewer 的意见继续修订源码

**设计原则**：

- 单文件实现
- 业务优先
- 真实调用链
- 避免 AI 痕迹
- 行数符合软著约束

---

### 3.3 code-reviewer

**模型**：`chuxin-ai/qwen3.5-plus`

**职责**：

1. 审核设计说明书与代码一致性
2. 识别 AI 生成痕迹
3. 评估软著审核风险
4. 给出结构化、可执行的修改建议

**权限约束**：

- 不直接写文件
- 不直接修改文件
- 审核结果由 orchestrator 负责落盘

这样设计的原因是：

- 保持 reviewer 为“只读审查员”
- 避免审查角色越权改代码
- 明确“写”和“审”的边界

---

## 四、配置文件结构

当前项目通过根目录 `opencode.json` 定义智能体架构。

核心配置逻辑如下：

1. `default_agent = orchestrator`
2. writer / reviewer 为 subagent
3. orchestrator 具备 write / edit / bash 权限
4. reviewer 不具备 write / edit 权限

这意味着：

- 用户默认面对的是编排层
- 编排层自动组织后续动作
- 不要求用户手工切 agent 完成完整流程

---

## 五、目录契约

### 5.1 输入目录

```bash
test_cases/
```

用于存放：

- 设计说明书
- 用户指定的输入样例

典型输入：

```bash
test_cases/sheji.md
```

### 5.2 输出目录

```bash
test_cases/outputs/
```

用于存放：

- Writer 生成的源码
- Reviewer 审核报告
- 运行日志
- 结构化日志

典型输出：

- `test_cases/outputs/sheji.ts`
- `test_cases/outputs/sheji.go`
- `test_cases/outputs/sheji_audit_report.md`
- `test_cases/outputs/patentforge.log`
- `test_cases/outputs/logs.json`

### 5.3 目录契约原则

必须遵守：

1. Code-Writer 的代码必须落盘到 `test_cases/outputs/`
2. Code-Reviewer 的结论必须最终落盘到 `test_cases/outputs/`
3. 不允许只在对话中输出，不写文件

---

## 六、执行流程设计

### 6.1 标准生成流程

```text
用户输入设计说明书任务
    ↓
orchestrator
    ↓
识别输入文件 / 代码类型 / 输出名
    ↓
调用 code-writer
    ↓
生成单文件源码并落盘到 test_cases/outputs/
    ↓
调用 code-reviewer
    ↓
生成审核结论
    ↓
orchestrator 将审核报告落盘到 test_cases/outputs/
    ↓
向用户返回结果摘要
```

### 6.2 修订流程

```text
用户要求根据审核意见修改代码
    ↓
orchestrator
    ↓
读取既有审核报告
    ↓
调用 code-writer 修订已有源码
    ↓
更新源码文件
    ↓
再次调用 code-reviewer 复审
    ↓
更新审核报告
```

---

## 七、为什么不直接让 writer 和 reviewer 都作为 primary

如果 writer 和 reviewer 都是 primary，会存在几个问题：

1. 用户需要频繁手工切换角色
2. 自动执行顺序不稳定
3. 容易出现“writer 写完后没有及时审核”
4. 不利于后续接入更多角色

通过引入 orchestrator：

- 流程统一从一个入口进入
- 自动按顺序执行
- 角色职责更清晰
- 扩展能力更强

---

## 八、为什么 reviewer 不直接写审核报告文件

从权限设计角度，reviewer 是“只读审核角色”。

它负责：

- 判断
- 评估
- 给建议

但不负责：

- 直接改代码
- 直接写审查报告文件

由 orchestrator 负责落盘审核结果的好处：

1. reviewer 权限更收敛
2. 流程控制更统一
3. 更符合“编排层负责过程、审核层负责结论”的设计

---

## 九、Prompt 文件职责

当前项目中，角色逻辑不是全部写在 JSON 里，而是拆到三个 prompt 文件：

### 9.1 `agent/orchestrator.md`

负责定义：

- 工作顺序
- 路径契约
- 自动审核触发规则
- 是否允许迭代修订

### 9.2 `agent/programmer.md`

负责定义：

- 代码生成原则
- 软著场景下的真实性要求
- 代码风格与风险规避要求

### 9.3 `agent/reviewer.md`

负责定义：

- 审核维度
- 输出结构
- AI 痕迹判断标准
- 软著审核风险评估方法

这种拆分方式的价值在于：

- 更易维护
- 更易团队协作
- 更适合后续不断调优

---

## 十、设计取舍说明

### 10.1 为什么禁用 build / plan

当前项目的核心不是“通用工程构建”，而是“软著代码生成与审核”。

因此：

- `build` 暂时不参与主流程
- `plan` 也先禁用，避免与 orchestrator 重叠

如果未来需要更细粒度规划，可以重新启用 `plan`，让它成为 orchestrator 的辅助子角色。

### 10.2 为什么 writer 仍保留 edit 权限

因为本项目支持：

- 根据审核意见持续修订
- 在已有代码上做增量优化

所以 writer 必须具备 edit 权限。

### 10.3 为什么 orchestrator 也需要 write / edit / bash

因为它要承担：

- 文件落盘
- 审核报告生成
- 流程校验
- 路径和文件状态检查

如果没有这些权限，它就只能“口头编排”，不能真正闭环。

---

## 十一、后续扩展建议

当前三角色架构已经可以支撑基础闭环。后续如需扩展，可增加：

1. `doc-writer`
   - 自动生成设计说明书、使用说明书、补正说明

2. `test-runner`
   - 检查输出文件、统计行数、做基础验证

3. `risk-reviewer`
   - 专门做软著风险、代理提交风险分析

4. `refiner`
   - 在 reviewer 反馈后专门负责修订，不再由 writer 兼任

---

## 十二、总结

当前 PatentForge 的智能体架构本质上是一个项目级 AI 流程系统：

- `gpt-5.4` 负责总控和编排
- `MiniMax-M2.5` 负责写代码
- `qwen3.5-plus` 负责审核
- 所有产物统一落盘到 `test_cases/outputs/`

这一设计兼顾了：

- 自动化
- 角色边界
- 产物可追踪
- 团队可复用

它比“单一大模型包打天下”更适合在 PatentForge 这种有固定流程、固定目录契约、固定输出结构的项目中长期使用。
