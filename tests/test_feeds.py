import json
import random
from pathlib import Path

from boom.tennis.feeds import api_tennis, profile_stats_from_matches, sofascore_rapidapi
from boom.tennis.montecarlo import _constant, simulate_match
from boom.tennis.rules import MatchFormat

FIX = Path(__file__).parent / "fixtures"


def test_api_tennis_fixture():
    fx = json.loads((FIX / "api_tennis_fixture.json").read_text())["result"][0]
    m = api_tennis.parse_match(fx)
    assert m.players == ("Player One", "Player Two")
    assert len(m.points) == 25
    g2 = [p for p in m.points if p.game_no == 2]
    # Deuce game: 0-15, 15-15, 30-15, 30-30, 30-40, deuce, ad out, deuce, ad in, game.
    assert [p.winner for p in g2] == [1, 0, 0, 1, 1, 0, 1, 0, 0, 0]
    tb = [p for p in m.points if p.game_no == 13]
    assert all(p.tiebreak for p in tb)
    assert [p.server for p in tb[:5]] == [0, 1, 1, 0, 0]
    assert tb[-1].winner == 1
    a, b = m.serve_stats()
    assert a.serve_played + b.serve_played == 25


def test_rapidapi_fixture_orders_games():
    payload = json.loads((FIX / "rapidapi_tennisapi_pbp.json").read_text())
    m = sofascore_rapidapi.parse_point_by_point(payload, "1", ("H", "A"), "hard")
    assert [p.game_no for p in m.points] == [1] * 5 + [2] * 5
    assert m.set_scores() == [(1, 1)]
    h, a = m.serve_stats()
    assert (h.serve_won, h.serve_played) == (4, 5)
    assert (a.serve_won, a.serve_played) == (4, 5)


_SCORE = ["0", "15", "30", "40"]


def _game_score(a, b, tiebreak):
    if tiebreak:
        return f"{a} - {b}"
    if a >= 3 and b >= 3:
        if a == b:
            return "40 - 40"
        return "A - 40" if a > b else "40 - A"
    return f"{_SCORE[min(a, 3)]} - {_SCORE[min(b, 3)]}"


def _to_api_tennis(sim):
    """Serialize a simulated match in api-tennis.com's point-by-point shape."""
    games = {}
    for set_no, game_no, server_a, a_won, tb in sim.log:
        games.setdefault((set_no, game_no), []).append((server_a, a_won, tb))
    pbp = []
    for (set_no, game_no), pts in games.items():
        a = b = 0
        rows = []
        for i, (_s, a_won, tb) in enumerate(pts):
            a, b = (a + 1, b) if a_won else (a, b + 1)
            rows.append({"number_point": str(i + 1), "score": _game_score(a, b, tb)})
        first_server_a = pts[0][0]
        pbp.append({
            "set_number": f"Set {set_no}",
            "number_game": str(game_no),
            "player_served": "First Player" if first_server_a else "Second Player",
            "serve_winner": "First Player" if pts[-1][1] else "Second Player",
            "points": rows,
        })
    return {"event_key": 1, "event_first_player": "A", "event_second_player": "B",
            "surface": "hard", "pointbypoint": pbp}


def test_round_trip_simulated_match():
    rng = random.Random(3)
    for _ in range(20):
        sim = simulate_match(MatchFormat(3), rng, _constant(0.64, 0.60), rng.random() < 0.5, record=True)
        m = api_tennis.parse_match(_to_api_tennis(sim))
        assert [(p.server == 0, p.winner == 0) for p in m.points] == [(s, w) for _, _, s, w, _ in sim.log]
        assert m.set_scores() == sim.set_scores
        profiles = profile_stats_from_matches([m])
        assert profiles["A"].by_surface["hard"].serve_played + profiles["B"].by_surface["hard"].serve_played == len(sim.log)
