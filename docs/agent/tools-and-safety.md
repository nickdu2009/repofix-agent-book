# 工具系统与安全边界

### 7.1 MVP 工具集

```text
list_files
read_file
search_code
write_file
run_command
finish
```

工具应小而清晰。不要一开始提供一个可以完成所有操作的 `shell` 工具。

### 7.2 安全路径解析

```python
from pathlib import Path


def resolve_safe_path(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve()
    target = (resolved_root / relative_path).resolve()

    if target != resolved_root and resolved_root not in target.parents:
        raise ValueError("path escapes workspace")

    return target
```

必须测试：

```text
../../etc/passwd
/etc/passwd
工作区外的符号链接
不存在的文件
过大的文件
二进制文件
```

### 7.3 受限命令执行

在接入云沙箱前，只能在专门构造的 `fixtures/` 仓库中执行受限命令：

```python
import shlex
import subprocess
from pathlib import Path


ALLOWED_COMMANDS = {"pytest", "go", "npm", "git", "rg"}


def run_command(root: Path, command: str) -> dict[str, object]:
    args = shlex.split(command)

    if not args or args[0] not in ALLOWED_COMMANDS:
        raise ValueError("command is not allowed")

    result = subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[-10_000:],
        "stderr": result.stderr[-10_000:],
    }
```

不要使用 `shell=True`。这仍然不是完整沙箱，只是早期练习保护。

### 7.4 工具结果统一格式

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] | None = None
```

模型需要能够区分：

- 工具调用成功且结果为空。
- 工具调用失败。
- 命令成功执行但测试失败。
- 输出被截断。
- 命令超时。
