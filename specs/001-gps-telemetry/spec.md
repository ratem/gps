# Feature Specification: GPS Telemetry Client and PTY Simulator

**Feature Branch**: `001-gps-telemetry`

**Created**: 2026-09-10

**Status**: Draft

**Input**: Requirements from `GPS System Requirements and ICD.md`

## Clarifications

### Session 2026-09-10

- Q: Must every `$GPGGA` sentence include and pass the standard NMEA XOR checksum before it can be logged? → A: Every accepted `$GPGGA` sentence requires a valid `*HH` NMEA XOR checksum; missing or mismatched checksums are rejected.
- Q: Which one-byte `CMD_ID` starts the transition from `STANDBY` to `SCIENCE`? → A: `0x01` is the `SCIENCE_START` command.
- Q: Is the dual-memory, 10 MB reservation requirement limited to physical deployment hardware? → A: Yes; it is documented for deployment verification only and is not modeled by the client or simulator.
- Q: Which `CMD_ID` values request `SU_R_SDP` and `SU_R_HK` during error recovery? → A: `0x02` requests `SU_R_SDP`; `0x03` requests `SU_R_HK`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record GPS Telemetry (Priority: P1)

As a fleet manager, I need the system to continuously acquire valid GPS coordinates and
timestamps from the vehicle interface so that location data is retained in `telemetry.csv`.

**Why this priority**: Continuous, trustworthy location logging is the system's primary purpose.

**Independent Test**: Supply valid `$GPGGA` input while the system is in `SCIENCE` and confirm
that each accepted record appends latitude, longitude, and UTC timestamp to `telemetry.csv`.

**Acceptance Scenarios**:

1. **Given** an active serial connection and the `SCIENCE` state, **When** a valid `$GPGGA`
   sentence arrives, **Then** its latitude, longitude, and UTC timestamp are appended to
   `telemetry.csv`.
2. **Given** an active serial connection in `STANDBY`, **When** valid `$GPGGA` input arrives,
   **Then** no telemetry record is written until a valid command trigger enters `SCIENCE`.

---

### User Story 2 - Operate Deterministically (Priority: P1)

As an operator, I need predictable initialization, command-controlled acquisition, and timeout
handling so that the system cannot silently remain blocked after a hardware or simulation fault.

**Why this priority**: Deterministic control and fault containment are mandatory for the system's
safety and reliability requirements.

**Independent Test**: Initialize the system, issue the defined command trigger, then withhold an
incoming packet for 500 ms and observe the required state transitions and error recovery sequence.

**Acceptance Scenarios**:

1. **Given** a successfully initialized UART or PTY connection, **When** initialization completes,
   **Then** the state changes from `INIT` to `STANDBY` automatically.
2. **Given** `STANDBY`, **When** a valid `SCIENCE_START` command with `CMD_ID` `0x01` is received,
  **Then** the state changes to `SCIENCE` and acquisition becomes active.
3. **Given** `SCIENCE`, **When** a packet remains incomplete or the receive buffer is empty for
   500 ms, **Then** the system raises `SyncError`, enters `ERROR`, and performs the required
   recovery procedure in order.

---

### User Story 3 - Validate Data Before Storage (Priority: P1)

As a fleet manager, I need malformed or corrupted GPS input rejected so that archived telemetry
contains only trustworthy coordinate records.

**Why this priority**: Data integrity is necessary for every later analysis of recorded locations.

**Independent Test**: Provide valid, malformed, corrupt, incomplete, and non-`$GPGGA` input and
confirm that only input meeting the documented validation rule can create a telemetry record.

**Acceptance Scenarios**:

1. **Given** a `$GPGGA` sentence in `SCIENCE` with required fields and a valid `*HH` NMEA XOR
  checksum, **When** it is received, **Then** the system accepts it for logging.
2. **Given** malformed, corrupt, incomplete, or non-`$GPGGA` input, **When** it is received,
   **Then** the system does not append a telemetry record.

