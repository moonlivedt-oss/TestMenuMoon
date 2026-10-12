#!/usr/bin/env python3
"""tm — единая точка входа тулкита TestMenuMoon (один скрипт вместо семи).

Тонкая обёртка над пакетом `tmkit`. Примеры:
    python tm.py deploy 3          # разложить меню в game_3
    python tm.py all 3 5           # весь пайплайн для game_3 и game_5
    python tm.py uninstall ALL     # снести меню из всех игр манифеста
    python tm.py list              # игры манифеста: движок + статус установки
    python tm.py quick "D:/Games/X"  # меню в любую игру по пути, без манифеста
    python tm.py library "D:/Games"  # все игры в папке: движок + статус (--install)
    python tm.py saves             # редактор сохранений (нужен PyQt6)
Без номеров команда работает по всем играм манифеста (curate — по реально
распакованным в D:/_ta). Студия (studio.py) запускает эти же команды отдельным процессом.
"""

import argparse, sys

from tmkit.games import GAMES, ROOTS
from tmkit import games as games_mod
from tmkit.paths import ANA_BASE, BUILD, CAND_DIR, ENGINE_SRC, UNRPYC
from tmkit import (
    analysis,
    collect,
    deploy,
    engines,
    generate,
    manifest,
    report,
    validate,
    verify,
)


def _run_each(targets, fn):
    """Прогнать fn(i) по каждой цели, не роняя весь проход на одной игре."""
    for i in targets:
        try:
            fn(i)
        except Exception as e:
            report.err(i, str(e))


# ------------------------------------------------------------- команды
def _renpy_targets(args, pool):
    """Цели команды. Без номеров — только Ren'Py-игры манифеста: у Twine / RPG Maker
    своего collect/deploy нет, и они давали ложное «нет папки игры»."""
    if args.games:
        return args.games
    out = []
    for i in sorted(pool):
        eng = engines.detect_engine(ROOTS.get(i, ""))
        if eng is None or eng.key == "renpy":
            out.append(i)
    return out


def cmd_collect(args):
    _run_each(_renpy_targets(args, ROOTS), collect.collect)


def cmd_curate(args):
    targets = args.games or analysis.extracted_games()
    if not targets:
        print(f"Нет распакованных игр в {ANA_BASE} — сначала  python tm.py collect")
        return
    _run_each(targets, analysis.dump)


def cmd_gen(args):
    _run_each(args.games or sorted(GAMES), generate.gen)


def cmd_deploy(args):
    _run_each(_renpy_targets(args, ROOTS), deploy.deploy)
    # не-Ren'Py игры манифеста раскладываются своим движком (внедрение в HTML)
    if not args.games:
        for i in sorted(GAMES):
            eng = engines.detect_engine(ROOTS.get(i, ""))
            if eng is not None and eng.key != "renpy" and eng.deploy is not None:
                try:
                    report.info(i, f"{eng.key}: {eng.deploy(ROOTS[i])}")
                except Exception as e:
                    report.err(i, f"{eng.key}: {e}")


def cmd_verify(args):
    _run_each(_renpy_targets(args, GAMES), verify.verify)


def cmd_validate(args):
    games, _G, _A = manifest.load_games()
    total = 0
    for i in args.games or sorted(games):
        if i not in games:
            report.warn(i, "нет в манифесте")
            continue
        g = games[i]
        issues = validate.check_game(
            g.get("stats", []), g.get("actions", []), g.get("accent"), g.get("tweak")
        )
        if issues:
            report.bad(i, f"проблем: {len(issues)}")
            for s in issues:
                report.detail(s)
        else:
            report.ok(i, "данные чисты")
        total += len(issues)
    print(f"\nвсего проблем: {total}")


def cmd_uninstall(args):
    if any(g.upper() == "ALL" for g in args.games):
        targets = sorted(GAMES)
    else:
        try:
            targets = [int(g) for g in args.games]
        except ValueError:
            print("номера игр должны быть числами (или ALL)")
            return 2
    _run_each(targets, deploy.uninstall)


def cmd_quick(args):
    """Меню в любую игру по пути — без манифеста. Движок определяется сам:
    Ren'Py, Godot 4, Unity (BepInEx), Unreal (UE4SS), RPG Maker MV/MZ, Twine, HTML5."""
    from tmkit import engines as _engines

    failed = 0
    for path in args.paths:
        try:
            if args.remove:
                eng, _root, msg = _engines.quick_remove_any(path)
            else:
                eng, _root, msg = _engines.quick_install_any(path)
                if "Shift+T" not in msg:
                    msg += f"  (в игре: {_engines.HOTKEYS.get(eng.key, 'Shift+T')})"
            print(f"[OK] {eng.title}: {msg}")
        except Exception as e:  # одна сломанная игра не обрывает установку в остальные
            print(f"[X] {path}: {e}")
            failed += 1
    return 1 if failed else 0


