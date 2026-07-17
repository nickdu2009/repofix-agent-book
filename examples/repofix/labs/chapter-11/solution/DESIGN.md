<!-- LAB:chapter-11 STATUS:complete -->

# Sandbox 接入计划

| 阶段 | 输入 | 超时 | 失败后的清理 |
| --- | --- | --- | --- |
| Create | Run ID 与资源上限 | 30 秒 | Provider 自清理部分创建 |
| Clone | 只读临时仓库凭据 | 60 秒 | 删除整个 Sandbox |
| Execute | 受信命令 ID | 每工具独立期限 | 终止进程后删除 Sandbox |
| Delete | 持久化 Sandbox ID | 独立 30 秒 | 记录失败并交给孤儿清理器 |

不得注入 GitHub 主账号令牌或模型 API Key。后台任务按已过期 Run 与未删除 Sandbox ID 的差集检测孤儿资源。

本参考答案只完成可审查的设计，不代表 Daytona Adapter 或云端 Smoke 已落地。
