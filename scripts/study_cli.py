"""Small command-line adapter for manual use and Hermes skills."""

import argparse
import json
import sqlite3
import sys

import study_store as store
import knowledge_store
import knowledge_service
import knowledge_rules
import source_store


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
    add.add_argument("--topic-id", type=int)
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
    knowledge = groups.add_parser("knowledge")
    knowledge_commands = knowledge.add_subparsers(dest="action", required=True)
    status = knowledge_commands.add_parser("status")
    status_commands = status.add_subparsers(dest="status_action", required=True)
    show = status_commands.add_parser("show")
    show.add_argument("topic_id", type=int)
    listing = status_commands.add_parser("list")
    listing.add_argument("dimension", choices=sorted(knowledge_rules.DIMENSIONS))
    listing.add_argument("status", choices=sorted(knowledge_rules.STATUSES))
    evidence = knowledge_commands.add_parser("evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_action", required=True)
    evidence_list = evidence_commands.add_parser("list")
    evidence_list.add_argument("topic_id", type=int)
    evidence_list.add_argument("--dimension", choices=sorted(knowledge_rules.DIMENSIONS))
    session_evidence = evidence_commands.add_parser("for-session")
    session_evidence.add_argument("session_id", type=int)
    add = evidence_commands.add_parser("add")
    add.add_argument("topic_id", type=int)
    add.add_argument("dimension")
    add.add_argument("evidence_type")
    add.add_argument("result")
    add.add_argument("details")
    add.add_argument("--session-id", type=int)
    add.add_argument("--doubt-id", type=int)
    add.add_argument("--source-id", type=int)
    topics = knowledge_commands.add_parser("topics")
    topic_commands = topics.add_subparsers(dest="topics_action", required=True)
    topic_list = topic_commands.add_parser("list")
    topic_list.add_argument("--subject")
    misconceptions = knowledge_commands.add_parser("misconceptions")
    misconception_commands = misconceptions.add_subparsers(dest="misconception_action", required=True)
    listing = misconception_commands.add_parser("list")
    listing.add_argument("--topic-id", type=int)
    listing.add_argument("--status", choices=("active", "improving", "resolved"))
    misconception_add = misconception_commands.add_parser("add")
    misconception_add.add_argument("topic_id", type=int)
    misconception_add.add_argument("description")
    resolve = misconception_commands.add_parser("resolve")
    resolve.add_argument("id", type=int)

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
            subject_id = _subject_id(args.subject)
            if args.topic_id is not None:
                topic = next((item for item in source_store.list_topics(subject_id=subject_id) if item["id"] == args.topic_id), None)
                if topic is None:
                    raise ValueError("El topic debe pertenecer a la materia indicada.")
            doubt = store.add_doubt(subject_id, args.text, topic_id=args.topic_id)
            if args.topic_id is not None:
                knowledge_service.record_learning_event(args.topic_id, "conceptual", "doubt", "observed", args.text, doubt_id=doubt["id"])
            return doubt
        subject_id = _subject_id(args.subject) if args.subject else None
        status = "pending" if args.action == "pending" else args.status
        return store.list_doubts(subject_id=subject_id, status=status)

    if args.group == "knowledge":
        if args.action == "topics":
            subject_id = _subject_id(args.subject) if args.subject else None
            return knowledge_store.list_topics(subject_id)
        if args.action == "status":
            if args.status_action == "show":
                return knowledge_service.explain_topic(args.topic_id)
            return knowledge_store.list_topics_by_status(args.dimension, args.status)
        if args.action == "evidence":
            if args.evidence_action == "list":
                return knowledge_store.list_evidence(args.topic_id, args.dimension)
            if args.evidence_action == "for-session":
                return knowledge_store.list_evidence_for_session(args.session_id)
            return knowledge_service.record_learning_event(
                args.topic_id, args.dimension, args.evidence_type, args.result, args.details,
                args.session_id, args.doubt_id, args.source_id,
            )
        if args.misconception_action == "list":
            return knowledge_store.list_misconceptions(args.topic_id, args.status)
        if args.misconception_action == "add":
            return knowledge_store.add_or_update_misconception(args.topic_id, args.description)
        return knowledge_store.resolve_misconception(args.id)

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
    except (store.StudyStoreError, knowledge_store.KnowledgeStoreError, ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
