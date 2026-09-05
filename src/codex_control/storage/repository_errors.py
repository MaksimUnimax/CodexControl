"""Finite, content-free semantic errors for durable repositories."""

from enum import StrEnum


class RepositoryErrorCategory(StrEnum):
    INVALID_ARGUMENT = "invalid_argument"
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    VERSION_CONFLICT = "version_conflict"
    STATE_CONFLICT = "state_conflict"
    CLOCK_INVALID = "clock_invalid"
    INVARIANT_VIOLATION = "invariant_violation"

    def __str__(self) -> str:
        return self.value


class RepositoryError(Exception):
    """A deliberately finite and redacted repository diagnostic."""

    def __init__(self, category: RepositoryErrorCategory) -> None:
        try:
            normalized = (
                category
                if isinstance(category, RepositoryErrorCategory)
                else RepositoryErrorCategory(category)
            )
        except (TypeError, ValueError):
            normalized = RepositoryErrorCategory.INVALID_ARGUMENT
        self.category = normalized
        super().__init__(normalized.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"RepositoryError({self.category.value!r})"
