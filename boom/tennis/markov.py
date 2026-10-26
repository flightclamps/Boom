"""Exact Markov-chain match distribution.

Point probabilities are constant within a match (iid points given server),
so the full distribution of final outcomes can be computed exactly by
dynamic programming instead of sampled. This is the pricing engine; the
Monte Carlo simulator in montecarlo.py runs the same rules point by point
and is used to cross-check it and for anything path dependent.

Convention throughout: pa = P(A wins a point on A's serve),
pb = P(B wins a point on B's serve).
"""

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from .rules import MatchFormat


def game_win_prob(p: float) -> float:
    """P(server holds) when the server wins each point with probability p."""
    q = 1.0 - p
    deuce = p * p / (p * p + q * q)
    # Win to 0, 15 or 30, or reach 3-3 and win from deuce.
    return p**4 * (1 + 4 * q + 10 * q * q) + 20 * p**3 * q**3 * deuce


def tiebreak_win_prob(pa: float, pb: float, target: int = 7, a_serves_first: bool = True) -> float:
    """P(A wins a tiebreak to `target`, win by two)."""
    a_return = 1.0 - pb
    # From any tie at target-1 or beyond, each pair of points has one serve
    # each, so the tie is a two-outcome race per pair.
    win_pair = pa * a_return
    lose_pair = (1.0 - pa) * pb
    from_tie = win_pair / (win_pair + lose_pair) if win_pair + lose_pair > 0 else 0.5

    @lru_cache(maxsize=None)
    def f(a: int, b: int) -> float:
        if a >= target and a - b >= 2:
            return 1.0
        if b >= target and b - a >= 2:
            return 0.0
        if a == b and a >= target - 1:
            return from_tie
        k = a + b
        # Serve order in a tiebreak: S, R, R, S, S, R, R, ...
        first_server_on_serve = ((k + 1) // 2) % 2 == 0
        a_serving = first_server_on_serve == a_serves_first
        p = pa if a_serving else a_return
        return p * f(a + 1, b) + (1.0 - p) * f(a, b + 1)

    return f(0, 0)


def set_distribution(pa: float, pb: float, a_serves_first: bool, tiebreak_target: int = 7) -> dict[tuple[int, int], float]:
    """Distribution of final set scores (games_a, games_b)."""
    hold_a = game_win_prob(pa)
    hold_b = game_win_prob(pb)
    # The player who serves first in the set also serves first in the tiebreak.
    tb_a = tiebreak_win_prob(pa, pb, tiebreak_target, a_serves_first)

    dist: dict[tuple[int, int], float] = defaultdict(float)
    frontier = {(0, 0): 1.0}
    while frontier:
        nxt: dict[tuple[int, int], float] = defaultdict(float)
        for (a, b), pr in frontier.items():
            if (a == 6 and b <= 4) or (b == 6 and a <= 4) or a == 7 or b == 7:
                dist[(a, b)] += pr
                continue
            if a == 6 and b == 6:
                dist[(7, 6)] += pr * tb_a
                dist[(6, 7)] += pr * (1.0 - tb_a)
                continue
            a_serving = ((a + b) % 2 == 0) == a_serves_first
            g = hold_a if a_serving else 1.0 - hold_b
            nxt[(a + 1, b)] += pr * g
            nxt[(a, b + 1)] += pr * (1.0 - g)
        frontier = nxt
    return dict(dist)


@dataclass(frozen=True)
class Outcome:
    """Final match state: sets and total games won by each player."""

    sets_a: int
    sets_b: int
    games_a: int
    games_b: int


def match_distribution(pa: float, pb: float, fmt: MatchFormat, a_serves_first: float = 0.5) -> dict[Outcome, float]:
    """Exact distribution over final match outcomes.

    a_serves_first is the probability A serves the first game (0.5 = coin
    toss not yet known).
    """
    need = fmt.sets_to_win
    cache: dict[tuple[bool, bool], dict[tuple[int, int], float]] = {}

    def set_dist(a_first: bool, final: bool):
        key = (a_first, final)
        if key not in cache:
            target = fmt.final_set_tiebreak_target if final else fmt.tiebreak_target
            cache[key] = set_distribution(pa, pb, a_first, target)
        return cache[key]

    result: dict[Outcome, float] = defaultdict(float)
    # State: (sets_a, sets_b, a serves first in this set, games_a, games_b)
    frontier: dict[tuple, float] = defaultdict(float)
    if a_serves_first > 0:
        frontier[(0, 0, True, 0, 0)] += a_serves_first
    if a_serves_first < 1:
        frontier[(0, 0, False, 0, 0)] += 1.0 - a_serves_first
    while frontier:
        nxt: dict[tuple, float] = defaultdict(float)
        for (sa, sb, a_first, ga, gb), pr in frontier.items():
            final = sa == need - 1 and sb == need - 1
            for (x, y), ps in set_dist(a_first, final).items():
                nsa, nsb = (sa + 1, sb) if x > y else (sa, sb + 1)
                state_p = pr * ps
                if nsa == need or nsb == need:
                    result[Outcome(nsa, nsb, ga + x, gb + y)] += state_p
                else:
                    # Serve keeps alternating across sets.
                    next_a_first = a_first if (x + y) % 2 == 0 else not a_first
                    nxt[(nsa, nsb, next_a_first, ga + x, gb + y)] += state_p
        frontier = nxt
    return dict(result)