def cmd_library(args):
    """Все игры в папке: движок и состояние меню; --install / --update / --remove — пачкой."""
    from tmkit import library

    found = library.find_games(args.folder, depth=args.depth)
    if not found:
        print(f"игр не найдено: {args.folder}")
        return 1
    failed = 0
    for g in found:
        act = None
        if args.remove and g.status in ("ok", "stale"):
            act = library.remove
        elif args.install and g.status != "ok":
            act = library.install
        elif args.update and g.status == "stale":
            act = library.install
        if act is not None:
            try:
                print(f"     {act(g)}")
                library.refresh(g)
            except Exception as e:  # одна игра не обрывает остальные
                print(f"[X] {g.name}: {e}")
                failed += 1
        mark = {"ok": report.OK, "stale": report.NOTE, "none": "[ ]"}.get(g.status, report.WARN)
        num = f"game_{g.index}" if g.index is not None else ""
        print(f"{mark:4} {g.engine.key:8} {_STATUS.get(g.status, '?'):12} {num:8} {g.name}  ({g.folder})")
    return 1 if failed else 0


def cmd_saves(args):
    """Редактор сохранений (окно PyQt6): файл сейва или выбор игры в окне."""
    try:
        from tmstudio import save_editor
    except ImportError as e:
        print(f"[X] редактору сохранений нужен PyQt6 ({e}):  pip install -r requirements.txt")
        return 1
    return save_editor.main(args.file)


# студия «Весь пайплайн» гоняет ровно этот порядок (collect -> curate -> gen -> deploy)
_PIPELINE = (
    ("collect", collect.collect),
    ("curate", analysis.dump),
    ("gen", generate.gen),
    ("deploy", deploy.deploy),
)


def cmd_all(args):
    targets = _renpy_targets(args, GAMES)
    for label, fn in _PIPELINE:
        print(f"\n=== {label} ===")
        before = report.exit_code()
        _run_each(targets, fn)
        # как в студии: после провалившегося шага дальше не раскладываем
        if report.exit_code() and not before:
            print(f"\n[X] шаг «{label}» с ошибками — пайплайн остановлен")
            return 1


def cmd_list(args):
    """Игры манифеста: индекс, распознанный движок, статус установки, путь."""
    for i in sorted(GAMES):
        g = GAMES[i]
        root = g["root"]
        eng = engines.detect_engine(root)
        ekey = eng.key if eng else "?"
        report.line(
            i,
            f"[{ekey:8}] {g.get('title', ''):24} {_STATUS[_status(i, eng)]:12} {root}",
        )


_STATUS = {"none": "нет", "stale": "устарело", "ok": "установлено"}


def _status(i, eng):
    """'none' | 'stale' | 'ok' для игры манифеста — с учётом движка."""
    root = GAMES[i]["root"]
    if eng is None or eng.key == "renpy":
        return deploy.status_of(i)
    if not (eng.installed and eng.installed(root)):
        return "none"
    return "ok" if (eng.current is None or eng.current(root)) else "stale"


def cmd_doctor(args):
    """Проверка окружения и всех игр манифеста: что мешает пайплайну прямо сейчас."""
    import importlib.util, os

    def env(ok, text, fatal=True):
        print(f"{report.OK if ok else (report.BAD if fatal else report.WARN)} {text}")
        if not ok and fatal:
            report._problem()

    print(f"Python {sys.version.split()[0]}")
    env(os.path.exists(ENGINE_SRC), f"движок: {ENGINE_SRC}")
    env(
        os.path.isdir(deploy.UI_SRC),
        f"UI-тайлы: {deploy.UI_SRC} (без них — прямоугольные фоны)",
        fatal=False,
    )
    env(
        os.path.exists(UNRPYC),
        f"unrpyc: {UNRPYC} (нужен для collect: .rpyc -> .rpy)",
        fatal=False,
    )
    env(
        importlib.util.find_spec("PyQt6") is not None,
        "PyQt6 в этом Python (нужен только студии)",
        fatal=False,
    )
    print(f"     build: {BUILD}\n     анализ: {ANA_BASE}\n     кандидаты: {CAND_DIR}\n")

    for i in args.games or sorted(GAMES):
        if i not in GAMES:
            report.warn(i, "нет в манифесте")
            continue
        g = GAMES[i]
        root = g["root"]
        if not os.path.isdir(root) and not os.path.isfile(root):
            report.warn(i, f"папки игры нет на диске: {root}")
            continue
        eng = engines.detect_engine(root)
        if eng is None:
            report.warn(i, f"движок не распознан: {root}")
            continue
        st = _status(i, eng)
        notes = []
        if eng.key == "renpy":
            issues = validate.check_game(
                g.get("stats", []), g.get("actions", []), g.get("accent"), g.get("tweak")
            )
            if issues:
                notes.append(f"проблем в данных: {len(issues)} (tm.py validate {i})")
            if not (games_mod.launcher(i) and games_mod.python_exe(i)):
                notes.append("нет python/launcher — lint недоступен")
            if not g.get("stats"):
                notes.append("статы не заданы")
        text = f"[{eng.key}] {_STATUS[st]}" + ("".join("; " + n for n in notes))
        if st == "ok" and not notes:
            report.ok(i, text)
        elif st == "stale":
            report.note(i, text + f"  ->  python tm.py deploy {i}")
        else:
            report.warn(i, text)


