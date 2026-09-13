"""P7.C17 post-delete oracle successor preparation.

This module is preparation-only.  It composes the accepted P7.C16/P7.C15
child graph and changes only the proof boundary: current-run marker
selection, sanitized attribution, and a durable oracle-facts observation.
All real effects remain behind the distinct, disabled P7.C17 gate.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from unittest.mock import patch

from codex_control.adapters.codex.isolation import IsolationPathAuthority
from tests.real import test_p7_c12_strict_approval_matcher as p7c12
from tests.real import test_p7_c13_final_hard_delete_acceptance as p7c13
from tests.real import test_p7_c15_final_hard_delete_successor as p7c15
from tests.real import test_p7_c16_final_hard_delete_successor as p7c16


P7C17_FUTURE_REAL_GATE = "P7C17_FUTURE_REAL_GATE"
P7C17_EXPECTED_HEAD = "P7C17_EXPECTED_HEAD"
P7C17_EXPECTED_TREE = "P7C17_EXPECTED_TREE"
P7C17_EXPECTED_LAUNCHER_BLOB = "P7C17_EXPECTED_LAUNCHER_BLOB"
P7C17_EXPECTED_P7C16_LAUNCHER_BLOB = "P7C17_EXPECTED_P7C16_LAUNCHER_BLOB"
P7C17_EXPECTED_P7C15_LAUNCHER_BLOB = "P7C17_EXPECTED_P7C15_LAUNCHER_BLOB"
P7C17_EXPECTED_P7C14_LAUNCHER_BLOB = "P7C17_EXPECTED_P7C14_LAUNCHER_BLOB"
P7C17_EXPECTED_P7C13_HARNESS_BLOB = "P7C17_EXPECTED_P7C13_HARNESS_BLOB"
P7C17_EXPECTED_P7C12_MATCHER_BLOB = "P7C17_EXPECTED_P7C12_MATCHER_BLOB"
P7C17_EXPECTED_TESTS_INIT_BLOB = "P7C17_EXPECTED_TESTS_INIT_BLOB"
P7C17_EXPECTED_TESTS_REAL_INIT_BLOB = "P7C17_EXPECTED_TESTS_REAL_INIT_BLOB"
P7C17_LEDGER_PATH = Path("/root/.codexcontrol/p7c17-one-shot.json")
P7C17_IMPORT_ROOTS = ("/root/CodexControl/src", "/root/CodexControl")
P7C17_PYTHONPATH = os.pathsep.join(P7C17_IMPORT_ROOTS)
P7C17_PROFILE_ID = p7c16.P7C16_ENGINE_PROFILE_ID
P7C17_LEDGER_SCHEMA = "p7c17-one-shot-v1"
P7C17_BOOT_SCHEMA = "p7c17-boot-v1"
P7C17_CHILD_RESULT_SCHEMA = "p7c17-child-result-v1"
P7C17_ORACLE_FACTS_SCHEMA = "p7c17-oracle-facts-v1"
P7C17_ATTRIBUTION_SCHEMA = "p7c17-unrelated-removal-v1"
P7C17_MARKER_POLICY_VERSION = "p7c17-current-run-markers-v1"
P7C17_STATES = frozenset(("RESERVED", "COMPLETED", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"))
_FROZEN_POST_DELETE_ACCEPTANCE = p7c13.post_delete_acceptance


class P7C17PreparationError(RuntimeError):
    """Finite, path-free preparation failure."""


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _repository() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=_repository(), check=True, capture_output=True, text=True).stdout.strip()


def _blob(path: Path) -> str:
    return _git("hash-object", str(path))


@dataclass(frozen=True)
class P7C17SourceAuthority:
    head: str
    tree: str
    launcher_blob: str
    p7c16_launcher_blob: str
    p7c15_launcher_blob: str
    p7c14_launcher_blob: str
    p7c13_harness_blob: str
    p7c12_matcher_blob: str
    tests_init_blob: str
    tests_real_init_blob: str
    import_root_authority: bool
    tracked_worktree_clean: bool
    tracked_index_clean: bool


@dataclass(frozen=True)
class P7C17ArchitectContract:
    authorization_token: str
    expected_head: str
    expected_tree: str
    expected_launcher_blob: str
    expected_p7c16_launcher_blob: str
    expected_p7c15_launcher_blob: str
    expected_p7c14_launcher_blob: str
    expected_p7c13_harness_blob: str
    expected_p7c12_matcher_blob: str
    expected_tests_init_blob: str
    expected_tests_real_init_blob: str
    expected_import_roots: tuple[str, str] = P7C17_IMPORT_ROOTS
    expected_tracked_worktree_clean: bool = True
    expected_tracked_index_clean: bool = True


def current_p7c17_source_authority() -> P7C17SourceAuthority:
    repo = _repository()
    worktree_clean = subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    index_clean = subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    return P7C17SourceAuthority(
        _git("rev-parse", "HEAD"), _git("rev-parse", "HEAD^{tree}"), _blob(Path(__file__).resolve()),
        _blob(repo / "tests/real/test_p7_c16_final_hard_delete_successor.py"),
        _blob(repo / "tests/real/test_p7_c15_final_hard_delete_successor.py"),
        _blob(repo / "tests/real/test_p7_c14_final_hard_delete_recovery.py"),
        _blob(repo / "tests/real/test_p7_c13_final_hard_delete_acceptance.py"),
        _blob(repo / "tests/real/test_p7_c12_strict_approval_matcher.py"),
        _blob(repo / "tests/__init__.py"), _blob(repo / "tests/real/__init__.py"),
        p7c15.validate_p7c15_import_root_authority(), worktree_clean, index_clean,
    )


def _contract_from_environment(environ: Mapping[str, str]) -> P7C17ArchitectContract:
    values = {name: environ.get(name, "") for name in (
        P7C17_FUTURE_REAL_GATE, P7C17_EXPECTED_HEAD, P7C17_EXPECTED_TREE,
        P7C17_EXPECTED_LAUNCHER_BLOB, P7C17_EXPECTED_P7C16_LAUNCHER_BLOB,
        P7C17_EXPECTED_P7C15_LAUNCHER_BLOB, P7C17_EXPECTED_P7C14_LAUNCHER_BLOB,
        P7C17_EXPECTED_P7C13_HARNESS_BLOB, P7C17_EXPECTED_P7C12_MATCHER_BLOB,
        P7C17_EXPECTED_TESTS_INIT_BLOB, P7C17_EXPECTED_TESTS_REAL_INIT_BLOB,
    )}
    return P7C17ArchitectContract(
        values[P7C17_FUTURE_REAL_GATE], values[P7C17_EXPECTED_HEAD], values[P7C17_EXPECTED_TREE],
        values[P7C17_EXPECTED_LAUNCHER_BLOB], values[P7C17_EXPECTED_P7C16_LAUNCHER_BLOB],
        values[P7C17_EXPECTED_P7C15_LAUNCHER_BLOB], values[P7C17_EXPECTED_P7C14_LAUNCHER_BLOB],
        values[P7C17_EXPECTED_P7C13_HARNESS_BLOB], values[P7C17_EXPECTED_P7C12_MATCHER_BLOB],
        values[P7C17_EXPECTED_TESTS_INIT_BLOB], values[P7C17_EXPECTED_TESTS_REAL_INIT_BLOB],
    )


def p7c17_source_bundle_gate(environ: Mapping[str, str], contract: P7C17ArchitectContract | None,
                             authority: P7C17SourceAuthority) -> bool:
    if contract is None or contract.expected_import_roots != P7C17_IMPORT_ROOTS:
        return False
    if contract.expected_tracked_worktree_clean is not True or contract.expected_tracked_index_clean is not True:
        return False
    expected = (contract.authorization_token, contract.expected_head, contract.expected_tree,
                contract.expected_launcher_blob, contract.expected_p7c16_launcher_blob,
                contract.expected_p7c15_launcher_blob, contract.expected_p7c14_launcher_blob,
                contract.expected_p7c13_harness_blob, contract.expected_p7c12_matcher_blob,
                contract.expected_tests_init_blob, contract.expected_tests_real_init_blob)
    if not all(expected) or environ.get(P7C17_FUTURE_REAL_GATE) != contract.authorization_token:
        return False
    env_names = (P7C17_EXPECTED_HEAD, P7C17_EXPECTED_TREE, P7C17_EXPECTED_LAUNCHER_BLOB,
                 P7C17_EXPECTED_P7C16_LAUNCHER_BLOB, P7C17_EXPECTED_P7C15_LAUNCHER_BLOB,
                 P7C17_EXPECTED_P7C14_LAUNCHER_BLOB, P7C17_EXPECTED_P7C13_HARNESS_BLOB,
                 P7C17_EXPECTED_P7C12_MATCHER_BLOB, P7C17_EXPECTED_TESTS_INIT_BLOB,
                 P7C17_EXPECTED_TESTS_REAL_INIT_BLOB)
    supplied = tuple(environ.get(name, "") for name in env_names)
    actual = current_p7c17_source_authority()
    actual_protected = (actual.launcher_blob, actual.p7c16_launcher_blob, actual.p7c15_launcher_blob,
                        actual.p7c14_launcher_blob, actual.p7c13_harness_blob, actual.p7c12_matcher_blob,
                        actual.tests_init_blob, actual.tests_real_init_blob)
    expected_protected = (contract.expected_launcher_blob, contract.expected_p7c16_launcher_blob,
                          contract.expected_p7c15_launcher_blob, contract.expected_p7c14_launcher_blob,
                          contract.expected_p7c13_harness_blob, contract.expected_p7c12_matcher_blob,
                          contract.expected_tests_init_blob, contract.expected_tests_real_init_blob)
    return (supplied == (contract.expected_head, contract.expected_tree, *expected_protected)
            and actual.head == contract.expected_head and actual.tree == contract.expected_tree
            and actual_protected == expected_protected and actual.import_root_authority
            and actual.tracked_worktree_clean and actual.tracked_index_clean
            and authority == actual)


def p7c17_fresh_run_paths(fragment: str, *, root: Path, authority: Path) -> dict[str, str]:
    safe = "".join(char for char in fragment if char in "0123456789abcdef")[:32]
    if not safe:
        raise P7C17PreparationError("safe run hash fragment required")
    return {
        "isolated_root": str(root / f"p7c17-isolated-{safe}"),
        "controller_db": str(authority / f"p7c17-controller-{safe}.sqlite3"),
        "workdir": str(root / f"p7c17-work-{safe}"),
        "approval_target": str(root / f"p7c17-approval-{safe}"),
        "boot": str(authority / f"p7c17-boot-{safe}.json"),
        "child_result": str(authority / f"p7c17-child-result-{safe}.json"),
        "wire": str(authority / f"p7c17-wire-{safe}.json"),
        "approval_journal": str(authority / f"p7c17-approval-journal-{safe}.json"),
        "stage": str(authority / f"p7c17-stage-{safe}.jsonl"),
        "oracle_facts": str(authority / f"p7c17-oracle-facts-{safe}.json"),
        "unrelated_removal": str(authority / f"p7c17-unrelated-removal-{safe}.json"),
    }


class P7C17CurrentRunMarkerPolicy:
    """Immutable validator/filter for the inherited five-marker tuple."""

    version = P7C17_MARKER_POLICY_VERSION
    marker_classes = ("memory_marker", "response_marker", "approval_target", "turn3_prompt")

    def __init__(self, approval_target: str) -> None:
        self.approval_target = approval_target
        self._selected: tuple[bytes, ...] | None = None

    @staticmethod
    def _fresh(value: bytes) -> bool:
        if not value or len(value) < 20 or len(value) > 512:
            return False
        return len(set(value)) >= 10 and value not in {b"P7C16_MEMORY_SYNTHETIC", b"P7C15_RESPONSE_SYNTHETIC"}

    def select(self, supplied: Sequence[bytes]) -> tuple[bytes, ...]:
        if len(supplied) != 5 or any(not isinstance(item, bytes) or not item for item in supplied):
            raise P7C17PreparationError("P7.C17 marker shape drift")
        memory, response, target, prompt, fixed = supplied
        if not self._fresh(memory) or not self._fresh(response) or memory == response:
            raise P7C17PreparationError("P7.C17 fresh marker authority invalid")
        expected_target = self.approval_target.encode()
        expected_prompt = p7c13.c11_explicit_escalation_prompt(self.approval_target).encode()
        if target != expected_target or prompt != expected_prompt or fixed != p7c13.TURN4_STIMULUS.encode():
            raise P7C17PreparationError("P7.C17 marker semantic classes drifted")
        # The fixed behavioral Turn-4 stimulus is deliberately identified and
        # excluded.  Target/prompt are run-unique and remain eligible.
        self._selected = (memory, response, target, prompt)
        return self._selected

    @property
    def selected(self) -> tuple[bytes, ...]:
        if self._selected is None:
            raise P7C17PreparationError("P7.C17 marker policy not selected")
        return self._selected

    @property
    def enabled_marker_classes(self) -> tuple[str, ...]:
        return self.marker_classes

    @property
    def safe_identity_hashes(self) -> tuple[str, ...]:
        return tuple(_sha256(item) for item in self.selected)


class P7C17BoundedTargetOracle(p7c13.BoundedTargetOracle):
    """Inherited no-follow/bounded scanner with corrected marker authority."""

    def __init__(self, profile: Any, thread_id: str, markers: Sequence[bytes], *, policy: P7C17CurrentRunMarkerPolicy,
                 max_bytes: int = 4 * 1024 * 1024, families: Sequence[str] | None = None) -> None:
        self.policy = policy
        super().__init__(profile, thread_id, policy.select(markers), max_bytes=max_bytes, families=families)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise P7C17PreparationError("duplicate JSON key")
        result[key] = value
    return result


class _RootOnlyJsonAuthority:
    MAX_BYTES = 32768
    schema = ""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._identity: tuple[int, int] | None = None

    def _check_identity(self) -> os.stat_result:
        st = self.path.lstat()
        if (st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
                or not stat.S_ISREG(st.st_mode) or st.st_size > self.MAX_BYTES):
            raise P7C17PreparationError("P7.C17 authority identity invalid")
        identity = (st.st_dev, st.st_ino)
        if self._identity is not None and identity != self._identity:
            raise P7C17PreparationError("P7.C17 authority replacement")
        self._identity = identity
        return st

    def _validate(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("schema") != self.schema:
            raise P7C17PreparationError("P7.C17 authority schema invalid")
        return dict(value)

    def write(self, value: Mapping[str, Any]) -> dict[str, Any]:
        checked = self._validate(dict(value))
        payload = (json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        if len(payload) > self.MAX_BYTES:
            raise P7C17PreparationError("P7.C17 authority too large")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.fchmod(fd, 0o600); os.write(fd, payload); os.fsync(fd)
            st = os.fstat(fd)
            if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
                raise P7C17PreparationError("P7.C17 authority identity invalid")
            self._identity = (st.st_dev, st.st_ino)
        finally:
            os.close(fd)
        return self.read()

    def read(self, *, expected: Mapping[str, Any] | None = None) -> dict[str, Any]:
        identity = self._check_identity()
        fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            data = os.read(fd, self.MAX_BYTES + 1); current = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino) or current.st_nlink != 1:
                raise P7C17PreparationError("P7.C17 authority identity drift")
        finally:
            os.close(fd)
        if len(data) > self.MAX_BYTES:
            raise P7C17PreparationError("P7.C17 authority too large")
        value = self._validate(json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys))
        if expected is not None:
            for key, expected_value in expected.items():
                if value.get(key) != expected_value:
                    raise P7C17PreparationError("P7.C17 authority correlation mismatch")
        return value


def _hex_hashes(values: Any, *, bound: int = 4096) -> bool:
    return (isinstance(values, list) and len(values) <= bound
            and all(isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value) for value in values))


class P7C17UnrelatedRemovalAttributionAuthority(_RootOnlyJsonAuthority):
    schema = P7C17_ATTRIBUTION_SCHEMA

    def _validate(self, value: Any) -> dict[str, Any]:
        value = super()._validate(value)
        required = {"schema", "source_head", "source_tree", "launcher_blob", "run_id_hash", "boot_authority_sha256",
                    "before_path_hashes", "after_path_hashes", "target_path_hashes", "removed_unrelated_path_hashes",
                    "before_count", "after_count", "target_count", "removed_unrelated_count", "unrelated_removed"}
        if set(value) != required or any(not isinstance(value.get(key), str) or not value[key] for key in ("source_head", "source_tree", "launcher_blob", "run_id_hash", "boot_authority_sha256")):
            raise P7C17PreparationError("P7.C17 attribution shape invalid")
        if len(value["run_id_hash"]) != 64 or any(not _hex_hashes(value[key]) for key in ("before_path_hashes", "after_path_hashes", "target_path_hashes", "removed_unrelated_path_hashes")):
            raise P7C17PreparationError("P7.C17 attribution hashes invalid")
        if any(type(value[key]) is not int or value[key] < 0 for key in ("before_count", "after_count", "target_count", "removed_unrelated_count")) or type(value["unrelated_removed"]) is not bool:
            raise P7C17PreparationError("P7.C17 attribution counts invalid")
        return value


ORACLE_FACT_KEYS = frozenset({
    "schema", "source_head", "source_tree", "launcher_blob", "run_id_hash", "boot_authority_sha256", "boot_identity_class",
    "official_delete_class", "application_delete_class", "tombstone_bounded", "live_binding_present",
    "post_delete_schema_class", "post_delete_schema_version", "isolation_envelope_class",
    "isolated_sqlite_regular_descendants", "isolated_sqlite_special_descendants", "isolated_sqlite_symlinks", "isolated_sqlite_scan_errors",
    "isolated_logs_regular_descendants", "isolated_logs_special_descendants", "isolated_logs_symlinks", "isolated_logs_scan_errors",
    "persistent_thread_count", "persistent_thread_filename_count", "persistent_thread_directory_count", "persistent_marker_count", "persistent_scan_errors",
    "isolated_thread_count", "isolated_marker_count", "isolated_scan_errors", "combined_scan_errors",
    "unrelated_target_specific_removal_detected", "recovery_class", "budgets_ok", "runtime_child_quiescent",
    "marker_policy_class", "marker_policy_version", "enabled_marker_classes", "enabled_marker_identity_sha256",
    "unrelated_removal_authority_sha256",
})


class P7C17RootOnlyOracleFactsAuthority(_RootOnlyJsonAuthority):
    schema = P7C17_ORACLE_FACTS_SCHEMA

    def _validate(self, value: Any) -> dict[str, Any]:
        value = super()._validate(value)
        if set(value) != ORACLE_FACT_KEYS:
            raise P7C17PreparationError("P7.C17 oracle-facts key drift")
        strings = ("source_head", "source_tree", "launcher_blob", "run_id_hash", "boot_authority_sha256", "boot_identity_class",
                   "official_delete_class", "application_delete_class", "post_delete_schema_class", "isolation_envelope_class",
                   "recovery_class", "marker_policy_class", "marker_policy_version", "unrelated_removal_authority_sha256")
        if any(not isinstance(value[key], str) or not value[key] for key in strings) or len(value["run_id_hash"]) != 64:
            raise P7C17PreparationError("P7.C17 oracle-facts scalar invalid")
        bools = ("tombstone_bounded", "live_binding_present", "unrelated_target_specific_removal_detected", "budgets_ok", "runtime_child_quiescent")
        if any(type(value[key]) is not bool for key in bools) or type(value["post_delete_schema_version"]) is not int:
            raise P7C17PreparationError("P7.C17 oracle-facts boolean invalid")
        counts = tuple(key for key in value if key.endswith("descendants") or key.endswith("symlinks") or key.endswith("errors")
                       or key.endswith("count"))
        if any(type(value[key]) is not int or value[key] < 0 for key in counts):
            raise P7C17PreparationError("P7.C17 oracle-facts count invalid")
        if not isinstance(value["enabled_marker_classes"], list) or not all(isinstance(item, str) for item in value["enabled_marker_classes"]):
            raise P7C17PreparationError("P7.C17 marker classes invalid")
        if not _hex_hashes(value["enabled_marker_identity_sha256"], bound=8):
            raise P7C17PreparationError("P7.C17 marker identities invalid")
        return value


@dataclass(frozen=True)
class P7C17OracleEvaluation:
    passed: frozenset[str]
    failed: frozenset[str]
    unavailable: frozenset[str]


def evaluate_p7c17_oracle_facts(facts: Mapping[str, Any]) -> P7C17OracleEvaluation:
    predicates: tuple[tuple[str, Callable[[Mapping[str, Any]], bool]], ...] = (
        ("official.delete_class == DELETE_CONFIRMED", lambda f: f["official_delete_class"] == "DELETE_CONFIRMED"),
        ("application.delete_class == DELETED", lambda f: f["application_delete_class"] == "DELETED"),
        ("tombstone.bounded == true", lambda f: f["tombstone_bounded"] is True),
        ("live_binding.present == false", lambda f: f["live_binding_present"] is False),
        ("post_delete.schema == 4", lambda f: f["post_delete_schema_class"] == "V4" and f["post_delete_schema_version"] == 4),
        ("isolation.envelope == VALID", lambda f: f["isolation_envelope_class"] == "VALID"),
        ("isolated.sqlite.regular_descendants == 0", lambda f: f["isolated_sqlite_regular_descendants"] == 0),
        ("isolated.sqlite.special_descendants == 0", lambda f: f["isolated_sqlite_special_descendants"] == 0),
        ("isolated.sqlite.symlinks == 0", lambda f: f["isolated_sqlite_symlinks"] == 0),
        ("isolated.sqlite.scan_errors == 0", lambda f: f["isolated_sqlite_scan_errors"] == 0),
        ("isolated.logs.regular_descendants == 0", lambda f: f["isolated_logs_regular_descendants"] == 0),
        ("isolated.logs.special_descendants == 0", lambda f: f["isolated_logs_special_descendants"] == 0),
        ("isolated.logs.symlinks == 0", lambda f: f["isolated_logs_symlinks"] == 0),
        ("isolated.logs.scan_errors == 0", lambda f: f["isolated_logs_scan_errors"] == 0),
        ("persistent.thread_count == 0", lambda f: f["persistent_thread_count"] == 0),
        ("persistent.thread_filename_count == 0", lambda f: f["persistent_thread_filename_count"] == 0),
        ("persistent.thread_directory_count == 0", lambda f: f["persistent_thread_directory_count"] == 0),
        ("persistent.marker_count == 0", lambda f: f["persistent_marker_count"] == 0),
        ("persistent.scan_errors == 0", lambda f: f["persistent_scan_errors"] == 0),
        ("isolated.thread_count == 0", lambda f: f["isolated_thread_count"] == 0),
        ("isolated.marker_count == 0", lambda f: f["isolated_marker_count"] == 0),
        ("isolated.scan_errors == 0", lambda f: f["isolated_scan_errors"] == 0),
        ("combined.scan_errors == 0", lambda f: f["combined_scan_errors"] == 0),
        ("unrelated_target_specific_removal == false", lambda f: f["unrelated_target_specific_removal_detected"] is False),
        ("recovery.class == COMPLETED", lambda f: f["recovery_class"] == "COMPLETED"),
        ("budgets.ok == true", lambda f: f["budgets_ok"] is True),
        ("runtime_child.quiescent == true", lambda f: f["runtime_child_quiescent"] is True),
    )
    passed: set[str] = set(); failed: set[str] = set(); unavailable: set[str] = set()
    for name, predicate in predicates:
        try:
            result = predicate(facts)
        except (KeyError, TypeError, ValueError):
            unavailable.add(name)
        else:
            (passed if result else failed).add(name)
    return P7C17OracleEvaluation(frozenset(passed), frozenset(failed), frozenset(unavailable))


def _p7c17_safe_attribution(before: Mapping[str, tuple[int, int]], after: Mapping[str, tuple[int, int]],
                            target_paths: set[str], *, source: Mapping[str, Any], path: Path) -> dict[str, Any]:
    before_hashes = sorted(_sha256(item) for item in before)
    after_hashes = sorted(_sha256(item) for item in after)
    target_hashes = sorted(_sha256(item) for item in target_paths)
    removed = sorted(set(before_hashes) - set(after_hashes) - set(target_hashes))
    record = {
        "schema": P7C17_ATTRIBUTION_SCHEMA, "source_head": source["source_head"], "source_tree": source["source_tree"],
        "launcher_blob": source["launcher_blob"], "run_id_hash": source["run_id_hash"],
        "boot_authority_sha256": source["boot_authority_sha256"], "before_path_hashes": before_hashes,
        "after_path_hashes": after_hashes, "target_path_hashes": target_hashes,
        "removed_unrelated_path_hashes": removed, "before_count": len(before_hashes), "after_count": len(after_hashes),
        "target_count": len(target_hashes), "removed_unrelated_count": len(removed), "unrelated_removed": bool(removed),
    }
    return P7C17UnrelatedRemovalAttributionAuthority(path).write(record)


class P7C17RootOnlyBootAuthority(p7c16.P7C16RootOnlyBootAuthority):
    """P7.C17 boot identity, retaining the accepted path validation rules."""

    KEYS = p7c16.P7C16RootOnlyBootAuthority.KEYS | frozenset(("oracle_facts", "unrelated_removal"))
    PATH_KEYS = p7c16.P7C16RootOnlyBootAuthority.PATH_KEYS + ("oracle_facts", "unrelated_removal")

    @classmethod
    def validate(cls, value: Mapping[str, Any], *, authority_path: Path | None = None, allow_test_home: bool = False) -> dict[str, Any]:
        base = dict(value)
        if set(base) != cls.KEYS:
            raise P7C17PreparationError("P7.C17 boot key drift")
        extras = {key: base[key] for key in ("oracle_facts", "unrelated_removal")}
        base.pop("oracle_facts"); base.pop("unrelated_removal")
        base["schema"] = p7c16.P7C16_BOOT_SCHEMA
        # The inherited validator is used as the structural authority.  Its
        # namespace check is narrowed to P7.C17 after validation below.
        original_controller = base["controller_db"]
        base["controller_db"] = str(Path(original_controller).with_name("p7c16-controller-validation.sqlite3"))
        checked = p7c16.P7C16RootOnlyBootAuthority.validate(base, authority_path=authority_path, allow_test_home=allow_test_home)
        checked["controller_db"] = original_controller
        checked["schema"] = P7C17_BOOT_SCHEMA
        checked.update(extras)
        if not Path(checked["controller_db"]).name.startswith("p7c17-controller-"):
            raise P7C17PreparationError("P7.C17 controller namespace invalid")
        namespace_keys = set(cls.PATH_KEYS) - {"isolated_sqlite", "isolated_logs"}
        if not all(Path(checked[key]).name.startswith("p7c17-") for key in namespace_keys):
            raise P7C17PreparationError("P7.C17 path namespace invalid")
        return checked


class P7C17LateBoundControllerRuntimeView(p7c16.P7C16LateBoundControllerRuntimeView):
    def bind_exact_path(self) -> IsolationPathAuthority:
        path = Path(self.controller_db_path)
        if (not path.is_absolute() or not path.name.startswith("p7c17-controller-")
                or path.is_symlink() or not path.is_file()):
            raise ValueError("controller_storage_mismatch")
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1 or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("controller_storage_mismatch")
        exact = IsolationPathAuthority((self.profile,), controller_db_path=str(path), repository_root=str(self.repository), protected_roots=())
        exact.validate_runtime_authority()
        self._exact_authority = exact
        return exact


class P7C17RuntimeManagerView(p7c16.P7C16RuntimeManagerView):
    def __init__(self, underlying: Any, boot: Mapping[str, Any]) -> None:
        super().__init__(underlying, boot)
        self._authority_view = P7C17LateBoundControllerRuntimeView(underlying, self._authority_view.profile, _repository(), boot["controller_db"])


class P7C17ProductionChildOrchestrator(p7c16.P7C16ProductionChildOrchestrator):
    """The accepted P7.C16 chain with a proof-only P7.C17 seam."""

    def __init__(self, boot: Mapping[str, Any], journal: Any, *, runtime_factory: Callable[[], Any] | None = None,
                 force_failure: bool = False, stage_timeouts: Mapping[str, float] | None = None) -> None:
        self.p7c17_manager: P7C17RuntimeManagerView | None = None
        self._p7c17_policy = P7C17CurrentRunMarkerPolicy(boot["approval_target"])
        self._p7c17_before: Mapping[str, tuple[int, int]] = {}
        self._p7c17_target_paths: set[str] = set()
        self._p7c17_after: Mapping[str, tuple[int, int]] = {}

        def factory() -> P7C17RuntimeManagerView:
            raw = runtime_factory() if runtime_factory is not None else p7c15._build_p7c15_runtime_manager(boot)
            configure = getattr(raw, "configure", None)
            if callable(configure):
                configure(boot)
            self.p7c17_manager = P7C17RuntimeManagerView(raw, boot)
            return self.p7c17_manager

        # P7.C16's frozen constructor closes over its module-level view class.
        # Substitute only that view during construction so the inherited
        # factory still owns the runtime reservation and lifecycle graph while
        # the controller path accepts the P7.C17 namespace.
        with patch.object(p7c16, "P7C16RuntimeManagerView", P7C17RuntimeManagerView):
            super().__init__(boot, journal, runtime_factory=runtime_factory, force_failure=force_failure, stage_timeouts=stage_timeouts)

    async def run_async(self) -> dict[str, Any]:
        self.p7c17_manager = self.p7c16_manager
        def oracle_factory(profile: Any, thread: str, markers: Sequence[bytes], **kwargs: Any) -> P7C17BoundedTargetOracle:
            return P7C17BoundedTargetOracle(profile, thread, markers, policy=self._p7c17_policy, **kwargs)

        original_snapshot = p7c13.target_metadata_snapshot
        original_derived = p7c13.derived_unrelated_removal_fact

        def snapshot(profile: Any, thread: str) -> tuple[dict[str, tuple[int, int]], set[str]]:
            value = original_snapshot(profile, thread)
            if not self._p7c17_before:
                self._p7c17_before, self._p7c17_target_paths = value
            else:
                self._p7c17_after, _ = value
            return value

        def derived(before: Mapping[str, tuple[int, int]], after: Mapping[str, tuple[int, int]], *, target_paths: set[str]) -> bool:
            self._p7c17_before, self._p7c17_after, self._p7c17_target_paths = before, after, target_paths
            return original_derived(before, after, target_paths=target_paths)

        def acceptance(**kwargs: Any) -> bool:
            persistent = kwargs["persistent"]; isolated = kwargs["isolated"]
            sqlite = p7c13.bounded_descendant_observation(Path(self.boot["isolated_sqlite"]))
            logs = p7c13.bounded_descendant_observation(Path(self.boot["isolated_logs"]))
            source = {"source_head": self.boot["source_head"], "source_tree": self.boot["source_tree"],
                      "launcher_blob": self.boot["launcher_blob"], "run_id_hash": self.boot["run_id_hash"],
                      "boot_authority_sha256": _sha256(Path(self.boot["boot_authority_path"]).read_bytes())}
            attribution = _p7c17_safe_attribution(self._p7c17_before, self._p7c17_after, self._p7c17_target_paths,
                                                   source=source, path=Path(self.boot["unrelated_removal"]))
            manager = self.p7c16_manager
            runtime_quiescent = self._runtime_quiescent(manager) if manager is not None else False
            facts = {
                "schema": P7C17_ORACLE_FACTS_SCHEMA, **source, "boot_identity_class": "ROOT_0600_REGULAR_NLINK1",
                "official_delete_class": kwargs["official_delete"], "application_delete_class": kwargs["application_result"],
                "tombstone_bounded": bool(kwargs["tombstone_bounded"]), "live_binding_present": bool(kwargs["live_binding"]),
                "post_delete_schema_class": "V4", "post_delete_schema_version": 4,
                "isolation_envelope_class": "VALID" if kwargs["envelope_valid"] else "INVALID",
                "isolated_sqlite_regular_descendants": sqlite[0], "isolated_sqlite_special_descendants": sqlite[1],
                "isolated_sqlite_symlinks": sqlite[2], "isolated_sqlite_scan_errors": sqlite[3],
                "isolated_logs_regular_descendants": logs[0], "isolated_logs_special_descendants": logs[1],
                "isolated_logs_symlinks": logs[2], "isolated_logs_scan_errors": logs[3],
                "persistent_thread_count": persistent.thread_count, "persistent_thread_filename_count": persistent.thread_filename_count,
                "persistent_thread_directory_count": persistent.thread_directory_count, "persistent_marker_count": persistent.marker_count,
                "persistent_scan_errors": persistent.scan_errors, "isolated_thread_count": isolated.thread_count,
                "isolated_marker_count": isolated.marker_count, "isolated_scan_errors": isolated.scan_errors,
                "combined_scan_errors": persistent.scan_errors + isolated.scan_errors + sqlite[3] + logs[3],
                "unrelated_target_specific_removal_detected": bool(kwargs["unrelated_target_specific_removal_detected"]),
                "recovery_class": p7c13.map_terminal_recovery_class(
                    official_status=kwargs["official_delete"], application_status=kwargs["application_result"]),
                "budgets_ok": bool(kwargs["budgets_ok"]),
                "runtime_child_quiescent": runtime_quiescent, "marker_policy_class": type(self._p7c17_policy).__name__,
                "marker_policy_version": self._p7c17_policy.version, "enabled_marker_classes": list(self._p7c17_policy.enabled_marker_classes),
                "enabled_marker_identity_sha256": list(self._p7c17_policy.safe_identity_hashes),
                "unrelated_removal_authority_sha256": _sha256(json.dumps(attribution, sort_keys=True).encode()),
            }
            facts_authority = P7C17RootOnlyOracleFactsAuthority(self.boot["oracle_facts"])
            facts_authority.write(facts)
            self._p7c17_facts = facts
            self._p7c17_evaluation = evaluate_p7c17_oracle_facts(facts)
            return _FROZEN_POST_DELETE_ACCEPTANCE(**kwargs)

        with patch.object(p7c13, "BoundedTargetOracle", oracle_factory), \
             patch.object(p7c13, "target_metadata_snapshot", snapshot), \
             patch.object(p7c13, "derived_unrelated_removal_fact", derived), \
             patch.object(p7c13, "post_delete_acceptance", acceptance), \
             patch.object(p7c16, "P7C16RuntimeManagerView", P7C17RuntimeManagerView):
            return await super().run_async()


class P7C17ChildResultAuthority(_RootOnlyJsonAuthority):
    schema = P7C17_CHILD_RESULT_SCHEMA

    def _validate(self, value: Any) -> dict[str, Any]:
        value = super()._validate(value)
        required = set(p7c16.P7C16ChildResultAuthority.KEYS) | {"oracle_facts_sha256", "failed_predicate_count"}
        if set(value) != required or value.get("status") not in {"PASS", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"} or type(value.get("verdict")) is not bool:
            raise P7C17PreparationError("P7.C17 child result schema invalid")
        if type(value["failed_predicate_count"]) is not int or value["failed_predicate_count"] < 0:
            raise P7C17PreparationError("P7.C17 child result oracle class invalid")
        return value

    @classmethod
    def write_payload(cls, path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
        return cls(path).write(payload)


def _p7c17_child_result_file_is_valid(path: Path, boot: Mapping[str, Any]) -> bool:
    try:
        value = P7C17ChildResultAuthority(path).read()
        return all(value.get(key) == boot.get(key) for key in ("source_head", "source_tree", "launcher_blob", "run_id_hash", "boot_authority_path"))
    except (OSError, UnicodeError, json.JSONDecodeError, P7C17PreparationError):
        return False


class P7C17DurableOneShotLedger(_RootOnlyJsonAuthority):
    schema = P7C17_LEDGER_SCHEMA
    MAX_BYTES = 8192

    def _validate(self, value: Any) -> dict[str, Any]:
        value = super()._validate(value)
        required = {"schema", "state", "source_head", "source_tree", "launcher_blob", "run_id_hash", "engine_profile_id", "effect_counts", "recovery"}
        if set(value) != required or value["state"] not in P7C17_STATES or any(not isinstance(value.get(key), str) or not value[key] for key in required - {"schema", "state", "effect_counts", "recovery"}):
            raise P7C17PreparationError("P7.C17 ledger schema invalid")
        if not isinstance(value["effect_counts"], dict) or not isinstance(value["recovery"], dict):
            raise P7C17PreparationError("P7.C17 ledger maps invalid")
        return value

    def reserve(self, value: Mapping[str, Any]) -> bool:
        if dict(value).get("state") != "RESERVED":
            raise P7C17PreparationError("P7.C17 ledger reservation invalid")
        try:
            return bool(self.write(value))
        except FileExistsError:
            self._check_identity(); return False

    def update(self, **changes: Any) -> dict[str, Any]:
        value = self.read()
        if set(changes) - {"state", "recovery"} or value["state"] != "RESERVED" or changes.get("state") not in P7C17_STATES - {"RESERVED"}:
            raise P7C17PreparationError("P7.C17 terminal transition invalid")
        value.update(changes)
        payload = (json.dumps(self._validate(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        fd = os.open(self.path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            current = os.fstat(fd)
            if self._identity != (current.st_dev, current.st_ino): raise P7C17PreparationError("P7.C17 ledger replacement")
            os.ftruncate(fd, 0); os.write(fd, payload); os.fsync(fd)
        finally:
            os.close(fd)
        return self.read()


def p7c17_exact_effect_pass_gate(counts: Mapping[str, int]) -> bool:
    return p7c16.p7c16_exact_effect_pass_gate(counts)


def _p7c17_boot(root: Path, contract: P7C17ArchitectContract) -> dict[str, Any]:
    authority = root / "authority"; authority.mkdir(mode=0o700); run_root = root / "run"; run_root.mkdir(mode=0o700)
    paths = p7c17_fresh_run_paths("a" * 24, root=run_root, authority=authority)
    paths["ledger_path"] = str(authority / "p7c17-one-shot.json"); paths["codex_home"] = str(root / "fake-home")
    Path(paths["codex_home"]).mkdir(mode=0o700)
    return {"schema": P7C17_BOOT_SCHEMA, "profile_id": P7C17_PROFILE_ID, "engine_profile_id": P7C17_PROFILE_ID,
            "source_head": contract.expected_head, "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
            "run_id_hash": _sha256("p7c17-synthetic"), "effect_ceiling": dict(p7c13.FROZEN_EFFECT_BUDGET), "codex_home": paths["codex_home"],
            "isolated_root": paths["isolated_root"], "isolated_sqlite": str(Path(paths["isolated_root"]) / "sqlite"),
            "isolated_logs": str(Path(paths["isolated_root"]) / "logs"), "controller_db": paths["controller_db"], "workdir": paths["workdir"],
            "approval_target": paths["approval_target"], "ledger_path": paths["ledger_path"], "boot_authority_path": paths["boot"],
            "child_result_path": paths["child_result"], "wire_path": paths["wire"], "approval_journal_path": paths["approval_journal"],
            "stage_journal_path": paths["stage"], "oracle_facts": paths["oracle_facts"], "unrelated_removal": paths["unrelated_removal"],
            "import_roots": list(P7C17_IMPORT_ROOTS), "deterministic_import_root": P7C17_PYTHONPATH, "runtime_authority": "/usr/local/bin/codex"}


def _p7c17_child_payload(boot: Mapping[str, Any], result: Mapping[str, Any], child: P7C17ProductionChildOrchestrator | None,
                         journal: Any) -> dict[str, Any]:
    budget = child.budget if child is not None else None
    facts = getattr(child, "_p7c17_evaluation", None)
    return {"schema": P7C17_CHILD_RESULT_SCHEMA, "status": result.get("status", "FAILED"), "verdict": bool(result.get("verdict", False)),
            "source_head": boot["source_head"], "source_tree": boot["source_tree"], "launcher_blob": boot["launcher_blob"],
            "run_id_hash": boot["run_id_hash"], "boot_authority_path": boot["boot_authority_path"],
            "effect_counts": {key: budget.count(key) if budget is not None else 0 for key in p7c13.FROZEN_EFFECT_BUDGET},
            "outcomes": dict(result.get("outcomes", {})), "classes": dict(result.get("classes", {})),
            "terminal_exception_class": result.get("terminal_exception_class"), "terminal_error_category": result.get("terminal_error_category"),
            "last_confirmed_stage": result.get("last_confirmed_stage", "PRE_CHILD"), "stage_journal_sha256": result.get("stage_journal_sha256") or journal.digest(),
            "runtime_child_quiescent": bool(result.get("runtime_child_quiescent", False)), "parent_process_group_quiescent": None,
            "oracle_facts_sha256": _sha256(Path(boot["oracle_facts"]).read_bytes()) if Path(boot["oracle_facts"]).exists() else "",
            "failed_predicate_count": len(facts.failed) if facts is not None else 0}


def p7c17_future_child_main(boot_path: str | Path, *, runtime_factory: Callable[[], Any] | None = None) -> int:
    boot = P7C17RootOnlyBootAuthority(boot_path).read(allow_test_home=runtime_factory is not None)
    journal = p7c16.P7C16StageJournal(boot["stage_journal_path"]); child: P7C17ProductionChildOrchestrator | None = None
    old_umask = os.umask(0o077)
    try:
        if runtime_factory is None: p7c13.InstalledRuntimeAuthority().verify()
        child = P7C17ProductionChildOrchestrator(boot, journal, runtime_factory=runtime_factory)
        result = asyncio.run(child.run_async()); payload = _p7c17_child_payload(boot, result, child, journal)
        P7C17ChildResultAuthority.write_payload(Path(boot["child_result_path"]), payload)
        return 0 if payload["status"] == "PASS" and payload["verdict"] else 1
    except BaseException as error:
        payload = _p7c17_child_payload(boot, {"status": "FAILED", "verdict": False, "last_confirmed_stage": child.last_confirmed_stage if child else "PRE_CHILD",
                                             "terminal_exception_class": type(error).__name__}, child, journal)
        try:
            journal.append("TERMINAL_EXCEPTION", "FAILED", effect_class="terminal", error=error)
            payload["stage_journal_sha256"] = journal.digest(); P7C17ChildResultAuthority.write_payload(Path(boot["child_result_path"]), payload)
        except (OSError, P7C17PreparationError): pass
        return 1
    finally:
        os.umask(old_umask)


def _p7c17_parse_child_boot(arguments: Sequence[str]) -> Path:
    if len(arguments) != 3 or arguments.count("--p7c17-future-child") != 1 or arguments.count("--boot-authority") != 1:
        raise P7C17PreparationError("P7.C17 child arguments invalid")
    index = arguments.index("--boot-authority")
    if not os.path.isabs(arguments[index + 1]):
        raise P7C17PreparationError("P7.C17 boot authority missing")
    return Path(arguments[index + 1]).absolute()


class P7C17PreparedFutureExecutor:
    def __init__(self, ledger: P7C17DurableOneShotLedger, *, watchdog: Any | None = None,
                 child_dispatch: Callable[[Path], int] | None = None, run_paths: Mapping[str, str] | None = None,
                 boot_path: Path | None = None, test_only_codex_home: Path | None = None,
                 test_only_watchdog_bounds: tuple[float, float, float] | None = None, mutation_events: list[str] | None = None) -> None:
        self.ledger, self.watchdog, self.child_dispatch = ledger, watchdog, child_dispatch
        self.run_paths, self.boot_path, self.test_only_codex_home = dict(run_paths or {}), boot_path, test_only_codex_home
        self.test_only_watchdog_bounds, self.calls, self.mutation_events = test_only_watchdog_bounds, 0, mutation_events or []

    @classmethod
    def production(cls, contract: P7C17ArchitectContract) -> "P7C17PreparedFutureExecutor":
        return cls._production_with_authority(contract, ledger_path=P7C17_LEDGER_PATH)

    @classmethod
    def _production_with_authority(cls, contract: P7C17ArchitectContract, *, ledger_path: Path,
                                   child_dispatch: Callable[[Path], int] | None = None,
                                   test_only_codex_home: Path | None = None,
                                   test_only_watchdog_bounds: tuple[float, float, float] | None = None,
                                   mutation_events: list[str] | None = None) -> "P7C17PreparedFutureExecutor":
        run_hash = _sha256(os.urandom(32)); state_parent = ledger_path.parent.parent / f"p7c17-state-parent-{run_hash[:12]}"
        work_parent = ledger_path.parent.parent / f"p7c17-work-parent-{run_hash[:12]}"
        paths = p7c17_fresh_run_paths(run_hash, root=state_parent, authority=ledger_path.parent)
        paths["workdir"] = str(work_parent / f"p7c17-work-{run_hash[:32]}"); boot_path = Path(paths["boot"])
        paths["ledger_path"] = str(ledger_path); paths["codex_home"] = str(test_only_codex_home or "/root/.codex_second")
        record = {"schema": P7C17_LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head,
                  "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob, "run_id_hash": run_hash,
                  "engine_profile_id": P7C17_PROFILE_ID, "effect_counts": {}, "recovery": {}}
        watchdog = p7c13.OwnedParentChildWatchdog()
        executor = cls(P7C17DurableOneShotLedger(ledger_path), watchdog=watchdog, child_dispatch=child_dispatch,
                       run_paths=paths, boot_path=boot_path, test_only_codex_home=test_only_codex_home,
                       test_only_watchdog_bounds=test_only_watchdog_bounds, mutation_events=mutation_events)
        executor._record = record
        return executor

    def run(self, contract: P7C17ArchitectContract) -> Any:
        if self.calls: raise P7C17PreparationError("second child/retry forbidden")
        self.calls += 1; record = self._record
        if not self.ledger.reserve(record): raise P7C17PreparationError("P7.C17 reservation consumed")
        self.mutation_events.append("LEDGER_RESERVED")
        for key in ("isolated_root", "workdir"):
            parent = Path(self.run_paths[key]).parent; parent.mkdir(mode=0o700, exist_ok=False); self.mutation_events.append("RUN_PARENT_CREATED")
        if self.test_only_codex_home is not None:
            home = Path(self.test_only_codex_home); home.mkdir(mode=0o700, parents=True, exist_ok=True)
            sessions = home / "sessions"; sessions.mkdir(mode=0o700); (sessions / "unrelated-retained.jsonl").write_text("historical Turn 3 and Turn 4 wording; sleep 120\n", encoding="utf-8")
        boot = _p7c17_boot_from_paths(self.run_paths, self.ledger.path, self.boot_path, contract, record, self.test_only_codex_home)
        P7C17RootOnlyBootAuthority(self.boot_path).create(boot, allow_test_home=self.test_only_codex_home is not None); self.mutation_events.append("BOOT_CREATED")
        class OfflineProcess:
            pid = os.getpid(); returncode = 0
            def wait(inner, timeout: float | None = None) -> int:
                del timeout; inner.returncode = self.child_dispatch(Path(boot["boot_authority_path"])) if self.child_dispatch else 1; return inner.returncode
        if self.child_dispatch is not None:
            self.watchdog.process_factory = lambda *_args, **_kwargs: OfflineProcess()
            self.watchdog.active_group_probe = lambda _pgid: 0; self.watchdog.zombie_group_probe = lambda _pgid: 0; self.watchdog.group_scan_error_probe = lambda _pgid: 0
            command = ("p7c17-future-child", "--boot-authority", boot["boot_authority_path"])
        else:
            command = ("/usr/bin/env", f"PYTHONPATH={P7C17_PYTHONPATH}", "/usr/bin/python", "-m",
                       "tests.real.test_p7_c17_final_hard_delete_successor", "--p7c17-future-child",
                       "--boot-authority", boot["boot_authority_path"])
        self.mutation_events.append("CHILD_DISPATCHED")
        bounds = self.test_only_watchdog_bounds or (p7c16.P7C16_REAL_WATCHDOG_HARD_DEADLINE, p7c13.REAL_WATCHDOG_TERM_GRACE, p7c13.REAL_WATCHDOG_KILL_GRACE)
        observed = self.watchdog.run(command, result_path=boot["child_result_path"],
                                     timeout_seconds=bounds[0], term_grace_seconds=bounds[1], kill_grace_seconds=bounds[2],
                                     result_validator=lambda path: _p7c17_child_result_file_is_valid(Path(path), boot))
        try: result = P7C17ChildResultAuthority(boot["child_result_path"]).read()
        except (OSError, P7C17PreparationError, json.JSONDecodeError): result = None
        if result and Path(boot["oracle_facts"]).exists():
            try:
                P7C17RootOnlyOracleFactsAuthority(boot["oracle_facts"]).read(expected={
                    "source_head": contract.expected_head, "source_tree": contract.expected_tree,
                    "launcher_blob": contract.expected_launcher_blob, "run_id_hash": record["run_id_hash"],
                    "boot_authority_sha256": _sha256(Path(boot["boot_authority_path"]).read_bytes()),
                })
                facts_valid = True
            except (OSError, P7C17PreparationError, json.JSONDecodeError):
                facts_valid = False
        else:
            facts_valid = False
        state = "COMPLETED" if result and facts_valid and observed.status == "COMPLETED" and result["status"] == "PASS" and result["verdict"] and p7c17_exact_effect_pass_gate(result["effect_counts"]) and result["runtime_child_quiescent"] else (result["status"] if result and result["status"] in {"UNKNOWN", "CONFIRMED_PENDING"} else "FAILED")
        self.ledger.update(state=state, recovery={"watchdog_status": observed.status, "child_count": observed.child_count,
                                                   "retry_count": getattr(self.watchdog, "retry_count", 0), "oracle_facts": result.get("oracle_facts_sha256") if result else None})
        return observed


def _p7c17_boot_from_paths(paths: Mapping[str, str], ledger: Path, boot_path: Path, contract: P7C17ArchitectContract,
                           record: Mapping[str, Any], home: Path | None) -> dict[str, Any]:
    isolated = paths["isolated_root"]
    return {"schema": P7C17_BOOT_SCHEMA, "profile_id": P7C17_PROFILE_ID, "engine_profile_id": P7C17_PROFILE_ID,
            "source_head": contract.expected_head, "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
            "run_id_hash": record["run_id_hash"], "effect_ceiling": dict(p7c13.FROZEN_EFFECT_BUDGET), "codex_home": str(home or "/root/.codex_second"),
            "isolated_root": isolated, "isolated_sqlite": str(Path(isolated) / "sqlite"), "isolated_logs": str(Path(isolated) / "logs"),
            "controller_db": paths["controller_db"], "workdir": paths["workdir"], "approval_target": paths["approval_target"], "ledger_path": str(ledger),
            "boot_authority_path": str(boot_path), "child_result_path": paths["child_result"], "wire_path": paths["wire"],
            "approval_journal_path": paths["approval_journal"], "stage_journal_path": paths["stage"], "oracle_facts": paths["oracle_facts"],
            "unrelated_removal": paths["unrelated_removal"], "import_roots": list(P7C17_IMPORT_ROOTS), "deterministic_import_root": P7C17_PYTHONPATH,
            "runtime_authority": "/usr/local/bin/codex"}


def p7c17_real_entrypoint(*, environ: Mapping[str, str], authority: P7C17SourceAuthority | None = None,
                          executor: P7C17PreparedFutureExecutor | None = None) -> Any:
    current = authority or current_p7c17_source_authority(); contract = _contract_from_environment(environ)
    if not p7c17_source_bundle_gate(environ, contract, current):
        raise P7C17PreparationError("P7C17_FUTURE_REAL_GATE=DISABLED_OR_SOURCE_MISMATCH")
    selected = executor or P7C17PreparedFutureExecutor.production(contract)
    return selected.run(contract)


def reproduce_p7c17_old_static_marker_false_positive() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p7c17-old-marker-") as directory:
        root = Path(directory); home = root / "home"; sessions = home / "sessions"; sessions.mkdir(mode=0o700, parents=True)
        memory, response = p7c13.fresh_non_secret_markers(); target = "/tmp/p7c17-current-target"; prompt = p7c13.c11_explicit_escalation_prompt(target)
        (sessions / "unrelated-retained.jsonl").write_text("old Turn 3 wording; old Turn 4 wording; sleep 120\n", encoding="utf-8")
        profile = p7c13.CodexProfile("p7c17", str(home), "P7.C17", str(root / "isolated"))
        current_context = {"memory_marker": memory, "response_marker": response, "approval_target": target, "turn3_prompt": prompt}
        markers = (memory.encode(), response.encode(), target.encode(), prompt.encode(), p7c13.TURN4_STIMULUS.encode())
        old_count = p7c13.BoundedTargetOracle(profile, "thread-p7c17", markers).observe().marker_count
        corrected_count = P7C17BoundedTargetOracle(profile, "thread-p7c17", markers, policy=P7C17CurrentRunMarkerPolicy(target)).observe().marker_count
        return {"current_run_context": current_context, "old_count": old_count, "corrected_count": corrected_count, "reproduced": old_count > 0}


def _synthetic_facts(**changes: Any) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "schema": P7C17_ORACLE_FACTS_SCHEMA, "source_head": "h" * 40, "source_tree": "t" * 40,
        "launcher_blob": "l" * 40, "run_id_hash": "r" * 64, "boot_authority_sha256": "b" * 64,
        "boot_identity_class": "ROOT_0600_REGULAR_NLINK1", "official_delete_class": "DELETE_CONFIRMED",
        "application_delete_class": "DELETED", "tombstone_bounded": True, "live_binding_present": False,
        "post_delete_schema_class": "V4", "post_delete_schema_version": 4, "isolation_envelope_class": "VALID",
        "isolated_sqlite_regular_descendants": 0, "isolated_sqlite_special_descendants": 0, "isolated_sqlite_symlinks": 0,
        "isolated_sqlite_scan_errors": 0, "isolated_logs_regular_descendants": 0, "isolated_logs_special_descendants": 0,
        "isolated_logs_symlinks": 0, "isolated_logs_scan_errors": 0, "persistent_thread_count": 0,
        "persistent_thread_filename_count": 0, "persistent_thread_directory_count": 0, "persistent_marker_count": 0,
        "persistent_scan_errors": 0, "isolated_thread_count": 0, "isolated_marker_count": 0, "isolated_scan_errors": 0,
        "combined_scan_errors": 0, "unrelated_target_specific_removal_detected": False, "recovery_class": "COMPLETED",
        "budgets_ok": True, "runtime_child_quiescent": True, "marker_policy_class": "P7C17CurrentRunMarkerPolicy",
        "marker_policy_version": P7C17_MARKER_POLICY_VERSION, "enabled_marker_classes": ["memory_marker", "response_marker"],
        "enabled_marker_identity_sha256": ["a" * 64, "c" * 64], "unrelated_removal_authority_sha256": "u" * 64,
    }
    facts.update(changes)
    return facts


def _valid_marker_tuple(target: str = "/tmp/p7c17-target") -> tuple[bytes, ...]:
    return (b"memory-current-run-0123456789", b"response-current-run-0123456789", target.encode(),
            p7c13.c11_explicit_escalation_prompt(target).encode(), p7c13.TURN4_STIMULUS.encode())


class P7C17MarkerPolicyTests(unittest.TestCase):
    def test_old_static_marker_false_positive_is_reproduced(self) -> None:
        result = reproduce_p7c17_old_static_marker_false_positive()
        self.assertTrue(result["reproduced"]); self.assertGreater(result["old_count"], 0); self.assertEqual(0, result["corrected_count"])

    def test_shape_is_fail_closed_and_fixed_behavioral_stimulus_is_excluded(self) -> None:
        target = "/tmp/p7c17-target"; policy = P7C17CurrentRunMarkerPolicy(target)
        selected = policy.select(_valid_marker_tuple(target))
        self.assertEqual(4, len(selected)); self.assertNotIn(p7c13.TURN4_STIMULUS.encode(), selected)
        for index, replacement in ((0, b"short"), (1, b"short"), (2, b"wrong-target"), (3, b"generic Turn 3"), (4, b"common")):
            values = list(_valid_marker_tuple(target)); values[index] = replacement
            with self.subTest(index=index), self.assertRaises(P7C17PreparationError): policy.select(values)

    def test_unrelated_static_text_and_historical_markers_are_immune(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c17-marker-matrix-") as directory:
            root = Path(directory); home = root / "home"; sessions = home / "sessions"; sessions.mkdir(mode=0o700, parents=True)
            target = "/tmp/p7c17-target"; values = _valid_marker_tuple(target)
            (sessions / "historical.jsonl").write_text("sleep 120; generic Turn 3; generic Turn 4; P7C16 historical marker\n", encoding="utf-8")
            profile = p7c13.CodexProfile("p7c17", str(home), "P7.C17", str(root / "isolated"))
            observed = P7C17BoundedTargetOracle(profile, "thread-p7c17", values, policy=P7C17CurrentRunMarkerPolicy(target)).observe()
            self.assertEqual(0, observed.marker_count)
            for marker in values[:4]:
                (sessions / "residual.jsonl").write_bytes(marker)
                residual = P7C17BoundedTargetOracle(profile, "thread-p7c17", values, policy=P7C17CurrentRunMarkerPolicy(target)).observe()
                self.assertGreater(residual.marker_count, 0)
                (sessions / "residual.jsonl").unlink()

    def test_thread_filename_directory_isolated_and_scan_residuals_remain_independent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c17-residual-matrix-") as directory:
            root = Path(directory); home = root / "home"; sessions = home / "sessions"; sessions.mkdir(mode=0o700, parents=True)
            target = "/tmp/p7c17-target"; values = _valid_marker_tuple(target); profile = p7c13.CodexProfile("p7c17", str(home), "P7.C17", str(root / "isolated"))
            policy = P7C17CurrentRunMarkerPolicy(target)
            (sessions / "thread-p7c17.jsonl").write_bytes(b"thread-p7c17")
            self.assertGreater(P7C17BoundedTargetOracle(profile, "thread-p7c17", values, policy=policy).observe().thread_count, 0)
            (sessions / "thread-p7c17.jsonl").unlink(); (sessions / "thread-p7c17").mkdir()
            self.assertGreater(P7C17BoundedTargetOracle(profile, "thread-p7c17", values, policy=policy).observe().thread_directory_count, 0)
            (sessions / "thread-p7c17").rmdir(); isolated = Path(profile.isolated_state_root) / "sqlite"; isolated.mkdir(mode=0o700, parents=True)
            (isolated / "residual").write_bytes(b"thread-p7c17" + values[0])
            observed = P7C17BoundedTargetOracle(profile, "thread-p7c17", values, policy=policy, families=("isolated_sqlite",)).observe()
            self.assertGreater(observed.thread_count, 0); self.assertGreater(observed.marker_count, 0)
            (isolated / "link").symlink_to(isolated / "residual")
            self.assertGreater(P7C17BoundedTargetOracle(profile, "thread-p7c17", values, policy=policy, families=("isolated_sqlite",)).observe().scan_errors, 0)


class P7C17OracleFactsTests(unittest.TestCase):
    def test_failed_predicate_is_exactly_recoverable(self) -> None:
        facts = _synthetic_facts(persistent_marker_count=1)
        evaluation = evaluate_p7c17_oracle_facts(facts)
        self.assertEqual(frozenset({"persistent.marker_count == 0"}), evaluation.failed)
        self.assertEqual(frozenset(), evaluation.unavailable)

    def test_root_only_facts_correlation_and_safety_matrix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c17-facts-") as directory:
            root = Path(directory); path = root / "facts.json"; authority = P7C17RootOnlyOracleFactsAuthority(path); facts = _synthetic_facts()
            self.assertEqual(facts, authority.write(facts)); self.assertEqual(facts, authority.read(expected={"source_head": "h" * 40, "run_id_hash": "r" * 64}))
            for key, wrong in (("source_head", "x" * 40), ("run_id_hash", "x" * 64), ("boot_authority_sha256", "x" * 64)):
                with self.subTest(key=key), self.assertRaises(P7C17PreparationError): authority.read(expected={key: wrong})
            duplicate = root / "duplicate.json"; duplicate.write_text('{"schema":"p7c17-oracle-facts-v1","schema":"p7c17-oracle-facts-v1"}\n', encoding="utf-8"); os.chmod(duplicate, 0o600)
            with self.assertRaises(P7C17PreparationError): P7C17RootOnlyOracleFactsAuthority(duplicate).read()
            link = root / "link.json"; link.symlink_to(path)
            with self.assertRaises(P7C17PreparationError): P7C17RootOnlyOracleFactsAuthority(link).read()
            hardlink = root / "hardlink.json"; os.link(path, hardlink)
            with self.assertRaises(P7C17PreparationError): P7C17RootOnlyOracleFactsAuthority(hardlink).read()
            os.chmod(path, 0o644)
            with self.assertRaises(P7C17PreparationError): authority.read()

    def test_unrelated_removal_attribution_is_safe_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c17-attribution-") as directory:
            root = Path(directory); target = str(root / "target"); unrelated = str(root / "unrelated")
            source = {"source_head": "h" * 40, "source_tree": "t" * 40, "launcher_blob": "l" * 40,
                      "run_id_hash": "r" * 64, "boot_authority_sha256": "b" * 64}
            before = {target: (1, 1), unrelated: (1, 2)}; after_target = {unrelated: (1, 2)}
            false_record = _p7c17_safe_attribution(before, after_target, {target}, source=source, path=root / "false.json")
            self.assertFalse(false_record["unrelated_removed"]); self.assertEqual([], false_record["removed_unrelated_path_hashes"])
            after_unrelated = {target: (1, 1)}
            true_record = _p7c17_safe_attribution(before, after_unrelated, {target}, source=source, path=root / "true.json")
            self.assertTrue(true_record["unrelated_removed"]); self.assertEqual(1, true_record["removed_unrelated_count"])
            self.assertNotIn(target, json.dumps(true_record)); self.assertNotIn(unrelated, json.dumps(true_record))


class P7C17HandoffTests(unittest.TestCase):
    def _authority_environment(self) -> tuple[P7C17SourceAuthority, P7C17ArchitectContract, dict[str, str]]:
        actual = current_p7c17_source_authority()
        values = (actual.head, actual.tree, actual.launcher_blob, actual.p7c16_launcher_blob, actual.p7c15_launcher_blob,
                  actual.p7c14_launcher_blob, actual.p7c13_harness_blob, actual.p7c12_matcher_blob, actual.tests_init_blob, actual.tests_real_init_blob)
        contract = P7C17ArchitectContract("synthetic-token", *values)
        names = (P7C17_EXPECTED_HEAD, P7C17_EXPECTED_TREE, P7C17_EXPECTED_LAUNCHER_BLOB, P7C17_EXPECTED_P7C16_LAUNCHER_BLOB,
                 P7C17_EXPECTED_P7C15_LAUNCHER_BLOB, P7C17_EXPECTED_P7C14_LAUNCHER_BLOB, P7C17_EXPECTED_P7C13_HARNESS_BLOB,
                 P7C17_EXPECTED_P7C12_MATCHER_BLOB, P7C17_EXPECTED_TESTS_INIT_BLOB, P7C17_EXPECTED_TESTS_REAL_INIT_BLOB)
        return actual, contract, {P7C17_FUTURE_REAL_GATE: "synthetic-token", **dict(zip(names, values))}

    def test_default_entrypoint_full_production_shaped_handoff_and_exact_effects(self) -> None:
        authority, contract, environment = self._authority_environment()
        with tempfile.TemporaryDirectory(prefix="p7c17-handoff-") as directory:
            root = Path(directory); ledger = root / "authority" / "p7c17-one-shot.json"; home = root / "home"
            def dispatch(boot: Path) -> int:
                return p7c17_future_child_main(boot, runtime_factory=p7c16._P7C16UnderlyingFakeRuntimeManager)
            executor = P7C17PreparedFutureExecutor._production_with_authority(
                contract, ledger_path=ledger, child_dispatch=dispatch, test_only_codex_home=home, test_only_watchdog_bounds=(10, 1, 1))
            with patch.object(P7C17PreparedFutureExecutor, "production", return_value=executor):
                observed = p7c17_real_entrypoint(environ=environment, authority=authority, executor=None)
            self.assertEqual("COMPLETED", observed.status); self.assertEqual("COMPLETED", P7C17DurableOneShotLedger(ledger).read()["state"])
            result = P7C17ChildResultAuthority(executor.run_paths["child_result"]).read()
            self.assertEqual({"new_threads": 1, "model/list": 1, "thread/start": 1, "thread/resume": 1, "turn/start": 4,
                              "approval_responses": 1, "allow_responses": 1, "turn/interrupt": 1, "thread/delete": 1,
                              "thread/read": 0, "thread/list": 0, "second_child": 0, "real_retry": 0, "telegram": 0}, result["effect_counts"])
            facts = P7C17RootOnlyOracleFactsAuthority(executor.run_paths["oracle_facts"]).read()
            self.assertEqual(0, facts["persistent_marker_count"]); self.assertEqual(0, facts["combined_scan_errors"])
            self.assertEqual(0, result["failed_predicate_count"]); self.assertEqual(1, result["effect_counts"]["thread/delete"])

    def test_disabled_entrypoint_has_zero_effect_and_no_real_ledger(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c17-disabled-") as directory, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(2, _module_main(["--p7c17-real-run"]))
            self.assertFalse(P7C17_LEDGER_PATH.exists()); self.assertFalse(Path(directory, "p7c17-one-shot.json").exists())

    def test_unknown_and_pending_are_terminal_without_second_delete(self) -> None:
        contract = P7C17ArchitectContract("token", "h", "t", "l", "l16", "l15", "l14", "l13", "l12", "ti", "tri")
        for scenario, expected in (("delete_unknown", "UNKNOWN"), ("confirmed_pending", "CONFIRMED_PENDING")):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory(prefix="p7c17-terminal-") as directory:
                root = Path(directory); boot = _p7c17_boot(root, contract); P7C17RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot, allow_test_home=True)
                manager = p7c16._P7C16UnderlyingFakeRuntimeManager(scenario=scenario)
                self.assertEqual(1, p7c17_future_child_main(boot["boot_authority_path"], runtime_factory=lambda: manager))
                result = P7C17ChildResultAuthority(boot["child_result_path"]).read()
                self.assertEqual(expected, result["status"]); self.assertEqual(1, manager.client.calls.count("thread/delete")); self.assertEqual(0, result["effect_counts"]["real_retry"])


def _module_main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--p7c17-real-run" in arguments:
        try: return 0 if getattr(p7c17_real_entrypoint(environ=dict(os.environ)), "status", "") == "COMPLETED" else 1
        except P7C17PreparationError: return 2
    if "--p7c17-future-child" in arguments:
        try:
            return p7c17_future_child_main(_p7c17_parse_child_boot(arguments))
        except (IndexError, OSError, P7C17PreparationError, ValueError): return 1
    unittest.main(argv=[sys.argv[0], *arguments]); return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
