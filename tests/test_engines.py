"""Реестр движков и установщики: RPG Maker, HTML5, Twine, Godot, Unity, Unreal; веб-ядро меню."""

from helpers import *  # noqa: F401,F403  (общие импорты и помощники)


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


def test_engines_registry_capabilities():
    assert set(engines.REGISTRY) == {"renpy", "twine", "rpgmaker", "godot", "unity", "web", "unreal", "gamemaker"}
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
    assert '["game", T("Игра")]' in core and "function renderGame" in core and "requestAnimationFrame" in core
    rpgm = open(os.path.join(ROOT, "engines", "rpgmaker", "tm_menu.js"), encoding="utf-8").read()
    for key in ("speed: function", "cheats: function", "places:", "isDebugThrough", "canEncounter", "Отряд: "):
        assert key in rpgm, key
    web = open(os.path.join(ROOT, "engines", "web", "tm_menu.js"), encoding="utf-8").read()
    for key in ("speed: true", "cr_getC2Runtime", "renderAndStep", "registry"):
        assert key in web, key


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


def test_unity_mono_x86_game_gets_x86_loader():
    """32-битная Mono-игра: загрузчик winhttp.dll из BepInEx 5 x86, плагин тот же (AnyCPU)."""
    import subprocess

    ui = engines._load_engine_module("unity", "inject.py")
    mono_build = engines._load_engine_module("unity", "mono_build.py")
    csc = mono_build.csc_path()
    if not csc or not os.path.isdir(ui.BEPINEX5_X86):
        return
    with tempfile.TemporaryDirectory() as tmp:
        game = os.path.join(tmp, "Game")
        managed = os.path.join(game, "Game_Data", "Managed")
        os.makedirs(managed)
        _fake_unity_player(os.path.join(game, "UnityPlayer.dll"), 0x14C)
        stub = os.path.join(ROOT, "tests", "fixtures", "unity_mono_stubs.cs")
        r = subprocess.run([csc, "/nologo", "/target:library",
                            "/out:" + os.path.join(managed, "UnityEngine.dll"), stub], capture_output=True)
        assert r.returncode == 0, r.stdout
        msg = engines.REGISTRY["unity"].deploy(game)
        assert "x86" in msg, msg
        assert _pe_machine(os.path.join(game, "winhttp.dll")) == 0x14C
        engines.REGISTRY["unity"].uninstall(game)
        assert sorted(os.listdir(game)) == ["Game_Data", "UnityPlayer.dll"]


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


def test_rpgmaker_unpack_keeps_japanese_names():
    import zipfile

    ri = engines._load_inject("rpgmaker")
    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, "package.nw")
        with zipfile.ZipFile(pkg, "w") as z:
            z.writestr("index.html", "<html><body></body></html>")
            z.writestr("js/plugins.js", _MV_PLUGINS)
            z.writestr("js/rpg_core.js", "")
            z.writestr("data/System.json", "{}")
            z.writestr(_Cp932Info("img/pictures/立ち絵.png"), b"png")
        ri.deploy_file(tmp)
        assert os.path.isfile(os.path.join(pkg, "img", "pictures", "立ち絵.png"))
        assert os.path.isfile(os.path.join(pkg, "js", "plugins", "TM_Menu.js"))


def test_web_game_stays_web_after_menu_install():
    """В тексте меню есть «SugarCube»: после установки HTML5-игра не должна стать «Twine»."""
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "index.html"), "w").write("<html><body><canvas></canvas></body></html>")
        assert engines.detect_engine(tmp).key == "web"
        engines.REGISTRY["web"].deploy(tmp)
        assert engines.detect_engine(tmp).key == "web"


def test_web_unpacks_packed_nwjs_game():
    import zipfile

    with tempfile.TemporaryDirectory() as tmp:
        pkg = os.path.join(tmp, "package.nw")
        with zipfile.ZipFile(pkg, "w") as z:
            z.writestr("package.json", '{"main":"index.html"}')
            z.writestr("index.html", "<html><body><canvas></canvas></body></html>")
            z.writestr("c2runtime.js", "")
        open(os.path.join(tmp, "Game.exe"), "w").close()
        eng = engines.detect_engine(tmp)
        assert eng is not None and eng.key == "web", eng
        msg = eng.deploy(tmp)
        assert "package.nw" in msg and zipfile.is_zipfile(pkg + ".tm_bak")
        assert eng.installed(tmp) and eng.current(tmp)
        eng.uninstall(tmp)
        assert not eng.installed(tmp) and os.path.isdir(pkg)


