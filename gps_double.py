from __future__ import annotations

import os
import pty
import sys
import time

from gps_client import Command, CommandFrame, xor_bytes


def gpgga_sentence() -> bytes:
    payload = "GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,"
    checksum = xor_bytes(payload.encode("ascii"))
    return f"${payload}*{checksum:02X}\r\n".encode("ascii")


def run_simulator() -> None:
    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)
    print(slave_path, flush=True)
    try:
        while True:
            os.write(master_fd, CommandFrame(Command.SCIENCE_START).encode())
            os.write(master_fd, gpgga_sentence())
            time.sleep(1)
    finally:
        os.close(master_fd)
        os.close(slave_fd)


if __name__ == "__main__":
    try:
        run_simulator()
    except KeyboardInterrupt:
        sys.exit(0)