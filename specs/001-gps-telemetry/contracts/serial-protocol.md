# Serial Protocol Contract

## UART Configuration

Every serial endpoint uses 9600 baud, eight data bits, no parity, one start bit, and one stop bit
(Req: GPS-E-0210). Multi-byte values are little-endian and bytes are LSB-first where transport
configuration exposes bit order (Reqs: GPS-SW-0015, GPS-SW-0016). Unit tests verify byte
encoding and serial configuration; selected UART hardware or integration evidence verifies
wire-level LSB-first transmission.

## Command Frame

```text
0x7E | CMD_ID | LEN | DATA[LEN] | XOR
```

`XOR` is the bitwise XOR of `CMD_ID`, `LEN`, and each data byte. Invalid start byte, length, XOR,
or command ID causes rejection without a state change.

| CMD_ID | Name | Valid use |
|---:|---|---|
| `0x01` | `SCIENCE_START` | Transitions `STANDBY` to `SCIENCE` |
| `0x02` | `SU_R_SDP` | Recovery action two |
| `0x03` | `SU_R_HK` | Recovery action three |

## PTY Directionality and Recovery Event

During simulation, `gps_double.py` owns the PTY master. It writes `SCIENCE_START` frames and
checksummed `$GPGGA` input to the master for the client slave to read. The client writes recovery
frames `0x02` and `0x03` to the slave for the simulator master to observe. `OBC_SU_HK` is a
process-local recovery packet event emitted by the client after those two requests; tests observe
it through the client's recovery-event interface, not as an additional UART command.

## NMEA Input and Timeout

Only `$GPGGA` ASCII sentences with non-empty UTC, latitude, longitude, and valid `*HH` checksum
are accepted. Empty or incomplete input at 500 ms raises `SyncError`; the observed deadline must
be between 500 ms and 550 ms. During `SCIENCE`, that enters `ERROR` and starts recovery.