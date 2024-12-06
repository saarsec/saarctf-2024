import os
import threading
import time
from hashlib import sha256
from pathlib import Path

from app import create_app
from db.models import User, Printer
from db.repository import DbRepository
from printer_utils import add_printer_to_cups
from views.web import Template


def main() -> None:
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(mode=0o750, exist_ok=True)
    repo = DbRepository(data_dir / 'db.sqlite3')
    (data_dir / 'db.sqlite3').chmod(0o640)

    user1 = User(0, 'admin', sha256(b'admin').hexdigest())
    user2 = User(0, 'test', sha256(b'test').hexdigest())
    repo.users.store(user1)
    repo.users.store(user2)

    tmpl = [t for t in Template.all_public() if t.name.endswith('branding')]
    printer1 = Printer(0, 'admin-Demo-Printer', user1, [str(t.pdf.absolute()) for t in tmpl], [])
    printer2 = Printer(0, 'test-Digital-Printer', user2, [], ['digitalize', 'tls'])
    repo.printers.store(printer1)
    repo.printers.store(printer2)

    app = create_app(data_dir, repo)
    t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=6310), daemon=True)
    t.start()

    time.sleep(1)

    add_printer_to_cups(printer1.name, f'http://127.0.0.1:6310/printserver/{printer1.name}')
    add_printer_to_cups(printer2.name, f'http://127.0.0.1:6310/printserver/{printer2.name}')

    secret_file = data_dir / 'secret.txt'
    if secret_file.exists():
        secret_file.unlink()

    print('[DONE]')
    time.sleep(1)


if __name__ == '__main__':
    os.chdir(Path(__file__).absolute().parent)
    main()
