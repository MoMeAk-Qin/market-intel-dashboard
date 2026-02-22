#!/usr/bin/env bash
set -Eeuo pipefail

start_ts=$(date +%s)
repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if command -v pnpm >/dev/null 2>&1; then
  PNPM_BIN="pnpm"
elif [[ -x "$repo_root/.corepack/pnpm" ]]; then
  PNPM_BIN="$repo_root/.corepack/pnpm"
else
  printf '[review:release] 未找到 pnpm，请先安装 pnpm 或初始化 .corepack/pnpm\\n' >&2
  exit 2
fi

version=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version=*)
      version="${1#*=}"
      shift
      ;;
    --version)
      version="${2:-}"
      shift 2
      ;;
    *)
      printf '[review:release] 未知参数: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$version" ]]; then
  version=$(git describe --tags --always 2>/dev/null || git rev-parse --short HEAD)
fi

version_slug=$(printf '%s' "$version" | tr '/ :@' '----')
report_date=$(date +%F)
sha=$(git rev-parse --short HEAD)
report_path="docs/reviews/release/${report_date}-${version_slug}.md"
if [[ -f "$report_path" ]]; then
  report_path="docs/reviews/release/${report_date}-${version_slug}-${sha}.md"
fi

api_pid=""
web_pid=""
api_log=$(mktemp -t review-api.XXXX.log)
web_log=$(mktemp -t review-web.XXXX.log)

log() {
  printf '[review:release] %s\n' "$*"
}

run_cmd() {
  log "RUN: $*"
  "$@"
}

cleanup() {
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$web_pid" ]]; then
    kill "$web_pid" >/dev/null 2>&1 || true
  fi
}

on_error() {
  local lineno=$1
  log "发布审查失败（line ${lineno}）"
  if [[ -f "$api_log" ]]; then
    log "API 日志（最后50行）:"
    tail -n 50 "$api_log" || true
  fi
  if [[ -f "$web_log" ]]; then
    log "Web 日志（最后50行）:"
    tail -n 50 "$web_log" || true
  fi
}

trap cleanup EXIT
trap 'on_error $LINENO' ERR

wait_for_url() {
  local url=$1
  local name=$2
  local attempt=0
  while (( attempt < 60 )); do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      log "${name} 已就绪: ${url}"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  log "等待 ${name} 超时: ${url}"
  return 1
}

log "开始发布前全链路审查，版本: ${version}"
run_cmd "$PNPM_BIN" -C apps/web build

log "启动 API 服务"
uv run --project apps/api uvicorn main:app --host 127.0.0.1 --port 4000 >"$api_log" 2>&1 &
api_pid=$!

log "启动 Web 服务"
"$PNPM_BIN" -C apps/web start >"$web_log" 2>&1 &
web_pid=$!

wait_for_url "http://127.0.0.1:4000/health" "API"
wait_for_url "http://127.0.0.1:3000" "Web"

log "执行全链路冒烟脚本"
API_BASE_URL="http://127.0.0.1:4000" WEB_BASE_URL="http://127.0.0.1:3000" \
  run_cmd bash tools/review/release_smoke.sh

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

cat > "$report_path" <<REPORT
# 发布前全链路审查报告

- 日期: ${report_date}
- 版本: ${version}
- 提交: ${sha}
- 耗时: ${duration}s
- 结果: PASS（全链路检查通过）

## 自动检查结果

- [x] 启动 API/Web 本地服务
- [x] API 冒烟（health/refresh/events/summary/asset/qa/analysis tasks）
- [x] 前端页面可达性（/, /events, /asset/NVDA, /research）
- [x] 数据来源标识专项（API 字段 + 前端可见性）

## 风险与说明

- 若出现外部数据源波动导致失败，需标注为“环境/上游依赖问题”并复跑。
- 若来源字段检查失败，阻断发布并回写 `docs/todo.md`。

## 结论

- [x] 允许发布
REPORT

log "发布审查通过，报告已生成: ${report_path}"
