#!/usr/bin/env python3
"""Smoke-тесты тулкита: детерминизм манифеста и генерация data-файлов.

Без сторонних зависимостей. Запуск:
    python tests/test_smoke.py      (встроенный раннер, печатает PASS/FAIL)
    pytest tests/test_smoke.py      (если установлен pytest — подхватит test_*)

Проверяем инварианты, а не конкретные значения игр, чтобы тесты не ломались
при правках манифеста:
  * manifest.dumps — валидный Python и идемпотентен (round-trip не теряет данные);
  * generate.esc / rows_of — корректное экранирование строк для .rpy;
  * generate.gen — пишет файл с заголовком/акцентом и синтаксически целыми списками;
  * manifest.add_game / remove_game / next_index — правка состава игр.
"""

import os, sys, ast, json, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tmkit import manifest
from tmkit import generate
from tmkit import validate
from tmkit import analysis
from tmkit import rpa
from tmkit import games
from tmkit import engines
from tmkit import deploy as tmdeploy
from tmkit.cli import parse_game_targets
import tm  # единая точка входа (python tm.py <команда>)


def _parse_manifest_text(text):
    """Выполнить сгенерированный games_data.py и вернуть (GAMES, G, ACCENT)."""
    ns = {}
    exec(compile(text, "<manifest>", "exec"), ns)
    return ns["GAMES"], ns["G"], ns["ACCENT"]


# --------------------------------------------------------------- манифест


def test_dumps_is_valid_python():
    games, G, ACCENT = manifest.load_games()
    text = manifest.dumps(games, G, ACCENT)
    # не должно кидать SyntaxError
    compile(text, "<manifest>", "exec")


def test_manifest_roundtrip_preserves_data():
    games, G, ACCENT = manifest.load_games()
    text = manifest.dumps(games, G, ACCENT)
    games2, G2, ACCENT2 = _parse_manifest_text(text)
    assert G2 == G, "G изменился при round-trip"
    assert ACCENT2 == ACCENT, "ACCENT изменился при round-trip"
    assert sorted(games2) == sorted(games), "набор игр изменился"
    for i in games:
        for field in ("title", "root", "status"):
            assert games2[i].get(field) == games[i].get(field), (
                f"game_{i}.{field} потерян"
            )
        # stats/actions сравниваем как списки пар (tuple/list не важен)
        for field in ("stats", "actions"):
            a = [tuple(p) for p in games[i].get(field, [])]
            b = [tuple(p) for p in games2[i].get(field, [])]
            assert a == b, f"game_{i}.{field} изменился при round-trip"


def test_manifest_writes_per_game_accent_only_when_set():
    games = {
        1: {
            "title": "A",
            "root": "x/game",
            "status": "",
            "accent": "#ff0000",
            "stats": [],
            "actions": [],
        },
        2: {
            "title": "B",
            "root": "y/game",
            "status": "",  # без акцента -> наследует глобальный
            "stats": [],
            "actions": [],
        },
    }
    games2, _G, _A = _parse_manifest_text(manifest.dumps(games, "G", "#38e0c8"))
    assert games2[1].get("accent") == "#ff0000", (
        "per-game акцент потерян при round-trip"
    )
    assert "accent" not in games2[2], "пустой акцент не должен писаться в манифест"


def test_dumps_is_idempotent():
    games, G, ACCENT = manifest.load_games()
    text1 = manifest.dumps(games, G, ACCENT)
    games2, G2, ACCENT2 = _parse_manifest_text(text1)
    text2 = manifest.dumps(games2, G2, ACCENT2)
    assert text1 == text2, (
        "dumps не идемпотентен: повторная сериализация даёт другой текст"
    )


def test_dumps_on_disk_matches_current_file():
    """Сериализация того, что на диске, совпадает с самим файлом games_data.py
    (гарантия, что формат детерминирован и файл не «дрейфует» при пересохранении)."""
    games, G, ACCENT = manifest.load_games()
    text = manifest.dumps(games, G, ACCENT)
    with open(manifest.GAMES_DATA_PATH, encoding="utf-8") as f:
        on_disk = f.read()
    assert text == on_disk, (
        "games_data.py не в каноническом формате — пересохрани через студию/manifest"
    )


# --------------------------------------------------------------- add / remove


def test_next_index_fills_gaps():
    assert manifest.next_index({}) == 1
    assert manifest.next_index({1: {}, 2: {}}) == 3
    assert manifest.next_index({1: {}, 3: {}}) == 2  # заполняет дыру


def test_add_game_assigns_free_index_and_defaults():
    games = {1: {}, 2: {}}
    idx = manifest.add_game(games, r"C:\Games\Foo\game", title="Foo")
    assert idx == 3
    assert games[3]["title"] == "Foo"
    assert games[3]["root"] == "C:/Games/Foo/game"  # бэкслеши нормализованы
    assert games[3]["stats"] == [] and games[3]["actions"] == []


def test_add_game_rejects_duplicate_index():
    games = {1: {}}
    try:
        manifest.add_game(games, "x", index=1)
    except ValueError:
        pass
    else:
        raise AssertionError("add_game должен отклонять занятый индекс")


def test_remove_game_pops_entry():
    games = {1: {"title": "A"}, 2: {"title": "B"}}
    rec = manifest.remove_game(games, 1)
    assert rec["title"] == "A"
    assert 1 not in games and 2 in games


def test_remove_game_missing_raises():
    try:
        manifest.remove_game({1: {}}, 99)
    except KeyError:
        pass
    else:
        raise AssertionError(
            "remove_game должен кидать KeyError на отсутствующий индекс"
        )


def test_add_remove_survive_manifest_roundtrip():
    games, G, ACCENT = manifest.load_games()
    idx = manifest.add_game(games, "D:/tmp/game", title='Кавычки "и" бэкслеш \\')
    text = manifest.dumps(games, G, ACCENT)
    games2, _, _ = _parse_manifest_text(text)
    assert games2[idx]["title"] == 'Кавычки "и" бэкслеш \\'
    assert games2[idx]["root"] == "D:/tmp/game"
    manifest.remove_game(games2, idx)
    assert idx not in games2


# --------------------------------------------------------------- валидация


def test_validate_clean_game_has_no_issues():
    stats = [("— секция —", ""), ("Деньги", "money"), ("Сила", "p.str")]
    actions = [("Деньги +100", "money += 100"), ("Выдать", 'add_item("x", 1)')]
    assert validate.check_game(stats, actions) == []


def test_validate_sections_are_not_flagged():
    # заголовки секций (пустое значение) не должны считаться проблемами
    stats = [("— Навыки —", ""), ("— Прочее —", "")]
    assert validate.check_stats(stats) == []


def test_validate_catches_syntax_error_in_action():
    issues = validate.check_actions([("Битое", "money +=")])
    assert len(issues) == 1 and "синтаксис" in issues[0]


def test_validate_catches_duplicate_stat_path():
    issues = validate.check_stats([("Деньги", "money"), ("Кэш", "money")])
    assert any("дубль" in s for s in issues)


def test_validate_catches_duplicate_action_code():
    issues = validate.check_actions([("A", "money += 1"), ("B", "money += 1")])
    assert any("дубль" in s for s in issues)


def test_validate_catches_path_without_label():
    issues = validate.check_stats([("", "money")])
    assert any("без метки" in s for s in issues)


def test_validate_compound_for_action_compiles():
    # реальный паттерн выдачи из манифеста — валидная compound-строка
    code = 'for _i in ["a","b"]: add_item(_i, 1)'
    assert validate.check_actions([("Всё", code)]) == []


def test_validate_real_manifest_is_clean():
    # текущие данные манифеста не должны содержать синтаксических ошибок
    games, _G, _A = manifest.load_games()
    for i, g in games.items():
        issues = validate.check_actions(g.get("actions", []))
        syntax = [s for s in issues if "синтаксис" in s]
        assert syntax == [], f"game_{i}: битый код действий: {syntax}"


# --------------------------------------------------------------- генерация


def test_esc_escapes_quotes_and_backslashes():
    assert generate.esc(r'a"b') == r"a\"b"
    assert generate.esc(r"a\b") == r"a\\b"
    assert generate.esc("plain") == "plain"


def test_rows_of_roundtrips_through_literal_eval():
    pairs = [
        ("Деньги", "money"),
        ('Кавычки "х"', r'd["a"]["b"]'),
        ("Бэкслеш", r"path\to"),
        ("— секция —", ""),
    ]
    rendered = generate.rows_of(pairs)
    parsed = ast.literal_eval("[" + rendered + "]")
    assert parsed == [tuple(p) for p in pairs], "экранирование строк ломает round-trip"


def test_gen_writes_wellformed_data_file():
    games = generate.GAMES
    i = sorted(games)[0]
    orig_out = generate.OUT
    with tempfile.TemporaryDirectory() as tmp:
        generate.OUT = tmp
        try:
            generate.gen(i)
            path = os.path.join(tmp, f"game_{i}", "zzz_testmenu_data.rpy")
            assert os.path.exists(path), "data-файл не создан"
            body = open(path, encoding="utf-8").read()
        finally:
            generate.OUT = orig_out

    assert games[i]["title"] in body, "заголовок игры не попал в файл"
    assert generate.ACCENT in body, "акцент не попал в файл"
    assert "store.tm_stats" in body and "store.tm_actions" in body

    # списки статов/действий должны быть синтаксически целыми: извлекаем и парсим
    for marker in ("store.tm_stats = [", "store.tm_actions = ["):
        start = body.index(marker) + len(marker) - 1  # позиция '['
        depth, end = 0, None
        for j in range(start, len(body)):
            if body[j] == "[":
                depth += 1
            elif body[j] == "]":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        assert end is not None, f"не найден конец списка для {marker}"
        ast.literal_eval(body[start:end])  # кинет, если синтаксис битый


def test_gen_uses_per_game_accent_over_global():
    i = sorted(generate.GAMES)[0]
    g = generate.GAMES[i]
    orig_out, had_accent, orig_accent = generate.OUT, ("accent" in g), g.get("accent")
    with tempfile.TemporaryDirectory() as tmp:
        generate.OUT = tmp
        g["accent"] = "#abcdef"
        try:
            generate.gen(i)
            body = open(
                os.path.join(tmp, f"game_{i}", "zzz_testmenu_data.rpy"),
                encoding="utf-8",
            ).read()
        finally:
            generate.OUT = orig_out
            if had_accent:
                g["accent"] = orig_accent
            else:
                g.pop("accent", None)
    assert 'store.tm_accent = "#abcdef"' in body, "per-game акцент не попал в data-файл"


# --------------------------------------------------------------- анализ (curate)


def test_analysis_re_flat_matches_numeric_and_bool():
    m = analysis.RE_FLAT.match("default money = 100")
    assert m and m.group(1) == "money" and m.group(2) == "100"
    assert analysis.RE_FLAT.match("define GID = True").group(2) == "True"
    assert analysis.RE_FLAT.match('default name = "x"') is None  # не число/булево
    m = analysis.RE_FLAT.match("default money = 100  # старт")  # хвостовой комментарий
    assert m and m.group(1) == "money" and m.group(2) == "100"


def test_analysis_is_stat_keywords_and_exclusions():
    assert analysis.is_stat("money")
    assert analysis.is_stat("player_affection")
    assert not analysis.is_stat("gui.text_size")  # gui.* исключён
    assert not analysis.is_stat("_internal")  # _* исключён
    assert not analysis.is_stat("background_image")  # нет stat-ключа


def test_analysis_is_stat_token_boundary_not_substring():
    # A3: ключевое слово матчится по границе токена/префиксу, не подстрокой
    assert analysis.is_stat("affection")  # префикс aff
    assert analysis.is_stat("player_strength")  # токен strength (префикс str)
    assert analysis.is_stat("focusLevel")  # camelCase -> [focus, level]
    assert not analysis.is_stat("irrelevant")  # 'rel' не в начале токена (было ложное)
    assert not analysis.is_stat("instruction")  # 'str' лишь подстрокой (было ложное)
    assert not analysis.is_stat("waypoint")  # 'point' не префикс токена


def test_analysis_a1_dollar_and_python_regexes():
    assert analysis.RE_DOLLAR.match("$ money = 100").group(1) == "money"
    assert analysis.RE_DOLLAR.match("    $ day = 1  # коммент").group(2) == "1"
    assert analysis.RE_PYHEAD.match("init python:")
    assert analysis.RE_PYHEAD.match("    init -2 python:")
    assert analysis.RE_PYHEAD.match("python:")
    m = analysis.RE_PYASSIGN.match("    gold = 25")
    assert m and m.group(2) == "gold" and m.group(3) == "25"


