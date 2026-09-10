# Tasks: GPS Telemetry Client and PTY Simulator

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [serial-protocol.md](contracts/serial-protocol.md), and
[quickstart.md](quickstart.md)

**Tests**: Required. Write each test before its corresponding implementation and confirm it fails.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the Python runtime, dependency declaration, and test entry point.

- [X] T001 Create `requirements.txt` with the `pyserial` runtime dependency per Constitution I.
- [X] T002 Create the `unittest` discovery command and test-file layout in `test_parser.py`,
  `test_client.py`, and `test_integration.py` per FR-013.
- [X] T003 [P] Document the physical deployment verification for dual memory capacity and connector
  mate/de-mate limits in `specs/001-gps-telemetry/quickstart.md` per FR-011 and FR-012.

## Phase 2: Foundational Protocol and State Components

**Purpose**: Build the shared, testable rules that block every user story.

- [X] T004 Write failing command-frame tests in `test_parser.py` for `0x7E | CMD_ID | LEN | DATA |
  XOR`, length mismatch, invalid XOR, and unknown command rejection per FR-007 and FR-016.
- [X] T005 Write failing state and recovery tests in `test_client.py` for `INIT` to `STANDBY`,
  `SCIENCE_START` (`0x01`), `SyncError`, and the ordered recovery actions per FR-004 through
  FR-006.
- [X] T006 Implement command-frame encoding and validation in `gps_client.py`, including `0x01`
  (`SCIENCE_START`), `0x02` (`SU_R_SDP`), and `0x03` (`SU_R_HK`) per FR-007 and FR-016.
- [X] T007 Implement the explicit operational-state model and legal transitions in `gps_client.py`
  per FR-005.
- [X] T008 Implement `SyncError` handling and the ordered abort, `SU_R_SDP`, `SU_R_HK`,
  `OBC_SU_HK`, and shutdown recovery behavior in `gps_client.py` per FR-004 and FR-006.

**Checkpoint**: Command framing, state transitions, and recovery tests pass before user-story work.

## Phase 3: User Story 1 - Record GPS Telemetry (Priority: P1)

**Goal**: Persist accepted GPS observations only while acquisition is active.

**Independent Test**: Supply an accepted sentence in `SCIENCE` and verify one CSV record with UTC,
latitude, and longitude; verify `STANDBY` does not append a record.

- [X] T009 [US1] Write failing CSV logging tests in `test_client.py` for a validated telemetry
  record in `SCIENCE` and no writes in `STANDBY` per FR-001 and FR-005.
- [X] T010 [US1] Implement append-only validated telemetry-record writing with UTC timestamp,
  latitude, longitude, and persisted timestamp in `gps_client.py` per FR-001.
- [X] T011 [US1] Implement state-gated CSV writing for validated telemetry records in
  `gps_client.py` per FR-001 and FR-005.

## Phase 4: User Story 2 - Operate Deterministically (Priority: P1)

**Goal**: Configure the serial port and execute control and recovery behavior deterministically.

**Independent Test**: Use a controllable serial double to verify 9600 8N1, a 500 ms timeout,
`SCIENCE_START`, and ordered recovery on absent or incomplete input.

- [X] T012 [US2] Write failing serial-configuration and timeout tests in `test_client.py` for 9600
  8N1 and the 500 ms `SyncError` deadline per FR-002 and FR-004.
- [X] T013 [US2] Implement serial-port initialization with 9600 8N1 and a 500 ms timeout in
  `gps_client.py` per FR-002 and FR-004.
- [X] T014 [US2] Implement the client control loop that processes commands, enters `SCIENCE` only
  for `0x01`, and invokes recovery on timeout in `gps_client.py` per FR-005 and FR-006.

## Phase 5: User Story 3 - Validate Data Before Storage (Priority: P1)

**Goal**: Reject invalid GPS input before it reaches storage.

**Independent Test**: Parse valid checksummed `$GPGGA`, then verify malformed, missing-field,
missing-checksum, mismatched-checksum, and non-`$GPGGA` input produce no telemetry record.

- [X] T015 [US3] Write failing NMEA parser tests in `test_parser.py` for `$GPGGA` field extraction,
  valid `*HH` XOR, and each required rejection case per FR-008 and FR-015.
- [X] T016 [US3] Implement `$GPGGA` checksum and required-field validation in `gps_client.py` per
  FR-008 and FR-015.
- [X] T017 [US3] Implement NMEA field extraction and pass accepted records to the state-gated CSV
  writer in `gps_client.py` per FR-001, FR-008, and FR-015.

## Phase 6: User Story 4 - Simulate Flight Hardware (Priority: P2)

**Goal**: Provide a real Linux serial endpoint for reproducible end-to-end verification.

**Independent Test**: Start the simulator, obtain the slave path, attach the client, and observe
three one-second NMEA intervals plus clean handling of an intentional simulator stop.

- [X] T018 [US4] Write failing PTY integration tests in `test_integration.py` for master-to-slave
  commands and NMEA, slave-to-master recovery frames, published paths, one-second output, client
  logging, and PTY loss per FR-009, FR-010, and FR-013.
- [X] T019 [US4] Implement PTY master/slave creation and slave-path publication in `gps_double.py`
  per FR-009.
- [X] T020 [US4] Implement deterministic one-second, checksummed `$GPGGA` streaming and controlled
  shutdown in `gps_double.py` per FR-009 and FR-015.
- [X] T021 [US4] Complete end-to-end client/simulator and PTY-loss verification in
  `test_integration.py` per FR-010 and FR-013.

## Phase 7: Polish and Cross-Cutting Verification

- [X] T022 Verify little-endian multi-byte encoding and serial configuration in `test_parser.py`,
  then record wire-level LSB-first UART integration evidence in
  `contracts/serial-protocol.md` per FR-003.
- [X] T023 Run the complete `unittest` suite and the manual quickstart verification in
  `specs/001-gps-telemetry/quickstart.md` per FR-013.
- [X] T024 Verify each completed task against the ICD traceability table in
  `specs/001-gps-telemetry/plan.md` per FR-014.

## Dependencies and Execution Order

`T001` through `T003` establish the project. `T004` and `T005` must precede the shared
implementation tasks `T006` through `T008`. User-story phases proceed in P1 order; each test task
precedes its matching implementation task. `T018` may start after `T001`, but `T021` depends on the
client work in Phases 3 through 5 and simulator tasks `T019` and `T020`. Phase 7 follows all prior
phases.

## Parallel Opportunities

- `T003` may run with `T001` and `T002`.
- `T004` and `T005` may run in parallel because they affect separate test files.
- After Phase 2, the test-first slices for telemetry, serial control, NMEA validation, and PTY
  simulation may be assigned independently, while changes to `gps_client.py` remain sequential.

## Implementation Strategy

The MVP is Phase 2 plus User Story 1, with a small serial double sufficient to prove state-gated
CSV logging. Add deterministic serial control and data validation next, then introduce the real PTY
double for integration and fault verification. Acceptance requires all tests and the quickstart
workflow to pass with ICD traceability recorded.