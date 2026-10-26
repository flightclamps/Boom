from dataclasses import dataclass, field

from ..model import PlayerProfile, SurfaceStats


@dataclass(frozen=True)
class Point:
    set_no: int
    game_no: int
    # 0 = first player (home), 1 = second player (away)
    server: int
    winner: int
    tiebreak: bool = False


@dataclass
class NormalizedMatch:
    match_id: str
    players: tuple[str, str]
    surface: str | None = None
    tour: str | None = None
    points: list[Point] = field(default_factory=list)

    def serve_stats(self) -> tuple[SurfaceStats, SurfaceStats]:
        """Per-player serve/return point counts from the point log."""
        stats = [SurfaceStats(), SurfaceStats()]
        for pt in self.points:
            srv, ret = stats[pt.server], stats[1 - pt.server]
            srv.serve_played += 1
            ret.return_played += 1
            if pt.winner == pt.server:
                srv.serve_won += 1
            else:
                ret.return_won += 1
        return stats[0], stats[1]

    def set_scores(self) -> list[tuple[int, int]]:
        """Final games per set, reconstructed from the last point of each game."""
        games: dict[tuple[int, int], int] = {}
        for pt in self.points:
            games[(pt.set_no, pt.game_no)] = pt.winner
        sets: dict[int, list[int]] = {}
        for (s, _g), w in sorted(games.items()):
            sets.setdefault(s, [0, 0])[w] += 1
        return [tuple(v) for _, v in sorted(sets.items())]


def profile_stats_from_matches(matches: list[NormalizedMatch], tour: str = "atp") -> dict[str, PlayerProfile]:
    """Aggregate point logs into per-player, per-surface profiles."""
    profiles: dict[str, PlayerProfile] = {}
    for m in matches:
        if m.surface is None:
            continue
        for name, st in zip(m.players, m.serve_stats()):
            prof = profiles.setdefault(name, PlayerProfile(name=name, tour=m.tour or tour))
            prof.by_surface[m.surface] = prof.by_surface.get(m.surface, SurfaceStats()) + st
    return profiles
