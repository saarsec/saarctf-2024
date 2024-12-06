import io
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path

import cv2
import fpdf
import numpy
from pyipp.enums import IppStatus, IppJobState
from pypdf import PdfReader
from pyzbar import pyzbar

try:
    from checkers.lib import ServiceSession, MyIppClient
    from checkers.ipp_message import IppMessage
except ImportError:
    from .lib import ServiceSession, MyIppClient
    from .ipp_message import IppMessage

from gamelib import *
from gamelib.usernames import generate_password, generate_name, USERNAME_ADJECTIVES, USERNAME_NOUNS


def assert_ipp_success(response: IppMessage) -> IppMessage:
    if response.status_code != IppStatus.OK:
        print('<', response)
        raise MumbleException(f'IPP response failed with status {response.status_code}')
    return response


def pdf_to_text(pdf: bytes) -> str:
    result = ''
    reader = PdfReader(io.BytesIO(pdf))
    for page in reader.pages:
        result += page.extract_text() + '\n\n\n'
    return result


class QrDecoder:
    def __init__(self) -> None:
        self.detector1 = cv2.QRCodeDetector()
        self.detector2 = cv2.QRCodeDetectorAruco()

    def decode(self, data: bytes) -> str:
        image = cv2.imdecode(numpy.frombuffer(data, dtype=numpy.uint8), flags=cv2.IMREAD_ANYCOLOR)
        reversed_image = 255 - image
        if result := self.decode_cv_2(reversed_image): return result
        if result := self.decode_zbar(reversed_image): return result
        if result := self.decode_cv_1(reversed_image): return result
        if result := self.decode_cv_2(image): return result
        if result := self.decode_zbar(image): return result
        if result := self.decode_cv_1(image): return result
        return ''

    def decode_cv_1(self, image) -> str | None:
        data, _, _ = self.detector1.detectAndDecode(image)
        return data

    def decode_cv_2(self, image) -> str | None:
        data, _, _ = self.detector2.detectAndDecode(image)
        return data

    def decode_zbar(self, image) -> str | None:
        result: list = pyzbar.decode(image, [pyzbar.ZBarSymbol.QRCODE])
        if len(result) > 0:
            return result[0].data.decode('utf-8')


def qr_to_text(pdf: bytes) -> str:
    decoder = QrDecoder()
    result = ''
    reader = PdfReader(io.BytesIO(pdf))
    for page in reader.pages:
        for img in page.images:
            result += decoder.decode(img.data) + '\n'
    return result


@dataclass
class TickConfig:
    username: str
    password: str
    flag: str
    has_tls: bool
    is_qr: bool
    template: str
    is_retry: bool


