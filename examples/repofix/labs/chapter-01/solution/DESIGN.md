<!-- LAB:chapter-01 STATUS:complete -->

# 系统所有权决策

| 状态或资源 | 唯一所有者 | 失败时由谁收敛 |
| --- | --- | --- |
| Run 终态 | Go Control Plane | Go 持久化失败、取消或超时 |
| Agent Loop | Python Agent | Go 根据服务结果决定是否继续 |
| Sandbox 生命周期 | Go Control Plane | Go 使用独立清理期限删除 |
| 页面派生状态 | TypeScript Web | REST 快照覆盖过期的本地状态 |

模型只能提交候选结果；Go 必须在当前 revision 上独立验证测试，才能写入成功终态。
