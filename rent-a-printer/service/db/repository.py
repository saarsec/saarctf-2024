import json
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection, connect
from threading import Lock
from typing import TypeVar, Generic, Protocol

from pyipp.enums import IppJobState

from db.models import User, Printer, Job


class Model(Protocol):
    id: int
    name: str


T = TypeVar('T', bound=Model)


class Table(Generic[T]):
    init_stmts: list[str] = []
    tbl_name: str = ''
    joins: str = ''

    def __init__(self, db: Connection, lock: Lock) -> None:
        self.db = db
        self.lock = lock
        with lock:
            for stmt in self.init_stmts:
                self.db.execute(stmt)

    def by(self, field: str, value: int | str) -> T | None:
        with self.lock:
            result = self.db.execute(
                f'SELECT * FROM {self.tbl_name} {self.joins} WHERE {self.tbl_name}.{field} = ? LIMIT 1', (value,)
            ).fetchone()
            return self.row_to_model(result) if result else None

    def by_id(self, id: int) -> T | None:
        return self.by('id', id)

    def by_name(self, name: str) -> T | None:
        return self.by('name', name)

    def all(self) -> list[T]:
        result = []
        with self.lock:
            for row in self.db.execute(
                    f'SELECT * FROM {self.tbl_name} {self.joins} ORDER BY {self.tbl_name}.id').fetchall():
                result.append(self.row_to_model(row))
        return result

    def by_many(self, field: str, value: int | str) -> list[T]:
        result = []
        with self.lock:
            for row in self.db.execute(
                    f'SELECT * FROM {self.tbl_name} {self.joins} WHERE {self.tbl_name}.{field} = ? ORDER BY {self.tbl_name}.id',
                    (value,)
            ).fetchall():
                result.append(self.row_to_model(row))
        return result

    def store(self, obj: T) -> None:
        if obj.id is None or obj.id == 0:
            obj.id = self.insert(obj)
        else:
            self.update(obj)

    def insert(self, obj: T) -> int:
        fields, values = self._model_to_row(obj)
        with self.lock:
            cursor = self.db.cursor()
            try:
                fields_str = '"' + '","'.join(fields) + '"'
                params = ','.join('?' for _ in values)
                cursor.execute(f'INSERT INTO {self.tbl_name} ({fields_str}) VALUES ({params});', values)
                new_id = cursor.lastrowid
            finally:
                cursor.close()
            self.db.commit()
            if new_id is None:
                raise Exception('Could not insert')
            return new_id

    def update(self, obj: T) -> None:
        fields, values = self._model_to_row(obj)
        fields_str = ', '.join(f'"{f}" = ?' for f in fields)
        self._exec(f'UPDATE {self.tbl_name} SET {fields_str} WHERE id = ?;', values + [obj.id])

    def _exec(self, stmt: str, values: list | tuple) -> None:
        with self.lock:
            cursor = self.db.cursor()
            try:
                cursor.execute(stmt, values)
            finally:
                cursor.close()
            self.db.commit()

    @classmethod
    def row_to_model(cls, result: tuple) -> T:
        raise NotImplementedError

    def _model_to_row(self, obj: T) -> tuple[list[str], list]:
        raise NotImplementedError


class Users(Table[User]):
    tbl_name = 'users'
    init_stmts = [
        '''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL
        );
        ''',
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS users_name_idx ON users (name);
        '''
    ]

    @classmethod
    def row_to_model(cls, result: tuple) -> User:
        user_id, name, password_hash = result
        return User(id=user_id, name=name, password_hash=password_hash)

    def _model_to_row(self, user: User) -> tuple[list[str], list]:
        return ['name', 'password_hash'], [user.name, user.password_hash]


class Printers(Table[Printer]):
    tbl_name = 'printers'
    init_stmts = [
        '''
        CREATE TABLE IF NOT EXISTS printers(
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id),
            templates TEXT NOT NULL DEFAULT '',
            upgrades TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            trial_expires_at INTEGER DEFAULT NULL
        );
        ''',
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS printers_name_idx ON printers (name);
        '''
    ]
    joins = 'LEFT JOIN users ON printers.user_id = users.id'

    @classmethod
    def row_to_model(cls, result: tuple) -> Printer:
        printer_id, name, _, templates, upgrades, created_at, trial_expires_at = result[:7]
        return Printer(id=printer_id, name=name, user=Users.row_to_model(result[7:]),
                       templates=[t for t in templates.split('\n') if t],
                       upgrades=[u for u in upgrades.split('\n') if u],
                       created_at=datetime.fromtimestamp(created_at, tz=timezone.utc),
                       trial_expires_at=datetime.fromtimestamp(trial_expires_at, tz=timezone.utc) \
                           if trial_expires_at is not None else None)

    def _model_to_row(self, printer: Printer) -> tuple[list[str], list]:
        return (['name', 'user_id', 'templates', 'upgrades', 'created_at', 'trial_expires_at'],
                [
                    printer.name, printer.user.id,
                    '\n'.join(printer.templates), '\n'.join(printer.upgrades),
                    printer.created_at.timestamp(),
                    printer.trial_expires_at.timestamp() if printer.trial_expires_at is not None else None
                ])


class Jobs(Table[Job]):
    tbl_name = 'jobs'
    init_stmts = [
        '''
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            printer_id INTEGER NOT NULL REFERENCES printers(id),
            name TEXT NOT NULL,
            doctype TEXT NOT NULL,
            attributes TEXT NOT NULL,
            "state" INT NOT NULL
        );
        ''',
        '''
        CREATE INDEX IF NOT EXISTS jobs_printer_id ON jobs (printer_id);
        '''
    ]
    joins = 'LEFT JOIN printers ON jobs.printer_id = printers.id LEFT JOIN users ON printers.user_id = users.id'

    @classmethod
    def row_to_model(cls, result: tuple) -> Job:
        job_id, _, name, doctype, attributes, state = result[:6]
        return Job(id=job_id, printer=Printers.row_to_model(result[6:]),
                   name=name, doctype=doctype, attributes=json.loads(attributes), state=IppJobState(state))

    def _model_to_row(self, job: Job) -> tuple[list[str], list]:
        return (['printer_id', 'name', 'doctype', 'attributes', 'state'],
                [job.printer.id, job.name, job.doctype, json.dumps(job.attributes), job.state.value])

    def update_state(self, job: Job) -> None:
        self._exec('UPDATE jobs SET state = ? WHERE id = ?', (job.state.value, job.id))

    def abort_pending(self, printer_id: int) -> None:
        self._exec('UPDATE jobs SET state = ? WHERE printer_id = ? AND state = ?',
                   (IppJobState.ABORTED.value, printer_id, IppJobState.PENDING.value))


class DbRepository:
    def __init__(self, file: Path) -> None:
        self.lock = Lock()
        self.db: Connection = connect(str(file), check_same_thread=False)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys = ON')
        self.users = Users(self.db, self.lock)
        self.printers = Printers(self.db, self.lock)
        self.jobs = Jobs(self.db, self.lock)
