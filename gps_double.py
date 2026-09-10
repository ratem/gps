from __future__ import annotations

import os
import pty
import select
import sys
import time

from gps_client import Command, CommandFrame, xor_bytes


def gpgga_sentence() -> bytes:
    payload = "GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,"
    checksum = xor_bytes(payload.encode("ascii"))
    return f"${payload}*{checksum:02X}\r\n".encode("ascii")


def read_recovery_frames(master_fd: int, timeout_seconds: float) -> list[CommandFrame]:
    ready, _, _ = select.select([master_fd], [], [], timeout_seconds)
    if not ready:
        return []
    packet = os.read(master_fd, 1024)
    frames = []
    while packet:
        data_length = packet[2]
        frame_length = data_length + 4
        frames.append(CommandFrame.decode(packet[:frame_length]))
        packet = packet[frame_length:]
    return frames


def run_simulator() -> None:
    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)
    print(slave_path, flush=True)
    try:
        next_nmea_at = time.monotonic()
        while True:
            os.write(master_fd, CommandFrame(Command.SCIENCE_START).encode())
            if time.monotonic() >= next_nmea_at:
                os.write(master_fd, gpgga_sentence())
                next_nmea_at += 1
            time.sleep(0.25)
    finally:
        os.close(master_fd)
        os.close(slave_fd)


if __name__ == "__main__":
    try:
        run_simulator()
    except KeyboardInterrupt:
        sys.exit(0)