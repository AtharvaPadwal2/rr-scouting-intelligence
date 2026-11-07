import pandas as pd
import pytest

from scouting.synthetic import generate_players


def test_seed_is_reproducible():
    pd.testing.assert_frame_equal(generate_players(), generate_players())
    assert not generate_players(seed=7).equals(generate_players())


def test_demo_contains_expected_test_defects():
    frame = generate_players()
    assert frame["player_id"].nunique() == 96
    assert len(frame) == 96 * 3 + 1
    assert frame["source"].eq("synthetic").all()
    assert frame.duplicated().sum() == 1
    assert frame["balls_faced"].isna().sum() == 2  # One missing record plus its duplicate.
    assert frame["runs"].lt(0).sum() == 1
    assert frame["role"].ne(frame["role"].str.strip()).sum() == 1


def test_player_count_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        generate_players(players=0)
