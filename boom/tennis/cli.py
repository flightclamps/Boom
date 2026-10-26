"""Command line entry point.

  python -m boom.tennis parse --source api-tennis FILE.json
  python -m boom.tennis price --pa 0.66 --pb 0.62 --best-of 3 --total 22.5
  python -m boom.tennis price --profiles players.json --a "Sinner" --b "Alcaraz" \\
      --surface clay --tour atp --grand-slam --total 38.5 --set-spread -1.5
"""

import argparse
import json
import sys

from .feeds import PARSERS
from .markov import match_distribution
from .model import PlayerProfile, matchup_point_probs, serve_return_rates
from .montecarlo import empirical_distribution, simulate_matches
from .pricing import MarketBook, breakeven_from_multiplier, breakeven_per_leg, fair_american
from .rules import MatchFormat, format_for_event


def _parse(args) -> dict:
    with open(args.file) as f:
        payload = json.load(f)
    parser = PARSERS[args.source]
    fixtures = payload.get("result", payload) if args.source == "api-tennis" else payload
    if isinstance(fixtures, dict):
        fixtures = [fixtures]
    out = []
    for fx in fixtures:
        m = parser(fx)
        a, b = m.serve_stats()
        out.append({
            "match_id": m.match_id,
            "players": m.players,
            "points": len(m.points),
            "set_scores": m.set_scores(),
            "serve_points_won": {
                m.players[0]: f"{a.serve_won}/{a.serve_played}",
                m.players[1]: f"{b.serve_won}/{b.serve_played}",
            },
        })
    return {"matches": out}


def _price(args) -> dict:
    if args.profiles:
        with open(args.profiles) as f:
            profiles = {p["name"]: PlayerProfile.from_dict(p) for p in json.load(f)}
        a, b = profiles[args.a], profiles[args.b]
        pa, pb = matchup_point_probs(a, b, args.surface)
        fmt = format_for_event(a.tour, args.grand_slam)
        inputs = {
            "surface": args.surface,
            "rates": {
                a.name: dict(zip(("serve", "return"), map(lambda x: round(x, 4), serve_return_rates(a, args.surface)))),
                b.name: dict(zip(("serve", "return"), map(lambda x: round(x, 4), serve_return_rates(b, args.surface)))),
            },
        }
    else:
        if args.pa is None or args.pb is None:
            sys.exit("give --pa/--pb or --profiles with --a/--b")
        pa, pb = args.pa, args.pb
        fmt = MatchFormat(best_of=args.best_of, final_set_tiebreak_target=10 if args.grand_slam else 7)
        inputs = {}

    if args.monte_carlo:
        dist = empirical_distribution(simulate_matches(pa, pb, fmt, n=args.monte_carlo, seed=args.seed))
    else:
        dist = match_distribution(pa, pb, fmt)
    book = MarketBook(dist)

    be = breakeven_from_multiplier(args.multiplier) if args.multiplier else breakeven_per_leg(args.entry_payout, args.legs)
    p_win = book.match_win_a()
    markets = {
        "match_winner_a": {"prob": round(p_win, 4), "fair_american": fair_american(p_win)},
        "expected_total_games": round(book.mean(book.total_games()), 2),
        "set_scores": {k: round(v, 4) for k, v in book.set_scores().items()},
    }

    def priced(name, lp):
        best = max(("over", lp.over), ("under", lp.under), key=lambda t: t[1])
        markets[name] = {**lp.to_dict(), "best_side": best[0], "edge_vs_breakeven": round(best[1] - be, 4)}

    if args.total is not None:
        priced(f"total_games_{args.total}", book.line(book.total_games(), args.total))
    if args.games_a is not None:
        priced(f"a_games_won_{args.games_a}", book.line(book.games_won_a(), args.games_a))
    if args.games_b is not None:
        priced(f"b_games_won_{args.games_b}", book.line(book.games_won_b(), args.games_b))
    if args.game_spread is not None:
        priced(f"a_game_spread_{args.game_spread}", book.handicap(book.game_spread(), args.game_spread))
    if args.set_spread is not None:
        priced(f"a_set_spread_{args.set_spread}", book.handicap(book.set_spread(), args.set_spread))

    return {
        "pa_serve_point": round(pa, 4),
        "pb_serve_point": round(pb, 4),
        "format": {"best_of": fmt.best_of, "final_set_tiebreak": fmt.final_set_tiebreak_target},
        "engine": f"monte_carlo n={args.monte_carlo}" if args.monte_carlo else "exact_markov",
        "pick_breakeven": round(be, 4),
        **inputs,
        "markets": markets,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m boom.tennis")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse", help="parse a point-by-point JSON response")
    p.add_argument("file")
    p.add_argument("--source", choices=sorted(PARSERS), required=True)

    q = sub.add_parser("price", help="price props for a matchup")
    q.add_argument("--pa", type=float, help="P(A wins point on own serve)")
    q.add_argument("--pb", type=float, help="P(B wins point on own serve)")
    q.add_argument("--profiles", help="JSON list of player profiles")
    q.add_argument("--a")
    q.add_argument("--b")
    q.add_argument("--surface", default="hard")
    q.add_argument("--best-of", type=int, default=3, choices=(3, 5))
    q.add_argument("--grand-slam", action="store_true")
    q.add_argument("--total", type=float, help="total games line")
    q.add_argument("--games-a", type=float, help="player A games won line")
    q.add_argument("--games-b", type=float, help="player B games won line")
    q.add_argument("--game-spread", type=float, help="A game handicap, e.g. -3.5")
    q.add_argument("--set-spread", type=float, help="A set handicap, e.g. -1.5")
    q.add_argument("--multiplier", type=float, help="per-pick payout multiplier (Sleeper)")
    q.add_argument("--entry-payout", type=float, default=3.0, help="all-hit entry payout (default 2-pick 3x)")
    q.add_argument("--legs", type=int, default=2)
    q.add_argument("--monte-carlo", type=int, metavar="N", help="sample N matches instead of exact Markov")
    q.add_argument("--seed", type=int)

    args = ap.parse_args(argv)
    result = _parse(args) if args.cmd == "parse" else _price(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
