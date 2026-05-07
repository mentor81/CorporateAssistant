import re
import pdfplumber


def fix_backward_persian(text):
    if not text:
        return ""

    def protect_numbers(line):
        return re.sub(r'[\d۰-۹٠-٩٬,]+', lambda m: f"__NUM_{m.group(0)}__", line)

    def restore_numbers(line):
        return re.sub(r'__NUM_(.*?)__', lambda m: m.group(1), line)

    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        protected = protect_numbers(line)
        reversed_line = protected[::-1]

        def fix_english(match):
            return match.group(0)[::-1]

        fixed_line = re.sub(r'[a-zA-Z0-9\+\/\.#]+', fix_english, reversed_line)
        restored = restore_numbers(fixed_line)
        fixed_lines.append(restored)

    return '\n'.join(fixed_lines)


def extract_pdf_text(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text()
            text += fix_backward_persian(raw) + "\n"
    return text
