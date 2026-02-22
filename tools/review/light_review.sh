#!/usr/bin/env bash
set -euo pipefail

start_ts=$(date +%s)
repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if command -v pnpm >/dev/null 2>&1; then
  PNPM_BIN="pnpm"
elif [[ -x "$repo_root/.corepack/pnpm" ]]; then
  PNPM_BIN="$repo_root/.corepack/pnpm"
else
  printf '[review:light] 未找到 pnpm，请先安装 pnpm 或初始化 .corepack/pnpm\\n' >&2
  exit 2
fi

log() {
  printf '[review:light] %s\n' "$*"
}

run_cmd() {
  log "RUN: $*"
  "$@"
}

run_pyright_with_baseline() {
  local python_bin
  python_bin=$(uv run --project apps/api python -c "import sys; print(sys.executable)")
  local pyright_json
  pyright_json=$(mktemp)

  log "RUN: uvx pyright --pythonpath ${python_bin} apps/api/app apps/api/tests --outputjson > ${pyright_json}"
  if ! uvx pyright --pythonpath "${python_bin}" apps/api/app apps/api/tests --outputjson >"${pyright_json}"; then
    log "pyright 返回非零，继续执行基线对比以判断是否存在新增告警。"
  fi

  run_cmd uv run --project apps/api python tools/typecheck/check_pyright_baseline.py \
    --input "${pyright_json}" \
    --baseline tools/typecheck/pyright-baseline.json
  rm -f "${pyright_json}"
}

resolve_diff_range() {
  if [[ "${1:-}" == "--range" && -n "${2:-}" ]]; then
    printf '%s\n' "$2"
    return
  fi

  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    local base
    base=$(git merge-base origin/main HEAD)
    printf '%s..HEAD\n' "$base"
    return
  fi

  if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    printf 'HEAD~1..HEAD\n'
    return
  fi

  printf 'HEAD\n'
}

has_changed_regex() {
  local pattern=$1
  printf '%s\n' "$changed_files" | grep -Eq "$pattern"
}

diff_range=$(resolve_diff_range "${1:-}" "${2:-}")
changed_files=$(git diff --name-only "$diff_range" || true)

if [[ -z "$changed_files" ]]; then
  changed_files=$(git diff --name-only --cached || true)
fi

if [[ -z "$changed_files" ]]; then
  log "未检测到变更文件，将仅执行固定检查。"
else
  log "Diff 范围: $diff_range"
  log "变更文件:\n$changed_files"
fi

log "执行固定检查（每次都跑）"
run_cmd uv run --project apps/api pytest -q apps/api/tests/test_health_endpoint.py apps/api/tests/test_events_endpoint.py
run_cmd "$PNPM_BIN" -C apps/web test:contract

if has_changed_regex '^(apps/api/app/|apps/api/tests/)'; then
  log "检测到 API/后端测试改动，执行 pyright（基线门禁）。"
  run_pyright_with_baseline
fi

if has_changed_regex '^(apps/web/src/|packages/shared/)'; then
  log "检测到前端/共享类型改动，执行 eslint。"
  run_cmd "$PNPM_BIN" exec eslint . --ext .ts,.tsx --max-warnings=0
fi

if has_changed_regex '^(apps/api/app/api\.py|apps/api/app/services/analysis\.py|apps/api/app/services/task_queue\.py|apps/api/tests/test_qa_endpoint\.py|apps/api/tests/test_analysis_service\.py|apps/api/tests/test_analysis_tasks_endpoint\.py|apps/web/src/lib/api\.ts)'; then
  log "检测到 QA/Analysis/Task 相关改动，执行定向测试。"
  run_cmd uv run --project apps/api pytest -q \
    apps/api/tests/test_qa_endpoint.py \
    apps/api/tests/test_analysis_service.py \
    apps/api/tests/test_analysis_tasks_endpoint.py
fi

if has_changed_regex '^(apps/api/app/api\.py|apps/api/app/sources/quotes\.py|apps/api/app/services/seed\.py|apps/web/src/app/asset/\[id\]/page\.tsx|apps/api/tests/test_asset_quote_endpoint\.py|apps/api/tests/test_asset_profile_endpoint\.py|apps/api/tests/test_quotes_source\.py)'; then
  log "检测到 quotes/asset/profile 相关改动，执行定向测试。"
  run_cmd uv run --project apps/api pytest -q \
    apps/api/tests/test_asset_quote_endpoint.py \
    apps/api/tests/test_asset_profile_endpoint.py \
    apps/api/tests/test_quotes_source.py
fi

end_ts=$(date +%s)
duration=$((end_ts - start_ts))
log "轻量审查通过，耗时 ${duration}s。"
