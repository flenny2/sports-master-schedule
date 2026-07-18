"""Tests for app/fantasy.py — the my-guys crossover tagger (brief D5)."""

import config
from app.fantasy import tag_my_guys


def _nfl_game(home_abbr, away_abbr):
    return {
        "sport": "football",
        "home_team": {"abbreviation": home_abbr},
        "away_team": {"abbreviation": away_abbr},
    }


def test_empty_roster_tags_empty_lists(monkeypatch):
    monkeypatch.setattr(config, "FANTASY_ROSTER", {})
    games = tag_my_guys([_nfl_game("PIT", "BAL")])
    assert games[0]["my_guys"] == []


def test_players_matched_to_both_sides(monkeypatch):
    monkeypatch.setattr(config, "FANTASY_ROSTER", {
        "Josh Jacobs": "GB",
        "Amon-Ra St. Brown": "DET",
        "Bench Guy": "MIA",
    })
    games = tag_my_guys([_nfl_game("DET", "GB")])
    # Away-side players listed before home-side
    assert games[0]["my_guys"] == ["Josh Jacobs", "Amon-Ra St. Brown"]


def test_abbreviation_match_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(config, "FANTASY_ROSTER", {"Some RB": "pit"})
    games = tag_my_guys([_nfl_game("PIT", "CLE")])
    assert games[0]["my_guys"] == ["Some RB"]


def test_non_football_games_get_empty_list(monkeypatch):
    monkeypatch.setattr(config, "FANTASY_ROSTER", {"Some RB": "PIT"})
    soccer = {
        "sport": "soccer",
        "home_team": {"abbreviation": "PIT"},  # coincidental abbrev
        "away_team": {"abbreviation": "ARS"},
    }
    games = tag_my_guys([soccer])
    assert games[0]["my_guys"] == []
