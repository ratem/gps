import os
import signal
import subprocess
import sys
import unittest
from pathlib import Path

from gps_client import GpsClient, SyncError


PROJECT_ROOT = Path(__file__).parent


class GpsIntegrationTests(unittest.TestCase):
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
            record = None
            for _ in range(4):
                record = client.process_once()
                if record is not None:
                    break
            self.assertIsNotNone(record)
            os.killpg(os.getpgid(simulator.pid), signal.SIGTERM)
            simulator.wait(timeout=2)
            for _ in range(4):
                with self.assertRaises(SyncError):
                    client.process_once()
                break
            client.close()
        finally:
            if simulator.poll() is None:
                os.killpg(os.getpgid(simulator.pid), signal.SIGTERM)
            if simulator.stdout is not None:
                simulator.stdout.close()


if __name__ == "__main__":
    unittest.main()