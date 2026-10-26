"""Minimal HTTP fetchers for the feeds. Keys come from the environment.

Endpoint paths follow each provider's public docs and have not been called
successfully yet (the cloud sandbox's network policy blocks them); run these
from a machine with open network access.
"""

import json
import os
import urllib.parse
import urllib.request


def _get(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def api_tennis_fixtures(date_start: str, date_stop: str, **params) -> dict:
    """api-tennis.com get_fixtures; needs API_TENNIS_KEY."""
    q = {"method": "get_fixtures", "APIkey": os.environ["API_TENNIS_KEY"],
         "date_start": date_start, "date_stop": date_stop, **params}
    return _get("https://api.api-tennis.com/tennis/?" + urllib.parse.urlencode(q))


def api_tennis_livescore() -> dict:
    q = {"method": "get_livescore", "APIkey": os.environ["API_TENNIS_KEY"]}
    return _get("https://api.api-tennis.com/tennis/?" + urllib.parse.urlencode(q))


def rapidapi_point_by_point(event_id: int) -> dict:
    """RapidAPI TennisApi point-by-point; needs RAPIDAPI_KEY."""
    host = "tennisapi1.p.rapidapi.com"
    return _get(
        f"https://{host}/api/tennis/event/{event_id}/point-by-point",
        {"x-rapidapi-key": os.environ["RAPIDAPI_KEY"], "x-rapidapi-host": host},
    )
