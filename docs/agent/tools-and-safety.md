# 第 06 章 · 工具系统与安全边界

工具让模型影响外部世界，也是 RepoFix 风险最高的边界。本章把工具协议、路径限制和执行隔离分别处理；命令名白名单不再被描述成沙箱。

## 快速开始

| 入口 | 内容 |
| --- | --- |
| Codespaces | [打开 RepoFix 通用工作区](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json) |
| 只读骨架 | `examples/repofix/labs/chapter-06/start/` |
| 准备工作副本 | `make chapter-prepare CHAPTER=chapter-06` |
| 工作副本 | `.work/chapter-06/` |
| 结构检查 | `make chapter-check CHAPTER=chapter-06` |
| 复盘参考 | `examples/repofix/labs/chapter-06/solution/` |

在 Codespaces 终端进入 `examples/repofix`，先运行 `chapter-prepare`，再只在 `.work/chapter-06/` 完成 TODO，最后运行 `chapter-check`。`start/` 始终只读；只有通过验收并记录自己的取舍后才用 `solution/` 复盘，不要从参考实现开始复制。

完成路径函数后运行 `python .work/chapter-06/exercise.py`，确认正常路径与逃逸路径都符合预期；只运行教程自带的短练习。

## 本章卡片

| 项目 | 内容 |
| --- | --- |
| 前置章节 | Agent 状态与决策循环；第一个缺陷练习仓库 |
| 最终产物 | 六个严格工具 Schema、统一 `ToolResult`、安全路径函数、Fake Executor |
| 预计时间 | 3～4 小时 |
| 关键限制 | Daytona 接入前，真实模型不能读写或执行开发宿主机上的仓库 |

完成后，你应该能够解释：

- JSON Schema 严格模式解决什么问题，又没有解决什么问题。
- 路径校验、命令白名单和真正的进程隔离有什么区别。
- 为什么 `pytest`、`npm test` 和 `go test` 也属于执行不可信代码。
- Executor 必须向核心返回哪些可验证元数据。

## 1. 先建立威胁模型

模型可能产生错误或恶意的：

- `../../etc/passwd`、绝对路径和符号链接逃逸。
- 超大文件、二进制文件和恶意编码。
- 修改测试以制造“通过”。
- `npm test`、pytest 插件、Go 测试等仓库内任意代码执行。
- 挂起、海量输出、派生子进程和网络外传。
- 在测试通过后继续修改文件，再使用旧结果完成。

因此本教程固定以下执行矩阵：

| 模型 | Executor | 是否允许 | 用途 |
| --- | --- | --- | --- |
| Fake | Fake | 允许 | Agent Loop 单元测试 |
| Fake | 本地受信 Fixture 辅助代码 | 仅允许人工触发 | 语言和路径练习 |
| 真实模型 | Fake 或宿主机 | 禁止，代码直接拒绝 | 无 |
| 真实模型 | Daytona Sandbox | 接入后允许 | 真实修复 Smoke/Eval |

命令第一项在白名单中并不等于安全。`pytest` 可以加载插件，`npm` 可以运行 scripts，`go test` 会编译并执行仓库代码，`git` 的部分操作也可能触发 Hook 或网络访问。

## 2. MVP 只有六个工具

```text
list_files
read_file
search_code
write_file
run_tests
finish
```

这里故意没有通用 `run_command`：

- `run_tests` 只接受控制面预先配置的命名目标，例如 `unit`。
- 模型不能把任意 shell 字符串传给系统。
- `finish` 由 Runner 处理，不交给 Executor。
- 后续如果确实需要命令工具，也必须由 Sandbox Adapter 执行结构化参数，而不是 `shell=True`。

## 3. 严格 Schema 是第一道边界

一个工具定义示例：

```python
{
    "type": "function",
    "name": "read_file",
    "description": "Read one UTF-8 text file inside the workspace.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    "strict": True,
}
```

`schemas.py` 中所有字段都列入 `required`，并设置 `additionalProperties=False`。Runner 在解析 JSON 后还会再次验证：

- 工具名必须已注册。
- 参数必须是 JSON Object。
- 不能缺字段或增加字段。
- 当前所有参数值必须是字符串。

严格 Schema 减少格式错误，但不会判断路径是否安全、内容是否可信、测试是否覆盖真实需求。这些仍由工具实现和系统状态验证。

验证全部 Schema：

```bash
cd examples/repofix/services/agent
../../.venv/bin/python -m pytest -q tests/test_schemas.py
```

预期输出：

```text
1 passed
```

## 4. 所有执行结果使用同一格式

```python
@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

字段语义：

| 字段 | 含义 |
| --- | --- |
| `ok` | 工具本身是否完成；不等于测试通过 |
| `output` | 经过大小限制和脱敏的文本输出 |
| `error` | 工具失败原因；成功时为 `None` |
| `metadata` | 程序消费的结构化事实，不由模型填写 |

`run_tests` 正常执行但测试失败时，`ok=True`、`metadata.exit_code=1`。如果 Sandbox 进程根本无法启动，则 `ok=False`。

成功测试还必须提供：

```json
{
  "exit_code": 0,
  "tested_revision": 3,
  "target": "unit"
}
```

## 5. 路径必须相对于 Workspace

伴随代码的 `path_tools.py` 首先拒绝空路径和绝对路径，再解析符号链接并验证最终目标仍在根目录内：

```python
def resolve_safe_path(root: Path, relative_path: str) -> Path:
    if not relative_path:
        raise WorkspacePathError("path must not be empty")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise WorkspacePathError("absolute paths are not allowed")

    resolved_root = root.resolve(strict=True)
    target = (resolved_root / candidate).resolve(strict=False)
    if target != resolved_root and resolved_root not in target.parents:
        raise WorkspacePathError("path escapes workspace")
    return target
