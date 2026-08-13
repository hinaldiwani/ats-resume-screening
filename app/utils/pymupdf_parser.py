"""
app/utils/pymupdf_parser.py

Primary PDF text extraction via PyMuPDF (imported as `fitz`), per the
project's tech stack. This is the default PDF parser; pdfplumber
(app/utils/pdf_parser.py) is kept as a fallback for the rare PDF that
PyMuPDF extracts poorly from — resume_parser_service.py tries this module
first and only falls back if it returns empty or near-empty text.
"""

import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts all text from a PDF, page by page, joined with newlines, using
    PyMuPDF. Returns an empty string if no text layer is found (e.g. a
    scanned image with no OCR layer) — callers should treat an empty result
    as a signal to try the pdfplumber fallback.
    """
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            page_text = page.get_text("text")
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())
    return "\n".join(text_parts)
