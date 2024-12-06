import random
import subprocess
import sys
import time
from pathlib import Path

from checkers.interface import PrinterServiceInterface, qr_to_text
from gamelib import Team

BASE = Path(__file__).absolute().parent.parent


class DemoDocBuilder:
    def __init__(self):
        self.interface = PrinterServiceInterface(1)
        self.team = Team(1, 'X', '127.0.0.1')

    def build_doc(self, flag):
        uploaded_doc = self.interface.generate_document('My flag: ' + flag)
        # Path('tmp1.pdf').write_bytes(uploaded_doc)
        qr_doc = self.to_qr(uploaded_doc)
        # Path('tmp2.pdf').write_bytes(qr_doc)
        return qr_doc

    def to_qr(self, doc: bytes) -> bytes:
        result = subprocess.run([sys.executable, 'filters/qrcodes.py', 'x', 'x', 'x', 'x', 'x'],
                                cwd=BASE / 'service', input=doc, stdout=subprocess.PIPE)
        assert result.returncode == 0
        return result.stdout

    def test_qr_reader(self, flag: str, prefix: str = ''):
        doc = self.build_doc(flag)
        t = time.monotonic()
        text = qr_to_text(doc)
        dt = time.monotonic() - t
        if not flag in text:
            print('ERROR', repr(flag), repr(text))
            Path('error.pdf').write_bytes(doc)
            assert False
        print(f'{prefix}[ok] {dt:.3f}  {flag}')

    def test_qr_reader_many(self, count: int = 100):
        start = random.randint(0, 1000000)
        for i in range(count):
            self.test_qr_reader(self.interface.get_flag(self.team, start + i), prefix=f'{i + 1:3d}/{count} ')
        print('[ok] mass test done')


def main():
    builder = DemoDocBuilder()
    # builder.test_qr_reader(builder.interface.get_flag(builder.team, 1))
    builder.test_qr_reader_many(1000)


if __name__ == '__main__':
    main()
