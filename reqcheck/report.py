import json
import re
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt

from .clarifier import LABEL, PRIORITY, finding_id
from .findings import Finding
from .pipeline import Analysis
from .quality import Quality


def literal(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>()#+.!|~&-])", r"\\\1", " ".join(text.split()))


def finding_lines(identifier: str, finding: Finding) -> list[str]:
    confidence = f" · согласие {finding.confidence:.0%}" if finding.confidence is not None else ""
    return [
        f"**{identifier} · {literal(finding.criterion)} · {LABEL[finding.severity]}{confidence}**",
        "",
        *[f"> **{literal(e.locator)}** · {literal(e.quote)}" for e in finding.evidence],
        "",
        f"- Дефект — {literal(finding.explanation)}",
        f"- Правка — {literal(finding.fix)}",
        "",
    ]


def critical_category(finding: Finding) -> str:
    criterion = finding.criterion.casefold()
    if finding.code == "http-get-write" or re.search(r"согласован|противореч|consisten|conflict", criterion):
        return "Противоречивые"
    if re.search(r"полн|пропуск|complet", criterion):
        return "Неполные"
    if re.search(r"проверяем|однознач|измерим|verif|ambigu|testab", criterion):
        return "Непроверяемые"
    return "Другие критические дефекты"


def render_markdown(result: Analysis) -> str:
    p = result.passport
    out = [
        "# Отчёт о проверке требований", "", "## Паспорт прогона", "",
        f"- Документ — {literal(p.document)}",
        f"- Начало — {p.started:%Y-%m-%d %H:%M:%S UTC}",
        f"- Окончание — {p.finished:%Y-%m-%d %H:%M:%S UTC}",
        f"- Модель — {literal(p.model)}",
        f"- Провайдер — {literal(p.provider)}",
        f"- Версия агента — {literal(p.version)}",
        f"- SHA-256 документа — `{p.sha256}`",
        f"- Запросы к модели — {p.calls}",
        f"- Ответы из кэша — {p.cache_hits}",
        f"- Отклонённые выводы без подтверждённых цитат — {p.dropped}",
        f"- Режим — {p.mode}",
    ]
    if p.failed_agents:
        out.append("- Проверки без ответа — " + literal(", ".join(p.failed_agents)))

    out.extend(["", "## Выделенные требования", "",
                "| ID в отчёте | ID в документе | Краткая формулировка |",
                "| --- | --- | --- |"])
    for requirement in result.requirements:
        formulation = literal(requirement.quote)
        if not requirement.document_id:
            formulation += " · " + literal(requirement.source.locator)
        out.append(f"| {requirement.id} | {literal(requirement.document_id or '—')} | "
                   f"{formulation} |")
    individual = defaultdict(list)
    set_findings = []
    for index, finding in enumerate(result.findings):
        entry = (finding_id(index), finding)
        if finding.scope == "requirement":
            for identifier in finding.requirements:
                individual[identifier].append(entry)
        else:
            set_findings.append(entry)

    out.extend(["", "## Проверка каждого требования", ""])
    for requirement in result.requirements:
        section = " › ".join(requirement.source.section)
        out.extend([f"### {requirement.id}", "",
                    f"{literal(section)} · {literal(requirement.source.locator)}", ""])
        tagged = individual[requirement.id]
        if tagged:
            for identifier, finding in tagged:
                out.extend(finding_lines(identifier, finding))
        else:
            out.extend(["В выполненных проверках подтверждённых дефектов нет.", ""])

    out.extend(["## Проверка набора требований", ""])
    for identifier, finding in set_findings:
        if finding.requirements:
            out.extend(["Связанные требования — " + ", ".join(finding.requirements), ""])
        out.extend(finding_lines(identifier, finding))
    if not set_findings:
        out.extend(["В выполненных проверках набора подтверждённых дефектов нет.", ""])

    if result.simulation.scenarios:
        out.extend(["## Моделирование сценариев", "",
                    f"Правил со сверенными цитатами — {len(result.simulation.rules)}. "
                    f"Отклонено записей таблицы — {result.simulation.dropped}.", "",
                    "| Сценарий | Условия | Результат |", "| --- | --- | --- |"])
        states = {"covered": "Покрыт", "conflict": "Противоречие", "uncovered": "Нет результата"}
        for scenario in result.simulation.scenarios:
            facts = json.dumps(scenario.facts, ensure_ascii=False)
            source = f" · {scenario.evidence.locator}" if scenario.evidence else " · синтетический"
            out.append(f"| {literal(scenario.label + source)} | {literal(facts)} | {states[scenario.status]} |")
        out.append("")

    counts = Counter(f.severity for f in result.findings)
    ranked = sorted(enumerate(result.findings), key=lambda row: PRIORITY[row[1].severity])
    out.extend(["## Сводка", "",
                f"- Требований — {len(result.requirements)}",
                f"- Нарушений — {len(result.findings)}",
                *[f"- {label.capitalize()} уровень — {counts[key]}" for key, label in LABEL.items()],
                "", "### Критические дефекты", ""])
    critical = defaultdict(list)
    for index, finding in ranked:
        if finding.severity == "critical":
            critical[critical_category(finding)].append((index, finding))
    for category, entries in critical.items():
        out.extend([f"#### {category}", ""])
        for index, finding in entries:
            out.append(f"- **{finding_id(index)}** · {literal(finding.explanation)}")
            out.extend(f"  - {literal(e.locator)} · «{literal(e.quote)}»" for e in finding.evidence)
        out.append("")
    if not critical:
        out.extend(["Подтверждённых критических дефектов в выполненных проверках нет.", ""])

    out.extend(["## Уточняющие вопросы", ""])
    grouped = defaultdict(list)
    by_id = {finding_id(index): finding for index, finding in enumerate(result.findings)}
    for item in result.questions:
        grouped[item.stakeholder].append(item)
    for stakeholder, items in grouped.items():
        out.extend([f"### {stakeholder}", ""])
        for item in items:
            out.append(f"- **{item.id} · {LABEL[item.priority]}** · {literal(item.text)} "
                       f"({', '.join(item.finding_ids)})")
            quotes = dict.fromkeys(
                (e.locator, e.quote)
                for ref in item.finding_ids if ref in by_id for e in by_id[ref].evidence
            )
            out.extend(f"  - {literal(locator)} · «{literal(quote)}»" for locator, quote in quotes)
        out.append("")
    if not grouped:
        out.extend(["Вопросов по подтверждённым дефектам нет.", ""])

    if result.answers:
        out.extend(["## Ответы и повторная проверка", ""])
        for answer in result.answers:
            out.append(f"- **{answer.question.id}** · {literal(answer.question.text)} "
                       f"— {literal(answer.text)}")
        out.append("")
        for index, finding in enumerate(result.follow_up, 1):
            out.extend(finding_lines(f"U-{index:03}", finding))

    out.extend(["", "## Вердикт", ""])
    if counts["critical"] or counts["major"]:
        out.append("Полную разработку и тестирование следует начинать после устранения дефектов, влияющих на поведение и приёмку.")
    elif p.failed_agents or not result.requirements:
        out.append("Для решения о начале разработки и тестирования требуется полная проверка документа.")
    else:
        out.append("Разработку и проектирование тестов можно начинать по проверенным требованиям.")
    if ranked:
        out.extend(["", "Первоочередные правки", ""])
        for index, finding in ranked[:3]:
            out.append(f"- **{finding_id(index)}** · {literal(finding.fix)}")

    if result.quality.requirements:
        quality = result.quality
        out.extend(["", "## Показатели качества", "",
                    f"Индекс по найденным дефектам — {quality.score} из 100.",
                    "Штраф на требование по критерию — 40 за критический дефект, "
                    "15 за существенный, 5 за незначительный. Учитывается наибольший штраф.",
                    "Нулевое число нарушений у критерия показывает результат проведённых проверок.", ""])
        if quality.partial:
            out.extend(["Индекс предварительный. Часть проверок недоступна.", ""])
        out.extend(["| Критерий ISO 29148 | Требований с нарушением |", "| --- | --- |"])
        for criterion, count in quality.affected_criteria.items():
            out.append(f"| {criterion} | {count} |")
        out.extend(["", "| Требование | Балл из 100 |", "| --- | --- |"])
        for requirement, score in quality.requirements.items():
            out.append(f"| {requirement} | {score} |")

    if result.qa.trace:
        out.extend(["", "## Сценарии тестирования", ""])
        kinds = {"positive": "Позитивный", "negative": "Негативный", "boundary": "Граничный"}
        for case in result.qa.tests:
            out.extend([f"### {case.id} · {kinds[case.kind]}", "",
                        "Требования — " + ", ".join(case.requirements), "",
                        *["    " + line for line in case.gherkin.splitlines()], ""])
        if result.qa.uncovered:
            out.extend(["Нет проверяемого результата в таблице решений для требований:", "",
                        ", ".join(result.qa.uncovered), ""])
        out.extend(["## Матрица трассировки", "",
                    "| Цель | Требование | Приёмка | API или данные | Тесты |",
                    "| --- | --- | --- | --- | --- |"])
        for row in result.qa.trace:
            cells = [row.goal or "—", row.requirement, ", ".join(row.acceptance) or "—",
                     ", ".join(row.contracts) or "—", ", ".join(row.tests) or "—"]
            out.append("| " + " | ".join(literal(value) for value in cells) + " |")
        if result.qa.rewrites:
            out.extend(["", "## Предлагаемые правки", "",
                        "Проект для согласования с владельцем требований.", ""])
            for patch in result.qa.rewrites:
                out.extend([f"### {patch.requirement}", "",
                            f"{literal(patch.locator)} · {', '.join(patch.findings)}", "",
                            *["    " + line for line in patch.diff.splitlines()], ""])
    return "\n".join(out).rstrip() + "\n"


STYLE = """
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#142b29;background:#f2f6f4}
body{max-width:1020px;margin:0 auto;padding:2rem 1rem}
article{background:white;padding:clamp(1rem,4vw,3rem);border:1px solid #c9dbd4;border-radius:12px}
h1,h2,h3{line-height:1.2}h2{margin-top:2rem;border-top:1px solid #d9e6e1;padding-top:1rem}
p,li,td,th{line-height:1.55;overflow-wrap:anywhere}
table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #d9e6e1;padding:.5rem}
th{background:#e9f3ee}blockquote{margin:1rem 0;padding:.3rem .9rem;border-left:3px solid #187967;background:#edf5f1}
.quality{display:grid;gap:.45rem;margin-block:1.4rem;padding:1rem;border:1px solid #c9dbd4}
meter{width:min(100%,30rem);height:1.25rem}
.quality dl{display:grid;grid-template-columns:minmax(10rem,1fr) minmax(4rem,2fr);gap:.3rem .65rem;margin:0}
.quality dd{margin:0}
"""


def render_html(markdown: str, quality: Quality | None = None) -> str:
    content = MarkdownIt("commonmark", {"html": False}).enable("table").render(markdown)
    if quality and quality.score is not None:
        states = {"blocked": "Сначала устранить блокирующие дефекты",
                  "incomplete": "Нужна полная проверка", "ready": "Можно начать разработку и тестирование"}
        maximum = max(1, len(quality.requirements))
        rows = "".join(
            f'<dt>{escape(name)}</dt><dd><meter aria-label="{escape(name)}" min="0" max="{maximum}" value="{count}">'
            f'{count}</meter> {count}</dd>'
            for name, count in quality.affected_criteria.items()
        )
        block = (f'<section class="quality" aria-label="Показатели качества"><strong>{states[quality.readiness]}</strong>'
                 f'<label for="quality-score">Индекс по найденным дефектам — {quality.score} из 100</label>'
                 f'<meter id="quality-score" min="0" max="100" value="{quality.score}">{quality.score}</meter>'
                 f"<dl>{rows}</dl></section>")
        content = content.replace("<h2>Показатели качества</h2>", "<h2>Показатели качества</h2>" + block, 1)
    return (
        '<!doctype html><html lang="ru"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Отчёт о проверке требований</title><style>{STYLE}</style>'
        f'<body><article>{content}</article></body></html>'
    )


def write(result: Analysis, output: Path) -> tuple[Path, Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    html, data = output.with_suffix(".html"), output.with_suffix(".json")
    if output in {html, data}:
        raise ValueError("Укажите файл Markdown для параметра --output.")
    markdown = render_markdown(result)
    output.write_text(markdown, encoding="utf-8")
    html.write_text(render_html(markdown, result.quality), encoding="utf-8")
    data.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output, html, data
