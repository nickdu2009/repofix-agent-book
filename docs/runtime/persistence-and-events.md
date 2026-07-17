# 持久化、恢复与事件

### 11.1 最小数据表

```text
tasks
runs
steps
artifacts
evaluations
```

Step 至少保存：

```text
step_number
type
tool_name
arguments
result_summary
started_at
completed_at
duration_ms
status
```

敏感参数和完整文件内容不应默认写入数据库。

### 11.2 恢复策略

服务重启后，对未完成 Run 执行：

1. 查询数据库状态。
2. 查询沙箱是否仍然存在。
3. 判断当前 Step 是否可重试。
4. 可恢复则继续，不可恢复则明确标记失败。
5. 记录恢复原因和决策。

### 11.3 SSE 事件

```text
run.started
sandbox.created
step.started
tool.called
tool.completed
tests.completed
patch.created
run.succeeded
run.failed
```

事件必须带有 `run_id`、序号和时间，前端才能处理重连和去重。
