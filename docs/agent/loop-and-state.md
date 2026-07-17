# Agent 状态与决策循环

这一章实现 RepoFix 最重要的部分：模型可以提出动作，但只有程序能够推进状态、计算预算并确认“候选修复已就绪”。最终 Run 成功仍由 Go 控制面在独立验证后决定。

## 本章卡片

| 项目 | 内容 |
| --- | --- |
| 前置章节 | Python 基础恢复与项目环境 |
| 最终产物 | 可运行的 `AgentRunner`、Fake 模型与 Executor、完整失败路径测试 |
| 预计时间 | 3～4 小时 |
| 本章不做 | 网络调用、真实仓库命令、Go 持久化、自动重试 |

完成后，你应该能够：

- 画出一次 `模型 → 工具 → 工具结果 → 模型` 循环的数据流。
- 区分模型历史、领域状态和控制状态。
- 解释普通文本、旧测试结果和模型自报成功为什么都不可信。
- 用测试证明步数、Token、时间与取消信号由程序控制。

## 1. 先运行测试，再读实现

```bash
cd examples/repofix
make test
```

当前测试覆盖以下关键路径：

| 场景 | 预期结果 |
| --- | --- |
| 修改后对当前版本测试，再调用 `finish` | `candidate_ready` |
| 未修改代码就测试并调用 `finish` | 拒绝完成 |
| 尝试修改受保护测试 | 工具拒绝，不能完成 |
| 模型只回复“完成了” | 协议失败 |
| 未执行测试就调用 `finish` | 拒绝完成 |
| 测试通过后再次写文件 | 拒绝完成 |
| 超过最大 Step 或 Token | 预算失败 |
| 控制面已取消 | `cancelled`，不调用模型 |
| 工具参数多字段或少字段 | 协议失败 |
| 真实模型连接 Fake Executor | 构造阶段拒绝 |

测试文件是 `services/agent/tests/test_runner.py`。建议先只运行一条：

```bash
cd services/agent
../../.venv/bin/python -m pytest -q \
  tests/test_runner.py::test_success_requires_write_current_tests_and_finish
```

预期输出：

```text
1 passed
```

## 2. 三类状态不要混在一起

### 2.1 模型历史

历史是送回模型的 JSON 数据，包括：

- 用户任务。
- 模型的工具调用。
- 与 `call_id` 对应的 `function_call_output`。

它帮助模型继续推理，但不能作为系统真实状态。

### 2.2 领域状态

`AgentState` 是程序拥有的事实：

```python
@dataclass
class AgentState:
    task: str
    status: AgentStatus = AgentStatus.RUNNING
    steps: list[StepRecord] = field(default_factory=list)
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    initial_workspace_revision: int = 0
    workspace_revision: int = 0
    last_tested_revision: int | None = None
    last_test_exit_code: int | None = None
    unresolved_tool_errors: list[str] = field(default_factory=list)
    failure_reason: str | None = None
```

### 2.3 控制状态

`RunBudget` 和 `CancellationToken` 不交给模型决定：

```python
@dataclass(frozen=True)
class RunBudget:
    max_steps: int = 20
    max_model_calls: int = 20
    max_total_tokens: int = 100_000
    max_seconds: float = 300.0
```

Go 控制面以后会拥有取消和截止时间；当前 Python 对象先固定语义并便于测试。

## 3. 模型和工具都经过端口

核心只认识两个 `Protocol`：

```python
class ModelClient(Protocol):
    @property
    def is_live(self) -> bool: ...

    def create_response(..., timeout_seconds: float) -> ModelResponse: ...


class ToolExecutor(Protocol):
    @property
    def is_sandboxed(self) -> bool: ...

    @property
    def workspace_revision(self) -> int: ...

    def execute(..., timeout_seconds: float) -> ToolResult: ...
```

`ModelResponse`、`ToolCall` 和 `ToolResult` 都是 RepoFix 自己的 DTO。OpenAI Adapter 可以变化，Agent Loop 的规则不随 SDK 类型变化。

## 4. 一轮循环的精确顺序

`AgentRunner.run()` 每轮执行：

1. 检查取消、时间、Step 和模型调用预算。
2. 使用当前历史调用 `ModelClient`。
3. 累加输入和输出 Token，并再次检查预算。
4. 把模型输出加入下一轮历史。
5. 要求恰好存在一个工具调用；普通文本或异常的多调用不能结束 Run。
6. 解析 JSON，并用严格 Schema 再做一次运行时校验。
7. 执行工具，更新 Workspace Revision 和测试事实。
8. 记录不可变的 `StepRecord`。
9. 把序列化后的 `ToolResult` 作为 `function_call_output` 送回下一轮。

核心结构可以概括为：

```python
while True:
    check_control_limits()
    response = model_client.create_response(...)
    account_tokens(response)

    if response.has_no_tool_call:
        raise ModelProtocolError("plain text cannot complete a run")

    for call in response.tool_calls:
        arguments = validate_strict_arguments(call)
        if call.name == "finish":
            return validate_finish(arguments)

        result = tool_executor.execute(call.name, arguments)
        update_program_state(result)
        record_step(call, result)
        append_function_call_output(call.call_id, result)
```

完整实现位于 `services/agent/src/repofix_agent/runner.py`。不要直接复制上面的教学伪代码替换实现，因为异常映射、历史保存和状态更新也属于协议。

