"""Редактор сохранений: форматы Ren'Py (сейвы и persistent), RPG Maker, Godot, JSON."""

from helpers import *  # noqa: F401,F403  (общие импорты и помощники)


def test_lzstring_matches_reference_vector():
    from tmkit import lzstring

    # эталон — lz-string 1.5.0 (JS): compressToBase64(JSON.stringify({gold:250,n:"Тереза"}))
    src = '{"gold":250,"n":"Тереза"}'
    ref = "N4Ig5g9gNgJiBcAmArABgDQgHYJIIhBBWEEAEQAwdhBAGEBAF8g="
    assert lzstring.compress_to_base64(src) == ref
    assert lzstring.decompress_from_base64(ref) == src
    assert lzstring.decompress_from_base64(lzstring.compress_to_base64("😀" + "x" * 500)) == "😀" + "x" * 500


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
    import pickle as _p, types as _t, zipfile as _zf
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


def test_saves_renpy_persistent_roundtrip_bumps_changed():
    from tmkit import saves

    raw, mods = _persistent_bytes({"gold": 5, "seen": [1, 2], "_preferences": "x"}, {"gold": 10.0})
    with tempfile.TemporaryDirectory() as tmp:
        saves_dir = os.path.join(tmp, "game", "saves")
        os.makedirs(saves_dir)
        path = os.path.join(saves_dir, "persistent")
        open(path, "wb").write(raw)
        found = [p for _l, p in saves.find_saves(os.path.join(tmp, "game"), "renpy")]
        assert path in found
        d = saves.open_save(path)
        assert d.kind == "persistent" and not d.signed
        by = {it.label: it for it in d.items()}
        assert set(by) == {"gold", "seen[0]", "seen[1]"}  # служебные «_…» скрыты
        d.set(by["gold"].path, 777)
        d.set(by["seen[1]"].path, 9)
        d.save()
        assert os.path.exists(path + ".tm_bak")
        o = _load_persistent(open(path, "rb").read(), mods)
    assert o.gold == 777 and o.seen == [1, 9] and o._preferences == "x"
    # время правки поля — «сейчас»: при слиянии копий persistent правка не проиграет старой
    assert o._changed["gold"] > 10.0 and o._changed["seen"] > 1e9


def test_saves_renpy_signed_persistent_refuses_without_key():
    from tmkit import saves

    raw, _mods = _persistent_bytes({"gold": 5}, {})
    signed, _m = _persistent_bytes({"gold": 5}, {}, signed=True)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "persistent")
        open(path, "wb").write(signed)
        d = saves.open_save(path)
        assert d.signed
        d.set(d.items()[0].path, 1)
        d.game_base = tmp  # тут нет Python игры — подписать нечем
        try:
            d.save()
            raise AssertionError("подписанный persistent записан без подписи")
        except ValueError as e:
            assert "подпис" in str(e)
        assert open(path, "rb").read() == signed  # файл не тронут


def test_web_core_has_frame_step_fps_and_saves_tab():
    core = open(os.path.join(ROOT, "engines", "_shared", "tm_menu_core.js"), encoding="utf-8").read()
    for key in ("function frameStep", "function setFps", "Шаг кадра", '["saves", T("Сейвы")]',
                "function renderSaves", "decompressFromBase64", "indexedDB", "tm_bak:"):
        assert key in core, key
    rpgm = open(os.path.join(ROOT, "engines", "rpgmaker", "tm_menu.js"), encoding="utf-8").read()
    assert "step: function" in rpgm
    for path in (("godot", "tm_menu.gd"), ("unity", "plugin", "Plugin.cs"), ("unity", "mono", "TestMenuMono.cs")):
        text = open(os.path.join(ROOT, "engines", *path), encoding="utf-8").read()
        assert "Шаг кадра" in text and "FPS" in text, path


def test_saves_find_rpgmaker():
    from tmkit import saves

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "www", "save"))
        open(os.path.join(tmp, "www", "save", "file1.rpgsave"), "w").close()
        open(os.path.join(tmp, "www", "save", "file1.rpgsave.tm_bak"), "w").close()
        found = saves.find_saves(tmp, "rpgmaker")
        assert [os.path.basename(p) for _l, p in found] == ["file1.rpgsave"]


def test_saves_renpy_py2_old_class_written_with_obj():
    """Объект старого класса py2 (INST в сейве) пишется обратно через OBJ, а не NEWOBJ:
    у классов без object в py2 нет __new__, и Ren'Py не загрузил бы такой сейв."""
    import io as _io, pickletools as _pt
    from tmkit import saves

    data = b"(istore\nOldGirl\n(dp0\nS'love'\np1\nI3\nsb."
    o = saves._Unpickler(_io.BytesIO(data), encoding="bytes").load()
    assert o.__dict__.get("_tm_old") is True
    added = saves._register_stubs()
    try:
        buf = _io.BytesIO()
        saves._Pickler(buf, protocol=2).dump(o)
    finally:
        for mn in added:
            sys.modules.pop(mn, None)
    ops = [op.name for op, _a, _p in _pt.genops(buf.getvalue())]
    assert "OBJ" in ops and "NEWOBJ" not in ops, ops


def test_saves_coerce_keeps_big_ints():
    from tmkit import saves

    assert saves.coerce(1, "12345678901234567891") == 12345678901234567891
    assert saves.coerce(1, "1 000") == 1000 and saves.coerce(1, "2,7") == 2
    assert saves.coerce(1.0, "2,5") == 2.5 and saves.coerce(True, "нет") is False


def test_saves_snapshot_diff_and_cli():
    from tmkit.saves import diff as sdiff
    from tmkit import saves

    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, "a.json"), os.path.join(tmp, "b.json")
        open(a, "w", encoding="utf-8").write('{"gold": 5, "hero": {"hp": 10, "name": "Ann"}, "old": 1}')
        open(b, "w", encoding="utf-8").write('{"gold": 50, "hero": {"hp": 10, "name": "Анна"}, "new": true}')
        ch = sdiff.diff(sdiff.snapshot(saves.open_save(a)), sdiff.snapshot(saves.open_save(b)))
        got = {(c.label, c.kind, sdiff.text(c.before), sdiff.text(c.after)) for c in ch}
        assert got == {("gold", "changed", "5", "50"), ("hero.name", "changed", "Ann", "Анна"),
                       ("new", "added", "—", "true"), ("old", "removed", "1", "—")}, got
        assert [c.kind for c in ch] == ["changed", "changed", "added", "removed"]
        # снимок на диске переживает перезапуск
        snap = sdiff.snapshot(saves.open_save(a))
        sdiff.save_snap(a, snap)
        assert sdiff.load_snap(a) == snap
        os.remove(sdiff._snap_path(a))  # снимки живут в build/ — тестовый не оставляем
        import io as _io, contextlib

        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert tm.main(["saves", a, "--diff", b]) == 0
        assert "~ gold: 5 -> 50" in buf.getvalue() and "различий: 4" in buf.getvalue()
