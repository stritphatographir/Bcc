import csv
import json
from pathlib import Path

from docx import Document
from docx.shared import Inches
from markdown_it import MarkdownIt

from .clarifier import finding_id
from .pipeline import Analysis
from .report import render_markdown


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


def export(result: Analysis, prefix: Path) -> tuple[Path, Path, Path]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, docx_path = (prefix.with_name(prefix.name + suffix) for suffix in
                                       (".jira.csv", ".jira.json", ".docx"))
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
    _docx(render_markdown(result)).save(docx_path)
    return csv_path, json_path, docx_path
