from pathlib import Path
import json
import csv
from pypdf import PdfReader
from docx import Document

def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    
    if suffix == ".csv":
        return _extract_csv(file_path)

    if suffix == ".txt":
        return _extract_txt(file_path)

    if suffix == ".docx":
        return _extract_docx(file_path)

    if suffix == ".json":
        return _extract_json(file_path)

    raise ValueError(f"Unsupported file type: {suffix}")

def _extract_pdf(path: Path) -> str:
    reader = PdfReader(path)
    pages = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    return "\n".join(pages)

def _extract_csv(path: Path) -> str:
    rows = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            # skip completely empty rows
            if not any(cell.strip() for cell in row):
                continue

            # join columns in a readable way
            rows.append(" | ".join(cell.strip() for cell in row))

    return "\n".join(rows)

def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_json(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return json.dumps(data, indent=2)