def test_analysis_a2_single_line_dict():
    m = analysis.RE_DICTONE.match('default pdata = {"empathy": 5, "focus": 10}')
    assert m and m.group(1) == "pdata"
    assert ("empathy", "5") in analysis.RE_DICTNUM.findall(m.group(2))


def test_analysis_a4_class_level_numeric_var():
    m = analysis.RE_CLASSVAR.match("        base_level = 2")
    assert m and m.group(2) == "base_level" and m.group(3) == "2"
    assert (
        analysis.RE_CLASSVAR.match("        self.x = 5") is None
    )  # self. — не поле тела класса


def test_analysis_dump_end_to_end_tracks_indent():
    src = "\n".join(
        [
            "default money = 100  # flat",
            "$ energy = 50",
            "",
            "init python:",
            "    day = 1",
            "    start_gold = 25",
            "    def _helper():",
            "        loot = 999",  # локал в теле def — НЕ захватывать
            "",
            "    class Hero:",
            "        base_level = 2",  # A4: поле уровня класса
            "        def __init__(self):",
            "            self.strength = 5",
            "            self.focus = 3",
            "",
            'default player_data = {"empathy": 5, "focus": 10}',  # A2 однострочный
            "",
            "default nested = {",  # A2 вложенный многострочный
            '    "outer": {',
            '        "hp": 7,',
            "    },",
            '    "gold": 3,',
            "}",
            "",
            "default state = Hero()",
            "",
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        game_src = os.path.join(tmp, "game")
        os.makedirs(game_src)
        with open(os.path.join(game_src, "s.rpy"), "w", encoding="utf-8") as fh:
            fh.write(src)
        cand_dir = os.path.join(tmp, "cand")
        saved = (analysis.CAND_DIR, analysis.ana_dir, analysis.cand_file)
        analysis.CAND_DIR = cand_dir
        analysis.ana_dir = lambda i: game_src
        analysis.cand_file = lambda i: os.path.join(cand_dir, f"game_{i}.txt")
        try:
            analysis.dump(1)
            out = open(os.path.join(cand_dir, "game_1.txt"), encoding="utf-8").read()
        finally:
            analysis.CAND_DIR, analysis.ana_dir, analysis.cand_file = saved

    assert "money = 100" in out  # default
    assert "energy = 50" in out  # A1 $-строка
    assert (
        "day = 1" in out and "start_gold = 25" in out
    )  # A1 python-блок (базовый уровень)
    assert "loot" not in out  # A1: локал в def не захвачен
    assert "base_level" in out and "state.base_level" in out  # A4 + путь через инстанс
    assert "state.strength" in out and "state.focus" in out  # self-поля
    assert "empathy=5" in out  # A2 однострочный dict
    assert "hp=7" in out and "gold=3" in out  # A2 вложенный dict закрылся на верной }


def test_analysis_dict_num_pairs():
    found = analysis.RE_DICTNUM.findall('"empathy": 5, "focus": 10')
    assert ("empathy", "5") in found and ("focus", "10") in found


def test_analysis_inventory_and_money_signatures():
    assert analysis.RE_INV.search("def add_item(name, n):")
    assert analysis.RE_INV.search("class PlayerInventory:")
    assert analysis.RE_MONEY.search("def gain_money(self, n):")


def test_analysis_object_stat_regexes():
    assert analysis.RE_CLASS.match("class PlayerStats:").group(2) == "PlayerStats"
    assert analysis.RE_SELFNUM.match("        self.strength = 5").group(1) == "strength"
    assert (
        analysis.RE_SELFNUM.match("    self.hp = 10  # max").group(1) == "hp"
    )  # с комментарием
    mi = analysis.RE_INSTANCE.match("default state = GlobalState(")
    assert mi and mi.group(1) == "state" and mi.group(2) == "GlobalState"


def test_analysis_extracted_games_lists_numeric_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "game_3"))
        os.makedirs(os.path.join(tmp, "game_10"))
        os.makedirs(os.path.join(tmp, "game_x"))  # не число — пропуск
        open(os.path.join(tmp, "game_7"), "w").close()  # файл, не папка — пропуск
        old = analysis.ANA_BASE
        analysis.ANA_BASE = tmp.replace("\\", "/")
        try:
            assert analysis.extracted_games() == [3, 10]
        finally:
            analysis.ANA_BASE = old


# --------------------------------------------------------------- rpa (распаковка)


def _build_rpa3(files, key=0xDEADBEEF):
    """Собрать валидный RPA-3.0 из {имя: bytes}. Возвращает bytes архива."""
    import zlib, pickle

    header_len = len(b"RPA-3.0 %016x %08x\n" % (0, 0))  # фикс. длина (34)
    data = b""
    index = {}
    for name, content in files.items():
        off = header_len + len(data)
        index[name] = [(off ^ key, len(content) ^ key)]  # 2-tuple, prefix пуст
        data += content
    index_off = header_len + len(data)
    blob = zlib.compress(pickle.dumps(index))
    header = b"RPA-3.0 %016x %08x\n" % (index_off, key)
    assert len(header) == header_len
    return header + data + blob


def test_rpa_extract_roundtrip():
    files = {
        "script.rpy": b"label start:\n    pass\n",
        "img.png": b"\x89PNG\x00\x01\x02",
    }
    with tempfile.TemporaryDirectory() as tmp:
        arc = os.path.join(tmp, "a.rpa")
        with open(arc, "wb") as f:
            f.write(_build_rpa3(files))
        out = os.path.join(tmp, "out")
        n = rpa.extract(arc, out)
        assert n == 2
        for name, content in files.items():
            with open(os.path.join(out, name), "rb") as f:
                assert f.read() == content


def test_rpa_scripts_only_filters_nonscripts():
    files = {"script.rpy": b"x", "img.png": b"y"}
    with tempfile.TemporaryDirectory() as tmp:
        arc = os.path.join(tmp, "a.rpa")
        with open(arc, "wb") as f:
            f.write(_build_rpa3(files))
        out = os.path.join(tmp, "out")
        n = rpa.extract(arc, out, scripts_only=True)
        assert n == 1
        assert os.path.exists(os.path.join(out, "script.rpy"))
        assert not os.path.exists(os.path.join(out, "img.png"))


def test_rpa_rejects_non_rpa():
    with tempfile.TemporaryDirectory() as tmp:
        arc = os.path.join(tmp, "bad.rpa")
        with open(arc, "wb") as f:
            f.write(b"NOT-AN-RPA\n")
        try:
            rpa.extract(arc, os.path.join(tmp, "out"))
        except ValueError:
            pass
        else:
            raise AssertionError("extract должен отклонять не-RPA архив")


# --------------------------------------------------------------- games / cli


def test_games_roots_match_manifest():
    assert sorted(games.ROOTS) == sorted(games.GAMES)
    for i, g in games.GAMES.items():
        assert games.ROOTS[i] == g["root"]


def test_games_basedir_is_parent_of_root():
    for i in games.GAMES:
        assert games.basedir(i) == os.path.dirname(games.GAMES[i]["root"])


def test_games_launcher_prefers_paired_exe():
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "b.py"), "w").close()  # без парного .exe
        open(os.path.join(tmp, "a.py"), "w").close()
        open(os.path.join(tmp, "a.exe"), "w").close()  # a.py — с парой
        games.GAMES[999] = {"root": os.path.join(tmp, "game").replace("\\", "/")}
        try:
            assert os.path.basename(games.launcher(999)) == "a.py"
            assert games.python_exe(999) is None  # нет lib/**/python.exe
        finally:
            del games.GAMES[999]


def test_cli_parse_game_targets_explicit_and_default():
    old = sys.argv
    try:
        sys.argv = ["prog", "3", "5"]
        assert parse_game_targets("d", lambda: [1, 2]) == [3, 5]
        sys.argv = ["prog"]  # без аргументов — дефолт
        assert parse_game_targets("d", lambda: [1, 2]) == [1, 2]
    finally:
        sys.argv = old


# --------------------------------------------------------------- twine PoC (инжектор)


def _load_twine_inject():
    import importlib.util

    path = os.path.join(ROOT, "engines", "twine", "inject.py")
    spec = importlib.util.spec_from_file_location("twine_inject", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_twine_inject_before_body_and_idempotent():
    ti = _load_twine_inject()
    html = "<html><body><p>hi</p></body></html>"
    out = ti.inject(html, "console.log(1)")
    assert ti.MARK_START in out and "console.log(1)" in out
    assert out.index(ti.MARK_START) < out.lower().index("</body>")  # перед </body>
    # повторное внедрение не дублирует блок
    out2 = ti.inject(out, "console.log(2)")
    assert out2.count(ti.MARK_START) == 1
    assert "console.log(2)" in out2 and "console.log(1)" not in out2  # заменилось


def test_twine_remove_restores_html():
    ti = _load_twine_inject()
    html = "<html><body><p>hi</p></body></html>"
    out = ti.inject(html, "X()")
    cleaned = ti.remove(out)
    assert ti.MARK_START not in cleaned and "X()" not in cleaned
    assert "<p>hi</p>" in cleaned


def test_twine_inject_without_body_appends():
    ti = _load_twine_inject()
    out = ti.inject("<div>no body tag</div>", "Y()")
    assert ti.MARK_START in out and out.strip().endswith(ti.MARK_END)


# --------------------------------------------------------------- engine backends


def test_engines_registry_capabilities():
    assert set(engines.REGISTRY) == {"renpy", "twine", "rpgmaker", "godot", "unity", "web", "unreal"}
    assert engines.REGISTRY["web"].supports("deploy") and not engines.REGISTRY["web"].supports("extract")
    assert engines.REGISTRY["godot"].supports("deploy") and engines.REGISTRY[
        "godot"
    ].supports("scan")
    assert engines.REGISTRY["unity"].supports("deploy") and not engines.REGISTRY[
        "unity"
    ].supports("generate")
    assert engines.REGISTRY["renpy"].supports("extract")
    assert engines.REGISTRY["twine"].supports("deploy")
    assert engines.REGISTRY["twine"].supports("scan")  # имена $var из пассажей
    assert not engines.REGISTRY["twine"].supports("extract")  # значения в рантайме
    assert engines.REGISTRY["rpgmaker"].supports("deploy")
    assert engines.REGISTRY["rpgmaker"].supports(
        "scan"
    )  # data/*.json -> имена статически
    assert not engines.REGISTRY["rpgmaker"].supports(
        "generate"
    )  # значения правятся в рантайме


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def test_rpgmaker_scan_reads_system_items_and_paths():
    scan = engines._load_engine_module("rpgmaker", "scan.py")
    with tempfile.TemporaryDirectory() as tmp:
        data = os.path.join(tmp, "www", "data")  # вариант с www/
        os.makedirs(data)
        _write_json(
            os.path.join(data, "System.json"),
            {
                "variables": [
                    "",
                    "Бонус золота",
                    "",
                    "Репутация",
                ],  # индекс 0 пуст, 2 без имени
                "switches": ["", "Интро пройдено"],
                "currencyUnit": "G",
            },
        )
        _write_json(
            os.path.join(data, "Items.json"),
            [None, {"id": 1, "name": "Зелье"}, {"id": 2, "name": ""}],
        )  # пустое имя -> отсев
        _write_json(
            os.path.join(data, "Weapons.json"), [None, {"id": 1, "name": "Меч"}]
        )

        assert scan.find_data_dir(tmp).endswith(os.path.join("www", "data"))
        c = scan.scan(tmp)
        assert (1, "Бонус золота") in c["variables"] and (3, "Репутация") in c[
            "variables"
        ]
        assert all(
            idx != 2 for idx, _n in c["variables"]
        )  # безымянная переменная отсеяна
        assert (1, "Интро пройдено") in c["switches"]
        assert c["items"] == [(1, "Зелье")]  # запись с пустым name отсеяна
        assert c["weapons"] == [(1, "Меч")]
        assert c["currency"] == "G"

        text = scan.report(tmp)
        assert "$gameVariables.value(3)" in text  # путь переменной по индексу
        assert "$gameSwitches.value(1)" in text
        assert "$gameParty.gainItem($dataItems[1], 1)" in text
        assert "$gameParty.gainItem($dataWeapons[1], 1)" in text
        assert "$gameParty.gainGold(1000)" in text


def test_rpgmaker_scan_missing_data_raises():
    scan = engines._load_engine_module("rpgmaker", "scan.py")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            scan.scan(tmp)
            assert False, "ожидали FileNotFoundError при отсутствии data/System.json"
        except FileNotFoundError:
            pass


_TWINE_STORY = (
    "<html><body>\n"
    '<tw-storydata name="X" startnode="1">\n'
    '<tw-passagedata pid="1" name="Start">У тебя $gold золота и $rep репутации. Приз: $5!\n'
    "&lt;&lt;set $gold to 100&gt;&gt;\n"
    "&lt;&lt;set $intro_done to true&gt;&gt;\n"
    '&lt;&lt;set $hero_name to "Alex"&gt;&gt;\n'
    "$gold $gold\n"
    "</tw-passagedata>\n"
    "</tw-storydata>\n"
    "</body></html>\n"
)


def test_twine_scan_enumerates_vars_and_type_hints():
    scan = engines._load_engine_module("twine", "scan.py")
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "story.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write(_TWINE_STORY)
        c = scan.scan(html)
        by = dict(c["variables"])
        assert by["gold"] == "num"  # <<set $gold to 100>>
        assert by["intro_done"] == "bool"
        assert by["hero_name"] == "str"
        assert by["rep"] == ""  # упомянут, но без <<set>> — тип неизвестен
        assert "5" not in by  # "$5" в прозе — не переменная
        text = scan.report(html)
        assert "State.variables.gold" in text and "$rep" in text


def test_twine_scan_resolves_dir_to_largest_html():
    scan = engines._load_engine_module("twine", "scan.py")
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "stub.html"), "w", encoding="utf-8") as f:
            f.write("<html></html>")  # мелкая заглушка
        with open(os.path.join(tmp, "story.html"), "w", encoding="utf-8") as f:
            f.write(_TWINE_STORY)  # крупная история
        assert scan.find_html(tmp).endswith("story.html")
        assert engines.detect_engine(tmp).key == "twine"  # папка с .html -> twine


