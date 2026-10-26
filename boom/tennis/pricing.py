"""Turn a match outcome distribution into prop prices.

Every market is read off the same joint distribution, so match winner,
total games, set spread, game spread and player games won are consistent
with each other.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from .markov import Outcome


@dataclass(frozen=True)
class LinePrice:
    over: float
    push: float
    under: float

    def to_dict(self) -> dict:
        return {"over": round(self.over, 4), "push": round(self.push, 4), "under": round(self.under, 4)}


class MarketBook:
    def __init__(self, dist: dict[Outcome, float]):
        total = sum(dist.values())
        self.dist = {k: v / total for k, v in dist.items()}

    def _marginal(self, f: Callable[[Outcome], int]) -> dict[int, float]:
        m: dict[int, float] = defaultdict(float)
        for o, p in self.dist.items():
            m[f(o)] += p
        return dict(sorted(m.items()))

    def match_win_a(self) -> float:
        return sum(p for o, p in self.dist.items() if o.sets_a > o.sets_b)

    def total_games(self) -> dict[int, float]:
        return self._marginal(lambda o: o.games_a + o.games_b)

    def game_spread(self) -> dict[int, float]:
        """A's games minus B's games."""
        return self._marginal(lambda o: o.games_a - o.games_b)

    def set_spread(self) -> dict[int, float]:
        """A's sets minus B's sets."""
        return self._marginal(lambda o: o.sets_a - o.sets_b)

    def total_sets(self) -> dict[int, float]:
        return self._marginal(lambda o: o.sets_a + o.sets_b)

    def games_won_a(self) -> dict[int, float]:
        return self._marginal(lambda o: o.games_a)

    def games_won_b(self) -> dict[int, float]:
        return self._marginal(lambda o: o.games_b)

    def set_scores(self) -> dict[str, float]:
        m: dict[str, float] = defaultdict(float)
        for o, p in self.dist.items():
            m[f"{o.sets_a}-{o.sets_b}"] += p
        return dict(sorted(m.items()))

    @staticmethod
    def line(marginal: dict[int, float], line: float) -> LinePrice:
        over = sum(p for k, p in marginal.items() if k > line)
        push = sum(p for k, p in marginal.items() if k == line)
        return LinePrice(over, push, 1.0 - over - push)

    @staticmethod
    def handicap(spread: dict[int, float], handicap: float) -> LinePrice:
        """P(A covers `handicap`), e.g. -1.5 sets means A wins by 2+.

        `over` is A covering, `under` is B covering.
        """
        return MarketBook.line(spread, -handicap)

    @staticmethod
    def mean(marginal: dict[int, float]) -> float:
        return sum(k * p for k, p in marginal.items())


def fair_american(p: float) -> int:
    if p <= 0 or p >= 1:
        raise ValueError("probability must be in (0, 1)")
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def breakeven_from_multiplier(multiplier: float) -> float:
    """Per-pick break-even probability for a pick paying `multiplier`x
    (e.g. a Sleeper option's payout_multiplier)."""
    return 1.0 / multiplier


def breakeven_per_leg(entry_payout: float, legs: int) -> float:
    """Per-leg break-even for an all-must-hit pick'em entry, e.g. a 2-pick
    Underdog/Sleeper power play paying 3x -> 0.577."""
    return entry_payout ** (-1.0 / legs)


def edge(p: float, breakeven: float) -> float:
    return p - breakeven
