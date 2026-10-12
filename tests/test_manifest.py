"""Манифест игр, генерация data-файлов, офлайн-проверка данных, CLI tm.py."""

from helpers import *  # noqa: F401,F403  (общие импорты и помощники)


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


def test_render_game_matches_render_and_takes_own_manifest():
    i = sorted(generate.GAMES)[0]
    assert generate.render_game(i, generate.GAMES[i]) == generate.render(i)
    body = generate.render_game(7, {"title": "Своя", "stats": [("A", "a")]}, "#123456")
    assert 'store.tm_title = "Своя"' in body and 'store.tm_accent = "#123456"' in body


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
