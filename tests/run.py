#!/usr/bin/env python3
"""Запуск всех тестов без сторонних зависимостей:  python tests/run.py [часть имени теста]

Тесты — функции test_* в tests/test_*.py (совместимы с pytest). Каждый файл — своя тема:
manifest (манифест, генерация, CLI), renpy (меню Ren'Py, установка, анализ), engines
(остальные движки и веб-ядро), saves (редактор сохранений), studio (GUI, нужен PyQt6).
"""

import glob
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main(argv):
    only = argv[1] if len(argv) > 1 else ""
    passed = failed = 0
    for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        mod = importlib.import_module(os.path.splitext(os.path.basename(path))[0])
        tests = sorted(
            (n, f)
            for n, f in vars(mod).items()
            if n.startswith("test_") and callable(f)
        )
        for name, fn in tests:
            if only and only not in name:
                continue
            try:
                fn()
                print(f"  PASS  {mod.__name__}.{name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {mod.__name__}.{name}: {type(e).__name__}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
