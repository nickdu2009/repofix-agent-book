# 第 14 章 · 上下文选择与失败恢复

只有评测已经暴露“上下文不够”或“重复调用”时，才增加本章能力。第一版不需要向量数据库。

## 快速开始

[打开通用 Codespaces](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json){ .md-button .md-button--primary }

| 用途 | 路径 |
| --- | --- |
| 只读排名、预算与恢复骨架 | `examples/repofix/labs/chapter-14/start/` |
| 你的练习副本 | `examples/repofix/.work/chapter-14/` |
| 参考实现 | `examples/repofix/labs/chapter-14/solution/` |

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-14
python .work/chapter-14/exercise.py
make chapter-check CHAPTER=chapter-14
```

在 `.work/chapter-14/exercise.py` 中实现稳定排序与硬 Token 预算，并用固定输入验证选择结果。chapter-check 只检查 TODO；把策略迁入主项目前，收益还必须由 Eval 证明。start 不直接修改，没有收益的增强不进入主线。

## 本章契约

- **前置**：已有稳定 Eval Runner 和失败分类。
- **产物**：RepositorySummary、文件评分器、ContextBudget、重复调用检测和重规划策略。
- **验收**：在固定案例集上提高成功率或降低成本，并能说明变化来自哪里。

!!! info "诚实状态"
    chapter-14 Lab 提供可重复的排名与预算练习；循环检测和重规划仍在正文中设计，尚未全部接入主项目 Agent Loop。只有在固定 Eval 上有收益、失败路径有测试时，才把对应实现迁入 `services/agent`。

## 实践顺序

1. 用同一批案例记录成功率、步骤数、Token 和失败类型，保存无增强基线。
2. 只实现文件评分与明确的 `ContextBudget`，不要同时引入缓存和重规划。
3. 加入重复指纹与震荡检测，构造能稳定触发的反例。
4. 重跑相同案例，比较收益与新增失败；没有收益就撤回策略。
5. 通过 chapter-check 后再对照 solution，并记录实现差异。

## 建立仓库摘要

摘要只包含可验证事实：

```text
主要语言和包管理器
顶层目录
测试文件位置
可信测试命令 ID
最近失败输出
已经读取的文件与行范围
```

忽略 `.git`、依赖目录、构建产物、二进制、大文件、Secret 和隐藏评测文件。

## 文件评分

MVP 使用可解释规则：

```python
def score_file(path: str, query_terms: set[str], failing_paths: set[str]) -> int:
    score = 0
    if path in failing_paths:
        score += 100
    if any(term.lower() in path.lower() for term in query_terms):
        score += 20
    if "/tests/" in f"/{path}":
        score += 10
    if path.endswith((".lock", ".min.js", ".map")):
        score -= 50
    return score
```

评分不是“智能检索”的替代品，而是可测试基线。评测证明规则不足后再调整。

## ContextBudget

预算同时限制：

```text
最大总字符/Token
单文件上限
单次读取行数
失败日志尾部大小
重复片段去重
必须保留的任务、系统规则和最新测试结果
```

超预算时优先保留任务、最新测试失败、当前修改文件及其邻近测试；旧工具输出只保留摘要和引用 ID。

## 重复与震荡检测

为每次工具调用生成稳定指纹：

```text
sha256(tool_name + canonical_json(arguments) + workspace_revision)
```

- 同一 revision 连续出现相同指纹：重复调用。
- 两个文件内容在两个 revision 之间反复切换：修改震荡。
- 相同测试失败连续出现且没有相关文件变化：无进展。

达到阈值后不要无限继续，而是生成结构化重规划输入：已尝试什么、有哪些证据、哪些假设失败、剩余预算是多少。

## 错误分类

| 类型 | 策略 |
| --- | --- |
| 临时模型限流 | 指数退避，受 Run deadline 限制 |
| 工具超时 | 记录结果，允许一次收窄命令后的重规划 |
| Schema 错误 | 把验证错误反馈模型，不执行工具 |
| 测试失败 | 作为证据继续 Loop |
| 取消或整体超时 | 立即停止，不重规划 |
| 权限/安全拒绝 | 不绕过，明确失败或请求受支持工具 |

## 测试与实验

至少构造：大仓库目录、超大日志、重复搜索、A/B 文件震荡、无关文件噪声和取消中的重规划。每项都有预算断言，不能只观察日志。

## 练习

1. 让两个文件得到相同分数，定义并测试稳定的次级排序规则。
2. 构造“参数相同但 revision 不同”的调用，证明它不应被误判为重复。
3. 为一次无收益的上下文改进写回滚结论，而不是只展示最好的一次运行。

## 故障排查与验收

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 模型总是漏掉关键测试 | 排名不包含失败路径 | 将测试输出中的文件路径加入高权重证据 |
| Token 持续增长 | 只追加不压缩 | 按 revision 保存摘要并去重旧输出 |
| 死循环检测误报 | 指纹没有包含 revision | 将工作区版本加入指纹 |

验收报告必须比较增强前后成功率、步骤数、Token、成本和失败类型；没有可测收益的策略不进入主线。
