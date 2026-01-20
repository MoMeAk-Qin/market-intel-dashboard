# HKMA API 端点清单（待确认）

HKMA API 端点需要从官方文档确认具体 `dataset/table` 名称。下面列出**建议优先接入的表**，并提供可填写到 `HKMA_ENDPOINTS` 的 URL 模板。请确认每个表的真实名称后替换。

## URL 模板

```
https://api.hkma.gov.hk/public/market-data-and-statistics/{dataset}/{table}?format=json
```

## 建议优先接入的表（请确认表名）

1) **HIBOR / HIBID**
- 目的：港元短端利率曲线
- 需要确认：是否按 `tenor` 字段返回（ON/1W/1M/3M/6M/12M）
- 预期字段：`date` + `tenor` + `value`/`rate`

2) **Base Rate / Discount Window**
- 目的：政策利率与流动性指标
- 需要确认：表名与字段名（`base_rate` / `discount_window_rate`）

3) **USD/HKD Spot 或参考汇率**
- 目的：联系汇率指标
- 需要确认：是否提供 `mid_rate` / `closing_rate`

4) **Exchange Fund Bills/Notes Yields**
- 目的：港币短端收益率结构
- 需要确认：是否有按期限列（`tenor`）

5) **Aggregate Balance / Interbank Liquidity**
- 目的：资金面与流动性监测
- 需要确认：是否有 `aggregate_balance` 指标

## 填写示例（确认后替换）

```
HKMA_ENDPOINTS=
https://api.hkma.gov.hk/public/market-data-and-statistics/<dataset>/<table1>?format=json,
https://api.hkma.gov.hk/public/market-data-and-statistics/<dataset>/<table2>?format=json
```

## 需要你确认的表

- HIBOR/HIBID 数据集与表名
- Base Rate / Discount Window 表名
- USD/HKD 参考汇率表名
- Exchange Fund Bills/Notes 收益率表名
- Aggregate Balance/资金面指标表名

## 待办事项

- 确认 HKMA 的具体 dataset/table 名称（见本文件）。确认后写入 `HKMA_ENDPOINTS` 并进行字段映射微调。
