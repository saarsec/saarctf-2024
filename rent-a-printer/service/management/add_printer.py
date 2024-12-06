import argparse
import tempfile
from urllib.parse import urlparse, urlunparse

import cups
import requests


def get_cups_connection() -> cups.Connection:
    cups.ppdSetConformance(cups.PPD_CONFORM_RELAXED)
    # TODO credentials  REMOVE-VULNBOX
    cups.setUser('root')  # REMOVE-VULNBOX
    cups.setPasswordCB(lambda _: '123456789')  # REMOVE-VULNBOX
    return cups.Connection(host='192.168.56.105')  # REMOVE-VULNBOX
    return cups.Connection(host='/run/cups/cups.sock')


def add_shared_printer(conn: cups.Connection, name: str, url: str, ppd: cups.PPD) -> None:
    conn.addPrinter(name=name, device=url, ppd=ppd)
    conn.enablePrinter(name)
    conn.acceptJobs(name)
    try:
        conn.setPrinterShared(name, True)
    except cups.IPPError as e:
        print('Cannot share the printer:', e)


def get_ppd(url: str) -> cups.PPD:
    parsed = urlparse(url)
    if parsed.scheme in ('ipp', 'ipps') and ':' not in parsed.netloc:
        parsed = parsed._replace(scheme=parsed.scheme.replace('ipp', 'http'), netloc=parsed.netloc + ':631')
    parsed = parsed._replace(path=parsed.path.replace('/printers/', '/ppds/').replace('/printserver/', '/ppds/'))
    url = urlunparse(parsed)

    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError('Cannot retrieve printer info')

    with tempfile.NamedTemporaryFile() as tmpf:
        tmpf.write(response.content)
        tmpf.flush()
        try:
            return cups.PPD(tmpf.name)
        except (cups.IPPError, RuntimeError):
            raise ValueError("Server's ppd file is corrupted.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('name', type=str, help='Printer name')
    parser.add_argument('url', type=str, help='Printer URL')
    args = parser.parse_args()

    conn = get_cups_connection()
    ppd = get_ppd(args.url)
    add_shared_printer(conn, args.name, args.url, ppd)
    print('[OK] printer added')


if __name__ == '__main__':
    main()
