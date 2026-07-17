# Python 基础恢复与项目环境

这一章不从语法表重新学习 Python，而是建立一个可以测试、可以替换模型、不会把 SDK 类型泄漏进核心逻辑的 Agent 包。

## 本章卡片

| 项目 | 内容 |
| --- | --- |
| 前置章节 | 云端工作区；第一个缺陷练习仓库 |
| 开发基线 | Python 3.14.x；只使用稳定语言特性 |
| 最终产物 | `repofix_agent` 源码包、确定性 Demo、完整离线单元测试 |
| 预计时间 | 2～3 小时 |
| 安全边界 | 本章不允许真实模型执行宿主机工具或命令 |

完成后，你应该能够解释：

- `dataclass`、`StrEnum` 和 `Protocol` 分别承担什么职责。
- 为什么 Agent 核心只依赖自有 DTO，而不依赖 OpenAI SDK 返回类型。
- 为什么真实模型客户端与本地 Fake Executor 不能组合。
- 如何在没有 API Key、没有网络的情况下测试完整决策循环。

## 1. 从伴随代码开始

本章代码位于：

```text
examples/repofix/services/agent/
├── pyproject.toml
├── src/
│   └── repofix_agent/
│       ├── __init__.py
│       ├── __main__.py
│       ├── api.py
│       ├── api_models.py
│       ├── config.py
│       ├── domain.py
│       ├── errors.py
│       ├── fake.py
│       ├── openai_adapter.py
│       ├── path_tools.py
│       ├── protocols.py
│       ├── runner.py
│       ├── schemas.py
│       └── service.py
└── tests/
    ├── test_api.py
    ├── test_openai_adapter.py
    ├── test_path_tools.py
    ├── test_runner.py
    └── test_schemas.py
```

在书籍仓库根目录执行：

```bash
cd examples/repofix
make bootstrap
make test
```

预期最后一行类似：

```text
31 passed
```

测试数随教程扩展可能增加；关键是退出码为 `0`，且测试没有访问网络。

## 2. 读懂 `pyproject.toml`

`services/agent/pyproject.toml` 同时声明 Python 版本、包发现方式和测试配置：

```toml
[project]
name = "repofix-agent"
requires-python = ">=3.14,<3.15"
dependencies = []

[project.optional-dependencies]
dev = ["httpx==0.28.1", "pytest==9.1.1", "ruff==0.15.22"]
live = ["openai>=2.0,<3"]
service = ["fastapi==0.139.2", "pydantic==2.13.4", "uvicorn==0.51.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

这里有四个有意的选择：

1. 默认依赖为空，Agent 核心可以完全离线运行。
2. OpenAI SDK 是 `live` 可选依赖，只存在于适配器一侧。
3. FastAPI、Pydantic 和 Uvicorn 只在 `service` extra 中；HTTPX 只用于离线 ASGI 测试。
4. `src` 布局避免测试偶然从项目根目录导入错误模块。
5. Python 版本限定为 3.14 系列，让正文、骨架、CI 和类型工具使用同一套现代语义。

## 3. 用 Go 经验理解第一批 Python 特性

| Python 特性 | RepoFix 中的用途 | 可类比的 Go 概念 | 不能忽略的差异 |
| --- | --- | --- | --- |
| 类型标注 | 工具参数、状态和返回值 | 静态类型声明 | 默认不在运行时强制检查 |
| `dataclass` | `AgentState`、`ToolResult` | `struct` | 可生成初始化和比较方法 |
| `dataclass(slots=True)` | 小型领域 DTO | 更紧凑的固定字段 struct | 不再允许运行时随意添加属性 |
| `StrEnum` | `AgentStatus` | 自定义字符串常量 | 同时是枚举和值为字符串的类型；不要与 Go 拥有的 RunStatus 混用 |
| `Protocol` | `ModelClient`、`ToolExecutor` | `interface` | 采用结构化子类型，无需显式注册 |
| `type` 类型别名 | `ModelOutput` 等联合类型 | `type` 声明 | 只服务静态类型，不做运行时校验 |
| `Path` | 工作区路径校验 | `filepath` | `resolve()` 会处理符号链接 |
| 异常 | 协议、预算、取消失败 | `error` | 沿调用栈传播，不作为返回值 |
| pytest fixture | 临时目录和测试替身 | `testing` helper | 由名字注入测试函数 |

暂时不要学习元类、描述符、复杂装饰器、多进程和类型体操。这些内容不会帮助我们建立第一条修复闭环。

## 4. 核心 DTO 不认识 OpenAI SDK

模型适配器把外部响应归一化成自己的对象：

```python
@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True, slots=True)
class ModelResponse:
    output: tuple[ToolCall | AssistantText, ...]
    input_tokens: int = 0
    output_tokens: int = 0
