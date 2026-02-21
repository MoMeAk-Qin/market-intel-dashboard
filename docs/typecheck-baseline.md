# Pyright 告警基线说明（阶段99）

## 1. 目的

阶段99要求在不扩大范围的前提下收敛指定文件的类型告警，并把类型检查纳入 CI 阻断。  
当前基线文件为：

- `/Users/qinzheng/Code/market-intel-dashboard/tools/typecheck/pyright-baseline.json`

其作用是：

1. 记录阶段99范围外的既有告警。
2. 阻断任何“新增”告警。
3. 允许后续阶段逐步清理既有告警。

## 2. 使用方式

统一执行流程：

1. 运行 `pyright --outputjson` 生成报告。
2. 使用基线脚本比对新增项。

对应命令（仓库根目录）：

```bash
PYTHON_BIN=$(uv run --project apps/api python -c "import sys; print(sys.executable)")
uvx pyright --pythonpath "$PYTHON_BIN" apps/api/app apps/api/tests --outputjson > pyright.json || true
uv run --project apps/api python tools/typecheck/check_pyright_baseline.py --input pyright.json --baseline tools/typecheck/pyright-baseline.json
```

## 3. 存量告警归属（阶段99范围外）

| 文件 | 规则 | 数量 | 计划归属 |
|---|---|---:|---|
| `apps/api/app/services/http_client.py` | `reportAttributeAccessIssue` | 7 | 后续类型治理任务 |
| `apps/api/app/sources/hkma.py` | `reportArgumentType` | 1 | HKMA 数据链路后续任务 |
| `apps/api/app/sources/hkma_discovery.py` | `reportArgumentType` | 1 | HKMA 发现链路后续任务 |
| `apps/api/tests/test_asset_profile_endpoint.py` | `reportArgumentType` | 2 | 资产接口测试后续任务 |
| `apps/api/tests/test_qa_endpoint.py` | `reportArgumentType` | 1 | QA 测试后续任务 |

总计：12 条。

## 4. 维护规则

1. 新增告警必须先修复，不允许直接并入基线。
2. 既有告警修复后，应同步更新基线文件（删除对应条目）。
3. 每次调整基线，都必须在提交说明中写明“原因 + 对应任务编号”。
