import os
import pty
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

from gps_client import Command, CommandFrame, GpsClient, OperationalState, SyncError
from gps_double import read_recovery_frames


PROJECT_ROOT = Path(__file__).parent


class GpsIntegrationTests(unittest.TestCase):
    def test_live_pty_timeout_is_within_required_deadline(self) -> None:
        master_fd, slave_fd = pty.openpty()
        client = GpsClient(os.ttyname(slave_fd))
        client.initialize()
        client.state = OperationalState.SCIENCE
        try:
            started = time.monotonic()
            with self.assertRaises(SyncError):
                client.process_once()
            elapsed = time.monotonic() - started
        finally:
            client.close()
            os.close(master_fd)
            os.close(slave_fd)

        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLessEqual(elapsed, 0.55)

    def test_master_observes_client_recovery_frames(self) -> None:
        master_fd, slave_fd = pty.openpty()
        client = GpsClient(os.ttyname(slave_fd))
        client.initialize()
        client.state = OperationalState.SCIENCE
        try:
            client.recover()
            frames = read_recovery_frames(master_fd, timeout_seconds=0.2)
        finally:
            client.close()
            os.close(master_fd)
            os.close(slave_fd)

        self.assertEqual([frame.command for frame in frames], [Command.SU_R_SDP, Command.SU_R_HK])

    def test_ptys_stream_commands_and_gps_then_handle_loss(self) -> None:
        simulator = subprocess.Popen(
            [sys.executable, "gps_double.py"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
        try:
            assert simulator.stdout is not None
            slave_path = simulator.stdout.readline().strip()
            self.assertTrue(slave_path.startswith("/dev/pts/"))
            client = GpsClient(slave_path, PROJECT_ROOT / "telemetry.csv")
            client.initialize()
            nmea_times = []
            record = None
            for _ in range(20):
                record = client.process_once()
                if record is not None:
                    nmea_times.append(time.monotonic())
                    if len(nmea_times) == 3:
                        break
            self.assertIsNotNone(record)
            self.assertEqual(len(nmea_times), 3)
            for earlier, later in zip(nmea_times, nmea_times[1:]):
                self.assertGreaterEqual(later - earlier, 0.95)
                self.assertLessEqual(later - earlier, 1.10)
            os.killpg(os.getpgid(simulator.pid), signal.SIGTERM)
            simulator.wait(timeout=2)
            with self.assertRaises(SyncError):
                client.process_once()
            client.close()
        finally:
            if simulator.poll() is None:
                os.killpg(os.getpgid(simulator.pid), signal.SIGTERM)
                simulator.wait(timeout=2)
            if simulator.stdout is not None:
                simulator.stdout.close()


if __name__ == "__main__":
    unittest.main()