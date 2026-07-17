# Python 基础恢复与项目环境

Python 不需要重新从零学习。重点恢复语法、类型、测试和工程组织，并立即用于 Agent。

### 5.1 第一批 Python 特性

| 特性 | RepoFix 中的用途 | 对应 Go 概念 |
| --- | --- | --- |
| 类型标注 | 明确工具参数和返回值 | 静态类型声明 |
| `dataclass` | AgentState、StepRecord | `struct` |
| `StrEnum` | RunStatus、StepStatus | 字符串常量类型 |
| `Protocol` | ModelClient、Sandbox | `interface` |
| `pathlib.Path` | 安全文件访问 | `filepath` |
| 异常 | 工具执行和模型错误 | `error`，但传播方式不同 |
| `pytest` | Agent、工具和评测测试 | `testing` |

暂时不学习元类、描述符、复杂装饰器、类型体操和多进程。

### 5.2 环境初始化

在 Codespaces 中：

```bash
cd services/agent
python -m venv .venv
source .venv/bin/activate
pip install openai pytest ruff
```

在 Codespaces Secrets 中设置：

```text
OPENAI_API_KEY
OPENAI_MODEL
```

不要向 Git 提交 `.env`、API Key 或模型请求日志中的敏感信息。

### 5.3 第一次模型调用

```python
import os

from openai import OpenAI


def main() -> None:
    client = OpenAI()

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
        input="用一句话解释什么是 AI Agent。",
    )

    print(response.output_text)


if __name__ == "__main__":
    main()
```

练习要求：

1. 将模型名改为环境变量配置。
2. 捕获认证错误和网络错误。
3. 打印请求耗时，但不打印 API Key。
4. 为模型客户端定义接口，准备后续 Fake 实现。

参考：[OpenAI API Quickstart](https://developers.openai.com/api/docs/quickstart)
