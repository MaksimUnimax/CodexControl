"""Frozen schema-v1 DDL from ADR-0018."""

from hashlib import sha256

SCHEMA_VERSION = 1
MIGRATION_ID = "0001_initial_state"

SCHEMA_V1_STATEMENTS: tuple[str, ...] = (
    """CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version >= 1),
    migration_id TEXT NOT NULL UNIQUE CHECK (length(migration_id) BETWEEN 1 AND 128),
    ddl_sha256 TEXT NOT NULL CHECK (length(ddl_sha256) = 64),
    applied_at_ms INTEGER NOT NULL CHECK (applied_at_ms >= 0)
)""",
    """CREATE TABLE controller_runtime (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    last_control_epoch INTEGER NOT NULL CHECK (last_control_epoch >= 0),
    requested_mode TEXT NOT NULL CHECK (requested_mode IN ('ACTIVE','SLEEP')),
    boot_generation INTEGER NOT NULL CHECK (boot_generation >= 0),
    fleet_version TEXT NOT NULL CHECK (length(fleet_version) BETWEEN 1 AND 128),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= created_at_ms)
)""",
    """CREATE TABLE settings (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    profile_id TEXT CHECK (profile_id IS NULL OR length(profile_id) BETWEEN 1 AND 128),
    model_id TEXT CHECK (model_id IS NULL OR length(model_id) BETWEEN 1 AND 256),
    reasoning_effort TEXT CHECK (reasoning_effort IS NULL OR length(reasoning_effort) BETWEEN 1 AND 64),
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= created_at_ms)
)""",
    """CREATE TABLE dialogues (
    dialogue_id TEXT PRIMARY KEY CHECK (length(dialogue_id) BETWEEN 1 AND 128),
    live_slot INTEGER NOT NULL DEFAULT 1 UNIQUE CHECK (live_slot = 1),
    server_id TEXT NOT NULL CHECK (length(server_id) BETWEEN 1 AND 128),
    profile_id TEXT NOT NULL CHECK (length(profile_id) BETWEEN 1 AND 128),
    thread_id TEXT CHECK (thread_id IS NULL OR length(thread_id) BETWEEN 1 AND 512),
    state TEXT NOT NULL CHECK (state IN ('CREATING','IDLE','CREATE_UNKNOWN','ERROR','TURN_RUNNING','INTERRUPTING','TURN_UNKNOWN','DELETE_PENDING','DELETING','DELETE_UNKNOWN')),
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= created_at_ms),
    last_error_class TEXT CHECK (last_error_class IS NULL OR length(last_error_class) BETWEEN 1 AND 128)
)""",
    """CREATE TABLE turn_jobs (
    job_id TEXT PRIMARY KEY CHECK (length(job_id) BETWEEN 1 AND 128),
    telegram_update_id INTEGER NOT NULL UNIQUE CHECK (telegram_update_id >= 0),
    source_chat_id INTEGER NOT NULL,
    source_message_id INTEGER NOT NULL CHECK (source_message_id >= 0),
    dialogue_id TEXT NOT NULL REFERENCES dialogues(dialogue_id) ON DELETE CASCADE,
    server_id TEXT NOT NULL CHECK (length(server_id) BETWEEN 1 AND 128),
    profile_id TEXT NOT NULL CHECK (length(profile_id) BETWEEN 1 AND 128),
    thread_id TEXT CHECK (thread_id IS NULL OR length(thread_id) BETWEEN 1 AND 512),
    model_id TEXT CHECK (model_id IS NULL OR length(model_id) BETWEEN 1 AND 256),
    reasoning_effort TEXT CHECK (reasoning_effort IS NULL OR length(reasoning_effort) BETWEEN 1 AND 64),
    input_sha256 TEXT NOT NULL CHECK (length(input_sha256) = 64),
    codex_turn_id TEXT CHECK (codex_turn_id IS NULL OR length(codex_turn_id) BETWEEN 1 AND 512),
    state TEXT NOT NULL CHECK (state IN ('RECEIVED','CLAIMED','CODEX_STARTING','CODEX_RUNNING','CODEX_COMPLETED','FAILED','UNKNOWN','DELIVERY_PENDING','DELIVERING','DELIVERED','DELIVERY_UNKNOWN')),
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= created_at_ms),
    error_class TEXT CHECK (error_class IS NULL OR length(error_class) BETWEEN 1 AND 128)
)""",
    """CREATE TABLE transient_payloads (
    payload_id TEXT PRIMARY KEY CHECK (length(payload_id) BETWEEN 1 AND 128),
    dialogue_id TEXT REFERENCES dialogues(dialogue_id) ON DELETE CASCADE,
    job_id TEXT REFERENCES turn_jobs(job_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('INPUT','OUTPUT','APPROVAL','DISPLAY')),
    content BLOB NOT NULL CHECK (typeof(content) = 'blob'),
    content_sha256 TEXT NOT NULL CHECK (length(content_sha256) = 64),
    byte_length INTEGER NOT NULL CHECK (byte_length >= 0 AND byte_length = length(content)),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    expires_at_ms INTEGER NOT NULL CHECK (expires_at_ms >= created_at_ms),
    CHECK (dialogue_id IS NOT NULL OR job_id IS NOT NULL)
)""",
    """CREATE TABLE delivery_segments (
    job_id TEXT NOT NULL REFERENCES turn_jobs(job_id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL CHECK (sequence >= 1),
    operation TEXT NOT NULL CHECK (operation IN ('CREATE','EDIT')),
    target_message_id INTEGER CHECK (target_message_id IS NULL OR target_message_id >= 0),
    payload_id TEXT REFERENCES transient_payloads(payload_id) ON DELETE SET NULL,
    payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
    state TEXT NOT NULL CHECK (state IN ('PENDING','SENDING','CONFIRMED','UNKNOWN','FAILED')),
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    confirmed_message_id INTEGER CHECK (confirmed_message_id IS NULL OR confirmed_message_id >= 0),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= created_at_ms),
    PRIMARY KEY (job_id, sequence)
)""",
    """CREATE TABLE ingress_updates (
    update_id INTEGER PRIMARY KEY CHECK (update_id >= 0),
    received_at_ms INTEGER NOT NULL CHECK (received_at_ms >= 0),
    completed_at_ms INTEGER CHECK (completed_at_ms IS NULL OR completed_at_ms >= received_at_ms),
    disposition TEXT NOT NULL CHECK (
        disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED')
        OR (substr(disposition, 1, 4) = 'JOB:' AND length(disposition) > 4)
    )
)""",
    """CREATE TABLE callback_actions (
    token_hash_sha256 TEXT PRIMARY KEY CHECK (length(token_hash_sha256) = 64),
    action TEXT NOT NULL CHECK (length(action) BETWEEN 1 AND 128),
    subject_type TEXT NOT NULL CHECK (length(subject_type) BETWEEN 1 AND 64),
    subject_id TEXT NOT NULL CHECK (length(subject_id) BETWEEN 1 AND 128),
    expected_version INTEGER NOT NULL CHECK (expected_version >= 0),
    expected_state TEXT NOT NULL CHECK (length(expected_state) BETWEEN 1 AND 64),
    authorized_user_id INTEGER NOT NULL,
    authorized_chat_id INTEGER NOT NULL,
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    expires_at_ms INTEGER NOT NULL CHECK (expires_at_ms >= created_at_ms),
    consumed_at_ms INTEGER CHECK (consumed_at_ms IS NULL OR consumed_at_ms >= created_at_ms)
)""",
    """CREATE TABLE approvals (
    approval_id TEXT PRIMARY KEY CHECK (length(approval_id) BETWEEN 1 AND 128),
    profile_id TEXT NOT NULL CHECK (length(profile_id) BETWEEN 1 AND 128),
    wire_request_id_type TEXT NOT NULL CHECK (wire_request_id_type IN ('INTEGER','STRING')),
    wire_request_id_int INTEGER,
    wire_request_id_text TEXT CHECK (wire_request_id_text IS NULL OR length(wire_request_id_text) BETWEEN 1 AND 256),
    job_id TEXT NOT NULL REFERENCES turn_jobs(job_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('command_execution','file_change','permissions','apply_patch','exec_command')),
    display_payload_id TEXT REFERENCES transient_payloads(payload_id) ON DELETE SET NULL,
    state TEXT NOT NULL CHECK (state IN ('PENDING','APPROVED','DENIED','EXPIRED','CANCELLED')),
    created_at_ms INTEGER NOT NULL CHECK (created_at_ms >= 0),
    updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms >= created_at_ms),
    expires_at_ms INTEGER NOT NULL CHECK (expires_at_ms >= created_at_ms),
    CHECK (
        (wire_request_id_type = 'INTEGER' AND wire_request_id_int IS NOT NULL AND wire_request_id_text IS NULL)
        OR
        (wire_request_id_type = 'STRING' AND wire_request_id_int IS NULL AND wire_request_id_text IS NOT NULL)
    )
)""",
    """CREATE TABLE deletion_tombstones (
    dialogue_id TEXT PRIMARY KEY CHECK (length(dialogue_id) BETWEEN 1 AND 128),
    thread_identity_sha256 TEXT NOT NULL CHECK (length(thread_identity_sha256) = 64),
    stale_generation INTEGER NOT NULL CHECK (stale_generation >= 0),
    deleted_at_ms INTEGER NOT NULL CHECK (deleted_at_ms >= 0),
    expires_at_ms INTEGER NOT NULL CHECK (expires_at_ms >= deleted_at_ms)
)""",
    """CREATE TABLE errors (
    fingerprint_sha256 TEXT PRIMARY KEY CHECK (length(fingerprint_sha256) = 64),
    error_class TEXT NOT NULL CHECK (length(error_class) BETWEEN 1 AND 128),
    count INTEGER NOT NULL CHECK (count >= 1),
    first_seen_at_ms INTEGER NOT NULL CHECK (first_seen_at_ms >= 0),
    last_seen_at_ms INTEGER NOT NULL CHECK (last_seen_at_ms >= first_seen_at_ms),
    dialogue_id TEXT REFERENCES dialogues(dialogue_id) ON DELETE SET NULL,
    job_id TEXT REFERENCES turn_jobs(job_id) ON DELETE SET NULL
)""",
    "CREATE INDEX idx_turn_jobs_dialogue_state ON turn_jobs(dialogue_id, state)",
    "CREATE INDEX idx_transient_payloads_expires ON transient_payloads(expires_at_ms)",
    "CREATE INDEX idx_transient_payloads_dialogue ON transient_payloads(dialogue_id)",
    "CREATE INDEX idx_transient_payloads_job ON transient_payloads(job_id)",
    "CREATE INDEX idx_delivery_segments_state ON delivery_segments(state, job_id, sequence)",
    "CREATE INDEX idx_delivery_segments_payload ON delivery_segments(payload_id)",
    "CREATE INDEX idx_callback_actions_expiry ON callback_actions(expires_at_ms, consumed_at_ms)",
    "CREATE INDEX idx_approvals_job_state_expiry ON approvals(job_id, state, expires_at_ms)",
    "CREATE INDEX idx_approvals_wire_request ON approvals(profile_id, wire_request_id_type, wire_request_id_int, wire_request_id_text, state)",
    "CREATE INDEX idx_approvals_display_payload ON approvals(display_payload_id)",
    "CREATE INDEX idx_deletion_tombstones_expiry ON deletion_tombstones(expires_at_ms)",
    "CREATE INDEX idx_errors_last_seen ON errors(last_seen_at_ms)",
    "CREATE INDEX idx_errors_dialogue ON errors(dialogue_id)",
    "CREATE INDEX idx_errors_job ON errors(job_id)",
)


def canonicalize_sql(statement: str) -> str:
    value = statement.strip()
    if value.endswith(";"):
        value = value[:-1].rstrip()
    return " ".join(value.split()) + ";"


SCHEMA_V1_CANONICAL_SQL = "\n".join(
    canonicalize_sql(statement) for statement in SCHEMA_V1_STATEMENTS
) + "\n"
SCHEMA_V1_DDL_SHA256 = sha256(SCHEMA_V1_CANONICAL_SQL.encode("utf-8")).hexdigest()

TABLE_NAMES = frozenset(
    statement.split()[2]
    for statement in SCHEMA_V1_STATEMENTS
    if statement.lstrip().upper().startswith("CREATE TABLE ")
)
INDEX_NAMES = frozenset(
    statement.split()[2]
    for statement in SCHEMA_V1_STATEMENTS
    if statement.lstrip().upper().startswith("CREATE INDEX ")
)