def test_renpy_installed_checks_engine_file():
    eng = engines.REGISTRY["renpy"]
    with tempfile.TemporaryDirectory() as tmp:
        assert eng.installed(tmp) is False
        open(os.path.join(tmp, "zzz_testmenu_engine.rpy"), "w").close()
        assert eng.installed(tmp) is True


def test_twine_installed_reflects_deploy_and_remove_via_dir():
    eng = engines.REGISTRY["twine"]
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "story.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write("<html><body><p>hi</p></body></html>")
        assert eng.installed(tmp) is False  # папка-цель, до деплоя
        eng.deploy(tmp)  # резолвит папку -> html
        assert eng.installed(tmp) is True and eng.installed(html) is True
        eng.uninstall(tmp)
        assert eng.installed(tmp) is False


def test_rpgmaker_installed_reflects_deploy_and_remove():
    eng = engines.REGISTRY["rpgmaker"]
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
            f.write("<html><body></body></html>")
        assert eng.installed(tmp) is False
        eng.deploy(tmp)
        assert eng.installed(tmp) is True
        eng.uninstall(tmp)
        assert eng.installed(tmp) is False


def test_engines_detect_routes_by_target():
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "game.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write("<html><body></body></html>")
        assert engines.detect_engine(html).key == "web"  # обычный HTML -> HTML5-движок
        story = os.path.join(tmp, "story.html")
        with open(story, "w", encoding="utf-8") as f:
            f.write(_TWINE_STORY)
        assert engines.detect_engine(story).key == "twine"  # есть <tw-storydata>

        gdir = os.path.join(tmp, "game")
        os.makedirs(gdir)
        open(os.path.join(gdir, "script.rpy"), "w").close()
        assert engines.detect_engine(gdir).key == "renpy"

        # собранная игра: только .rpyc, без исходников
        comp = os.path.join(tmp, "compiled")
        os.makedirs(comp)
        open(os.path.join(comp, "script.rpyc"), "w").close()
        assert engines.detect_engine(comp).key == "renpy"

        # корень дистрибутива: game/ + renpy/, скрипты внутри game/
        dist = os.path.join(tmp, "MyRenpyGame-1.0")
        os.makedirs(os.path.join(dist, "game"))
        os.makedirs(os.path.join(dist, "renpy"))
        open(os.path.join(dist, "game", "script.rpyc"), "w").close()
        assert engines.detect_engine(dist).key == "renpy"

        assert engines.detect_engine(os.path.join(tmp, "nope.txt")) is None

        rpgm = os.path.join(tmp, "MyRPG")
        os.makedirs(os.path.join(rpgm, "js"))
        open(os.path.join(rpgm, "index.html"), "w").close()
        open(os.path.join(rpgm, "js", "rpg_core.js"), "w").close()
        assert engines.detect_engine(rpgm).key == "rpgmaker"


def test_engines_twine_deploy_uninstall_via_registry():
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "g.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write("<html><body><p>x</p></body></html>")
        e = engines.REGISTRY["twine"]
        e.deploy(html)
        assert "TM_TWINE_MENU_START" in open(html, encoding="utf-8").read()
        e.uninstall(html)
        assert "TM_TWINE_MENU_START" not in open(html, encoding="utf-8").read()


def test_web_engine_detects_folder_and_injects_index():
    e = engines.REGISTRY["web"]
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "www"))
        idx = os.path.join(tmp, "www", "index.html")
        with open(idx, "w", encoding="utf-8") as f:
            f.write("<html><body><canvas></canvas></body></html>")
        with open(os.path.join(tmp, "credits.html"), "w", encoding="utf-8") as f:
            f.write("<html><body>" + "x" * 5000 + "</body></html>")  # крупнее, но не игра
        assert engines.detect_engine(tmp).key == "web"
        assert e.installed(tmp) is False
        e.deploy(tmp)
        e.deploy(tmp)  # повторно — без дублей
        text = open(idx, encoding="utf-8").read()
        assert text.count("TM_WEB_MENU_START") == 1 and "TM_TWINE_MENU_START" not in text
        assert "window.TM_ADAPTER" in text and e.installed(tmp) and e.current(tmp)
        e.uninstall(tmp)
        assert open(idx, encoding="utf-8").read() == "<html><body><canvas></canvas></body></html>"


def test_web_menus_have_game_tab_contract():
    core = open(os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"), encoding="utf-8").read()
    assert '["game", "Игра"]' in core and "function renderGame" in core and "requestAnimationFrame" in core
    rpgm = open(os.path.join(ROOT, "engines", "rpgmaker", "tm_menu.js"), encoding="utf-8").read()
    for key in ("speed: function", "cheats: function", "places:", "isDebugThrough", "canEncounter", "Отряд: "):
        assert key in rpgm, key
    web = open(os.path.join(ROOT, "engines", "web", "tm_menu.js"), encoding="utf-8").read()
    for key in ("speed: true", "cr_getC2Runtime", "renderAndStep", "registry"):
        assert key in web, key


# --------------------------------------------------------------- редактор сохранений
def test_lzstring_matches_reference_vector():
    from tmkit import lzstring

    # эталон — lz-string 1.5.0 (JS): compressToBase64(JSON.stringify({gold:250,n:"Тереза"}))
    src = '{"gold":250,"n":"Тереза"}'
    ref = "N4Ig5g9gNgJiBcAmArABgDQgHYJIIhBBWEEAEQAwdhBAGEBAF8g="
    assert lzstring.compress_to_base64(src) == ref
    assert lzstring.decompress_from_base64(ref) == src
    assert lzstring.decompress_from_base64(lzstring.compress_to_base64("😀" + "x" * 500)) == "😀" + "x" * 500


def _rpgm_save_dir(tmp, mz):
    import json as _j

    os.makedirs(os.path.join(tmp, "data"))
    os.makedirs(os.path.join(tmp, "save"))
    with open(os.path.join(tmp, "data", "System.json"), "w", encoding="utf-8") as f:
        _j.dump({"variables": ["", "Репутация"], "switches": ["", "Дверь"]}, f)
    with open(os.path.join(tmp, "data", "Items.json"), "w", encoding="utf-8") as f:
        _j.dump([None, {"id": 1, "name": "Зелье"}], f)
    root = {"party": {"_gold": 250, "_items": {"1": 3}}, "variables": {"_data": [None, 5]},
            "switches": {"_data": [None, False]}, "actors": {"_data": [None, {"_name": "Харольд", "_hp": 80}]}}
    return os.path.join(tmp, "save", "file1." + ("rmmzsave" if mz else "rpgsave")), root


def test_saves_rpgmaker_mv_and_mz_roundtrip():
    import json as _j, zlib as _z
    from tmkit import saves, lzstring

    for mz in (False, True):
        with tempfile.TemporaryDirectory() as tmp:
            path, root = _rpgm_save_dir(tmp, mz)
            text = _j.dumps(root, ensure_ascii=False, separators=(",", ":"))
            raw = (_z.compress(text.encode("utf-8"), 1).decode("latin-1").encode("utf-8") if mz
                   else lzstring.compress_to_base64(text).encode("ascii"))
            open(path, "wb").write(raw)
            d = saves.open_save(path)
            assert d.kind == ("rpgmz" if mz else "rpgmv")
            by = {it.label: it for it in d.items()}
            gold = [it for lab, it in by.items() if lab.startswith("Золото")][0]
            assert any(lab.startswith("Переменная #1 Репутация") for lab in by)
            assert any(lab.startswith("Предмет #1 Зелье") for lab in by)
            assert any(lab.startswith("Харольд: HP") for lab in by)
            d.set(gold.path, saves.coerce(gold.value, "9999"))
            d.save()
            assert os.path.exists(path + ".tm_bak")
            d2 = saves.open_save(path)
            assert d2.root["party"]["_gold"] == 9999 and d2.root["actors"]["_data"][1]["_hp"] == 80


def test_saves_godot_cfg_and_json():
    from tmkit import saves

    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "save.cfg")
        open(cfg, "w", encoding="utf-8").write('[player]\ngold=10\nname="Moon"\npos=Vector2(1, 2)\nalive=true\n')
        d = saves.open_save(cfg)
        assert d.kind == "godotcfg"
        by = {it.label: it for it in d.items()}
        assert set(by) == {"player/gold", "player/name", "player/alive"}  # Vector2 не трогаем
        d.set(by["player/gold"].path, 500)
        d.set(by["player/name"].path, "Луна")
        d.save()
        text = open(cfg, encoding="utf-8").read()
        assert "gold=500" in text and 'name="Луна"' in text and "pos=Vector2(1, 2)" in text
        js = os.path.join(tmp, "s.json")
        open(js, "w", encoding="utf-8").write('{"hero": {"hp": 5, "tags": ["a"]}, "ok": true}')
        d = saves.open_save(js)
        by = {it.label: it for it in d.items()}
        d.set(by["hero.hp"].path, 99)
        d.save()
        assert '"hp":99' in open(js, encoding="utf-8").read()


def test_saves_renpy_pickle_stubs_roundtrip():
    """Сейв Ren'Py из классов, которых в студии нет: открыть на заглушках, поменять, записать,
    затем прочитать настоящими классами — значения новые, остальное на месте."""
    import io as _io, pickle as _p, types as _t, zipfile as _zf
    from tmkit import saves

    mod = _t.ModuleType("store")
    exec("class Girl(object):\n    pass\nclass Pos(object):\n    __slots__ = ('x', 'y')\n"
         "class RevertableList(list):\n    pass\n", mod.__dict__)
    sys.modules["store"] = mod
    try:
        g = mod.Girl(); g.love = 3; g.name = "Ann"
        pos = mod.Pos(); pos.x, pos.y = 1, 2
        lst = mod.RevertableList([1, 2])
        roots = {"store.money": 5, "store.girl": g, "store.pos": pos, "store.inv": lst, "store._hidden": 1}
        log = _p.dumps((roots, {"log": []}), protocol=2)
    finally:
        del sys.modules["store"]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "1-1-LT1.save")
        with _zf.ZipFile(path, "w") as z:
            z.writestr("log", log)
            z.writestr("extra_info", "x")
        d = saves.open_save(path)
        assert d.kind == "renpy"
        by = {it.label: it for it in d.items()}
        assert "_hidden" not in by and {"money", "girl.love", "inv[0]"} <= set(by)
        d.set(by["money"].path, 100)
        d.set(by["girl.love"].path, 42)
        d.set(by["inv[1]"].path, 7)
        saves.Doc.save(d)
        data = _zf.ZipFile(path).read("log")
        assert _zf.ZipFile(path).read("extra_info") == b"x"
    sys.modules["store"] = mod
    try:
        r, _log = _p.loads(data)
    finally:
        del sys.modules["store"]
    assert r["store.money"] == 100 and r["store.girl"].love == 42 and r["store.girl"].name == "Ann"
    assert type(r["store.inv"]) is mod.RevertableList and list(r["store.inv"]) == [1, 7]
    assert (r["store.pos"].x, r["store.pos"].y) == (1, 2)


