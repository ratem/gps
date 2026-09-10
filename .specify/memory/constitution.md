<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Modified principles: II. UART and Binary Protocol Fidelity (clarified software and hardware
    verification responsibilities).
- Added sections: none.
- Removed sections: none.
- Follow-up TODOs: none.
-->

# GPS Telemetry System Constitution

## Core Principles

### I. Python Quality and Explicit Interfaces
Production code MUST target Python 3.11 or later, use `pyserial` for serial communication, and
keep hardware interaction behind explicit interfaces. Public functions, state transitions, command
frames, and failure paths MUST have deterministic behavior and clear tests. Complexity that does
not support an ICD requirement or a testable operational need is prohibited.

### II. UART and Binary Protocol Fidelity
All UART connections MUST use 9600 baud, 8 data bits, no parity, one start bit, and one stop bit
(Req: GPS-E-0210). Multi-byte sequences MUST use little-endian ordering (Req: GPS-SW-0015),
and the UART transport MUST transmit each byte LSB-first (Req: GPS-SW-0016). Software MUST
encode and test multi-byte values as little-endian and verify serial configuration and command
frames. Wire-level LSB-first behavior MUST be verified through the selected UART hardware or its
integration documentation because `pyserial` does not control bit order. Commands MUST use the
frame `0x7E | CMD_ID | LEN | DATA | XOR`, with XOR calculated over `CMD_ID`, `LEN`, and `DATA`
(Req: GPS-SW-0170).

### III. Deterministic Timing and Fail-Safe States
Every incoming serial packet read MUST use a 500 ms timeout. An incomplete packet or empty
buffer at that limit MUST raise `SyncError` and transition the system to `ERROR` (Req:
GPS-SW-0270). State transitions MUST be explicit: successful initialization moves `INIT` to
`STANDBY`; only a CMD_ID script trigger moves `STANDBY` to `SCIENCE`; and a timeout in
`SCIENCE` moves to `ERROR` (Reqs: GPS-SM-0010 through GPS-SM-0040). `ERROR` recovery MUST
execute, in order: abort operations, request `SU_R_SDP`, request `SU_R_HK`, produce
`OBC_SU_HK`, then turn off the unit or simulation stream (Req: GPS-SW-0140).

### IV. NMEA Integrity and Telemetry Preservation
Only validated `$GPGGA` ASCII input MAY be logged. The client MUST extract latitude, longitude,
and UTC timestamp and append them to `telemetry.csv` only while in `SCIENCE` (Req:
GPS-SW-0025). The Linux hardware double MUST use a PTY master/slave pair, expose the slave
path, and emit deterministic hardcoded `$GPGGA` data every second (Req: GPS-E-0010). Invalid,
corrupt, incomplete, or untimely data MUST never be silently accepted as telemetry.

### V. Verification and ICD Traceability
Each requirement implemented in code, test, or operational procedure MUST cite its ICD identifier
and be traceable to one or more verification artifacts. Changes MUST follow a read-write-verify
loop and include unit tests for parser and command behavior plus integration tests that exercise
the client against the PTY double. Adversarial tests MUST cover PTY loss and demonstrate that no
system latch-up occurs. Acceptance requires the relevant automated tests to pass.

## Engineering Constraints

The authoritative source is `GPS System Requirements and ICD.md`; this constitution governs
implementation decisions when lower-level artifacts conflict with local convention. The system
MUST retain hardware-agnostic client logic so the PTY slave is a drop-in replacement for a
physical serial port. Physical connector testing MUST not exceed ten mate/de-mate cycles
(Req: GPS-E-0020). Deployment design MUST provide two independent mass-memory units with at
least 10 MB reserved on each for science and housekeeping logs (Req: GPS-SW-0040).

## Development and Verification Workflow

Work MUST begin with or amend a specification that identifies the applicable ICD requirements.
Plans and tasks MUST preserve requirement identifiers and name the verification approach. Before
implementation, cross-artifact review MUST resolve contradictions and untestable acceptance
criteria. Pull requests or equivalent change reviews MUST show the ICD mapping, test evidence,
and any deliberate deviations approved by the project owner.

## Governance

This constitution supersedes informal project practices for the GPS Telemetry System. Amendments
MUST document their rationale, the affected ICD requirements, migration impact, and required test
updates. Versions follow semantic versioning: MAJOR for incompatible principle removal or
redefinition, MINOR for new or materially expanded governance, and PATCH for clarification only.

Every implementation plan, task list, review, and release decision MUST check compliance with
this constitution and `GPS System Requirements and ICD.md`. Exceptions require written approval
from the project owner and a bounded remediation plan. The constitution MUST be reviewed whenever
the ICD changes or a verification failure exposes a governance gap.

**Version**: 1.1.0 | **Ratified**: 2026-09-10 | **Last Amended**: 2026-09-10