## 5. 严格定义成功

`finish` 必须是该模型响应中的唯一工具调用，且以下条件全部成立：

```text
workspace_revision > initial_workspace_revision
last_test_exit_code == 0
last_tested_revision is not None
last_tested_revision == workspace_revision
unresolved_tool_errors == []
```

这组条件只产生 `AgentStatus.CANDIDATE_READY`，不是持久化的 `RunStatus.SUCCEEDED`。模型可见测试仍可能不完整或被针对性绕过；Go 必须在受保护的独立验证环境中应用 patch 并运行可信测试，才有权把 Run 置为 `succeeded`。

### 为什么需要两个 Revision

假设执行顺序是：

```text
run_tests (revision=0, passed)
write_file (revision=1)
finish
```

只检查退出码会错误地允许成功。比较 `last_tested_revision` 与 `workspace_revision` 才能证明测试覆盖当前内容。

每次成功写入都必须增加 Revision，即使新内容看起来相同。未来的 Daytona Adapter 可以把它映射到受控计数器、内容快照或 Git Tree 哈希，但不能由模型填写。

### 普通文本不是停止条件

模型输出“测试已经通过”只是一段未验证陈述。没有 `finish` 工具调用时，Runner 抛出 `ModelProtocolError` 并把状态设为 `failed`。

### MVP 中工具错误如何处理

本版采取保守且确定的策略：一次 Run 中出现的任何失败 `ToolResult` 都进入 `unresolved_tool_errors`，模型不能用自然语言清除它，`finish` 将被拒绝。读者应根据轨迹启动一次新 Run。

后续若要支持同一 Run 内恢复，必须增加一个程序可验证的错误恢复状态机，而不是简单清空列表。

## 6. Step、模型调用和预算不是同一概念

- 一个模型响应可以没有工具调用；这属于协议错误。
- MVP 设置 `parallel_tool_calls=False`，但 Runner 仍会防御异常的多个调用。
- 每个工具调用（包括 `finish`）记录一个 Step。
- 模型调用次数单独计算，避免无工具输出反复消耗费用。
- Token 在 Adapter 归一化后累加。
- 截止时间使用单调时钟，不依赖系统日期跳变；剩余时间会传给模型和工具 Adapter，由 Adapter 对正在进行的外部调用实施超时。

预算耗尽、协议失败和完成条件不满足分别使用不同异常，方便未来映射到 Go 的错误码与事件类型。

## 7. Fake 驱动的第一个成功闭环

```python
model = FakeModelClient(
    [
        response("1", "write_file", path="calculator.py", content="fixed"),
        response("2", "run_tests", target="unit"),
        response("3", "finish", summary="fixed division"),
    ]
)
executor = FakeToolExecutor(files={"calculator.py": "buggy"})

result = AgentRunner(model, executor).run("fix division")

assert result.state.status is AgentStatus.CANDIDATE_READY
assert result.state.workspace_revision == 1
assert result.state.last_tested_revision == 1
```

Fake Executor 不读磁盘、不运行子进程。它只在内存里更新文件和 Revision，并默认拒绝写入 `tests/` 与 `.github/`。这适合证明循环和策略逻辑，但不能代替独立验证，更不能证明真实修复能力。

## 8. 练习

1. 基础：给 `RunBudget(max_steps=0)` 写失败测试，再解释为什么构造时失败比运行时失败更好。
2. 调试：让 Fake 模型返回损坏的 JSON，断言状态为 `failed` 且 Executor 没被调用。
3. 状态：模拟第一次测试失败、随后再次测试通过，确认最后一个测试事实覆盖前一个测试事实。
4. 安全：尝试写入 `tests/test_calculator.py`，确认策略拒绝且本次 Run 不能完成。
5. 扩展：设计“可恢复工具错误”的状态转移表。先写 ADR，不要直接清空错误列表。

## 9. 常见问题

| 现象 | 原因 | 排查 |
| --- | --- | --- |
| Fake 响应耗尽 | 脚本化响应数量少于实际模型调用次数 | 查看 `FakeModelClient.requests` 和已记录 Step |
| 已测试仍无法 `finish` | 测试后又发生写入 | 比较两个 Revision，而不是只看退出码 |
| 工具成功但 `finish` 被拒绝 | 之前存在失败 `ToolResult` | 查看 `unresolved_tool_errors`；MVP 重新开始 Run |
| Token 预算立即耗尽 | Fake 或 Adapter 返回了超过上限的 Usage | 检查输入、输出 Token 是否被重复累计 |
| 取消后仍访问模型 | 在调用模型前没有检查 Token | 运行 `test_cancelled_run_does_not_call_model` |

## 10. 本章验收

```bash
cd examples/repofix/services/agent
../../.venv/bin/python -m pytest -q tests/test_runner.py
```

完成标准：

- 成功、普通文本、未测试完成、旧测试、最大步数和取消测试全部通过。
- 每个 Step 都包含 `call_id`、参数、统一结果和 Workspace Revision。
- Core 文件没有导入 `openai`。
- 你能够从测试轨迹说明候选修复为什么就绪或失败，以及谁决定最终 Run 成功。
- 修改任何完成条件后，至少一条失败路径测试会报警。