def test_saves_find_rpgmaker():
    from tmkit import saves

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "www", "save"))
        open(os.path.join(tmp, "www", "save", "file1.rpgsave"), "w").close()
        open(os.path.join(tmp, "www", "save", "file1.rpgsave.tm_bak"), "w").close()
        found = saves.find_saves(tmp, "rpgmaker")
        assert [os.path.basename(p) for _l, p in found] == ["file1.rpgsave"]


def test_engine_menu_core_has_scanner_and_actions():
    core = open(
        os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"), encoding="utf-8"
    ).read()
    assert "Сканер" in core and "Экшены" in core and "scanNarrow" in core
    assert "tm-finput" in core and "applyFilter" in core  # фильтр по имени
    assert "localStorage" in core  # запоминание состояния


def test_engine_adapters_define_adapter():
    for name in ("twine", "rpgmaker"):
        ad = open(
            os.path.join(ROOT, "engines", name, "tm_menu.js"), encoding="utf-8"
        ).read()
        assert "window.TM_ADAPTER" in ad and "actions" in ad, (
            f"{name}: адаптер неполный"
        )


def test_engine_deploy_bundles_adapter_and_core():
    ti = _load_twine_inject()
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "g.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write("<html><body></body></html>")
        ti.deploy_file(html)
        out = open(html, encoding="utf-8").read()
        assert (
            "window.TM_ADAPTER" in out and "scanNarrow" in out
        )  # адаптер + ядро склеены


def test_engines_rpgmaker_deploy_resolves_index_html():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "js"))
        idx = os.path.join(tmp, "index.html")
        with open(idx, "w", encoding="utf-8") as f:
            f.write("<html><body></body></html>")
        open(os.path.join(tmp, "js", "rmmz_core.js"), "w").close()
        e = engines.REGISTRY["rpgmaker"]
        e.deploy(tmp)  # цель — папка, index.html найдётся сам
        assert "TM_RPGM_MENU_START" in open(idx, encoding="utf-8").read()
        e.uninstall(tmp)
        assert "TM_RPGM_MENU_START" not in open(idx, encoding="utf-8").read()


# --------------------------------------------------------------- deploy / uninstall


def test_deploy_to_copies_engine_data_ui_and_cleans_rpyc():
    with tempfile.TemporaryDirectory() as tmp:
        engine_src = os.path.join(tmp, "engine_src.rpy")
        data_file = os.path.join(tmp, "data_src.rpy")
        with open(engine_src, "w", encoding="utf-8") as f:
            f.write("# engine")
        with open(data_file, "w", encoding="utf-8") as f:
            f.write("# data")
        ui_src = os.path.join(tmp, "assets", "tm_ui")
        os.makedirs(ui_src)
        open(os.path.join(ui_src, "tm_btn.png"), "w").close()
        open(
            os.path.join(ui_src, "_scratch.png"), "w"
        ).close()  # служебный -> не копируется

        root = os.path.join(tmp, "game")
        os.makedirs(root)
        open(
            os.path.join(root, "zzz_testmenu_engine.rpyc"), "w"
        ).close()  # устаревший .rpyc

        removed = tmdeploy.deploy_to(
            root, data_file, engine_src=engine_src, ui_src=ui_src
        )

        assert removed == 1, "устаревший .rpyc не снесён"
        assert (
            open(os.path.join(root, tmdeploy.ENGINE_NAME), encoding="utf-8").read()
            == "# engine"
        )
        assert (
            open(os.path.join(root, tmdeploy.DATA_NAME), encoding="utf-8").read()
            == "# data"
        )
        assert os.path.exists(os.path.join(root, "tm_ui", "tm_btn.png"))
        assert not os.path.exists(
            os.path.join(root, "tm_ui", "_scratch.png")
        )  # ignore _*


def test_deploy_to_missing_engine_or_data_raises():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "game")
        os.makedirs(root)
        data_file = os.path.join(tmp, "data.rpy")
        open(data_file, "w").close()
        # нет движка
        try:
            tmdeploy.deploy_to(
                root, data_file, engine_src=os.path.join(tmp, "no_engine.rpy")
            )
            raise AssertionError("ожидали FileNotFoundError при отсутствии движка")
        except FileNotFoundError:
            pass
        # нет data
        engine_src = os.path.join(tmp, "e.rpy")
        open(engine_src, "w").close()
        try:
            tmdeploy.deploy_to(
                root, os.path.join(tmp, "no_data.rpy"), engine_src=engine_src
            )
            raise AssertionError("ожидали FileNotFoundError при отсутствии data")
        except FileNotFoundError:
            pass


def test_remove_from_deletes_menu_files_and_ui_only():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "game")
        os.makedirs(root)
        for name in (
            "zzz_testmenu_engine.rpy",
            "zzz_testmenu_data.rpy",
            "zzz_testmenu_engine.rpyc",
        ):
            open(os.path.join(root, name), "w").close()
        os.makedirs(os.path.join(root, "tm_ui"))
        open(os.path.join(root, "tm_ui", "tm_btn.png"), "w").close()
        open(os.path.join(root, "script.rpy"), "w").close()  # чужой файл — не трогаем

        removed = tmdeploy.remove_from(root)

        assert removed == 4, "должны снестись 3 файла меню + папка tm_ui"
        assert not os.path.exists(os.path.join(root, "tm_ui"))
        assert not os.path.exists(os.path.join(root, "zzz_testmenu_engine.rpy"))
        assert os.path.exists(os.path.join(root, "script.rpy")), (
            "чужой .rpy снесён по ошибке"
        )


def test_deploy_to_survives_missing_ui_dir():
    # нет tm_ui рядом с движком -> deploy всё равно кладёт engine+data (graceful)
    with tempfile.TemporaryDirectory() as tmp:
        engine_src = os.path.join(tmp, "e.rpy")
        open(engine_src, "w").close()
        data_file = os.path.join(tmp, "d.rpy")
        open(data_file, "w").close()
        root = os.path.join(tmp, "game")
        os.makedirs(root)
        tmdeploy.deploy_to(
            root, data_file, engine_src=engine_src, ui_src=os.path.join(tmp, "no_ui")
        )
        assert os.path.exists(os.path.join(root, tmdeploy.ENGINE_NAME))
        assert not os.path.exists(os.path.join(root, "tm_ui"))


# --------------------------------------------------------------- tm (единая точка входа)


def test_tm_routes_target_command_and_parses_numbers():
    args = tm.build_parser().parse_args(["deploy", "3", "5"])
    assert args.func is tm.cmd_deploy and args.games == [3, 5]


def test_tm_target_command_defaults_to_empty_list():
    args = tm.build_parser().parse_args(["gen"])
    assert args.games == []  # пусто -> команда сама подставит все игры


def test_tm_uninstall_accepts_all_keyword():
    args = tm.build_parser().parse_args(["uninstall", "ALL"])
    assert args.func is tm.cmd_uninstall and args.games == ["ALL"]


def test_tm_all_and_list_are_registered():
    assert tm.build_parser().parse_args(["all"]).func is tm.cmd_all
    assert tm.build_parser().parse_args(["list"]).func is tm.cmd_list


def test_tm_requires_a_subcommand():
    try:
        tm.build_parser().parse_args([])  # без команды — argparse ругается
    except SystemExit:
        pass
    else:
        raise AssertionError("tm без команды должен требовать субкоманду")


