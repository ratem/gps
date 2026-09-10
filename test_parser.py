import unittest

from gps_client import Command, CommandFrame, parse_gpgga


VALID_GPGGA = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"


class CommandFrameTests(unittest.TestCase):
    def test_round_trip_science_start_frame(self) -> None:
        frame = CommandFrame(Command.SCIENCE_START).encode()

        decoded = CommandFrame.decode(frame)

        self.assertEqual(decoded.command, Command.SCIENCE_START)
        self.assertEqual(decoded.data, b"")

    def test_rejects_bad_xor_and_unknown_command(self) -> None:
        with self.assertRaises(ValueError):
            CommandFrame.decode(b"\x7e\x01\x00\x00")
        with self.assertRaises(ValueError):
            CommandFrame.decode(b"\x7e\x7f\x00\x7f")

    def test_preserves_little_endian_multibyte_command_data(self) -> None:
        frame = CommandFrame(Command.SCIENCE_START, data=b"\x34\x12").encode()

        self.assertEqual(frame[3:5], b"\x34\x12")
        self.assertEqual(CommandFrame.decode(frame).data, b"\x34\x12")


class GpggaParserTests(unittest.TestCase):
    def test_extracts_required_fields_from_valid_sentence(self) -> None:
        record = parse_gpgga(VALID_GPGGA)

        self.assertEqual(record.utc_timestamp, "123519")
        self.assertEqual(record.latitude, "4807.038")
        self.assertEqual(record.longitude, "01131.000")

    def test_rejects_bad_checksum_missing_required_fields_and_other_types(self) -> None:
        invalid_sentences = (
            VALID_GPGGA.replace("*47", "*00"),
            VALID_GPGGA.replace("4807.038", ""),
            VALID_GPGGA.replace("$GPGGA", "$GPRMC"),
            VALID_GPGGA.rsplit("*", 1)[0],
        )

        for sentence in invalid_sentences:
            with self.subTest(sentence=sentence), self.assertRaises(ValueError):
                parse_gpgga(sentence)


if __name__ == "__main__":
    unittest.main()