# Implementation Plan: GPS Telemetry Client and PTY Simulator

**Branch**: `001-gps-telemetry` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Approved feature specification in [spec.md](spec.md)

## Summary

Implement a Linux GPS telemetry client and PTY hardware double. The client opens a 9600 8N1
serial port through `pyserial`, processes framed control commands, transitions through the defined
states, validates checksummed `$GPGGA` input in `SCIENCE`, and appends accepted records to CSV.
The simulator creates the PTY pair, publishes its slave path, and emits deterministic NMEA input
every second.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pyserial`; standard library `csv`, `enum`, `pty`, `time`, `unittest`,
and `subprocess`

**Storage**: Local append-only `telemetry.csv`; physical dual-memory capacity is deployment-only

**Testing**: `unittest` unit and Linux PTY integration tests

**Target Platform**: Linux

**Project Type**: Command-line telemetry client and hardware simulator

**Performance Goals**: Emit one hardcoded `$GPGGA` sentence each second; detect an absent or
incomplete serial packet at 500 ms; preserve every accepted telemetry record

**Constraints**: UART 9600 8N1; little-endian multi-byte values; LSB-first bit order; framed XOR
commands; mandatory NMEA checksum; no physical-memory emulation; maximum ten physical
mate/de-mate cycles during hardware integration

**Scale/Scope**: One serial input, one PTY double, one CSV output, and the `INIT`, `STANDBY`,
`SCIENCE`, and `ERROR` state machine

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: Python 3.11+, explicit hardware interfaces, deterministic state transitions, and focused
  automated tests are planned (Constitution I).
- PASS: UART, byte/bit ordering, command framing, and XOR verification are represented in the
  serial contract and unit tests (Constitution II).
- PASS: The 500 ms `SyncError` behavior and ordered five-step recovery are explicit in the state
  design and integration tests (Constitution III).
- PASS: Only checksummed, complete `$GPGGA` data can reach CSV storage; the PTY produces one
  record per second (Constitution IV).
- PASS: Each work item will cite the ICD requirement it verifies; PTY-loss testing is required
  (Constitution V).

**Post-design re-check**: PASS. The design introduces no exception to the constitution.

## Project Structure

### Documentation (this feature)

```text
specs/001-gps-telemetry/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
gps_client.py             # Serial client, command parser, state machine, NMEA parser, CSV writer
gps_double.py             # PTY hardware double and deterministic NMEA stream
test_parser.py            # Unit tests for NMEA and command-frame validation
test_client.py            # Unit tests for state transitions, timeout, and recovery ordering
test_integration.py       # PTY client/simulator integration and PTY-loss tests
requirements.txt          # Runtime dependency declaration
GPS System Requirements and ICD.md
```

**Structure Decision**: Keep the small command-line system flat at the repository root. This
matches its two executable entry points and lets `unittest discover` find focused test files
without an unnecessary package layer.

## Complexity Tracking

No constitution exceptions require justification.
