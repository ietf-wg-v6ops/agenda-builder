import os

import pytest

from build_agenda import (
    format_duration,
    extract_draft_url,
    parse_csv_rows,
    split_sections,
    compute_local_time_window,
    fetch_meeting_timezone,
    fetch_group_session,
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


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_meeting_timezone(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert params == {"number": 126, "format": "json"}
        return _FakeResponse({"objects": [{"time_zone": "Asia/Shanghai"}]})

    monkeypatch.setattr("build_agenda.requests.get", fake_get)
    assert fetch_meeting_timezone(126) == "Asia/Shanghai"


def test_fetch_meeting_timezone_not_found(monkeypatch):
    monkeypatch.setattr(
        "build_agenda.requests.get",
        lambda url, params=None, timeout=None: _FakeResponse({"objects": []}),
    )
    with pytest.raises(ValueError):
        fetch_meeting_timezone(999)


def test_fetch_group_session_found(monkeypatch):
    payload = {
        "126": [
            {
                "objtype": "session",
                "group": {"acronym": "v6ops", "name": "IPv6 Operations"},
                "location": "Grand Ballroom 1",
                "start": "2026-03-16T01:00:00Z",
                "duration": "2:00:00",
            },
            {
                "objtype": "session",
                "group": {"acronym": "srv6ops", "name": "SRv6 Operations"},
                "location": "Shangri-la Ballroom 2",
                "start": "2026-03-20T03:30:00Z",
                "duration": "1:00:00",
            },
        ]
    }

    def fake_get(url, timeout=None):
        assert url == "https://datatracker.ietf.org/meeting/126/agenda.json"
        return _FakeResponse(payload)

    monkeypatch.setattr("build_agenda.requests.get", fake_get)
    session = fetch_group_session(126, "v6ops")
    assert session["location"] == "Grand Ballroom 1"
    assert session["group"]["name"] == "IPv6 Operations"


def test_fetch_group_session_not_found(monkeypatch):
    monkeypatch.setattr(
        "build_agenda.requests.get",
        lambda url, timeout=None: _FakeResponse({"126": []}),
    )
    with pytest.raises(ValueError):
        fetch_group_session(126, "v6ops")


from build_agenda import render_agenda, render_bullet


def test_render_bullet_with_url():
    row = {
        "topic": "IPv6 CE Router (7084bis)",
        "presenter": "Tim Winters",
        "duration": "10m",
        "url": "https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc7084bis/",
        "adopted": True,
    }
    assert render_bullet(row) == (
        "* IPv6 CE Router (7084bis), Tim Winters, 10m\n"
        "  Draft: [https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc7084bis/]"
        "(https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc7084bis/)"
    )


def test_render_bullet_without_url():
    row = {
        "topic": "CGNATs: early observations",
        "presenter": "Marwan Fayed",
        "duration": "10m",
        "url": None,
        "adopted": False,
    }
    assert render_bullet(row) == "* CGNATs: early observations, Marwan Fayed, 10m"


def test_render_agenda_full_document():
    wg_rows = [
        {
            "topic": "Stateful NAT64",
            "presenter": "Jordi Palet",
            "duration": "10m",
            "url": "https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/",
            "adopted": True,
        }
    ]
    individual_rows = [
        {
            "topic": "Enhanced Dual Stack",
            "presenter": "Xipeng Xiao",
            "duration": "15m",
            "url": None,
            "adopted": False,
        }
    ]
    doc = render_agenda(
        group_name="IPv6 Operations",
        group_acronym="v6ops",
        meeting=126,
        session_id=35105,
        weekday="Mon",
        start="9:00",
        end="11:00",
        location="Grand Ballroom 1",
        minute_taker="Jane Doe",
        chairs_item="Chairs Opening and WG status, 10m",
        wg_rows=wg_rows,
        individual_rows=individual_rows,
    )
    assert doc == (
        "# IPv6 Operations (v6ops) - IETF 126 Agenda\n"
        "\n"
        "Mon. 9:00-11:00, Grand Ballroom 1\n"
        "\n"
        "[Meetecho (Full Client)](https://meetings.conf.meetecho.com/ietf126/?session=35105)\n"
        "[Meetecho (Onsite Tool)](https://meetings.conf.meetecho.com/onsite126/?session=35105)\n"
        "\n"
        "Minute taker: Jane Doe\n"
        "\n"
        "* Chairs Opening and WG status, 10m\n"
        "\n"
        "## WG Drafts\n"
        "\n"
        "* Stateful NAT64, Jordi Palet, 10m\n"
        "  Draft: [https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/]"
        "(https://datatracker.ietf.org/doc/draft-ietf-v6ops-rfc6146-bis/)\n"
        "\n"
        "## Individual Drafts\n"
        "\n"
        "* Enhanced Dual Stack, Xipeng Xiao, 15m\n"
    )


def test_render_agenda_omits_empty_section():
    doc = render_agenda(
        group_name="IPv6 Operations",
        group_acronym="v6ops",
        meeting=126,
        session_id=35105,
        weekday="Mon",
        start="9:00",
        end="11:00",
        location="Grand Ballroom 1",
        minute_taker="TBD",
        chairs_item="Chairs Opening and WG status, 10m",
        wg_rows=[],
        individual_rows=[],
    )
    assert "## WG Drafts" not in doc
    assert "## Individual Drafts" not in doc


from build_agenda import main


def test_main_end_to_end(monkeypatch, tmp_path):
    def fake_get(url, params=None, timeout=None):
        if "meeting/meeting" in url:
            return _FakeResponse({"objects": [{"time_zone": "Asia/Shanghai"}]})
        assert url == "https://datatracker.ietf.org/meeting/126/agenda.json"
        return _FakeResponse(
            {
                "126": [
                    {
                        "objtype": "session",
                        "group": {"acronym": "v6ops", "name": "IPv6 Operations"},
                        "location": "Grand Ballroom 1",
                        "start": "2026-03-16T01:00:00Z",
                        "duration": "2:00:00",
                        "session_id": 35105,
                    }
                ]
            }
        )

    monkeypatch.setattr("build_agenda.requests.get", fake_get)

    output_path = tmp_path / "out.md"
    exit_code = main(
        [
            "--csv",
            FIXTURE_CSV,
            "--meeting",
            "126",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    content = output_path.read_text(encoding="utf-8")
    assert content.startswith("# IPv6 Operations (v6ops) - IETF 126 Agenda\n")
    assert "Mon. 9:00-11:00, Grand Ballroom 1" in content
    assert (
        "[Meetecho (Full Client)](https://meetings.conf.meetecho.com/ietf126/?session=35105)"
        in content
    )
    assert (
        "[Meetecho (Onsite Tool)](https://meetings.conf.meetecho.com/onsite126/?session=35105)"
        in content
    )
    assert "Minute taker: TBD" in content
    assert "## WG Drafts" in content
    assert "## Individual Drafts" in content


def test_main_errors_on_unscheduled_session(monkeypatch, tmp_path, capsys):
    def fake_get(url, params=None, timeout=None):
        if "meeting/meeting" in url:
            return _FakeResponse({"objects": [{"time_zone": "Asia/Shanghai"}]})
        return _FakeResponse({"126": []})

    monkeypatch.setattr("build_agenda.requests.get", fake_get)

    exit_code = main(
        [
            "--csv",
            FIXTURE_CSV,
            "--meeting",
            "126",
            "--output",
            str(tmp_path / "out.md"),
        ]
    )
    assert exit_code == 1
    assert "No scheduled v6ops session" in capsys.readouterr().err


def test_main_errors_on_session_missing_start_key(monkeypatch, tmp_path, capsys):
    def fake_get(url, params=None, timeout=None):
        if "meeting/meeting" in url:
            return _FakeResponse({"objects": [{"time_zone": "Asia/Shanghai"}]})
        return _FakeResponse(
            {
                "126": [
                    {
                        "objtype": "session",
                        "group": {"acronym": "v6ops", "name": "IPv6 Operations"},
                        "location": "Grand Ballroom 1",
                        "duration": "2:00:00",
                    }
                ]
            }
        )

    monkeypatch.setattr("build_agenda.requests.get", fake_get)

    exit_code = main(
        [
            "--csv",
            FIXTURE_CSV,
            "--meeting",
            "126",
            "--output",
            str(tmp_path / "out.md"),
        ]
    )
    assert exit_code == 1
    assert capsys.readouterr().err.startswith("Error: ")
