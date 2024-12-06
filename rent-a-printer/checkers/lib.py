import re
import uuid
from urllib.parse import urlparse, urlunparse

import requests
from flask import Response
from pyipp.enums import IppOperation, IppFinishing, IppStatus

from gamelib import Session, assert_requests_response
from .ipp_message import IppMessage


class ServiceSession:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip('/')
        self.session = Session()

    def get(self, url: str, **kwargs) -> Response:
        return self.session.get(self.url + url, **kwargs)

    def post(self, url: str, *args, **kwargs) -> Response:
        return self.session.post(self.url + url, *args, **kwargs)

    def login(self, username: str, password: str) -> bool:
        response = assert_requests_response(
            self.post('/login', {'name': username, 'password': password}),
            'text/html; charset=utf-8')
        return f'Welcome, {username}' in response.text

    def signup(self, username: str, password: str) -> bool:
        response = assert_requests_response(
            self.post('/signup', {'name': username, 'password': password}),
            'text/html; charset=utf-8')
        return f'Welcome, {username}' in response.text

    def rent_printer(self, name: str, templates: list[str], upgrades: list[str]) -> Response:
        data = [('name', name)]
        for tmpl in templates:
            data.append((f'template-{tmpl}', '1'))
        for upgrade in upgrades:
            data.append(('upgrades', upgrade))
        response = assert_requests_response(self.post('/rent-a-printer', data, timeout=12), 'text/html; charset=utf-8')
        assert f'Your printer is active' in response.text, 'Could not add printer'
        assert name in response.text, 'Printer added but not in list'
        return response

    def printer_url(self, username: str, printer_name: str, has_tls: bool) -> str:
        p = urlparse(self.url)
        p2 = p._replace(scheme='ipps' if has_tls else 'ipp', netloc=p.netloc.split(':')[0] + ':631',
                        path=f'/printers/{username}-{printer_name}')
        return urlunparse(p2)

    def get_documents(self) -> list[str]:
        response = assert_requests_response(self.get('/me'), 'text/html; charset=utf-8')
        return re.findall(r'href="/docs/(job-\d+\.(?:pdf|ps|bin))"', response.text)

    def download(self, docname: str) -> bytes:
        response = assert_requests_response(self.get(f'/docs/{docname}'), 'application/pdf')
        return response.content

    def upload_template(self, data: bytes) -> None:
        response = assert_requests_response(
            self.post('/upload-template', files={'template': ('template.pdf', data)}),
            'text/html; charset=utf-8'
        )
        assert 'Template added' in response.text, 'Could not upload template'


def format_op(i: int) -> str:
    try:
        op = IppOperation(i)
        return f'{op.name}: {op.value}'
    except ValueError:
        return str(i)


def format_status(i: int) -> str:
    try:
        op = IppStatus(i)
        return f'{op.name}: {op.value}'
    except ValueError:
        return str(i)


class MyIppClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.http_url = url.replace('ipp://', 'http://').replace('ipps://', 'https://')
        self.session = Session()
        self.next_request_id = 1
        self.default_attrs = {
            'attributes-charset': 'utf-8',
            'attributes-natural-language': 'en-us',
            'printer-uri': self.url,
            "requesting-user-name": "saarsec",
        }

    def request(self, req: IppMessage) -> IppMessage:
        req.request_id = self.next_request_id
        self.next_request_id += 1

        for k, v in self.default_attrs.items():
            if k not in req.operation_attributes:
                req.operation_attributes[k] = v

        print(f'> IPP {self.http_url} {format_op(req.operation_id)}')
        http_response = self.session.post(self.http_url, data=req.encode(), headers={'content-type': 'application/ipp'},
                                          verify=False)
        assert http_response.status_code == 200, f'IPP request failed with status code {http_response.status_code}'
        response = IppMessage.decode(http_response.content)
        print(f'< IPP {format_status(response.status_code)}')
        return response

    def get_printer_attributes(self, attrs=('all',)):
        return self.request(IppMessage(
            status_code=IppOperation.GET_PRINTER_ATTRIBUTES.value,
            operation_attributes={
                'requested-attributes': list(attrs),
            }
        ))

    def get_job_attributes(self, job_id: int):
        return self.request(IppMessage(
            status_code=IppOperation.GET_JOB_ATTRIBUTES.value,
            operation_attributes={
                'job-id': job_id,
                "requested-attributes": [
                    'job-id', 'job-state', 'job-state-reasons', 'job-impressions-completed',
                    'job-media-sheets-completed'
                ]
            }
        ))

    def print_job(self, doctype: str, docname: str, document: bytes):
        return self.request(IppMessage(
            status_code=IppOperation.PRINT_JOB.value,
            operation_attributes={
                'job-name': docname,
                'document-name': docname,
                'document-format': doctype,
                'job-impressions': 1,
                'job-media-sheets': 1,
            },
            jobs=[{
                # 'ColorModel': 'Gray',
                'document-name-supplied': docname,
                # 'Duplex': 'None',
                'finishings': IppFinishing.NONE.value,
                'job-cancel-after': 10800,
                'job-originating-host-name': 'localhost',
                'job-originating-user-name': 'root',
                'job-priority': 50,
                'job-sheets': ['none'],
                'job-uuid': 'urn:uuid:' + str(uuid.uuid4()),
                'media': 'iso_a4_210x297mm',
                'media-size': {
                    "x-dimension": 21000,
                    "y-dimension": 29700
                },
                'number-up': 1,
                'orientation-requested': 0,
                'output-bin': 'face-down',
                'output-format': 'pdf',
                'print-color-mode': 'color',
                'print-quality': 0,
                'printer-resolution': (300, 300, 3),
                # 'Resolution': '600dpi',
                'sides': 'one-sided'
            }],
            data=document
        ))
