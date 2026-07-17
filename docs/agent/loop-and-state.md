# Agent 状态与决策循环

### 6.1 定义状态

```python
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class StepRecord:
    number: int
    tool_name: str
    arguments: dict[str, Any]
    result: str


@dataclass
class AgentState:
    task: str
    status: RunStatus = RunStatus.RUNNING
    steps: list[StepRecord] = field(default_factory=list)
    last_test_exit_code: int | None = None
```

实践重点：

- 为什么状态不能只存在于 Prompt 中。
- 哪些状态属于模型上下文，哪些属于系统控制状态。
- 为什么测试退出码比模型的成功声明更可信。
- 如何限制最大步骤数、运行时间和模型费用。

### 6.2 定义模型接口

使用 `Protocol` 隔离 OpenAI SDK：

```python
from typing import Protocol


class ModelClient(Protocol):
    def create_response(
        self,
        *,
        instructions: str,
        history: list[object],
        tools: list[dict[str, object]],
    ) -> object:
        ...
```

实现：

```text
OpenAIModelClient   真实模型调用
FakeModelClient     单元测试中的确定性返回
```

这样可以让大多数测试不消耗模型额度，也不受网络波动影响。

### 6.3 手写 Agent Loop

```python
import json


def run_agent(task: str, max_steps: int = 20) -> str:
    history: list[object] = [
        {"role": "user", "content": task}
    ]

    for step_number in range(1, max_steps + 1):
        response = model_client.create_response(
            instructions=SYSTEM_INSTRUCTIONS,
            history=history,
            tools=TOOL_SCHEMAS,
        )

        history.extend(response.output)

        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            return response.output_text

        for call in tool_calls:
            arguments = json.loads(call.arguments)

            if call.name == "finish":
                return validate_finish(arguments)

            result = tool_executor.execute(call.name, arguments)

            history.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError("maximum agent steps exceeded")
```

OpenAI Responses API 的工具循环包括：模型返回 `function_call`，应用执行函数，再用 `function_call_output` 返回结果。参考：[Function Calling](https://developers.openai.com/api/docs/guides/function-calling)

### 6.4 明确停止条件

Agent 只有在以下条件全部满足时才能成功：

- 调用了 `finish`。
- 至少执行过一次测试命令。
- 最近一次相关测试退出码为 `0`。
- 没有未处理的工具错误。
- 没有超过时间、步骤和成本预算。

```python
def validate_finish(arguments: dict[str, object]) -> str:
    if state.last_test_exit_code != 0:
        raise RuntimeError("cannot finish before tests pass")

    state.status = RunStatus.SUCCEEDED
    return str(arguments["summary"])
```
