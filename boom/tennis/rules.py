from dataclasses import dataclass


@dataclass(frozen=True)
class MatchFormat:
    best_of: int = 3
    # Points needed to win a regular-set tiebreak at 6-6.
    tiebreak_target: int = 7
    # Points needed to win the deciding-set tiebreak at 6-6. All four Grand
    # Slams have played a 10-point tiebreak at 6-6 in the final set since 2022.
    final_set_tiebreak_target: int = 7

    @property
    def sets_to_win(self) -> int:
        return self.best_of // 2 + 1


def format_for_event(tour: str, grand_slam: bool) -> MatchFormat:
    """Singles format for a tour event.

    Grand Slam men's singles is best-of-5; everything else on the ATP/WTA
    main tours is best-of-3. Slams use a 10-point final-set tiebreak.
    """
    tour = tour.lower()
    if tour not in ("atp", "wta"):
        raise ValueError(f"unknown tour {tour!r}")
    if grand_slam:
        return MatchFormat(best_of=5 if tour == "atp" else 3, final_set_tiebreak_target=10)
    return MatchFormat(best_of=3)
