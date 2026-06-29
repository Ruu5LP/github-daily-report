"""Entry point for github-daily-report CLI."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone

from src.config.settings import load_settings
from src.notification.factory import NotifierFactory
from src.report.generator import generate_report
from src.services.collector import DataCollector
from src.utils.logger import logger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="daily-report",
        description="Generate a GitHub daily activity report.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect data and generate report but do not send notification.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the report to stdout regardless of NOTIFY_PROVIDER.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Target date for the report (default: today in JST).",
    )
    return parser.parse_args(argv)


def resolve_date(date_str: str | None) -> date:
    if date_str:
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            logger.error("Invalid date format: %r (expected YYYY-MM-DD)", date_str)
            sys.exit(1)
    # Default: today in JST
    jst = timezone(timedelta(hours=9))
    return datetime.now(tz=jst).date()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    settings = load_settings()
    errors = settings.validate()
    if errors:
        for err in errors:
            logger.error("Configuration error: %s", err)
        sys.exit(1)

    target_date = resolve_date(args.date)
    logger.info("Generating daily report for %s", target_date)

    # Collect data
    collector = DataCollector(settings)
    report = collector.collect(target_date)

    # Generate markdown
    markdown = generate_report(report)

    # Output to stdout if requested
    if args.stdout:
        print(markdown)

    # Send notification unless dry-run
    if args.dry_run:
        logger.info("--dry-run: skipping notification")
        if not args.stdout:
            print(markdown)
        return

    notifier = NotifierFactory.create(settings)
    logger.info("Sending notification via %s", type(notifier).__name__)
    # Skip StdoutNotifier if already printed via --stdout to avoid duplication
    from src.notification.factory import StdoutNotifier

    if args.stdout and isinstance(notifier, StdoutNotifier):
        pass
    else:
        notifier.send(markdown)

    logger.info("Done.")


if __name__ == "__main__":
    main()
