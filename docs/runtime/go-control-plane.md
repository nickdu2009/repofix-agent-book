# Go 控制平面

Python Agent 能独立完成最小闭环以后，再加入 Go。

### 9.1 核心实体

```text
Task
  用户目标和仓库信息

Run
  Task 的一次实际执行

Step
  一次模型响应或工具调用

Artifact
  Diff、测试报告、日志

Evaluation
  一个评测案例的运行结果
```

### 9.2 Run 状态机

```text
Pending
  → Provisioning
  → Running
  → Testing
  → Succeeded

任意未完成状态
  → Failed
  → Cancelled
  → TimedOut
```

必须明确：

- 哪些转移合法。
- 谁能触发转移。
- 转移是否需要事务。
- 服务重启后如何恢复。
- 重复请求如何保证幂等。

### 9.3 API

```text
POST /tasks
POST /tasks/{task_id}/runs
GET  /runs/{run_id}
GET  /runs/{run_id}/events
POST /runs/{run_id}/cancel
GET  /runs/{run_id}/artifacts
```

### 9.4 Go 与 Python 的边界

推荐职责：

```text
Go：
  何时开始和结束
  Run 当前状态
  沙箱生命周期
  超时、重试、取消
  事件与持久化

Python：
  下一步做什么
  给模型什么上下文
  调用哪个工具
  如何根据工具结果继续
```

Go 不解析 Prompt，Python 不拥有最终 Run 状态。
