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
from typing import Any, Mapping, Sequence

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
    command_sha256: str


@dataclass(frozen=True)
class CorrelatedWireRecord:
    kind: str
    request_ordinal: int
    local_sequence: int
    thread_sha256: str
    turn_sha256: str
    cwd_sha256: str
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
    )


def _wire_matches_request(wire: CorrelatedWireRecord, request: CapturedRequest) -> bool:
    return (
        wire.kind == request.kind
        and wire.request_ordinal == request.request_ordinal
        and wire.local_sequence == request.local_sequence
        and wire.thread_sha256 == request.thread_sha256
        and wire.turn_sha256 == request.turn_sha256
        and wire.cwd_sha256 == request.cwd_sha256
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
SYNTHETIC_THREAD_SHA = _sha256("synthetic-p7c12-thread")
SYNTHETIC_TURN_SHA = _sha256("synthetic-p7c12-turn")
SYNTHETIC_CWD_SHA = _sha256("/synthetic/p7c12-cwd")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
) -> tuple[CapturedRequest, ExpectedAuthority, CorrelatedWireRecord]:
    value = command if command is not None else shlex.join(["/bin/bash", "-lc", f"touch {target}"])
    digest = _sha256(value)
    request = CapturedRequest(
        kind, request_ordinal, local_sequence, thread_sha256, turn_sha256,
        cwd_sha256, digest,
    )
    expected = ExpectedAuthority(
        kind, request_ordinal, local_sequence, thread_sha256, turn_sha256,
        cwd_sha256, target, digest,
    )
    wire = CorrelatedWireRecord(
        kind, request_ordinal, local_sequence, thread_sha256, turn_sha256,
        cwd_sha256, _sha256(target), value, digest,
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


class AuthorityProjectionError(ValueError):
    """Bounded test-only failure before any matcher projection is returned."""


@dataclass(frozen=True)
class RetainedAuthorityFixture:
    journal_records: tuple[Mapping[str, Any], ...]
    wire: Mapping[str, Any]
    child_result: Mapping[str, Any]
    parent_result: Mapping[str, Any] | None
    parent_outcome: Mapping[str, Any] | None


_APPROVAL_EVENT_RE = re.compile(r"^APPROVAL_REQUEST_([1-9][0-9]*)_OBSERVED$")
_DENY_INTENT_RE = re.compile(r"^DENY_RESPONSE_([1-9][0-9]*)_DISPATCH_INTENT$")
_DENY_RESULT_RE = re.compile(r"^DENY_RESPONSE_([1-9][0-9]*)_RESULT$")
_RETAINED_TARGET_RE = re.compile(r"/root/\.codexcontrol-p7c11-escalation-probe-[0-9a-f]{32}")


def _projection_require(condition: bool, reason: str) -> None:
    if not condition:
        raise AuthorityProjectionError(reason)


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _candidate_target_from_wire(command: object, *, retained: bool) -> str:
    """Recover one exact target in memory from an already validated wire."""
    _projection_require(isinstance(command, str) and command, "WIRE_COMMAND_INVALID")
    try:
        vector = shlex.split(command, comments=False, posix=True)
    except (TypeError, ValueError) as error:
        raise AuthorityProjectionError("WIRE_COMMAND_NOT_SHLEX_CANONICAL") from error
    _projection_require(shlex.join(vector) == command, "WIRE_COMMAND_NOT_SHLEX_CANONICAL")
    _projection_require(vector[:2] == ["/bin/bash", "-lc"] and len(vector) == 3, "WIRE_COMMAND_VECTOR_INVALID")
    try:
        inner = shlex.split(vector[2], comments=False, posix=True)
    except (TypeError, ValueError) as error:
        raise AuthorityProjectionError("WIRE_INNER_NOT_SHLEX_CANONICAL") from error
    _projection_require(shlex.join(inner) == vector[2] and len(inner) == 2 and inner[0] == "touch", "WIRE_INNER_INVALID")
    target = inner[1]
    _projection_require(vector[2] == f"touch {target}" and vector[2].count(target) == 1, "TARGET_CANDIDATE_INVALID")
    if retained:
        matches = _RETAINED_TARGET_RE.findall(vector[2])
        _projection_require(len(matches) == 1 and matches[0] == target, "RETAINED_TARGET_CANDIDATE_INVALID")
    return target


def _require_deny_chronology(
    records: Sequence[Mapping[str, Any]], *, request_ordinal: int,
) -> None:
    positions = {id(record): index for index, record in enumerate(records)}
    intents = [(record, _DENY_INTENT_RE.fullmatch(str(record.get("event", "")))) for record in records]
    results = [(record, _DENY_RESULT_RE.fullmatch(str(record.get("event", "")))) for record in records]
    intents = [(record, match) for record, match in intents if match is not None]
    results = [(record, match) for record, match in results if match is not None]
    _projection_require(len(intents) == 1 and len(results) == 1, "DENY_CHRONOLOGY_CARDINALITY_INVALID")
    intent, intent_match = intents[0]
    result, result_match = results[0]
    _projection_require(
        int(intent_match.group(1)) == request_ordinal
        and int(result_match.group(1)) == request_ordinal
        and intent.get("request_count") == request_ordinal
        and result.get("request_count") == request_ordinal,
        "DENY_CHRONOLOGY_ORDINAL_INVALID",
    )
    _projection_require(
        type(intent.get("attempt")) is int
        and type(result.get("attempt")) is int
        and intent.get("attempt") == result.get("attempt")
        and intent.get("status") == "PENDING"
        and result.get("result") == "DENIED_CONFIRMED",
        "DENY_CHRONOLOGY_RESULT_INVALID",
    )
    request_records = [
        record for record in records
        if _APPROVAL_EVENT_RE.fullmatch(str(record.get("event", ""))) is not None
    ]
    _projection_require(len(request_records) == 1, "APPROVAL_REQUEST_CARDINALITY_INVALID")
    request_position = positions[id(request_records[0])]
    _projection_require(request_position < positions[id(intent)] < positions[id(result)], "DENY_CHRONOLOGY_ORDER_INVALID")


def project_retained_authority(
    fixture: RetainedAuthorityFixture, *, retained_target_shape: bool = False,
) -> tuple[CapturedRequest, ExpectedAuthority, CorrelatedWireRecord]:
    """Reconcile independent retained authorities, then project pure matcher inputs."""
    records = fixture.journal_records
    request_records = [
        (record, _APPROVAL_EVENT_RE.fullmatch(str(record.get("event", ""))))
        for record in records
    ]
    request_records = [(record, match) for record, match in request_records if match is not None]
    _projection_require(len(request_records) == 1, "APPROVAL_REQUEST_CARDINALITY_INVALID")
    journal_request, request_match = request_records[0]
    ordinal = int(request_match.group(1))
    _projection_require(type(journal_request.get("request_count")) is int and journal_request.get("request_count") == ordinal, "APPROVAL_REQUEST_ORDINAL_INVALID")
    _projection_require(journal_request.get("kind") == "command_execution", "APPROVAL_REQUEST_KIND_INVALID")
    _projection_require(
        journal_request.get("thread_match") is True
        and journal_request.get("turn_match") is True
        and journal_request.get("cwd_match") is True,
        "APPROVAL_REQUEST_IDENTITY_FLAGS_INVALID",
    )
    journal_wire_sha = journal_request.get("wire_command_sha256")
    _projection_require(_valid_sha(journal_wire_sha), "APPROVAL_REQUEST_WIRE_SHA_INVALID")
    _projection_require(journal_request.get("sentinel_reference_class") == c11.SENTINEL_EMBEDDED, "APPROVAL_REQUEST_SENTINEL_CLASS_INVALID")

    wire = fixture.wire
    _projection_require(wire.get("request_kind") == "command_execution", "WIRE_KIND_INVALID")
    local_sequence = wire.get("local_request_sequence")
    _projection_require(type(local_sequence) is int and local_sequence == ordinal, "WIRE_SEQUENCE_INVALID")
    for key in ("thread_id_sha256", "turn_id_sha256", "actual_cwd_sha256", "expected_sentinel_path_sha256", "wire_command_sha256"):
        _projection_require(_valid_sha(wire.get(key)), f"WIRE_{key.upper()}_INVALID")
    wire_sha = wire["wire_command_sha256"]
    _projection_require(journal_wire_sha == wire_sha, "JOURNAL_WIRE_SHA_MISMATCH")
    command = wire.get("wire_command_plaintext")
    _projection_require(_sha256(command) == wire_sha if isinstance(command, str) else False, "WIRE_COMMAND_SHA_MISMATCH")

    # Identity hashes are projected only after the journal has proven all three matches.
    target = _candidate_target_from_wire(command, retained=retained_target_shape)
    candidate_target_sha = _sha256(target)
    _projection_require(wire["expected_sentinel_path_sha256"] == candidate_target_sha, "WIRE_TARGET_SHA_MISMATCH")

    child_hash = fixture.child_result.get("target_sentinel_path_sha256")
    _projection_require(_valid_sha(child_hash) and child_hash == candidate_target_sha, "CHILD_TARGET_SHA_MISMATCH")
    if fixture.parent_result is not None:
        parent = fixture.parent_result
        parent_hash = parent.get("parent_target_sentinel_path_sha256")
        _projection_require(_valid_sha(parent_hash) and parent_hash == candidate_target_sha, "PARENT_TARGET_SHA_MISMATCH")
        if "target_sentinel_path_sha256" in parent:
            _projection_require(parent.get("target_sentinel_path_sha256") == candidate_target_sha, "PARENT_CHILD_TARGET_SHA_MISMATCH")
    if fixture.parent_outcome is not None and "normal_final_result_present" in fixture.parent_outcome:
        _projection_require(fixture.parent_outcome.get("normal_final_result_present") is True, "PARENT_OUTCOME_NOT_FINAL")

    _require_deny_chronology(records, request_ordinal=ordinal)
    thread_sha = wire["thread_id_sha256"]
    turn_sha = wire["turn_id_sha256"]
    cwd_sha = wire["actual_cwd_sha256"]
    request = CapturedRequest("COMMAND_EXECUTION", ordinal, local_sequence, thread_sha, turn_sha, cwd_sha, wire_sha)
    expected = ExpectedAuthority("COMMAND_EXECUTION", ordinal, local_sequence, thread_sha, turn_sha, cwd_sha, target, wire_sha)
    correlated_wire = CorrelatedWireRecord(
        "COMMAND_EXECUTION", ordinal, local_sequence, thread_sha, turn_sha, cwd_sha,
        candidate_target_sha, command, wire_sha,
    )
    return request, expected, correlated_wire


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
    c11.validate_child_result(child)
    parent = c11.read_bounded_private_json(c11.REAL_PROBE_RESULT)
    c11.validate_parent_final_result(parent)
    outcome = c11.read_bounded_private_json(c11.REAL_PROBE_OUTCOME)
    c11.validate_parent_execution_outcome(outcome)
    fixture = RetainedAuthorityFixture(tuple(journal), raw, child, parent, outcome)
    return project_retained_authority(fixture, retained_target_shape=True)


def _synthetic_retained_authority() -> RetainedAuthorityFixture:
    _request, expected, wire = _synthetic_authority()
    journal = (
        {
            "event": "APPROVAL_REQUEST_1_OBSERVED", "request_count": 1,
            "kind": "command_execution", "thread_match": True, "turn_match": True,
            "cwd_match": True, "wire_command_sha256": wire.command_sha256,
            "sentinel_reference_class": c11.SENTINEL_EMBEDDED,
        },
        {
            "event": "DENY_RESPONSE_1_DISPATCH_INTENT", "status": "PENDING",
            "attempt": 1, "request_count": 1,
        },
        {
            "event": "DENY_RESPONSE_1_RESULT", "result": "DENIED_CONFIRMED",
            "attempt": 1, "request_count": 1,
        },
    )
    wire_authority = {
        "format": 1, "thread_id_sha256": wire.thread_sha256,
        "turn_id_sha256": wire.turn_sha256, "actual_cwd_sha256": wire.cwd_sha256,
        "expected_sentinel_path_sha256": wire.expected_target_sha256,
        "wire_command_plaintext": wire.command_plaintext,
        "wire_command_sha256": wire.command_sha256,
        "request_kind": "command_execution", "local_request_sequence": 1,
        "capture_status": "CAPTURED_ROOT_ONLY",
    }
    expected_target_sha = wire.expected_target_sha256
    child = {"target_sentinel_path_sha256": expected_target_sha}
    parent = {
        "target_sentinel_path_sha256": expected_target_sha,
        "parent_target_sentinel_path_sha256": expected_target_sha,
    }
    outcome = {"normal_final_result_present": True}
    return RetainedAuthorityFixture(journal, wire_authority, child, parent, outcome)


class P7C12RetainedAuthorityProjectionTests(unittest.TestCase):
    def test_independent_authorities_project_only_after_all_bindings(self) -> None:
        fixture = _synthetic_retained_authority()
        request, expected, wire = project_retained_authority(fixture)
        self.assertEqual(
            set(request.__dict__),
            {"kind", "request_ordinal", "local_sequence", "thread_sha256", "turn_sha256", "cwd_sha256", "command_sha256"},
        )
        self.assertEqual(strict_p7c12_match(request, expected, [wire]), MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND)

    def test_independent_authority_corruption_matrix_fails_before_match(self) -> None:
        def mutate(
            base: RetainedAuthorityFixture, *,
            journal_changes: Mapping[int, Mapping[str, Any]] | None = None,
            append_journal: Mapping[str, Any] | None = None,
            wire_changes: Mapping[str, Any] | None = None,
            child_changes: Mapping[str, Any] | None = None,
            parent_changes: Mapping[str, Any] | None = None,
        ) -> RetainedAuthorityFixture:
            records = [dict(record) for record in base.journal_records]
            for index, changes in (journal_changes or {}).items():
                records[index].update(changes)
            if append_journal is not None:
                records.append(dict(append_journal))
            return RetainedAuthorityFixture(
                tuple(records), {**base.wire, **(wire_changes or {})},
                {**base.child_result, **(child_changes or {})},
                None if base.parent_result is None else {**base.parent_result, **(parent_changes or {})},
                base.parent_outcome,
            )

        base = _synthetic_retained_authority()
        request_record = base.journal_records[0]
        result_record = base.journal_records[2]
        cases = (
            ("journal wire SHA", mutate(base, journal_changes={0: {"wire_command_sha256": "0" * 64}})),
            ("journal kind", mutate(base, journal_changes={0: {"kind": "file_change"}})),
            ("journal ordinal", mutate(base, journal_changes={0: {"request_count": 2}})),
            ("journal thread flag", mutate(base, journal_changes={0: {"thread_match": False}})),
            ("journal Turn flag", mutate(base, journal_changes={0: {"turn_match": False}})),
            ("journal cwd flag", mutate(base, journal_changes={0: {"cwd_match": False}})),
            ("journal sentinel class", mutate(base, journal_changes={0: {"sentinel_reference_class": c11.SENTINEL_EXACT_ARG}})),
            ("DENY ordinal", mutate(base, journal_changes={1: {"event": "DENY_RESPONSE_2_DISPATCH_INTENT", "request_count": 2}})),
            ("DENY attempt", mutate(base, journal_changes={2: {"attempt": 2}})),
            ("DENY unknown result", mutate(base, journal_changes={2: {"result": "RESPONSE_UNKNOWN"}})),
            ("DENY chronology", mutate(base, journal_changes={1: {"event": "DENY_RESPONSE_1_RESULT", "result": "DENIED_CONFIRMED"}, 2: {"event": "DENY_RESPONSE_1_DISPATCH_INTENT", "status": "PENDING"}})),
            ("child target SHA", mutate(base, child_changes={"target_sentinel_path_sha256": "1" * 64})),
            ("parent target SHA", mutate(base, parent_changes={"parent_target_sentinel_path_sha256": "2" * 64})),
            ("wire target SHA", mutate(base, wire_changes={"expected_sentinel_path_sha256": "3" * 64})),
            ("multiple approval records", mutate(base, append_journal=request_record)),
            ("multiple DENY result records", mutate(base, append_journal=result_record)),
        )
        self.assertEqual(len(cases), 16)
        for label, corrupted in cases:
            with self.subTest(case=label):
                with self.assertRaises(AuthorityProjectionError):
                    project_retained_authority(corrupted)


class P7C12RetainedGoldenOfflineTests(unittest.TestCase):
    def test_retained_p7c11_wire_matches_in_memory(self) -> None:
        request, expected, wire = _retained_c11_authority()
        self.assertEqual(
            strict_p7c12_match(request, expected, [wire]),
            MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND,
        )


if __name__ == "__main__":
    unittest.main()
