"""Offline-testable production assembly and bounded controller lifecycle."""

from __future__ import annotations

import asyncio
import os
import signal
import sqlite3
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapters.codex.capabilities import REQUIRED_V1_CAPABILITIES, SUPPORTED_CODEX_VERSION, load_manifest
from .adapters.codex.isolation import IsolationError, IsolationPathAuthority
from .adapters.codex.model_catalog import CodexModelCatalogAdapter
from .adapters.codex.runtime import CodexRuntimeManager
from .adapters.codex.thread_lifecycle import CodexThreadLifecycleAdapter, TrustedWorkingDirectory
from .adapters.telegram.bot_api import TelegramBotApiTransport
from .adapters.telegram.fleet_keyboard import TelegramFleetKeyboardRenderer
from .adapters.telegram.fleet_status_render import TelegramFleetStatusRenderer
from .adapters.telegram.group_updates import TelegramGroupUpdateAdapter
from .adapters.telegram.private_control_render import TelegramPrivateControlRenderer
from .adapters.telegram.private_updates import PrivateInboundKind, TelegramPrivateUpdateAdapter
from .application import (
    ActiveTurnRegistry, ApprovalAwareTurnLifecycle,
    DialogueDeleteService, DialogueInterruptService, DialogueRecoveryService,
    DialogueTurnService, FleetControlService, FleetGroupRoutingService,
    FleetStatusService, LocalControllerOrchestrator, PrivateCallbackRequest,
    PrivateCommandRequest, PrivateControlService, TurnDeliveryService,
)
from .application.fleet_control import GroupInboundKind
from .application.live_approval import ApprovalDecisionSignal
from .config import ConfigurationError, ServerConfiguration, load_production_configuration
from .secrets import SecretAuthority, SecretsError, load_secrets
from .storage import ControllerRuntimeRepository, SqliteStorage


