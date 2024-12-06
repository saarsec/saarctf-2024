import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from flask import url_for

from db.models import Printer


def cups_url(printer: Printer) -> str:
    url = urlparse(url_for('web.index', _external=True))
    url = url._replace(scheme='ipps' if 'tls' in printer.upgrades else 'ipp',
                       netloc=url.netloc.split(':')[0], path=f'printers/{printer.name}')
    return urlunparse(url)


def add_printer_to_cups(name: str, backend_url: str) -> None:
    # TODO  REMOVE-VULNBOX
    backend_url = backend_url.replace('localhost', '192.168.56.1')  # REMOVE-VULNBOX
    root_dir = Path(__file__).absolute().parent
    script = root_dir / 'management' / 'add_printer.py'
    subprocess.run([sys.executable, str(script), name, backend_url], cwd=root_dir, check=True)  # REMOVE-VULNBOX
    return  # REMOVE-VULNBOX
    subprocess.run(['sudo', '-u', 'rent-a-printer-admin',
                    sys.executable, str(script), name, backend_url], cwd=root_dir, check=True)
