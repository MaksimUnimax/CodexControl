from enum import Enum


class StorageErrorCategory(str, Enum):
    INVALID_PATH = "invalid_path"
    INSECURE_PATH = "insecure_path"
    LOCKED = "locked"
    OPEN_FAILED = "open_failed"
    SCHEMA_UNSUPPORTED = "schema_unsupported"
    SCHEMA_INVALID = "schema_invalid"
    CLOSED = "closed"
    TRANSACTION_FAILED = "transaction_failed"

    def __str__(self) -> str:
        return self.value


class StorageError(Exception):
    """A deliberately finite, content-free storage diagnostic."""

    def __init__(self, category: StorageErrorCategory) -> None:
        try:
            normalized = (
                category
                if isinstance(category, StorageErrorCategory)
                else StorageErrorCategory(category)
            )
        except (TypeError, ValueError):
            normalized = StorageErrorCategory.TRANSACTION_FAILED
        self.category = normalized
        super().__init__(normalized.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"StorageError({self.category.value!r})"
