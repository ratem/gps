from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path
from typing import BinaryIO

import serial


SERIAL_TIMEOUT_SECONDS = 0.5


class SyncError(RuntimeError):
    """Raised when a serial packet does not arrive before the required deadline."""


class OperationalState(Enum):
    INIT = "INIT"
    STANDBY = "STANDBY"
    SCIENCE = "SCIENCE"
    ERROR = "ERROR"


class Command(IntEnum):
    SCIENCE_START = 0x01
    SU_R_SDP = 0x02
    SU_R_HK = 0x03


@dataclass(frozen=True)
class CommandFrame:
    command: Command
    data: bytes = b""

    def encode(self) -> bytes:
        if len(self.data) > 0xFF:
            raise ValueError("command data exceeds one-byte length")
        payload = bytes((int(self.command), len(self.data))) + self.data
        return b"\x7e" + payload + bytes((xor_bytes(payload),))

    @classmethod
    def decode(cls, packet: bytes) -> "CommandFrame":
        if len(packet) < 4 or packet[0] != 0x7E:
            raise ValueError("invalid command frame start or length")
        command_value, data_length = packet[1], packet[2]
        if len(packet) != data_length + 4:
            raise ValueError("command frame length mismatch")
        payload = packet[1:-1]
        if xor_bytes(payload) != packet[-1]:
            raise ValueError("command frame XOR mismatch")
        try:
            command = Command(command_value)
        except ValueError as error:
            raise ValueError("unknown command identifier") from error
        return cls(command=command, data=packet[3:-1])


@dataclass(frozen=True)
class TelemetryRecord:
    utc_timestamp: str
    latitude: str
    longitude: str


@dataclass(frozen=True)
class RecoveryEvent:
    actions: tuple[str, ...]


def xor_bytes(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def parse_gpgga(sentence: str) -> TelemetryRecord:
    if not sentence.startswith("$GPGGA,") or sentence.count("*") != 1:
        raise ValueError("expected checksummed $GPGGA sentence")
    payload, checksum_text = sentence[1:].split("*", 1)
    if len(checksum_text) != 2:
        raise ValueError("NMEA checksum must contain two hexadecimal digits")
    try:
        expected_checksum = int(checksum_text, 16)
    except ValueError as error:
        raise ValueError("invalid NMEA checksum") from error
    if xor_bytes(payload.encode("ascii")) != expected_checksum:
        raise ValueError("NMEA checksum mismatch")
    fields = payload.split(",")
    if len(fields) < 6 or not fields[1] or not fields[2] or not fields[4]:
        raise ValueError("$GPGGA sentence lacks UTC, latitude, or longitude")
    return TelemetryRecord(
        utc_timestamp=fields[1], latitude=fields[2], longitude=fields[4]
    )


class GpsClient:
    def __init__(self, port: str, telemetry_path: Path | str = "telemetry.csv") -> None:
        self.port = port
        self.telemetry_path = Path(telemetry_path)
        self.state = OperationalState.INIT
        self.serial_port: BinaryIO | serial.Serial | None = None
        self.recovery_events: list[RecoveryEvent] = []

    def initialize(self) -> None:
        self.serial_port = serial.Serial(
            self.port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=SERIAL_TIMEOUT_SECONDS,
        )
        self.state = OperationalState.STANDBY

    def handle_command(self, frame: CommandFrame) -> None:
        if frame.command is Command.SCIENCE_START:
            if self.state is OperationalState.STANDBY:
                self.state = OperationalState.SCIENCE
            return
        if frame.command not in (Command.SU_R_SDP, Command.SU_R_HK):
            raise ValueError("unsupported command")

    def process_once(self) -> TelemetryRecord | None:
        port = self._require_port()
        try:
            first_byte = port.read(1)
        except serial.SerialException as error:
            if self.state is OperationalState.SCIENCE:
                self.recover()
            raise SyncError("serial device disconnected") from error
        if not first_byte:
            if self.state is OperationalState.SCIENCE:
                self.recover()
                raise SyncError("serial input timed out")
            return None
        if first_byte == b"\x7e":
            self.handle_command(CommandFrame.decode(self._read_command_frame(first_byte)))
            return None
        line = port.readline()
        if not line.endswith(b"\n"):
            self._timeout()
        sentence = (first_byte + line).decode("ascii").strip()
        if self.state is not OperationalState.SCIENCE:
            return None
        record = parse_gpgga(sentence)
        self.write_telemetry(record)
        return record

    def write_telemetry(self, record: TelemetryRecord) -> None:
        if self.state is not OperationalState.SCIENCE:
            return
        new_file = not self.telemetry_path.exists() or self.telemetry_path.stat().st_size == 0
        with self.telemetry_path.open("a", newline="", encoding="ascii") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=("utc_timestamp", "latitude", "longitude", "persisted_at"),
            )
            if new_file:
                writer.writeheader()
            writer.writerow(
                {
                    "utc_timestamp": record.utc_timestamp,
                    "latitude": record.latitude,
                    "longitude": record.longitude,
                    "persisted_at": time.time(),
                }
            )

    def recover(self) -> RecoveryEvent:
        self.state = OperationalState.ERROR
        actions = ("ABORT", "SU_R_SDP", "SU_R_HK", "OBC_SU_HK", "TURN_OFF")
        port = self._require_port()
        event = RecoveryEvent(actions=actions)
        self.recovery_events.append(event)
        for command in (Command.SU_R_SDP, Command.SU_R_HK):
            try:
                port.write(CommandFrame(command).encode())
            except serial.SerialException:
                pass
        return event

    def close(self) -> None:
        if self.serial_port is not None:
            self.serial_port.close()

    def _read_command_frame(self, first_byte: bytes) -> bytes:
        port = self._require_port()
        header = port.read(2)
        if len(header) != 2:
            self._timeout()
        data_length = header[1]
        remainder = port.read(data_length + 1)
        if len(remainder) != data_length + 1:
            self._timeout()
        return first_byte + header + remainder

    def _timeout(self) -> None:
        if self.state is OperationalState.SCIENCE:
            self.recover()
        raise SyncError("serial packet incomplete")

    def _require_port(self) -> BinaryIO | serial.Serial:
        if self.serial_port is None:
            raise RuntimeError("client is not initialized")
        return self.serial_port


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 gps_client.py /dev/pts/N")
    client = GpsClient(sys.argv[1])
    client.initialize()
    try:
        while True:
            client.process_once()
    finally:
        client.close()


if __name__ == "__main__":
    main()