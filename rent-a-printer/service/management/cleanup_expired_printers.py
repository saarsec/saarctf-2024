import sys
from datetime import timezone, datetime
from pathlib import Path
from sqlite3 import connect

root_dir = Path(__file__).absolute().parent.parent
sys.path.append(str(root_dir))

from management.add_printer import get_cups_connection


def get_active_printers() -> list[str]:
    db = root_dir / "data" / "db.sqlite3"
    conn = connect(f'file:{db}?mode=ro', uri=True)
    try:
        result = []
        for row in conn.execute(
                f'SELECT name FROM printers WHERE trial_expires_at IS NULL OR trial_expires_at > ?',
                (datetime.now(tz=timezone.utc).timestamp(),)
        ).fetchall():
            result.append(row[0])
        return result
    finally:
        conn.close()


def main() -> None:
    active_printers = set(get_active_printers())

    conn = get_cups_connection()
    for printer in conn.getPrinters():
        if printer not in active_printers:
            print(f'... deleting {printer}')
            conn.deletePrinter(printer)
    print('[DONE]')


if __name__ == '__main__':
    main()
