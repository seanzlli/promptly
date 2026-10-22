"""Quiz progress (in-memory demo state).

- ``GET /api/progress/{user}``  profile: XP, streak, badges, subject levels

Subject levels: every user has a rank per subject (Beginner -> Expert)
based on the points earned in quizzes on that subject, see :func:`add_points`.

State is kept in memory for the demo; swap in a database later.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["progress"])

_BADGES = {
    100: "First steps",
    250: "Foundations",
    500: "Core",
    1000: "Applied",
    2000: "Master",
}

# Minimum subject points for each rank.
_RANKS = {
    0: "Beginner",
    50: "Basic",
    150: "Student",
    300: "Intermediate",
    600: "Advanced",
    1000: "Expert",
}

# user_id -> {"xp": int, "streak": int, "last_day": "YYYY-MM-DD"}
_STATE: dict[str, dict] = {}
# user_id -> normalized subject -> {"name": str, "points": int}
_SUBJECTS: dict[str, dict[str, dict]] = {}


def _touch(uid: str) -> None:
    today = date.today().isoformat()
    profile = _STATE.setdefault(uid, {"xp": 0, "streak": 0, "last_day": None})
    if profile["last_day"] == today:
        return
    profile["streak"] = 1 if profile["last_day"] is None else profile["streak"] + 1
    profile["last_day"] = today


def _subject_level(entry: dict) -> dict:
    points = entry["points"]
    reached = [rank for tier, rank in sorted(_RANKS.items()) if points >= tier]
    upcoming = [(tier, rank) for tier, rank in sorted(_RANKS.items()) if points < tier]
    return {
        "subject": entry["name"],
        "points": points,
        "rank": reached[-1],
        "next_rank": upcoming[0][1] if upcoming else None,
        "points_to_next": upcoming[0][0] - points if upcoming else None,
    }


def add_points(user: str, subject: str, points: int) -> dict:
    """Credit quiz points to a subject (and to the user's XP).

    Subjects that differ only in case or spacing count as one. Returns the
    subject's level, plus ``ranked_up`` if these points reached a new rank.
    """
    _touch(user)
    _STATE[user]["xp"] += points
    key = " ".join(subject.split()).casefold()
    entry = _SUBJECTS.setdefault(user, {}).setdefault(
        key, {"name": " ".join(subject.split()), "points": 0}
    )
    rank_before = _subject_level(entry)["rank"]
    entry["points"] += points
    level = _subject_level(entry)
    return {**level, "ranked_up": level["rank"] != rank_before}


@router.get("/progress/{user}")
def get_progress(user: str) -> dict:
    """Return the user's progress profile."""
    _touch(user)
    profile = _STATE[user]
    badges = [b for tier, b in sorted(_BADGES.items()) if profile["xp"] >= tier]
    subjects = sorted(
        (_subject_level(entry) for entry in _SUBJECTS.get(user, {}).values()),
        key=lambda s: s["points"],
        reverse=True,
    )
    return {"user": user, **profile, "badges": badges, "subjects": subjects}