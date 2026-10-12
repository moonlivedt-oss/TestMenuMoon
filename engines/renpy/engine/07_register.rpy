init python:
    def _tm_open_menu():
        # В главном меню и в меню игры (Esc) оверлеи скрыты: раньше меню «открывалось»
        # невидимо и выскакивало само при возврате в игру.
        if store.main_menu or getattr(store, "suppress_overlay", False) or getattr(store, "_menu", False):
            tm_note(u"Тест-меню доступно в самой игре (%s)" % tm_keys_text())
            return
        if tm_ui.auto:                         # клавиша меню во время авто-прохождения — стоп
            tm_auto_stop(u"вручную")
        store.tm_ui.open = True
        store.tm_ui.mini = False
        store.tm_ui.edit = None
        store.tm_ui.where_open = False
        store.tm_ui.diag_open = False
        store.tm_ui.confirm = ""
        store.tm_ui.help_open = False
        if not getattr(store.persistent, "tm_help_seen", False):
            store.tm_ui.help_open = True        # первый раз — «Как пользоваться»
            store.persistent.tm_help_seen = True
        store.tm_ui.slots = None             # время слотов перечитать один раз
        renpy.session["tm_auto"] = None      # авто-статы: игра могла завести новые переменные
        _tm_take_seen()                      # что игра изменила с прошлого открытия
        if tm_ui.deltas:
            tm_note(u"С прошлого открытия меню изменилось значений: %d (отмечены в «Переменных»)" % len(tm_ui.deltas))
        renpy.restart_interaction()

    def _tm_on_interact():
        _tm_theme_check()
        _tm_apply_frozen()
        _tm_log_tick()
        if tm_ui.auto:
            _tm_auto_interact()
        else:
            tm_restore_skip_prefs()
        if tm_ui.hist_pending and not store.main_menu:
            _tm_hist_finish()                # эффект выбора: игра дошла до следующей реплики
        if tm_ui.watch:
            _tm_hud_track()
        _tm_state_save()

    _tm_keymap = renpy.Keymap(tm_toggle_key=_tm_open_menu, tm_hints_key=tm_toggle_hints,
                              tm_bug_key=tm_bug_request, tm_qsave_key=_tm_key_qsave,
                              tm_qload_key=_tm_key_qload)

    # свои клавиши: (действие keymap, клавиша) — Shift+B заметка о баге, Shift+F5 / Shift+F9 слот 1
    TM_EXTRA_KEYS = (("tm_hints_key", "shift_K_h"), ("tm_bug_key", "shift_K_b"),
                     ("tm_qsave_key", "shift_K_F5"), ("tm_qload_key", "shift_K_F9"))

    def tm_register():
        # Горячие клавиши, оверлей и колбэк. Повторяется при старте и после загрузки:
        # игра, которая на init 1+ целиком переприсваивает config.underlay / keymap /
        # overlay_screens, иначе молча отключала меню.
        try:
            _alt = tm_alt_key()
            config.keymap["tm_toggle_key"] = ["shift_K_t"] + ([_alt] if _alt else [])
            for _act, _key in TM_EXTRA_KEYS:
                config.keymap.setdefault(_act, [])
                if _key not in config.keymap[_act]:
                    config.keymap[_act].append(_key)
            if _tm_keymap not in config.underlay:
                config.underlay.append(_tm_keymap)
            if "tm_overlay" not in config.overlay_screens:
                config.overlay_screens.append("tm_overlay")
            lst = getattr(config, "interact_callbacks", None)
            if isinstance(lst, _TM_LIST) and _tm_on_interact not in lst:
                lst.append(_tm_on_interact)
            lst = getattr(config, "periodic_callbacks", None)
            if isinstance(lst, _TM_LIST) and _tm_periodic not in lst:
                lst.append(_tm_periodic)
        except Exception:
            pass
        try:
            # переход на метку: стоп авто-прохождения, начало маршрута новой игры.
            # Новые Ren'Py — список label_callbacks, старые — одна функция (встаём в цепочку).
            # renpy.config, а не config: на 6.99 обращение к незнакомой переменной config
            # бросает исключение вместо значения по умолчанию
            rc = renpy.config
            lst = getattr(rc, "label_callbacks", None)
            if isinstance(lst, _TM_LIST):
                if _tm_on_label not in lst:
                    lst.append(_tm_on_label)
            elif getattr(rc, "label_callback", None) is not _tm_label_chain:
                tm_ui.label_prev = getattr(rc, "label_callback", None)
                rc.label_callback = _tm_label_chain
        except Exception:
            pass
        try:
            renpy.clear_keymap_cache()
        except Exception:
            pass
        _tm_install_menu_wrap()

    tm_register()

    def _tm_on_start(why=u"игра перезапустилась (конец игры или выход в меню)"):
        tm_register()
        tm_apply_theme()
        _tm_scrub_log()
        _tm_chars_apply()
        tm_ui.route_rec = []                 # маршрут — с этой загрузки (новая игра: метка start)
        tm_ui.route_start = "save"
        if tm_ui.auto:
            tm_auto_stop(why, "warn")

    def _tm_on_load():
        _tm_on_start(u"загружен сейв")

    # Тема и регистрация — при старте игры (и её перезапуске) и после загрузки.
    for _cb, _fn in (("start_callbacks", _tm_on_start), ("after_load_callbacks", _tm_on_load)):
        _lst = getattr(config, _cb, None)
        if isinstance(_lst, _TM_LIST) and _fn not in _lst:
            _lst.append(_fn)

# Регистрация ещё раз — после init всех файлов игры (её init 1+ мог всё перезаписать;
# zzz_ в имени — наш init 999 идёт последним).
init 999 python:
    tm_register()
    _tm_state_load()                         # избранное, HUD, вкладка — с прошлого
    if getattr(tm_ui, "bridge", False):
        tm_bridge_set(True, False)           # пульт в студии был включён — снова на связи запуска
    _tm_chars_apply()                        # свои имена персонажей

