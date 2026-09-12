"""P7.C12 strict approval matcher construction.

This module is deliberately offline and test-only.  The matcher classifies a
captured request; it never answers an approval request and never executes a
command.  The retained P7.C11 replay uses only the accepted bounded readers
from the immutable C11 harness and keeps retained plaintext in local memory.
"""

from __future__ import annotations

import hashlib
import re
import shlex
import unittest
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

from tests.real import test_p7_c11_deny_only_approval_probe as c11


class MatcherResult(str, Enum):
    MATCH_EXACT_P7_APPROVAL_COMMAND = "MATCH_EXACT_P7_APPROVAL_COMMAND"
    NO_MATCH_KIND = "NO_MATCH_KIND"
    NO_MATCH_REQUEST_IDENTITY = "NO_MATCH_REQUEST_IDENTITY"
    NO_MATCH_WIRE_AUTHORITY = "NO_MATCH_WIRE_AUTHORITY"
    NO_MATCH_VECTOR = "NO_MATCH_VECTOR"
    NO_MATCH_SHELL_EXECUTABLE = "NO_MATCH_SHELL_EXECUTABLE"
    NO_MATCH_SHELL_OPTION = "NO_MATCH_SHELL_OPTION"
    NO_MATCH_INNER_COMMAND = "NO_MATCH_INNER_COMMAND"
    NO_MATCH_TARGET = "NO_MATCH_TARGET"
    NO_MATCH_EXTRA_OPERATION = "NO_MATCH_EXTRA_OPERATION"
    NO_MATCH_AMBIGUOUS_OR_MULTIPLE = "NO_MATCH_AMBIGUOUS_OR_MULTIPLE"


@dataclass(frozen=True)
class ExpectedAuthority:
    kind: str
    request_ordinal: int
    local_sequence: int
    thread_sha256: str
    turn_sha256: str
    cwd_sha256: str
    correlation_key: str
    target: str
    command_sha256: str


@dataclass(frozen=True)
class CapturedRequest:
    kind: str
    request_ordinal: int
    local_sequence: int
    thread_sha256: str
    turn_sha256: str
    cwd_sha256: str
    correlation_key: str
    command_sha256: str


@dataclass(frozen=True)
class CorrelatedWireRecord:
    kind: str
    request_ordinal: int
    local_sequence: int
    thread_sha256: str
    turn_sha256: str
    cwd_sha256: str
    correlation_key: str
    expected_target_sha256: str
    command_plaintext: str
    command_sha256: str


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request_matches_expected(request: CapturedRequest, expected: ExpectedAuthority) -> bool:
    return (
        request.kind == expected.kind
        and request.request_ordinal == expected.request_ordinal
        and request.local_sequence == expected.local_sequence
        and request.thread_sha256 == expected.thread_sha256
        and request.turn_sha256 == expected.turn_sha256
        and request.cwd_sha256 == expected.cwd_sha256
        and request.correlation_key == expected.correlation_key
    )


def _wire_matches_request(wire: CorrelatedWireRecord, request: CapturedRequest) -> bool:
    return (
        wire.kind == request.kind
        and wire.request_ordinal == request.request_ordinal
        and wire.local_sequence == request.local_sequence
        and wire.thread_sha256 == request.thread_sha256
        and wire.turn_sha256 == request.turn_sha256
        and wire.cwd_sha256 == request.cwd_sha256
        and wire.correlation_key == request.correlation_key
    )


