"""Point-by-point Monte Carlo match simulator.

Plays every point under the same rules as markov.py. Kept separate so the
exact engine can be validated against a literal simulation, and so later
work (momentum, fatigue, in-play state) can plug into point_prob without
touching the pricing math.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from .markov import Outcome
from .rules import MatchFormat

# point_prob(server_is_a, state) -> P(server wins the point). The default
# ignores state, which makes the simulation match the exact Markov model.
PointProb = Callable[[bool, dict], float]


@dataclass
class SimulatedMatch:
    outcome: Outcome
    set_scores: list[tuple[int, int]] = field(default_factory=list)
    points_played: int = 0
    # (set_no, game_no, server_is_a, a_won, tiebreak) per point, when recorded
    log: list[tuple[int, int, bool, bool, bool]] = field(default_factory=list)


def _constant(pa: float, pb: float) -> PointProb:
    return lambda server_is_a, _state: pa if server_is_a else pb


def simulate_match(fmt: MatchFormat, rng: random.Random, point_prob: PointProb, a_serves_first: bool,
                   record: bool = False) -> SimulatedMatch:
    log: list[tuple[int, int, bool, bool, bool]] = []
    state = {"sets": [0, 0], "games": [0, 0], "set_scores": []}
    points = 0
    server_a = a_serves_first
    need = fmt.sets_to_win

    def play_point(server_is_a: bool, tiebreak: bool = False) -> bool:
        nonlocal points
        points += 1
        p = point_prob(server_is_a, state)
        a_won = (rng.random() < p) == server_is_a
        if record:
            log.append((len(state["set_scores"]) + 1, ga + gb + 1, server_is_a, a_won, tiebreak))
        return a_won

    while max(state["sets"]) < need:
        final = state["sets"][0] == need - 1 and state["sets"][1] == need - 1
        tb_target = fmt.final_set_tiebreak_target if final else fmt.tiebreak_target
        ga = gb = 0
        while True:
            if ga == 6 and gb == 6:
                # Tiebreak: the player due to serve this game serves first.
                ta = tb = 0
                k = 0
                while not ((ta >= tb_target or tb >= tb_target) and abs(ta - tb) >= 2):
                    first_on_serve = ((k + 1) // 2) % 2 == 0
                    if play_point(server_a if first_on_serve else not server_a, True):
                        ta += 1
                    else:
                        tb += 1
                    k += 1
                if ta > tb:
                    ga += 1
                else:
                    gb += 1
                server_a = not server_a
                break
            pa_pts = pb_pts = 0
            while not ((pa_pts >= 4 or pb_pts >= 4) and abs(pa_pts - pb_pts) >= 2):
                if play_point(server_a):
                    pa_pts += 1
                else:
                    pb_pts += 1
            if pa_pts > pb_pts:
                ga += 1
            else:
                gb += 1
            server_a = not server_a
            state["games"] = [ga, gb]
            if (ga >= 6 or gb >= 6) and abs(ga - gb) >= 2:
                break
        state["set_scores"].append((ga, gb))
        state["sets"][0 if ga > gb else 1] += 1
        state["games"] = [0, 0]

    total_a = sum(s[0] for s in state["set_scores"])
    total_b = sum(s[1] for s in state["set_scores"])
    return SimulatedMatch(
        Outcome(state["sets"][0], state["sets"][1], total_a, total_b),
        list(state["set_scores"]),
        points,
        log,
    )


def simulate_matches(
    pa: float,
    pb: float,
    fmt: MatchFormat,
    n: int = 10_000,
    seed: int | None = None,
    point_prob: PointProb | None = None,
) -> list[SimulatedMatch]:
    """Simulate n matches; first server is a coin toss per match."""
    rng = random.Random(seed)
    pp = point_prob or _constant(pa, pb)
    return [simulate_match(fmt, rng, pp, rng.random() < 0.5) for _ in range(n)]


def empirical_distribution(matches: list[SimulatedMatch]) -> dict[Outcome, float]:
    dist: dict[Outcome, float] = {}
    w = 1.0 / len(matches)
    for m in matches:
        dist[m.outcome] = dist.get(m.outcome, 0.0) + w
    return dist
