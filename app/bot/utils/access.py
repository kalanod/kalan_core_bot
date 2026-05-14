"""Access helpers for username allow-list checks."""

from collections.abc import Iterable


def normalize_username(username: str | None) -> str | None:
    """Normalize a Telegram username for allow-list checks."""
    if username is None:
        return None

    normalized = username.strip().removeprefix("@").lower()
    return normalized or None


def parse_allow_list(raw_allow_list: Iterable[str]) -> frozenset[str]:
    """Parse a Telegram username allow-list from an iterable of strings."""
    return frozenset(
        username
        for raw_username in raw_allow_list
        if (username := normalize_username(raw_username)) is not None
    )


def is_username_allowed(username: str | None, allow_list: Iterable[str]) -> bool:
    """Return whether the normalized username exists in the configured allow-list."""
    normalized_username = normalize_username(username)
    return normalized_username is not None and normalized_username in set(allow_list)
