from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

_API_ROOT = Path(__file__).resolve().parents[2]
if str(_API_ROOT) not in sys.path:
    # Allow "python apps/api/tools/pg/healthcheck.py" from repository root.
    sys.path.insert(0, str(_API_ROOT))

from app.config import AppConfig
from app.services.pg_vector_store import PgVectorStore


def _build_config(base: AppConfig, dsn: str, table: str) -> AppConfig:
    return replace(
        base,
        enable_vector_store=True,
        enable_pgvector=True,
        vector_backend="pgvector",
        pg_dsn=dsn,
        pgvector_dsn=dsn,
        pgvector_table=table,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="pgvector 健康检查")
    parser.add_argument("--dsn", default="", help="Postgres DSN，默认读取 PG_DSN/PGVECTOR_DSN")
    parser.add_argument("--table", default="", help="向量表名，默认读取 PGVECTOR_TABLE")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将执行的步骤")
    args = parser.parse_args()

    base = AppConfig.from_env()
    dsn = (args.dsn or base.pg_dsn or base.pgvector_dsn).strip()
    table = (args.table or base.pgvector_table).strip()

    if args.dry_run:
        print("[healthcheck] dry-run")
        print(f"  - table: {table}")
        print("  - checks: extension(vector), table existence, row count")
        if not dsn:
            print("  - dsn: <missing, will fail in non-dry-run mode>")
        return 0

    if not dsn:
        print("[healthcheck] 缺少 PG_DSN/PGVECTOR_DSN", file=sys.stderr)
        return 2
    if not table:
        print("[healthcheck] 缺少 PGVECTOR_TABLE", file=sys.stderr)
        return 2

    config = _build_config(base, dsn, table)
    try:
        store = PgVectorStore(config)
        result = store.healthcheck()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if bool(result.get("ok")) else 1
    except Exception as exc:
        print(f"[healthcheck] failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