def strict_p7c12_match(
    request: CapturedRequest,
    expected: ExpectedAuthority,
    wire_records: Sequence[CorrelatedWireRecord],
) -> MatcherResult:
    """Return one finite classification for one captured request.

    Every value used by this function is supplied by the caller.  In
    particular, no filesystem, subprocess, network, approval, or protocol
    operation is reachable from this matcher.
    """
    if not isinstance(request, CapturedRequest) or not isinstance(expected, ExpectedAuthority):
        return MatcherResult.NO_MATCH_WIRE_AUTHORITY
    if request.kind != "COMMAND_EXECUTION" or expected.kind != "COMMAND_EXECUTION":
        return MatcherResult.NO_MATCH_KIND
    if not _request_matches_expected(request, expected):
        return MatcherResult.NO_MATCH_REQUEST_IDENTITY
    if not isinstance(wire_records, Sequence) or isinstance(wire_records, (str, bytes)):
        return MatcherResult.NO_MATCH_WIRE_AUTHORITY
    if len(wire_records) != 1:
        return MatcherResult.NO_MATCH_AMBIGUOUS_OR_MULTIPLE
    wire = wire_records[0]
    if not isinstance(wire, CorrelatedWireRecord) or not _wire_matches_request(wire, request):
        return MatcherResult.NO_MATCH_WIRE_AUTHORITY

    command = wire.command_plaintext
    if (
        not isinstance(command, str)
        or not command
        or _sha256(command) != wire.command_sha256
        or request.command_sha256 != wire.command_sha256
        or expected.command_sha256 != wire.command_sha256
        or not isinstance(expected.target, str)
        or not expected.target
        or wire.expected_target_sha256 != _sha256(expected.target)
    ):
        return MatcherResult.NO_MATCH_WIRE_AUTHORITY

    try:
        vector = shlex.split(command, comments=False, posix=True)
    except (TypeError, ValueError):
        return MatcherResult.NO_MATCH_WIRE_AUTHORITY
    if not vector or shlex.join(vector) != command:
        return MatcherResult.NO_MATCH_WIRE_AUTHORITY
    if len(vector) != 3:
        return MatcherResult.NO_MATCH_VECTOR
    if vector[0] != "/bin/bash":
        return MatcherResult.NO_MATCH_SHELL_EXECUTABLE
    if vector[1] != "-lc":
        return MatcherResult.NO_MATCH_SHELL_OPTION

    script = vector[2]
    target = expected.target
    occurrence_count = script.count(target)
    if occurrence_count == 0:
        return MatcherResult.NO_MATCH_TARGET
    if occurrence_count != 1:
        return MatcherResult.NO_MATCH_AMBIGUOUS_OR_MULTIPLE
    if script != f"touch {target}":
        if any(
            marker in script
            for marker in (
                ";", "&&", "||", "|", ">", "<", "$(", "`", "${", "*", "?",
            )
        ) or script.count("touch") > 1:
            return MatcherResult.NO_MATCH_EXTRA_OPERATION
        return MatcherResult.NO_MATCH_TARGET
    try:
        inner = shlex.split(script, comments=False, posix=True)
    except (TypeError, ValueError):
        return MatcherResult.NO_MATCH_INNER_COMMAND
    if shlex.join(inner) != script or len(inner) != 2:
        return MatcherResult.NO_MATCH_INNER_COMMAND
    if inner != ["touch", target]:
        return MatcherResult.NO_MATCH_INNER_COMMAND
    return MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND


SYNTHETIC_TARGET = "/synthetic/p7c12-target-0123456789abcdef"
SYNTHETIC_ESCAPED_TARGET = SYNTHETIC_TARGET.replace("-", r"\-")
SYNTHETIC_KIND = "COMMAND_EXECUTION"
SYNTHETIC_CORRELATION = "synthetic-p7c12-correlation-1"
SYNTHETIC_THREAD_SHA = _sha256("synthetic-p7c12-thread")
SYNTHETIC_TURN_SHA = _sha256("synthetic-p7c12-turn")
SYNTHETIC_CWD_SHA = _sha256("/synthetic/p7c12-cwd")


def _synthetic_authority(
    *,
    command: str | None = None,
    target: str = SYNTHETIC_TARGET,
    kind: str = SYNTHETIC_KIND,
    request_ordinal: int = 1,
    local_sequence: int = 1,
    thread_sha256: str = SYNTHETIC_THREAD_SHA,
    turn_sha256: str = SYNTHETIC_TURN_SHA,
    cwd_sha256: str = SYNTHETIC_CWD_SHA,
    correlation_key: str = SYNTHETIC_CORRELATION,
) -> tuple[CapturedRequest, ExpectedAuthority, CorrelatedWireRecord]:
    value = command if command is not None else shlex.join(["/bin/bash", "-lc", f"touch {target}"])
    digest = _sha256(value)
    request = CapturedRequest(
        kind, request_ordinal, local_sequence, thread_sha256, turn_sha256,
        cwd_sha256, correlation_key, digest,
    )
    expected = ExpectedAuthority(
        kind, request_ordinal, local_sequence, thread_sha256, turn_sha256,
        cwd_sha256, correlation_key, target, digest,
    )
    wire = CorrelatedWireRecord(
        kind, request_ordinal, local_sequence, thread_sha256, turn_sha256,
        cwd_sha256, correlation_key, _sha256(target), value, digest,
    )
    return request, expected, wire


