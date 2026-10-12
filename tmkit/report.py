#!/usr/bin/env python3
"""Единый аккуратный вывод для CLI-скриптов.

Статусные строки — в общем формате `game_{i}: [MARK] текст`, чтобы вывод всего
пайплайна читался одинаково. Маркеры:
  [OK] успех | [X] ошибка/проблема | [?] неясно/пропуск | [!] предупреждение.
Подпункты (детали) — с отступом через detail().

bad()/err() считаются проблемами: exit_code() даёт по ним код возврата процесса,
чтобы студия и скрипты видели провал, а не вечный «код 0».
"""

OK, BAD, WARN, NOTE = "[OK]", "[X]", "[?]", "[!]"

_problems = 0


def line(i, text, mark=""):
    body = f"{mark} {text}" if mark else text
    print(f"game_{i}: {body}")


def _problem():
    global _problems
    _problems += 1


def ok(i, text):
    line(i, text, OK)


def bad(i, text):
    _problem()
    line(i, text, BAD)


def warn(i, text):
    line(i, text, WARN)


def note(i, text):
    line(i, text, NOTE)


def info(i, text):
    line(i, text)  # нейтральная инфо-строка (без маркера)


def err(i, text):
    _problem()
    line(i, f"ERROR {text}")  # необработанное исключение


def detail(text):
    """Подпункт под статусной строкой (с отступом)."""
    print("     " + text)


def exit_code():
    """Код возврата процесса: 1, если были bad()/err(), иначе 0."""
    return 1 if _problems else 0
