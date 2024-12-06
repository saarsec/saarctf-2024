import traceback
from concurrent.futures import ThreadPoolExecutor

from pyipp.enums import IppJobState

from db.models import Printer, Job
from db.repository import DbRepository
from printer.backends import PrinterBackend


class JobQueue:
    def __init__(self, repo: DbRepository, printer_model: Printer, backend: PrinterBackend,
                 pool: ThreadPoolExecutor) -> None:
        self.repo = repo
        self.model = printer_model
        self.backend = backend
        self.pool = pool
        self.repo.jobs.abort_pending(printer_model.id)
        self.jobs = self.repo.jobs.by_many('printer_id', printer_model.id)
        self.processing_jobs: int = 0

    def add_job(self, job: Job) -> int:
        self.jobs.append(job)
        job.printer = self.model
        self.repo.jobs.store(job)
        if job.document is not None:
            self._schedule_job(job)
        return job.id

    def add_document_to_job(self, job: Job, doc: bytes) -> None:
        job.set_document(doc)
        self._schedule_job(job)

    def _schedule_job(self, job: Job) -> None:
        self.pool.submit(self._process_job, job)
        self.processing_jobs += 1

    def cancel(self, job: Job) -> None:
        if job.state in (IppJobState.PENDING, IppJobState.STOPPED, IppJobState.HELD):
            job.state = IppJobState.CANCELED
            self.repo.jobs.update_state(job)

    def _process_job(self, job: Job) -> None:
        if job.state == IppJobState.CANCELED:
            return
        job.state = IppJobState.PROCESSING
        self.repo.jobs.update_state(job)
        try:
            self.backend.print_job(job)
        except:
            traceback.print_exc()
            job.state = IppJobState.ABORTED
            self.repo.jobs.update_state(job)
        else:
            job.state = IppJobState.COMPLETED
            self.repo.jobs.update_state(job)
        finally:
            self.processing_jobs -= 1

    def by_id(self, job_id: int) -> Job | None:
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def num_in_queue(self) -> int:
        n = 0
        for job in self.jobs:
            if job.state in (IppJobState.PENDING, IppJobState.STOPPED, IppJobState.PROCESSING):
                n += 1
        return n
