"""RapidAPI "TennisApi" (tennisapi1.p.rapidapi.com) adapter.

This RapidAPI listing mirrors SofaScore's event endpoints, so the shape is
SofaScore's /event/{id}/point-by-point: {"pointByPoint": [{"set": n,
"games": [{"game": n, "score": {"serving": 1|2, "scoring": 1|2},
"points": [{"homePoint": "15", "awayPoint": "0"}, ...]}]}]}. Sets and games
arrive newest first. Not yet verified against a live response (host blocked
from the cloud network).
"""

from .schema import NormalizedMatch, Point

_TENNIS_SCORE = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4}


def _val(raw: str, tiebreak: bool) -> int:
    return int(raw) if tiebreak else _TENNIS_SCORE[raw]


def parse_point_by_point(payload: dict, match_id: str = "", players: tuple[str, str] = ("home", "away"),
                         surface: str | None = None) -> NormalizedMatch:
    match = NormalizedMatch(match_id=match_id, players=players, surface=surface)
    for s in sorted(payload.get("pointByPoint", []), key=lambda x: x["set"]):
        for g in sorted(s.get("games", []), key=lambda x: x["game"]):
            server = g["score"]["serving"] - 1
            game_winner = g["score"]["scoring"] - 1
            pts = g.get("points") or []
            tiebreak = g["game"] == 13 or any(
                p["homePoint"] not in _TENNIS_SCORE or p["awayPoint"] not in _TENNIS_SCORE for p in pts
            )
            prev = (0, 0)
            for i, p in enumerate(pts):
                srv = server
                if tiebreak:
                    srv = server if ((i + 1) // 2) % 2 == 0 else 1 - server
                if i == len(pts) - 1:
                    w = game_winner
                else:
                    cur = (_val(p["homePoint"], tiebreak), _val(p["awayPoint"], tiebreak))
                    w = 0 if (cur[0] > prev[0] or cur[1] < prev[1]) else 1
                    prev = cur
                match.points.append(Point(s["set"], g["game"], srv, w, tiebreak))
    return match
