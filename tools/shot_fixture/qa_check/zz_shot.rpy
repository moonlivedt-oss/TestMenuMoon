# Проверка вкладки «Тест» и прочих новинок 2026-10-06 (заменяет game/zz_shot.rpy в копии фикстуры).
# Шаги по таймеру: авто-прохождение с лимитом, запись и сохранение маршрута, прохождение по маршруту,
# подсказки с кодом варианта, вкладки «Тест» / «Код» / «Перемотка», относительный ввод, заморозка
# флага и строки, перенос значений, персонажи, поиск по имени, выражение в HUD, заметка о баге.
# Результаты — в ZZ_OUT/dbg3.txt, скриншоты — ZZ_OUT/NN_имя.png.
init 1000 python:
    import os, traceback, io
    ZZ_OUT = os.environ.get("ZZ_OUT", "shots")
    zz_i = [0]
    zz_log = []

    def zz_w(*a):
        zz_log.append(u" ".join(u"%s" % (x,) for x in a))
        with io.open(os.path.join(ZZ_OUT, "dbg3.txt"), "w", encoding="utf-8") as f:
            f.write(u"\n".join(zz_log))

    def zz_shot(name):
        renpy.screenshot(os.path.join(ZZ_OUT, "%02d_%s.png" % (zz_i[0], name)))

    def zz_do(n):
        if n == 0:
            persistent.tm_help_seen = True
            persistent.tm_hints_hidden = True
            zz_w("label cb", _tm_on_label in (getattr(renpy.config, "label_callbacks", None) or []),
                 "chain", getattr(renpy.config, "label_callback", None) is _tm_label_chain)
            zz_w("route_start", tm_ui.route_start)
            tm_ui.auto_mode = "first"
            tm_ui.auto_limit = 10
            tm_ui.auto_stop_label = u""
            # авто-прохождение до первого выбора и дальше: лимит 1
            tm_ui.auto_limit = 10
            tm_auto_start()
            tm_ui.auto["left"] = 1
        elif n == 3:
            zz_w("auto after", tm_ui.auto, "log", tm_ui.auto_log)
            zz_w("route", tm_route_now(), tm_ui.route_rec, tm_ui.route_start, "alice_love", alice_love)
            tm_route_save()
            zz_w("routes", tm_ui.routes)
            zz_w("history", tm_ui.history)
            cov = tm_coverage()
            zz_w("coverage", cov["say"], cov["label"], cov["choice"], cov["scenes"])
            zz_w("refs alice_date", tm_scene_refs("alice_date"))
            _tm_open_menu()
            tm_ui.tab = "checklist"
        elif n == 4:
            zz_shot("test_tab")
            tm_ui.scene_all = True
            tm_scene_toggle("alice_date")
        elif n == 5:
            zz_shot("test_tab_refs")
            tm_ui.tab = "scanner"
        elif n == 6:
            zz_shot("scanner")
            zz_w("dialog log", tm_dialog_log())
            tm_ui.tab = "actions"
            tm_ui.code_text = u"money * 2"
            tm_code_run()
            tm_ui.code_text = u"money += 1"
            tm_code_run()
            tm_ui.code_text = u"1/0"
            tm_code_run()
            zz_w("code", tm_ui.code_hist, "money", money)
        elif n == 7:
            zz_shot("code_tab")
            m0 = money
            tm_input("money"); tm_ui.edit_text = u"+30"; tm_edit_apply()
            m1 = money
            tm_input("money"); tm_ui.edit_text = u"*2"; tm_edit_apply()
            m2 = money
            tm_input("money"); tm_ui.edit_text = u"=-5"; tm_edit_apply()
            m3 = money
            tm_input("money"); tm_ui.edit_text = u"/0"; tm_edit_apply()
            zz_w("rel", m0, m1, m2, m3, "err", tm_ui.edit_err)
            tm_edit_close()
            tm_freeze_toggle("met_alice")
            store.met_alice = False
            _tm_apply_frozen()
            tm_freeze_toggle("name_p")
            store.name_p = u"Other"
            _tm_apply_frozen()
            zz_w("freeze bool/str", met_alice, name_p, tm_ui.frozen)
            tm_freeze_clear()
            tm_values_export()
            store.alice_love = 100
            store.name_p = u"Changed"
            tm_values_import()
            zz_w("values", alice_love, name_p, "journal", len(tm_ui.journal))
            tm_char_rename("a", u"Алиса")
            zz_w("char", a.name, tm_characters())
            tm_scan_name(u"love")
            zz_w("scan name", _tm_scan()["cands"])
            tm_ui.hud_expr = u"money + hp"
            tm_hud_add_expr()
            zz_w("hud", tm_ui.watch)
            tm_ui.tab = "story"
        elif n == 8:
            zz_shot("story_chars")
            tm_jump("start")              # новая партия: маршрут пишется заново
        elif n == 9:
            zz_w("after jump route", tm_route_now(), tm_ui.route_start)
            tm_route_play(0)
        elif n == 12:
            zz_w("route play log", tm_ui.auto_log, "auto", tm_ui.auto, "alice_love", alice_love)
            tm_jump("start")
        elif n in (13, 14):
            renpy.queue_event("dismiss")
        elif n == 15:
            mn = tm_cur_menu_name()
            zz_w("menu", mn)
            tm_code_toggle((mn, 0))
            tm_code_toggle((mn, 2))
            zz_w("code0", tm_choice_code(mn, 0))
            zz_w("code2", tm_choice_code(mn, 2))
        elif n == 16:
            zz_shot("hints_code")
            zz_w("find choice", tm_find_lines(u"gift"))
            tm_bug_request()
        elif n == 17:
            zz_w("bug edit", tm_ui.edit, tm_ui.bug_shot)
            tm_ui.edit_text = u"Тестовый баг: Алиса не улыбается"
            zz_shot("bug_popup")
            tm_edit_apply()
            p = os.path.join(config.basedir, "tm_bugs", "tm_bugs.md")
            zz_w("bug file", io.open(p, encoding="utf-8").read() if os.path.exists(p) else "NO FILE", "count", tm_bug_count())
            zz_w("REPORT\n" + tm_report_text())
            tm_char_rename("a", u"")
            zz_w("char back", a.name)
            _tm_state_save()
            zz_w("state", io.open(os.path.join(config.gamedir, "tm_state.json"), encoding="utf-8").read())
            # сейв с открытым выбором и меню: не должен падать и не должен тащить узлы сценария
            renpy.save("zz_check")
            zz_w("save ok")
        elif n > 17:
            renpy.quit()

    def zz_step():
        try:
            zz_do(zz_i[0])
        except (renpy.game.QuitException, renpy.game.JumpException):
            zz_i[0] += 1
            raise
        except Exception:
            zz_w("STEP %d FAIL\n%s" % (zz_i[0], traceback.format_exc()))
        zz_i[0] += 1
        renpy.restart_interaction()

    config.overlay_screens.append("zz_shot")

screen zz_shot():
    timer 1.0 repeat True action Function(zz_step)
