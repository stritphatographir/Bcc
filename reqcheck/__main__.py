import argparse
from pathlib import Path


def parser():
    result = argparse.ArgumentParser(description="Агент проверки требований")
    result.add_argument("input", type=Path, help="Входной документ")
    result.add_argument("-o", "--output", type=Path, required=True, help="Файл отчёта")
    result.add_argument("--interactive", action="store_true", help="Задать уточняющие вопросы в терминале")
    return result


def main():
    args = parser()
    args.parse_args()
    args.error("Обработка документов ещё не подключена.")


if __name__ == "__main__":
    main()
