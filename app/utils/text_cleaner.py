"""
app/utils/text_cleaner.py

Normalizes raw extracted text before it's stored or parsed further:
collapses repeated whitespace, strips control characters that sometimes
leak through PDF extraction, and trims each line.
"""

import re


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    # Strip non-printable/control characters except newlines and tabs.
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", raw_text)

    # Collapse runs of spaces/tabs, but keep line breaks meaningful.
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)
