import pytest
# tests/test_utils.py
import pytest
from cogs.draft_commands import parse_riot_id, parse_winrate


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