class ServiceError(RuntimeError):
    """Finite startup/shutdown category with no payload content."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)

    def __repr__(self) -> str:
        return f"ServiceError({self.category!r})"


def _safe_dir(path: str, category: str, *, require_root: bool = True) -> None:
    try:
        info = os.stat(path, follow_symlinks=False)
    except OSError:
        raise ServiceError(category) from None
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o022 or (require_root and info.st_uid != 0):
        raise ServiceError(category)


def _read_schema(path: str) -> int:
    if not os.path.isabs(path) or os.path.islink(path):
        raise ServiceError("database_authority_invalid")
    uri = f"file:{path}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=1.0) as connection:
            value = connection.execute("PRAGMA user_version").fetchone()[0]
    except (OSError, sqlite3.Error, IndexError, TypeError):
        raise ServiceError("database_unavailable") from None
    if type(value) is not int or value != 4:
        raise ServiceError("schema_unsupported")
    return value


def validate_production_authority(config_path: str | Path, secrets_path: str | Path,
                                  *, test_only: bool = False) -> ServerConfiguration:
    """Run static, zero-external-effect preflight for ``validate``."""
    try:
        config = load_production_configuration(config_path, test_only=test_only)
        load_secrets(secrets_path, test_only=test_only)
    except (ConfigurationError, SecretsError):
        raise ServiceError("configuration_or_secrets_invalid") from None
    _safe_dir(config.state_root, "state_root_invalid", require_root=not test_only)
    _safe_dir(config.working_directory, "working_directory_invalid", require_root=not test_only)
    _safe_dir(config.repository_root, "repository_root_invalid", require_root=not test_only)
    for profile in config.profiles:
        _safe_dir(profile.codex_home, "codex_home_invalid", require_root=not test_only)
        _safe_dir(profile.isolated_state_root, "isolated_state_root_invalid", require_root=not test_only)
    executable = Path(config.codex_executable)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ServiceError("codex_executable_invalid")
    try:
        manifest = load_manifest(SUPPORTED_CODEX_VERSION)
        if manifest.check_required(REQUIRED_V1_CAPABILITIES).missing:
            raise ServiceError("capability_mismatch")
    except ServiceError:
        raise
    except Exception:
        raise ServiceError("capability_mismatch") from None
    _read_schema(config.controller_db_path)
    try:
        IsolationPathAuthority(
            config.profiles, controller_db_path=config.controller_db_path,
            controller_db_root=config.controller_db_root, repository_root=config.repository_root,
            protected_roots=config.protected_roots,
        ).validate_runtime_authority()
    except IsolationError:
        raise ServiceError("filesystem_authority_invalid") from None
    return config


class _WorkingDirectoryResolver:
    def __init__(self, path: str) -> None:
        self._path = path

    def resolve(self, profile_id: str) -> TrustedWorkingDirectory:
        return TrustedWorkingDirectory(self._path)


@dataclass
class ProductionAssembly:
    config: ServerConfiguration
    secrets: SecretAuthority
    storage: SqliteStorage
    runtime_manager: CodexRuntimeManager
    orchestrator: LocalControllerOrchestrator
    telegram: TelegramBotApiTransport
    group_adapter: TelegramGroupUpdateAdapter
    private_adapter: TelegramPrivateUpdateAdapter
    private_renderer: TelegramPrivateControlRenderer
    keyboard_renderer: TelegramFleetKeyboardRenderer
    mode: Any
    _mode_box: list[Any]


async def build_production_assembly(config_path: str | Path, secrets_path: str | Path,
                                    *, test_only: bool = False, telegram: TelegramBotApiTransport | None = None,
                                    runtime_manager_factory: Any | None = None) -> ProductionAssembly:
    """Construct accepted P0--P7 services after fail-closed preflight."""
    storage: SqliteStorage | None = None
    try:
        config = load_production_configuration(config_path, test_only=test_only)
        secrets = load_secrets(secrets_path, test_only=test_only)
    except (ConfigurationError, SecretsError):
        raise ServiceError("configuration_or_secrets_invalid") from None
    # This is the same fail-closed authority check as `validate`, except that
    # a first boot may create a missing controller DB under the configured
    # state root. Existing databases must already be v4; otherwise opening
    # them would silently invoke the legacy migration path.
    _safe_dir(config.state_root, "state_root_invalid", require_root=not test_only)
    _safe_dir(config.working_directory, "working_directory_invalid", require_root=not test_only)
    _safe_dir(config.repository_root, "repository_root_invalid", require_root=not test_only)
    executable = Path(config.codex_executable)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ServiceError("codex_executable_invalid")
    try:
        manifest = load_manifest(SUPPORTED_CODEX_VERSION)
        if manifest.check_required(REQUIRED_V1_CAPABILITIES).missing:
            raise ServiceError("capability_mismatch")
    except ServiceError:
        raise
    except Exception:
        raise ServiceError("capability_mismatch") from None
    if os.path.lexists(config.controller_db_path):
        _read_schema(config.controller_db_path)
    # The controller DB is created only in its explicitly configured parent.
    Path(config.controller_db_path).parent.mkdir(mode=0o700, exist_ok=True)
    try:
        os.chmod(Path(config.controller_db_path).parent, 0o700)
    except OSError:
        raise ServiceError("database_authority_invalid") from None
    try:
        storage = await SqliteStorage.open(config.controller_db_path)
    except Exception:
        raise ServiceError("storage_open_failed") from None
    try:
        authority = IsolationPathAuthority(
            config.profiles, controller_db_path=config.controller_db_path,
            controller_db_root=config.controller_db_root, repository_root=config.repository_root,
            protected_roots=config.protected_roots,
        )
        authority.validate_runtime_authority()
        factory = runtime_manager_factory or CodexRuntimeManager
        runtime_manager = factory(list(config.profiles), client_version="codex-control-p8a",
                                  executable=config.codex_executable, isolation_authority=authority)
        boot = await ControllerRuntimeRepository(storage).begin_boot(config.fleet.fleet_version)
        signal_bus = ApprovalDecisionSignal()
        catalog = CodexModelCatalogAdapter(runtime_manager)
        telegram_transport = telegram or TelegramBotApiTransport(secrets.telegram_bot_token)
        lifecycle = ApprovalAwareTurnLifecycle(
            storage, runtime_manager=runtime_manager, model_catalog=catalog,
            telegram=telegram_transport, approval_signal=signal_bus,
        )
        thread = CodexThreadLifecycleAdapter(runtime_manager, catalog)
        registry = ActiveTurnRegistry()
        resolver = _WorkingDirectoryResolver(config.working_directory)
        turns = DialogueTurnService(
            storage, server_id=config.identity.server_id, profiles=config.profiles,
            model_catalog=catalog, thread_lifecycle=thread, turn_lifecycle=lifecycle,
            working_directory_resolver=resolver, active_turn_registry=registry,
        )
        control = FleetControlService(
            storage, manifest=config.fleet, server_id=config.identity.server_id,
            operator_user_id=config.operator_user_id, control_chat_id=config.control_chat_id,
            boot_result=boot,
        )
        routing = FleetGroupRoutingService(storage, fleet_control=control, dialogue_turn=turns)
        interrupt = DialogueInterruptService(
            storage, server_id=config.identity.server_id, active_turn_registry=registry,
            turn_lifecycle=lifecycle,
        )
        # The cleanup coordinator is intentionally created by the accepted
        # delete service in the same authority graph; no new deletion logic is
        # introduced here.
        from .application.delete_storage_cleanup import DeleteStorageCleanupCoordinator
        cleanup = DeleteStorageCleanupCoordinator(storage, runtime_manager)
        delete = DialogueDeleteService(
            storage, server_id=config.identity.server_id, thread_lifecycle=thread,
            interrupt_service=interrupt, active_turn_registry=registry, local_cleanup=cleanup,
        )
        mode_box: list[Any] = [ControllerMode.SLEEP]
        private = PrivateControlService(
            storage, server_id=config.identity.server_id,
            server_display_name=config.identity.display_name,
            operator_user_id=config.operator_user_id, profiles=config.profiles,
            model_catalog=catalog, interrupt_service=interrupt, delete_service=delete,
            mode_provider=lambda: mode_box[0],
        )
        delivery = TurnDeliveryService(storage, telegram=telegram_transport, text_limit=config.telegram_text_limit)
        orchestrator = LocalControllerOrchestrator(
            storage, group_routing=routing,
            fleet_status=FleetStatusService(config.fleet, server_id=config.identity.server_id),
            fleet_status_renderer=TelegramFleetStatusRenderer(), private_control=private,
            turn_delivery=delivery, turn_lifecycle=lifecycle, approval_signal=signal_bus,
            dialogue_recovery=DialogueRecoveryService(storage, local_cleanup=cleanup),
        )
        return ProductionAssembly(
            config, secrets, storage, runtime_manager, orchestrator, telegram_transport,
            TelegramGroupUpdateAdapter(config.fleet, config.operator_user_id, config.control_chat_id),
            TelegramPrivateUpdateAdapter(config.operator_user_id), TelegramPrivateControlRenderer(),
            TelegramFleetKeyboardRenderer(), ControllerMode.SLEEP, mode_box,
        )
    except ServiceError:
        if storage is not None:
            await storage.close()
        raise
    except (IsolationError, Exception):
        if storage is not None:
            await storage.close()
        raise ServiceError("assembly_failed") from None


class ProductionService:
    """Sequential poll/dispatch loop with bounded, ownership-aware shutdown."""

    def __init__(self, assembly: ProductionAssembly, *, poll_interval: float = 1.0) -> None:
        if poll_interval <= 0 or poll_interval > 60:
            raise ValueError("poll_interval_invalid")
        self.assembly = assembly
        self._poll_interval = poll_interval
        self._stop = asyncio.Event()
        self._accepting = False
        self._poll_task: asyncio.Task[Any] | None = None
        self._closed = False

    def request_stop(self) -> None:
        """Synchronously stop ingress and interrupt an in-flight long poll."""
        self._accepting = False
        self._stop.set()
        task = self._poll_task
        if task is not None and not task.done():
            task.cancel()

    async def startup(self) -> None:
        if self._closed:
            raise ServiceError("service_closed")
        # begin_boot already forced effective SLEEP. Recovery must precede the
        # first call to getUpdates, so the ordinary poll task is created later.
        await self.assembly.orchestrator.recover_startup()
        self._accepting = True

    async def run(self) -> None:
        await self.startup()
        try:
            while not self._stop.is_set():
                self._poll_task = asyncio.create_task(self.assembly.telegram.get_updates())
                try:
                    updates = await self._poll_task
                except asyncio.CancelledError:
                    if self._stop.is_set():
                        break
                    raise
                finally:
                    self._poll_task = None
                for update in updates:
                    if self._stop.is_set() or not self._accepting:
                        break
                    await self.dispatch(update)
                if not updates:
                    try:
                        await asyncio.wait_for(self._stop.wait(), timeout=self._poll_interval)
                    except asyncio.TimeoutError:
                        continue
        finally:
            await self.shutdown()

    async def dispatch(self, update: object) -> None:
        if not self._accepting:
            return
        group = self.assembly.group_adapter.normalize(update)
        raw_chat = update.get("message", {}).get("chat", {}) if isinstance(update, dict) else {}
        is_group_candidate = isinstance(raw_chat, dict) and raw_chat.get("type") == "supergroup"
        # Route by Telegram envelope before normalizing content. A private
        # message is intentionally not a group update and must reach the
        # accepted private adapter.
        if is_group_candidate:
            result = await self.assembly.orchestrator.handle_group(group)
            if result.routing.snapshot is not None:
                self.assembly._mode_box[0] = result.routing.snapshot.effective_mode
            if result.fleet_status_payload is not None:
                await self.assembly.telegram.send_projection(chat_id=self.assembly.config.control_chat_id, projection=result.fleet_status_payload)
            elif group.kind is GroupInboundKind.CONTROL:
                await self.assembly.telegram.send_projection(chat_id=self.assembly.config.control_chat_id, projection={"text": "CodexControl", "reply_markup": self.assembly.keyboard_renderer.render(self.assembly.config.fleet)})
            return
        private = self.assembly.private_adapter.normalize(update)
        if private.kind is PrivateInboundKind.COMMAND:
            result = await self.assembly.orchestrator.handle_private_command(PrivateCommandRequest(private.update_id, private.user_id, private.chat_id, private.command))
        elif private.kind is PrivateInboundKind.CALLBACK:
            result = await self.assembly.orchestrator.handle_private_callback(PrivateCallbackRequest(private.update_id, private.user_id, private.chat_id, private.callback_query_id, private.callback_token))
            await self.assembly.telegram.answer_callback_query(callback_query_id=private.callback_query_id)
        else:
            return
        if result.panel is not None:
            await self.assembly.telegram.send_projection(chat_id=self.assembly.config.operator_user_id, projection=self.assembly.private_renderer.render(result.panel))

    async def shutdown(self) -> None:
        if self._closed:
            return
        self.request_stop()
        if self._poll_task is not None and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        runtime_failure: Exception | None = None
        try:
            await self.assembly.runtime_manager.shutdown_all()
        except Exception as error:
            # Runtime ownership failure must remain observable, but it must
            # not prevent SQLite from closing or turn shutdown into an
            # unbounded partial lifecycle.
            runtime_failure = error
        try:
            await self.assembly.storage.close()
        finally:
            self._closed = True
        if runtime_failure is not None:
            raise ServiceError("runtime_shutdown_failed") from None


def install_signal_handlers(service: ProductionService, loop: asyncio.AbstractEventLoop) -> tuple[signal.Signals, ...]:
    installed: list[signal.Signals] = []
    for value in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(value, service.request_stop)
            installed.append(value)
        except (NotImplementedError, RuntimeError):
            pass
    return tuple(installed)


async def serve(config_path: str | Path, secrets_path: str | Path, *, test_only: bool = False,
                telegram: TelegramBotApiTransport | None = None, runtime_manager_factory: Any | None = None) -> None:
    assembly = await build_production_assembly(config_path, secrets_path, test_only=test_only, telegram=telegram, runtime_manager_factory=runtime_manager_factory)
    service = ProductionService(assembly)
    install_signal_handlers(service, asyncio.get_running_loop())
    await service.run()


# Imported late to keep the service module's dependency graph one-way.
from .domain import ControllerMode


__all__ = ["ProductionAssembly", "ProductionService", "ServiceError", "build_production_assembly", "serve", "validate_production_authority"]
