<!-- LAB:chapter-07 STATUS:complete -->

# ADR：运行时边界

## Context

Agent 实验需要快速迭代，而 Run 状态、取消和 Sandbox 清理需要稳定的长期所有者。

## Decision

Go 持久化 Run、编排 Sandbox 并决定终态；Python 运行模型决策循环，只返回候选结果。跨进程数据遵循版本化 JSON 契约。

## Consequences

收益是所有权明确且可独立恢复；成本是增加服务与契约测试。若跨进程故障成本长期高于独立伸缩收益，则重新评估拆分。
