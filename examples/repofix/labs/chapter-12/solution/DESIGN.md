<!-- LAB:chapter-12 STATUS:complete -->

# 事件与恢复设计

- 成功：`sandbox.created → run.started → sandbox.deleted → run.succeeded`。
- 业务失败：`sandbox.created → run.started → sandbox.deleted → run.failed`。
- 清理失败：`sandbox.created → run.started → sandbox.cleanup_failed → run.failed`。
- 取消在提交前被观察时，清理完成后写入 `run.cancelled`。

状态转换与事件放在同一数据库事务；每个 Run 使用单调序号。SSE 客户端携带最后序号重放。非终态且租约过期的 Run 进入恢复扫描，终态绝不早于清理结果。

本参考答案是持久化与重放协议，不宣称 PostgreSQL Repository 或 SSE 服务已经实现。
