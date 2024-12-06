import io
import os
import sys
from pathlib import Path

import cups
from pypdf import PdfReader, PdfWriter, PageObject


def write_to_stdout(writer: PdfWriter) -> None:
    f = io.BytesIO()
    writer.write(f)
    sys.stdout.buffer.write(f.getvalue())


def get_templates() -> list[Path]:
    ppd = cups.PPD(os.environ['PPD'])
    template_attr = ppd.findAttr('saarsecFilterTemplate')
    if template_attr is None:
        return []

    result = [Path(template_attr.value)]
    while (template_attr := ppd.findNextAttr('saarsecFilterTemplate')) is not None:
        result.append(Path(template_attr.value))
    return result


def pdf_input(filename: str | None) -> PdfReader:
    if filename is not None:
        return PdfReader(filename)
    else:
        b = sys.stdin.buffer.read()
        # sys.stderr.write(f'read {len(b)} bytes {type(b)}\n')
        # sys.stderr.flush()
        if len(b) == 0:
            # this happens when CUPS/IPP/other filters bug around.
            # not really a solution, but no crashes
            sys.exit(0)
        return PdfReader(io.BytesIO(b))


def main(job_id: str, username: str, job_name: str, num_copies: str, options: str, filename: str | None = None) -> None:
    template_page: PageObject | None = None
    for tmpl in get_templates():
        if not tmpl.exists():
            sys.stderr.write(f'WARNING: File not found ({tmpl})\n')
            sys.stderr.flush()
            continue

        template_reader = PdfReader(tmpl)
        if template_page is None:
            template_page = template_reader.pages[0]
        else:
            template_page.merge_page(template_reader.pages[0], expand=False, over=True)

    reader = pdf_input(filename)
    writer = PdfWriter()
    for page in reader.pages:
        if template_page is not None:
            page.merge_page(template_page, expand=False, over=True)
        writer.add_page(page)
    write_to_stdout(writer)


if __name__ == '__main__':
    main(*sys.argv[1:])