class PrinterServiceInterface(ServiceInterface):
    name = 'Rent-a-Printer'

    flag_id_types = ['username']

    _templates = ['saarsec-branding', 'saarsec-watermark', 'template-00001']

    def _tick_config(self, team: Team, tick: int, should_generate_password: bool) -> TickConfig:
        username = self.get_flag_id(team, tick, 0)
        password = self.load(team, tick, 'password')
        has_tls = (team.id + tick) % 4 < 2
        is_qr = (team.id + tick) % 2 == 0
        tmpl = self._templates[(team.id + tick) % len(self._templates)]
        is_retry = password is not None and should_generate_password
        flag = self.get_flag(team, tick, payload=1 if is_qr else 0)
        if password is None:
            if should_generate_password:
                password = generate_password(12, 16)
                self.store(team, tick, 'password', password)
            else:
                raise FlagMissingException('never stored')
        return TickConfig(username, password, flag, has_tls, is_qr, tmpl, is_retry)

    def check_integrity(self, team: Team, tick: int):
        session = ServiceSession(f'http://{team.ip}:6310/')
        assert_requests_response(session.get('/'), 'text/html; charset=utf-8')

    def store_flags(self, team: Team, tick: int):
        cfg = self._tick_config(team, tick, True)
        print(cfg)

        # create account
        session = ServiceSession(f'http://{team.ip}:6310/')
        if not session.signup(cfg.username, cfg.password):
            if not cfg.is_retry or not session.login(cfg.username, cfg.password):
                raise MumbleException('Cannot signup')

        if cfg.template.startswith('template'):
            session.upload_template(self._generate_template(cfg))

        # create printer
        printer_name = generate_name()
        upgrades = []
        if cfg.has_tls:
            upgrades.append('tls')
        if cfg.is_qr:
            upgrades.append('digitalize')
        session.rent_printer(printer_name, [cfg.template], upgrades)

        time.sleep(1.2)

        # print the flag on that printer
        printer_url = session.printer_url(cfg.username, printer_name, cfg.has_tls)
        print('PRINTER: ' + printer_url)
        ipp = MyIppClient(printer_url)
        msg = assert_ipp_success(ipp.get_printer_attributes(['all']))
        assert len(msg.printers) > 0, 'printer not found'
        assert msg.printers[0]['printer-name'] == cfg.username + '-' + printer_name, 'Wrong printer name'

        doc = self.generate_document(f'My flag: {cfg.flag}')
        msg = assert_ipp_success(ipp.print_job('application/pdf', 'flag.pdf', doc))
        print('print-job result:', msg)
        job_id = msg.jobs[0]['job-id']
        assert job_id is not None

        # wait for print job to complete
        for _ in range(10):
            time.sleep(1)
            msg = assert_ipp_success(ipp.get_job_attributes(job_id))
            assert len(msg.jobs) > 0, 'Job not found in IPP message'
            state = msg.jobs[0]['job-state']
            print(f'state: {state}')
            if state in (IppJobState.ABORTED, IppJobState.STOPPED, IppJobState.CANCELED):
                raise MumbleException('Print job did not complete')
            if state == IppJobState.COMPLETED:
                print('Job completed')
                break

    def retrieve_flags(self, team: Team, tick: int):
        cfg = self._tick_config(team, tick, False)
        print(f'Retrieve config: {cfg}')

        session = ServiceSession(f'http://{team.ip}:6310/')
        assert session.login(cfg.username, cfg.password), 'Login failed'
        docs = session.get_documents()
        print(f'Documents: {docs}')
        for docname in docs:
            doc = session.download(docname)
            try:
                text = qr_to_text(doc) if cfg.is_qr else pdf_to_text(doc)
                print(f'Content of {docname}: {text!r}')
            except Exception as e:
                print(f'cannot read/parse {doc[:50]!r}...: {e}')
                continue
            if cfg.flag in text:
                self._validate_template(cfg, doc)
                return
        raise FlagMissingException('flag not found in documents')

    def generate_document(self, text: str) -> bytes:
        pdf = fpdf.FPDF(format='A4')  # pdf format
        pdf.l_margin = 30
        pdf.r_margin = 30
        pdf.add_page()  # create new page
        pdf.add_font('Roboto', fname='/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf', uni=True)
        pdf.set_font("Roboto", size=random.randint(12, 16))  # font and textsize
        pdf.y += random.randint(20, 90)
        pdf.cell(200, 10, text, ln=1, align="L", fill=False)

        pdf.set_font("Roboto", size=10)
        for _ in range(random.randint(0, 20)):
            pdf.cell(200, 7, ' '.join(
                random.choice(USERNAME_ADJECTIVES if random.randint(0, 99) < 60 else USERNAME_NOUNS) \
                for _ in range(random.randint(10, 11))), ln=1, align="L", fill=False)

        return pdf.output('', 'S').encode('latin-1')

    def _generate_template(self, cfg: TickConfig) -> bytes:
        pdf = fpdf.FPDF(format='A4')  # pdf format
        pdf.add_page()  # create new page
        pdf.add_font('Roboto', fname='/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf', uni=True)
        pdf.set_font("Roboto", size=8)  # font and textsize
        text1 = f'printed by {cfg.username}'
        text2 = '#' + md5(('wiuwd' + cfg.password).encode()).hexdigest()
        pdf.cell(180, 0, text1, ln=1, align="C")
        pdf.cell(180, 8, text2, ln=1, align="C")
        return pdf.output('', 'S').encode('latin-1')

    def _validate_template(self, cfg: TickConfig, doc: bytes) -> None:
        print(cfg.template)
        if cfg.template.startswith('template-'):
            text = pdf_to_text(doc)
            secret = md5(('wiuwd' + cfg.password).encode()).hexdigest()
            assert cfg.username in text, 'Custom template not applied'
            assert secret in text, 'Custom template not fully applied'

        elif cfg.template == 'saarsec-branding':
            reader = PdfReader(io.BytesIO(doc))
            logos = [img for img in reader.pages[0].images if img.image.size == (471, 471)]
            assert len(logos) > 0, 'logos from template "saarsec-branding" not found in final pdf'

        elif cfg.template == 'saarsec-watermark':
            reader = PdfReader(io.BytesIO(doc))
            print([img.image.size for img in reader.pages[0].images])
            logos = [img for img in reader.pages[0].images if img.image.size == (1024, 1024)]
            assert len(logos) > 0, 'logos from template "saarsec-watermark" not found in final pdf'


