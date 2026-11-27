import re
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pydantic import BaseModel
from pypdf import PdfReader


class Source(BaseModel):
    locator: str
    text: str
    section: tuple[str, ...] = ()
    heading: bool = False


def _blocks(path):
    extension = path.suffix.lower()
    if extension in {".md", ".txt"}:
        block = path.read_text(encoding="utf-8-sig")
        for number, line in enumerate(block.splitlines(), 1):
            yield f"строка {number}", line
    elif extension == ".pdf":
        for page_number, page in enumerate(PdfReader(path).pages, 1):
            for number, line in enumerate((page.extract_text() or "").splitlines(), 1):
                yield f"страница {page_number}, строка {number}", line
    elif extension == ".docx":
        doc = Document(path)
        for number, block in enumerate(doc.element.body, 1):
            if block.tag.endswith("}p"):
                paragraph = Paragraph(block, doc)
                heading = re.fullmatch(r"Heading (\d)", paragraph.style.name)
                prefix = "#" * int(heading[1]) + " " if heading else ""
                yield f"абзац {number}", prefix + paragraph.text
            elif block.tag.endswith("}tbl"):
                for row_number, row in enumerate(Table(block, doc).rows, 1):
                    text = " | ".join(" ".join(cell.text.split()) for cell in row.cells)
                    yield f"таблица в блоке {number}, строка {row_number}", f"| {text} |"
    elif extension in {".html", ".htm"}:
        soup = BeautifulSoup(path.read_text(encoding="utf-8-sig"), "html.parser")
        for element in soup(["script", "style", "template"]):
            element.decompose()
        tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "tr", "pre"]
        for number, block in enumerate(soup.find_all(tags), 1):
            if block.find_parent(["tr", "li", "pre"]):
                continue
            if block.name == "tr":
                text = " | ".join(cell.get_text(" ", strip=True) for cell in block.find_all(["td", "th"], recursive=False))
                text = f"| {text} |"
            else:
                text = block.get_text(" ", strip=True)
                if re.fullmatch(r"h[1-6]", block.name):
                    text = "#" * int(block.name[1]) + " " + text
            yield f"HTML, блок {number}", text
    else:
        raise ValueError(f"Формат {extension or 'без расширения'} не поддерживается.")


def unread_pages(path: Path) -> list[int]:
    """PDF pages without extractable text (scans, images): they are not checked and must be reported."""
    if path.suffix.lower() != ".pdf":
        return []
    return [number for number, page in enumerate(PdfReader(path).pages, 1)
            if not (page.extract_text() or "").strip()]


def load(path: Path) -> list[Source]:
    result = []
    sections: list[tuple[int, str]] = []
    for locator, raw in _blocks(path):
        text = raw.strip()
        if not text:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", text)
        if heading:
            level = len(heading[1])
            while sections and sections[-1][0] >= level:
                sections.pop()
            sections.append((level, heading[2]))
        result.append(Source(
            locator=locator, text=text, section=tuple(title for _, title in sections),
            heading=bool(heading),
        ))
    if not result:
        raise ValueError("Текст не найден. Для сканированного PDF сначала выполните OCR.")
    return result
