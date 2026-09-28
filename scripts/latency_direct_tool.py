"""Call Hermes' registered terminal dispatcher directly for latency controls.

Run from the project root with STUDY_DB_PATH pointing at an initialized test DB.
The script imports Hermes from its installed checkout and uses the same
``model_tools.handle_function_call`` route that dispatches model tool calls.
"""

import argparse
import json
import os
from pathlib import Path
import shlex
import sys
import uuid

from latency_profiler import LatencyRun

ROOT = Path(__file__).resolve().parents[1]
HERMES_INSTALL = Path.home() / ".hermes" / "hermes-agent"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="Física")
    parser.add_argument("--target-minutes", type=int, default=1)
    parser.add_argument("--hard-limit-minutes", type=int, default=2)
    parser.add_argument("--repeat", type=int, default=1)
    return parser


def _call_terminal(handle_function_call, args, run: LatencyRun, run_number: int) -> dict:
    command = " ".join((
        ".venv/bin/python scripts/study_cli.py session start",
        shlex.quote(args.subject),
        f"--target-minutes {args.target_minutes}",
        f"--hard-limit-minutes {args.hard_limit_minutes}",
    ))
    run.mark("tool_dispatch_started")
    result_text = handle_function_call(
        "terminal",
        {"command": command, "timeout": 30, "workdir": str(ROOT)},
        task_id=f"latency-direct-{run_number}",
        session_id=f"latency-direct-{run_number}",
        tool_call_id=str(uuid.uuid4()),
        enabled_toolsets=["terminal"],
    )
    run.mark("tool_dispatch_finished")
    run.mark("timer_started")
    run.mark("final_response_ready")
    run.increment("number_of_tool_calls")
    try:
        result = json.loads(result_text)
        run.success = result.get("exit_code") == 0 and not result.get("error")
        if not run.success:
            run.error_type = "ToolExecutionError"
    except (TypeError, json.JSONDecodeError):
        result = {"error": "invalid_tool_result"}
        run.success = False
        run.error_type = "InvalidToolResult"
    run.mark("core_program_finished")
    run.finish(success=bool(run.success), error=RuntimeError(run.error_type) if run.error_type else None)
    return {"run_id": run.run_id, "success": run.success, "tool_result": result}


def main() -> int:
    args = _parser().parse_args()
    if args.repeat < 1 or args.repeat > 10:
        print("--repeat debe estar entre 1 y 10.", file=sys.stderr)
        return 2
    if not os.environ.get("STUDY_DB_PATH"):
        print("Definí STUDY_DB_PATH a una base temporal inicializada.", file=sys.stderr)
        return 2
    if not HERMES_INSTALL.is_dir():
        print(f"No se encuentra la instalación Hermes: {HERMES_INSTALL}", file=sys.stderr)
        return 2
    runs = []
    first_run = LatencyRun.from_environment("timer_direct_tool")
    first_run.set_benchmark("timer_direct_tool")
    first_run.mark("user_request_received")
    first_run.mark("python_entry_started")
    sys.path.insert(0, str(HERMES_INSTALL))
    try:
        from model_tools import handle_function_call
    except Exception as error:
        print(f"No se pudo cargar el dispatcher de Hermes: {type(error).__name__}", file=sys.stderr)
        return 1
    first_run.mark("core_program_started")
    runs.append(first_run)
    for _ in range(1, args.repeat):
        run = LatencyRun.from_environment("timer_direct_tool")
        run.set_benchmark("timer_direct_tool")
        run.mark("user_request_received")
        run.mark("python_entry_started")
        run.mark("core_program_started")
        runs.append(run)
    results = [_call_terminal(handle_function_call, args, run, i + 1)
               for i, run in enumerate(runs)]
    print(json.dumps(results, ensure_ascii=False))
    return 0 if all(result["success"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
