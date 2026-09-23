"""Small command-line adapter for manual use and Hermes skills."""

import argparse
import json
import sqlite3
import sys

import study_store as store


def _subject_id(name: str) -> int:
    subject = store.get_subject_by_name(name)
    if subject is None:
        raise store.NotFoundError(f"No existe la materia: {name}")
    return subject["id"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operaciones locales del Study Agent")
    groups = parser.add_subparsers(dest="group", required=True)

    subjects = groups.add_parser("subjects")
    subject_commands = subjects.add_subparsers(dest="action", required=True)
    add = subject_commands.add_parser("add")
    add.add_argument("name")
    add.add_argument("--type")
    listing = subject_commands.add_parser("list")
    listing.add_argument("--all", action="store_true")

    doubts = groups.add_parser("doubts")
    doubt_commands = doubts.add_subparsers(dest="action", required=True)
    add = doubt_commands.add_parser("add")
    add.add_argument("subject")
    add.add_argument("text")
    for action in ("pending", "list"):
        query = doubt_commands.add_parser(action)
        query.add_argument("--subject")
        if action == "list":
            query.add_argument("--status", choices=sorted(store.DOUBT_STATUSES))

    sessions = groups.add_parser("session")
    session_commands = sessions.add_subparsers(dest="action", required=True)
    start = session_commands.add_parser("start")
    start.add_argument("subject")
    start.add_argument("--target-minutes", required=True, type=int)
    start.add_argument("--hard-limit-minutes", required=True, type=int)
    for action in ("pause", "resume", "close", "checkpoint", "show"):
        command = session_commands.add_parser(action)
        command.add_argument("session_id", type=int)
        if action == "close":
            command.add_argument("--status", choices=("completed", "cancelled"), default="completed")
        if action == "checkpoint":
            for field in ("current-topic", "current-source", "current-exercise", "current-step", "next-action"):
                command.add_argument(f"--{field}")
    restore = session_commands.add_parser("restore")
    restore.add_argument("subject")
    return parser


def _run(args: argparse.Namespace):
    if args.group == "subjects":
        if args.action == "add":
            return store.add_subject(args.name, args.type)
        return store.list_subjects(active_only=not args.all)

    if args.group == "doubts":
        if args.action == "add":
            return store.add_doubt(_subject_id(args.subject), args.text)
        subject_id = _subject_id(args.subject) if args.subject else None
        status = "pending" if args.action == "pending" else args.status
        return store.list_doubts(subject_id=subject_id, status=status)

    if args.action == "start":
        return store.start_session(
            _subject_id(args.subject), args.target_minutes, args.hard_limit_minutes
        )
    if args.action == "restore":
        subject_id = _subject_id(args.subject)
        checkpoint = store.get_latest_checkpoint_for_subject(subject_id)
        return {
            "session": store.get_session(checkpoint["session_id"]) if checkpoint else None,
            "checkpoint": checkpoint,
        }
    if args.action == "show":
        session = store.get_session(args.session_id)
        if session is None:
            raise store.NotFoundError(f"No existe la sesión con id {args.session_id}.")
        return session
    if args.action == "pause":
        return store.pause_session(args.session_id)
    if args.action == "resume":
        return store.resume_session(args.session_id)
    if args.action == "close":
        return store.close_session(args.session_id, args.status)
    return store.create_checkpoint(
        args.session_id,
        current_topic=args.current_topic,
        current_source=args.current_source,
        current_exercise=args.current_exercise,
        current_step=args.current_step,
        next_action=args.next_action,
    )


def main() -> int:
    try:
        result = _run(_parser().parse_args())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (store.StudyStoreError, ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
