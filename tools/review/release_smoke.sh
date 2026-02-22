#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:4000}"
WEB_BASE_URL="${WEB_BASE_URL:-http://127.0.0.1:3000}"

log() {
  printf '[review:release:smoke] %s\n' "$*"
}

get_json() {
  local path=$1
  curl -fsS --max-time 120 "${API_BASE_URL}${path}"
}

post_json() {
  local path=$1
  local payload=$2
  curl -fsS --max-time 120 \
    -X POST \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "${API_BASE_URL}${path}"
}

check_page() {
  local path=$1
  curl -fsS --max-time 60 "${WEB_BASE_URL}${path}" >/dev/null
}

log "API 冒烟检查"
get_json "/health" >/dev/null
post_json "/admin/refresh" '{}' >/dev/null
get_json "/events?origin=live&page=1&pageSize=5" >/dev/null
get_json "/events?origin=seed&page=1&pageSize=5" >/dev/null
get_json "/dashboard/summary" >/dev/null
get_json "/assets/NVDA/profile?range=1M" >/dev/null
post_json "/qa" '{"question":"今日市场有哪些关键风险？"}' >/dev/null

analysis_task_resp=$(post_json "/analysis/tasks" '{"question":"Summarize key market risk factors"}')
analysis_task_id=$(node -e "const d=JSON.parse(process.argv[1]); if(!d.task_id){process.stderr.write('missing task_id'); process.exit(1)}; process.stdout.write(d.task_id);" "$analysis_task_resp")
get_json "/analysis/tasks/${analysis_task_id}" >/dev/null
get_json "/analysis/tasks?limit=5" >/dev/null

log "前端页面可达性检查"
check_page "/"
check_page "/events"
check_page "/asset/NVDA"
check_page "/research"

log "数据来源标识专项检查（API）"
events_payload=$(get_json "/events?origin=all&page=1&pageSize=5")
node -e '
const payload = JSON.parse(process.argv[1]);
if (!Array.isArray(payload.items)) {
  throw new Error("events.items is not array");
}
if (payload.items.length > 0) {
  const item = payload.items[0];
  const origins = new Set(["live", "seed"]);
  const sourceTypes = new Set(["news", "filing", "earnings", "research", "macro_data"]);
  if (!origins.has(item.data_origin)) {
    throw new Error(`invalid data_origin: ${item.data_origin}`);
  }
  if (!sourceTypes.has(item.source_type)) {
    throw new Error(`invalid source_type: ${item.source_type}`);
  }
}
' "$events_payload"

log "数据来源标识专项检查（前端可见性）"
if ! grep -q "data_origin" apps/web/src/app/events/page.tsx; then
  log "events 页面未检测到 data_origin 字段展示"
  exit 1
fi
if ! grep -Eq "实时行情|回退行情|is_fallback" 'apps/web/src/app/asset/[id]/page.tsx'; then
  log "asset 页面未检测到来源可见性标识"
  exit 1
fi

log "发布前全链路冒烟检查通过"
