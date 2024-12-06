import sys
from io import BytesIO

import qrcode
from pypdf import PdfReader, PdfWriter, PageObject

from filters.add_template import write_to_stdout, pdf_input


def image_to_pdf(img) -> PdfReader:
    img_as_pdf = BytesIO()
    img.save(img_as_pdf, "pdf")
    return PdfReader(img_as_pdf)


def text_to_qr(source: PageObject, dest: PageObject) -> None:
    text = source.extract_text().strip()
    if not text:
        dest.merge_page(source)
        return

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)
    pdf_img = image_to_pdf(qr.make_image(fill_color="black", back_color="white")).pages[0]

    border = 30
    sf = min((dest.mediabox.width - 2 * border) / pdf_img.mediabox.width,
             (dest.mediabox.height - 2 * border) / pdf_img.mediabox.height,
             0.75)
    pdf_img.scale(sf, sf)

    dest.merge_translated_page(pdf_img, border, border)


def main(job_id: str, username: str, job_name: str, num_copies: str, options: str, filename: str | None = None) -> None:
    reader = pdf_input(filename)
    writer = PdfWriter()
    for page in reader.pages:
        text_to_qr(page, writer.add_blank_page(page.mediabox.width, page.mediabox.height))
    write_to_stdout(writer)


if __name__ == '__main__':
    main(*sys.argv[1:])
