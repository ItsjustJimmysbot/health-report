# AGENT_WORKFLOWS.md

这份文件定义 8 个 agent 的“自动执行工作流（Heartbeat 驱动）”与统一记忆读写规范。

## 0. 全局规则（所有 agent）

每次执行都遵循：
1. 读取记忆（shared + long-term + daily）
2. 执行本职任务
3. 写回记忆（结构化条目）
4. 更新状态（todo/doing/blocked/done）
5. 由 heartbeat 触发 Git 同步

统一输出格式：
- 结论
- 依据
- 风险
- 下一步

---

## 1) front
- 输入：前端需求、设计稿、接口契约
- 流程：读 shared + MEMORY -> 实现/联调 -> 写 UI 决策与坑点 -> 标记状态
- 记忆写入：`memory/YYYY-MM-DD.md`（UI 决策/联调问题）

## 2) backend
- 输入：接口/业务需求/数据约束
- 流程：读 shared + MEMORY -> API/数据实现 -> 写变更影响和回滚点 -> 标记状态
- 记忆写入：`memory/YYYY-MM-DD.md`（接口字段/性能/风险）

## 3) arch-dev
- 输入：全局目标与各 agent 状态
- 流程：读全部状态 -> 拆解/调度 -> 生成任务分发 -> 写架构决策
- 记忆写入：`MEMORY.md`（长期决策）、`memory/YYYY-MM-DD.md`（当日调度）

## 4) crypto-research
- 输入：研究主题/标的
- 流程：读 shared 研究上下文 -> 调研 -> 交叉验证 -> 输出结论分级
- 记忆写入：`memory/shared/SHARED_DECISIONS.md`、`memory/shared/SHARED_RISKS.md` + `memory/YYYY-MM-DD.md`

## 5) health
- 输入：健康目标、作息/活动数据
- 流程：读 shared 健康上下文 -> 给计划 -> 标注风险与提醒级别
- 记忆写入：`memory/shared/SHARED_CONSTRAINTS.md`、`memory/shared/SHARED_TODOS.md` + `memory/YYYY-MM-DD.md`

## 6) work-ops
- 输入：PDF/Docx/XLSX/文本任务
- 流程：读模板偏好 -> 处理文档 -> 产出结果与可复现步骤
- 记忆写入：`memory/shared/SHARED_DECISIONS.md`、`memory/shared/SHARED_TODOS.md` + `memory/YYYY-MM-DD.md`

## 7) media-ai
- 输入：视频/图片/语音任务
- 流程：读参数偏好 -> 处理/生成 -> 记录参数效果与素材链接
- 记忆写入：`memory/shared/SHARED_DECISIONS.md`、`memory/shared/SHARED_RISKS.md` + `memory/YYYY-MM-DD.md`

## 8) general-knowledge
- 输入：泛知识问题
- 流程：读长期偏好 -> 解释/对比 -> 输出可验证结论
- 记忆写入：仅写长期有复用价值结论到 `MEMORY.md` 或当天记忆

---

## Heartbeat 自动化职责

heartbeat 到来时执行：
1. 读取 `HEARTBEAT.md`
2. 执行 `scripts/heartbeat_memory_sync.sh`
3. 若有 agent 队列任务，按 `AGENT_ROLES.md` + 本文件流程处理
4. 自动提交 memory 变更到 git（可选自动 push）

## Shared 记忆写入规范（防冲突）

为减少同一行冲突，所有 agent 写 `memory/shared/*.md` 时必须：
- 只做**追加**，不要改写/重排旧条目
- 每条使用统一结构（建议追加到文件末尾）：

```md
## [YYYY-MM-DD HH:mm] <agent-id>
- 结论：
- 依据：
- 风险：
- 下一步：
- 状态：todo|doing|blocked|done
```

- 若需修正旧结论，不覆盖原文，追加“修正条目”并引用旧时间戳