def test_root_wrappers_import_cleanly():
    """Каждая тонкая root-обёртка импортируется без ошибок — ловит поломку
    `from tmkit import …` после рефакторингов. Важно: studio.py запускает эти
    файлы по имени, так что битый импорт молча ломает студию, а не тесты.
    Импорт выполняет top-level код; блок `if __name__ == '__main__'` не срабатывает."""
    import importlib.util

    wrappers = (
        "tm.py",
        "deploy.py",
        "uninstall.py",
        "verify.py",
        "collect_sources.py",
        "curate_dump.py",
        "gen_data.py",
        "validate.py",
    )
    for fname in wrappers:
        path = os.path.join(ROOT, fname)
        assert os.path.exists(path), f"обёртка пропала: {fname}"
        spec = importlib.util.spec_from_file_location("wrap_" + fname[:-3], path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise AssertionError(f"{fname} не импортируется: {type(e).__name__}: {e}")


# --------------------------------------------------------------- регрессии (аудит)


def test_validate_flags_unparsable_and_readonly_stat_paths():
    issues = validate.check_stats([("Битый", 'd["a"'), ("Вызов", "get_money()")])
    assert any("не разбирается" in s for s in issues), issues
    assert any("только чтение" in s for s in issues), issues
    # ни то ни другое не «синтаксис»: пайплайн студии блокируют только действия
    assert not any("синтаксис" in s for s in issues)
    assert (
        validate.check_stats([("Ок", 'state.get("x").hp'), ("Ок2", 'd["a"][0]')]) == []
    )


def test_validate_accent_hex_normalizes_and_rejects():
    assert validate.accent_hex("#ABC") == "#aabbcc"
    assert validate.accent_hex(" #38E0C8 ") == "#38e0c8"
    assert validate.accent_hex("red") is None and validate.accent_hex("") is None
    assert validate.check_game([], [], "red") != []
    assert validate.check_game([], [], "") == [] and validate.check_game([], []) == []


def test_esc_keeps_multiline_cell_on_one_line():
    # вставленный в таблицу многострочный текст не должен рвать литерал в .rpy
    rendered = generate.rows_of([("a\nb", "x\ty\r")])
    assert "\n" not in rendered
    assert ast.literal_eval("[" + rendered + "]") == [("a\nb", "x\ty\r")]


def test_gen_falls_back_on_non_hex_accent_and_escapes_title():
    i = sorted(generate.GAMES)[0]
    g = generate.GAMES[i]
    saved = {k: g.get(k) for k in ("accent", "title")}
    had_accent = "accent" in g
    try:
        g["accent"] = 'red"; import os'
        g["title"] = 'T "quoted" \\ end'
        body = generate.render(i)
    finally:
        g["title"] = saved["title"]
        if had_accent:
            g["accent"] = saved["accent"]
        else:
            g.pop("accent", None)
    assert 'store.tm_accent = "%s"' % validate.accent_hex(generate.ACCENT) in body
    line = [l for l in body.splitlines() if "store.tm_title" in l][0]
    assert ast.literal_eval(line.split("=", 1)[1].strip()) == 'T "quoted" \\ end'


def test_gen_is_stale_tracks_manifest_changes():
    i = sorted(generate.GAMES)[0]
    g = generate.GAMES[i]
    orig_out, orig_title = generate.OUT, g["title"]
    with tempfile.TemporaryDirectory() as tmp:
        generate.OUT = tmp
        try:
            assert generate.is_stale(i)  # файла ещё нет
            generate.gen(i)
            assert not generate.is_stale(i)
            g["title"] = orig_title + " *"
            assert generate.is_stale(i)  # манифест ушёл вперёд
        finally:
            generate.OUT = orig_out
            g["title"] = orig_title


def _rpa3_from_index(index, payload=b""):
    import zlib, pickle

    key = 0x42
    header_len = len(b"RPA-3.0 %016x %08x\n" % (0, key))
    enc = {
        n: [(header_len + off ^ key, ln ^ key, b"")] for n, (off, ln) in index.items()
    }
    blob = zlib.compress(pickle.dumps(enc, protocol=2))
    return b"RPA-3.0 %016x %08x\n" % (header_len + len(payload), key) + payload + blob


def test_rpa_skips_paths_escaping_outdir():
    payload = b"EVILGOOD"
    arc_bytes = _rpa3_from_index(
        {"../evil.rpy": (0, 4), "ok/good.rpy": (4, 4)}, payload
    )
    with tempfile.TemporaryDirectory() as tmp:
        arc = os.path.join(tmp, "a.rpa")
        with open(arc, "wb") as f:
            f.write(arc_bytes)
        out = os.path.join(tmp, "out", "deep")
        assert rpa.extract(arc, out) == 1
        assert not os.path.exists(os.path.join(tmp, "out", "evil.rpy"))
        with open(os.path.join(out, "ok", "good.rpy"), "rb") as f:
            assert f.read() == b"GOOD"


def test_rpa_reads_py2_byte_names():
    # py2-архивы хранят имена байтами; не-ASCII имя раньше роняло весь архив
    name = "сцены/глава.rpy".encode("utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        arc = os.path.join(tmp, "a.rpa")
        with open(arc, "wb") as f:
            f.write(_rpa3_from_index({name: (0, 3)}, b"abc"))
        out = os.path.join(tmp, "out")
        assert rpa.extract(arc, out, scripts_only=True) == 1
        assert os.path.exists(os.path.join(out, "сцены", "глава.rpy"))


def test_rpa_index_cannot_execute_code():
    import zlib, pickle

    class Boom(object):
        def __reduce__(self):
            return (os.getcwd, ())

    blob = zlib.compress(pickle.dumps({"a.rpy": Boom()}, protocol=2))
    header = b"RPA-3.0 %016x %08x\n" % (34, 0)
    assert len(header) == 34
    with tempfile.TemporaryDirectory() as tmp:
        arc = os.path.join(tmp, "a.rpa")
        with open(arc, "wb") as f:
            f.write(header + blob)
        try:
            rpa.extract(arc, os.path.join(tmp, "out"))
        except pickle.UnpicklingError:
            pass
        else:
            raise AssertionError("индекс с глобалом должен отклоняться")


def test_manifest_save_is_atomic_and_keeps_backup():
    games_, G, ACCENT = manifest.load_games()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "games_data.py")
        manifest.save_games(games_, G, ACCENT, path=path)
        first = open(path, encoding="utf-8").read()
        assert not os.path.exists(path + ".bak") and not os.path.exists(path + ".tmp")
        games_[manifest.next_index(games_)] = {"title": "N", "root": "X:/n/game"}
        manifest.save_games(games_, G, ACCENT, path=path)
        assert open(path + ".bak", encoding="utf-8").read() == first
        assert (
            _parse_manifest_text(open(path, encoding="utf-8").read())[0].keys()
            == games_.keys()
        )
        assert not os.path.exists(path + ".tmp")


def test_manifest_find_by_root_ignores_slashes_and_case():
    g = {2: {"root": "D:/Games/Foo/game"}}
    assert manifest.find_by_root(g, "d:\\games\\foo\\game\\") == 2 or os.name != "nt"
    assert manifest.find_by_root(g, "D:/Games/Foo/game") == 2
    assert manifest.find_by_root(g, "D:/Games/Bar/game") is None


def test_analysis_parse_candidates_all_line_kinds():
    text = "\n".join(
        [
            "# game_1: шапка",
            "## STAT-LIKE",
            "money = 100",
            "[Stats] | путь: state.ps",
            "    level -> state.ps.level",
            "    x -> <Owner>.attr.x",
            "pdata: empathy=5, focus=10",
            "src/a.rpy:12:  def add_item(self, item):",
            "$gold   [num]   ->   State.variables.gold",
        ]
    )
    assert analysis.parse_candidates(text) == [
        ("money", "money"),
        ("level", "state.ps.level"),
        ("empathy", 'pdata["empathy"]'),
        ("focus", 'pdata["focus"]'),
        ("gold", "State.variables.gold"),
    ]


def test_analysis_dump_skips_own_menu_and_reads_inline_dict_head():
    orig = analysis.ana_dir, analysis.cand_file, analysis.CAND_DIR
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        with open(os.path.join(src, "script.rpy"), "w", encoding="utf-8") as f:
            f.write(
                'default money = 5\ndefine pdata = {"empathy": 5,\n    "focus": 10}\n'
                "default after_dict = 1\n"
            )
        with open(
            os.path.join(src, "zzz_testmenu_engine.rpy"), "w", encoding="utf-8"
        ) as f:
            f.write("default tm_stat_step = 1\ndefault level_from_menu = 3\n")
        out = os.path.join(tmp, "cand.txt")
        analysis.ana_dir = lambda i: src
        analysis.cand_file = lambda i: out
        analysis.CAND_DIR = tmp
        try:
            analysis.dump(1)
        finally:
            analysis.ana_dir, analysis.cand_file, analysis.CAND_DIR = orig
        body = open(out, encoding="utf-8").read()
    assert "money = 5" in body and "after_dict = 1" in body
    assert "pdata: empathy=5, focus=10" in body  # ключ на строке заголовка не потерян
    assert "level_from_menu" not in body and "tm_stat_step" not in body
    assert "{{" not in body


def test_inject_keeps_line_endings_and_backs_up_original():
    ti = _load_twine_inject()
    original = (
        b"<html>\n<body>\n<p>hi</p>\n</body>\n</html>\n"  # LF, как у собранной игры
    )
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "g.html")
        with open(html, "wb") as f:
            f.write(original)
        ti.deploy_file(html)
        ti.deploy_file(html)  # повтор не перетирает бэкап внедрённой версией
        with open(html + ".tm_bak", "rb") as f:
            assert f.read() == original
        ti.remove_file(html)
        with open(html, "rb") as f:
            cleaned = f.read()
    assert cleaned == original, "внедрение + удаление должно вернуть файл байт-в-байт"


def test_report_exit_code_counts_problems():
    from tmkit import report
    import io, contextlib

    saved = report._problems
    try:
        report._problems = 0
        with contextlib.redirect_stdout(io.StringIO()):
            report.ok(1, "x")
            report.warn(1, "x")
            report.info(1, "x")
            assert report.exit_code() == 0
            report.bad(1, "x")
            assert report.exit_code() == 1
    finally:
        report._problems = saved


def test_games_path_helpers_work_without_manifest_entry():
    # студия зовёт *_of(root) для игр, которых нет в games.GAMES (добавлены в сеансе)
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "game").replace("\\", "/")
        open(os.path.join(tmp, "g.py"), "w").close()
        for arch in ("py3-windows-i686", "py3-windows-x86_64"):
            os.makedirs(os.path.join(tmp, "lib", arch))
            open(os.path.join(tmp, "lib", arch, "python.exe"), "w").close()
        assert os.path.basename(games.launcher_of(root)) == "g.py"
        assert "x86_64" in games.python_exe_of(root)
        assert os.path.samefile(games.basedir_of(root), tmp)


def test_engine_rpy_escapes_values_shown_as_text():
    eng = open(os.path.join(ROOT, "zzz_testmenu_engine.rpy"), encoding="utf-8").read()
    assert "def tm_q(" in eng and "def tm_fmt(" in eng
    # значение/метка/путь в text — только через !q или tm_fmt (иначе «[x]»/«{b}» роняют экран)
    for bad in (
        'text "[val]"',
        'text "[label]"',
        'text "[_p]"',
        'text "[_msg]"',
        'textbutton "[label]"',
        '"%s → %s" %',
        "для [%s]",
    ):
        assert bad not in eng, f"неэкранированный вывод: {bad}"


def test_menu_core_isolates_input_from_game():
    core = open(
        os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"), encoding="utf-8"
    ).read()
    assert (
        "isTyping" in core and 'e.code === "KeyT"' in core
    )  # T в поле ввода — текст; RU-раскладка
    assert (
        "SWALLOW" in core and "stopPropagation" in core
    )  # мышь/клавиши не уходят в игру
    rp = open(
        os.path.join(ROOT, "engines", "rpgmaker", "tm_menu.js"), encoding="utf-8"
    ).read()
    assert "window.$game" not in rp  # MZ: глобалы через let, не window.*


# --------------------------------------------------------------- статус установки / doctor


def test_deploy_status_none_stale_ok():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "game")
        os.makedirs(root)
        engine_src = os.path.join(tmp, "engine.rpy")
        with open(engine_src, "w", encoding="utf-8", newline="") as f:
            f.write("# engine v2\r\n")
        assert tmdeploy.status(root, "data", engine_src=engine_src) == "none"
        with open(
            os.path.join(root, tmdeploy.ENGINE_NAME), "w", encoding="utf-8", newline=""
        ) as f:
            f.write("# engine v1\n")
        assert tmdeploy.status(root, engine_src=engine_src) == "stale"  # старый движок
        with open(
            os.path.join(root, tmdeploy.ENGINE_NAME), "w", encoding="utf-8", newline=""
        ) as f:
            f.write("# engine v2\n")  # LF против CRLF — не разница
        assert tmdeploy.status(root, engine_src=engine_src) == "ok"
        assert (
            tmdeploy.status(root, "data", engine_src=engine_src) == "stale"
        )  # data нет/другой
        with open(os.path.join(root, tmdeploy.DATA_NAME), "w", encoding="utf-8") as f:
            f.write("data")
        assert tmdeploy.status(root, "data", engine_src=engine_src) == "ok"


def test_render_game_matches_render_and_takes_own_manifest():
    i = sorted(generate.GAMES)[0]
    assert generate.render_game(i, generate.GAMES[i]) == generate.render(i)
    body = generate.render_game(7, {"title": "Своя", "stats": [("A", "a")]}, "#123456")
    assert 'store.tm_title = "Своя"' in body and 'store.tm_accent = "#123456"' in body


def test_inject_is_current_detects_outdated_block():
    ti = _load_twine_inject()
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "g.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write("<html><body></body></html>")
        assert not ti.is_current(html)
        ti.deploy_file(html)
        assert ti.is_current(html)
        with open(html, encoding="utf-8", newline="") as f:
            text = f.read()
        with open(html, "w", encoding="utf-8", newline="") as f:
            f.write(text.replace("scanNarrow", "scanNarrowOld"))  # «старая версия»
        assert ti.is_installed(html) and not ti.is_current(html)


def test_tm_doctor_runs_and_list_shows_status():
    import io, contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        tm.main(["doctor"])
        tm.main(["list"])
    out = buf.getvalue()
    assert "движок:" in out and "unrpyc" in out
    for i in games.GAMES:
        assert f"game_{i}:" in out


def test_engine_rpy_menu_state_is_not_rolled_back():
    eng = open(os.path.join(ROOT, "zzz_testmenu_engine.rpy"), encoding="utf-8").read()
    assert "class _TmUI(NoRollback)" in eng and "tm_ui = _TmUI()" in eng
    # состояние меню не должно жить в откатываемых store-переменных
    for old in (
        "default tm_open",
        "default tm_tab",
        'SetVariable("tm_',
        'VariableInputValue("tm_',
    ):
        assert old not in eng, f"осталось откатываемое состояние: {old}"
    assert "def tm_freeze_toggle(" in eng and "interact_callbacks" in eng
    assert "def tm_labels(" in eng


# --------------------------------------------------------------- быстрая установка / движок v2
def test_resolve_game_dir_accepts_root_game_and_exe():
    with tempfile.TemporaryDirectory() as d:
        game = os.path.join(d, "game")
        os.makedirs(game)
        exe = os.path.join(d, "Game.exe")
        open(exe, "w").close()
        assert tmdeploy.resolve_game_dir(d) == game
        assert tmdeploy.resolve_game_dir(game) == game
        assert tmdeploy.resolve_game_dir(exe) == game
        empty = os.path.join(d, "empty")
        os.makedirs(empty)
        assert tmdeploy.resolve_game_dir(empty) is None
        loose = os.path.join(d, "loose")  # скрипты прямо в папке
        os.makedirs(loose)
        open(os.path.join(loose, "script.rpyc"), "w").close()
        assert tmdeploy.resolve_game_dir(loose) == loose


def test_quick_install_engine_only_keeps_data_and_cleans_rpyc():
    with tempfile.TemporaryDirectory() as d:
        game = os.path.join(d, "game")
        os.makedirs(game)
        data = os.path.join(game, tmdeploy.DATA_NAME)
        with open(data, "w", encoding="utf-8") as f:
            f.write("# user data\n")
        stale = os.path.join(game, "zzz_testmenu_engine.rpyc")
        open(stale, "w").close()
        root = tmdeploy.quick_install(d)
        assert root == game
        assert os.path.exists(os.path.join(game, tmdeploy.ENGINE_NAME))
        assert not os.path.exists(stale)
        with open(data, encoding="utf-8") as f:
            assert f.read() == "# user data\n"  # data-файл не тронут
        assert tmdeploy.status(game) in ("ok", "stale")
        try:
            tmdeploy.quick_install(os.path.join(d, "nope"))
        except ValueError:
            pass
        else:
            raise AssertionError("ожидали ValueError для не-игры")


