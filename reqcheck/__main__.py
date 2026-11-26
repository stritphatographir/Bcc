import argparse
from pathlib import Path


def parser():
    result = argparse.ArgumentParser(description="Агент проверки требований")
    result.add_argument("input", type=Path, help="Входной документ")
    result.add_argument("-o", "--output", type=Path, required=True, help="Файл отчёта")
    return result


def main():
    args = parser()
    args.parse_args()
    args.error("Обработка документов ещё не подключена.")


if __name__ == "__main__":
    main()
