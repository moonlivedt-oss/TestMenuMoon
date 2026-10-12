# ==================== Ctrl+K: поиск по всем функциям меню + простой режим ====================
init -3 python:
    # разделы вкладок «Тест» и «Настройки» и частые команды — чтобы находились по слову
    TM_PAL_SECTIONS = [
        (u"Авто-прохождение", u"Тест", "checklist", "test_sec", "auto"),
        (u"Маршруты", u"Тест", "checklist", "test_sec", "routes"),
        (u"Покрытие", u"Тест", "checklist", "test_sec", "cov"),
        (u"Сцены", u"Тест", "checklist", "test_sec", "scenes"),
        (u"Заметки о багах", u"Тест", "checklist", "test_sec", "bugs"),
        (u"Цвет, прозрачность, размер, язык", u"Настройки", "settings", "set_sec", "look"),
        (u"HUD поверх игры", u"Настройки", "settings", "set_sec", "play"),
        (u"Все клавиши", u"Настройки", "settings", "set_sec", "keys"),
        (u"Пульт в студии, консоль, скриншот", u"Настройки", "settings", "set_sec", "tools"),
    ]
    TM_PAL_MAX = 12

    def tm_head_name():
        # заголовок окна: название игры без служебного «TEST MENU |» (его и так видно по окну)
        t = tm_str(getattr(store, "tm_title", u"") or u"").strip()
        if t.upper().startswith(u"TEST MENU"):
            t = t[len(u"TEST MENU"):].lstrip(u" |:—-")
        return t or u"TEST MENU"

    def tm_simple():
        # простой режим: без «Теста» и «Кода» и без инструментов списка значений
        return bool(tm_pref("tm_simple", False))

    def tm_set_simple(on):
        store.persistent.tm_simple = bool(on)
        if on and tm_ui.tab not in [k for k, _l, _t in tm_tabs()]:
            tm_ui.tab = "stats"
        renpy.restart_interaction()

    def tm_pal_open():
        tm_ui.pal_text = u""
        tm_ui.pal_open = True
        renpy.restart_interaction()

    def tm_pal_tab(tab, field=None, value=None):
        tm_ui.tab = tab
        if field:
            setattr(tm_ui, field, value)
        renpy.restart_interaction()

    def tm_pal_stat(path):
        # к строке значения: вкладка «Значения», фильтр по пути, строка раскрыта
        tm_ui.tab = "stats"
        tm_ui.vals_mode = "stats"
        tm_ui.stat_filter = path
        tm_ui.stat_page = 0
        tm_ui.row_open = path
        renpy.restart_interaction()

    def tm_pal_items(q):
        # -> [(подпись, раздел, действие)] под запрос q (не больше TM_PAL_MAX)
        q = (q or u"").strip().lower()
        tabs = [k for k, _l, _t in tm_tabs()]
        out = []
        for k, l, _t in tm_tabs():
            out.append((l, u"вкладка", Function(tm_pal_tab, k)))
        out.append((u"Найти переменную", u"Значения", Function(tm_pal_tab, "stats", "vals_mode", "scan")))
        for l, sec, tab, field, val in TM_PAL_SECTIONS:
            if tab in tabs:
                out.append((l, sec, Function(tm_pal_tab, tab, field, val)))
        if tm_ui.journal:
            out.append((u"Отменить последнюю правку", u"Ctrl+Z", Function(tm_undo)))
        out += [
            (u"Свернуть в мини-плашку", u"меню", Function(tm_minimize)),
            (u"Где я", u"файл, строка, метка", Function(tm_where_am_i)),
            (u"Заметка о баге", u"Shift+B", Function(tm_bug_request)),
            (u"Справка", u"F1", SetField(tm_ui, "help_open", True)),
            ((u"Простой режим: выключить" if tm_simple() else u"Простой режим: включить"), u"меню",
             Function(tm_set_simple, not tm_simple())),
        ]
        if q:
            try:
                for r in tm_all_stats():
                    if r[1]:
                        out.append((tm_nice(r[0], r[1])[0], r[1], Function(tm_pal_stat, r[1])))
            except Exception:
                pass
            for label, code in (getattr(store, "tm_actions", None) or []):
                if code:
                    out.append((label, u"выдача", Function(tm_run, code, 1)))
            out = [it for it in out if q in (tm_str(it[0]) + u" " + tm_str(it[1])).lower()]
        return out[:TM_PAL_MAX]

    def tm_pal_first():
        # Enter в поле поиска: выполнить первый найденный пункт
        items = tm_pal_items(tm_ui.pal_text)
        tm_ui.pal_open = False
        if items:
            renpy.run(items[0][2])
        renpy.restart_interaction()

    class TmPalValue(FieldInputValue):
        # поле поиска: Enter — первый результат (а не просто выход из ввода)
        def enter(self):
            tm_pal_first()
            return None

# ---------------------- попап: поиск по функциям ----------------------
screen tm_pal_popup():
    modal True
    zorder 300
    $ _iv = TmPalValue(tm_ui, "pal_text", default=True)
    $ _items = tm_pal_items(tm_ui.pal_text)
    key "dismiss" action NullAction()
    key "game_menu" action SetField(tm_ui, "pal_open", False)
    key "ctrl_K_k" action SetField(tm_ui, "pal_open", False)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000b0"
        action SetField(tm_ui, "pal_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.3
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 760
            padding (20, 16)
            vbox:
                spacing 8
                hbox:
                    spacing 10
                    use tm_icon("scanner", 28)
                    button:
                        style "tm_field"
                        xsize 660
                        action _iv.Enable()
                        input value _iv style "tm_filter_text" length 60 copypaste True
                text "Вкладка, значение, выдача или команда. Enter — первый результат, Esc — закрыть." style "tm_dim" size 15
                null height 2
                if not _items:
                    text "Ничего не найдено." style "tm_dim"
                for _l, _s, _a in _items:
                    button:
                        style "tm_side_btn"
                        xfill True
                        action [SetField(tm_ui, "pal_open", False), _a]
                        hbox:
                            spacing 12
                            text tm_q(_tm_short(_l, 46)) style "tm_side_text" min_width 470
                            text tm_q(_tm_short(_s, 30)) style "tm_dim" size 15 yalign 0.5
