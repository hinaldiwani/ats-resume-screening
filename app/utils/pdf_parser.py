"""
app/utils/pdf_parser.py

Text extraction from PDF files via pdfplumber. Isolated from DOCX handling
so each parser can be swapped/upgraded (e.g. OCR fallback) independently.
"""

import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts all text from a PDF, page by page, joined with newlines.
    Returns an empty string if the PDF has no extractable text (e.g. a
    scanned image with no OCR layer) — callers should treat an empty
    result as a signal to fall back to OCR in a future iteration.
    """
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)
