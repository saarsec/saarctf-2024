import time
from abc import ABC, abstractmethod
from pathlib import Path

from db.models import Job


class PrinterBackend(ABC):
    @abstractmethod
    def print_job(self, job: Job) -> None:
        raise NotImplementedError


class FilePrinterBackend(PrinterBackend):
    def __init__(self, base: Path) -> None:
        self.base = base

    def print_job(self, job: Job) -> None:
        if job.document is None:
            raise ValueError

        ext = 'bin'
        if job.doctype == 'application/pdf':
            ext = 'pdf'
        elif job.doctype == 'application/postscript':
            ext = 'ps'

        number = 1
        f = self.base / f'job-{number:05d}.{ext}'
        while f.exists():
            number += 1
            f = self.base / f'job-{number:05d}.{ext}'
        f.write_bytes(job.document)
        print(f'Wrote {f}')
