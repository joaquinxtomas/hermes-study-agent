"""Run the post-change Hermes Fast Path benchmarks against isolated SQLite files."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "scripts" / "latency_hermes_capture.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="/tmp/latency-audit/fastpath-hermes.jsonl")
    parser.add_argument("--timer-only", action="store_true", help="Run 3 cold + 3 warm timer requests.")
    parser.add_argument("--sessions-only", action="store_true", help="Run session start/status/pause/resume once each.")
    parser.add_argument("--v12", action="store_true", help="Run the complete V1.2 validation matrix.")
    parser.add_argument("--direct-only", action="store_true", help="Append only the V1.2 direct-tool samples.")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not args.direct_only:
        output.write_text("", encoding="utf-8")

    run_tag = uuid4().hex[:8]
    schedule = [] if args.sessions_only or args.direct_only else [
        ("timer_natural", "cold", None, 3),
        ("timer_natural", "warm", f"fastpath-v1-timer-warm-{run_tag}", 3),
    ]
    if args.v12 and not args.direct_only:
        schedule.extend([
            ("session_start_natural", "cold", None, 3),
            ("session_start_natural", "warm", f"fastpath-v12-session-warm-{run_tag}", 3),
            ("session_status_natural", "warm", f"fastpath-v12-status-warm-{run_tag}", 3),
            ("hello_control", "cold", None, 3),
            ("hello_control", "warm", f"fastpath-v12-hello-warm-{run_tag}", 3),
        ])
    elif not args.timer_only and not args.direct_only:
        schedule.extend([
            ("session_start_natural", "cold", None, 1),
            ("session_status_natural", "cold", None, 1),
            ("timer_pause_natural", "cold", None, 1),
            ("timer_resume_natural", "cold", None, 1),
        ])

    run_number = 0
    for benchmark, mode, session, count in schedule:
        for _ in range(count):
            run_number += 1
            db = Path(f"/tmp/latency-audit/fastpath-{run_tag}-{benchmark}-{mode}-{run_number}.db")
            command = [sys.executable, str(CAPTURE), benchmark, mode,
                       "--db", str(db), "--output", str(output)]
            if session:
                command.extend(["--continue-session", session])
            result = subprocess.run(command, cwd=ROOT, env=os.environ.copy(),
                                    text=True, capture_output=True)
            print(result.stdout.rstrip(), flush=True)
            if result.returncode:
                print(result.stderr.rstrip(), file=sys.stderr)
                return result.returncode
            try:
                captured = json.loads(result.stdout.splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                print("No pude validar el resultado JSON del benchmark.", file=sys.stderr)
                return 1
            if not captured.get("success"):
                print("La herramienta rápida devolvió error; la corrida no cuenta como éxito.",
                      file=sys.stderr)
                return 1
    if args.v12 and not args.direct_only:
        sys.path.insert(0, str(ROOT / "scripts"))
        import init_db
        import study_store

        for sequence in range(3):
            db = Path(f"/tmp/latency-audit/fastpath-{run_tag}-pause-resume-{sequence}.db")
            os.environ["STUDY_DB_PATH"] = str(db)
            study_store.DATABASE_PATH = db
            init_db.initialize_database(db)
            subject = study_store.add_subject("Física", "problem_solving")
            started = study_store.start_session(subject["id"], 1, 1)
            conversation = f"fastpath-v12-pause-resume-{run_tag}"
            for benchmark, expected_status in (("timer_pause_natural", "paused"),
                                               ("timer_resume_natural", "active")):
                command = [sys.executable, str(CAPTURE), benchmark, "warm", "--db", str(db),
                           "--reuse-db", "--output", str(output), "--continue-session", conversation]
                result = subprocess.run(command, cwd=ROOT, env=os.environ.copy(),
                                        text=True, capture_output=True)
                if result.returncode:
                    print(result.stderr.rstrip(), file=sys.stderr)
                    return result.returncode
                captured = json.loads(result.stdout.splitlines()[-1])
                print(result.stdout.rstrip(), flush=True)
                session = study_store.get_session(started["id"])
                if not captured.get("success") or captured.get("tool_timer_status") != expected_status or (
                    session["status"] != expected_status
                ):
                    print(f"Estado incorrecto tras {benchmark}.", file=sys.stderr)
                    return 1

    if args.v12:
        direct = ROOT / "scripts" / "latency_fastpath_direct.py"
        hermes_python = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
        for index in range(3):
            db = Path(f"/tmp/latency-audit/fastpath-{run_tag}-direct-cold-{index}.db")
            start_wall_ms = time.time() * 1000
            start = time.perf_counter()
            result = subprocess.run([str(hermes_python), str(direct), "--db", str(db)], cwd=ROOT,
                                    text=True, capture_output=True)
            total_ms = round((time.perf_counter() - start) * 1000, 3)
            if result.returncode:
                print(result.stderr.rstrip(), file=sys.stderr)
                return result.returncode
            item = json.loads(result.stdout.splitlines()[-1])[0]
            row = {"benchmark": "timer_direct_tool", "mode": "cold", "success": item["success"],
                   "total_ms": total_ms,
                   "timer_start_latency_ms": round(item["action_completed_epoch_ms"] - start_wall_ms, 3),
                   "dispatch_ms": item["dispatch_ms"], "local_execution_ms": item["local_execution_ms"],
                   "number_of_tool_calls": 1,
                   "number_of_tool_searches": 0, "number_of_skill_loads": 0,
                   "number_of_subprocesses": item["process_spawns"]}
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
            if not item["success"]:
                return 1
        db = Path(f"/tmp/latency-audit/fastpath-{run_tag}-direct-warm.db")
        result = subprocess.run([str(hermes_python), str(direct), "--db", str(db), "--repeat", "4"],
                                cwd=ROOT, text=True, capture_output=True)
        if result.returncode:
            print(result.stderr.rstrip(), file=sys.stderr)
            return result.returncode
        for item in json.loads(result.stdout.splitlines()[-1])[1:]:
            row = {"benchmark": "timer_direct_tool", "mode": "warm", "success": item["success"],
                   "total_ms": item["dispatch_ms"], "timer_start_latency_ms": item["dispatch_ms"],
                   "dispatch_ms": item["dispatch_ms"], "local_execution_ms": item["local_execution_ms"],
                   "number_of_tool_calls": 1,
                   "number_of_tool_searches": 0, "number_of_skill_loads": 0,
                   "number_of_subprocesses": item["process_spawns"]}
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
            if not item["success"]:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
