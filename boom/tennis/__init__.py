"""Tennis point-by-point match model.

Pipeline: feed JSON -> normalized points (feeds) -> player serve/return
profiles (model) -> per-point win probabilities for a matchup -> exact
Markov distribution or Monte Carlo samples (markov / montecarlo) -> prop
prices (pricing).
"""

from .rules import MatchFormat, format_for_event
from .model import PlayerProfile, SurfaceStats, matchup_point_probs
from .markov import match_distribution
from .montecarlo import simulate_matches
from .pricing import MarketBook

__all__ = [
    "MatchFormat",
    "format_for_event",
    "PlayerProfile",
    "SurfaceStats",
    "matchup_point_probs",
    "match_distribution",
    "simulate_matches",
    "MarketBook",
]
