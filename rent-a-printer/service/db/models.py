from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast

from flask_login import UserMixin
from pyipp.enums import IppJobState


@dataclass
class User(UserMixin):
    id: int
    name: str
    password_hash: str

    @property
    def is_active(self):
        return self.id > 0


@dataclass
class Printer:
    id: int
    name: str
    user: User
    templates: list[str]
    upgrades: list[str]
    created_at: datetime = datetime.now(tz=timezone.utc)
    trial_expires_at: datetime | None = None

    @property
    def active(self) -> bool:
        return self.trial_expires_at is None or self.trial_expires_at > datetime.now(tz=timezone.utc)


UndefinedPrinter: Printer = cast(Printer, None)


@dataclass
class Job:
    id: int
    printer: Printer
    name: str
    doctype: str
    attributes: dict
    document: bytes | None = None

    state: IppJobState = IppJobState.PENDING

    @classmethod
    def from_attributes(cls, name: str, doctype: str, d: dict | None) -> 'Job':
        if d is None:
            d = {}
        return Job(0, UndefinedPrinter, name, doctype, attributes=d)

    def set_document(self, doc: bytes) -> None:
        self.document = doc
        if doc.startswith(b'%PDF-'):
            self.doctype = 'application/pdf'
