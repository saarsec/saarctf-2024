import logging
import pprint
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Blueprint, request, Response
from pyipp.enums import IppOperation

from db.repository import DbRepository
from ipp import parser
from ipp.ipp_message import IppMessage
from printer.factory import PrinterFactory
from views.web import View


class IppView(View):
    def __init__(self, data_dir: Path, repo: DbRepository) -> None:
        super().__init__(data_dir, repo)

        self.factory = PrinterFactory(self.data_dir, self.repo, ThreadPoolExecutor(max_workers=2))

        self._logger = logging.Logger('ipp_request')
        fh = logging.FileHandler('data/ipp.log')
        fh.setLevel(logging.INFO)
        self._logger.addHandler(fh)

    def blueprint(self) -> Blueprint:
        bp = Blueprint('ipp_server', __name__)
        bp.add_url_rule('/printserver/<printer>', None, self.ipp_request, methods=['POST'])
        bp.add_url_rule('/printers/<printer>', None, self.ipp_request, methods=['POST'])
        bp.add_url_rule('/', None, self.ipp_request, methods=['POST'], defaults={'printer': ''})
        bp.add_url_rule('/ppds/<printer>', None, self.ppd_request, methods=['GET'])
        return bp

    def ipp_request(self, printer: str) -> Response:
        # self._logger.info('-' * 80)
        if request.headers['Content-Type'] != 'application/ipp':
            return Response('Invalid content type', status=400)
        body: bytes = request.data
        msg = IppMessage.decode(body)
        # self._logger.info(pprint.pformat(msg, indent=2))

        if not printer and 'printer-uri' in msg.operation_attributes:
            printer = msg.operation_attributes['printer-uri'].split('/')[-1]
        try:
            printer_instance = self.factory.get(printer)
        except KeyError:
            self._logger.info(f'printer not found: {printer!r}')
            return Response('not found', status=404)

        response = None
        match msg.operation_id:
            case IppOperation.GET_PRINTER_ATTRIBUTES:
                response = printer_instance.get_printer_attributes(msg)
            case IppOperation.PRINT_JOB:
                response = printer_instance.add_job(msg)
            case IppOperation.GET_JOBS:
                response = printer_instance.get_jobs(msg)
            case IppOperation.VALIDATE_JOB:
                response = printer_instance.validate_job(msg)
            case IppOperation.CANCEL_JOB.value:
                response = printer_instance.cancel_job(msg)
            case IppOperation.GET_JOB_ATTRIBUTES.value:
                response = printer_instance.get_job_attributes(msg)
            case _:
                logging.error('Unsupported operation id', msg.operation_id)
                self._logger.error('Unsupported operation id', msg.operation_id)

        if response is not None:
            response.request_id = msg.request_id
            # self._logger.info('=> ' + pprint.pformat(parser.parse(response.encode()), indent=2))
            sys.stdout.flush()
            return Response(response.encode(), content_type='application/ipp', status=200)

        return Response('Not implemented', status=500)

    def ppd_request(self, printer: str):
        if printer.endswith('.ppd'):
            printer = printer[:-4]
        try:
            printer_instance = self.factory.get(printer)
        except KeyError:
            return Response('not found', status=404)
        return Response(printer_instance.get_ppd(), content_type='application/ppd', status=200)
