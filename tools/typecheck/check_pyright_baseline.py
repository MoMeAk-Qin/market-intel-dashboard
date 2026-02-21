from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


DiagnosticEntry = dict[str, str | int]


def _entry_key(entry: DiagnosticEntry) -> tuple[str, str, str, int, int, str]:
    return (
        str(entry["file"]),
        str(entry["severity"]),
        str(entry["rule"]),
        int(entry["line"]),
        int(entry["character"]),
        str(entry["message"]),
    )


def _normalize_file_path(file_path: str, repo_root: Path) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        return str(path)
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _normalize_report_entry(diag: dict[str, Any], repo_root: Path) -> DiagnosticEntry:
    start = diag.get("range", {}).get("start", {})
    message = str(diag.get("message", "")).splitlines()[0].strip()
    return {
        "file": _normalize_file_path(str(diag.get("file", "")), repo_root),
        "severity": str(diag.get("severity", "")),
        "rule": str(diag.get("rule", "")),
        "line": int(start.get("line", 0)) + 1,
        "character": int(start.get("character", 0)) + 1,
        "message": message,
    }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: {path}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 解析失败: {path} ({exc})") from exc


def _load_baseline_entries(path: Path) -> list[DiagnosticEntry]:
    data = _load_json(path)
    raw_entries = data.get("entries", [])
    if not isinstance(raw_entries, list):
        raise RuntimeError(f"基线文件 entries 不是数组: {path}")

    entries: list[DiagnosticEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "file": str(item.get("file", "")),
                "severity": str(item.get("severity", "")),
                "rule": str(item.get("rule", "")),
                "line": int(item.get("line", 0)),
                "character": int(item.get("character", 0)),
                "message": str(item.get("message", "")),
            }
        )
    return entries


def _format_entry(entry: DiagnosticEntry) -> str:
    return (
        f"{entry['file']}:{entry['line']}:{entry['character']} "
        f"[{entry['severity']}/{entry['rule']}] {entry['message']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check pyright diagnostics against a baseline.")
    parser.add_argument("--input", required=True, help="Path to pyright --outputjson report.")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON file.")
    parser.add_argument("--repo-root", default=".", help="Repository root for path normalization.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    report_path = Path(args.input)
    baseline_path = Path(args.baseline)

    try:
        report = _load_json(report_path)
        baseline_entries = _load_baseline_entries(baseline_path)
    except RuntimeError as exc:
        print(f"[typecheck-baseline] {exc}", file=sys.stderr)
        return 2

    diagnostics = report.get("generalDiagnostics", [])
    if not isinstance(diagnostics, list):
        print("[typecheck-baseline] pyright 输出缺少 generalDiagnostics 数组", file=sys.stderr)
        return 2

    current_entries = [
        _normalize_report_entry(diag, repo_root)
        for diag in diagnostics
        if isinstance(diag, dict) and str(diag.get("severity", "")).lower() in {"error", "warning"}
    ]

    current_by_key = {_entry_key(item): item for item in current_entries}
    baseline_by_key = {_entry_key(item): item for item in baseline_entries}

    new_keys = sorted(set(current_by_key) - set(baseline_by_key))
    stale_keys = sorted(set(baseline_by_key) - set(current_by_key))

    print(
        "[typecheck-baseline] "
        f"current={len(current_by_key)} baseline={len(baseline_by_key)} "
        f"new={len(new_keys)} stale={len(stale_keys)}"
    )

    if stale_keys:
        print("[typecheck-baseline] 以下告警已不存在，可后续从基线移除：")
        for key in stale_keys:
            print(f"  - {_format_entry(baseline_by_key[key])}")

    if new_keys:
        print("[typecheck-baseline] 检测到新增告警（阻断）：", file=sys.stderr)
        for key in new_keys:
            print(f"  - {_format_entry(current_by_key[key])}", file=sys.stderr)
        return 1

    print("[typecheck-baseline] 未发现新增告警。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
