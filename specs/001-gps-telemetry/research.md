# Research: GPS Telemetry Client and PTY Simulator

## Serial and PTY Interfaces

- **Decision**: Use `pyserial.Serial` for the client and `pty.openpty()` for the simulator.
- **Rationale**: A PTY slave is a Linux serial device, so the same client path serves simulation
  and physical UART use without core-logic changes (Req: GPS-E-0010).
- **Alternative rejected**: In-memory streams do not exercise the operating-system serial path.

## State Management

- **Decision**: Use an explicit `Enum` for `INIT`, `STANDBY`, `SCIENCE`, and `ERROR` with a
  controller that validates every transition.
- **Rationale**: The transition graph and `SyncError` recovery remain independently testable
  (Reqs: GPS-SM-0010 through GPS-SM-0040).
- **Alternative rejected**: Boolean flags cannot clearly represent permitted transitions.

## Message Validation and Commands

- **Decision**: Accept only `$GPGGA` sentences with UTC, latitude, longitude, and a valid `*HH`
  NMEA XOR checksum. Support `0x01` (`SCIENCE_START`), `0x02` (`SU_R_SDP`), and `0x03`
  (`SU_R_HK`) framed commands.
- **Rationale**: The approved specification makes these integrity and recovery rules mandatory.
- **Alternative rejected**: Checksum-free NMEA and unframed commands violate the approved spec.

## Testing

- **Decision**: Use standard-library `unittest` for parser, command, state, and subprocess PTY
  integration tests.
- **Rationale**: It supports the required adversarial PTY-loss test without adding dependencies
  beyond the mandated `pyserial`.