```

这样做带来三个结果：

- Agent Loop 可以用 Fake 响应做确定性测试。
- SDK 升级只影响 `openai_adapter.py`。
- Python、Go 和 TypeScript 可以围绕项目契约演进，而不是围绕某个 SDK 类演进。

`ModelClient` 使用 `Protocol` 表达最小端口：

```python
class ModelClient(Protocol):
    @property
    def is_live(self) -> bool: ...

    def create_response(
        self,
        *,
        instructions: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> ModelResponse: ...
```

`FakeModelClient` 只按顺序返回预先写好的 `ModelResponse`，并保存收到的请求，便于测试下一轮是否包含上一轮工具结果。

## 5. 运行零网络 Demo

从 `examples/repofix/services/agent` 执行：

```bash
PYTHONPATH=src ../../.venv/bin/python -m repofix_agent
```

预期输出：

```text
status=candidate_ready
steps=3
summary=Fixed and verified calculator
```

这个 Demo 的三个模型响应都是脚本化数据：`write_file → run_tests → finish`。它验证循环能形成候选结果，不代表真实缺陷已被修复，也不等于最终 Run 成功。

## 6. 可选：第一次真实模型调用

只有这一小节需要网络和 API Key，而且不向模型提供文件或命令工具。

```bash
cd examples/repofix/services/agent
../../.venv/bin/python -m pip install -e '.[live]'
export OPENAI_API_KEY='在 Codespaces Secret 中设置，不要写入仓库'
export OPENAI_MODEL='gpt-5.6-sol'
```

创建一个临时练习脚本，调用 Responses API 并只打印文本：

```python
import os

from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model=os.getenv("OPENAI_MODEL", "gpt-5.6-sol"),
    input="用一句话说明 Agent State 为什么不能只写在 Prompt 中。",
)
print(response.output_text)
```

正式 RepoFix 使用 `OpenAIModelClient`。它会：

- 将 SDK 输出转换为项目 DTO。
- 保存可继续传回 Responses API 的历史项。
- 记录输入和输出 Token。
- 为单次响应设置输出上限，并默认不保存响应。
- 使用 Run 剩余时间设置请求超时，并关闭 SDK 自动重试，避免与控制面重试叠加。
- 关闭并行工具调用，避免 MVP 中多个写操作竞态。
- 拒绝 `failed`、`incomplete` 和意外状态。

模型名始终可以通过 `OPENAI_MODEL` 替换，不要把教程的默认值当成永久不变的产品选择。当前 API 用法参考 [OpenAI Responses API](https://developers.openai.com/api/docs/guides/function-calling)。

## 7. 安全门必须由代码执行

`OpenAIModelClient.is_live` 为 `True`，`FakeToolExecutor.is_sandboxed` 为 `False`。以下组合会在构造 Runner 时立即失败：

```python
AgentRunner(OpenAIModelClient(), FakeToolExecutor())
# UnsafeExecutionError: a live model requires a sandboxed executor
```

这不是 Prompt 建议，而是程序不变量。接入 Daytona 后，只有真正把读写和测试留在隔离环境中的 Adapter 才能返回 `is_sandboxed=True`。

## 8. 小练习

先亲自完成，再查看伴随代码：

1. 写一个不超过 30 行的 `FakeModelClient`，连续调用三次时返回三条不同响应。
2. 给 `RunBudget` 增加非法值校验，并为 `max_steps=0` 写测试。
3. 在 Fake 请求记录中断言工具 Schema 被传给每一次模型调用。
4. 扩展 OpenAI Adapter 测试，使 `status="failed"` 时不返回 `ModelResponse`。

不要把练习改成真实 API 单测；单元测试必须保持零费用、零网络、可重复。

## 9. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `No module named repofix_agent` | 没有从 Agent 目录运行，且未设置源码路径 | 使用 `PYTHONPATH=src ../../.venv/bin/python -m repofix_agent` |
| `No module named pytest` | 尚未执行工作区初始化 | 回到 `examples/repofix` 执行 `make bootstrap` |
| `UnsafeExecutionError` | 把真实模型与非沙箱 Executor 组合 | 保留 Fake，或先完成 Daytona 章节 |
| API 认证失败 | Codespaces Secret 未注入当前终端 | 重新打开 Codespace，并只检查变量是否存在，不打印值 |
| 默认模型不可用 | 账号权限或模型目录已变化 | 查阅官方模型目录并设置 `OPENAI_MODEL` |

## 10. 本章验收

在 `examples/repofix` 执行：

```bash
make test
cd services/agent
PYTHONPATH=src ../../.venv/bin/python -m repofix_agent
```

完成标准：

- 测试全部通过且没有网络请求。
- Demo 以 `candidate_ready` 结束并记录三个 Step。
- 你能指出 SDK 类型止步于哪个文件。
- 你能演示真实模型加 Fake Executor 会被拒绝。
- API Key、`.env` 和模型原始敏感日志均未进入 Git。
