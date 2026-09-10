import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gps_client import (
    Command,
    CommandFrame,
    GpsClient,
    OperationalState,
    SyncError,
    TelemetryRecord,
)


VALID_GPGGA = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"


class FakeSerial:
    def __init__(self, incoming: bytes = b"") -> None:
        self.incoming = bytearray(incoming)
        self.written = bytearray()
        self.closed = False

    def read(self, size: int = 1) -> bytes:
        result = bytes(self.incoming[:size])
        del self.incoming[:size]
        return result

    def readline(self) -> bytes:
        newline = self.incoming.find(b"\n")
        size = len(self.incoming) if newline < 0 else newline + 1
        return self.read(size)

    def write(self, data: bytes) -> int:
        self.written.extend(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


class GpsClientTests(unittest.TestCase):
    def test_initialization_uses_required_uart_configuration(self) -> None:
        with patch("gps_client.serial.Serial") as serial_constructor:
            client = GpsClient("/dev/pts/1")
            client.initialize()

        self.assertEqual(client.state, OperationalState.STANDBY)
        self.assertEqual(serial_constructor.call_args.kwargs["baudrate"], 9600)
        self.assertEqual(serial_constructor.call_args.kwargs["timeout"], 0.5)

    def test_science_start_enables_csv_writing_only_in_science(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            telemetry_path = Path(directory) / "telemetry.csv"
            client = GpsClient("unused", telemetry_path)
            client.serial_port = FakeSerial()
            client.state = OperationalState.STANDBY
            record = TelemetryRecord("123519", "4807.038", "01131.000")

            client.write_telemetry(record)
            self.assertFalse(telemetry_path.exists())
            client.handle_command(CommandFrame(Command.SCIENCE_START))
            client.write_telemetry(record)

            with telemetry_path.open(newline="", encoding="ascii") as output:
                rows = list(csv.DictReader(output))
            self.assertEqual(rows[0]["utc_timestamp"], "123519")

    def test_timeout_enters_error_and_writes_ordered_recovery_requests(self) -> None:
        fake_port = FakeSerial()
        client = GpsClient("unused")
        client.serial_port = fake_port
        client.state = OperationalState.SCIENCE

        with self.assertRaises(SyncError):
            client.process_once()

        self.assertEqual(client.state, OperationalState.ERROR)
        self.assertEqual(
            client.recovery_events[0].actions,
            ("ABORT", "SU_R_SDP", "SU_R_HK", "OBC_SU_HK", "TURN_OFF"),
        )
        self.assertEqual(
            bytes(fake_port.written),
            CommandFrame(Command.SU_R_SDP).encode() + CommandFrame(Command.SU_R_HK).encode(),
        )

    def test_processes_science_command_then_valid_nmea(self) -> None:
        incoming = CommandFrame(Command.SCIENCE_START).encode() + VALID_GPGGA
        client = GpsClient("unused")
        client.serial_port = FakeSerial(incoming)
        client.state = OperationalState.STANDBY

        self.assertIsNone(client.process_once())
        record = client.process_once()

        self.assertEqual(client.state, OperationalState.SCIENCE)
        self.assertEqual(record.latitude, "4807.038")


if __name__ == "__main__":
    unittest.main()