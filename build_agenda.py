#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Build an IETF WG session agenda markdown file from a call-for-drafts CSV."""

from __future__ import annotations

import re

DURATION_RE = re.compile(r"(\d+)")
URL_RE = re.compile(r"https?://\S+")


def format_duration(raw: str) -> str:
    match = DURATION_RE.search(raw or "")
    if not match:
        raise ValueError(f"Cannot parse a duration from {raw!r}")
    return f"{match.group(1)}m"


def extract_draft_url(raw: str) -> str | None:
    match = URL_RE.search(raw or "")
    return match.group(0) if match else None
