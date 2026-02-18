# HEARTBEAT.md

## Heartbeat 自动任务（启用）

当收到 heartbeat poll 时，按顺序执行：

1. 执行：`bash scripts/heartbeat_memory_sync.sh`
2. **（如果已授权）执行：`bash scripts/sync-google-fit.sh` 同步健康数据**
3. 读取并遵循：`AGENT_ROLES.md` + `AGENT_WORKFLOWS.md`
3. 若有待办任务，按角色处理并将结果写入：
   - `memory/YYYY-MM-DD.md`（当日）
   - `MEMORY.md`（长期）
   - `memory/shared/*.md`（四个共享记忆）
4. 如果本次没有待办或无新增信息，回复：`HEARTBEAT_OK`

## 共享记忆说明（QMD）

QMD 同步配置：`.openclaw/qmd-memory-sync.yaml`

共享记忆文件（所有 agent 可读写）：
- `memory/shared/SHARED_CONSTRAINTS.md`
- `memory/shared/SHARED_DECISIONS.md`
- `memory/shared/SHARED_RISKS.md`
- `memory/shared/SHARED_TODOS.md`
- `memory/shared/health-shared.md`（健康数据，由 health agent 维护）

## Git 同步策略

- heartbeat 自动执行 git add + commit（有变化才提交）
- heartbeat 默认自动 push 到远程（可设置 `AUTO_PUSH=0` 关闭）
