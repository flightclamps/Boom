"""Live feed adapters.

Each adapter turns a provider's point-by-point JSON into the normalized
schema in schema.py, so the rest of the model never sees provider shapes.
"""

from .schema import NormalizedMatch, Point, profile_stats_from_matches
from . import api_tennis, sofascore_rapidapi

PARSERS = {
    "api-tennis": api_tennis.parse_match,
    "rapidapi-tennisapi": sofascore_rapidapi.parse_point_by_point,
}

__all__ = ["NormalizedMatch", "Point", "PARSERS", "profile_stats_from_matches"]
