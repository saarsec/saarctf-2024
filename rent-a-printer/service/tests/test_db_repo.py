import unittest
from pathlib import Path

from db.models import User, Printer, Job
from db.repository import DbRepository


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = DbRepository(Path(':memory:'))

    def test_store_user(self) -> None:
        user = User(0, 'Test-User', 'abc')
        self.repo.users.store(user)
        self.assertNotEqual(user.id, 0)

        uid = user.id
        self.repo.users.store(user)
        self.assertEqual(user.id, uid)

        user2 = self.repo.users.by_id(uid)
        self.assertEqual(user, user2)

    def test_store_printer(self) -> None:
        user = User(0, 'Test-User', 'abc')
        self.repo.users.store(user)

        printer = Printer(0, 'Test-Printer', user, ['a', 'b', 'c'], ['d'])
        self.repo.printers.store(printer)
        self.assertNotEqual(printer.id, 0)

        pid = printer.id
        self.repo.printers.store(printer)
        self.assertEqual(printer.id, pid)

        printer2 = self.repo.printers.by_id(pid)
        self.assertEqual(printer, printer2)

    def test_store_printer_empty(self) -> None:
        user = User(0, 'Test-User', 'abc')
        self.repo.users.store(user)

        printer = Printer(0, 'Test-Printer', user, [], [])
        self.repo.printers.store(printer)
        printer2 = self.repo.printers.by_id(printer.id)
        self.assertEqual(printer, printer2)

    def test_store_job(self) -> None:
        user = User(0, 'Test-User', 'abc')
        self.repo.users.store(user)
        printer = Printer(0, 'Test-Printer', user, [], [])
        self.repo.printers.store(printer)

        job = Job(0, printer, 'Testjob', 'application/pdf', attributes={'a': 'b', 'c': 1, 'd': False, 'e': [1, 2, 3]})
        self.repo.jobs.store(job)
        self.assertNotEqual(job.id, 0)

        jid = job.id
        self.repo.jobs.store(job)
        self.assertEqual(job.id, jid)

        job2 = self.repo.jobs.by_id(jid)
        self.assertEqual(job, job2)


if __name__ == '__main__':
    unittest.main()
