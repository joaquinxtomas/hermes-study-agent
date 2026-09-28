"""Summarize latency JSONL runs without requiring third-party packages."""

import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "storage" / "latency_runs.jsonl"
STAGES = (
    "model_decision_ms", "skill_load_ms", "tool_dispatch_ms", "process_start_ms",
    "python_import_ms", "program_execution_ms", "artifact_render_ms", "preview_ms",
    "post_tool_model_ms",
)


def read_runs(path: Path) -> list[dict]:
    runs = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"JSON inválido en línea {line_number}: {error.msg}") from error
            if not isinstance(value, dict):
                raise ValueError(f"La línea {line_number} debe contener un objeto JSON.")
            runs.append(value)
    return runs


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(runs: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for run in runs:
        groups.setdefault((str(run.get("benchmark", "unknown")), str(run.get("mode", "unknown"))), []).append(run)
    rows = []
    for (benchmark, mode), group in sorted(groups.items()):
        totals = [float(r["total_ms"]) for r in group if isinstance(r.get("total_ms"), (int, float))]
        stage_values = {
            key: [float(r[key]) for r in group if isinstance(r.get(key), (int, float))]
            for key in STAGES
        }
        medians = {key: statistics.median(values) for key, values in stage_values.items() if values}
        median_total = statistics.median(totals) if totals else None
        rows.append({
            "benchmark": benchmark, "mode": mode, "count": len(group),
            "median_ms": median_total, "average_ms": statistics.fmean(totals) if totals else None,
            "p95_ms": percentile(totals, .95), "min_ms": min(totals) if totals else None,
            "max_ms": max(totals) if totals else None,
            "dominant_stage": max(medians, key=medians.get) if medians else None,
            "dominant_stage_pct": round(100 * medians[max(medians, key=medians.get)] / median_total, 1)
            if medians and median_total else None,
            "average_model_turns": _average(group, "number_of_model_turns"),
            "average_tool_calls": _average(group, "number_of_tool_calls"),
            "average_process_spawns": _average(group, "number_of_process_spawns"),
            "success_count": sum(run.get("success") is True for run in group),
            "failure_count": sum(run.get("success") is False for run in group),
            "stage_medians_ms": medians,
        })
    return rows


def _average(group: list[dict], key: str) -> float | None:
    values = [float(run[key]) for run in group if isinstance(run.get(key), (int, float))]
    return round(statistics.fmean(values), 2) if values else None


def _fmt(value) -> str:
    return "—" if value is None else f"{value:.1f}"


def _share(row: dict, stage: str) -> str:
    total = row["median_ms"]
    value = row["stage_medians_ms"].get(stage)
    return f"{100 * value / total:.0f}%" if total and value is not None else "—"


def render(rows: list[dict]) -> str:
    lines = ["Benchmark | Mode | N | Median ms | Avg ms | P95 ms | Model% | Skill% | Tool% | Process% | Python% | Exec% | Render% | Preview% | Post-model% | Dominant | Turns | Tools | Spawns | OK/Fail",
             "---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:"]
    for row in rows:
        shares = (
            _share(row, "model_decision_ms"), _share(row, "skill_load_ms"),
            _share(row, "tool_dispatch_ms"), _share(row, "process_start_ms"),
            _share(row, "python_import_ms"), _share(row, "program_execution_ms"),
            _share(row, "artifact_render_ms"), _share(row, "preview_ms"),
            _share(row, "post_tool_model_ms"),
        )
        lines.append(" | ".join((
            row["benchmark"], row["mode"], str(row["count"]), _fmt(row["median_ms"]),
            _fmt(row["average_ms"]), _fmt(row["p95_ms"]), *shares,
            row["dominant_stage"] or "—", _fmt(row["average_model_turns"]),
            _fmt(row["average_tool_calls"]), _fmt(row["average_process_spawns"]),
            f'{row["success_count"]}/{row["failure_count"]}',
        )))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    try:
        rows = summarize(read_runs(args.input))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
