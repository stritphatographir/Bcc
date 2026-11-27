import csv
import json
from pathlib import Path

from docx import Document
from docx.shared import Inches
from markdown_it import MarkdownIt

from .clarifier import finding_id
from .pipeline import Analysis
from .report import render_markdown

FONTS = Path(__file__).with_name("fonts")


def _pdf(markdown: str, path: Path) -> None:
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import LongTable, Paragraph, Preformatted, SimpleDocTemplate, Spacer, TableStyle

    for name, file in (("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
    body = ParagraphStyle("body", fontName="DejaVu", fontSize=9, leading=12, spaceAfter=4)
    cell = ParagraphStyle("cell", parent=body, fontSize=7.5, leading=9.5, spaceAfter=0)
    quote = ParagraphStyle("quote", parent=body, leftIndent=10, textColor=colors.HexColor("#1f4e79"))
    heads = {level: ParagraphStyle(f"h{level}", parent=body, fontName="DejaVu-Bold",
                                   fontSize=size, leading=size * 1.3, spaceBefore=8, spaceAfter=5)
             for level, size in ((1, 16), (2, 13), (3, 11), (4, 10), (5, 9), (6, 9))}
    width = A4[0] - 3 * cm
    story, table, row, level, inside_quote = [], None, [], None, False
    for token in MarkdownIt("commonmark", {"html": False}).enable("table").parse(markdown):
        if token.type == "heading_open":
            level = int(token.tag[1:])
        elif token.type == "blockquote_open":
            inside_quote = True
        elif token.type == "blockquote_close":
            inside_quote = False
        elif token.type == "table_open":
            table = []
        elif token.type == "tr_open":
            row = []
        elif token.type == "tr_close":
            table.append(row)
        elif token.type == "table_close":
            columns = max(len(r) for r in table)
            grid = LongTable([r + [""] * (columns - len(r)) for r in table],
                             colWidths=[width / columns] * columns, repeatRows=1)
            grid.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde7f3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story += [grid, Spacer(1, 6)]
            table = None
        elif token.type == "inline":
            plain = "".join(child.content if child.type != "softbreak" else "\n"
                            for child in token.children or [])
            text = escape(plain).replace("\n", "<br/>")
            if table is not None:
                row.append(Paragraph(text, cell))
            elif level is not None:
                story.append(Paragraph(text, heads[level]))
                level = None
            else:
                story.append(Paragraph(text, quote if inside_quote else body))
        elif token.type in {"code_block", "fence"}:
            story.append(Preformatted(token.content.rstrip(), cell))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                      topMargin=1.5 * cm, bottomMargin=1.5 * cm, title="Отчёт reqcheck").build(story)


def _issues(result: Analysis):
    priorities = {"critical": "Highest", "major": "High", "minor": "Low"}
    for number, finding in enumerate(result.findings):
        ref = finding_id(number)
        evidence = "\n".join(f"{e.locator} — {e.quote}" for e in finding.evidence)
        yield {
            "Issue Type": "Bug", "Summary": f"{ref} · {finding.criterion}: {finding.explanation}"[:255],
            "Description": f"{result.passport.document}\n\n{evidence}\n\n{finding.explanation}\n\n"
                           f"Правка — {finding.fix}\nВопрос — {finding.question}",
            "Priority": priorities[finding.severity], "Labels": "reqcheck",
            "External issue ID": ref,
        }


def _docx(markdown: str) -> Document:
    document = Document()
    section = document.sections[0]
    section.left_margin = section.right_margin = Inches(0.75)
    table = None
    row = []
    alignment = None
    for token in MarkdownIt("commonmark", {"html": False}).enable("table").parse(markdown):
        if token.type == "heading_open":
            alignment = int(token.tag[1:])
        elif token.type == "table_open":
            table = []
        elif token.type == "tr_open":
            row = []
        elif token.type == "tr_close":
            table.append(row)
        elif token.type == "table_close":
            grid = document.add_table(rows=0, cols=len(table[0]))
            grid.style = "Light Shading Accent 1"
            for values in table:
                cells = grid.add_row().cells
                for cell, value in zip(cells, values):
                    cell.text = value
            table = None
        elif token.type == "inline":
            plain = "".join(child.content if child.type != "softbreak" else "\n"
                            for child in token.children or [])
            if table is not None:
                row.append(plain)
            elif alignment is not None:
                document.add_heading(plain, level=0 if alignment == 1 else alignment - 1)
                alignment = None
            else:
                document.add_paragraph(plain)
        elif token.type in {"code_block", "fence"}:
            document.add_paragraph(token.content.rstrip())
    return document


def export(result: Analysis, prefix: Path) -> tuple[Path, Path, Path, Path]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, docx_path, pdf_path = (prefix.with_name(prefix.name + suffix) for suffix in
                                                 (".jira.csv", ".jira.json", ".docx", ".pdf"))
    fields = ["Issue Type", "Summary", "Description", "Priority", "Labels", "External issue ID"]
    issues = list(_issues(result))
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for issue in issues:
            writer.writerow({name: "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
                             for name, value in issue.items()})
    jira = {"issues": [{
        "externalId": row["External issue ID"],
        "fields": {"summary": row["Summary"], "description": row["Description"],
                   "issuetype": {"name": row["Issue Type"]}, "priority": {"name": row["Priority"]},
                   "labels": [row["Labels"]]},
    } for row in issues]}
    json_path.write_text(json.dumps(jira, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(result)
    _docx(markdown).save(docx_path)
    _pdf(markdown, pdf_path)
    return csv_path, json_path, docx_path, pdf_path
