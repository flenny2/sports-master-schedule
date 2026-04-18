"""Tests for app.availability."""

from app.availability import tag_availability


def _game(iso_date):
    return {"date": iso_date, "availability": None}


def test_weekday_midday_is_unavailable():
    # Monday 2026-04-13 at 19:00 UTC → noon Pacific (inside work hours)
    games = tag_availability([_game("2026-04-13T19:00Z")])
    assert games[0]["availability"] == "will_miss"


def test_weekday_evening_is_available():
    # Monday 2026-04-13 at 03:00 UTC → Sun 8pm Pacific (outside work hours)
    # Use Tue 04:00 UTC → Mon 9pm Pacific instead, unambiguous weekday
    games = tag_availability([_game("2026-04-14T04:00Z")])
    assert games[0]["availability"] == "can_watch"


def test_weekend_is_always_available():
    # Saturday 2026-04-11 at 20:00 UTC → 1pm Pacific, but Saturday is off
    games = tag_availability([_game("2026-04-11T20:00Z")])
    assert games[0]["availability"] == "can_watch"


def test_malformed_date_defaults_to_available():
    games = tag_availability([{"date": "not-a-date", "availability": None}])
    assert games[0]["availability"] == "can_watch"


def test_boundary_hour_6pm_is_available():
    # 6pm is the end_hour (exclusive) → available
    # Monday 2026-04-13 at 01:00 UTC → Sun 6pm Pacific — skip weekday bit
    # Use Tue 2026-04-14 at 01:00 UTC → Mon 6pm Pacific
    games = tag_availability([_game("2026-04-14T01:00Z")])
    assert games[0]["availability"] == "can_watch"
