"""Run one Hermes stream-json request and retain timing/count metadata only."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", choices=(
        "hello_control", "timer_natural", "session_start_natural", "session_status_natural",
        "timer_pause_natural", "timer_resume_natural",
    ))
    parser.add_argument("mode", choices=("cold", "warm"))
    parser.add_argument("--continue-session")
    parser.add_argument("--db", required=True, help="Isolated temporary SQLite path for this run.")
    parser.add_argument("--reuse-db", action="store_true", help="Use a prepared database for a sequence.")
    parser.add_argument("--output", default="/tmp/latency-audit/hermes.jsonl")
    args = parser.parse_args()
    prompts = {
        "hello_control": "Respondé solamente OK. No uses herramientas.",
        "timer_natural": "Poneme un timer de 1 minuto para estudiar Física.",
        "session_start_natural": "Iniciá una sesión de estudio de Física sobre Ley de Gauss.",
        "session_status_natural": "¿Cuál es mi sesión actual y cuánto tiempo me queda?",
        "timer_pause_natural": "Pausá el timer.",
        "timer_resume_natural": "Reanudá el timer.",
    }
    prompt = prompts[args.benchmark]
    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    os.environ["STUDY_DB_PATH"] = str(db)
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import init_db
    import study_store
    if not args.reuse_db:
        init_db.initialize_database(db)
    if args.benchmark != "hello_control" and not args.reuse_db:
        subject = study_store.get_subject_by_name("Física") or study_store.add_subject(
            "Física", "problem_solving"
        )
        if args.benchmark in {"session_status_natural", "timer_pause_natural", "timer_resume_natural"}:
            session = study_store.start_session(subject["id"], 5, 10)
            if args.benchmark == "timer_resume_natural":
                study_store.pause_session(session["id"])
    command = ["hermes", "chat", "--query", prompt, "--oneshot", "--format", "stream-json",
               "--in", str(ROOT), "--run-budget", "180"]
    if args.continue_session:
        command[2:2] = ["--continue", args.continue_session, "--create-if-missing"]

    start_wall = time.time() * 1000
    start = time.perf_counter()
    process_env = os.environ.copy()
    audit_path = db.with_name(f"{db.stem}-{uuid4().hex}-tool.jsonl")
    process_env.update({"HERMES_LATENCY": "1", "HERMES_LATENCY_PATH": str(audit_path),
                        "HERMES_LATENCY_MODE": args.mode,
                        "HERMES_LATENCY_BENCHMARK": args.benchmark})
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, env=process_env)
    events = []
    answer_parts = []
    pending_tools = []
    first_response_ms = first_tool_ms = timer_start_ms = useful_action_ms = None
    skill_loads = tool_searches = failed_tool_searches = tool_calls = 0
    fastpath_success = None
    tool_timer_status = None
    failed_fastpath_actions = 0
    result = None
    for line in process.stdout:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "text":
            answer_parts.append(str(event.get("content", event.get("text", ""))))
        timestamp = event.get("timestamp")
        elapsed = (timestamp - start_wall) if isinstance(timestamp, (int, float)) else None
        if kind in ("text", "tool_use") and first_response_ms is None and elapsed is not None:
            first_response_ms = round(elapsed, 3)
        if kind == "tool_use":
            tool_calls += 1
            name = event.get("name")
            pending_tools.append(name)
            if first_tool_ms is None and elapsed is not None:
                first_tool_ms = round(elapsed, 3)
            if name == "skill_view":
                skill_loads += 1
            if name == "tool_search":
                tool_searches += 1
        if kind == "tool_result" and event.get("name") == "tool_search":
            output = str(event.get("output", "")).lower()
            failed_tool_searches += int(bool(event.get("is_error")) or any(
                phrase in output for phrase in ("no matching", "no tools found", "not found")))
        if kind == "tool_result":
            tool_name = pending_tools.pop(0) if pending_tools else event.get("name")
            if tool_name and tool_name.startswith("study_"):
                tool_output = event.get("output", "")
                if isinstance(tool_output, str):
                    try:
                        tool_output = json.loads(tool_output)
                    except json.JSONDecodeError:
                        tool_output = {}
                action_ok = isinstance(tool_output, dict) and tool_output.get("ok") is True
                fastpath_success = action_ok
                failed_fastpath_actions += int(not action_ok)
                if action_ok:
                    tool_timer_status = (tool_output.get("timer") or {}).get("status")
                if action_ok and useful_action_ms is None and elapsed is not None:
                    useful_action_ms = round(elapsed, 3)
                if action_ok and tool_name == "study_timer_start" and timer_start_ms is None and elapsed is not None:
                    timer_start_ms = round(elapsed, 3)
        if kind == "result":
            result = {"exit_code": event.get("exit_code"), "duration_ms": event.get("duration_ms"),
                      "tokens_total": event.get("tokens", {}).get("total")}
        if kind in ("system", "tool_use", "tool_result", "result"):
            events.append({"type": kind, "name": event.get("name"), "timestamp": timestamp})
    process.wait()
    audit_rows = []
    if audit_path.exists():
        audit_rows = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    local_execution_ms = sum(row.get("program_execution_ms") or 0 for row in audit_rows) or None
    local_process_spawns = sum(row.get("number_of_process_spawns") or 0 for row in audit_rows)
    row = {"benchmark": args.benchmark, "mode": args.mode,
           "success": (process.returncode == 0 and
                       (fastpath_success is True if args.benchmark != "hello_control"
                        else tool_calls == 0)),
           "hello_ok": "".join(answer_parts).strip() == "OK" if args.benchmark == "hello_control" else None,
           "session_context_reused": bool(args.continue_session),
           "plugin_tool_calls": sum(1 for event in events if event.get("type") == "tool_use"
                                    and event.get("name", "").startswith("study_")),
           "fastpath_success": fastpath_success,
           "tool_timer_status": tool_timer_status,
           "failed_fastpath_actions": failed_fastpath_actions,
           "number_of_subprocesses": local_process_spawns if audit_rows else None,
           "local_execution_ms": round(local_execution_ms, 3) if local_execution_ms else None,
           "process_exit_code": process.returncode, "total_ms": round((time.perf_counter() - start) * 1000, 3),
           "first_response_ms": first_response_ms, "first_tool_ms": first_tool_ms,
           "timer_start_latency_ms": timer_start_ms, "useful_action_latency_ms": useful_action_ms,
           "response_latency_ms": round((time.perf_counter() - start) * 1000, 3),
           "number_of_tool_calls": tool_calls, "number_of_skill_loads": skill_loads,
           "number_of_tool_searches": tool_searches, "failed_tool_searches": failed_tool_searches,
           "result": result, "events": events}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False))
    return 0 if process.returncode == 0 else process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
