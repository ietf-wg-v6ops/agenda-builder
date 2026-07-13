#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Build an IETF WG session agenda markdown file from a call-for-drafts CSV."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DURATION_RE = re.compile(r"(\d+)")
URL_RE = re.compile(r"https?://\S+")

REQUIRED_COLUMNS = {
    "topic": "Draft Topic (e.g. Use of the IPv6 Flow Label for WLCG Packet Marking)",
    "presenter": "Presenter Name (if someone other than requestor)",
    "duration": "Time slot duration",
    "url": "URL for Draft",
    "adopted": "Adopted WG Draft?",
}


def format_duration(raw: str) -> str:
    match = DURATION_RE.search(raw or "")
    if not match:
        raise ValueError(f"Cannot parse a duration from {raw!r}")
    return f"{match.group(1)}m"


def extract_draft_url(raw: str) -> str | None:
    match = URL_RE.search(raw or "")
    return match.group(0) if match else None


def parse_csv_rows(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header_by_stripped_name = {
            name.strip(): name for name in (reader.fieldnames or [])
        }

        def get(raw_row: dict, column_key: str) -> str:
            header = REQUIRED_COLUMNS[column_key]
            actual_header = header_by_stripped_name.get(header)
            if actual_header is None:
                raise ValueError(f"CSV is missing required column {header!r}")
            return (raw_row.get(actual_header) or "").strip()

        rows = []
        for line_num, raw_row in enumerate(reader, start=2):
            topic = get(raw_row, "topic")
            presenter = get(raw_row, "presenter")
            if not topic or not presenter:
                raise ValueError(
                    f"Row {line_num}: missing topic or presenter"
                )
            rows.append(
                {
                    "topic": topic,
                    "presenter": presenter,
                    "duration": format_duration(get(raw_row, "duration")),
                    "url": extract_draft_url(get(raw_row, "url")),
                    "adopted": get(raw_row, "adopted").lower() == "yes",
                }
            )
        return rows


def split_sections(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    wg_rows = [r for r in rows if r["adopted"]]
    individual_rows = [r for r in rows if not r["adopted"]]
    return wg_rows, individual_rows


def compute_local_time_window(
    start_utc_iso: str, duration_hms: str, tz_name: str
) -> tuple[str, str, str]:
    start_utc = datetime.fromisoformat(start_utc_iso.replace("Z", "+00:00"))
    hours_str, minutes_str, seconds_str = duration_hms.split(":")
    duration = timedelta(
        hours=int(hours_str), minutes=int(minutes_str), seconds=int(seconds_str)
    )

    tz = ZoneInfo(tz_name)
    end_utc = start_utc + duration
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)

    weekday = start_local.strftime("%a")
    start_str = f"{start_local.hour}:{start_local.minute:02d}"
    end_str = f"{end_local.hour}:{end_local.minute:02d}"
    return weekday, start_str, end_str
