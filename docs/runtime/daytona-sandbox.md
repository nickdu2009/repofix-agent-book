# Daytona 云沙箱

Daytona 是 RepoFix 执行不可信仓库代码的边界。接入本章之前，真实模型只能观察工具协议，不能在 Codespaces 中执行它生成或修改后的代码。

## 本章契约

- **前置**：Fake Agent Loop、Python HTTP 服务、Go 控制平面和 Fake Sandbox 合约全部通过；已接受运行时所有权 ADR。
- **产物**：Go `SandboxManager` 与 `ToolGateway`，以及 Fake Daytona 测试替身。
- **安全边界**：只有 Go 控制平面持有 `DAYTONA_API_KEY`。
- **验收**：成功、失败、超时和取消四条路径都会删除 Sandbox。

!!! warning "设计蓝图，尚未发布云端 Adapter"
    当前仓库只有 Fake Sandbox 合约和下面的锁版实现指南，没有 Daytona SDK 依赖、`sandbox-smoke` target 或云端测试。完成真实 Adapter、锁定 `go.mod` 并通过手动 Smoke 后，才会发布本章 solution tag。

Daytona Go SDK 要求 Go 1.25 或更高版本；本书统一使用 Go 1.26.x。正式接入时把 SDK 精确版本写入 `go.mod`，不要在教材分支上长期使用未锁定的 `@latest`：

```bash
go get github.com/daytona/clients/sdk-go@<本章 checkpoint 锁定版本>
```

尖括号是发布流程要替换的版本占位符，不是可直接复制的命令；先查看伴随代码 `go.mod`。当前未发布 Daytona Adapter checkpoint 时，不要自行猜版本。

## 最小生命周期

下面代码展示 SDK 边界；正式项目应把它封装在 `internal/sandbox/daytona.go`，不要让 HTTP Handler 直接依赖 SDK：

```go
package sandbox

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/daytona/clients/sdk-go/pkg/daytona"
	"github.com/daytona/clients/sdk-go/pkg/options"
)

func Smoke(ctx context.Context) (err error) {
	client, err := daytona.NewClient()
	if err != nil {
		return fmt.Errorf("create daytona client: %w", err)
	}
	defer client.Close(context.WithoutCancel(ctx))

	box, err := client.Create(ctx, nil)
	if err != nil {
		return fmt.Errorf("create sandbox: %w", err)
	}
	defer func() {
		cleanupCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if deleteErr := box.Delete(cleanupCtx); deleteErr != nil {
			err = errors.Join(err, fmt.Errorf("request sandbox deletion: %w", deleteErr))
		}
	}()

	result, err := box.Process.ExecuteCommand(
		ctx,
		`python -c 'print("sandbox ready")'`,
		options.WithExecuteTimeout(120*time.Second),
	)
	if err != nil {
		return fmt.Errorf("execute sandbox smoke: %w", err)
	}
	if result.ExitCode != 0 {
		return fmt.Errorf("sandbox smoke failed: %s", result.Result)
	}
	return nil
}
```

这个 Smoke 只验证创建、执行和发出删除请求；它不假装仓库已经出现在空 Sandbox 中。真正的 Adapter 合约还必须按固定 commit clone 或上传 Fixture、创建 `workspace`、准备依赖，并由后台清理器确认异步删除最终完成。删除失败必须与原业务错误一起保留，不能被吞掉。SDK 方法名应以项目锁定版本为准。升级 Daytona 时先运行手动 Smoke Test，再更新书中代码。参考：[Go SDK](https://www.daytona.io/docs/en/go-sdk/) 和 [Process Execution](https://www.daytona.io/docs/en/process-code-execution/)。

## Tool Gateway 不接受任意命令

模型不直接提交 shell 字符串，只选择稳定的语义测试目标：

```json
{
  "tool": "run_tests",
  "arguments": {"target": "unit"}
}
```

Python 到 Go Tool Gateway 的 Wire DTO 仍然是 `target=unit`。Go 根据已验证的仓库配置，在内部把这个目标映射为可信 `command_id`；模型看不到也不能覆盖具体命令、环境变量或工作目录。例如：

```text
python.pytest  → python -m pytest -q
go.test        → go test ./...
web.test       → npm test -- --run
git.diff       → git diff --no-ext-diff
```

禁止模型传入环境变量、工作目录、重定向或复合 shell 表达式。

## 创建策略

每个 Run：

1. 创建独立、短生命周期 Sandbox。
2. 固定仓库 commit SHA，不跟随移动分支。
3. 默认不注入宿主环境变量和 GitHub 主 Token。
4. 默认关闭出站网络；安装依赖时只开放所需包源。
5. 设置 CPU、内存、磁盘、命令超时和整体 Run deadline。
6. 配置 auto-delete 作为兜底，但仍在 `defer` 中显式删除。
7. 数据库保存 `sandbox_id` 和清理状态，不保存凭据。

## 测试层次

| 测试 | 默认执行 | 内容 |
| --- | --- | --- |
| `FakeSandboxManager` 单测 | 是 | 创建、执行、删除的调用顺序 |
| Adapter 合约测试 | PR | 超时、取消、输出截断、删除失败 |
| Daytona Smoke | 手动 | 创建真实 Sandbox、运行固定命令、删除 |
| Live Agent Eval | 手动 | 真实模型修改 fixture 并在 Sandbox 测试 |

不要在普通 PR 中使用真实模型或无条件创建付费 Sandbox。

## 故障排查

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| `DAYTONA_API_KEY` 缺失 | Secret 未配置在 Go 服务 | 只在控制平面设置变量，不注入 Sandbox |
| 命令超时但 Run 仍运行 | 只设置了 SDK 请求超时 | 同时设置命令 timeout 和 Run deadline |
| 删除失败产生孤儿环境 | 取消后的 Context 已失效 | 使用独立、短时 cleanup Context，并运行后台清理器 |
| 本地测试意外联网 | Fake 与真实 Adapter 混用 | 默认构建只注册 Fake；真实测试要求显式环境开关 |

## 练习与验收

1. 为 `FakeSandboxManager` 注入一次删除失败。
2. 证明取消测试命令后仍调用删除。
3. 列出 Sandbox 中绝不能出现的五类凭据。

完成 Adapter 后应增加以下目标命令：

```bash
make sandbox-contract-test
RUN_DAYTONA_SMOKE=1 make sandbox-smoke
```

这两个 target 当前尚不存在，不能用空命令伪造；第二条未来也必须由开发者显式运行。
