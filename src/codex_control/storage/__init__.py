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
from .idempotency_records import (
    IngressClaimResult,
    IngressDispositionKind,
    IngressUpdateRecord,
    ControlClaimStatus,
    ControlClaimResult,
    CallbackActionRecord,
    CallbackClaimStatus,
    CallbackClaimResult,
)
from .idempotency_repositories import (
    IngressUpdateRepository,
    ControlIngressRepository,
    CallbackActionRepository,
)
from .turn_job_records import (
    TurnExecutionClaimResult,
    TurnIngressClaimResult,
    TurnIngressClaimStatus,
    TurnJobFinishResult,
    TurnJobRecord,
    TurnJobState,
    TurnTerminalOutcome,
)
from .transient_payloads import (
    MAX_TRANSIENT_PAYLOAD_BYTES,
    TransientPayloadKind,
    TransientPayloadRecord,
)
from .turn_job_repositories import TurnJobRepository, TransientPayloadRepository
from .delivery_records import (
    DeliveryOperation,
    DeliverySegmentState,
    DeliveryFinishOutcome,
    DeliveryPlanItem,
    DeliverySegmentRecord,
    DeliveryPlanResult,
    DeliveryClaimResult,
    DeliveryFinishResult,
)
from .delivery_repositories import DeliverySegmentRepository
from .approval_records import (
    ApprovalKind,
    ApprovalState,
    ApprovalCallbackClaimStatus,
    ApprovalRecord,
    ApprovalCallbackClaimResult,
)
from .approval_repositories import ApprovalRepository
from .retention import RetentionRepository, RetentionSweepResult
from .deletion_records import DeletionFinalizeResult, DeletionTombstoneRecord
from .deletion_repositories import DeletionRepository
from .error_records import ErrorFingerprintRecord
from .error_repositories import ErrorFingerprintRepository
from .metadata_retention import (
    METADATA_RETENTION_MS,
    MetadataRetentionRepository,
    MetadataRetentionSweepResult,
)
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .settings_dialogue_guards import SettingsDialogueGuardRepository
from .interrupt_coordination import InterruptCoordinationRepository
from .private_management import PrivateCallbackActionSpec, PrivateManagementRepository

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
    "IngressUpdateRepository",
    "ControlIngressRepository",
    "CallbackActionRepository",
    "IngressDispositionKind",
    "IngressUpdateRecord",
    "IngressClaimResult",
    "ControlClaimStatus",
    "ControlClaimResult",
    "CallbackActionRecord",
    "CallbackClaimStatus",
    "CallbackClaimResult",
    "TurnJobState",
    "TurnJobRecord",
    "TurnIngressClaimStatus",
    "TurnIngressClaimResult",
    "TurnExecutionClaimResult",
    "TurnTerminalOutcome",
    "TurnJobFinishResult",
    "TransientPayloadKind",
    "TransientPayloadRecord",
    "MAX_TRANSIENT_PAYLOAD_BYTES",
    "TurnJobRepository",
    "TransientPayloadRepository",
    "DeliveryOperation",
    "DeliverySegmentState",
    "DeliveryFinishOutcome",
    "DeliveryPlanItem",
    "DeliverySegmentRecord",
    "DeliveryPlanResult",
    "DeliveryClaimResult",
    "DeliveryFinishResult",
    "DeliverySegmentRepository",
    "ApprovalState",
    "ApprovalKind",
    "ApprovalCallbackClaimStatus",
    "ApprovalRecord",
    "ApprovalCallbackClaimResult",
    "ApprovalRepository",
    "RetentionRepository",
    "RetentionSweepResult",
    "DeletionTombstoneRecord",
    "DeletionFinalizeResult",
    "DeletionRepository",
    "ErrorFingerprintRecord",
    "ErrorFingerprintRepository",
    "METADATA_RETENTION_MS",
    "MetadataRetentionRepository",
    "MetadataRetentionSweepResult",
    "SettingsDialogueGuardRepository",
    "InterruptCoordinationRepository",
    "PrivateCallbackActionSpec",
    "PrivateManagementRepository",
]