```

读文件还会检查：

- 目标是普通文件。
- 默认不超过 1 MB。
- 不包含 NUL 字节。
- 内容是合法 UTF-8。

写文件先检查编码后的大小，再在同一目录创建临时文件、刷新并使用 `os.replace()` 原子替换。这样可以减少半写入文件，但它仍不是针对恶意并发进程的完整防御。

运行路径测试：

```bash
cd examples/repofix/services/agent
../../.venv/bin/python -m pytest -q tests/test_path_tools.py
```

测试包含 `../`、绝对路径、工作区外符号链接、二进制、超大文件和正常 UTF-8 写入。

## 6. Executor 接口预留真正沙箱

```python
class SandboxExecutor(ToolExecutor, Protocol):
    """实现必须把读、写和测试全部留在同一个隔离 Sandbox。"""
```

接口还要求两个属性：

```python
is_sandboxed: bool
workspace_revision: int
```

`AgentRunner` 在构造阶段执行安全门：

```python
if model_client.is_live and not tool_executor.is_sandboxed:
    raise UnsafeExecutionError("a live model requires a sandboxed executor")
```

不要创建一个只把 `is_sandboxed` 写成 `True`、实际仍在宿主机运行的 Adapter。Python Adapter 只调用带短期 capability 的 Go Tool Gateway；Go 必须保证文件读取、修改、测试进程、工作目录和 Revision 都来自同一个隔离实例，并在所有结束路径删除 Daytona Sandbox。

## 7. Fake Executor 如何帮助学习

`FakeToolExecutor`：

- 文件只存在于内存字典。
- `write_file` 每次将 Revision 加一。
- `run_tests` 从预设退出码队列取值。
- `write_file` 默认拒绝 `tests/` 与 `.github/` 受保护路径。
- 从不打开网络、磁盘或子进程。
- 明确返回 `is_sandboxed=False`。

这使我们能够安全构造“测试后又修改”“测试失败后重试”和“文件不存在”等轨迹。它不能代替 Daytona 集成测试。

## 8. 验证故意失败的 Fixture

练习仓库位于：

```text
examples/repofix/fixtures/buggy-calculator/
├── calculator.py
├── README.md
└── tests/
    └── test_calculator.py
```

`calculator.py` 故意把真除法写成整除。该代码由教程作者控制，不是模型生成代码；在 `examples/repofix` 人工执行：

```bash
make fixture-test
```

预期基线必须是：

```text
FAILED ...::test_fractional_division - assert 2 == 2.5
1 failed, 1 passed
```

验收规则：

- 只允许修改 `calculator.py`。
- 不允许修改或删除测试。
- 将 `//` 修复为 `/` 后必须是 `2 passed`。
- 恢复故意缺陷后再继续后续章节，避免书籍基线被悄悄改成绿色。

真实模型直到 Daytona 章节才接触这份 Fixture。

## 9. 练习

1. 路径：增加一个指向工作区内部文件的符号链接测试，说明它为何可以读取。
2. 大小：把最大文件限制作为 Executor 配置传入，并测试边界值正好等于上限。
3. Schema：向 `read_file` 增加非必需参数时，研究严格模式如何用 `null` 表达可选值。
4. 结果：模拟 Sandbox 启动失败和测试退出码为 `1`，比较两个 `ToolResult`。
5. 安全设计：列出 `run_command("pytest")` 仍可被利用的三条路径，并解释结构化 `run_tests(target="unit")` 如何缩小权限。

## 10. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 正常路径被判定逃逸 | Workspace 根目录不存在或路径经过外部符号链接 | 先确认根目录，再检查 `resolve()` 后的实际目标 |
| 测试失败却看到 `ToolResult.ok=True` | 工具进程成功执行，业务测试退出码非零 | 读取 `metadata.exit_code`，不要混淆两层成功 |
| `finish` 没有进入 Executor 调用记录 | 它属于 Runner 的控制动作 | 查看 `StepRecord`，而不是 Fake Executor calls |
| Fixture 测试全部通过 | 故意缺陷已被本地修改 | 恢复 `calculator.py` 的基线，或对照 Fixture README |
| 想临时开放 `git`/`npm` | 命令白名单被误当成隔离 | 等待 Daytona，并为具体能力设计结构化工具 |

## 11. 本章验收

```bash
cd examples/repofix
make test
make fixture-baseline
```

完成标准：

- Agent 单元测试全部通过。
- Fixture 精确显示 `1 failed, 1 passed`。
- 修改 `tests/test_calculator.py` 的尝试会被策略拒绝。
- 路径逃逸、外部符号链接、二进制和大文件测试存在。
- 六个工具 Schema 均为严格且关闭额外字段。
- 核心只处理 `ToolResult`，没有混用字典返回值。
- 真实模型与非沙箱 Executor 的组合由代码拒绝。
- 教程没有建议在 Codespaces 执行模型生成的命令或代码。