---

### User Story 4 - Simulate Flight Hardware (Priority: P2)

As a developer, I need a Linux PTY hardware double that behaves as the serial interface so that
the client can be verified without physical GPS hardware or changes to core client behavior.

**Why this priority**: The simulator enables reproducible integration testing and hardware-agnostic
client behavior.

**Independent Test**: Start the simulator, obtain its published slave-device path, attach a serial
client using the required UART settings, and observe hardcoded `$GPGGA` input every second.

**Acceptance Scenarios**:

1. **Given** the simulator starts on Linux, **When** its PTY pair is created, **Then** it publishes
   the slave-device path for a client to use as a serial port.
2. **Given** a connected client, **When** the simulator is running, **Then** it emits hardcoded
   `$GPGGA` sentences at one-second intervals.

### Edge Cases

- A serial packet is incomplete at the 500 ms deadline; the system raises `SyncError` and executes
  the complete `ERROR` recovery sequence.
- The PTY stream ends unexpectedly during `SCIENCE`; the system does not block or append a record
  after the loss.
- A `$GPGGA` sentence has missing latitude, longitude, or UTC timestamp fields; the system rejects
  it without writing telemetry.
- A command frame has an incorrect start byte, declared length, or XOR value; the system rejects it
  without changing state.
- The simulator is stopped during integration verification; the client reaches its defined error
  behavior without a process latch-up.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST acquire GPS telemetry from standard `$GPGGA` NMEA ASCII sentences
  and persist accepted latitude, longitude, and UTC timestamp records in `telemetry.csv`
  (Req: GPS-SW-0025).
- **FR-002**: The client MUST use a UART interface configured for 9600 baud, 8 data bits, no
  parity, one start bit, and one stop bit (Req: GPS-E-0210).
- **FR-003**: The system MUST use little-endian ordering for every multi-byte sequence and
  LSB-first bit transmission for every byte (Reqs: GPS-SW-0015, GPS-SW-0016).
- **FR-004**: The system MUST detect an empty receive buffer or an incomplete incoming serial
  packet after 500 ms, raise `SyncError`, and prevent indefinite blocking (Req: GPS-SW-0270).
- **FR-005**: The system MUST implement the `INIT`, `STANDBY`, `SCIENCE`, and `ERROR` states.
  Successful initialization MUST transition from `INIT` to `STANDBY`; only a valid command trigger
  may transition from `STANDBY` to `SCIENCE`; and a `SyncError` in `SCIENCE` MUST enter `ERROR`
  (Reqs: GPS-SM-0010, GPS-SM-0020, GPS-SM-0030, GPS-SM-0040).
- **FR-006**: Upon an error or timeout, the system MUST perform this ordered procedure: abort
  current operations; send `SU_R_SDP` using `CMD_ID` `0x02`; send `SU_R_HK` using `CMD_ID`
  `0x03`; produce `OBC_SU_HK` even without a hardware response; then turn off the unit or
  simulation stream (Req: GPS-SW-0140).
- **FR-007**: Every command MUST use a frame consisting of start byte `0x7E`, one-byte `CMD_ID`,
  one-byte `LEN`, optional `DATA`, and one-byte XOR calculated over `CMD_ID`, `LEN`, and `DATA`
  (Req: GPS-SW-0170).
- **FR-008**: The system MUST reject `$GPGGA` input that fails its documented NMEA integrity and
  field-validation rules; rejected input MUST NOT create a telemetry record (Req: GPS-SW-0025).
- **FR-009**: The simulator MUST create a Linux PTY master/slave pair, publish the slave path, and
  send hardcoded `$GPGGA` sentences at one-second intervals (Req: GPS-E-0010).
- **FR-010**: The client MUST use the PTY slave as a drop-in serial port and retain the same core
  behavior required for physical serial hardware (Req: GPS-E-0010).
