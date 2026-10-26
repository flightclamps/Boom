"""Serve/return profiles and matchup point probabilities.

A player's surface rate is shrunk toward their own all-surface rate (shifted
by the tour's surface effect), and that in turn toward the tour average, so a
player with 300 clay points isn't priced off noise. The matchup uses the
additive Barnett-Clarke form: A's serve-point probability against B is the
surface average, plus how much better than average A serves, minus how much
better than average B returns.
"""

from dataclasses import dataclass, field

SURFACES = ("hard", "clay", "grass")

# Approximate tour-average share of service points won by the server.
# Placeholders until computed from the live feed's historical data.
TOUR_SERVE_AVG = {
    "atp": {"hard": 0.645, "clay": 0.625, "grass": 0.665, "all": 0.640},
    "wta": {"hard": 0.565, "clay": 0.555, "grass": 0.580, "all": 0.562},
}

# Pseudo-points of prior weight. Roughly: a surface rate needs ~2000 points
# before it outweighs the player's overall rate.
SURFACE_PRIOR_POINTS = 2000
OVERALL_PRIOR_POINTS = 1000


@dataclass
class SurfaceStats:
    serve_won: int = 0
    serve_played: int = 0
    return_won: int = 0
    return_played: int = 0

    def __add__(self, other: "SurfaceStats") -> "SurfaceStats":
        return SurfaceStats(
            self.serve_won + other.serve_won,
            self.serve_played + other.serve_played,
            self.return_won + other.return_won,
            self.return_played + other.return_played,
        )


@dataclass
class PlayerProfile:
    name: str
    tour: str = "atp"
    by_surface: dict[str, SurfaceStats] = field(default_factory=dict)

    def overall(self) -> SurfaceStats:
        total = SurfaceStats()
        for s in self.by_surface.values():
            total = total + s
        return total

    @classmethod
    def from_dict(cls, d: dict) -> "PlayerProfile":
        return cls(
            name=d["name"],
            tour=d.get("tour", "atp"),
            by_surface={k: SurfaceStats(**v) for k, v in d.get("by_surface", {}).items()},
        )


def _shrink(won: int, played: int, prior: float, weight: float) -> float:
    return (won + weight * prior) / (played + weight)


def serve_return_rates(player: PlayerProfile, surface: str) -> tuple[float, float]:
    """Shrunk (serve points won %, return points won %) on a surface."""
    avgs = TOUR_SERVE_AVG[player.tour]
    surf_serve_avg, all_serve_avg = avgs[surface], avgs["all"]
    overall = player.overall()
    overall_serve = _shrink(overall.serve_won, overall.serve_played, all_serve_avg, OVERALL_PRIOR_POINTS)
    overall_return = _shrink(overall.return_won, overall.return_played, 1 - all_serve_avg, OVERALL_PRIOR_POINTS)
    surface_shift = surf_serve_avg - all_serve_avg
    s = player.by_surface.get(surface, SurfaceStats())
    serve = _shrink(s.serve_won, s.serve_played, overall_serve + surface_shift, SURFACE_PRIOR_POINTS)
    ret = _shrink(s.return_won, s.return_played, overall_return - surface_shift, SURFACE_PRIOR_POINTS)
    return serve, ret


def matchup_point_probs(a: PlayerProfile, b: PlayerProfile, surface: str) -> tuple[float, float]:
    """(P(A wins a point on A's serve), P(B wins a point on B's serve))."""
    if surface not in SURFACES:
        raise ValueError(f"surface must be one of {SURFACES}")
    if a.tour != b.tour:
        raise ValueError("players are on different tours")
    avg_serve = TOUR_SERVE_AVG[a.tour][surface]
    avg_return = 1 - avg_serve
    a_serve, a_return = serve_return_rates(a, surface)
    b_serve, b_return = serve_return_rates(b, surface)
    pa = avg_serve + (a_serve - avg_serve) - (b_return - avg_return)
    pb = avg_serve + (b_serve - avg_serve) - (a_return - avg_return)
    return _clamp(pa), _clamp(pb)


def _clamp(p: float) -> float:
    return min(0.95, max(0.30, p))
