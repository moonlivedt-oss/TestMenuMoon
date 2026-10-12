"""Студия (PyQt6, тесты пропускаются без него), обучение, библиотека игр, точки входа."""

from helpers import *  # noqa: F401,F403  (общие импорты и помощники)


def test_library_finds_games_and_skips_noise():
    from tmkit import library

    with tempfile.TemporaryDirectory() as tmp:
        lib = os.path.join(tmp, "game")  # сама папка называется game, но это не игра
        rp = os.path.join(lib, "Visual Novel v1.2", "game")
        os.makedirs(rp)
        open(os.path.join(rp, "script.rpy"), "w").close()
        web = os.path.join(lib, "Bakery")
        os.makedirs(web)
        open(os.path.join(web, "index.html"), "w").write("<html><head><title>Pixel Shop</title></head><body></body></html>")
        docs = os.path.join(lib, "Manual")
        os.makedirs(docs)
        open(os.path.join(docs, "readme.html"), "w").close()  # одна страница — не игра
        found = library.find_games(lib, games={})
        by = {g.engine.key: g for g in found}
        assert sorted(by) == ["renpy", "web"], [(g.name, g.engine.key) for g in found]
        assert by["renpy"].name == "Visual Novel" and by["renpy"].target == rp
        assert by["web"].name == "Pixel Shop" and by["web"].status == "none"
        library.install(by["web"])
        library.refresh(by["web"], games={})
        assert by["web"].status == "ok"
        library.install(by["renpy"])
        assert library.refresh(by["renpy"], games={}).status == "ok"
        library.remove(by["web"])
        assert library.refresh(by["web"], games={}).status == "none"


def test_entry_points_import_cleanly():
    """Точки входа импортируются без ошибок — ловит поломку `from tmkit import …` после
    рефакторингов. Студия запускает команды tm.py отдельным процессом, так что битый
    импорт молча ломал бы студию, а не тесты. Модули студии — только если есть PyQt6."""
    import importlib, importlib.util

    spec = importlib.util.spec_from_file_location("entry_tm", os.path.join(ROOT, "tm.py"))
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        return
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    for name in ("tmstudio.theme", "tmstudio.tabs", "tmstudio.window", "tmstudio.tour",
                 "tmstudio.save_editor", "tmstudio.library"):
        importlib.import_module(name)


def test_studio_runs_only_tm_commands():
    """Студия ставит в очередь команды tm.py, а не старые скрипты-обёртки из корня."""
    for fn in ("window.py", "tabs.py"):
        text = open(os.path.join(ROOT, "tmstudio", fn), encoding="utf-8").read()
        for old in ("deploy.py", "gen_data.py", "uninstall.py", "verify.py",
                    "collect_sources.py", "curate_dump.py"):
            assert '"%s"' % old not in text, (fn, old)
    sub = {a.dest: a for a in tm.build_parser()._actions if a.dest == "cmd"}["cmd"]
    for cmd in ("collect", "curate", "gen", "deploy", "verify", "uninstall", "saves"):
        assert cmd in sub.choices, cmd


def test_studio_tour_steps_are_well_formed():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        import PyQt6  # noqa: F401  (студия; тестам он не обязателен — в CI его нет)
    except ImportError:
        return
    from tmstudio import tour

    st = tour.steps()
    assert len(st) >= 8
    for s in st:
        assert s.title and s.text
        assert os.path.exists(
            os.path.join(ROOT, "assets", "icons", s.mascot + ".png")
        ), s.mascot


def test_game_icons_for_new_tabs():
    for k in ("rocket", "flag", "checklist", "code", "download", "upload"):
        assert os.path.exists(os.path.join(ROOT, "assets", "tm_ui", "ic", k + ".png")), k
