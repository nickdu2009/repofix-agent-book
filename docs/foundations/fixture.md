# 第 03 章 · 第一个缺陷练习仓库

## 快速开始

[打开通用 Codespaces](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json){ .md-button .md-button--primary }

| 用途 | 路径 |
| --- | --- |
| 只读缺陷骨架 | `examples/repofix/labs/chapter-03/start/` |
| 你的练习副本 | `examples/repofix/.work/chapter-03/` |
| 最小修复参考 | `examples/repofix/labs/chapter-03/solution/` |

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-03
python .work/chapter-03/exercise.py
make chapter-check CHAPTER=chapter-03
```

在 `.work/chapter-03/exercise.py` 中先运行并观察失败，再完成最小修复；不要直接修改 start。`chapter-check` 验证 TODO 与完成标记，不替代你对程序输出的判断。`solution/` 只在验收后用于比较。

## 本章目标

完成本章后，你能够：

- 用失败测试证明缺陷在修复前真实存在；
- 把 Issue 描述转成输入、实际结果、预期结果和约束；
- 人工完成一次最小修复并用测试证明行为；
- 解释为什么 Fixture、测试和修复代码必须分开保存。

## 前置条件与本章产物

前置条件：已经完成[仓库与云端开发工作区](cloud-workspace.md)，`make bootstrap` 成功。

本章会使用：

```text
examples/repofix/fixtures/buggy-calculator/
├── README.md
├── calculator.py
└── tests/
    └── test_calculator.py
```

产物是一份人工修复 Diff 和一篇学习日志。后续 Agent 章节会从干净的缺陷 Checkpoint 重新完成同一任务。

## 1. 阅读 Issue，而不是先猜代码

练习 Issue：

> `divide` 对不能整除的整数返回了截断结果。`divide(5, 2)` 当前返回 `2`，应返回 `2.5`。保持已有整数整除行为，并且只做解决该缺陷所需的最小修改。

把它拆成可验证契约：

| 项目 | 值 |
| --- | --- |
| 输入 | `divide(5, 2)` |
| 当前错误结果 | `2` |
| 预期结果 | `2.5` |
| 回归约束 | 原有整数整除测试继续通过 |
| 修改范围 | `calculator.py` 的除法实现 |

“最小修改”不等于“不写测试”。测试是修复成立的证据，不是附加功能。

## 2. 证明基线确实失败

从伴随项目根目录执行：

```bash
make fixture-baseline
```

输出中应同时出现：

```text
1 failed, 1 passed
PASS: buggy-calculator has exactly one failure and one pass before repair
```

这个 Make target 把“预期存在一个失败”当作成功验收，因此最终退出码是 `0`。如果两个测试都通过，它反而失败，因为那说明 Fixture 不再是书中定义的起始状态。

直接运行测试则会返回非零退出码：

```bash
make fixture-test
```

不要在 CI 中把所有失败都解释为“Fixture 正常”。只有 `make fixture-baseline` 对这个已知基线执行反向断言。

## 3. 重现和定位

先直接观察行为：

```bash
cd fixtures/buggy-calculator
../../.venv/bin/python -c 'from calculator import divide; print(divide(5, 2))'
cd ../..
```

修复前输出：

```text
2
```

阅读实现和测试：

```bash
sed -n '1,160p' fixtures/buggy-calculator/calculator.py
sed -n '1,200p' fixtures/buggy-calculator/tests/test_calculator.py
```

`//` 是 Python 的向下取整除法，`/` 才产生普通除法结果。这里不需要新框架、浮点格式化或重写函数。

## 4. 完成最小人工修复

在 `calculator.py` 中把返回表达式改为：

```python
return left / right
```

检查 Diff，确认没有改测试：

```bash
git diff -- examples/repofix/fixtures/buggy-calculator
```

然后验证：

```bash
make fixture-test
```

预期结尾：

```text
2 passed
```

最后再次重现：

```bash
cd fixtures/buggy-calculator
../../.venv/bin/python -c 'from calculator import divide; print(divide(5, 2))'
```

预期输出：

```text
2.5
```

## 5. 这条人工基线有什么用

以后运行 Agent 时，你已经知道：

- 任务有一个确定、可复现的修复；
- 初始测试确实失败；
- 修复后可信测试会通过；
- 人工基线只需要一次局部修改；
- Agent 若修改测试、删除断言或声称无法解决，应判为失败或异常。

这使你能够把 Agent 故障与练习仓库本身的故障分开。

## 测试与验收

- [ ] 干净起始状态下，`make fixture-baseline` 输出 `1 failed, 1 passed` 后返回成功。
- [ ] 修复前，`divide(5, 2)` 输出 `2`。
- [ ] Diff 只修改实现，没有弱化或删除测试。
- [ ] 修复后，`make fixture-test` 输出 `2 passed`。
- [ ] 修复后，`divide(5, 2)` 输出 `2.5`。
- [ ] 能解释为什么模型自报成功不能替代这些断言。

## 故障排查

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| `make fixture-baseline` 报“unexpectedly passed” | 当前学习分支已经修复 Fixture | 先保存学习提交，再从未修改 Fixture 的 `main` 创建新练习分支并重跑基线 |
| `No module named calculator` | 从错误目录直接导入 | 使用本章给出的 `cd fixtures/buggy-calculator` 命令 |
| 修复后仍返回 `2` | 仍使用 `//`，或改错文件 | 查看 `git diff` 和 Python 实际导入路径 |
| 测试通过但 Git Diff 包含测试修改 | 验收证据被污染 | 恢复测试，只修改实现后重新运行 |
| 整个 `make test` 因 Fixture 失败 | 把故意失败案例加入默认测试目标 | 默认项目测试与 `fixture-test` 分开运行 |

## 练习

1. **基础**：解释 `5 // 2`、`5 / 2` 和 `-5 // 2` 的差别。
2. **调试**：故意把预期值改成错误值，观察为什么“修改测试让它通过”不是修复。
3. **扩展**：为负数和零除数补充测试，先写清预期行为，再修改代码。

## Checkpoint

把人工修复保存为学习提交，并记录测试输出。后续 Agent 章节不要沿用已经修好的分支；从仍保留原始缺陷的 `main` 创建新练习分支，并先用 `make fixture-baseline` 证明 Agent 面对的是可验证起点。章节 Lab 始终可通过 `chapter-prepare` 从只读骨架重新生成，不依赖 tag。
