import asyncio
import os
import sqlite3
import tempfile
import threading
import unittest
import hashlib

from codex_control.domain import ControllerMode
from codex_control.storage import (
    CallbackActionRepository,
    CallbackClaimStatus,
    ControlClaimStatus,
    ControlIngressRepository,
    ControllerRuntimeRepository,
    IngressDispositionKind,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
)
from codex_control.storage.idempotency_repositories import (
    _ensure_exact_rowcount,
    _materialize_callback,
)

MAX_SQLITE_INT = 9223372036854775807
MIN_SQLITE_INT = -9223372036854775808


def hash_of(ch: str, count: int = 64) -> str:
    token = hashlib.sha256(ch.encode("utf-8")).hexdigest()
    repeat = ((count + len(token) - 1) // len(token))
    return (token * repeat)[:count]


class IngressControlCallbackClaimsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self, now_ms=None):
        return await SqliteStorage.open(self.path, now_ms=now_ms or (lambda: 1))

    async def callback_create(self, storage, token, *, now=0, expires=10, **overrides):
        values = dict(
            token_hash_sha256=hash_of(token),
            action="approve",
            subject_type="job",
            subject_id="job-1",
            expected_version=0,
            expected_state="new",
            authorized_user_id=1,
            authorized_chat_id=2,
            expires_at_ms=expires,
        )
        values.update(overrides)
        return await CallbackActionRepository(storage, now_ms=lambda: now).create(**values)

    async def test_ingress_claim_ignored_new_duplicate_and_boundaries(self):
        storage = await self.open()
        calls = []
        repo = IngressUpdateRepository(storage, now_ms=lambda: (calls.append(1) or 10))

        first = await repo.claim_ignored(update_id=0, disposition=IngressDispositionKind.IGNORED_SLEEP)
        self.assertEqual(0, first.record.update_id)
        self.assertEqual(first.record.received_at_ms, 10)
        self.assertEqual(first.record.completed_at_ms, 10)
        self.assertFalse(first.duplicate)

        duplicate = await IngressUpdateRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
            "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
        ))).claim_ignored(update_id=0, disposition=IngressDispositionKind.IGNORED_UNAUTHORIZED)
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(first.record, duplicate.record)

        valid = await repo.claim_ignored(update_id=MAX_SQLITE_INT, disposition=IngressDispositionKind.IGNORED_SLEEP)
        self.assertEqual(MAX_SQLITE_INT, valid.record.update_id)

        with self.assertRaises(RepositoryError) as raised:
            await repo.claim_ignored(update_id=True, disposition=IngressDispositionKind.IGNORED_SLEEP)
        self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        with self.assertRaises(RepositoryError) as raised:
            await repo.claim_ignored(update_id=-1, disposition=IngressDispositionKind.IGNORED_SLEEP)
        self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        with self.assertRaises(RepositoryError) as raised:
            await repo.claim_ignored(update_id=MAX_SQLITE_INT + 1, disposition=IngressDispositionKind.IGNORED_SLEEP)
        self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)

        self.assertEqual(2, len(calls))
        await storage.close()

    async def test_ingress_claim_ignored_invalid_disposition(self):
        storage = await self.open()
        calls = []
        repo = IngressUpdateRepository(storage, now_ms=lambda: (calls.append(1) or 10))
        for invalid in (
            IngressDispositionKind.CONTROL,
            IngressDispositionKind.JOB,
            "IGNORED_SLEEP",
            "IGNORED_UNAUTHORIZED",
            "CONTROL",
            1,
            None,
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.claim_ignored(update_id=1, disposition=invalid)  # type: ignore[arg-type]
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        self.assertEqual(0, len(calls))
        self.assertEqual(0, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM ingress_updates WHERE update_id=1").fetchone()[0]
        ))
        await storage.close()

    async def test_ingress_corrupt_rows_fail_closed(self):
        storage = await self.open()
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) VALUES"
                "(1, 1, 2, 'JOB:" + "x" * 129 + "')"
            )
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) VALUES(2, 1.5, 2, 'CONTROL')"
            )

        storage = await self.open()
        try:
            for update_id in (1, 2):
                with self.subTest(update_id=update_id):
                    with self.assertRaises(RepositoryError) as raised:
                        await IngressUpdateRepository(storage).get(update_id)
                    self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_ingress_fresh_clock_failure_rolls_back_and_redacts(self):
        storage = await self.open()
        calls = []

        def failing_clock():
            calls.append(1)
            raise RuntimeError("PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK")

        with self.assertRaises(RepositoryError) as raised:
            await IngressUpdateRepository(storage, now_ms=failing_clock).claim_ignored(
                update_id=77,
                disposition=IngressDispositionKind.IGNORED_SLEEP,
            )
        self.assertEqual(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
        self.assertNotIn("PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK", str(raised.exception))
        self.assertEqual(1, len(calls))
        self.assertEqual(0, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM ingress_updates WHERE update_id=77").fetchone()[0]
        ))
        await storage.close()

    async def test_job_suffix_materialization_uses_suffix_bound(self):
        storage = await self.open()
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) "
                "VALUES(10, 1, 1, ?)", ("JOB:" + "j" * 128,)
            )
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) "
                "VALUES(11, 1, 1, ?)", ("JOB:" + "j" * 129,)
            )
        storage = await self.open()
        try:
            valid = await IngressUpdateRepository(storage).get(10)
            self.assertEqual(IngressDispositionKind.JOB, valid.disposition)
            self.assertEqual("j" * 128, valid.job_id)
            with self.assertRaises(RepositoryError) as raised:
                await IngressUpdateRepository(storage).get(11)
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_control_missing_controller_no_clock(self):
        storage = await self.open()
        with self.assertRaises(RepositoryError) as raised:
            await ControlIngressRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
                "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
            ))).claim_control(update_id=1, control_epoch=1, requested_mode=ControllerMode.ACTIVE)
        self.assertEqual(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
        await storage.close()

    async def test_control_fresh_clock_failure_is_atomic_and_redacted(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        before = await ControllerRuntimeRepository(storage).get()

        def failing_clock():
            raise RuntimeError("PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK")

        with self.assertRaises(RepositoryError) as raised:
            await ControlIngressRepository(storage, now_ms=failing_clock).claim_control(
                update_id=78,
                control_epoch=10,
                requested_mode=ControllerMode.ACTIVE,
            )
        self.assertEqual(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
        self.assertNotIn("PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK", str(raised.exception))
        self.assertEqual(0, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM ingress_updates WHERE update_id=78").fetchone()[0]
        ))
        self.assertEqual(before, await ControllerRuntimeRepository(storage).get())
        self.assertEqual(before, await ControllerRuntimeRepository(storage).get())
        await storage.close()

    async def test_control_mode_requires_exact_enum_objects(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        for invalid in ("ACTIVE", "SLEEP", None, 1):
            with self.subTest(invalid=invalid):
                with self.assertRaises(RepositoryError) as raised:
                    await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
                        update_id=100 + len(str(invalid)),
                        control_epoch=1,
                        requested_mode=invalid,  # type: ignore[arg-type]
                    )
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        self.assertEqual(0, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM ingress_updates").fetchone()[0]
        ))
        await storage.close()

    async def test_control_applied_stale_duplicate_and_cross_classification(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")

        applied = await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
            update_id=1,
            control_epoch=10,
            requested_mode=ControllerMode.ACTIVE,
        )
        self.assertEqual(ControlClaimStatus.APPLIED, applied.status)
        self.assertEqual(ControllerMode.ACTIVE, applied.controller.requested_mode)
        self.assertEqual(10, applied.controller.last_control_epoch)

        stale = await ControlIngressRepository(storage, now_ms=lambda: 3).claim_control(
            update_id=2,
            control_epoch=10,
            requested_mode=ControllerMode.SLEEP,
        )
        self.assertEqual(ControlClaimStatus.STALE, stale.status)
        self.assertEqual(ControllerMode.ACTIVE, stale.controller.requested_mode)

        duplicate = await ControlIngressRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
            "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
        ))).claim_control(update_id=1, control_epoch=11, requested_mode=ControllerMode.SLEEP)
        self.assertEqual(ControlClaimStatus.DUPLICATE, duplicate.status)
        self.assertIsNone(duplicate.controller)

        cross_control = await IngressUpdateRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
            "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
        ))).claim_ignored(update_id=1, disposition=IngressDispositionKind.IGNORED_SLEEP)
        self.assertTrue(cross_control.duplicate)
        self.assertEqual(IngressDispositionKind.CONTROL, cross_control.record.disposition)

        await IngressUpdateRepository(storage, now_ms=lambda: 4).claim_ignored(
            update_id=3,
            disposition=IngressDispositionKind.IGNORED_SLEEP,
        )
        cross = await ControlIngressRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
            "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
        ))).claim_control(update_id=3, control_epoch=10, requested_mode=ControllerMode.ACTIVE)
        self.assertEqual(ControlClaimStatus.DUPLICATE, cross.status)
        self.assertIsNone(cross.controller)

        await storage.close()

    async def test_control_restart_sleep_prevents_activation_restore(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 10).begin_boot("fleet")
        await ControlIngressRepository(storage, now_ms=lambda: 11).claim_control(
            update_id=1,
            control_epoch=10,
            requested_mode=ControllerMode.ACTIVE,
        )
        await storage.close()

        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 20).begin_boot("fleet")
        replay = await ControlIngressRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
            "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
        ))).claim_control(update_id=1, control_epoch=10, requested_mode=ControllerMode.ACTIVE)
        self.assertEqual(ControlClaimStatus.DUPLICATE, replay.status)
        self.assertIsNone(replay.controller)

        fresh = await ControlIngressRepository(storage, now_ms=lambda: 30).claim_control(
            update_id=2,
            control_epoch=11,
            requested_mode=ControllerMode.SLEEP,
        )
        self.assertEqual(ControlClaimStatus.APPLIED, fresh.status)
        self.assertEqual(ControllerMode.SLEEP, fresh.controller.requested_mode)
        self.assertEqual(11, fresh.controller.last_control_epoch)
        await storage.close()

    async def test_control_same_update_concurrent_claims_have_duplicate(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        first, second = await asyncio.gather(
            ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
                update_id=42,
                control_epoch=1,
                requested_mode=ControllerMode.ACTIVE,
            ),
            ControlIngressRepository(storage, now_ms=lambda: 3).claim_control(
                update_id=42,
                control_epoch=2,
                requested_mode=ControllerMode.SLEEP,
            ),
            return_exceptions=True,
        )
        self.assertNotIsInstance(first, Exception)
        self.assertNotIsInstance(second, Exception)
        self.assertEqual({first.status, second.status}, {ControlClaimStatus.APPLIED, ControlClaimStatus.DUPLICATE})
        self.assertEqual(1, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM ingress_updates WHERE update_id=42").fetchone()[0]
        ))
        await storage.close()

    async def test_control_same_epoch_competing_updates(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        first, second = await asyncio.gather(
            ControlIngressRepository(storage, now_ms=lambda: 10).claim_control(
                update_id=43,
                control_epoch=10,
                requested_mode=ControllerMode.ACTIVE,
            ),
            ControlIngressRepository(storage, now_ms=lambda: 11).claim_control(
                update_id=44,
                control_epoch=10,
                requested_mode=ControllerMode.SLEEP,
            ),
        )
        self.assertEqual({first.status, second.status}, {ControlClaimStatus.APPLIED, ControlClaimStatus.STALE})
        applied = first if first.status is ControlClaimStatus.APPLIED else second
        final = await ControllerRuntimeRepository(storage).get()
        self.assertEqual(applied.controller.requested_mode, final.requested_mode)
        self.assertEqual(2, await storage.read(
            lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id IN (43, 44) AND disposition='CONTROL'"
            ).fetchone()[0]
        ))

        third = await ControlIngressRepository(storage, now_ms=lambda: 12).claim_control(
            update_id=45,
            control_epoch=10,
            requested_mode=ControllerMode.ACTIVE,
        )
        self.assertEqual(ControlClaimStatus.STALE, third.status)
        await storage.close()

    async def test_control_higher_epoch_is_final_authority(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        low, high = await asyncio.gather(
            ControlIngressRepository(storage, now_ms=lambda: 10).claim_control(
                update_id=201, control_epoch=10, requested_mode=ControllerMode.ACTIVE,
            ),
            ControlIngressRepository(storage, now_ms=lambda: 11).claim_control(
                update_id=202, control_epoch=11, requested_mode=ControllerMode.SLEEP,
            ),
        )
        self.assertEqual(ControlClaimStatus.APPLIED, high.status)
        self.assertIn(low.status, (ControlClaimStatus.APPLIED, ControlClaimStatus.STALE))
        final = await ControllerRuntimeRepository(storage).get()
        self.assertEqual(11, final.last_control_epoch)
        self.assertEqual(ControllerMode.SLEEP, final.requested_mode)
        self.assertEqual(2, await storage.read(
            lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id IN (201, 202) AND disposition='CONTROL'"
            ).fetchone()[0]
        ))
        await storage.close()

    async def test_private_cas_rowcount_guard_fails_closed(self):
        for count in (0, 2):
            with self.subTest(count=count):
                with self.assertRaises(RepositoryError) as raised:
                    _ensure_exact_rowcount(count, 1)
                self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

    async def test_callback_create_and_hash_contract(self):
        storage = await self.open()
        repo = CallbackActionRepository(storage, now_ms=lambda: 1)
        await repo.create(
            token_hash_sha256=hash_of("a"),
            action="approve",
            subject_type="job",
            subject_id="job-1",
            expected_version=0,
            expected_state="new",
            authorized_user_id=1,
            authorized_chat_id=2,
            expires_at_ms=10,
        )

        for invalid in (
            hash_of("a", 63),
            hash_of("a", 65),
            "A" * 64,
            "g" * 64,
            "PRIVATE_P2_3_HASH",
        ):
            with self.subTest(hash_value=invalid):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.create(
                        token_hash_sha256=invalid,
                        action="approve",
                        subject_type="job",
                        subject_id="job-1",
                        expected_version=0,
                        expected_state="new",
                        authorized_user_id=1,
                        authorized_chat_id=2,
                        expires_at_ms=10,
                    )
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)

        with self.assertRaises(RepositoryError) as raised:
            await repo.create(
                token_hash_sha256=hash_of("a"),
                action="approve",
                subject_type="job",
                subject_id="job-1",
                expected_version=0,
                expected_state="new",
                authorized_user_id=1,
                authorized_chat_id=2,
                expires_at_ms=10,
            )
        self.assertEqual(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
        await storage.close()

    async def test_callback_duplicate_create_is_zero_clock_and_no_overwrite(self):
        storage = await self.open()
        original = await self.callback_create(
            storage, "duplicate-create", now=10, expires=100,
            action="original", subject_id="original-id", expected_version=1,
        )
        calls = []

        def unexpected_clock():
            calls.append(1)
            raise RuntimeError("PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK")

        with self.assertRaises(RepositoryError) as raised:
            await CallbackActionRepository(storage, now_ms=unexpected_clock).create(
                token_hash_sha256=hash_of("duplicate-create"),
                action="replacement",
                subject_type="other",
                subject_id="replacement-id",
                expected_version=2,
                expected_state="other",
                authorized_user_id=3,
                authorized_chat_id=4,
                expires_at_ms=200,
            )
        self.assertEqual(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
        self.assertEqual([], calls)
        durable = await storage.read(
            lambda c: (
                tuple(c.execute(
                    "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
                    "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms "
                    "FROM callback_actions WHERE token_hash_sha256=?", (hash_of("duplicate-create"),)
                ).fetchone())
            )
        )
        self.assertEqual(
            (
                original.token_hash_sha256, original.action, original.subject_type, original.subject_id,
                original.expected_version, original.expected_state, original.authorized_user_id,
                original.authorized_chat_id, original.created_at_ms, original.expires_at_ms, original.consumed_at_ms,
            ),
            tuple(durable),
        )
        await storage.close()

    async def test_callback_expiry_static_validation_and_exact_boundary(self):
        storage = await self.open()
        calls = []
        repo = CallbackActionRepository(storage, now_ms=lambda: (calls.append(1) or 0))
        for index, invalid in enumerate((True, False, "123", 1.5, -1, MAX_SQLITE_INT + 1)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.create(
                        token_hash_sha256=hash_of("expiry-invalid-" + str(index)),
                        action="approve", subject_type="job", subject_id="id",
                        expected_version=0, expected_state="new",
                        authorized_user_id=1, authorized_chat_id=2,
                        expires_at_ms=invalid,  # type: ignore[arg-type]
                    )
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        self.assertEqual([], calls)
        await repo.create(
            token_hash_sha256=hash_of("expiry-one"), action="approve", subject_type="job", subject_id="id",
            expected_version=0, expected_state="new", authorized_user_id=1, authorized_chat_id=2,
            expires_at_ms=1,
        )
        await repo.create(
            token_hash_sha256=hash_of("expiry-max"), action="approve", subject_type="job", subject_id="id",
            expected_version=0, expected_state="new", authorized_user_id=1, authorized_chat_id=2,
            expires_at_ms=MAX_SQLITE_INT,
        )
        with self.assertRaises(RepositoryError) as raised:
            await repo.create(
                token_hash_sha256=hash_of("expiry-equal"), action="approve", subject_type="job", subject_id="id",
                expected_version=0, expected_state="new", authorized_user_id=1, authorized_chat_id=2,
                expires_at_ms=0,
            )
        self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        self.assertEqual(2, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM callback_actions").fetchone()[0]
        ))

        boundary = await CallbackActionRepository(storage, now_ms=lambda: 200).claim(
            token_hash_sha256=hash_of("expiry-one"), authorized_user_id=1, authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.EXPIRED, boundary.status)
        self.assertIsNone(boundary.record)
        self.assertEqual(1, await storage.read(
            lambda c: c.execute(
                "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256=?",
                (hash_of("expiry-one"),),
            ).fetchone()[0]
        ))
        rollback = await CallbackActionRepository(storage, now_ms=lambda: 150).claim(
            token_hash_sha256=hash_of("expiry-one"), authorized_user_id=1, authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, rollback.status)

        await self.callback_create(storage, "expiry-exact", now=100, expires=200)
        exact = await CallbackActionRepository(storage, now_ms=lambda: 200).claim(
            token_hash_sha256=hash_of("expiry-exact"), authorized_user_id=1, authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.EXPIRED, exact.status)
        self.assertIsNone(exact.record)
        self.assertEqual(200, await storage.read(
            lambda c: c.execute(
                "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256=?",
                (hash_of("expiry-exact"),),
            ).fetchone()[0]
        ))
        exact_rollback = await CallbackActionRepository(storage, now_ms=lambda: 150).claim(
            token_hash_sha256=hash_of("expiry-exact"), authorized_user_id=1, authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, exact_rollback.status)
        await storage.close()

    async def test_callback_authorization_privacy_and_backward_clock(self):
        storage = await self.open()
        await CallbackActionRepository(storage, now_ms=lambda: 100).create(
            token_hash_sha256=hash_of("b"),
            action="approve",
            subject_type="task",
            subject_id="alpha",
            expected_version=5,
            expected_state="created",
            authorized_user_id=10,
            authorized_chat_id=-999,
            expires_at_ms=300,
        )

        unauthorized = await CallbackActionRepository(storage).claim(
            token_hash_sha256=hash_of("b"),
            authorized_user_id=11,
            authorized_chat_id=-999,
        )
        self.assertEqual(CallbackClaimStatus.UNAUTHORIZED, unauthorized.status)
        self.assertIsNone(unauthorized.record)

        before = await storage.read(
            lambda c: c.execute(f"SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256='{hash_of('b')}'").fetchone()[0]
        )
        self.assertIsNone(before)

        claimed = await CallbackActionRepository(storage, now_ms=lambda: 50).claim(
            token_hash_sha256=hash_of("b"),
            authorized_user_id=10,
            authorized_chat_id=-999,
        )
        self.assertEqual(CallbackClaimStatus.CLAIMED, claimed.status)
        self.assertEqual(100, claimed.record.consumed_at_ms)

        await storage.close()

    async def test_callback_authorization_precedes_consumed_and_expired_state(self):
        storage = await self.open()
        await self.callback_create(storage, "wrong-user", now=10, expires=100)
        await self.callback_create(storage, "wrong-chat", now=10, expires=100)
        await self.callback_create(storage, "consumed-private", now=10, expires=100)
        await self.callback_create(storage, "expired-private", now=10, expires=20)
        await CallbackActionRepository(storage, now_ms=lambda: 20).claim(
            token_hash_sha256=hash_of("consumed-private"), authorized_user_id=1, authorized_chat_id=2,
        )
        await CallbackActionRepository(storage, now_ms=lambda: 20).claim(
            token_hash_sha256=hash_of("expired-private"), authorized_user_id=1, authorized_chat_id=2,
        )

        clock_calls = []

        def unexpected_clock():
            clock_calls.append(1)
            raise RuntimeError("PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK")

        for token, user, chat in (
            ("wrong-user", 99, 2),
            ("wrong-chat", 1, 99),
            ("consumed-private", 99, 2),
            ("expired-private", 99, 2),
        ):
            with self.subTest(token=token):
                result = await CallbackActionRepository(storage, now_ms=unexpected_clock).claim(
                    token_hash_sha256=hash_of(token), authorized_user_id=user, authorized_chat_id=chat,
                )
                self.assertEqual(CallbackClaimStatus.UNAUTHORIZED, result.status)
                self.assertIsNone(result.record)
        self.assertEqual([], clock_calls)
        self.assertEqual(2, await storage.read(
            lambda c: c.execute(
                "SELECT count(*) FROM callback_actions WHERE consumed_at_ms IS NOT NULL"
            ).fetchone()[0]
        ))
        await storage.close()

    async def test_callback_expiry_terminalization_and_non_resurrection(self):
        storage = await self.open()
        await CallbackActionRepository(storage, now_ms=lambda: 10).create(
            token_hash_sha256=hash_of("c"),
            action="approve",
            subject_type="task",
            subject_id="beta",
            expected_version=0,
            expected_state="created",
            authorized_user_id=1,
            authorized_chat_id=2,
            expires_at_ms=20,
        )

        expired = await CallbackActionRepository(storage, now_ms=lambda: 50).claim(
            token_hash_sha256=hash_of("c"),
            authorized_user_id=1,
            authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.EXPIRED, expired.status)
        consumed = await storage.read(
            lambda c: c.execute(f"SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256='{hash_of('c')}'").fetchone()[0]
        )
        self.assertEqual(20, consumed)

        again = await CallbackActionRepository(storage, now_ms=lambda: 10).claim(
            token_hash_sha256=hash_of("c"),
            authorized_user_id=1,
            authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, again.status)
        await storage.close()

    async def test_callback_concurrent_fresh_and_expired(self):
        storage = await self.open()
        repo = CallbackActionRepository(storage, now_ms=lambda: 1)
        await repo.create(
            token_hash_sha256=hash_of("d"),
            action="approve",
            subject_type="task",
            subject_id="parallel-fresh",
            expected_version=0,
            expected_state="new",
            authorized_user_id=1,
            authorized_chat_id=1,
            expires_at_ms=500,
        )
        fresh1, fresh2 = await asyncio.gather(
            CallbackActionRepository(storage, now_ms=lambda: 5).claim(
                token_hash_sha256=hash_of("d"),
                authorized_user_id=1,
                authorized_chat_id=1,
            ),
            CallbackActionRepository(storage, now_ms=lambda: 5).claim(
                token_hash_sha256=hash_of("d"),
                authorized_user_id=1,
                authorized_chat_id=1,
            ),
        )
        self.assertEqual({fresh1.status, fresh2.status}, {CallbackClaimStatus.CLAIMED, CallbackClaimStatus.ALREADY_CONSUMED})

        await repo.create(
            token_hash_sha256=hash_of("e"),
            action="approve",
            subject_type="task",
            subject_id="parallel-expired",
            expected_version=0,
            expected_state="new",
            authorized_user_id=2,
            authorized_chat_id=2,
            expires_at_ms=100,
        )
        expired1, expired2 = await asyncio.gather(
            CallbackActionRepository(storage, now_ms=lambda: 200).claim(
                token_hash_sha256=hash_of("e"),
                authorized_user_id=2,
                authorized_chat_id=2,
            ),
            CallbackActionRepository(storage, now_ms=lambda: 200).claim(
                token_hash_sha256=hash_of("e"),
                authorized_user_id=2,
                authorized_chat_id=2,
            ),
        )
        self.assertEqual(
            {expired1.status, expired2.status},
            {CallbackClaimStatus.EXPIRED, CallbackClaimStatus.ALREADY_CONSUMED},
        )
        await storage.close()

    async def test_callback_cancellation_keeps_transaction(self):
        storage = await self.open()
        await CallbackActionRepository(storage, now_ms=lambda: 1).create(
            token_hash_sha256=hash_of("f"),
            action="approve",
            subject_type="task",
            subject_id="cancel",
            expected_version=0,
            expected_state="new",
            authorized_user_id=5,
            authorized_chat_id=6,
            expires_at_ms=500,
        )

        entered = threading.Event()
        release = threading.Event()

        def blocked_clock():
            entered.set()
            release.wait(5)
            return 9

        task = asyncio.create_task(
            CallbackActionRepository(storage, now_ms=blocked_clock).claim(
                token_hash_sha256=hash_of("f"),
                authorized_user_id=5,
                authorized_chat_id=6,
            )
        )
        await asyncio.to_thread(entered.wait, 5)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        release.set()
        result = await task
        self.assertEqual(CallbackClaimStatus.CLAIMED, result.status)
        self.assertFalse(task.cancelled())
        consumed_count = await storage.read(
            lambda c: c.execute(
                "SELECT count(*) FROM callback_actions WHERE token_hash_sha256='" + hash_of("f") + "' AND consumed_at_ms IS NOT NULL"
            ).fetchone()[0]
        )
        self.assertEqual(1, consumed_count)
        await storage.close()

    async def test_restart_persistence_ingress_and_callback(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
            update_id=1,
            control_epoch=1,
            requested_mode=ControllerMode.ACTIVE,
        )
        await storage.close()

        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 3).begin_boot("fleet")
        duplicate = await ControlIngressRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError(
            "PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK"
        ))).claim_control(update_id=1, control_epoch=1, requested_mode=ControllerMode.ACTIVE)
        self.assertEqual(ControlClaimStatus.DUPLICATE, duplicate.status)
        self.assertIsNone(duplicate.controller)

        await CallbackActionRepository(storage, now_ms=lambda: 10).create(
            token_hash_sha256=hash_of("g"),
            action="approve",
            subject_type="session",
            subject_id="s1",
            expected_version=0,
            expected_state="new",
            authorized_user_id=1,
            authorized_chat_id=2,
            expires_at_ms=100,
        )
        claim = await CallbackActionRepository(storage, now_ms=lambda: 20).claim(
            token_hash_sha256=hash_of("g"),
            authorized_user_id=1,
            authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.CLAIMED, claim.status)
        await storage.close()

        storage = await self.open()
        again = await CallbackActionRepository(storage, now_ms=lambda: 30).claim(
            token_hash_sha256=hash_of("g"),
            authorized_user_id=1,
            authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, again.status)

        await CallbackActionRepository(storage, now_ms=lambda: 5).create(
            token_hash_sha256=hash_of("h"),
            action="approve",
            subject_type="session",
            subject_id="s2",
            expected_version=0,
            expected_state="new",
            authorized_user_id=3,
            authorized_chat_id=4,
            expires_at_ms=10,
        )
        expired = await CallbackActionRepository(storage, now_ms=lambda: 20).claim(
            token_hash_sha256=hash_of("h"),
            authorized_user_id=3,
            authorized_chat_id=4,
        )
        self.assertEqual(CallbackClaimStatus.EXPIRED, expired.status)
        await storage.close()

        storage = await self.open()
        old_clock_expired = await CallbackActionRepository(storage, now_ms=lambda: 1).claim(
            token_hash_sha256=hash_of("h"),
            authorized_user_id=3,
            authorized_chat_id=4,
        )
        self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, old_clock_expired.status)
        await storage.close()

        storage = await self.open()
        await self.callback_create(storage, "restart-fresh", now=100, expires=200)
        await storage.close()
        storage = await self.open()
        fresh = await CallbackActionRepository(storage, now_ms=lambda: 150).claim(
            token_hash_sha256=hash_of("restart-fresh"), authorized_user_id=1, authorized_chat_id=2,
        )
        self.assertEqual(CallbackClaimStatus.CLAIMED, fresh.status)
        await storage.close()

    async def test_corruption_cases_for_callback_records(self):
        storage = await self.open()
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO callback_actions(token_hash_sha256, action, subject_type, subject_id, "
                "expected_version, expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
                "expires_at_ms, consumed_at_ms) VALUES('" + "A" * 64 + "', 'approve', 'subject', 'id', 1, 'state', 1, 2, 10, 20, 30)"
            )
            connection.execute(
                "INSERT INTO callback_actions(token_hash_sha256, action, subject_type, subject_id, "
                "expected_version, expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
                "expires_at_ms, consumed_at_ms) VALUES('" + hash_of("0") + "', 'approve', 'subject', 'id', 1.5, 'state', 1, 2, 10, 20, NULL)"
            )
            connection.execute(
                "INSERT INTO callback_actions(token_hash_sha256, action, subject_type, subject_id, "
                "expected_version, expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
                "expires_at_ms, consumed_at_ms) VALUES('" + hash_of("1") + "', 'approve', 'subject', 'id', 0, 'state', 0, 2, 10, 20, NULL)"
            )
            connection.execute(
                "INSERT INTO callback_actions(token_hash_sha256, action, subject_type, subject_id, "
                "expected_version, expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
                "expires_at_ms, consumed_at_ms) VALUES('" + hash_of("2") + "', 'approve', 'subject', 'id', 0, 'state', 1, 2, 10, 10, 20)"
            )
            connection.execute(
                "INSERT INTO callback_actions(token_hash_sha256, action, subject_type, subject_id, "
                "expected_version, expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
                "expires_at_ms, consumed_at_ms) VALUES('" + hash_of("3") + "', 'approve', 'subject', 'id', 0, 'state', 1, 2, 10, 10, NULL)"
            )

        storage = await self.open()
        try:
            repo = CallbackActionRepository(storage)
            with sqlite3.connect(self.path) as connection:
                uppercase_row = connection.execute(
                    "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
                    "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms "
                    "FROM callback_actions WHERE token_hash_sha256=?", ("A" * 64,)
                ).fetchone()
            with self.assertRaises(RepositoryError) as raised:
                _materialize_callback(uppercase_row)
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("A" * 64, str(raised.exception))
            self.assertNotIn("A" * 64, repr(raised.exception))

            for token in (hash_of("0"), hash_of("1"), hash_of("2"), hash_of("3")):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.claim(token_hash_sha256=token, authorized_user_id=1, authorized_chat_id=2)
                self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_persisted_controller_corruption_is_invariant_and_atomic(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        await storage.close()

        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE controller_runtime SET boot_generation=1.5")
        storage = await self.open()
        try:
            with self.assertRaises(RepositoryError) as raised:
                await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
                    update_id=301, control_epoch=1, requested_mode=ControllerMode.ACTIVE,
                )
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("1.5", str(raised.exception))
            self.assertNotIn("1.5", repr(raised.exception))
            self.assertEqual(0, await storage.read(
                lambda c: c.execute("SELECT count(*) FROM ingress_updates").fetchone()[0]
            ))
        finally:
            await storage.close()

        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE controller_runtime SET boot_generation=1, fleet_version=?", ("bad\x00version",))
        storage = await self.open()
        try:
            with self.assertRaises(RepositoryError) as raised:
                await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
                    update_id=302, control_epoch=1, requested_mode=ControllerMode.ACTIVE,
                )
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("bad\x00version", str(raised.exception))
            self.assertEqual(0, await storage.read(
                lambda c: c.execute("SELECT count(*) FROM ingress_updates").fetchone()[0]
            ))
        finally:
            await storage.close()
        
    async def test_boundaries_for_control_clock_and_callback_identifiers(self):
        storage = await self.open()
        repo = CallbackActionRepository(storage, now_ms=lambda: 1)

        for value in (0, MAX_SQLITE_INT):
            await repo.create(
                token_hash_sha256=hash_of("i") if value == 0 else hash_of("j"),
                action="x" * 128,
                subject_type="z" * 64,
                subject_id="a" * 128,
                expected_version=value,
                expected_state="s" * 64,
                authorized_user_id=1,
                authorized_chat_id=MIN_SQLITE_INT,
                expires_at_ms=100 if value == 0 else 200,
            )

        for invalid in ("", "x" * 129, "a!", "a b", "a\0"):
            with self.subTest(action=invalid):
                with self.assertRaises(RepositoryError):
                    await CallbackActionRepository(storage).create(
                        token_hash_sha256=hash_of("k"),
                        action=invalid,
                        subject_type="z",
                        subject_id="a",
                        expected_version=0,
                        expected_state="s",
                        authorized_user_id=1,
                        authorized_chat_id=1,
                        expires_at_ms=100,
                    )

        with self.assertRaises(RepositoryError):
            await repo.create(
                token_hash_sha256=hash_of("l"),
                action="x",
                subject_type="z",
                subject_id="a",
                expected_version=MAX_SQLITE_INT + 1,
                expected_state="s",
                authorized_user_id=1,
                authorized_chat_id=1,
                expires_at_ms=200,
            )

        for invalid in (True, -1, MAX_SQLITE_INT + 1):
            with self.subTest(control_epoch=invalid):
                with self.assertRaises(RepositoryError):
                    await ControlIngressRepository(storage, now_ms=lambda: 1).claim_control(
                        update_id=999,
                        control_epoch=invalid,
                        requested_mode=ControllerMode.ACTIVE,
                    )

        await storage.close()

    async def test_callback_numeric_boundary_matrix(self):
        storage = await self.open()
        calls = []
        repo = CallbackActionRepository(storage, now_ms=lambda: (calls.append(1) or 0))
        await repo.create(
            token_hash_sha256=hash_of("numeric-user-min"), action="a", subject_type="s", subject_id="i",
            expected_version=0, expected_state="e", authorized_user_id=1, authorized_chat_id=1, expires_at_ms=1,
        )
        await repo.create(
            token_hash_sha256=hash_of("numeric-user-max"), action="a", subject_type="s", subject_id="i",
            expected_version=MAX_SQLITE_INT, expected_state="e", authorized_user_id=MAX_SQLITE_INT,
            authorized_chat_id=MAX_SQLITE_INT, expires_at_ms=2,
        )
        await repo.create(
            token_hash_sha256=hash_of("numeric-chat-min"), action="a", subject_type="s", subject_id="i",
            expected_version=0, expected_state="e", authorized_user_id=1,
            authorized_chat_id=MIN_SQLITE_INT, expires_at_ms=3,
        )
        invalid_cases = (
            ("u0", 0, 1, 0), ("ubool", True, 1, 0), ("ufalse", False, 1, 0),
            ("umax", MAX_SQLITE_INT + 1, 1, 0), ("uminus", -1, 1, 0),
            ("c0", 1, 0, 0), ("cbool", 1, True, 0), ("cfalse", 1, False, 0),
            ("cbelow", 1, MIN_SQLITE_INT - 1, 0), ("cover", 1, MAX_SQLITE_INT + 1, 0),
            ("vbool", 1, 1, True), ("vfalse", 1, 1, False), ("vnegative", 1, 1, -1),
            ("vfloat", 1, 1, 1.5), ("vover", 1, 1, MAX_SQLITE_INT + 1),
        )
        for index, (label, user, chat, version) in enumerate(invalid_cases):
            with self.subTest(label=label):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.create(
                        token_hash_sha256=hash_of("numeric-invalid-" + str(index)),
                        action="a", subject_type="s", subject_id="i", expected_version=version,
                        expected_state="e", authorized_user_id=user, authorized_chat_id=chat, expires_at_ms=100,
                    )
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        self.assertEqual(3, len(calls))
        self.assertEqual(3, await storage.read(
            lambda c: c.execute("SELECT count(*) FROM callback_actions").fetchone()[0]
        ))
        await storage.close()

    async def test_callback_identifier_boundary_and_regex_matrix(self):
        storage = await self.open()
        calls = []
        repo = CallbackActionRepository(storage, now_ms=lambda: (calls.append(1) or 0))
        await repo.create(
            token_hash_sha256=hash_of("identifier-max"), action="a" * 128, subject_type="s" * 64,
            subject_id="i" * 128, expected_version=0, expected_state="e" * 64,
            authorized_user_id=1, authorized_chat_id=1, expires_at_ms=1,
        )
        invalid_fields = (
            ("action", ""), ("action", "a" * 129), ("action", "a b"), ("action", "a/b"),
            ("action", "a\\b"), ("action", "a\nb"), ("action", "a\x00b"),
            ("subject_type", ""), ("subject_type", "s" * 65), ("subject_type", "s t"),
            ("subject_type", "s/s"), ("subject_type", "s\\s"), ("subject_type", "s\ns"), ("subject_type", "s\x00s"),
            ("subject_id", ""), ("subject_id", "i" * 129), ("subject_id", "i\x00d"),
            ("expected_state", ""), ("expected_state", "e" * 65), ("expected_state", "e e"),
            ("expected_state", "e/e"), ("expected_state", "e\\e"), ("expected_state", "e\ne"),
            ("expected_state", "e\x00e"),
        )
        for index, (field, value) in enumerate(invalid_fields):
            values = dict(
                token_hash_sha256=hash_of("identifier-invalid-" + str(index)), action="a",
                subject_type="s", subject_id="i", expected_version=0, expected_state="e",
                authorized_user_id=1, authorized_chat_id=1, expires_at_ms=100,
            )
            values[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.create(**values)
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        self.assertEqual(1, len(calls))
        await storage.close()


if __name__ == "__main__":
    unittest.main()
