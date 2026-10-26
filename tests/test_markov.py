import pytest

from boom.tennis.markov import game_win_prob, match_distribution, set_distribution, tiebreak_win_prob
from boom.tennis.montecarlo import empirical_distribution, simulate_matches
from boom.tennis.pricing import MarketBook
from boom.tennis.rules import MatchFormat, format_for_event


def test_game_win_prob_known_values():
    assert game_win_prob(0.5) == pytest.approx(0.5)
    # Standard textbook value: a 60% server holds ~73.6% of the time.
    assert game_win_prob(0.6) == pytest.approx(0.7357, abs=1e-4)
    assert game_win_prob(1.0) == pytest.approx(1.0)


@pytest.mark.parametrize("target", [7, 10])
def test_tiebreak_symmetric(target):
    assert tiebreak_win_prob(0.65, 0.65, target) == pytest.approx(0.5)
    assert tiebreak_win_prob(0.65, 0.65, target, a_serves_first=False) == pytest.approx(0.5)
    assert tiebreak_win_prob(0.70, 0.60, target) > 0.5


def test_longer_tiebreak_favors_better_player():
    assert tiebreak_win_prob(0.70, 0.60, 10) > tiebreak_win_prob(0.70, 0.60, 7)


def test_set_distribution_valid():
    d = set_distribution(0.64, 0.61, True)
    assert sum(d.values()) == pytest.approx(1.0)
    assert set(d) <= {(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5), (7, 6),
                      (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 7), (6, 7)}


@pytest.mark.parametrize("fmt", [MatchFormat(3), MatchFormat(5, final_set_tiebreak_target=10)])
def test_match_distribution_sums_and_symmetry(fmt):
    d = match_distribution(0.63, 0.63, fmt)
    assert sum(d.values()) == pytest.approx(1.0)
    assert MarketBook(d).match_win_a() == pytest.approx(0.5)


def test_best_of_five_amplifies_favorite():
    p3 = MarketBook(match_distribution(0.66, 0.62, MatchFormat(3))).match_win_a()
    p5 = MarketBook(match_distribution(0.66, 0.62, MatchFormat(5, final_set_tiebreak_target=10))).match_win_a()
    assert 0.5 < p3 < p5


def test_monte_carlo_agrees_with_exact():
    fmt = MatchFormat(3)
    exact = MarketBook(match_distribution(0.66, 0.62, fmt))
    mc = MarketBook(empirical_distribution(simulate_matches(0.66, 0.62, fmt, n=20_000, seed=7)))
    assert mc.match_win_a() == pytest.approx(exact.match_win_a(), abs=0.015)
    assert mc.mean(mc.total_games()) == pytest.approx(exact.mean(exact.total_games()), abs=0.15)
    assert MarketBook.line(mc.total_games(), 22.5).over == pytest.approx(
        MarketBook.line(exact.total_games(), 22.5).over, abs=0.015)


def test_format_for_event():
    assert format_for_event("atp", grand_slam=True).best_of == 5
    assert format_for_event("wta", grand_slam=True).best_of == 3
    assert format_for_event("atp", grand_slam=False) == MatchFormat(3)
    assert format_for_event("atp", grand_slam=True).final_set_tiebreak_target == 10
