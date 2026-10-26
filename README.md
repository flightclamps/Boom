# Boom

Point-by-point tennis match model for pricing player props (match winner,
total games, games won, game and set spreads) against Sleeper / Underdog
pick'em lines.

## How it works

1. **Feed** (`boom/tennis/feeds`): adapters turn a provider's point-by-point
   JSON into one normalized point log (server, winner, set, game, tiebreak).
   Adapters exist for api-tennis.com and the RapidAPI "TennisApi"
   (SofaScore-shaped) feed. `profile_stats_from_matches` rolls point logs up
   into per-player, per-surface serve/return counts.
2. **Model** (`model.py`): surface rates are shrunk toward the player's
   overall rate and the tour average, then combined into a matchup:
   `P(A wins serve point) = avg + (A serve - avg) - (B return - avg return)`.
3. **Engine**: `markov.py` computes the exact distribution of every final
   outcome (sets and games for each player); `montecarlo.py` plays the same
   rules point by point and is used to cross-check and for future
   state-dependent models. Grand Slam men are best-of-5, everything else
   best-of-3, with a 10-point final-set tiebreak at Slams.
4. **Pricing** (`pricing.py`): every market is read off the same joint
   distribution, and compared with the pick'em break-even (e.g. 57.7% per leg
   for a 2-pick 3x entry, or `1 / payout_multiplier` on Sleeper).

## Usage

```bash
python -m boom.tennis price --pa 0.66 --pb 0.62 --total 22.5 --set-spread -1.5
python -m boom.tennis price --profiles examples/synthetic_profiles.json \
  --a "Big Server (synthetic)" --b "Clay Grinder (synthetic)" \
  --surface clay --grand-slam --total 38.5 --set-spread -1.5
python -m boom.tennis parse --source api-tennis tests/fixtures/api_tennis_fixture.json
python -m pytest
```

## Live data status

The cloud sandbox blocks every tennis feed host (tennis-api.com,
RapidAPI incl. Matchstat, api-tennis.com, Sportradar, SofaScore), so the
adapters are written against documented response shapes and tested on
synthetic fixtures plus a simulate -> serialize -> parse round trip. To go
live, set `API_TENNIS_KEY` and/or `RAPIDAPI_KEY` and use
`boom/tennis/feeds/client.py` from a machine with open network access, then
save a real response into `tests/fixtures/`.

Tour-average serve rates in `model.py` are placeholders until computed from
the feed's history.
