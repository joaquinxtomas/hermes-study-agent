"""Hermes tools that dispatch common study actions directly to the Study Core."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def _project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "scripts" / "study_store.py").is_file():
            return parent
    for parent in Path.cwd().resolve().parents:
        if (parent / "scripts" / "study_store.py").is_file():
            return parent
    raise RuntimeError("No encuentro scripts/study_store.py; abrí Hermes desde el proyecto Study Agent.")


def _core():
    root = _project_root()
    scripts = str(root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import study_store
    return study_store


def _result(action, operation):
    try:
        result = operation()
        return json.dumps({"ok": True, "action": action, **result}, ensure_ascii=False)
    except Exception as error:
        return json.dumps({"ok": False, "action": action, "error": str(error)}, ensure_ascii=False)


def _session_payload(store, session):
    if session is None:
        return {"session": None, "timer": None, "timers": []}
    return {
        "session": store.get_session(session["id"]),
        "session_timer": store.session_timer(session["id"]),
        "timer": store.get_current_study_timer(session["id"]),
        "timers": store.list_study_timers(session["id"]),
    }


def _handler(action):
    def handle(params, **_kwargs):
        root = _project_root()
        scripts = str(root / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from latency_profiler import LatencyRun

        audit = LatencyRun.from_environment("fast_path")
        audit.fast_path_used = True
        audit.action = action
        audit.mark("tool_dispatch_started")
        audit.mark("core_program_started")
        store = _core()
        args = params or {}

        def run():
            if action in {"study_timer_start", "study_session_start"}:
                timer = action == "study_timer_start"
                if timer:
                    minutes = args.get("duration_minutes")
                    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1:
                        raise ValueError("duration_minutes debe ser un entero mayor que cero.")
                    target, hard_limit = 75, 90
                else:
                    target = args.get("target_minutes", 75)
                    hard_limit = args.get("hard_limit_minutes", max(target, 90))
                    if isinstance(target, bool) or not isinstance(target, int) or target < 1:
                        raise ValueError("target_minutes debe ser un entero mayor que cero.")
                    if isinstance(hard_limit, bool) or not isinstance(hard_limit, int):
                        raise ValueError("hard_limit_minutes debe ser un entero mayor que cero.")
                subject_name = str(args.get("subject", "")).strip()
                if not subject_name:
                    current = store.get_active_session() or store.get_latest_session("paused")
                    if current:
                        subject_name = store.get_session(current["id"])["subject_name"]
                    else:
                        subjects = store.list_subjects()
                        if len(subjects) != 1:
                            raise ValueError(
                                "Indicá la materia; solo puedo inferirla si hay exactamente una materia activa."
                            )
                        subject = subjects[0]
                else:
                    subject = store.get_subject_by_name(subject_name)
                if subject_name:
                    subject = store.get_subject_by_name(subject_name)
                if subject is None or not subject["active"]:
                    raise store.NotFoundError(f"No encuentro una materia activa llamada {subject_name!r}.")
                if timer:
                    session = store.get_active_session()
                    if session and session["subject_id"] != subject["id"]:
                        session = None
                    if session and store.session_timer(session["id"])["hard_limit_remaining_seconds"] <= 0:
                        store.fire_session_timer(session["id"], "hard_limit")
                        session = None
                    existing_active = store.get_active_session()
                    if session is None and existing_active is None:
                        paused = store.get_latest_session("paused")
                        if (paused and paused["subject_id"] == subject["id"]
                                and not paused["hard_limit_notified_at"]):
                            session = store.resume_session(paused["id"])
                    if session is None:
                        session = store.start_session(subject["id"], target, hard_limit)
                    timer_row = store.start_study_timer(
                        session["id"], minutes, str(args.get("topic") or "").strip() or None,
                    )
                    topic = str(args.get("topic", "")).strip()
                    if topic:
                        store.create_checkpoint(session["id"], current_topic=topic)
                    audit.mark("timer_started")
                else:
                    session = store.start_session(subject["id"], target, hard_limit)
                topic = str(args.get("topic", "")).strip()
                if topic and not timer:
                    store.create_checkpoint(session["id"], current_topic=topic)
                return {"message": "Timer iniciado dentro de la sesión." if timer else "Sesión iniciada.",
                        **({"timer": timer_row} if timer else {}),
                        **_session_payload(store, session)}

            if action == "study_timer_pause":
                timer_row = store.pause_study_timer()
                session = store.get_session(timer_row["session_id"])
                return {"message": "Timer pausado; la sesión sigue abierta.", "timer": timer_row,
                        **_session_payload(store, session)}

            if action == "study_timer_resume":
                timer_row = store.resume_study_timer()
                session = store.get_session(timer_row["session_id"])
                return {"message": "Timer reanudado.", "timer": timer_row,
                        **_session_payload(store, session)}

            if action == "study_timer_stop":
                timer_row = store.stop_study_timer(args.get("session_id"))
                session = store.get_session(timer_row["session_id"])
                return {"message": "Timer detenido; la sesión sigue abierta.", "timer": timer_row,
                        **_session_payload(store, session)}

            if action == "study_session_end":
                session_id = args.get("session_id")
                session = (store.get_session(session_id) if session_id else
                           store.get_latest_session("active") or store.get_latest_session("paused"))
                if session is None:
                    raise store.StudyStoreError("No hay una sesión activa para terminar.")
                status = args.get("status", "completed")
                closed = store.close_session(session["id"], status)
                return {"message": "Sesión terminada.", **_session_payload(store, closed)}

            session_id = args.get("session_id")
            session = (store.get_session(session_id) if session_id else
                       store.get_latest_session("active") or store.get_latest_session("paused"))
            if session_id and session is None:
                raise store.NotFoundError(f"No existe la sesión {session_id}.")
            if session is None:
                return {"message": "No hay sesiones de estudio registradas.", "session": None, "timer": None}
            return _session_payload(store, session)

        output = _result(action, run)
        audit.mark("tool_dispatch_finished")
        audit.mark("core_program_finished")
        audit.increment("number_of_tool_calls")
        succeeded = '"ok": true' in output
        audit.finish(success=succeeded, error=None if succeeded else RuntimeError("FastPathActionFailed"))
        return output
    return handle


_TOOLS = {
    "study_timer_start": {
        "description": "Start a local countdown inside the current study session, or create one if needed. Multiple timer rounds stay in the same session. Use for 'poneme 20 minutos', 'iniciá un timer' or 'timer de estudio'. Pass the conversation subject; when omitted, infer only if exactly one active subject exists. Do not use cron/reminders.",
        "properties": {
            "duration_minutes": {"type": "integer", "minimum": 1, "description": "Countdown duration in whole minutes."},
            "subject": {"type": "string", "description": "Existing active study subject; use current conversation subject."},
            "topic": {"type": "string", "description": "Optional current study topic."},
        }, "required": ["duration_minutes"],
    },
    "study_timer_pause": {"description": "Pause only the current local countdown; keep its study session open. Do not use cron/reminders.", "properties": {}, "required": []},
    "study_timer_resume": {"description": "Resume the paused local countdown without creating a new study session. Do not use cron/reminders.", "properties": {}, "required": []},
    "study_timer_stop": {"description": "Stop only the current local countdown; keep the study session open. Do not use cron/reminders.", "properties": {"session_id": {"type": "integer", "minimum": 1}}, "required": []},
    "study_session_start": {
        "description": "Start a new persisted study session for an existing subject. Any open session is checkpointed and closed first. Defaults: 75 target and 90 minute hard limit. No reminders are scheduled.",
        "properties": {
            "subject": {"type": "string", "description": "Exact name of an existing active subject."},
            "topic": {"type": "string", "description": "Optional current topic, saved as a checkpoint."},
            "target_minutes": {"type": "integer", "minimum": 1, "default": 75},
            "hard_limit_minutes": {"type": "integer", "minimum": 1, "default": 90},
        }, "required": ["subject"],
    },
    "study_session_end": {
        "description": "End the active study session and persist its final state. Use completed by default, or cancelled if the user cancels.",
        "properties": {
            "session_id": {"type": "integer", "minimum": 1},
            "status": {"type": "string", "enum": ["completed", "cancelled"], "default": "completed"},
        }, "required": [],
    },
    "study_session_status": {
        "description": "Return the current study session and local timer state without artifacts or subprocesses.",
        "properties": {"session_id": {"type": "integer", "minimum": 1}}, "required": [],
    },
}


def register(ctx):
    for name, definition in _TOOLS.items():
        schema = {
            "name": name,
            "description": definition["description"],
            "parameters": {
                "type": "object",
                "properties": definition["properties"],
                "required": definition["required"],
                "additionalProperties": False,
            },
        }
        # Hermes keeps project-scoped plugin tools on its eager desktop surface; other plugin
        # toolsets go through the deferred tool_search bridge.
        ctx.register_tool(name=name, toolset="project", schema=schema,
                          handler=_handler(name), emoji="⏱️")
    ctx.register_command(
        "study-timer", handler=_timer_command,
        description="Controla el timer de estudio sin pasar por el modelo.",
        args_hint="<minutos|pausa|reanudar|detener|estado>",
    )


def _timer_command(raw: str = ""):
    value = raw.strip().lower()
    if value in {"pausa", "pause"}:
        return _handler("study_timer_pause")({})
    if value in {"reanudar", "resume"}:
        return _handler("study_timer_resume")({})
    if value in {"detener", "stop"}:
        return _handler("study_timer_stop")({})
    if value in {"estado", "status", ""}:
        return _handler("study_session_status")({})
    token = value.removesuffix("min").removesuffix("m").strip()
    if not token.isdigit() or int(token) < 1:
        return "Usá /study-timer 25, /study-timer pausa, reanudar, detener o estado."
    store = _core()
    session = store.get_active_session() or store.get_latest_session("paused")
    if session:
        subject = store.get_subject_by_name(
            store.get_session(session["id"])["subject_name"]
        )
    else:
        subjects = store.list_subjects()
        if len(subjects) != 1:
            return "Iniciá una sesión o dejá una sola materia activa para usar /study-timer <minutos>."
        subject = subjects[0]
    return _handler("study_timer_start")({
        "duration_minutes": int(token), "subject": subject["name"],
    })