def demo_docs(service: PrinterServiceInterface):
    cfg = TickConfig(username='AbleSimpleNut3863', password='...', flag='SAAR{AQABAAEAAAA1gl4THL8cvFriWd_mag-H}',
                     has_tls=False, is_qr=False, template='template-00001', is_retry=False)
    Path('example-template.pdf').write_bytes(service._generate_template(cfg))
    Path('example-doc.pdf').write_bytes(service.generate_document('My flag: ' + cfg.flag))
    subprocess.check_call([sys.executable, '../service/filters/qrcodes.py', '', '', '', '', '', 'example-doc.pdf'],
                          stdout=open('example-doc-qr.pdf', 'wb'))
    ppd = '*PPD-Adobe: "4.3"\n'
    ppd += '*FormatVersion: "4.3"\n'
    ppd += '*FileVersion: "1.28.17"\n'
    ppd += '*LanguageVersion: English\n'
    ppd += '*LanguageEncoding: ISOLatin1\n'
    ppd += f'*saarsecFilterTemplate: "{Path(__file__).absolute().parent.parent}/service/static/pdf/saarsec-watermark.pdf"\n'
    Path('/tmp/tmp.ppd').write_text(ppd)
    subprocess.check_call([sys.executable, '../service/filters/add_template.py', '', '', '', '', '', 'example-doc.pdf'],
                          stdout=open('example-doc-tmpl.pdf', 'wb'), env={'PPD': '/tmp/tmp.ppd'})
    Path('/tmp/tmp.ppd').unlink(missing_ok=True)
    reader = PdfReader('example-doc-tmpl.pdf')
    print([img.image.size for img in reader.pages[0].images])


if __name__ == '__main__':
    # USAGE: python3 interface.py                      # test against localhost
    # USAGE: python3 interface.py 1.2.3.4              # test against IP
    # USAGE: python3 interface.py 1.2.3.4 retrieve     # retrieve last 10 ticks (for exploits relying on checker interaction)
    # USAGE: python3 interface.py 1.2.3.4 store        # store a few ticks (for exploits relying on checker interaction)
    # (or use gamelib/run-checkers to test against docker container)
    # team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    service = PrinterServiceInterface(1)

    if len(sys.argv) > 2 and sys.argv[2] == 'retrieve':
        for tick in range(1, 10):
            try:
                service.retrieve_flags(team, tick)
            except:
                pass
        sys.exit(0)
    elif len(sys.argv) > 2 and sys.argv[2] == 'store':
        for tick in range(50, 55):
            try:
                service.store_flags(team, tick)
            except:
                pass
        sys.exit(0)
    elif len(sys.argv) > 2 and sys.argv[2] == 'testdocs':
        demo_docs(service)
        sys.exit(0)

    for tick in range(1, 5):
        print(f'\n\n=== TICK {tick} ===')
        service.check_integrity(team, tick)
        service.store_flags(team, tick)
        service.retrieve_flags(team, tick)
