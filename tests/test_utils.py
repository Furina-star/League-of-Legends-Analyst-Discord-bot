"""
This is where to test everything that doesn't fit in the other test files, such as the parsing functions for the draft commands.
"""

import pytest
from cogs.draft_commands import parse_riot_id, parse_winrate, sort_team_roles


def test_parse_riot_id():
    # Test perfect formatting
    assert parse_riot_id("Hide on bush#KR1") == ("Hide on bush", "KR1")

    # Test space formatting
    assert parse_riot_id("Faker KR1") == ("Faker", "KR1")

    # Test missing tag
    assert parse_riot_id("JustAName") == (None, None)

    # Test too long
    assert parse_riot_id("ThisNameIsWayTooLongToActuallyBeReal#12345") == (None, None)


def test_parse_winrate():
    # Test standard format
    assert parse_winrate("Gold II (45 LP) | **55.5% WR** (100 games)") == pytest.approx(55.5)

    # Test whole numbers
    assert parse_winrate("Silver I | **60% WR**") == pytest.approx(60.0)

    # Test unranked
    assert parse_winrate("Unranked") == pytest.approx(50.0)
    assert parse_winrate(None) == pytest.approx(50.0)


def test_sort_team_roles():
    # Create fake data for the test
    fake_meta_db = {"KNOWN_TOPS": ["Sion"], "PURE_ADCS": ["Jinx"]}
    fake_champ_dict = {"1": "Sion", "2": "Jinx", "3": "Ahri", "4": "Lee Sin", "5": "Leona"}

    # Create a fake team of 5 players
    fake_team = [
        {"championId": 1, "spell1Id": 4, "spell2Id": 12},  # Top
        {"championId": 2, "spell1Id": 4, "spell2Id": 7},  # ADC
        {"championId": 3, "spell1Id": 4, "spell2Id": 14},  # Mid
        {"championId": 4, "spell1Id": 11, "spell2Id": 4},  # Jungle, especially Smite (11) should be a dead giveaway
        {"championId": 5, "spell1Id": 4, "spell2Id": 3}  # Support
    ]

    roles = sort_team_roles(fake_team, fake_champ_dict, fake_meta_db)

    # It should successfully figure out the Jungle because of Smite (spell 11)
    assert roles[1] == "Lee Sin"