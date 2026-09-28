"""Call the registered Study Fast Path tool through Hermes' real tool dispatcher."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

from latency_profiler import LatencyRun


ROOT = Path(__file__).resolve().parents[1]
HERMES_INSTALL = Path.home() / ".hermes" / "hermes-agent"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Temporary SQLite path (one database per repeat).")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 10:
        parser.error("--repeat debe estar entre 1 y 10.")
    if not HERMES_INSTALL.is_dir():
        parser.error(f"No se encuentra Hermes en {HERMES_INSTALL}.")

    os.environ["HERMES_LATENCY"] = "0"
    os.environ["STUDY_DB_PATH"] = args.db
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(HERMES_INSTALL))
    import init_db
    import study_store
    try:
        from model_tools import handle_function_call
    except Exception as error:
        print(json.dumps({"error": f"Hermes dispatcher import failed: {type(error).__name__}"}))
        return 1

    rows = []
    for index in range(args.repeat):
        db = Path(args.db) if args.repeat == 1 else Path(f"{args.db}.{index + 1}")
        os.environ["STUDY_DB_PATH"] = str(db)
        study_store.DATABASE_PATH = db
        init_db.initialize_database(db)
        subject = study_store.add_subject("Física", "problem_solving")
        run = LatencyRun("timer_direct_fastpath", "warm", enabled=True,
                         output="/tmp/latency-audit/fastpath-direct.jsonl")
        run.mark("user_request_received")
        run.mark("core_program_started")
        run.mark("tool_dispatch_started")
        started = time.perf_counter()
        result_text = handle_function_call(
            "study_timer_start", {"duration_minutes": 1, "subject": subject["name"]},
            task_id=f"fastpath-{index}", session_id=f"fastpath-{index}",
            tool_call_id=str(uuid.uuid4()), enabled_toolsets=["project"],
        )
        dispatch_ms = round((time.perf_counter() - started) * 1000, 3)
        run.mark("tool_dispatch_finished")
        run.mark("timer_started")
        run.mark("core_program_finished")
        run.mark("final_response_ready")
        run.increment("number_of_tool_calls")
        result = json.loads(result_text)
        audit = run.finish(success=result.get("ok") is True,
                           error=RuntimeError("ToolFailed") if result.get("ok") is not True else None)
        rows.append({"success": result.get("ok") is True, "dispatch_ms": dispatch_ms,
                     "action_completed_epoch_ms": round(time.time() * 1000, 3),
                     "local_execution_ms": audit.get("program_execution_ms") if audit else None,
                     "timer_status": result.get("timer", {}).get("status"),
                     "number_of_tool_calls": 1, "tool_searches": 0, "skill_loads": 0,
                     "process_spawns": run.counts.get("number_of_process_spawns", 0)})
    print(json.dumps(rows, ensure_ascii=False))
    return 0 if all(row["success"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
