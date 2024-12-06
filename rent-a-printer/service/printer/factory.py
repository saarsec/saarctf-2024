from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from db.repository import DbRepository
from printer import printers
from printer.backends import FilePrinterBackend
from printer.job_queue import JobQueue


class PrinterFactory:
    def __init__(self, data_dir: Path, repo: DbRepository, pool: ThreadPoolExecutor) -> None:
        self.repo = repo
        self.data_dir = data_dir
        self.pool = pool
        self._printers: dict[str, printers.Printer] = {}

    def get(self, name: str) -> printers.Printer:
        if name not in self._printers:
            self._load(name)
        return self._printers[name]

    def _load(self, name: str) -> None:
        model = self.repo.printers.by_name(name)
        if not model:
            raise KeyError(name)
        queue = JobQueue(self.repo, model, FilePrinterBackend(self.data_dir / model.user.name), self.pool)
        self._printers[name] = printers.Printer(model.name, queue)