def _synthetic_case(
    *,
    command: str | None = None,
    **changes: object,
) -> tuple[CapturedRequest, ExpectedAuthority, CorrelatedWireRecord]:
    request, expected, wire = _synthetic_authority(command=command)
    request_values = request.__dict__.copy()
    expected_values = expected.__dict__.copy()
    wire_values = wire.__dict__.copy()
    for key, value in changes.items():
        if key in request_values:
            request_values[key] = value
        elif key in expected_values:
            expected_values[key] = value
        elif key in wire_values:
            wire_values[key] = value
        else:
            raise AssertionError("unknown synthetic mutation")
    return (
        CapturedRequest(**request_values),
        ExpectedAuthority(**expected_values),
        CorrelatedWireRecord(**wire_values),
    )


def _run(request: CapturedRequest, expected: ExpectedAuthority, wire: CorrelatedWireRecord | None) -> MatcherResult:
    return strict_p7c12_match(request, expected, [] if wire is None else [wire])


class P7C12PositiveOfflineTests(unittest.TestCase):
    def test_exact_synthetic_request_matches(self) -> None:
        request, expected, wire = _synthetic_authority()
        self.assertEqual(strict_p7c12_match(request, expected, [wire]), MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND)

    def test_accepted_shlex_round_trip_matches(self) -> None:
        request, expected, wire = _synthetic_authority()
        self.assertEqual(shlex.join(shlex.split(wire.command_plaintext, comments=False, posix=True)), wire.command_plaintext)
        self.assertEqual(strict_p7c12_match(request, expected, [wire]), MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND)

    def test_repeated_invocation_is_deterministic_and_pure(self) -> None:
        request, expected, wire = _synthetic_authority()
        before = (request, expected, wire)
        results = [strict_p7c12_match(request, expected, [wire]) for _ in range(25)]
        self.assertEqual(results, [MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND] * 25)
        self.assertEqual((request, expected, wire), before)

    def test_each_authority_component_mutation_fails_closed(self) -> None:
        mutations = (
            {"request_ordinal": 2}, {"local_sequence": 2},
            {"thread_sha256": _sha256("wrong-thread")},
            {"turn_sha256": _sha256("wrong-turn")},
            {"cwd_sha256": _sha256("/synthetic/other-cwd")},
            {"correlation_key": "synthetic-p7c12-other-correlation"},
            {"kind": "FILE_CHANGE"},
            {"command_sha256": _sha256("synthetic-other-command")},
            {"target": "/synthetic/p7c12-other-target"},
        )
        for mutation in mutations:
            with self.subTest(component=next(iter(mutation))):
                request, expected, wire = _synthetic_case(**mutation)
                self.assertNotEqual(_run(request, expected, wire), MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND)