def test_web_journal_where_and_construct3_present():
    core = open(os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"), encoding="utf-8").read()
    for key in ("function journalTick", 'jMark(fkey, T("меню"))', 'jMark(k, T("заморозка"))', "function whereDone"):
        assert key in core, key
    web = open(os.path.join(ROOT, "engines", "web", "tm_menu.js"), encoding="utf-8").read()
    for key in ("function tmwWatch", "where: function", "function tmwConstruct3", "c3_runtimeInterface", "globalVars"):
        assert key in web, key


def test_bridge_sync_delivers_commands_once():
    import json as _j
    import socket
    import urllib.request
    from tmkit import bridge

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    b = bridge.Bridge(port)
    assert b.start()
    try:
        def sync(state):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/sync", _j.dumps(state).encode(),
                                         {"Content-Type": "text/plain"})
            with urllib.request.urlopen(req, timeout=5) as r:
                assert r.headers["Access-Control-Allow-Origin"] == "*"
                return _j.loads(r.read())

        st = {"id": "g1", "title": "Игра", "rows": [{"k": "a", "v": 1}]}
        assert sync(st) == {"cmds": []}
        (cid, got, alive), = b.games()
        assert cid == "g1" and alive and got["rows"][0]["v"] == 1
        assert b.send("g1", "set", "a", 5) and b.send("g1", "speed", v=0)
        assert not b.send("нет такой", "step")
        assert sync(st)["cmds"] == [{"op": "set", "k": "a", "v": 5}, {"op": "speed", "v": 0}]
        assert sync(st)["cmds"] == []  # доставляется один раз
    finally:
        b.stop()
    for f, keys in ((("engines", "_shared", "tm_menu_core.js"), ("function bridgeTick", "47820", "Пульт в студии")),
                    (("engines", "renpy", "engine", "12_bridge.rpy"), ("TMB_PORT = 47820", "def _tm_bridge_periodic"))):
        text = open(os.path.join(ROOT, *f), encoding="utf-8").read()
        for k in keys:
            assert k in text, (f, k)


def _mk_fake_pck3(path, files):
    """Минимальный .pck формата 1 (Godot 3): без флагов пакета и записей."""
    import struct

    entries = [("res://" + n, t.encode()) for n, t in files.items()]
    head = struct.pack("<4sIIII", b"GDPC", 1, 3, 5, 1) + b"\0" * 64
    dir_size = 4 + sum(4 + len(n.encode()) + 16 + 16 for n, _ in entries)
    d, data, ofs = struct.pack("<I", len(entries)), b"", len(head) + dir_size
    for n, b in entries:
        nb = n.encode()
        d += struct.pack("<I", len(nb)) + nb + struct.pack("<QQ", ofs, len(b)) + b"\0" * 16
        data += b
        ofs += len(b)
    with open(path, "wb") as f:
        f.write(head + d + data)


def test_godot3_gets_gdscript1_menu_and_godot4_flies():
    gi = engines._load_engine_module("godot", "inject.py")
    with tempfile.TemporaryDirectory() as tmp:
        _mk_fake_pck3(os.path.join(tmp, "Game.pck"), {"project.binary": "x"})
        assert gi.godot_version(tmp)[0] == 3
        assert engines.detect_engine(tmp).key == "godot"
        msg = gi.deploy_file(tmp)
        assert "Godot 3.5.1" in msg, msg
        got = open(os.path.join(tmp, "tm_godot", "tm_menu.gd"), encoding="utf-8").read()
        assert got == open(gi.MENU_SRC3, encoding="utf-8").read()
        assert gi.is_installed(tmp) and gi.is_current(tmp)
        gi.remove_file(tmp)
        assert not gi.is_installed(tmp)
    g3 = open(gi.MENU_SRC3, encoding="utf-8").read()
    # GDScript 1: без лямбд и аннотаций Godot 4, сигналы через connect(сигнал, self, метод)
    for bad in ("func():", "@onready", "@export", "await ", "Callable(", "-> void"):
        assert bad not in g3, bad
    for need in ('connect("pressed", self, method, binds)', "yield(get_tree()", "Engine.time_scale", "TYPE_REAL"):
        assert need in g3, need
    g4 = open(gi.MENU_SRC, encoding="utf-8").read()
    for need in ("func _set_fly", "func _set_noclip", "set_physics_process(false)", "collision_mask = 0"):
        assert need in g4, need


