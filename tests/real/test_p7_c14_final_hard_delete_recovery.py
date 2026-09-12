"""P7.C14 launcher recovery preparation.

This is a thin successor parent around the accepted P7.C13 implementation.
It owns a distinct gate and replay ledger; preparation never enters either
real child execution or the accepted P7.C13 parent entrypoint.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import os
import secrets
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from unittest.mock import Mock

from tests.real import test_p7_c13_final_hard_delete_acceptance as p7c13


P7C14_FUTURE_REAL_GATE = "P7C14_FUTURE_REAL_GATE"
P7C14_EXPECTED_HEAD = os.environ.get("P7C14_EXPECTED_HEAD", "")
P7C14_EXPECTED_TREE = os.environ.get("P7C14_EXPECTED_TREE", "")
P7C14_EXPECTED_LAUNCHER_BLOB = os.environ.get("P7C14_EXPECTED_LAUNCHER_BLOB", "")
P7C14_EXPECTED_P7C13_HARNESS_BLOB = os.environ.get("P7C14_EXPECTED_P7C13_HARNESS_BLOB", "")
P7C14_EXPECTED_P7C12_MATCHER_BLOB = os.environ.get("P7C14_EXPECTED_P7C12_MATCHER_BLOB", "")

P7C14_EXPECTED_P7C13_HARNESS_BLOB_VALUE = "5a1fe8e32cd985b1e1845d73266211632e33950c"
P7C14_EXPECTED_P7C12_MATCHER_BLOB_VALUE = "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1"
P7C14_LEDGER_PATH = Path("/root/.codexcontrol/p7c14-one-shot.json")
P7C13_LEDGER_PATH = Path("/root/.codexcontrol/p7c13-one-shot.json")
P7C14_IMPORT_ROOTS = ("/root/CodexControl/src", "/root/CodexControl")
P7C14_PYTHONPATH = os.pathsep.join(P7C14_IMPORT_ROOTS)


class P7C14PreparationGateError(RuntimeError):
    """Finite, fail-closed successor preparation error."""


@dataclass(frozen=True)
class P7C14SourceAuthority:
    head: str
    tree: str
    launcher_blob: str
    p7c13_harness_blob: str
    p7c12_matcher_blob: str
    tests_init_blob: str
    tests_real_init_blob: str
    import_root_authority: bool
    tracked_clean: bool


@dataclass(frozen=True)
class P7C14ArchitectContract:
    """A later architect contract; no token is created by preparation."""

    authorization_token: str
    expected_head: str
    expected_tree: str
    expected_launcher_blob: str
    expected_p7c13_harness_blob: str
    expected_p7c12_matcher_blob: str
    expected_tests_init_blob: str
    expected_tests_real_init_blob: str
    expected_import_roots: tuple[str, str] = P7C14_IMPORT_ROOTS


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _repository() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments), cwd=_repository(), check=True,
        capture_output=True, text=True,
    )
    return completed.stdout.strip()


def _blob(path: Path) -> str:
    return _git("hash-object", str(path))


def _spec_is_under(spec: object, root: Path) -> bool:
    origin = getattr(spec, "origin", None)
    if not isinstance(origin, str) or origin in {"built-in", "frozen"}:
        return False
    try:
        Path(origin).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def validate_p7c14_import_root_authority(environ: dict[str, str] | None = None) -> bool:
    """Validate exact future roots and bounded module specs before ledger use."""
    environment = os.environ if environ is None else environ
    if environment.get("PYTHONPATH") != P7C14_PYTHONPATH:
        return False
    repository = _repository()
    source = repository / "src"
    tests_root = repository / "tests"
    codex_spec = importlib.machinery.PathFinder.find_spec("codex_control", [str(source)])
    tests_spec = importlib.machinery.PathFinder.find_spec("tests", [str(repository)])
    if not _spec_is_under(codex_spec, source) or not _spec_is_under(tests_spec, tests_root):
        return False
    loaded = sys.modules.get("tests")
    if loaded is not None and not _spec_is_under(getattr(loaded, "__spec__", None), tests_root):
        return False
    codex_loaded = sys.modules.get("codex_control")
    return codex_loaded is None or _spec_is_under(getattr(codex_loaded, "__spec__", None), source)


def current_p7c14_source_authority() -> P7C14SourceAuthority:
    """Read source/index/hash authority; this function has no write effects."""
    repository = _repository()
    tracked_clean = (
        subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repository).returncode == 0
        and subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repository).returncode == 0
    )
    return P7C14SourceAuthority(
        head=_git("rev-parse", "HEAD"),
        tree=_git("rev-parse", "HEAD^{tree}"),
        launcher_blob=_blob(Path(__file__).resolve()),
        p7c13_harness_blob=_blob(repository / "tests/real/test_p7_c13_final_hard_delete_acceptance.py"),
        p7c12_matcher_blob=_blob(repository / "tests/real/test_p7_c12_strict_approval_matcher.py"),
        tests_init_blob=_blob(repository / "tests/__init__.py"),
        tests_real_init_blob=_blob(repository / "tests/real/__init__.py"),
        import_root_authority=validate_p7c14_import_root_authority(),
        tracked_clean=tracked_clean,
    )


def p7c14_source_bundle_gate(
    environ: dict[str, str], contract: P7C14ArchitectContract | None,
    authority: P7C14SourceAuthority,
) -> bool:
    """Match every successor authority before selecting an executor."""
    if contract is None or not isinstance(contract, P7C14ArchitectContract):
        return False
    expected = (
        contract.authorization_token, contract.expected_head, contract.expected_tree,
        contract.expected_launcher_blob, contract.expected_p7c13_harness_blob,
        contract.expected_p7c12_matcher_blob, contract.expected_tests_init_blob,
        contract.expected_tests_real_init_blob,
    )
    if not all(expected) or contract.expected_import_roots != P7C14_IMPORT_ROOTS:
        return False
    return (
        environ.get(P7C14_FUTURE_REAL_GATE) == contract.authorization_token
        and environ.get("P7C14_EXPECTED_HEAD") == contract.expected_head
        and environ.get("P7C14_EXPECTED_TREE") == contract.expected_tree
        and environ.get("P7C14_EXPECTED_LAUNCHER_BLOB") == contract.expected_launcher_blob
        and environ.get("P7C14_EXPECTED_P7C13_HARNESS_BLOB") == contract.expected_p7c13_harness_blob
        and environ.get("P7C14_EXPECTED_P7C12_MATCHER_BLOB") == contract.expected_p7c12_matcher_blob
        and environ.get("P7C14_EXPECTED_TESTS_INIT_BLOB") == contract.expected_tests_init_blob
        and environ.get("P7C14_EXPECTED_TESTS_REAL_INIT_BLOB") == contract.expected_tests_real_init_blob
        and authority.head == contract.expected_head
        and authority.tree == contract.expected_tree
        and authority.launcher_blob == contract.expected_launcher_blob
        and authority.p7c13_harness_blob == contract.expected_p7c13_harness_blob
        and authority.p7c12_matcher_blob == contract.expected_p7c12_matcher_blob
        and authority.tests_init_blob == contract.expected_tests_init_blob
        and authority.tests_real_init_blob == contract.expected_tests_real_init_blob
        and authority.import_root_authority
        and authority.tracked_clean
    )


def _contract_from_environment(environ: dict[str, str]) -> P7C14ArchitectContract:
    return P7C14ArchitectContract(
        authorization_token=environ.get(P7C14_FUTURE_REAL_GATE, ""),
        expected_head=environ.get("P7C14_EXPECTED_HEAD", ""),
        expected_tree=environ.get("P7C14_EXPECTED_TREE", ""),
        expected_launcher_blob=environ.get("P7C14_EXPECTED_LAUNCHER_BLOB", ""),
        expected_p7c13_harness_blob=environ.get("P7C14_EXPECTED_P7C13_HARNESS_BLOB", ""),
        expected_p7c12_matcher_blob=environ.get("P7C14_EXPECTED_P7C12_MATCHER_BLOB", ""),
        expected_tests_init_blob=environ.get("P7C14_EXPECTED_TESTS_INIT_BLOB", ""),
        expected_tests_real_init_blob=environ.get("P7C14_EXPECTED_TESTS_REAL_INIT_BLOB", ""),
    )


class P7C14PreparedFutureRealExecutor(p7c13.PreparedFutureRealExecutor):
    """Accepted child/delete implementation with a P7.C14 replay authority."""

    @staticmethod
    def _adapt_contract(
        contract: P7C14ArchitectContract | None,
    ) -> p7c13.FutureArchitectContract:
        """Adapt successor source authority to the frozen inherited interface."""
        if contract is None or not isinstance(contract, P7C14ArchitectContract):
            raise P7C14PreparationGateError("valid P7.C14 contract required")
        required = (
            contract.authorization_token, contract.expected_head, contract.expected_tree,
            contract.expected_launcher_blob, contract.expected_p7c13_harness_blob,
            contract.expected_p7c12_matcher_blob, contract.expected_tests_init_blob,
            contract.expected_tests_real_init_blob,
        )
        if not all(required) or contract.expected_import_roots != P7C14_IMPORT_ROOTS:
            raise P7C14PreparationGateError("P7.C14 contract malformed")
        return p7c13.FutureArchitectContract(
            authorization_token=contract.authorization_token,
            expected_head=contract.expected_head,
            expected_tree=contract.expected_tree,
            expected_harness_blob=contract.expected_p7c13_harness_blob,
        )

    def run(self, *, contract: P7C14ArchitectContract | None = None) -> object:
        """Enter the inherited executor only through an explicit adaptation."""
        adapted = self._adapt_contract(contract)
        return super().run(contract=adapted)

    @classmethod
    def production(cls, contract: P7C14ArchitectContract) -> "P7C14PreparedFutureRealExecutor":
        record = {
            "schema": p7c13.LEDGER_SCHEMA,
            "state": "RESERVED",
            "source_head": contract.expected_head,
            "source_tree": contract.expected_tree,
            "harness_blob": contract.expected_p7c13_harness_blob,
            "run_id_hash": _sha256(secrets.token_bytes(32)),
            "path_hashes": {"ledger": _sha256(str(P7C14_LEDGER_PATH))},
            "effect_counts": {},
            "recovery": {},
        }
        return cls(
            ledger=p7c13.DurableOneShotLedger(P7C14_LEDGER_PATH),
            watchdog=p7c13.OwnedParentChildWatchdog(), child_command=(),
            result_path=P7C14_LEDGER_PATH.with_name("p7c14-child-result-pending.json"),
            record=record,
            child_factory=lambda boot_path: (
                "/usr/bin/env", f"PYTHONPATH={P7C14_PYTHONPATH}", sys.executable,
                "-m", "tests.real.test_p7_c13_final_hard_delete_acceptance",
                "--p7c13-future-child", "--boot-authority", str(boot_path),
            ),
            fresh_production=True,
        )


def p7c14_real_entrypoint(
    *, environ: dict[str, str], authority: P7C14SourceAuthority | None = None,
    executor: p7c13.FutureRealExecutor | None = None,
    contract: P7C14ArchitectContract | None = None,
) -> object:
    """Parent boundary: source/import gate, then distinct P7.C14 executor."""
    current = authority or current_p7c14_source_authority()
    selected_contract = contract or _contract_from_environment(environ)
    if not p7c14_source_bundle_gate(environ, selected_contract, current):
        raise P7C14PreparationGateError("P7C14_FUTURE_REAL_GATE=DISABLED_OR_SOURCE_MISMATCH")
    selected = executor or P7C14PreparedFutureRealExecutor.production(selected_contract)
    return selected.run(contract=selected_contract)


def _synthetic_authority() -> P7C14SourceAuthority:
    return P7C14SourceAuthority(
        "synthetic-p7c14-head", "synthetic-p7c14-tree", "synthetic-p7c14-launcher",
        "synthetic-p7c13-harness", "synthetic-p7c12-matcher", "synthetic-tests", "synthetic-tests-real",
        True, True,
    )


def _synthetic_contract() -> P7C14ArchitectContract:
    return P7C14ArchitectContract(
        "offline-token", "synthetic-p7c14-head", "synthetic-p7c14-tree", "synthetic-p7c14-launcher",
        "synthetic-p7c13-harness", "synthetic-p7c12-matcher", "synthetic-tests", "synthetic-tests-real",
    )


def _synthetic_environment(contract: P7C14ArchitectContract) -> dict[str, str]:
    return {
        P7C14_FUTURE_REAL_GATE: contract.authorization_token,
        "P7C14_EXPECTED_HEAD": contract.expected_head,
        "P7C14_EXPECTED_TREE": contract.expected_tree,
        "P7C14_EXPECTED_LAUNCHER_BLOB": contract.expected_launcher_blob,
        "P7C14_EXPECTED_P7C13_HARNESS_BLOB": contract.expected_p7c13_harness_blob,
        "P7C14_EXPECTED_P7C12_MATCHER_BLOB": contract.expected_p7c12_matcher_blob,
        "P7C14_EXPECTED_TESTS_INIT_BLOB": contract.expected_tests_init_blob,
        "P7C14_EXPECTED_TESTS_REAL_INIT_BLOB": contract.expected_tests_real_init_blob,
    }


class P7C14OfflineAuthorityTests(unittest.TestCase):
    def test_executor_contract_adaptation_precedes_reserve(self) -> None:
        class CountingLedger(p7c13.DurableOneShotLedger):
            def __init__(self, path: Path) -> None:
                super().__init__(path)
                self.reserve_calls = 0

            def reserve(self, record: dict[str, object]) -> bool:
                self.reserve_calls += 1
                return super().reserve(record)

        with tempfile.TemporaryDirectory(prefix="p7c14-adaptation-") as directory:
            ledger = CountingLedger(Path(directory) / "p7c14-ledger.json")
            executor = P7C14PreparedFutureRealExecutor(
                ledger=ledger, watchdog=Mock(), child_command=("synthetic-child",),
                result_path=Path(directory) / "result.json", record=p7c13._synthetic_ledger_record(),
            )
            for malformed in (None, p7c13.FutureArchitectContract("token", "head", "tree", "harness")):
                with self.subTest(contract=malformed):
                    with self.assertRaises(P7C14PreparationGateError):
                        executor.run(contract=malformed)
            self.assertEqual(0, ledger.reserve_calls)

    def test_executor_contract_adaptation_keeps_launcher_and_harness_separate(self) -> None:
        contract = _synthetic_contract()
        adapted = P7C14PreparedFutureRealExecutor._adapt_contract(contract)
        self.assertEqual(contract.expected_head, adapted.expected_head)
        self.assertEqual(contract.expected_tree, adapted.expected_tree)
        self.assertEqual(contract.expected_p7c13_harness_blob, adapted.expected_harness_blob)
        self.assertNotEqual(contract.expected_launcher_blob, adapted.expected_harness_blob)

    def test_exact_authorized_synthetic_handoff_uses_inherited_executor(self) -> None:
        class CountingLedger(p7c13.DurableOneShotLedger):
            def __init__(self, path: Path) -> None:
                super().__init__(path)
                self.reserve_calls = 0

            def reserve(self, record: dict[str, object]) -> bool:
                self.reserve_calls += 1
                return super().reserve(record)

        class SyntheticWatchdog:
            def __init__(self, owner: P7C14PreparedFutureRealExecutor) -> None:
                self.owner = owner
                self.calls = 0
                self.fake_child_calls = 0
                self.real_child_calls = 0
                self.commands: list[tuple[str, ...]] = []

            def run(self, command: tuple[str, ...], *, result_path: Path, result_validator=None, **kwargs: object) -> p7c13.WatchdogResult:
                self.calls += 1
                self.fake_child_calls += 1
                self.commands.append(tuple(command))
                boot = p7c13.RootOnlyBootAuthority(self.owner.boot_path).read()
                budget = p7c13.EffectBudget(dict(p7c13.FROZEN_EFFECT_BUDGET))
                budget.counts = dict(p7c13.FROZEN_EFFECT_BUDGET)
                child = p7c13.CompleteChildResult(
                    True, {"synthetic": "PASS"},
                    {"persistent": 0, "isolated": 0, "scan_errors": 0}, {"synthetic": "PASS"},
                )
                p7c13._write_child_result(result_path, p7c13._child_result_payload(boot, child, budget))
                if result_validator is None or not result_validator(Path(result_path)):
                    raise AssertionError("synthetic child result was not accepted by watchdog validator")
                return p7c13.WatchdogResult("COMPLETED", child_result_valid=True)

        contract = _synthetic_contract()
        environment = _synthetic_environment(contract)
        with tempfile.TemporaryDirectory(prefix="p7c14-handoff-") as directory:
            root = Path(directory)
            ledger = CountingLedger(root / "p7c14-ledger.json")
            executor = P7C14PreparedFutureRealExecutor(
                ledger=ledger, watchdog=Mock(), child_command=("synthetic-child",),
                result_path=root / "p7c14-result.json", boot_path=root / "p7c14-boot.json",
                record=p7c13._synthetic_ledger_record(),
                child_factory=lambda boot_path: ("synthetic-child", str(boot_path)),
                run_paths={
                    "isolated_root": str(root / "isolated"),
                    "controller_db": str(root / "controller.sqlite3"),
                    "workdir": str(root / "workdir"),
                    "approval_target": str(root / "approval-target"),
                },
            )
            watchdog = SyntheticWatchdog(executor)
            executor.watchdog = watchdog

            self.assertTrue(p7c14_source_bundle_gate(environment, contract, _synthetic_authority()))
            result = p7c14_real_entrypoint(
                environ=environment, authority=_synthetic_authority(),
                executor=executor, contract=contract,
            )

            self.assertEqual("COMPLETED", result.status)
            self.assertEqual(1, executor.calls)
            self.assertEqual(["ledger", "boot", "child"], executor.order)
            self.assertEqual(1, ledger.reserve_calls)
            self.assertEqual(1, watchdog.calls)
            self.assertEqual(1, watchdog.fake_child_calls)
            self.assertEqual(0, watchdog.real_child_calls)
            self.assertNotEqual(ledger.path, P7C13_LEDGER_PATH)

            boot = p7c13.RootOnlyBootAuthority(executor.boot_path).read()
            self.assertEqual(contract.expected_head, boot["source_head"])
            self.assertEqual(contract.expected_tree, boot["source_tree"])
            self.assertEqual(contract.expected_p7c13_harness_blob, boot["harness_blob"])
            self.assertNotEqual(contract.expected_launcher_blob, boot["harness_blob"])
            self.assertEqual(str(ledger.path), boot["ledger_path"])
            parent_result = p7c13.read_child_result(executor.result_path, boot=boot)
            self.assertTrue(p7c13.child_result_passes(parent_result, boot))

    def test_wrong_authority_matrix_blocks_before_executor(self) -> None:
        contract = _synthetic_contract()
        environment = _synthetic_environment(contract)
        cases = {
            "wrong token": (dict(environment, **{P7C14_FUTURE_REAL_GATE: "wrong"}), _synthetic_authority()),
            "wrong HEAD": (environment, replace(_synthetic_authority(), head="wrong")),
            "wrong TREE": (environment, replace(_synthetic_authority(), tree="wrong")),
            "wrong launcher": (environment, replace(_synthetic_authority(), launcher_blob="wrong")),
            "wrong harness": (environment, replace(_synthetic_authority(), p7c13_harness_blob="wrong")),
            "wrong matcher": (environment, replace(_synthetic_authority(), p7c12_matcher_blob="wrong")),
            "wrong tests init": (environment, replace(_synthetic_authority(), tests_init_blob="wrong")),
            "wrong real init": (environment, replace(_synthetic_authority(), tests_real_init_blob="wrong")),
            "wrong import roots": (environment, replace(_synthetic_authority(), import_root_authority=False)),
            "tracked worktree drift": (environment, replace(_synthetic_authority(), tracked_clean=False)),
            "tracked index drift": (environment, replace(_synthetic_authority(), tracked_clean=False)),
        }
        for name, (candidate_environment, authority) in cases.items():
            with self.subTest(name=name):
                executor = Mock(spec=p7c13.FutureRealExecutor)
                with self.assertRaises(P7C14PreparationGateError):
                    p7c14_real_entrypoint(
                        environ=candidate_environment, authority=authority,
                        executor=executor, contract=contract,
                    )
                executor.run.assert_not_called()

    def test_distinct_ledger_and_inherited_bindings(self) -> None:
        self.assertNotEqual(P7C14_LEDGER_PATH, P7C13_LEDGER_PATH)
        self.assertEqual(P7C14_EXPECTED_P7C13_HARNESS_BLOB_VALUE, "5a1fe8e32cd985b1e1845d73266211632e33950c")
        self.assertEqual(P7C14_EXPECTED_P7C12_MATCHER_BLOB_VALUE, "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1")
        executor = P7C14PreparedFutureRealExecutor.production(_synthetic_contract())
        self.assertEqual(P7C14_LEDGER_PATH, executor.ledger.path)
        self.assertIsInstance(executor, p7c13.PreparedFutureRealExecutor)

    def test_offline_one_shot_terminal_latch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c14-one-shot-") as directory:
            path = Path(directory) / "p7c14-one-shot.json"
            record = p7c13._synthetic_ledger_record()
            ledger = p7c13.DurableOneShotLedger(path)
            self.assertTrue(ledger.reserve(record))
            self.assertFalse(p7c13.DurableOneShotLedger(path).reserve(record))
            for state in ("COMPLETED", "FAILED", "UNKNOWN", "CONFIRMED_PENDING"):
                terminal_path = Path(directory) / f"{state}.json"
                terminal = p7c13.DurableOneShotLedger(terminal_path)
                self.assertTrue(terminal.reserve(record))
                terminal.update(state=state)
                self.assertFalse(p7c13.DurableOneShotLedger(terminal_path).reserve(record))

    def test_import_root_validator_requires_exact_future_authority(self) -> None:
        self.assertTrue(validate_p7c14_import_root_authority({"PYTHONPATH": P7C14_PYTHONPATH}))
        self.assertFalse(validate_p7c14_import_root_authority({"PYTHONPATH": "/wrong"}))

    def test_child_import_smoke_is_not_a_real_child_boot(self) -> None:
        environment = dict(os.environ, PYTHONPATH=P7C14_PYTHONPATH)
        completed = subprocess.run(
            (sys.executable, "-c", "import tests.real.test_p7_c13_final_hard_delete_acceptance"),
            cwd=_repository(), env=environment, capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)


def _module_main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--p7c14-real-run" in arguments:
        try:
            p7c14_real_entrypoint(environ=dict(os.environ))
        except P7C14PreparationGateError:
            return 2
        return 0
    unittest.main(argv=[sys.argv[0], *arguments])
    return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
