"""api-tennis.com adapter.

Shape (from the provider's public docs; not yet verified against a live
response because the cloud network blocks the host): each fixture has
"pointbypoint", a list of games with "set_number" ("Set 1"), "number_game",
"player_served" ("First Player"/"Second Player"), "serve_winner", and
"points" whose "score" is "first - second" after the point ("15 - 0",
"A - 40", or "3 - 2" inside a tiebreak).
"""

from .schema import NormalizedMatch, Point

_SIDE = {"First Player": 0, "Second Player": 1}
_TENNIS_SCORE = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4}


def _score(raw: str, tiebreak: bool) -> tuple[int, int]:
    a, b = (s.strip() for s in raw.split("-"))
    if tiebreak:
        return int(a), int(b)
    return _TENNIS_SCORE[a], _TENNIS_SCORE[b]


def _point_winner(prev: tuple[int, int], cur: tuple[int, int]) -> int:
    # Advantage lost goes A-40 -> 40-40, so a drop on one side is a point to the other.
    if cur[0] > prev[0] or cur[1] < prev[1]:
        return 0
    if cur[1] > prev[1] or cur[0] < prev[0]:
        return 1
    raise ValueError(f"score did not change: {prev} -> {cur}")


def parse_match(fixture: dict) -> NormalizedMatch:
    players = (fixture["event_first_player"], fixture["event_second_player"])
    match = NormalizedMatch(
        match_id=str(fixture["event_key"]),
        players=players,
        surface=(fixture.get("surface") or None),
    )
    for game in fixture.get("pointbypoint", []):
        set_no = int(str(game["set_number"]).replace("Set", "").strip())
        game_no = int(game["number_game"])
        server = _SIDE[game["player_served"]]
        winner = _SIDE[game["serve_winner"]]
        pts = game.get("points") or []
        # Tiebreak points are scored 1, 2, 3... which never appear in a regular game.
        tiebreak = game_no == 13 or any(
            x.strip() not in _TENNIS_SCORE for p in pts for x in p["score"].split("-")
        )
        prev = (0, 0)
        for i, p in enumerate(pts):
            if tiebreak:
                # Tiebreak serve rotation: S, R, R, S, S, ...
                srv = server if ((i + 1) // 2) % 2 == 0 else 1 - server
            else:
                srv = server
            if i == len(pts) - 1:
                w = winner  # the game-winning point often carries the game score, not a point score
            else:
                cur = _score(p["score"], tiebreak)
                w = _point_winner(prev, cur)
                prev = cur
            match.points.append(Point(set_no, game_no, srv, w, tiebreak))
    return match
