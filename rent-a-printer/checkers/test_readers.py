import unittest
from pathlib import Path

from checkers.interface import qr_to_text


class TestReaders(unittest.TestCase):
    def test_qr_reader(self) -> None:
        pdf = Path('demo-qr.pdf').read_bytes()
        result = qr_to_text(pdf)
        print(result)
        self.assertIn('SAAR{', result)

    def test_qr_reader_2(self) -> None:
        pdf = Path('job-00001.pdf').read_bytes()
        result = qr_to_text(pdf)
        print(result)
        self.assertIn('SAAR{', result)

    def test_qr_reader_3(self) -> None:
        pdf = Path('sample_docs/error1.pdf').read_bytes()
        result = qr_to_text(pdf)
        print(result)
        self.assertIn('SAAR{', result)
