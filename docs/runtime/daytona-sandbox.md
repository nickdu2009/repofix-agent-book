# 云沙箱接入

### 8.1 抽象 Sandbox 接口

```python
from typing import Protocol


class Sandbox(Protocol):
    def clone(self, repository_url: str) -> None:
        ...

    def read_file(self, path: str) -> str:
        ...

    def write_file(self, path: str, content: str) -> None:
        ...

    def exec(self, command: str, timeout: int) -> ToolResult:
        ...

    def close(self) -> None:
        ...
```

实现两个适配器：

```text
LocalSandbox       单元测试与受控 Fixture
DaytonaSandbox     真实隔离执行
```

### 8.2 Python 特性：上下文管理器

沙箱必须保证清理，适合使用 `with`：

```python
with DaytonaSandbox() as sandbox:
    sandbox.clone(repository_url)
    result = sandbox.exec("pytest", timeout=120)
```

需要学习：

- `__enter__` 与 `__exit__`。
- `try/finally`。
- 异常发生时的资源清理。
- `async`、`await`、超时与取消。

Daytona 支持创建隔离 Sandbox，并执行带工作目录、环境变量和超时的命令。参考：[Daytona SDK](https://www.daytona.io/docs/en/python-sdk/) 和 [Process Execution](https://www.daytona.io/docs/en/process-code-execution/)

### 8.3 沙箱安全规则

- 每个 Run 使用独立沙箱。
- 设置最大运行时长。
- 限制 CPU、内存和磁盘。
- 默认不传入宿主环境变量。
- 不传入主 GitHub Token。
- 不允许访问生产数据库。
- 限制日志大小。
- 无论成功、失败还是取消，都执行清理。