- **FR-011**: The deployment design MUST provide two independent mass-memory units, each with at
  least 10 MB reserved for science and housekeeping logs (Req: GPS-SW-0040).
- **FR-012**: Physical connector integration procedures MUST limit flight-grade connector
  mate/de-mate operations to ten cycles (Req: GPS-E-0020).
- **FR-013**: Verification MUST include a read-write-verify loop, unit coverage for parser and
  command behavior, integration coverage using the PTY double, and adversarial PTY-loss testing
  that demonstrates no system latch-up (ICD section 6; Constitution V).
- **FR-014**: Each implementation, test, and operational procedure MUST identify the ICD
  requirement or section it verifies (Constitution V).
- **FR-015**: Every accepted `$GPGGA` sentence MUST include a two-hex-digit `*HH` checksum and
  pass standard NMEA XOR validation over the characters between `$` and `*`. The system MUST reject
  a sentence with a missing, malformed, or mismatched checksum and MUST NOT write a telemetry
  record for it.
- **FR-016**: The system MUST recognize valid command identifiers, including the command that
  requests transition from `STANDBY` to `SCIENCE`. `CMD_ID` `0x01` MUST mean `SCIENCE_START`,
  `0x02` MUST mean `SU_R_SDP`, and `0x03` MUST mean `SU_R_HK`. The client MUST reject any other
  command identifier without changing state until that identifier is defined by the ICD.
- **FR-017**: The two independent mass-memory units and their 10 MB reservations are a physical
  deployment requirement. Deployment verification MUST document compliance with Req: GPS-SW-0040;
  the GPS client and PTY simulator MUST NOT model, detect, or emulate the memory units.

### Key Entities *(include if feature involves data)*

- **Telemetry Record**: An accepted GPS observation containing UTC timestamp, latitude, longitude,
  and the time it was persisted.
- **NMEA Sentence**: An incoming ASCII sentence classified by message type, integrity status, and
  required-field availability.
- **Command Frame**: A control message with start byte, command identifier, declared data length,
  optional data, and integrity XOR.
- **Operational State**: One of `INIT`, `STANDBY`, `SCIENCE`, or `ERROR`, with defined allowed
  transitions.
- **Recovery Event**: The ordered response initiated by an error or `SyncError`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With valid `$GPGGA` input in `SCIENCE`, 100% of input records accepted under the
  documented validation rule are appended with latitude, longitude, and UTC timestamp.
- **SC-002**: With invalid, corrupt, incomplete, or non-`$GPGGA` input, 0 telemetry records are
  appended for the rejected input.
- **SC-003**: In a controlled timeout test, the system detects no input or an incomplete packet and
  raises `SyncError` within 500 ms plus the test harness measurement tolerance.
- **SC-004**: Every tested timeout transitions to `ERROR` and records all five ordered recovery
  actions before the unit or simulation stream is turned off.
- **SC-005**: The simulator publishes a usable PTY slave path and emits a `$GPGGA` sentence once
  per second for at least three consecutive intervals in an integration test.
- **SC-006**: Automated verification demonstrates successful client logging with the PTY double
  and no client latch-up after intentional PTY loss.
- **SC-007**: Every functional requirement has at least one identified verification artifact before
  implementation is accepted.

## Assumptions

- The initial deliverable runs on Linux, where PTY master/slave pairs are available.
- The `telemetry.csv` location, column order, header policy, file-rotation policy, and retention
  policy are not specified by the ICD; these must be selected during planning without weakening the
  required stored fields.
- Standard NMEA syntax is available to the source hardware, including a two-hex-digit checksum.
- The initial command set defines `CMD_ID` `0x01` (`SCIENCE_START`), `0x02` (`SU_R_SDP`), and
  `0x03` (`SU_R_HK`); future command identifiers require an ICD amendment before implementation.
- The deployment hardware owns physical connector-cycle control and memory redundancy; those
  physical requirements are documented for deployment verification, not implemented in this feature.