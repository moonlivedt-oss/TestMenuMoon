"""Ren'Py: меню (движок), установка и снятие, анализ исходников, .rpa, понятные имена, твики."""

from helpers import *  # noqa: F401,F403  (общие импорты и помощники)


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


def test_engine_rpy_escapes_values_shown_as_text():
    eng = _engine_text()
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


def test_engine_rpy_menu_state_is_not_rolled_back():
    eng = _engine_text()
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


def test_deploy_does_not_hide_menu_files():
    """Установка не прячет файлы меню: раньше знаковый результат GetFileAttributesW (-1 у
    несуществующего файла) читался как «скрытый», и после установки прятались все файлы."""
    if os.name != "nt":
        return
    import ctypes

    def hidden(p):
        return bool(ctypes.windll.kernel32.GetFileAttributesW(p) & 0xFFFFFFFF & 2)

    with tempfile.TemporaryDirectory() as tmp:
        game = os.path.join(tmp, "game")
        os.makedirs(game)
        open(os.path.join(game, "script.rpy"), "w").close()
        tmdeploy.quick_install(game)
        eng = os.path.join(game, tmdeploy.ENGINE_NAME)
        assert os.path.isfile(eng) and not hidden(eng)
        # а спрятанное пользователем остаётся спрятанным после переустановки
        ctypes.windll.kernel32.SetFileAttributesW(eng, 0x22)
        tmdeploy.quick_install(game)
        assert hidden(eng)
        ctypes.windll.kernel32.SetFileAttributesW(eng, 0x20)


def test_engine_has_change_journal():
    eng = _engine_text()
    for key in ("def _tm_log_tick", "_tm_log_tick()", "screen tm_log_popup", 'u"заморозка"',
                "== Журнал изменений", "self.changelog = []"):
        assert key in eng, key


def test_renpy_menu_english_is_complete_and_fresh():
    """Каждая русская строка меню Ren'Py есть в lang_en.json, у перевода те же подстановки,
    а 13_lang.rpy собран из текущего JSON (python tools/gen_renpy_lang.py)."""
    import importlib.util
    import re

    spec = importlib.util.spec_from_file_location("gen_lang", os.path.join(ROOT, "tools", "gen_renpy_lang.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    assert g.missing() == [], g.missing()[:10]
    d = json.load(open(g.SRC, encoding="utf-8"))
    ph = re.compile(r"%[sdr%]|\[\[|\[[^\[\]]+\]")
    bad = [k for k, v in d.items() if sorted(ph.findall(k)) != sorted(ph.findall(v))]
    assert not bad, bad[:10]
    rows = "".join("        %s: %s,\n" % (g.py_str(k), g.py_str(v)) for k, v in d.items())
    want = (g.HEAD + rows + g.TAIL).replace("\r\n", "\n")
    got = open(g.OUT, encoding="utf-8").read().replace("\r\n", "\n")
    assert got == want, "13_lang.rpy устарел: python tools/gen_renpy_lang.py"
