from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path
import sys
import time

_API_ROOT = Path(__file__).resolve().parents[2]
if str(_API_ROOT) not in sys.path:
    # Allow "python apps/api/tools/pg/backfill_vectors.py" from repository root.
    sys.path.insert(0, str(_API_ROOT))

from app.config import AppConfig
from app.services.ingestion import refresh_store, write_vectors
from app.services.vector_store import EmbeddingsUnavailable, create_vector_store
from app.state import InMemoryStore


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
    parser = argparse.ArgumentParser(description="回填事件向量到 pgvector")
    parser.add_argument("--dsn", default="", help="Postgres DSN，默认读取 PG_DSN/PGVECTOR_DSN")
    parser.add_argument("--table", default="", help="向量表名，默认读取 PGVECTOR_TABLE")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将执行的步骤")
    args = parser.parse_args()

    base = AppConfig.from_env()
    dsn = (args.dsn or base.pg_dsn or base.pgvector_dsn).strip()
    table = (args.table or base.pgvector_table).strip()

    if args.dry_run:
        print("[backfill] dry-run")
        print("  - refresh events from configured sources")
        print("  - init pgvector store and ensure schema")
        print("  - upsert embeddings into table")
        print(f"  - table: {table}")
        if not dsn:
            print("  - dsn: <missing, will fail in non-dry-run mode>")
        return 0

    if not dsn:
        print("[backfill] 缺少 PG_DSN/PGVECTOR_DSN", file=sys.stderr)
        return 2
    if not table:
        print("[backfill] 缺少 PGVECTOR_TABLE", file=sys.stderr)
        return 2

    config = _build_config(base, dsn, table)
    started = time.perf_counter()

    try:
        store = InMemoryStore()
        report = asyncio.run(refresh_store(store, config))
        print(
            "[backfill] refresh done "
            f"events={len(store.events)} live={report.live_events} seed={report.seed_events}"
        )

        vector_store = create_vector_store(config)
        inserted = write_vectors(store.events, config, vector_store)
        elapsed = time.perf_counter() - started
        print(f"[backfill] inserted={inserted} elapsed={elapsed:.2f}s")
        return 0
    except EmbeddingsUnavailable as exc:
        print(f"[backfill] embeddings unavailable: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"[backfill] failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
