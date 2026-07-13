import os

import pytest

from build_agenda import (
    format_duration,
    extract_draft_url,
    parse_csv_rows,
    split_sections,
    compute_local_time_window,
)


def test_format_duration_minutes():
    assert format_duration("10 minutes") == "10m"


def test_format_duration_other_phrasing():
    assert format_duration("15 minutes") == "15m"


def test_format_duration_no_digits_raises():
    with pytest.raises(ValueError):
        format_duration("a while")


def test_extract_draft_url_present():
    url = "https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/"
    assert extract_draft_url(url) == url


def test_extract_draft_url_absent():
    assert extract_draft_url("No draft; only sharing observations") is None


FIXTURE_CSV = os.path.join(os.path.dirname(__file__), "fixtures", "sample.csv")


def test_parse_csv_rows_count_and_fields():
    rows = parse_csv_rows(FIXTURE_CSV)
    assert len(rows) == 4
    first = rows[0]
    assert first["topic"] == (
        "Stateful NAT64: Network Address and Protocol Translation "
        "from IPv6 Clients to IPv4 Servers"
    )
    assert first["presenter"] == "Jordi Palet"
    assert first["duration"] == "10m"
    assert first["url"] == "https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/"
    assert first["adopted"] is True


def test_parse_csv_rows_no_url_row():
    rows = parse_csv_rows(FIXTURE_CSV)
    last = rows[-1]
    assert last["adopted"] is False
    assert last["url"] is None


def test_parse_csv_rows_missing_topic_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    header = (
        "Timestamp,Email Address,"
        "Draft Topic (e.g. Use of the IPv6 Flow Label for WLCG Packet Marking),"
        "Presenter Name (if someone other than requestor),Presenter Email,"
        "URL for Draft,Time slot duration ,Adopted WG Draft?,"
        "Additional notes for chair consideration\n"
    )
    row = "6/25/2026 3:25:25,a@b.com,,Jordi Palet,a@b.com,https://example.com/,10 minutes,Yes,\n"
    bad_csv.write_text(header + row, encoding="utf-8")
    with pytest.raises(ValueError):
        parse_csv_rows(str(bad_csv))


def test_split_sections():
    rows = parse_csv_rows(FIXTURE_CSV)
    wg_rows, individual_rows = split_sections(rows)
    assert [r["topic"] for r in wg_rows] == [
        "Stateful NAT64: Network Address and Protocol Translation "
        "from IPv6 Clients to IPv4 Servers",
        "IPv6 CE Router (7084bis)",
    ]
    assert [r["topic"] for r in individual_rows] == [
        "Enhanced Dual Stack: Selecting IPv6/IPv4 based on Performance",
        "CGNATs: early observations from a CDN about performance, and prevalence in v6 networks",
    ]


def test_compute_local_time_window_shanghai_no_leading_zero():
    weekday, start, end = compute_local_time_window(
        "2026-03-16T01:00:00Z", "2:00:00", "Asia/Shanghai"
    )
    assert (weekday, start, end) == ("Mon", "9:00", "11:00")


def test_compute_local_time_window_two_digit_hour():
    weekday, start, end = compute_local_time_window(
        "2026-03-16T05:00:00Z", "1:30:00", "Asia/Shanghai"
    )
    assert (weekday, start, end) == ("Mon", "13:00", "14:30")


def test_compute_local_time_window_dst_crossing():
    # Spring-forward DST transition on 2026-03-08 in America/New_York.
    # start_utc = 2026-03-08T06:00:00Z (1:00 AM EST, before transition)
    # end_utc = 2026-03-08T08:00:00Z (4:00 AM EDT, after 2:00 AM -> 3:00 AM jump)
    # Wall-clock duration: 1:00 AM -> 4:00 AM = 3 hours (1 hour offset by DST)
    weekday, start, end = compute_local_time_window(
        "2026-03-08T06:00:00Z", "2:00:00", "America/New_York"
    )
    assert (weekday, start, end) == ("Sun", "1:00", "4:00")
