import os
from pypdf import PdfReader
from docx import Document


def load_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def load_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def load_document(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    loaders = {
        ".txt": load_txt,
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".doc": load_docx,
    }
    loader = loaders.get(ext)
    if loader is None:
        raise ValueError(f"不支持的文件格式: {ext}，支持 .txt / .pdf / .docx")
    return loader(file_path)
