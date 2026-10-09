"""Render the actual generated PDF locally; no external preview service."""
from io import BytesIO


def render_pdf_page(pdf_bytes: bytes, page_index: int, scale: float = 1.5) -> bytes:
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(pdf_bytes) as document:
        if not 0 <= page_index < len(document):
            raise ValueError("Page outside document")
        page = document[page_index]
        bitmap = page.render(scale=scale)
        try:
            output = BytesIO()
            bitmap.to_pil().save(output, format="PNG")
            return output.getvalue()
        finally:
            bitmap.close()
            page.close()
