# Data Model: GPS Telemetry Client and PTY Simulator

## Operational State

| Value | Entry condition | Exit condition | ICD source |
|---|---|---|---|
| `INIT` | Client creation | Successful serial initialization | GPS-SM-0010 |
| `STANDBY` | Successful initialization | `SCIENCE_START` (`0x01`) | GPS-SM-0020 |
| `SCIENCE` | Valid start command | `SyncError` | GPS-SM-0030 |
| `ERROR` | `SyncError` in `SCIENCE` | Recovery completion and shutdown | GPS-SM-0040 |

## Command Frame

| Field | Size | Rule |
|---|---:|---|
| Start byte | 1 byte | Always `0x7E` |
| Command ID | 1 byte | `0x01`, `0x02`, or `0x03` |
| Length | 1 byte | Number of following data bytes |
| Data | Variable | Exactly the declared length; optional |
| XOR | 1 byte | XOR of command ID, length, and data |

## NMEA Sentence and Telemetry Record

| Item | Required attributes |
|---|---|
| NMEA sentence | `$GPGGA`, UTC timestamp, latitude, longitude, valid `*HH` XOR checksum |
| Telemetry record | UTC timestamp, latitude, longitude, persisted timestamp |

Telemetry records are append-only and are created only for accepted NMEA sentences in `SCIENCE`.

## Recovery Event

Recovery actions are ordered: abort current operations, send `SU_R_SDP` (`0x02`), send
`SU_R_HK` (`0x03`), produce `OBC_SU_HK`, then shut down the unit or stream.