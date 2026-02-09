# Market Intel Dashboard 项目评估（可执行版）

> 更新日期：2026-02-09  
> 适用场景：个人 PC / 1-2GB 轻量节点服务器

## 1. 当前状态（基于代码核对）

| 模块 | 状态 | 说明 |
|---|---|---|
| Dashboard | ✅ 可用 | KPI / Key Asset / Timeline 已接通 |
| Event Hub | ✅ 可用 | 过滤、排序、分页、详情、`origin` 筛选已支持 |
| Search & Q&A | ✅ 可用 | `/qa` 已升级为“检索候选 + Qwen + 降级” |
| Asset Detail | ⚠️ 演示态 | K 线为模拟序列 |
| Research | ⚠️ 演示态 | 研究卡片为硬编码示例 |
| 今日新闻页面 | ❌ 未上线 | 仍在 todo 阶段 2 |

## 2. 关键结论（修订后）

### 2.1 已确认并已落地

1. Seed/Live 数据区分已实现  
- `Event` 已有 `data_origin: "live" | "seed"` 强类型字段。  
- `ingestion` 已支持 `ENABLE_SEED_DATA` + `SEED_ONLY_WHEN_NO_LIVE`。  
- 同标题去重时 `live` 优先于 `seed`。  
- `/events` 已支持 `origin=live|seed|all`。  

2. 前端已可识别来源  
- Event Hub 有 `Origin` 列和来源过滤器。  

### 2.2 需要纠正的旧判断

1. “Chroma 首次启动会下载 embedding 模型”不准确  
- 当前是调用 DashScope 远程 embedding 接口，不是本地下载模型。  

2. “默认应显示 seed”不建议  
- 生产口径应优先真实数据（`live`），seed 仅作为兜底或显式查看。  

3. 部署命令需修正  
- API 入口应为 `main:app`（不是 `app.main:app`）。  
- `--name` 是 PM2 参数，不是 uvicorn/next 参数。

## 3. 可执行优化清单

### 3.1 立即执行（1-2 小时）

1. 健康检查增强（推荐）  
- 目标：让运维一眼看出“有无数据、最近刷新时间、向量能力状态”。  
- 建议返回字段：`ok`、`store_events`、`updated_at`、`vector_store_enabled`、`vector_store_ready`。

2. 启动完成日志提示（推荐）  
- 目标：本地/服务器启动后无需手动探测端口。  
- 建议日志：`Market Intel API ready on http://0.0.0.0:4000`。

3. Seed 可视化警示增强（推荐）  
- 目标：避免用户把 seed 当真实数据。  
- 建议：`Seed` Badge 使用更高对比色（如橙/红）并附 tooltip“模拟数据”。

4. 演示数据显式标注（推荐）  
- 在 Research 与 Asset Detail 页面顶部显示“演示数据（非实时）”。

### 3.2 短期执行（1-2 天）

1. 日志轮转  
- 方案 A：`RotatingFileHandler`（代码内解决）。  
- 方案 B：`logrotate`（系统层解决）。

2. 部署模板  
- 增加 `Dockerfile`、`docker-compose.yml`。  
- 增加 `ecosystem.config.js`（PM2）与 `systemd` 示例。

3. 资源受限配置文档  
- 提供“轻量节点建议配置”模板。  
- 只列当前可生效变量；额外变量注明“需代码支持”。

## 4. 轻量节点推荐配置（当前可直接生效）

```bash
# apps/api/.env
ENABLE_LIVE_SOURCES=true
ENABLE_SEED_DATA=true
SEED_ONLY_WHEN_NO_LIVE=true
ENABLE_VECTOR_STORE=false

# 按需关闭数据源，减轻抓取压力
ENABLE_HKEX=false
ENABLE_HKMA=false
```

说明：
- `ENABLE_VECTOR_STORE=false` 可显著降低内存压力。  
- `SEED_ONLY_WHEN_NO_LIVE=true` 可避免真实与模拟混杂。

## 5. 部署命令（修正后）

### 5.1 PM2（推荐）

```bash
# API
pm2 start "uv run --project apps/api uvicorn main:app --host 0.0.0.0 --port 4000" --name market-intel-api

# Web
pm2 start "pnpm -C apps/web start -- -p 3000" --name market-intel-web

pm2 save
pm2 startup
```

### 5.3 Systemd 示例

```ini
[Unit]
Description=Market Intel API
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/market-intel-dashboard
ExecStart=/bin/bash -lc "uv run --project apps/api uvicorn main:app --host 0.0.0.0 --port 4000"
Restart=always
RestartSec=5
Environment=ENABLE_VECTOR_STORE=false

[Install]
WantedBy=multi-user.target
```

## 6. 验证命令（部署后确认）

```bash
# 克隆项目后初始化（仅首次）
pnpm install
uv sync --project apps/api

# 验证 API 启动（开发模式）
cd apps/api && uv run uvicorn main:app --host 0.0.0.0 --port 4000
# 访问 http://localhost:4000/health 确认返回 {"ok": true}

# 验证前端启动（开发模式）
cd apps/web && pnpm dev
# 访问 http://localhost:3000 确认页面正常渲染

# API 完整健康检查（增强后）
curl http://localhost:4000/health
# 期望返回示例：
# {
#   "ok": true,
#   "store_events": 80,
#   "updated_at": "2026-02-09T10:30:00+00:00",
#   "vector_store_enabled": true,
#   "vector_store_ready": true
# }
```

## 7. 验收标准（本轮建议）

1. 数据透明性  
- 默认用户路径不出现 seed（除非 live 不可用或用户显式筛选）。  

2. 可观测性  
- `/health` 能反映数据状态与向量能力状态。  

3. 资源可控  
- 在 `ENABLE_VECTOR_STORE=false` 下，API 常驻内存与启动时间明显下降。  

4. 部署可重复  
- 使用 PM2 或 systemd 可实现进程自动拉起与异常重启。

## 7. 总结

项目当前已经达到“本地可用 + 轻量部署可行”的状态。  
下一步重点不是大改架构，而是把“运维可观测性、部署稳定性、演示数据可见性”补齐，确保长期运行可控。