def test_tm_quick_cli_install_and_remove():
    with tempfile.TemporaryDirectory() as d:
        game = os.path.join(d, "game")
        os.makedirs(game)
        assert tm.main(["quick", d]) == 0
        assert os.path.exists(os.path.join(game, tmdeploy.ENGINE_NAME))
        assert tm.main(["quick", "--remove", d]) == 0
        assert not os.path.exists(os.path.join(game, tmdeploy.ENGINE_NAME))
        assert tm.main(["quick", os.path.join(d, "missing")]) == 1


def _engine_text():
    with open(os.path.join(ROOT, "zzz_testmenu_engine.rpy"), encoding="utf-8") as f:
        return f.read()


def test_engine_v2_features_present():
    eng = _engine_text()
    for needle in (
        "def tm_auto_stats(",
        "def tm_menu_hints(",
        "def tm_pick_choice(",
        "screen tm_hints_panel(",
        "screen tm_hud(",
        "screen tm_tab_story(",
        "def tm_unlock_all(",
        "def tm_find_lines(",
        "def tm_k(",
        "style tm_vscrollbar",
        "shift_K_h",
    ):
        assert needle in eng, needle


def test_engine_screen_text_has_no_unescaped_brackets():
    # «[X]» в литерале text = подстановка переменной X -> NameError при показе
    import re

    bad = []
    for n, line in enumerate(_engine_text().splitlines(), 1):
        m = re.match(r'\s*text "([^"]*)"', line)
        if not m:
            continue
        for tok in re.findall(r"(?<!\[)\[([^\[\]]+)\]", m.group(1)):
            if not re.match(r"^[A-Za-z_][\w.]*(![a-z]+)?$", tok):
                bad.append((n, tok))
    assert not bad, bad


def test_trim_row_keeps_pairs_and_limits():
    assert manifest.trim_row(("A", "a")) == ("A", "a")
    assert manifest.trim_row(("A", "a", "", "")) == ("A", "a")
    assert manifest.trim_row(("A", "a", "1")) == ("A", "a", "1", "")
    assert manifest.trim_row(("A", "a", "", "x_max")) == ("A", "a", "", "x_max")
    assert manifest.trim_row(["A", "a", 0, 4]) == ("A", "a", "0", "4")


def test_manifest_and_data_roundtrip_with_limits():
    games = {
        1: {
            "title": "T",
            "root": "D:/x/game",
            "status": "",
            "stats": [
                ("— S —", ""),
                ("Lvl", "p.lvl", "1", "p.lvl_max"),
                ("Money", "money"),
            ],
            "actions": [("A", "money += 1")],
        }
    }
    text = manifest.dumps(games, "G", "#38e0c8")
    g2, _G, _A = _parse_manifest_text(text)
    assert g2[1]["stats"][1] == ("Lvl", "p.lvl", "1", "p.lvl_max")
    assert g2[1]["stats"][2] == ("Money", "money")
    assert manifest.dumps(g2, "G", "#38e0c8") == text  # идемпотентно
    data = generate.render_game(1, games[1])
    body = data[data.index("store.tm_stats = [") + len("store.tm_stats = ") :]
    body = body[: body.index("\n    ]") + 6]
    rows = ast.literal_eval(body.strip())
    assert rows[1] == ("Lvl", "p.lvl", "1", "p.lvl_max")
    assert rows[2] == ("Money", "money")


def test_validate_limits():
    ok = [("Lvl", "p.lvl", "1", "4"), ("X", "x", "", "p.x_max")]
    assert validate.check_limits(ok) == []
    bad = validate.check_limits([("Lvl", "p.lvl", "5", "1"), ("Y", "y", "1 +", "")])
    assert any("больше max" in s for s in bad)
    assert any("не разбирается" in s for s in bad)
    assert any("секция" in s for s in validate.check_limits([("— S —", "", "1", "")]))


def test_engine_has_limits():
    eng = _engine_text()
    for needle in (
        "def tm_clamp(",
        "def tm_limits(",
        "def _tm_auto_max(",
        "tm_stat_view(path, val)",
        "sensitive _cup",
        "lim = tm_clamp(path, value)",
    ):
        assert needle in eng, needle


def test_engine_does_not_inflate_rollback_log():
    # 100000 шагов отката раздували сейвы до сотен МБ и давали лаги на автосейве
    import re

    eng = _engine_text()
    for m in re.finditer(
        r"config\.(rollback_length|hard_rollback_limit)\s*=\s*([^\n]+)", eng
    ):
        nums = [int(x) for x in re.findall(r"\d+", m.group(2))]
        assert nums and max(nums) <= 1000, m.group(0)


def test_engine_hbox_has_no_xfill():
    # hbox + xfill в Ren'Py раздаёт остаток ширины промежуткам -> «разъехавшиеся» строки
    lines = _engine_text().splitlines()
    for n, line in enumerate(lines):
        if line.strip() == "hbox:":
            ind = len(line) - len(line.lstrip())
            for nxt in lines[n + 1 : n + 4]:
                if len(nxt) - len(nxt.lstrip()) <= ind:
                    break
                assert nxt.strip() != "xfill True", f"hbox с xfill, строка {n + 1}"


def test_engine_hint_regexes_parse_effects():
    # регэкспы подсказок выборов — выдернуть из движка и проверить на типичных строках
    import re

    eng = _engine_text()
    assign = re.search(r"_TM_ASSIGN_RE = _tm_re\.compile\((r'.*?')\)\n", eng).group(1)
    rx = re.compile(ast.literal_eval(assign))
    assert rx.match("alice_love += 2").groups() == ("alice_love", "+=", "2")
    assert rx.match('stats["charm"] -= 1').groups()[:2] == ('stats["charm"]', "-=")
    assert rx.match("girls[0].affection = 5").group(1) == "girls[0].affection"
    assert rx.match("a == b") is None


# --------------------------------------------------------------- 2026-10-03: пути, версии, студия


def test_remove_from_bracket_path():
    # «Game [v0.5]» — glob-шаблон; без glob.escape движок оставался в игре
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "Game [v0.5]", "game")
        os.makedirs(os.path.join(root, tmdeploy.UI_DIRNAME))
        for fn in ("zzz_testmenu_engine.rpy", "zzz_testmenu_engine.rpyc", "script.rpy"):
            open(os.path.join(root, fn), "w").close()
        assert tmdeploy.remove_from(root) == 3
        assert os.listdir(root) == ["script.rpy"]


def test_renpy_version_and_engine_text_old():
    # 6.99: версия в renpy/__init__.py (version_tuple), у input нет copypaste
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "renpy"))
        root = os.path.join(d, "game")
        os.makedirs(root)
        src = os.path.join(d, "engine.rpy")
        with open(src, "w", encoding="utf-8") as f:
            f.write("input value v length 30 copypaste True\n")
        assert tmdeploy.renpy_version(root) is None
        with open(os.path.join(d, "renpy", "__init__.py"), "w") as f:
            f.write("version_tuple = (6, 99, 14, 3)\n")
        assert tmdeploy.renpy_version(root) == (6, 99)
        assert "copypaste" not in tmdeploy.engine_text(root, src)
        with open(os.path.join(d, "renpy", "vc_version.py"), "w") as f:
            f.write("version = '8.5.3.26051504'\n")
        assert tmdeploy.renpy_version(root) == (8, 5)
        assert "copypaste True" in tmdeploy.engine_text(root, src)


def test_engine_tm_run_keeps_renpy_p():
    # _p — функция Ren'Py; tm_run убирал её вместе с временными именами циклов
    import re

    eng = _engine_text()
    body = eng[eng.index("def tm_run(") :]
    body = body[: body.index("\n    def ", 10)]
    m = re.search(r"for _tmp in \(([^)]*)\)", body)
    assert m, "нет списка временных имён"
    names = re.findall(r"\"(\w+)\"", m.group(1))
    assert names and "_p" not in names, names
    assert "not in before" in body


def test_engine_isinstance_uses_builtin_types():
    # в сторе Ren'Py list/dict — Revertable-версии: isinstance(x, list) ложен для
    # config.interact_callbacks и __dict__ объектов (колбэк меню не регистрировался)
    import re

    eng = _engine_text()
    bad = re.findall(r"isinstance\([^()]*(?:\([^()]*\))?[^()]*,\s*(?:list|dict)\)", eng)
    assert not bad, bad
    assert "_TM_LIST = _tm_bi.list" in eng and "_TM_DICT = _tm_bi.dict" in eng


def test_engine_theme_reapplied_on_interact():
    # Ren'Py пересобирает стили после start_callbacks — тема накладывается заново
    eng = _engine_text()
    body = eng[eng.index("def _tm_on_interact(") :][:200]
    assert "_tm_theme_check()" in body


def test_default_title_strips_versions():
    cases = {
        "D:/G/Game [v0.5]/game": "Game",
        "D:/G/Game-0.5-pc/game": "Game",
        "D:/G/My_Game v1.2b/game": "My Game",
        "D:/G/Star Harbor 0.9.1/game": "Star Harbor",
        "D:/G/Moonlight Academy/game": "Moonlight Academy",
        "D:/G/{x}/game": "x",
        "D:/G/Version2/game": "Version2",
    }
    for root, want in cases.items():
        assert manifest.default_title(root) == want, (
            root,
            manifest.default_title(root),
        )
    assert manifest.default_title("") == "TEST MENU"


def test_pick_exe_skips_helpers():
    with tempfile.TemporaryDirectory() as d:
        folder = os.path.join(d, "Cool Game")
        os.makedirs(folder)
        for fn, size in (
            ("notification_helper.exe", 900),
            ("UnityCrashHandler64.exe", 900),
            ("unins000.exe", 900),
            ("small.exe", 10),
            ("big.exe", 500),
        ):
            with open(os.path.join(folder, fn), "wb") as f:
                f.write(b"x" * size)
        assert os.path.basename(games.pick_exe(folder)) == "big.exe"
        open(os.path.join(folder, "Cool Game.exe"), "w").close()
        assert os.path.basename(games.pick_exe(folder)) == "Cool Game.exe"
        open(os.path.join(folder, "Game.exe"), "w").close()
        assert os.path.basename(games.pick_exe(folder)) == "Game.exe"
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "notification_helper.exe"), "w").close()
        assert games.pick_exe(d) is None


def test_web_injectors_bundle_icons():
    # значки web-меню (data-URI) идут перед ядром; без эмодзи в ядре
    for eng in ("twine", "rpgmaker"):
        mod = engines._load_inject(eng)
        js = mod._menu_js()
        assert "var TM_ICONS" in js
        assert js.index("var TM_ICONS") < js.index("mkIco")
    core = open(
        os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"), encoding="utf-8"
    ).read()
    for ch in "\u270e\u2744\u21c4\u2715\u2713\U0001f4f7":
        assert ch not in core, repr(ch)


# --------------------------------------------------------------- web: кодировки, плагин RPG Maker

_MV_PLUGINS = (
    "// Generated by RPG Maker.\n"
    "// Do not edit this file directly.\n"
    "var $plugins =\n"
    "[\n"
    '{"name":"Community_Basic","status":true,"description":"Базовые настройки",'
    '"parameters":{"cacheLimit":"20","screenWidth":"816"}},\n'
    '{"name":"MadeWithMv","status":false,"description":"Show a Splash Screen \\"Made with MV\\"",'
    '"parameters":{"Show Made With MV":"true"}}\n'
    "];\n"
)


def _mk_mv_game(root, www=True):
    base = os.path.join(root, "www") if www else root
    os.makedirs(os.path.join(base, "js", "plugins"))
    with open(os.path.join(base, "index.html"), "w", encoding="utf-8") as f:
        f.write("<html><body><script src='js/main.js'></script></body></html>")
    with open(os.path.join(base, "js", "plugins.js"), "w", encoding="utf-8") as f:
        f.write(_MV_PLUGINS)
    open(os.path.join(base, "js", "rpg_core.js"), "w").close()
    return base


def test_htmlio_detects_and_roundtrips_encodings():
    io = engines._load_engine_module("_shared", "tm_htmlio.py")
    cp = '<html><head><meta charset="windows-1251"></head><body>Привет</body></html>'
    assert io.detect_encoding(cp.encode("cp1251")) == "cp1251"
    assert io.detect_encoding(b"\xef\xbb\xbf<html>") == "utf-8-sig"
    assert io.detect_encoding("ok ё".encode("utf-8")) == "utf-8"
    raw = bytes(range(256))  # не UTF-8 и без meta — обратимый latin-1
    enc = io.detect_encoding(raw)
    assert raw.decode(enc).encode(enc) == raw
    js = 'toast("Готово 🙂");'
    out = io.ascii_js(js)
    assert out.isascii() and "\\u0413" in out and "\\ud83d\\ude42" in out
    assert io.js_for("utf-8", js) == js and io.js_for("cp1251", js) == out