NEGATIVE_COMMANDS: tuple[tuple[str, str], ...] = (
    ("wrong shell PATH lookup", shlex.join(["bash", "-lc", f"touch {SYNTHETIC_TARGET}"])),
    ("wrong absolute shell", shlex.join(["/usr/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}"])),
    ("sh", shlex.join(["/bin/sh", "-lc", f"touch {SYNTHETIC_TARGET}"])),
    ("zsh", shlex.join(["/bin/zsh", "-lc", f"touch {SYNTHETIC_TARGET}"])),
    ("c option", shlex.join(["/bin/bash", "-c", f"touch {SYNTHETIC_TARGET}"])),
    ("alternate option", shlex.join(["/bin/bash", "--", f"touch {SYNTHETIC_TARGET}"])),
    ("direct target outer argv", shlex.join(["/bin/bash", "-lc", SYNTHETIC_TARGET])),
    ("missing target", shlex.join(["/bin/bash", "-lc", "touch"])),
    ("wrong target", shlex.join(["/bin/bash", "-lc", "touch /synthetic/p7c12-other-target"])),
    ("target prefix", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}-suffix"])),
    ("target suffix", shlex.join(["/bin/bash", "-lc", f"touch prefix-{SYNTHETIC_TARGET}"])),
    ("target embedded", shlex.join(["/bin/bash", "-lc", f"touch prefix{SYNTHETIC_TARGET}suffix"])),
    ("two target occurrences", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} {SYNTHETIC_TARGET}"])),
    ("leading script whitespace", shlex.join(["/bin/bash", "-lc", f" touch {SYNTHETIC_TARGET}"])),
    ("trailing script whitespace", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} "])),
    ("interposed whitespace", shlex.join(["/bin/bash", "-lc", f"touch  {SYNTHETIC_TARGET}"])),
    ("quoted alternate", shlex.join(["/bin/bash", "-lc", f"touch '{SYNTHETIC_TARGET}'"])),
    ("escaped alternate", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_ESCAPED_TARGET}"])),
    ("extra argument", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} extra"])),
    ("newline", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}\n"])),
    ("semicolon", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}; true"])),
    ("and", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} && true"])),
    ("or", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} || true"])),
    ("pipe", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} | true"])),
    ("stdout redirect", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} > /synthetic/out"])),
    ("stderr redirect", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} 2> /synthetic/err"])),
    ("command substitution", shlex.join(["/bin/bash", "-lc", f"touch $(printf {SYNTHETIC_TARGET})"])),
    ("variable expansion", shlex.join(["/bin/bash", "-lc", "touch $P7C12_TARGET"])),
    ("wildcard", shlex.join(["/bin/bash", "-lc", "touch /synthetic/p7c12-*"])),
    ("env wrapper", shlex.join(["/bin/bash", "-lc", f"env touch {SYNTHETIC_TARGET}"])),
    ("sudo wrapper", shlex.join(["/bin/bash", "-lc", f"sudo touch {SYNTHETIC_TARGET}"])),
    ("command wrapper", shlex.join(["/bin/bash", "-lc", f"command touch {SYNTHETIC_TARGET}"])),
    ("exec wrapper", shlex.join(["/bin/bash", "-lc", f"exec touch {SYNTHETIC_TARGET}"])),
    ("timeout wrapper", shlex.join(["/bin/bash", "-lc", f"timeout 1 touch {SYNTHETIC_TARGET}"])),
    ("second touch", shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}; touch /synthetic/other"])),
    ("retry loop", shlex.join(["/bin/bash", "-lc", f"for i in 1 2; do touch {SYNTHETIC_TARGET}; done"])),
    ("other equivalent executable", shlex.join(["/bin/bash", "-lc", f"install /dev/null {SYNTHETIC_TARGET}"])),
)


class P7C12NegativeOfflineTests(unittest.TestCase):
    def test_required_negative_command_matrix_fails_closed(self) -> None:
        for label, command in NEGATIVE_COMMANDS:
            with self.subTest(case=label):
                request, expected, wire = _synthetic_authority(command=command)
                self.assertNotEqual(_run(request, expected, wire), MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND)

    def test_wrong_kind_ordinal_sequence_thread_turn_and_cwd_fail_closed(self) -> None:
        for label, mutation in (
            ("kind", {"kind": "FILE_CHANGE"}),
            ("ordinal", {"request_ordinal": 9}),
            ("sequence", {"local_sequence": 9}),
            ("thread", {"thread_sha256": _sha256("wrong-thread")}),
            ("turn", {"turn_sha256": _sha256("wrong-turn")}),
            ("cwd", {"cwd_sha256": _sha256("/synthetic/wrong-cwd")}),
        ):
            with self.subTest(case=label):
                request, expected, wire = _synthetic_case(**mutation)
                self.assertNotEqual(_run(request, expected, wire), MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND)

    def test_missing_duplicate_hash_malformed_and_vector_authority_fail_closed(self) -> None:
        request, expected, wire = _synthetic_authority()
        self.assertEqual(_run(request, expected, None), MatcherResult.NO_MATCH_AMBIGUOUS_OR_MULTIPLE)
        self.assertEqual(strict_p7c12_match(request, expected, [wire, wire]), MatcherResult.NO_MATCH_AMBIGUOUS_OR_MULTIPLE)
        bad_hash = CorrelatedWireRecord(**{**wire.__dict__, "command_sha256": "0" * 64})
        self.assertEqual(_run(request, expected, bad_hash), MatcherResult.NO_MATCH_WIRE_AUTHORITY)
        malformed = CorrelatedWireRecord(**{**wire.__dict__, "command_plaintext": "'/bin/bash -lc"})
        malformed = CorrelatedWireRecord(**{**malformed.__dict__, "command_sha256": _sha256(malformed.command_plaintext)})
        request = CapturedRequest(**{**request.__dict__, "command_sha256": malformed.command_sha256})
        expected = ExpectedAuthority(**{**expected.__dict__, "command_sha256": malformed.command_sha256})
        self.assertEqual(_run(request, expected, malformed), MatcherResult.NO_MATCH_WIRE_AUTHORITY)
        for length in (1, 2, 4, 5):
            vector = ["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}", "extra", "another"]
            command = shlex.join(vector[:length])
            request, expected, wire = _synthetic_authority(command=command)
            self.assertEqual(_run(request, expected, wire), MatcherResult.NO_MATCH_VECTOR)
        request, expected, wire = _synthetic_authority(command="")
        self.assertEqual(_run(request, expected, wire), MatcherResult.NO_MATCH_WIRE_AUTHORITY)

    def test_substring_match_can_never_produce_match(self) -> None:
        command = shlex.join(["/bin/bash", "-lc", f"touch prefix-{SYNTHETIC_TARGET}-suffix"])
        request, expected, wire = _synthetic_authority(command=command)
        self.assertEqual(_run(request, expected, wire), MatcherResult.NO_MATCH_TARGET)

    def test_compound_commands_can_never_produce_match(self) -> None:
        for command in (
            shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET}; true"]),
            shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} && true"]),
            shlex.join(["/bin/bash", "-lc", f"touch {SYNTHETIC_TARGET} | true"]),
        ):
            request, expected, wire = _synthetic_authority(command=command)
            self.assertEqual(_run(request, expected, wire), MatcherResult.NO_MATCH_EXTRA_OPERATION)


