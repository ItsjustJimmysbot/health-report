#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p memory/shared .openclaw/cache

REPO_URL="${MEM_SYNC_REPO:-https://github.com/ItsjustJimmysbot/OpenClawMemoryBackup.git}"
CACHE_DIR=".openclaw/cache/OpenClawMemoryBackup"
STATE_FILE=".openclaw/heartbeat-memory-sync.state"

# 防止 heartbeat 过于频繁导致噪声：默认 30 分钟最小间隔
MIN_INTERVAL_SEC="${MEM_SYNC_MIN_INTERVAL_SEC:-10800}"
NOW="$(date +%s)"
LAST=0
if [[ -f "$STATE_FILE" ]]; then
  LAST="$(cat "$STATE_FILE" 2>/dev/null || echo 0)"
fi
if [[ $((NOW - LAST)) -lt $MIN_INTERVAL_SEC ]]; then
  exit 0
fi

echo "$NOW" > "$STATE_FILE"

# 拉取共享记忆仓库（失败不终止 heartbeat 主流程）
if [[ ! -d "$CACHE_DIR/.git" ]]; then
  git clone --depth 1 "$REPO_URL" "$CACHE_DIR" || true
else
  (cd "$CACHE_DIR" && git pull --ff-only) || true
fi

# 同步 shared memory（如果仓库可访问）
if [[ -d "$CACHE_DIR/memory/shared" ]]; then
  mkdir -p memory/shared
  cp -f "$CACHE_DIR"/memory/shared/*.md memory/shared/ 2>/dev/null || true
fi

# 确保本地 4 个共享文件存在（若远程没有也可正常运行）
for f in SHARED_CONSTRAINTS.md SHARED_DECISIONS.md SHARED_RISKS.md SHARED_TODOS.md; do
  if [[ ! -f "memory/shared/$f" ]]; then
    cat > "memory/shared/$f" <<EOF
# ${f%.md}

> 由 heartbeat 自动维护的共享记忆文件（跨频道共享）。

EOF
  fi
done

# 确保当天 memory 存在
TODAY="$(date +%F)"
mkdir -p memory
if [[ ! -f "memory/$TODAY.md" ]]; then
  cat > "memory/$TODAY.md" <<EOF
# $TODAY

## Heartbeat

EOF
fi

# 自动提交（仅当有变化）
git add memory MEMORY.md AGENT_ROLES.md AGENT_WORKFLOWS.md .openclaw/qmd-memory-sync.yaml 2>/dev/null || true
if ! git diff --cached --quiet; then
  git commit -m "chore(memory): heartbeat sync $(date '+%F %T')" || true
fi

# 自动推送（默认开启，可通过 AUTO_PUSH=0 关闭）
if [[ "${AUTO_PUSH:-1}" == "1" ]]; then
  git push || true
fi