def test_twine_inject_keeps_cp1251_page():
    ti = _load_twine_inject()
    page = (
        '<html><head><meta http-equiv="Content-Type" content="text/html; '
        'charset=windows-1251"></head>\r\n<body>Привет, мир</body></html>'
    )
    orig = page.encode("cp1251")
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, "g.html")
        with open(html, "wb") as f:
            f.write(orig)
        ti.deploy_file(html)  # раньше: UnicodeDecodeError
        raw = open(html, "rb").read()
        text = raw.decode("cp1251")
        assert "Привет, мир" in text and "\r\n<body>" in text
        start = text.index(ti.MARK_START)
        assert text[start:].split(ti.MARK_END)[0].isascii()
        assert ti.is_installed(html) and ti.is_current(html)
        ti.remove_file(html)
        assert open(html, "rb").read() == orig


def test_rpgmaker_installs_as_plugin():
    ri = engines._load_inject("rpgmaker")
    with tempfile.TemporaryDirectory() as tmp:
        base = _mk_mv_game(tmp)
        pjs = os.path.join(base, "js", "plugins.js")
        idx = os.path.join(base, "index.html")
        idx_before = open(idx, "rb").read()
        assert engines.detect_engine(tmp).key == "rpgmaker"
        assert ri.is_installed(tmp) is False
        ri.deploy_file(tmp)
        ri.deploy_file(tmp)  # повтор не дублирует строку
        arr = ri._parse_plugins(open(pjs, encoding="utf-8").read())[2]
        assert [p["name"] for p in arr] == ["Community_Basic", "MadeWithMv", "TM_Menu"]
        assert arr[0]["description"] == "Базовые настройки"
        assert 'Splash Screen \\"Made with MV\\"' in open(pjs, encoding="utf-8").read()
        pf = os.path.join(base, "js", "plugins", "TM_Menu.js")
        body = open(pf, encoding="utf-8").read()
        assert body.isascii() and "window.TM_ADAPTER" in body and "var TM_ICONS" in body
        assert open(idx, "rb").read() == idx_before  # index.html не тронут
        assert ri.is_installed(tmp) and ri.is_current(tmp)
        ri.remove_file(tmp)
        assert not os.path.exists(pf) and ri.is_installed(tmp) is False
        arr = ri._parse_plugins(open(pjs, encoding="utf-8").read())[2]
        assert [p["name"] for p in arr] == ["Community_Basic", "MadeWithMv"]


def test_rpgmaker_plugin_replaces_old_html_block():
    ri = engines._load_inject("rpgmaker")
    with tempfile.TemporaryDirectory() as tmp:
        base = _mk_mv_game(tmp, www=False)
        idx = os.path.join(base, "index.html")
        text = open(idx, encoding="utf-8").read()
        with open(idx, "w", encoding="utf-8") as f:
            f.write(ri.inject(text, "/* old menu */"))
        assert ri.is_installed(tmp)
        ri.deploy_file(tmp)
        assert ri.MARK_START not in open(idx, encoding="utf-8").read()
        assert ri.is_current(tmp)


def test_rpgmaker_unpacks_package_nw():
    import zipfile

    ri = engines._load_inject("rpgmaker")
    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, "package.nw")
        with zipfile.ZipFile(pkg, "w") as z:
            z.writestr("package.json", '{"main":"index.html"}')
            z.writestr("index.html", "<html><body></body></html>")
            z.writestr("js/plugins.js", _MV_PLUGINS)
            z.writestr("js/rpg_core.js", "")
            z.writestr("data/System.json", "{}")
        open(os.path.join(tmp, "Game.exe"), "w").close()
        assert engines.detect_engine(tmp).key == "rpgmaker"
        msg = ri.deploy_file(tmp)
        assert "package.nw" in msg
        assert os.path.isdir(pkg) and zipfile.is_zipfile(pkg + ".tm_bak")
        assert os.path.exists(os.path.join(pkg, "js", "plugins", "TM_Menu.js"))
        assert ri.is_installed(tmp) and ri.is_current(tmp)
        assert engines.detect_engine(tmp).key == "rpgmaker"
        assert engines._load_engine_module("rpgmaker", "scan.py").find_data_dir(tmp)
        ri.remove_file(tmp)
        assert ri.is_installed(tmp) is False and os.path.isdir(
            pkg
        )  # сейвы внутри — папку не трогаем


def test_rpgmaker_rejects_zip_slip():
    import zipfile

    ri = engines._load_inject("rpgmaker")
    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, "package.nw")
        with zipfile.ZipFile(pkg, "w") as z:
            z.writestr("../evil.js", "x")
            z.writestr("js/rpg_core.js", "")
        try:
            ri.deploy_file(tmp)
            raise AssertionError("должно упасть")
        except ValueError:
            pass
        assert zipfile.is_zipfile(pkg) and not os.path.exists(
            os.path.join(os.path.dirname(tmp), "evil.js")
        )


# --------------------------------------------------------------- обучение


def test_engine_has_help_popup():
    import re

    eng = _engine_text()
    assert "screen tm_help_popup():" in eng and "use tm_help_popup" in eng
    assert 'SetField(tm_ui, "help_open", True)' in eng  # кнопка «?» в шапке
    assert "tm_help_seen" in eng  # первый раз открывается сама
    body = eng[eng.index("TM_HELP = [") :]
    body = body[: body.index("\n    ]\n")]
    texts = "".join(re.findall(r'u"([^"]*)"', body))
    assert len(texts) > 200
    for ch in "[]{}":  # теги/подстановки Ren'Py в текстах справки ломают text
        assert ch not in texts, ch


def test_studio_tour_steps_are_well_formed():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        import PyQt6  # noqa: F401  (студия; тестам он не обязателен — в CI его нет)
    except ImportError:
        return
    import studio_tour

    st = studio_tour.steps()
    assert len(st) >= 8
    for s in st:
        assert s.title and s.text
        assert os.path.exists(
            os.path.join(ROOT, "assets", "icons", s.mascot + ".png")
        ), s.mascot


# --------------------------------------------------------------- понятные имена


def test_naming_vocabulary_comes_from_engine():
    from tmkit import naming

    words, generic = naming.vocabulary()
    assert words["love"] == "симпатия" and words["money"] == "деньги"
    assert "player" in generic and len(words) > 150


def test_naming_nice_labels():
    from tmkit import naming

    ch = {"alice": "Alice", "anna": "Anna"}
    cases = [
        (("alice_love", "alice_love"), ("Alice | Симпатия", True)),
        (("met_alice", "met_alice"), ("Alice | Встреча", True)),
        (("girls[Anna].love", "girls[0].love"), ("Anna | Симпатия", True)),
        (('stats["charm"]', 'stats["charm"]'), ("Обаяние", True)),
        (('inv["apple"]', 'inv["apple"]'), ("Инвентарь: apple", True)),
        (("playerMoney", "playerMoney"), ("Деньги", True)),
        (("affectionLevel", "affectionLevel"), ("Привязанность уровень", True)),
        (("xyz_foo", "xyz_foo"), ("Xyz foo", False)),
        (("timeline", "timeline"), ("Timeline", False)),  # time + line — не окончание
        (("ammo", "ammo"), ("Патроны", True)),  # слова экшен-игр
        (("lovePoints", "lovePoints"), ("Симпатия очки", True)),
        (("dominant", "dominant"), ("Доминирование", True)),  # основа domin-
        (("Деньги Алисы", "alice_money"), ("Деньги Алисы", True)),  # подпись из студии
    ]
    for (label, path), want in cases:
        assert naming.nice(label, path, ch) == want, (
            label,
            naming.nice(label, path, ch),
        )
    assert naming.nice("hp", "hp", ch, {"hp": "Здоровье героя"}) == (
        "Здоровье героя",
        True,
    )


def test_naming_characters_and_user_names():
    from tmkit import naming

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "script.rpy"), "w", encoding="utf-8") as f:
            f.write(
                'define a = Character("Alice Smith", color="#f00")\n'
                'define m = Character(_("Mom"))\n'
                'define n = Character("[pname]")\n'
            )
        ch = naming.characters(d)
        assert ch["alice"] == "Alice Smith" and ch["mom"] == "Mom"
        assert not any("[" in v for v in ch.values())
        assert naming.user_names(d) == {}
        with open(os.path.join(d, "tm_names.json"), "w", encoding="utf-8") as f:
            f.write('{"hp": "\u0425\u041f"}')
        assert naming.user_names(d) == {"hp": "ХП"}


def test_candidates_annotation_roundtrip():
    from tmkit import naming

    text = "# STAT-LIKE\nalice_love = 3\nxyz = 1\nGirl.love -> anna.love\n"
    out = naming.annotate(
        text, analysis.parse_candidates, {"alice": "Alice", "anna": "Anna"}
    )
    assert "alice_love = 3  // Alice | Симпатия" in out
    assert "xyz = 1  // " not in out  # ничего не переведено — подсказка не нужна
    assert "anna.love  // Anna | Симпатия" in out  # «->»: имя по пути, а не по классу
    assert (
        naming.label_for("Girl.love", "anna.love", {"anna": "Anna"})
        == "Anna | Симпатия"
    )
    part = naming.annotate("girl_love = 1", analysis.parse_candidates)
    assert part.endswith("(догадка)"), part
    # подсказка не попадает в путь при «в Характеристики»
    assert analysis.parse_candidates(out) == analysis.parse_candidates(text)


def test_engine_has_meaning_layer():
    eng = _engine_text()
    for fn in (
        "def _tm_usage(",
        "def tm_nice(",
        "def tm_meaning(",
        "def tm_thresholds(",
        "def tm_group_of(",
        "def tm_set_name(",
        "def tm_rename(",
    ):
        assert fn in eng, fn
    assert "tm_names.json" in eng and 'style "tm_name_btn"' in eng
    assert "Function(tm_to_threshold" in eng  # кнопка «до порога»
    # re.split по пустому совпадению на py2 не режет — владелец ищется по позициям
    body = eng[eng.index("def _tm_obj_name(") :][:600]
    assert "finditer" in body and "(?=" not in body


# --------------------------------------------------------------- Godot / Unity в реестре


def _mk_fake_pck(path, files):
    """Минимальный .pck формата 2 (Godot 4) с текстовыми файлами."""
    import struct

    entries = [("res://" + n, t.encode()) for n, t in files.items()]
    head = (
        struct.pack("<4sIIII", b"GDPC", 2, 4, 2, 2)
        + struct.pack("<IQ", 0, 0)
        + b"\0" * 64
    )
    dir_size = 4 + sum(4 + len(n.encode()) + 16 + 16 + 4 for n, _ in entries)
    base = len(head) + dir_size
    head = head[:20] + struct.pack("<IQ", 0, base) + head[32:]
    d, data, ofs = struct.pack("<I", len(entries)), b"", 0
    for n, b in entries:
        nb = n.encode()
        d += (
            struct.pack("<I", len(nb))
            + nb
            + struct.pack("<QQ", ofs, len(b))
            + b"\0" * 16
            + struct.pack("<I", 0)
        )
        data += b
        ofs += len(b)
    with open(path, "wb") as f:
        f.write(head + d + data)


def test_godot_and_unity_detect_and_scan():
    with tempfile.TemporaryDirectory() as tmp:
        g = os.path.join(tmp, "MyGodot")
        os.makedirs(g)
        open(os.path.join(g, "Game.exe"), "wb").close()
        _mk_fake_pck(
            os.path.join(g, "Game.pck"),
            {
                "dialogic/timelines/bar.dtl": "if {Stats.money} >= 200:\n\tset {Stats.love} += 1\n",
            },
        )
        assert engines.detect_engine(g).key == "godot"
        rep = engines.REGISTRY["godot"].scan(g)
        assert "Stats.money" in rep and ">= 200" in rep and "Stats.love" in rep
        u = os.path.join(tmp, "MyUnity")
        os.makedirs(u)
        open(os.path.join(u, "UnityPlayer.dll"), "wb").close()
        open(
            os.path.join(u, "Game.pck"), "wb"
        ).close()  # .pck рядом не делает её Godot-игрой
        assert engines.detect_engine(u).key == "unity"
        assert manifest.default_title(u) == "MyUnity"  # не родитель, а сама папка
        assert (
            manifest.default_title(os.path.join(tmp, "RenGame-1.0", "game"))
            == "RenGame"
        )


