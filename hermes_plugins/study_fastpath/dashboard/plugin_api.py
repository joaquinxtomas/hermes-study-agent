"""Local Hermes Desktop API for the persistent study timer panel."""

from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import study_store

router = APIRouter()


def _session():
    return study_store.get_active_session() or study_store.get_latest_session("paused")


@router.get("/timer")
async def timer_state():
    session = _session()
    return {
        "session": study_store.get_session(session["id"]) if session else None,
        "timer": study_store.get_current_study_timer(session["id"]) if session else None,
    }


class TimerAction(BaseModel):
    action: str
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)


@router.post("/timer/action")
async def timer_action(request: TimerAction):
    try:
        session = _session()
        if request.action == "start":
            if session is None or session["status"] != "active":
                raise study_store.StudyStoreError("Iniciá una sesión de estudio antes del timer.")
            if request.duration_minutes is None:
                raise ValueError("Indicá una duración en minutos.")
            timer = study_store.start_study_timer(session["id"], request.duration_minutes)
        elif request.action == "pause":
            timer = study_store.pause_study_timer(session["id"] if session else None)
        elif request.action == "resume":
            timer = study_store.resume_study_timer(session["id"] if session else None)
        elif request.action == "stop":
            timer = study_store.stop_study_timer(session["id"] if session else None)
        elif request.action == "end_session":
            if session is None:
                raise study_store.StudyStoreError("No hay una sesión abierta.")
            study_store.close_session(session["id"])
            timer = None
        elif request.action == "pause_session":
            if session is None:
                raise study_store.StudyStoreError("No hay una sesión abierta.")
            study_store.pause_session(session["id"])
            timer = study_store.get_current_study_timer(session["id"])
        elif request.action == "resume_session":
            if session is None:
                raise study_store.StudyStoreError("No hay una sesión abierta.")
            study_store.resume_session(session["id"])
            timer = study_store.get_current_study_timer(session["id"])
        else:
            raise ValueError("Acción de timer no reconocida.")
        session_id = timer["session_id"] if timer else (session["id"] if session else None)
        current = study_store.get_session(session_id) if session_id else None
        return {"session": current, "timer": timer or (
            study_store.get_current_study_timer(session_id) if session_id else None
        )}
    except (ValueError, study_store.StudyStoreError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
