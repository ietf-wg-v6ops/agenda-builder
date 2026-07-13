import pytest

from build_agenda import format_duration, extract_draft_url


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
