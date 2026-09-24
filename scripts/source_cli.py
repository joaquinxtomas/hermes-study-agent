"""Command-line operations for registering, ingesting and searching sources."""

import argparse
import json
import sqlite3
import sys

import source_ingest
import source_search
import source_store
import study_store


def _subject_id(name: str) -> int:
    subject = study_store.get_subject_by_name(name)
    if subject is None:
        raise study_store.NotFoundError(f"No existe la materia: {name}")
    return subject["id"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Administrar materiales de estudio locales")
    groups = parser.add_subparsers(dest="command", required=True)

    topic = groups.add_parser("add-topic")
    topic.add_argument("--subject", required=True)
    topic.add_argument("--name", required=True)
    topic.add_argument("--parent-topic-id", type=int)

    register = groups.add_parser("register-source")
    register.add_argument("--subject", required=True)
    register.add_argument("--title", required=True)
    register.add_argument("--type", required=True, choices=sorted(source_store.SOURCE_TYPES))
    register.add_argument("--path", required=True)
    register.add_argument("--topic-id", type=int)
    register.add_argument("--author")

    listing = groups.add_parser("list-sources")
    listing.add_argument("--subject")
    listing.add_argument("--topic-id", type=int)
    listing.add_argument("--all", action="store_true")

    ingest = groups.add_parser("ingest-source")
    ingest.add_argument("source_id", type=int)

    search = groups.add_parser("search-source")
    search.add_argument("query")
    search.add_argument("--source-id", type=int)
    search.add_argument("--subject")
    search.add_argument("--topic-id", type=int)
    search.add_argument("--limit", type=int, default=5)
    return parser


def _run(args: argparse.Namespace):
    if args.command == "add-topic":
        return source_store.add_topic(_subject_id(args.subject), args.name, args.parent_topic_id)
    if args.command == "register-source":
        return source_store.add_source(
            _subject_id(args.subject), args.title, args.type, args.path,
            topic_id=args.topic_id, author=args.author,
        )
    if args.command == "list-sources":
        subject_id = _subject_id(args.subject) if args.subject else None
        return source_store.list_sources(
            subject_id=subject_id, topic_id=args.topic_id, active_only=not args.all
        )
    if args.command == "ingest-source":
        return source_ingest.ingest_source(args.source_id)
    subject_id = _subject_id(args.subject) if args.subject else None
    return source_search.search_sources(
        args.query, source_id=args.source_id, subject_id=subject_id,
        topic_id=args.topic_id, limit=args.limit,
    )


def main() -> int:
    try:
        print(json.dumps(_run(_parser().parse_args()), ensure_ascii=False, indent=2))
        return 0
    except (study_store.StudyStoreError, ValueError, FileNotFoundError,
            RuntimeError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
