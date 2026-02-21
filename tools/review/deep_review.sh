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
  printf '[review:deep] 未找到 pnpm，请先安装 pnpm 或初始化 .corepack/pnpm\\n' >&2
  exit 2
fi

stage=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage=*)
      stage="${1#*=}"
      shift
      ;;
    --stage)
      stage="${2:-}"
      shift 2
      ;;
    *)
      printf '[review:deep] 未知参数: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$stage" ]]; then
  printf '[review:deep] 缺少 --stage 参数，例如: pnpm review:deep -- --stage=8\n' >&2
  exit 2
fi

log() {
  printf '[review:deep] %s\n' "$*"
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

log "开始阶段 ${stage} 深度审查"
run_cmd uv run --project apps/api pytest -q
run_pyright_with_baseline
run_cmd "$PNPM_BIN" lint -- --max-warnings=0
run_cmd "$PNPM_BIN" -C apps/web build

report_date=$(date +%F)
sha=$(git rev-parse --short HEAD)
report_path="docs/reviews/deep/${report_date}-stage-${stage}.md"
if [[ -f "$report_path" ]]; then
  report_path="docs/reviews/deep/${report_date}-stage-${stage}-${sha}.md"
fi

end_ts=$(date +%s)
duration=$((end_ts - start_ts))

cat > "$report_path" <<REPORT
# 阶段 ${stage} 深度审查报告

- 日期: ${report_date}
- 提交: ${sha}
- 耗时: ${duration}s
- 结果: PASS（自动检查通过）

## 自动检查结果

- [x] 全量后端测试：\`uv run --project apps/api pytest -q\`
- [x] 后端静态检查：\`uvx pyright --pythonpath <api-python> apps/api/app apps/api/tests --outputjson\` + 基线校验
- [x] 前端检查：\`pnpm lint -- --max-warnings=0\`
- [x] 前端构建：\`pnpm -C apps/web build\`

## 覆盖缺口核对（人工填写）

- [ ] \`/events\`（origin 过滤）
- [ ] \`/assets/{id}/profile\`
- [ ] \`/qa\`
- [ ] \`/analysis/tasks\`
- [ ] \`/news/today\`
- [ ] \`/daily/summary\`
- [ ] \`source_type/data_origin\` 前后端可见性

## 发现问题（人工填写）

- 无 / 待补充

## 覆盖缺口与后续任务（人工填写）

- 若有缺口，请回写 \`docs/todo.md\` 对应任务编号

## 结论

- [ ] 可进入下一阶段
- [ ] 需修复后复审
REPORT

log "深度审查通过，报告已生成: ${report_path}"
