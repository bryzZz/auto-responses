from __future__ import annotations

import argparse

from app.core.workflow import ApplicationWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-responses",
        description="Console-first MVP for automated job applications.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan hh.ru and print matching vacancies.")
    scan.add_argument("--limit", type=int, default=10, help="Maximum number of jobs to print.")

    login = subparsers.add_parser("login", help="Open hh.ru in a persistent browser for manual login.")
    login.add_argument(
        "--url",
        default="https://hh.ru/",
        help="Initial URL to open before waiting for manual login.",
    )

    draft = subparsers.add_parser("draft", help="Generate a cover letter draft for the first match.")
    draft.add_argument("--limit", type=int, default=10, help="Maximum number of jobs to inspect.")

    apply_cmd = subparsers.add_parser("apply", help="Generate a draft and start the apply flow.")
    apply_cmd.add_argument("--limit", type=int, default=10, help="Maximum number of jobs to inspect.")
    apply_cmd.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Skip terminal confirmation before apply.",
    )

    return parser


def run() -> None:
    parser = build_parser()
    args = parser.parse_args()
    workflow = ApplicationWorkflow.from_default_paths()

    if args.command == "scan":
        workflow.scan(limit=args.limit)
        return

    if args.command == "login":
        workflow.login(initial_url=args.url)
        return

    if args.command == "draft":
        workflow.draft(limit=args.limit)
        return

    if args.command == "apply":
        workflow.apply(limit=args.limit, auto_confirm=args.auto_confirm)
        return

    parser.error(f"Unsupported command: {args.command}")
