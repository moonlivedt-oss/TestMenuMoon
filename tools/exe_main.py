"""Точка входа собранной студии (TestMenuStudio.exe, см. tools/build_exe.py).

TestMenuStudio.exe                  студия
TestMenuStudio.exe --tm deploy 3    команда tm.py (так студия запускает пайплайн в .exe)
TestMenuStudio.exe --py script.py … любой Python-скрипт встроенным интерпретатором (unrpyc)
"""

import os
import runpy
import sys


def _console():
    """У оконного .exe нет консоли: sys.stdout = None. Если родитель (студия) дал канал —
    пишем в него, иначе вывод молча пропадает, а не роняет команду."""
    for fd, name in ((1, "stdout"), (2, "stderr")):
        if getattr(sys, name) is None:
            try:
                os.fstat(fd)
                setattr(sys, name, open(fd, "w", encoding="utf-8", errors="replace", closefd=False))
            except OSError:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


def main():
    args = sys.argv[1:]
    if args[:1] == ["--tm"]:
        _console()
        import tm

        sys.exit(tm.main(args[1:]))
    if args[:1] == ["--py"] and len(args) > 1:
        _console()
        script = os.path.abspath(args[1])
        sys.argv = [script] + args[2:]
        sys.path.insert(0, os.path.dirname(script))
        runpy.run_path(script, run_name="__main__")
        return
    from tmstudio.window import main as studio

    studio()


if __name__ == "__main__":
    main()
