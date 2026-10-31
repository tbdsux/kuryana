"""v2 page parsers: pure functions from a MyDramaList page to typed, JSON-ready dicts."""

from app.v2.parsers._helpers import error_info, pagination
from app.v2.parsers.cast import parse_cast
from app.v2.parsers.drama import parse_drama
from app.v2.parsers.dramalist import parse_dramalist
from app.v2.parsers.episodes import parse_episodes
from app.v2.parsers.lists import parse_list
from app.v2.parsers.person import parse_person
from app.v2.parsers.reviews import parse_reviews
from app.v2.parsers.search import parse_search

__all__ = [
    "error_info",
    "pagination",
    "parse_cast",
    "parse_drama",
    "parse_dramalist",
    "parse_episodes",
    "parse_list",
    "parse_person",
    "parse_reviews",
    "parse_search",
]
