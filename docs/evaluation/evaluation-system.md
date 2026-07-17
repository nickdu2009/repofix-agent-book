# 评测体系

Agent 开发不能只看一次演示是否成功。

### 12.1 评测案例结构

```text
evals/cases/python-off-by-one/
├── repository/
├── issue.md
├── expected-tests.txt
└── metadata.json
```

`metadata.json` 示例：

```json
{
  "case_id": "python-off-by-one",
  "language": "python",
  "difficulty": "easy",
  "expected_test_command": "pytest",
  "max_steps": 12
}
```

### 12.2 指标

```text
任务成功率
测试通过率
平均步骤数
无效工具调用数
重复动作数
平均耗时
输入和输出 Token
单任务成本
超时率
沙箱清理成功率
```

### 12.3 Python 测试特性

评测阶段重点学习：

- pytest fixture。
- `pytest.mark.parametrize`。
- `tmp_path`。
- Fake Model。
- 迭代器和生成器。
- JSONL。
- `statistics`。
- 测试替身和故障注入。

```python
import pytest


@pytest.mark.parametrize(
    ("case_name", "expected"),
    [
        ("python-off-by-one", True),
        ("go-nil-pointer", True),
        ("unsolvable", False),
    ],
)
def test_eval_case(case_name: str, expected: bool) -> None:
    result = run_eval(case_name)
    assert result.success is expected
```

### 12.4 测试分层

| 层级 | 触发时机 | 是否使用真实模型 |
| --- | --- | --- |
| 单元测试 | 每次提交 | 否，使用 Fake Model |
| 契约测试 | 每个 PR | 否 |
| 沙箱集成测试 | 每个 PR | 通常否 |
| Smoke Eval | Prompt、模型或工具变化 | 是，3～5 个案例 |
| Full Eval | 每周或发布前 | 是，20～30 个案例 |
