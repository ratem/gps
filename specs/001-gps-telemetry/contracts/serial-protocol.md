# Serial Protocol Contract

## UART Configuration

Every serial endpoint uses 9600 baud, eight data bits, no parity, one start bit, and one stop bit
(Req: GPS-E-0210). Multi-byte values are little-endian and bytes are LSB-first where transport
configuration exposes bit order (Reqs: GPS-SW-0015, GPS-SW-0016).

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

## NMEA Input and Timeout

Only `$GPGGA` ASCII sentences with non-empty UTC, latitude, longitude, and valid `*HH` checksum
are accepted. Empty or incomplete input at 500 ms raises `SyncError`; during `SCIENCE`, that enters
`ERROR` and starts the ordered recovery event.