def test_gamemaker_detect_script_and_guards():
    gm = engines._load_engine_module("gamemaker", "inject.py")
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "data.win"), "wb").write(b"FORM\0\0\0\0")
        open(os.path.join(tmp, "MyGame.exe"), "wb").write(b"MZ")
        assert engines.detect_engine(tmp).key == "gamemaker"
        assert not gm.is_installed(tmp) and gm.remove_file(tmp).endswith("(нет data.win.tm_bak)")
        if gm.cli_path() is None:
            try:
                gm.deploy_file(tmp)
                raise AssertionError("без UTMT установка должна отказаться")
            except FileNotFoundError as e:
                assert "UTMT_CLI" in str(e)
            assert not os.path.exists(os.path.join(tmp, "data.win.tm_bak"))
    csx = gm.script_text()
    assert "%CREATE%" not in csx and "%STEP%" not in csx and "%DRAW%" not in csx
    # GML в C#-строке @"…": кавычки удвоены, иначе скрипт UTMT не скомпилируется
    assert 'keyboard_check_pressed(ord(""T""))' in csx and 'ord("T")' not in csx
    assert "IsVersionAtLeast(2, 3)" in csx and "EventSubtypeDraw.DrawGUI" in csx


def _tm_en():
    text = open(os.path.join(ROOT, "engines", "_shared", "tm_lang.js"), encoding="utf-8").read()
    start = text.index("var TM_EN = ") + len("var TM_EN = ")
    return json.loads(text[start:text.index("\n};", start) + 2])


def test_web_menu_strings_have_english():
    """Каждая строка T("…") веб-меню есть в словаре tm_lang.js — иначе в EN останется русской."""
    import re

    en = _tm_en()
    missing = []
    for path in (("_shared", "tm_menu_core.js"), ("web", "tm_menu.js"), ("rpgmaker", "tm_menu.js"), ("twine", "tm_menu.js")):
        text = open(os.path.join(ROOT, "engines", *path), encoding="utf-8").read()
        for m in re.finditer(r'T\("((?:[^"\\]|\\.)*)"\)', text):
            key = json.loads('"' + m.group(1) + '"')
            if key not in en:
                missing.append((path[0], key))
    assert not missing, missing[:20]
    assert not [k for k, v in en.items() if not v], "пустые переводы"


def test_tokens_fresh_and_used():
    """Цвета меню и студии — из одного набора engines/_shared/tm_tokens.json: собранные файлы
    свежие (python tools/gen_tokens.py), а в ядрах не осталось прописанных вручную цветов набора."""
    import importlib.util
    import re

    spec = importlib.util.spec_from_file_location("gen_tok", os.path.join(ROOT, "tools", "gen_tokens.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    assert g.stale() == [], "устарели: %s — python tools/gen_tokens.py" % g.stale()
    cols = {v.lower()[:7] for k, v in g.load()["color"].items() if not k.startswith("tint_")}
    cols.discard("#ffffff")
    files = [os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"),
             os.path.join(ROOT, "tmstudio", "theme.py")]
    eng = os.path.join(ROOT, "engines", "renpy", "engine")
    files += [os.path.join(eng, n) for n in os.listdir(eng)
              if n.endswith(".rpy") and n not in ("00_tokens.rpy", "13_lang.rpy")]
    hexre = re.compile(r"(?<!\{color=)#[0-9a-fA-F]{6}")
    left = []
    for f in files:
        for m in hexre.finditer(open(f, encoding="utf-8").read()):
            if m.group(0).lower() in cols:
                left.append((os.path.basename(f), m.group(0)))
    assert not left, left[:10]
    js = tm_webinject_menu_js()
    assert js.index("var TM_TOK") < js.index("window.TM_ADAPTER"), "tm_tokens.js — до адаптера"


def tm_webinject_menu_js():
    sys.path.insert(0, os.path.join(ROOT, "engines", "_shared"))
    import tm_webinject

    return tm_webinject.menu_js(os.path.join(ROOT, "engines", "web", "tm_menu.js"))
