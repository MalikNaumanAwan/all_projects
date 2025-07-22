from PyPDF2 import PdfReader

def parse_pdf(path: str) -> str:
    reader = PdfReader(path)
    text = "\n".join([page.extract_text() or "" for page in reader.pages])
    return text
