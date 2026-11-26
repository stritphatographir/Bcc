import argparse
from pathlib import Path


def parser():
    result = argparse.ArgumentParser(description="Агент проверки требований")
    result.add_argument("input", type=Path, help="Входной документ")
    result.add_argument("-o", "--output", type=Path, required=True, help="Файл отчёта")
    result.add_argument("--interactive", action="store_true", help="Задать уточняющие вопросы в терминале")
    return result


def main():
    import sys

    from .clarifier import terminal_answers
    from .config import Settings
    from .pipeline import analyze
    from .report import write

    command = parser()
    args = command.parse_args()
    destinations = {args.output, args.output.with_suffix(".html"), args.output.with_suffix(".json"),
                    args.output.with_suffix(".trace.jsonl")}
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
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
