init 1000 python:
    import os, traceback
    ZZ_OUT = os.environ.get("ZZ_OUT", "shots")
    zz_steps = ["dbg", "rewind", "stats", "scanner", "story", "settings", "diag", "help", "quit"]
    zz_i = [0]

    def zz_dbg():
        lines = ["at start panel %r" % (style.tm_panel.background,)]
        lines.append("mark %r tries %r cbs %r" % (renpy.session.get("tm_theme_mark"), renpy.session.get("tm_theme_tries"), config.interact_callbacks))
        for code in ['config.keymap.get("tm_toggle_key")', '_tm_keymap in config.underlay',
                     'type(config.interact_callbacks)', '_tm_on_interact in config.interact_callbacks',
                     'config.start_callbacks', 'tm_register()', '_tm_on_interact in config.interact_callbacks',
                     'id(config.interact_callbacks)', 'id(renpy.config.interact_callbacks)', 'config']:
            try:
                lines.append("ok %s -> %r" % (code, eval(code, store.__dict__)))
            except Exception:
                lines.append("FAIL " + code + " " + traceback.format_exc())
        try:
            tm_set_name("hp", u"Здоровье героя")
            lines.append(u"names file: %r" % os.path.exists(os.path.join(config.gamedir, "tm_names.json")))
            lines.append(u"after reset: %s" % tm_nice("loop_i", "loop_i")[0])
        except Exception:
            lines.append(traceback.format_exc())
        try:
            renpy.session["tm_auto"] = None
            for r in tm_auto_stats():
                if r[1]:
                    nice, mean, tip = tm_row_info(r[0], r[1])
                    lines.append(u"  %s | %s | %s | %s" % (r[1], nice, mean, tm_thresholds(r[1])))
                else:
                    lines.append(u"# " + r[0])
        except Exception:
            lines.append(traceback.format_exc())
        lines.append("version %r" % (renpy.version_tuple,))
        lines.append("can_tint %r" % (tm_can_tint(),))
        with open(os.path.join(ZZ_OUT, "dbg.txt"), "w") as f:
            f.write("\n".join(lines))

    def zz_step():
        s = zz_steps[zz_i[0]]
        zz_i[0] += 1
        if s == "dbg":
            zz_dbg()
            tm_ui.open = True
            tm_ui.tab = "rewind"
        elif s == "quit":
            renpy.quit()
        else:
            renpy.screenshot(os.path.join(ZZ_OUT, "%02d_%s.png" % (zz_i[0], s)))
            if zz_i[0] < len(zz_steps) - 1:
                nxt = zz_steps[zz_i[0]]
                if nxt == "diag":
                    tm_ui.diag_open = True
                elif nxt == "help":
                    tm_ui.diag_open = False
                    tm_ui.help_open = True
                else:
                    tm_ui.tab = nxt
        renpy.restart_interaction()

    config.overlay_screens.append("zz_shot")

screen zz_shot():
    timer 1.2 repeat True action Function(zz_step)
