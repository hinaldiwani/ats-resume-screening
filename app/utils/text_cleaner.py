"""app/utils/text_cleaner.py"""
import re


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", raw_text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
