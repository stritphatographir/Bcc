import argparse
from pathlib import Path


def parser():
    result = argparse.ArgumentParser(
        description="Агент проверки требований",
        epilog="Подкоманды: reqcheck diff --help, reqcheck export --help.",
    )
    result.add_argument("input", type=Path, help="Входной документ")
    result.add_argument("-o", "--output", type=Path, required=True, help="Файл отчёта")
    result.add_argument("--interactive", action="store_true", help="Задать уточняющие вопросы в терминале")
    return result


def main():
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    if sys.argv[1:2] == ["diff"]:
        from .config import Settings
        from .diff import render_diff
        from .pipeline import Analysis, analyze

        command = argparse.ArgumentParser(prog="reqcheck diff", description="Сравнение дефектов двух версий")
        command.add_argument("old", type=Path)
        command.add_argument("new", type=Path)
        command.add_argument("-o", "--output", type=Path)
        args = command.parse_args(sys.argv[2:])
        if args.output and args.output.resolve() in {args.old.resolve(), args.new.resolve()}:
            command.error("Файл сравнения совпадает с входным документом.")

        def review(path):
            if path.suffix.lower() == ".json":
                return Analysis.model_validate_json(path.read_bytes())
            return analyze(path, Settings.from_env(), progress=lambda stage: print(stage, file=sys.stderr))

        try:
            comparison = render_diff(review(args.old), review(args.new))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(comparison, encoding="utf-8")
            else:
                print(comparison, end="")
        except (ValueError, OSError) as exc:
            command.error(str(exc))
        return

    if sys.argv[1:2] == ["export"]:
        from .exports import export
        from .pipeline import Analysis

        command = argparse.ArgumentParser(prog="reqcheck export", description="Экспорт отчёта в DOCX, PDF и Jira")
        command.add_argument("report", type=Path)
        command.add_argument("-o", "--output", type=Path, required=True, help="Путь и имя без расширения")
        args = command.parse_args(sys.argv[2:])
        try:
            result = Analysis.model_validate_json(args.report.read_bytes())
            for path in export(result, args.output):
                print(path)
        except (ValueError, OSError) as exc:
            command.error(str(exc))
        return

    from .clarifier import terminal_answers
    from .config import Settings
    from .pipeline import analyze
    from .report import write

    command = parser()
    args = command.parse_args()
    destinations = {args.output, args.output.with_suffix(".html"), args.output.with_suffix(".json"),
                    args.output.with_suffix(".trace.jsonl"), args.output.with_suffix(".pdf")}
    if args.input.resolve() in {path.resolve() for path in destinations}:
        command.error("Входной файл совпадает с одним из файлов отчёта.")
    try:
        options = {"collect": terminal_answers} if args.interactive else {}
        result = analyze(
            args.input, Settings.from_env(),
            progress=lambda stage: print(stage, file=sys.stderr, flush=True), **options,
        )
        paths = write(result, args.output)
    except (ValueError, OSError) as exc:
        command.error(str(exc))
    try:
        from .exports import _pdf

        pdf = args.output.with_suffix(".pdf")
        _pdf(args.output.read_text(encoding="utf-8"), pdf)
        paths = (*paths, pdf)
    except Exception as exc:  # PDF is a convenience copy; the Markdown report is the deliverable
        print(f"PDF не создан: {exc}", file=sys.stderr)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
