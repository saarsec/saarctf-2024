import logging
import time
from logging import Logger

from pyipp.enums import IppPrinterState, IppOperation, IppStatus, IppJobState

from db.models import Job
from ipp.ipp_message import IppMessage
from printer.job_queue import JobQueue


class Printer:
    def __init__(self, name: str, queue: JobQueue) -> None:
        self.name = name
        self.base_uri = f'ipp://192.168.56.1:5001/printers/{name}'
        self.queue = queue
        self.logger = Logger(self.__class__.__name__)
        self.logger.handlers = logging.root.handlers

    def get_ppd(self) -> str:
        ppd_lines = [
            '*PPD-Adobe: "4.3"',
            # '*APRemoteQueueID: ""',
            '*FormatVersion: "4.3"',
            '*FileVersion: "1.28.17"',
            '*LanguageVersion: English',
            '*LanguageEncoding: ISOLatin1',
            '*PSVersion: "(3010.000) 0"',
            '*LanguageLevel: "3"',
            '*FileSystem: False',
            '*PCFileName: "drvless.ppd"',
            '*Manufacturer: "Saarsec"',
            f'*ModelName: "{self.name}"',
            f'*Product: "Rent-a-printer {self.name}"',
            f'*NickName: "{self.name}"',
            f'*ShortNickName: "{self.name}"',
            '*DefaultOutputOrder: Normal',
            '*ColorDevice: True',
            '*cupsVersion: 2.4',
            '*cupsSNMPSupplies: False',
            '*cupsLanguages: "en"',
            '*cupsFilter2: "application/vnd.cups-pdf application/pdf 200 -"',
            '*OpenUI *PageSize/Media Size: PickOne',
            '*OrderDependency: 10 AnySetup *PageSize',
            '*DefaultPageSize: A4',
            '*PageSize A4/A4: "<</PageSize[595.275590551181 841.889763779528]>>setpagedevice"',
            '*PageSize Letter/US Letter: "<</PageSize[612 792]>>setpagedevice"',
            '*CloseUI: *PageSize',
            '*OpenUI *PageRegion/Media Size: PickOne',
            '*OrderDependency: 10 AnySetup *PageRegion',
            '*DefaultPageRegion: A4',
            '*PageRegion A4/A4: "<</PageSize[595.275590551181 841.889763779528]>>setpagedevice"',
            '*PageRegion Letter/US Letter: "<</PageSize[612 792]>>setpagedevice"',
            '*CloseUI: *PageRegion',
            '*DefaultImageableArea: A4',
            '*DefaultPaperDimension: A4',
            '*ImageableArea A4: "0 0 595.275590551181 841.889763779528"',
            '*PaperDimension A4: "595.275590551181 841.889763779528"',
            '*ImageableArea Letter: "0 0 612 792"',
            '*PaperDimension Letter: "612 792"',
            '*OpenUI *ColorModel/Print Color Mode: PickOne',
            '*OrderDependency: 10 AnySetup *ColorModel',
            '*DefaultColorModel: RGB',
            '*ColorModel FastGray/Fast Grayscale: "<</cupsColorSpace 3/cupsBitsPerColor 1/cupsColorOrder 0/cupsCompression 0/ProcessColorModel /DeviceGray>>setpagedevice"',
            '*ColorModel Gray/Grayscale: "<</cupsColorSpace 18/cupsBitsPerColor 8/cupsColorOrder 0/cupsCompression 0/ProcessColorModel /DeviceGray>>setpagedevice"',
            '*ColorModel RGB/Color: "<</cupsColorSpace 19/cupsBitsPerColor 8/cupsColorOrder 0/cupsCompression 0/ProcessColorModel /DeviceRGB>>setpagedevice"',
            '*CloseUI: *ColorModel',
            '*OpenUI *Duplex/2-Sided Printing: PickOne',
            '*OrderDependency: 10 AnySetup *Duplex',
            '*DefaultDuplex: None',
            '*Duplex None/Off: "<</Duplex false>>setpagedevice"',
            '*Duplex DuplexNoTumble/On (Portrait): "<</Duplex true/Tumble false>>setpagedevice"',
            '*Duplex DuplexTumble/On (Landscape): "<</Duplex true/Tumble true>>setpagedevice"',
            '*CloseUI: *Duplex',
            '*DefaultResolution: 300dpi',
        ]
        for tmpl in self.queue.model.templates:
            ppd_lines.append('*cupsFilter2: "application/pdf application/pdf 0 add_template.py"')
            ppd_lines.append(f'*saarsecFilterTemplate: {tmpl}')
        if 'digitalize' in self.queue.model.upgrades:
            ppd_lines.append('*cupsPreFilter: "application/pdf 0 qrcodes.py"')
        return '\n'.join(ppd_lines) + '\n'

    def _get_default_msg(self) -> IppMessage:
        return IppMessage(operation_attributes={
            'attributes-charset': 'utf-8',
            'attributes-natural-language': 'en-us'
        }, printers=[{
            'printer-is-accepting-jobs': True,
            'printer-state': IppPrinterState.IDLE.value if self.queue.processing_jobs == 0 else IppPrinterState.PROCESSING.value,
            'printer-state-reasons': 'none',
            'compression-supported': 'none',
        }])

    def get_printer_attributes(self, msg: IppMessage) -> IppMessage:
        self.logger.info(f'get_printer_attributes {msg.operation_attributes["requested-attributes"]}')
        result = self._get_default_msg()
        result.printers[0].update({
            'printer-dns-sd-name': self.name,
            'printer-is-temporary': False,
            'printer-type': 4,
            'printer-up-time': int(time.time()),
            'printer-uri-supported': self.base_uri,
            'queued-job-count': self.queue.num_in_queue(),
            'uri-security-supported': 'none',
            'uri-authentication-supported': 'none',
            'printer-name': self.name,
            'printer-location': 'Rent-a-printer',
            'printer-geo-location': 'Rent-a-printer HQ',
            'printer-info': f'Rent-a-printer powered printer for {self.queue.model.user.name}',
            'printer-organization': 'Rent-a-printer',
            'printer-organizational-unit': 'Rent-a-printer-HQ',
            # 'printer-uuid': 'urn:uuid:0fa9e6f6-f417-3de1-6237-30f77eafb0a7',
            'document-format-supported': ['application/pdf'],
            'document-format-default': 'application/pdf',
            'print-color-mode-default': 'color',
            'print-color-mode-supported': ["monochrome", "color"],
            'printer-make-and-model': 'Rent-a-printer Online Printer',
            'finishings-supported': 3,
            'finishings-default': 3,
            'charset-configured': 'utf-8',
            'charset-supported': ['us-ascii', 'utf-8'],
            'generated-natural-language-supported': 'en-us',
            'ipp-versions-supported': ['1.0', '1.1', '2.0'],
            'job-creation-attributes-supported': ['copies', 'finishings', 'finishings-col', 'job-name',
                                                  'job-priority', 'job-sheets', 'media', 'media-col',
                                                  'multiple-document-handling', 'number-up', 'number-up-layout',
                                                  'orientation-requested', 'page-delivery',
                                                  'page-ranges', 'print-color-mode', 'print-quality',
                                                  'print-scaling', 'printer-resolution', 'sides'],
            'job-settable-attributes-supported': ['copies', 'finishings', 'job-name',
                                                  'job-priority', 'media', 'media-col',
                                                  'multiple-document-handling', 'number-up',
                                                  'orientation-requested', 'page-ranges', 'print-color-mode',
                                                  'print-quality', 'printer-resolution', 'sides'],
            'job-priority-supported': 100,
            'media-col-supported': ['media-bottom-margin', 'media-left-margin', 'media-right-margin',
                                    'media-size', 'media-source', 'media-top-margin', 'media-type'],
            'multiple-document-handling-supported': ['separate-documents-uncollated-copies',
                                                     'separate-documents-collated-copies'],
            'multiple-document-jobs-supported': False,
            'natural-language-configured': 'en-us',
            'operations-supported': [
                IppOperation.GET_PRINTER_ATTRIBUTES.value,
                IppOperation.PRINT_JOB.value,
                IppOperation.VALIDATE_JOB.value,
                IppOperation.CANCEL_JOB.value,
                IppOperation.GET_JOB_ATTRIBUTES.value,
            ],
            'orientation-requested-supported': [3, 4, 5, 6],
            'page-delivery-supported': ['reverse-order', 'same-order'],
            'page-ranges-supported': False,
            'pdf-versions-supported': ['adobe-1.2', 'adobe-1.3', 'adobe-1.4', 'adobe-1.5', 'adobe-1.6',
                                       'adobe-1.7', 'iso-19005-1_2005', 'iso-32000-1_2008', 'pwg-5102.3'],
            'pdl-override-supported': 'not-attempted',
            'print-scaling-supported': ['none'],
            'printer-get-attributes-supported': 'document-format',
            'which-jobs-supported': ['completed', 'not-completed', 'aborted', 'all', 'canceled', 'pending',
                                     'pending-held', 'processing', 'processing-stopped'],

            'media-col-default': [{
                "media-size": {
                    "x-dimension": 21000,
                    "y-dimension": 29700
                },
                "media-bottom-margin": 0,
                "media-left-margin": 0,
                "media-right-margin": 0,
                "media-top-margin": 0
            }],
            'media-col-database': [
                # iso_a4_210x297mm
                {
                    "media-size": {
                        "x-dimension": 21000,
                        "y-dimension": 29700
                    },
                    "media-bottom-margin": 0,
                    "media-left-margin": 0,
                    "media-right-margin": 0,
                    "media-top-margin": 0
                },
                # na_letter_8.5x11in
                {
                    "media-size": {
                        "x-dimension": 21590,
                        "y-dimension": 27940
                    },
                    "media-bottom-margin": 0,
                    "media-left-margin": 0,
                    "media-right-margin": 0,
                    "media-top-margin": 0
                }
            ],
            'media-supported': [
                'iso_a4_210x297mm',
                'na_letter_8.5x11in'
            ],
            'media-size-supported': [
                {
                    "x-dimension": 21000,
                    "y-dimension": 29700
                },
                {
                    "x-dimension": 21590,
                    "y-dimension": 27940
                }
            ],
            'media-bottom-margin-supported': 0,
            'media-left-margin-supported': 0,
            'media-right-margin-supported': 0,
            'media-top-margin-supported': 0,
            'media-ready': [
                'iso_a4_210x297mm',
                'na_letter_8.5x11in'
            ],
            'media-col-ready': [
                # iso_a4_210x297mm
                {
                    "media-size": {
                        "x-dimension": 21000,
                        "y-dimension": 29700
                    },
                    "media-bottom-margin": 0,
                    "media-left-margin": 0,
                    "media-right-margin": 0,
                    "media-top-margin": 0
                },
                # na_letter_8.5x11in
                {
                    "media-size": {
                        "x-dimension": 21590,
                        "y-dimension": 27940
                    },
                    "media-bottom-margin": 0,
                    "media-left-margin": 0,
                    "media-right-margin": 0,
                    "media-top-margin": 0
                }
            ],
        })
        return result

    def validate_job(self, msg: IppMessage) -> IppMessage:
        self.logger.info(f'validate_job')
        result = self._get_default_msg()
        result.operation_attributes['status-message'] = 'successful-ok'
        return result

    def add_job(self, msg: IppMessage) -> IppMessage:
        self.logger.info(f'add_job')
        if 'job-name' not in msg.operation_attributes:
            msg.operation_attributes['job-name'] = f'job{time.time()}'
        job = Job.from_attributes(msg.operation_attributes['job-name'],
                                  msg.operation_attributes.get('document-format', 'application/pdf'),
                                  msg.jobs[0] if len(msg.jobs) > 0 else None)
        job.set_document(msg.data)
        self.queue.add_job(job)
        result = self._get_default_msg()
        result.operation_attributes['status-message'] = 'successful-ok'
        result.jobs.append({
            'job-uri': f'{self.base_uri}/jobs/{job.id}',
            'job-id': job.id,
            'job-state': IppJobState.PENDING.value,
            'job-state-reasons': ['job-restartable', 'none'],  # see 4.3.8
        })
        return result

    def _job_attributes(self, job: Job, required_attrs: list[str] | None = None) -> dict:
        result = {
            'job-uri': f'{self.base_uri}/jobs/{job.id}',
            'job-id': job.id,
            'job-name': job.name,
            'job-state': job.state.value,
            'job-impressions-completed': 1 if job.state == IppJobState.COMPLETED else 0,
            'job-media-sheets-completed': 1 if job.state == IppJobState.COMPLETED else 0,
            'job-state-reasons': ['job-restartable', 'none'],  # see 4.3.8
        }
        if required_attrs:
            for attr in required_attrs:
                if attr not in result and attr in job.attributes:
                    result[attr] = job.attributes[attr]
                if attr not in result: print('MISSING:', attr)
        return result

    def get_jobs(self, msg: IppMessage) -> IppMessage:
        show_completed = msg.operation_attributes.get('which-jobs', 'non-completed') == 'non-completed'
        attrs = msg.operation_attributes.get('requested-attributes', None)
        self.logger.info(f'get_jobs {msg.operation_attributes}')

        result = self._get_default_msg()
        for job in self.queue.jobs:
            job_complete = job.state in (IppJobState.COMPLETED, IppJobState.CANCELED, IppJobState.ABORTED)
            if job_complete == show_completed:
                result.jobs.append(self._job_attributes(job, attrs))
        return result

    def get_job_attributes(self, msg: IppMessage) -> IppMessage:
        job_id = msg.operation_attributes['job-id']  # might also be job-uri
        attrs = msg.operation_attributes.get('requested-attributes', None)
        result = self._get_default_msg()
        self.logger.info(f'get_job_attributes {job_id} {attrs}')

        job = self.queue.by_id(job_id)
        if not job:
            self.logger.warning('JOB NOT FOUND', job_id)
            result.status_code = IppStatus.ERROR_NOT_FOUND.value
            return result

        result.jobs.append(self._job_attributes(job, attrs))
        return result

    def cancel_job(self, msg: IppMessage) -> IppMessage:
        job_id = msg.operation_attributes['job-id']  # might also be job-uri
        self.logger.info(f'cancel_job {job_id}')
        result = self._get_default_msg()

        job = self.queue.by_id(job_id)
        if not job:
            self.logger.warning('JOB NOT FOUND CANCEL', job_id)
            result.status_code = IppStatus.ERROR_NOT_FOUND.value
            return result

        self.queue.cancel(job)
        return result