def _retained_c11_authority() -> tuple[CapturedRequest, ExpectedAuthority, CorrelatedWireRecord]:
    candidates = sorted(
        Path("/tmp").glob(
            "codexcontrol-p7c11-parent-*/codexcontrol-p7c11-probe-*/wire-command-recovery.json"
        )
    )
    if len(candidates) != 1:
        raise AssertionError("retained P7.C11 wire authority is not unique")
    wire_path = candidates[0]
    raw = c11.read_wire_authority(wire_path)
    journal = c11.read_authoritative_recovery_journal(wire_path.parent / "probe-recovery.json")
    child = c11.read_bounded_private_json(wire_path.parent / "probe-child-result.json")
    if not child or not journal:
        raise AssertionError("retained P7.C11 bounded authority is empty")
    if raw["local_request_sequence"] != 1 or raw["request_kind"] != "command_execution":
        raise AssertionError("retained P7.C11 request authority mismatch")
    request_events = [record for record in journal if record.get("event") == "APPROVAL_REQUEST_1_OBSERVED"]
    deny_results = [record for record in journal if record.get("event") == "DENY_RESPONSE_1_RESULT"]
    if len(request_events) != 1 or len(deny_results) != 1 or deny_results[0].get("result") != "DENIED_CONFIRMED":
        raise AssertionError("retained P7.C11 deny chronology mismatch")
    target_matches = re.findall(r"/root/\.codexcontrol-p7c11-escalation-probe-[0-9a-f]{32}", raw["wire_command_plaintext"])
    if len(target_matches) != 1:
        raise AssertionError("retained P7.C11 target occurrence is not unique")
    target = target_matches[0]
    correlation = "retained-p7c11-authoritative-sequence-1"
    request = CapturedRequest(
        "COMMAND_EXECUTION", 1, raw["local_request_sequence"], raw["thread_id_sha256"],
        raw["turn_id_sha256"], raw["actual_cwd_sha256"], correlation, raw["wire_command_sha256"],
    )
    expected = ExpectedAuthority(
        "COMMAND_EXECUTION", 1, raw["local_request_sequence"], raw["thread_id_sha256"],
        raw["turn_id_sha256"], raw["actual_cwd_sha256"], correlation, target,
        raw["wire_command_sha256"],
    )
    wire = CorrelatedWireRecord(
        "COMMAND_EXECUTION", 1, raw["local_request_sequence"], raw["thread_id_sha256"],
        raw["turn_id_sha256"], raw["actual_cwd_sha256"], correlation,
        raw["expected_sentinel_path_sha256"], raw["wire_command_plaintext"],
        raw["wire_command_sha256"],
    )
    return request, expected, wire


class P7C12RetainedGoldenOfflineTests(unittest.TestCase):
    def test_retained_p7c11_wire_matches_in_memory(self) -> None:
        request, expected, wire = _retained_c11_authority()
        self.assertEqual(
            strict_p7c12_match(request, expected, [wire]),
            MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND,
        )


if __name__ == "__main__":
    unittest.main()
