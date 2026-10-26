import pytest

from boom.tennis.markov import Outcome
from boom.tennis.model import PlayerProfile, SurfaceStats, matchup_point_probs, serve_return_rates
from boom.tennis.pricing import MarketBook, breakeven_per_leg, fair_american


def test_handicap_and_lines():
    book = MarketBook({Outcome(2, 0, 12, 5): 0.5, Outcome(2, 1, 15, 13): 0.3, Outcome(1, 2, 14, 16): 0.2})
    assert book.handicap(book.set_spread(), -1.5).over == pytest.approx(0.5)
    assert book.handicap(book.set_spread(), 1.5).over == pytest.approx(1.0)
    assert book.line(book.total_games(), 22.5).over == pytest.approx(0.5)
    tg = book.line(book.total_games(), 28)
    assert (tg.over, tg.push, tg.under) == pytest.approx((0.2, 0.3, 0.5))
    assert book.handicap(book.game_spread(), -3.5).over == pytest.approx(0.5)


def test_odds_helpers():
    assert fair_american(0.5) == -100
    assert fair_american(0.25) == 300
    assert breakeven_per_leg(3.0, 2) == pytest.approx(0.5774, abs=1e-4)


def _player(name, surface, sw, sp, rw, rp):
    return PlayerProfile(name, "atp", {surface: SurfaceStats(sw, sp, rw, rp)})


def test_unknown_player_is_tour_average():
    serve, ret = serve_return_rates(PlayerProfile("nobody"), "clay")
    assert serve == pytest.approx(0.625)
    assert ret == pytest.approx(0.375)


def test_surface_rates_shrink_toward_prior():
    small = _player("a", "grass", 80, 100, 30, 100)  # 80% on 100 points
    serve, _ = serve_return_rates(small, "grass")
    assert 0.665 < serve < 0.70


def test_matchup_adjusts_for_opponent_return():
    server = _player("big server", "hard", 7000, 10000, 3400, 10000)
    good_returner = _player("returner", "hard", 6400, 10000, 4200, 10000)
    weak_returner = _player("weak", "hard", 6400, 10000, 3000, 10000)
    pa_vs_good, _ = matchup_point_probs(server, good_returner, "hard")
    pa_vs_weak, _ = matchup_point_probs(server, weak_returner, "hard")
    assert pa_vs_good < pa_vs_weak
