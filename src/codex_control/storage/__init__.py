"""The controller's process-owned SQLite storage kernel."""

from .errors import StorageError, StorageErrorCategory
from .schema import (
    MIGRATION_ID,
    SCHEMA_VERSION,
    SCHEMA_V1_CANONICAL_SQL,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V1_STATEMENTS,
)
from .sqlite import SqliteStorage
from .core_repositories import (
    ControllerRuntimeRepository,
    DialogueRepository,
    SettingsRepository,
)
from .records import (
    ControllerBootResult,
    ControllerRuntimeRecord,
    DialogueRecord,
    DialogueState,
    SettingsInitializeResult,
    SettingsRecord,
)
from .repository_errors import RepositoryError, RepositoryErrorCategory

__all__ = [
    "MIGRATION_ID",
    "SCHEMA_VERSION",
    "SCHEMA_V1_CANONICAL_SQL",
    "SCHEMA_V1_DDL_SHA256",
    "SCHEMA_V1_STATEMENTS",
    "SqliteStorage",
    "StorageError",
    "StorageErrorCategory",
    "RepositoryError",
    "RepositoryErrorCategory",
    "DialogueState",
    "ControllerRuntimeRecord",
    "ControllerBootResult",
    "SettingsRecord",
    "SettingsInitializeResult",
    "DialogueRecord",
    "ControllerRuntimeRepository",
    "SettingsRepository",
    "DialogueRepository",
]