# ------------------------------------------------------------- парсер
def build_parser():
    p = argparse.ArgumentParser(
        prog="tm.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True, metavar="команда")

    # родитель для команд, принимающих номера игр
    targets = argparse.ArgumentParser(add_help=False)
    targets.add_argument(
        "games",
        nargs="*",
        type=int,
        metavar="N",
        help="номера игр; без аргументов — все из манифеста",
    )

    specs = [
        ("collect", "распаковать .rpa + декомпилировать .rpyc (в D:/_ta)", cmd_collect),
        ("curate", "собрать кандидатов статов/инвентаря (в D:/_ta/cand)", cmd_curate),
        ("gen", "сгенерировать data-файлы из манифеста (в build/)", cmd_gen),
        ("deploy", "разложить движок+data по играм (+ снос старых .rpyc)", cmd_deploy),
        ("verify", "проверка установки + Ren'Py lint (у больших игр долгий)", cmd_verify),
        (
            "validate",
            "офлайн-проверка данных (код действий, дубли, метки)",
            cmd_validate,
        ),
        ("all", "весь пайплайн: collect -> curate -> gen -> deploy", cmd_all),
    ]
    for name, help_, fn in specs:
        sp = sub.add_parser(name, parents=[targets], help=help_, description=help_)
        sp.set_defaults(func=fn)

    sp = sub.add_parser(
        "uninstall",
        help="снести меню из игр (N... | ALL)",
        description="снести меню из игр",
    )
    sp.add_argument(
        "games",
        nargs="+",
        metavar="N|ALL",
        help="номера игр, или ALL — из всех игр манифеста",
    )
    sp.set_defaults(func=cmd_uninstall)

    sp = sub.add_parser(
        "quick",
        help="поставить меню в любую игру по пути, без манифеста (движок определяется сам)",
        description="поставить (или --remove — снять) меню в игре по пути: папка игры, "
        "её game/, .exe или .html. Движок (Ren'Py, RPG Maker, HTML5, Twine, Godot, Unity, "
        "Unreal) определяется сам, статы меню находит само.",
    )
    sp.add_argument("paths", nargs="+", metavar="PATH", help="путь к игре")
    sp.add_argument("--remove", action="store_true", help="снять меню вместо установки")
    sp.set_defaults(func=cmd_quick)

    sp = sub.add_parser(
        "library",
        help="все игры в папке: движок и статус меню (поставить/обновить/снять пачкой)",
        description="найти игры в папке (на --depth уровней вниз), показать движок и статус меню",
    )
    sp.add_argument("folder", metavar="ПАПКА", help="папка с играми, например D:/Games")
    sp.add_argument("--depth", type=int, default=2, help="на сколько уровней заходить (2)")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--install", action="store_true", help="поставить меню, где его нет или оно старое")
    g.add_argument("--update", action="store_true", help="обновить только устаревшие")
    g.add_argument("--remove", action="store_true", help="снять меню отовсюду")
    sp.set_defaults(func=cmd_library)

    sp = sub.add_parser(
        "saves",
        help="редактор сохранений (окно; нужен PyQt6)",
        description="редактор сохранений: Ren'Py, RPG Maker, Unity, Godot, persistent Ren'Py",
    )
    sp.add_argument("file", nargs="?", help="файл сейва (без него — выбрать игру в окне)")
    sp.set_defaults(func=cmd_saves)

    sp = sub.add_parser(
        "list",
        help="игры манифеста: движок + статус установки",
        description="игры манифеста: движок + статус установки",
    )
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser(
        "doctor",
        parents=[targets],
        help="проверка окружения и игр: что установлено, устарело, сломано",
        description="проверка окружения и игр: что установлено, устарело, сломано",
    )
    sp.set_defaults(func=cmd_doctor)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args) or report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
