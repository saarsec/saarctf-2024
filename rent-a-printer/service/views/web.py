import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Blueprint, render_template, Response, send_file, flash, redirect, url_for, request
from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage

from db.models import Printer
from db.repository import DbRepository
from printer_utils import add_printer_to_cups, cups_url


@dataclass
class Doc:
    name: str
    size: int
    ts: float

    @classmethod
    def from_file(cls, f: Path) -> 'Doc':
        s = f.stat()
        return cls(name=f.name, size=s.st_size, ts=s.st_mtime)


@dataclass
class Template:
    key: str
    name: str
    pdf: Path
    preview: Path

    @classmethod
    def from_file(cls, f: Path) -> 'Template':
        return Template(key=f.stem, name=f.stem.replace('-', ' '), pdf=f, preview=f.with_suffix('.png'))

    @classmethod
    def all_public(cls) -> list['Template']:
        return [Template.from_file(f) for f in Path('static/pdf').iterdir() if f.name.endswith('.pdf')]

    @classmethod
    def from_user_dir(cls, base: Path) -> list['Template']:
        return [Template.from_file(f) for f in base.iterdir() if
                f.name.startswith('template') and f.name.endswith('.pdf')]

    @property
    def preview_url(self) -> str:
        if self.preview.parent.parent.name == 'static':
            return url_for('static', filename='pdf/' + self.preview.name)
        else:
            return url_for('web.doc_download', doc=self.preview.name)


class View:
    def __init__(self, data_dir: Path, repo: DbRepository) -> None:
        self.data_dir = data_dir
        self.repo = repo

    def blueprint(self) -> Blueprint:
        raise NotImplementedError


class WebsiteView(View):
    def index(self) -> str:
        return render_template("index.html", user=current_user)

    def _get_user_documents(self, username: str) -> list[Doc]:
        base = self.data_dir / username
        if not base.exists():
            return []
        return [Doc.from_file(f) for f in sorted(base.iterdir()) if f.is_file() and not f.name.endswith('.png')]

    @login_required
    def user_view(self) -> str:
        printers = self.repo.printers.by_many('user_id', current_user.id)
        docs = self._get_user_documents(current_user.name)
        return render_template("user.html", user=current_user, printers=printers, docs=docs)

    @login_required
    def doc_download(self, doc: str) -> Response:
        if not re.match(r'^[a-zA-Z0-9-]+\.(ps|pdf|bin|png)$', doc):
            flash('Invalid filename')
            return redirect(url_for('web.user_view'))
        return send_file(self.data_dir / current_user.name / doc)

    @login_required
    def printer_add(self) -> str:
        templates = Template.all_public() + Template.from_user_dir(self.data_dir / current_user.name)
        return render_template("printer_add.html", user=current_user, templates=templates)

    @login_required
    def printer_add_post(self) -> Response:
        name = request.form.get('name')
        template_candidates = Template.all_public() + Template.from_user_dir(self.data_dir / current_user.name)
        templates = [tmpl for tmpl in template_candidates if request.form.get(f'template-{tmpl.key}')]
        upgrades = [x for x in request.form.getlist('upgrades') if x]

        if not re.match(r'^[a-zA-Z0-9_]{3,64}$', name):
            flash('Invalid name')
            return redirect(url_for('web.printer_add'))

        name = current_user.name + '-' + name

        if self.repo.users.by_name(name) is not None:
            flash('Printer name already taken')
            return redirect(url_for('web.printer_add'))

        for upgrade in upgrades:
            if upgrade not in ('digitalize', 'tls'):
                flash('Invalid upgrade')
                return redirect(url_for('web.printer_add'))

        new_printer = Printer(0, name=name, user=current_user,
                              templates=[str(tmpl.pdf.absolute()) for tmpl in templates],
                              upgrades=upgrades,
                              trial_expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=30))
        self.repo.printers.store(new_printer)
        add_printer_to_cups(new_printer.name,
                            url_for('ipp_server.ipp_request', printer=new_printer.name, _external=True))
        flash('Your printer is active! Scan your network or add manually: ' + cups_url(new_printer))

        return redirect(url_for('web.user_view'))

    def template_add(self) -> Response:
        file: FileStorage = request.files['template']
        file_length = file.seek(0, os.SEEK_END)
        file.seek(0, os.SEEK_SET)

        if file_length < 10 or file_length > 1024 * 1024 or not file.filename.lower().endswith('.pdf'):
            flash('Invalid file (size or extension)')
            return redirect(url_for('web.user_view'))

        base = self.data_dir / current_user.name
        number = 1
        f = base / f'template-{number:05d}.pdf'
        while f.exists():
            number += 1
            f = base / f'template-{number:05d}.pdf'

        file.save(f)
        subprocess.check_call(['mogrify', '-format', 'png', '-density', '36', str(f)])
        flash('Template added')
        return redirect(url_for('web.user_view'))

    def blueprint(self) -> Blueprint:
        bp = Blueprint('web', __name__)
        bp.add_url_rule('/', None, self.index, methods=['GET'])
        bp.add_url_rule('/me', None, self.user_view, methods=['GET'])
        bp.add_url_rule('/docs/<doc>', None, self.doc_download, methods=['GET'])
        bp.add_url_rule('/rent-a-printer', None, self.printer_add, methods=['GET'])
        bp.add_url_rule('/rent-a-printer', None, self.printer_add_post, methods=['POST'])
        bp.add_url_rule('/upload-template', None, self.template_add, methods=['POST'])

        bp.app_template_filter('cups_url')(cups_url)

        @bp.app_template_filter('unix_timestamp')
        def format_timestamp(ts: int | datetime) -> str:
            dt = ts if isinstance(ts, datetime) else datetime.fromtimestamp(ts)
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        @bp.app_template_filter('unix_timestamp_short')
        def format_timestamp_short(ts: int | datetime) -> str:
            dt = ts if isinstance(ts, datetime) else datetime.fromtimestamp(ts)
            if dt.date() == datetime.today().date():
                return dt.strftime('%H:%M')
            else:
                return dt.strftime('%Y-%m-%d')

        return bp
