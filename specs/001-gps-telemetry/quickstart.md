# Quickstart: GPS Telemetry Client and PTY Simulator

## Prerequisites

- Linux with Python 3.11 or later.
- `pyserial` installed from `requirements.txt`.

## Automated Verification

Run the complete suite from the repository root:

```bash
python3 -m unittest discover -p 'test_*.py'
```

Expected outcome: unit tests verify parser, command, state, timeout, and recovery behavior; PTY
integration verifies logging and intentional PTY loss without a blocked client process.

## Manual PTY Verification

Start the simulator in one terminal:

```bash
python3 gps_double.py
```

Use its printed `/dev/pts/N` path to start the client in another terminal:

```bash
python3 gps_client.py /dev/pts/N
```

Send a valid `SCIENCE_START` (`0x01`) command frame and confirm that `telemetry.csv` receives rows
only in `SCIENCE`. Stop the simulator and verify `SyncError`, ordered recovery, and client shutdown.

## Deployment Checks

Verify dual-memory capacity and connector mate/de-mate limits against the physical deployment; they
are not simulated by this feature.