"""Opt-in, prompt-free latency recording for Study Agent CLI processes."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
_DURATIONS = {
    "total_ms": ("user_request_received", "final_response_ready"),
    "model_decision_ms": ("model_decision_started", "model_decision_finished"),
    "skill_load_ms": ("skill_load_started", "skill_load_finished"),
    "tool_dispatch_ms": ("tool_dispatch_started", "tool_dispatch_finished"),
    "process_start_ms": ("external_process_started", "core_program_started"),
    "python_import_ms": ("python_entry_started", "core_program_started"),
    "program_execution_ms": ("core_program_started", "core_program_finished"),
    "artifact_render_ms": ("artifact_render_started", "artifact_generated"),
    "preview_ms": ("preview_open_started", "preview_opened"),
    "post_tool_model_ms": ("post_tool_model_started", "final_response_ready"),
    "timer_start_latency_ms": ("user_request_received", "timer_started"),
}


class LatencyRun:
    """Record one run only when ``HERMES_LATENCY=1`` is set."""

    def __init__(self, benchmark: str, mode: str, *, enabled: bool = False,
                 run_id: str | None = None, output: str | Path | None = None,
                 benchmark_pinned: bool = False):
        self.enabled = enabled
        self.benchmark = benchmark
        self._benchmark_pinned = benchmark_pinned
        self.mode = mode
        self.run_id = run_id or str(uuid4())
        self.output = Path(output or os.environ.get(
            "HERMES_LATENCY_PATH", ROOT / "storage" / "latency_runs.jsonl"
        ))
        self._started = time.perf_counter()
        self.timestamps_ms: dict[str, float] = {}
        self.counts: dict[str, int] = {}
        self.artifact_generated: bool | None = None
        self.preview_opened: bool | None = None
        self.fast_path_used = False
        self.action: str | None = None
        self.success: bool | None = None
        self.error_type: str | None = None
        self._active = self.enabled
        if self.enabled:
            self._audit_hook = self._count_process_spawn
            sys.addaudithook(self._audit_hook)

    @classmethod
    def from_environment(cls, default_benchmark: str) -> "LatencyRun":
        pinned = "HERMES_LATENCY_BENCHMARK" in os.environ
        return cls(
            os.environ.get("HERMES_LATENCY_BENCHMARK", default_benchmark),
            os.environ.get("HERMES_LATENCY_MODE", "unknown"),
            enabled=os.environ.get("HERMES_LATENCY") == "1",
            run_id=os.environ.get("HERMES_LATENCY_RUN_ID"),
            benchmark_pinned=pinned,
        )

    def set_benchmark(self, benchmark: str) -> None:
        if not self._benchmark_pinned:
            self.benchmark = benchmark

    def _count_process_spawn(self, event: str, _args: tuple) -> None:
        if self._active and event == "subprocess.Popen":
            self.increment("number_of_process_spawns")

    def mark(self, name: str) -> None:
        if self.enabled:
            self.timestamps_ms.setdefault(name, round((time.perf_counter() - self._started) * 1000, 3))

    def increment(self, name: str, amount: int = 1) -> None:
        if self.enabled:
            self.counts[name] = self.counts.get(name, 0) + amount

    def finish(self, *, success: bool, error: BaseException | None = None) -> dict | None:
        if not self.enabled:
            return None
        self.success = success
        self.error_type = type(error).__name__ if error is not None else None
        self._active = False
        row = self.to_dict()
        self.output.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        fd = os.open(self.output, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(fd, encoded)
        finally:
            os.close(fd)
        return row

    def to_dict(self) -> dict:
        durations = {}
        for field, (start, end) in _DURATIONS.items():
            if start in self.timestamps_ms and end in self.timestamps_ms:
                durations[field] = round(max(0, self.timestamps_ms[end] - self.timestamps_ms[start]), 3)
            else:
                durations[field] = None
        return {
            "run_id": self.run_id,
            "benchmark": self.benchmark,
            "mode": self.mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **durations,
            "timestamps_ms": self.timestamps_ms,
            "number_of_model_turns": self.counts.get("number_of_model_turns"),
            "number_of_tool_calls": self.counts.get("number_of_tool_calls"),
            "number_of_process_spawns": self.counts.get("number_of_process_spawns", 0),
            "number_of_skill_loads": self.counts.get("number_of_skill_loads"),
            "artifact_generated": self.artifact_generated,
            "preview_opened": self.preview_opened,
            "fast_path_used": self.fast_path_used,
            "action": self.action,
            "success": self.success,
            "error_type": self.error_type,
        }
