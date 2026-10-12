init 1000 python:
    import os, traceback, io
    ZZ_OUT = os.environ.get("ZZ_OUT", "shots")
    zz_i = [0]
    zz_log = []

    def zz_w(*a):
        zz_log.append(u" ".join(u"%s" % (x,) for x in a))
        with io.open(os.path.join(ZZ_OUT, "dbg2.txt"), "w", encoding="utf-8") as f:
            f.write(u"\n".join(zz_log))

    def zz_shot(name):
        renpy.screenshot(os.path.join(ZZ_OUT, "%02d_%s.png" % (zz_i[0], name)))

    def zz_do(n):
        if n == 0:
            persistent.tm_hints_hidden = False
            persistent.tm_help_seen = True
            persistent.tm_spoil = None
            _tm_open_menu()                 # базовый снимок «прошлого открытия»
            tm_fav_toggle("alice_love")
            tm_watch_toggle("alice_love", "alice_love")
            tm_watch_toggle("money", "money")
            tm_ui.open = False
            zz_w("alt key", tm_alt_key(), config.keymap.get("tm_toggle_key"))
            zz_w("periodic", _tm_periodic in config.periodic_callbacks, "wrap", renpy.exports.menu is _tm_menu_wrap)
        elif n in (1, 2):
            renpy.queue_event("dismiss")
        elif n == 3:
            zz_w("node", tm_cur_menu())
            zz_shot("hints_full")
            persistent.tm_spoil = "sign"
        elif n == 4:
            zz_shot("hints_sign")
            persistent.tm_spoil = "click"
        elif n == 5:
            zz_shot("hints_click")
            persistent.tm_spoil = None
            renpy.queue_event("focus_down")
        elif n == 6:
            renpy.queue_event("button_select")
        elif n == 7:
            zz_w("history", tm_ui.history, "pending", tm_ui.hist_pending is not None)
            tm_note(u"Проверка тоста")
            tm_ui.mini = True
        elif n == 8:
            zz_shot("hud_flash_mini_toast")
            _tm_open_menu()
            zz_w("deltas", tm_ui.deltas)
            tm_ui.tab = "stats"
        elif n == 9:
            zz_shot("stats_deltas")
            tm_ui.only_changed = True
        elif n == 10:
            zz_shot("stats_only_changed")
            tm_ui.only_changed = False
            tm_freeze_toggle("money")
            tm_freeze_cycle("money")
            tm_set("money", 999)
            zz_w("after set", money, tm_ui.journal)
            tm_undo()
            zz_w("after undo", money, tm_ui.frozen, tm_ui.freeze_mode)
            tm_ui.tab = "story"
        elif n == 11:
            zz_shot("story")
            tm_ui.tab = "rewind"
            tm_set("hp", 40)
        elif n == 12:
            zz_shot("rewind_journal")
            tm_input("money")
        elif n == 13:
            zz_shot("edit_popup")
            tm_ui.edit_text = u"abc"
            tm_edit_apply()
            zz_w("edit err", tm_ui.edit_err)
            tm_ui.edit_text = u"777"
            tm_edit_apply()
            zz_w("edit ok", money, tm_ui.edit)
            tm_where_am_i()
        elif n == 14:
            zz_shot("where")
            tm_ui.where_open = False
            tm_ui.tab = "scanner"
            tm_scan_snapshot()
            store.money -= 50
            tm_scan_by("-50")
            zz_w("scan", _tm_scan()["cands"], tm_scan_trail())
        elif n == 15:
            zz_shot("scanner")
            tm_scan_back()
            zz_w("scan back", len(_tm_scan()["cands"]))
            tm_ui.tab = "settings"
        elif n == 16:
            zz_shot("settings")
            tm_write_report()
            _tm_state_save()
            zz_w("state", os.path.exists(os.path.join(config.gamedir, "tm_state.json")))
            zz_w("buttons", tm_screen_buttons())
            zz_w("where", tm_where_info())
            zz_w("cond_now", tm_cond_now("alice_love >= 5 and money > 100"))
            zz_w("eff", tm_eff_text("alice_love", 3, 4))
            zz_w("REPORT\n" + tm_report_text())
        else:
            renpy.quit()

    def zz_step():
        try:
            zz_do(zz_i[0])
        except renpy.game.QuitException:
            raise
        except Exception:
            zz_w("STEP %d FAIL\n%s" % (zz_i[0], traceback.format_exc()))
        zz_i[0] += 1
        renpy.restart_interaction()

    config.overlay_screens.append("zz_shot")

screen zz_shot():
    timer 1.0 repeat True action Function(zz_step)
