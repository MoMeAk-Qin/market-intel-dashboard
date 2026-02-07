from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.sources.hkma_discovery import run_discovery_cli


if __name__ == "__main__":
    raise SystemExit(run_discovery_cli())
