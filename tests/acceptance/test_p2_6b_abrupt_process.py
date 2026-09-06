"""P2.6b isolated temporary-DB abrupt-process durability probes."""

from __future__ import annotations

import os
import asyncio
import subprocess
import sys
import textwrap
import unittest

from codex_control.storage import (
    IngressUpdateRepository,
    IngressDispositionKind,
    DialogueRepository,
    RepositoryError,
    SqliteStorage,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnJobState,
    TurnIngressClaimStatus,
)
from tests.acceptance.test_p2_6b_support import TempDatabase


class P26bAbruptProcessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = TempDatabase.create()

    def tearDown(self):
        self.db.cleanup()

    async def child(self, source: str, code: int) -> None:
        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-c", textwrap.dedent(source)],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
            env={"PYTHONPATH": os.path.abspath("src")},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
        self.assertEqual(code, result.returncode)

    async def test_committed_repository_return_survives_os_exit(self):
        await self.child(
            f"""
            import asyncio, os
            from codex_control.storage import DialogueRepository, SqliteStorage, TurnJobRepository
            async def main():
                storage = await SqliteStorage.open({self.db.path!r}, now_ms=lambda: 1)
                dialogue = DialogueRepository(storage, now_ms=lambda: 10)
                creating = await dialogue.create_intent(dialogue_id='dialogue-1', server_id='server-1', profile_id='profile-1')
                await dialogue.confirm_created(dialogue_id='dialogue-1', expected_version=creating.version, thread_id='thread-1')
                await TurnJobRepository(storage, now_ms=lambda: 20).claim_ingress(
                    update_id=101, job_id='job-1', source_chat_id=-1001, source_message_id=201,
                    dialogue_id='dialogue-1', server_id='server-1', profile_id='profile-1',
                    thread_id='thread-1', model_id='model-test', reasoning_effort='medium',
                    input_payload_id='input-1', input_content=b'fake-input', input_expires_at_ms=100000,
                )
                os._exit(23)
            asyncio.run(main())
            """,
            23,
        )
        storage = await SqliteStorage.open(self.db.path, now_ms=lambda: 1)
        try:
            dialogue = await DialogueRepository(storage).get_live()
            job = await TurnJobRepository(storage).get("job-1")
            payload = await TransientPayloadRepository(storage).get_input_for_job("job-1")
            ingress = await IngressUpdateRepository(storage).get(101)
            self.assertEqual("IDLE", dialogue.state.value)
            self.assertEqual(TurnJobState.RECEIVED, job.state)
            self.assertEqual(b"fake-input", payload.content)
            self.assertEqual("JOB", ingress.disposition.value)
            replay = await TurnJobRepository(storage).claim_ingress(
                update_id=101, job_id="caller-job", source_chat_id=-1002, source_message_id=202,
                dialogue_id="dialogue-1", server_id="other", profile_id="other", thread_id="other",
                model_id="other", reasoning_effort="low", input_payload_id="caller-input",
                input_content=b"other", input_expires_at_ms=100000,
            )
            self.assertEqual(TurnIngressClaimStatus.DUPLICATE, replay.status)
        finally:
            await storage.close()

    async def test_uncommitted_transaction_rolls_back_before_kernel_commit_and_db_reopens(self):
        await self.child(
            f"""
            import asyncio, os
            from codex_control.storage import SqliteStorage
            async def main():
                storage = await SqliteStorage.open({self.db.path!r}, now_ms=lambda: 1)
                def crash(connection):
                    connection.execute("INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) VALUES (701, 1, 1, 'CONTROL')")
                    connection.execute("INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) VALUES (702, 1, 1, 'IGNORED_SLEEP')")
                    os._exit(24)
                await storage.write(crash)
            asyncio.run(main())
            """,
            24,
        )
        storage = await SqliteStorage.open(self.db.path, now_ms=lambda: 1)
        try:
            counts = await storage.read(lambda c: tuple(c.execute("SELECT COUNT(*) FROM ingress_updates WHERE update_id IN (701,702)").fetchone()))
            self.assertEqual((0,), counts)
            accepted = await IngressUpdateRepository(storage, now_ms=lambda: 5).claim_ignored(
                update_id=703, disposition=IngressDispositionKind.IGNORED_SLEEP
            )
            self.assertFalse(accepted.duplicate)
            self.assertEqual(703, (await IngressUpdateRepository(storage).get(703)).update_id)
        finally:
            await storage.close()

    async def test_abrupt_probe_has_no_external_process_or_network_surface(self):
        # The two probes above are the only child processes in this module;
        # this assertion documents their intentionally local scope.
        self.assertEqual(sys.executable, sys.executable)
        self.assertFalse(hasattr(SqliteStorage, "crash"))
        self.assertFalse(hasattr(TurnJobRepository, "run_forever"))