def test_quick_install_any_routes_to_engine():
    with tempfile.TemporaryDirectory() as tmp:
        g = os.path.join(tmp, "MyGodot")
        os.makedirs(g)
        open(os.path.join(g, "Game.exe"), "wb").close()
        _mk_fake_pck(os.path.join(g, "Game.pck"), {"project.binary": "x"})
        eng, root, msg = engines.quick_install_any(os.path.join(g, "Game.exe"))
        assert eng.key == "godot" and os.path.exists(os.path.join(g, "override.cfg"))
        assert engines.REGISTRY["godot"].current(g)
        eng, _r, _m = engines.quick_remove_any(g)
        assert not os.path.exists(
            os.path.join(g, "override.cfg")
        ) and not os.path.isdir(os.path.join(g, "tm_godot"))


# --------------------------------------------------------------- движок: инструменты тестера (2026-10-04)


def test_remove_from_cleans_state_and_quick_slots_keeps_user_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "Game [v1]", "game")
        os.makedirs(os.path.join(root, "saves"))
        for name in ("zzz_testmenu_engine.rpy", "tm_state.json", "tm_names.json"):
            open(os.path.join(root, name), "w").close()
        for name in ("tm_quick_1-LT1.save", "1-1-LT1.save"):
            open(os.path.join(root, "saves", name), "w").close()
        assert tmdeploy.remove_from(root) == 3
        assert not os.path.exists(os.path.join(root, "tm_state.json"))
        assert not os.path.exists(os.path.join(root, "saves", "tm_quick_1-LT1.save"))
        assert os.path.exists(os.path.join(root, "saves", "1-1-LT1.save")), (
            "сейв игрока"
        )
        assert os.path.exists(os.path.join(root, "tm_names.json")), "свои имена"


def test_engine_tester_tools_present():
    eng = _engine_text()
    for needle in (
        "def tm_undo(",  # журнал правок и отмена
        'key "ctrl_K_z"',
        "screen tm_edit_popup(",  # ввод в окне меню, не renpy.input
        "TM_FREEZE_MODES",  # заморозка = / ≥ / ≤
        "periodic_callbacks",  # заморозка между взаимодействиями
        "def tm_fav_toggle(",  # избранное
        "tm_state.json",  # состояние между запусками
        "def _tm_take_seen(",  # изменилось с прошлого открытия
        "def _tm_menu_wrap(",  # история выборов
        "def tm_cond_now(",  # условие скрытого варианта со значениями
        "TM_SPOIL_MODES",  # режимы спойлеров
        "def tm_screen_buttons(",  # кнопки экранов
        "screen tm_toasts(",  # свои уведомления
        "def tm_hud_flash(",  # вспышки HUD
        "screen tm_mini(",  # мини-режим
        "def tm_alt_key(",  # настраиваемая клавиша
        "screen tm_where_popup(",  # «Где я»
        "def tm_replay(",  # повтор сцены
        "def tm_write_report(",  # отчёт тестера
        "def tm_scan_back(",  # шаг назад в сканере
        "def tm_scan_by(",  # «изменилось на N»
        "def tm_purge(",  # убрать следы
    ):
        assert needle in eng, needle
    # notify только как запасной путь внутри tm_note
    assert eng.count("renpy.notify(") == 1
    # старый ввод через новый контекст убран
    assert "invoke_in_new_context(\n                renpy.input" not in eng


def test_engine_menu_wrap_reinstalls_and_keeps_original():
    eng = _engine_text()
    assert '_tm_menu_orig", None) is None' in eng, "оригинал запоминается один раз"
    assert "_tm_install_menu_wrap()" in eng.split("def tm_register():", 1)[1]


def test_engine_scanner_skips_modules_and_nan():
    eng = _engine_text()
    assert "isinstance(v, _TM_MODULE)" in eng
    assert "if v == v:" in eng


def test_engine_screen_scope_holds_only_plain_data():
    # переменные экранов пишутся в журнал отката и в сейв: узел сценария тянул за собой
    # весь сценарий по .next (RecursionError при сохранении большой игры, 2026-10-06)
    eng = _engine_text()
    screens = eng[eng.index("screen tm_icon(") :]
    for bad in ("= tm_cur_menu()", "= _tm_scan()", "= tm_screen_buttons(", "node.name"):
        assert bad not in screens, bad
    assert "def _tm_scrub_log(" in eng
    assert "_tm_scrub_log()" in eng.split("def _tm_on_start(", 1)[1][:300]


# --------------------------------------------------------------- твики игр (поле "tweak")


def test_tweak_is_appended_to_data_and_survives_dumps():
    from tmkit import generate, manifest
    from tmkit.validate import check_game

    with tempfile.TemporaryDirectory() as tmp:
        old = generate.TWEAKS_DIR
        generate.TWEAKS_DIR = tmp
        try:
            with open(
                os.path.join(tmp, "t.rpy"), "w", encoding="utf-8", newline=""
            ) as f:
                f.write("init 999 python:\r\n    zz_x = 1\r\n")
            g = {
                "title": "T",
                "root": "x",
                "stats": [],
                "actions": [],
                "tweak": "t.rpy",
            }
            text = generate.render_game(1, g)
            assert (
                "tweaks/t.rpy" in text and "    zz_x = 1\n" in text and "\r" not in text
            )
            assert check_game([], [], None, "t.rpy") == []
            assert check_game([], [], None, "nope.rpy") != []  # нет файла — проблема
            # без файла data рендерится без твика (не падает)
            g2 = dict(g, tweak="nope.rpy")
            assert "zz_x" not in generate.render_game(1, g2)
            # путь из манифеста — только имя внутри tweaks/
            assert generate.tweak_path("../evil.rpy") == os.path.join(tmp, "evil.rpy")
        finally:
            generate.TWEAKS_DIR = old
    text = manifest.dumps({1: g}, "G", "#38e0c8")
    assert "'tweak': 't.rpy'" in text
    ns = {}
    exec(compile(text, "games_data", "exec"), ns)
    assert ns["GAMES"][1]["tweak"] == "t.rpy"


def test_project_tweaks_exist_for_manifest():
    from tmkit import generate
    from tmkit.games_data import GAMES

    for i, g in GAMES.items():
        if g.get("tweak"):
            assert generate.tweak_text(g["tweak"]), (i, g["tweak"])


# --------------------------------------------------------------- раннер


def _run():
    tests = sorted(
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    )
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0




def test_engine_qa_tab_present():
    # вкладка «Тест» и прочие инструменты 2026-10-06
    eng = _engine_text()
    for needle in (
        "def tm_auto_start(",  # авто-прохождение
        "def _tm_auto_watch(",  # сторож: игра ждёт игрока
        "def tm_route_save(",  # маршруты
        "def _tm_route_prune(",  # откат стирает отменённые выборы
        "def tm_coverage(",  # покрытие
        "hash64",  # ключи просмотренного в 8.4+
        "def tm_scene_refs(",  # откуда сюда попадают
        "def tm_choice_code(",  # код варианта
        "def tm_bug_request(",  # заметка о баге
        "def tm_code_run(",  # свой код
        "def tm_hud_add_expr(",  # выражение в HUD
        "def tm_scan_name(",  # поиск по имени
        "def tm_rel_value(",  # +50 / *2
        "def tm_dialog_log(",  # лог реплик
        "RollbackToIdentifier(",
        "def tm_char_rename(",  # персонажи
        "def tm_values_export(",  # перенос значений
        "shift_K_b",
        "shift_K_F5",
        "screen tm_tab_test(",
        "screen tm_auto_badge(",
    ):
        assert needle in eng, needle
    # в 6.99 config.<незнакомое> бросает исключение — колбэки меток только через renpy.config
    assert 'getattr(config, "label_callback' not in eng
    # тег вкладки сохраняется в tm_state.json
    assert '"checklist", "settings"' in eng


def test_engine_relative_input_regex():
    import re

    eng = _engine_text()
    line = [l for l in eng.splitlines() if "_TM_REL_RE = " in l][0]
    pat = ast.literal_eval(line.split("compile(", 1)[1].rsplit(")", 1)[0])
    rx = re.compile(pat)
    assert rx.match("+50").groups() == ("+", "50")
    assert rx.match("-10").groups() == ("-", "10")
    assert rx.match("*2") and rx.match("/2,5") and rx.match("× 3")
    assert not rx.match("50") and not rx.match("=-5") and not rx.match("+abc")


def test_game_icons_for_new_tabs():
    for k in ("rocket", "flag", "checklist", "code", "download", "upload"):
        assert os.path.exists(os.path.join(ROOT, "assets", "tm_ui", "ic", k + ".png")), k
# --------------------------------------------------------------- Unity Mono и Unreal
# нужны скачанные tools/unity (fetch_unity_tools.py) и csc.exe — без них тест ничего не проверяет
def _fake_unity_player(path):
    import struct

    pe = bytearray(0x200)
    pe[0:2] = b"MZ"
    pe[0x3C:0x40] = struct.pack("<I", 0x80)
    pe[0x80:0x84] = b"PE\0\0"
    pe[0x84:0x86] = struct.pack("<H", 0x8664)
    open(path, "wb").write(bytes(pe))


def test_unity_mono_plugin_builds_and_deploys():
    import subprocess

    ui = engines._load_engine_module("unity", "inject.py")
    sys.path.insert(0, os.path.join(ROOT, "engines", "unity"))
    import mono_build

    csc = mono_build.csc_path()
    if not csc or not os.path.isdir(ui.BEPINEX5):
        return
    with tempfile.TemporaryDirectory() as tmp:
        game = os.path.join(tmp, "Game")
        managed = os.path.join(game, "Game_Data", "Managed")
        os.makedirs(managed)
        _fake_unity_player(os.path.join(game, "UnityPlayer.dll"))
        stub = os.path.join(ROOT, "tests", "fixtures", "unity_mono_stubs.cs")
        r = subprocess.run(
            [
                csc,
                "/nologo",
                "/target:library",
                "/out:" + os.path.join(managed, "UnityEngine.dll"),
                stub,
            ],
            capture_output=True,
        )
        assert r.returncode == 0, r.stdout
        e = engines.REGISTRY["unity"]
        assert engines.detect_engine(game).key == "unity"
        msg = e.deploy(game)
        assert "Mono" in msg
        menu = os.path.join(game, "BepInEx", "plugins", "TestMenu")
        assert os.path.isfile(os.path.join(menu, "TestMenu.Mono.dll"))
        assert os.path.isfile(os.path.join(game, "winhttp.dll"))
        assert e.installed(game) and e.current(game)
        e.uninstall(game)
        assert sorted(os.listdir(game)) == ["Game_Data", "UnityPlayer.dll"]


def test_unreal_deploy_remove_and_anticheat_guard():
    ue = engines._load_engine_module("unreal", "inject.py")
    with tempfile.TemporaryDirectory() as tmp:
        win64 = os.path.join(tmp, "MyGame", "Binaries", "Win64")
        os.makedirs(win64)
        open(os.path.join(win64, "MyGame-Win64-Shipping.exe"), "w").close()
        assert engines.detect_engine(tmp).key == "unreal"
        mods = ue._mods_txt(
            "CheatManagerEnablerMod : 0\nFoo : 1\n; Built-in keybinds, do not move up!\nKeybinds : 1\n"
        )
        assert "CheatManagerEnablerMod : 1" in mods and "Foo : 1" in mods
        assert mods.strip().splitlines()[-1] == "Keybinds : 1" and mods.index(
            "TestMenu : 1"
        ) < mods.index("; Built-in")
        if os.path.isdir(ue.UE4SS):
            e = engines.REGISTRY["unreal"]
            e.deploy(tmp)
            assert os.path.isfile(
                os.path.join(win64, "Mods", "TestMenu", "Scripts", "main.lua")
            )
            assert os.path.isfile(os.path.join(win64, "dwmapi.dll")) and e.current(tmp)
            e.uninstall(tmp)
            assert os.listdir(win64) == ["MyGame-Win64-Shipping.exe"]
        os.makedirs(os.path.join(tmp, "EasyAntiCheat"))
        try:
            ue.deploy_file(tmp)
            assert False, "античит не остановил установку"
        except ValueError as ex:
            assert "античит" in str(ex)


if __name__ == "__main__":
    sys.exit(_run())
