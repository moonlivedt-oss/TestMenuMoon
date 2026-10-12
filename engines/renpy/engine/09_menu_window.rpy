# ============================ main menu ============================
screen tm_menu():
    modal True
    zorder 200

    $ _w, _h = tm_win_size()
    $ _acc = tm_acc()
    $ _tip = GetTooltip()

    # --- проглатываем продвижение диалога, пока меню открыто (dismiss + модальность) ---
    key "dismiss" action NullAction()
    key "shift_K_t" action SetField(tm_ui, "open", False)
    if tm_alt_key():
        key tm_alt_key() action SetField(tm_ui, "open", False)
    key "game_menu" action SetField(tm_ui, "open", False)
    key "ctrl_K_z" action Function(tm_undo)
    if tm_ui.tab == "stats":
        key "K_PAGEUP" action Function(tm_stat_page, -1)
        key "K_PAGEDOWN" action Function(tm_stat_page, 1)

    # --- затемнение-ловушка: любой клик мимо окна съедается, в игру не идёт ---
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#05070bcc"
        action NullAction()

    # --- перетаскиваемое окно (хват — за шапку) ---
    draggroup:
        drag:
            drag_name "tm_window"
            draggable True
            drag_handle (0, 0, 1.0, int(56 * tm_k()))
            dragged tm_on_dragged
            if tm_ui.win_pos:
                pos tm_ui.win_pos
            else:
                xalign 0.5
                yalign 0.5

            # тонкая акцентная рамка вокруг окна (масштаб — под разрешение игры)
            frame at tm_pop(tm_k()):
                style "tm_border"
                padding (2, 2)

                frame:
                    style "tm_panel"
                    xsize _w
                    ysize _h

                    # fixed с явным размером: на 6.99 frame отдаёт ребёнку ширину экрана, а не
                    # свою (в 800x600 содержимое обрезалось справа); fixed берёт max(доступно, xsize)
                    fixed:
                        xsize _w
                        ysize _h
                        # side "t c b": шапка+вкладки сверху, футер снизу, контенту — остаток
                        # (раньше vbox + yfill выталкивал футер за пределы окна)
                        side "t c b":
                            vbox:
                                # ---------- шапка (зона перетаскивания) ----------
                                frame:
                                    style "tm_header_bg"
                                    xfill True
                                    padding (16, 8)
                                    fixed:
                                        xfill True
                                        ysize 38
                                        hbox:
                                            spacing 12
                                            yalign 0.5
                                            use tm_icon("logo", 34)
                                            # tm_q: «{» в заголовке игры иначе ломал текст-теги
                                            text tm_q(tm_title) style "tm_head_title" yalign 0.5
                                            text tm_engine_tag() style "tm_head_btn_text" color "#0a0c1099" bold False yalign 0.5
                                        hbox:
                                            spacing 8
                                            xalign 1.0
                                            yalign 0.5
                                            button:
                                                style "tm_head_btn"
                                                padding (6, 3)
                                                tooltip "Как пользоваться меню"
                                                action SetField(tm_ui, "help_open", True)
                                                if tm_ic("question"):
                                                    add tm_ic("question") zoom 0.45 align (0.5, 0.5)
                                                else:
                                                    text "?" style "tm_head_btn_text"
                                            textbutton "в центр":
                                                style "tm_head_btn" text_style "tm_head_btn_text"
                                                tooltip "Вернуть окно в центр экрана"
                                                action Function(tm_reset_pos)
                                            textbutton "свернуть":
                                                style "tm_head_btn" text_style "tm_head_btn_text"
                                                tooltip "Мини-режим: плашка с откатом, слотом 1, скипом и HUD поверх игры — с ней можно играть"
                                                action Function(tm_minimize)
                                            button:
                                                style "tm_head_btn"
                                                padding (6, 3)
                                                tooltip ("Закрыть меню (%s или Esc)" % tm_keys_text())
                                                action SetField(tm_ui, "open", False)
                                                if tm_ic("close"):
                                                    add tm_ic("close") zoom 0.45 align (0.5, 0.5)
                                                else:
                                                    text "X" style "tm_head_btn_text"

                                # ---------- вкладки ----------
                                frame:
                                    style "tm_tabbar_bg"
                                    xfill True
                                    padding (8, 6)
                                    hbox:
                                        spacing 2
                                        for _tk, _tl, _tt in tm_tabs():
                                            button:
                                                style "tm_tab_btn"
                                                selected (tm_ui.tab == _tk)
                                                tooltip _tt
                                                action [SetField(tm_ui, "tab", _tk), SetField(tm_ui, "confirm", "")]
                                                hbox:
                                                    spacing 5
                                                    use tm_icon(_tk, 26)
                                                    text _tl style "tm_tab_text" yalign 0.5
                                frame:
                                    xfill True
                                    ysize 2
                                    background Solid(_acc)

                            # ---------- контент ----------
                            frame:
                                background None
                                xfill True
                                yfill True
                                padding (26, 16, 26, 12)

                                if tm_ui.tab == "rewind":
                                    use tm_tab_rewind
                                elif tm_ui.tab == "stats":
                                    use tm_tab_stats
                                elif tm_ui.tab == "actions":
                                    use tm_tab_actions
                                elif tm_ui.tab == "scanner":
                                    use tm_tab_scanner
                                elif tm_ui.tab == "story":
                                    use tm_tab_story
                                elif tm_ui.tab == "checklist":
                                    use tm_tab_test
                                else:
                                    use tm_tab_settings

                            # ---------- футер: подсказка под курсором, иначе горячие клавиши ----------
                            frame:
                                style "tm_footer_bg"
                                xfill True
                                padding (18, 9)
                                if _tip:
                                    text tm_q(_tip) style "tm_tip"
                                else:
                                    text (tm_keys_text() + "  меню    Shift+H  подсказки    Shift+B  баг    Ctrl+Z  отмена    Esc  закрыть    Ctrl  скип") style "tm_foot"

    # ---------- попапы ----------
    if tm_ui.edit:
        use tm_edit_popup
    elif tm_ui.where_open:
        use tm_where_popup
    elif tm_ui.diag_open:
        use tm_diag_popup
    elif tm_ui.help_open:
        use tm_help_popup

# ---------------------- попап: ввод значения / имени ----------------------
screen tm_edit_popup():
    modal True
    zorder 300
    $ _kind, _path = tm_ui.edit
    # для имени/персонажа/заметки значение не читаем (в переменную экрана попал бы объект игры)
    $ _ok, _cur = tm_probe(_path) if _kind == "value" else (False, None)
    $ _lt = tm_lim_text(*tm_limits(_path)) if (isinstance(_cur, _TM_NUM) and not isinstance(_cur, bool)) else u""
    key "dismiss" action NullAction()
    key "game_menu" action Function(tm_edit_close)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000b0"
        action Function(tm_edit_close)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 760
            padding (24, 20)
            vbox:
                spacing 10
                text {"name": "Своё имя переменной", "char": "Своё имя персонажа", "bug": "Заметка о баге"}.get(_kind, "Новое значение") style "tm_h"
                if _kind == "bug":
                    text "Что не так? Место в сценарии, реплика, картинки, звук и скриншот запишутся сами — в tm_bugs/tm_bugs.md в папке игры." style "tm_dim" size 15
                elif _kind == "char":
                    text tm_q(u"%s — сейчас «%s». Пусто — вернуть исходное имя." % (_path, tm_str(getattr(getattr(store, _path, None), "name", u"")))) style "tm_dim" size 15
                else:
                    text tm_q(_path) style "tm_dim"
                if _kind == "value":
                    hbox:
                        spacing 12
                        text "сейчас:" style "tm_dim" yalign 0.5
                        text tm_fmt(_cur, 40) style "tm_value" yalign 0.5
                        if _lt:
                            text tm_q(u"границы " + _lt) style "tm_dim" yalign 0.5
                    if isinstance(_cur, bool):
                        text "да / нет (или 1 / 0)" style "tm_dim" size 15
                    elif isinstance(_cur, _TM_NUM):
                        text "+50, -10, *2, /2 — от текущего значения; =-5 — точно минус пять" style "tm_dim" size 15
                elif _kind == "name":
                    text "Пусто — вернуть автоматическое имя." style "tm_dim" size 15
                button:
                    style "tm_field"
                    xfill True
                    action tm_edit_iv.Enable()
                    input value tm_edit_iv style "tm_filter_text" size 22 length (240 if _kind == "bug" else 64)
                if tm_ui.edit_err:
                    text tm_q(tm_ui.edit_err) style "tm_bad" size 17
                hbox:
                    xalign 1.0
                    spacing 10
                    text "Enter — применить, Esc — отмена" style "tm_foot" yalign 0.5
                    textbutton "Отмена" style "tm_btn" text_style "tm_btn_text" action Function(tm_edit_close)
                    textbutton "Применить" style "tm_btn" text_style "tm_btn_text" action Function(tm_edit_apply)

# ---------------------- попап: где я ----------------------
screen tm_where_popup():
    modal True
    zorder 300
    $ _info = tm_where_info()
    key "dismiss" action NullAction()
    key "game_menu" action SetField(tm_ui, "where_open", False)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000b0"
        action SetField(tm_ui, "where_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 860
            padding (24, 20)
            vbox:
                spacing 10
                hbox:
                    spacing 10
                    use tm_icon("pin", 32)
                    text "Где я" style "tm_h" yalign 0.5
                for _t, _v in _info:
                    hbox:
                        spacing 14
                        text tm_q(_t) style "tm_dim" min_width 170
                        text tm_q(_v) style "tm_label" size 18 xmaximum 620
                hbox:
                    xalign 1.0
                    spacing 10
                    use tm_btn2("save", "Отчёт в файл", Function(tm_write_report), "Записать отчёт тестера (место, история выборов, правки) в папку игры")
                    textbutton "Закрыть" style "tm_btn" text_style "tm_btn_text" action SetField(tm_ui, "where_open", False)

# ---------------------- попап: как пользоваться ----------------------
screen tm_help_popup():
    modal True
    zorder 300
    key "dismiss" action NullAction()
    key "game_menu" action SetField(tm_ui, "help_open", False)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000d0"
        action SetField(tm_ui, "help_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 900
            ysize 620
            padding (24, 20)
            fixed:
                xsize 852
                ysize 580
                side "t c b":
                    hbox:
                        spacing 14
                        $ _m = tm_mascot("wave")
                        if _m:
                            add _m zoom 0.42 yalign 0.5
                        vbox:
                            yalign 0.5
                            spacing 4
                            text "Как пользоваться меню" style "tm_h"
                            text "Коротко о каждой вкладке. Колесо мыши — прокрутка." style "tm_dim"
                    viewport:
                        scrollbars "vertical"
                        style_prefix "tm"
                        mousewheel True
                        yfill True
                        xfill True
                        vbox:
                            spacing 14
                            null height 6
                            for _ic, _t, _d in TM_HELP:
                                hbox:
                                    spacing 14
                                    use tm_icon(_ic, 34)
                                    vbox:
                                        spacing 3
                                        text _t style "tm_label" bold True
                                        text _d style "tm_dim" xmaximum 740
                    hbox:
                        xalign 1.0
                        spacing 10
                        text "Справка откроется снова по кнопке со знаком вопроса в шапке" style "tm_foot" yalign 0.5
                        textbutton "Понятно" style "tm_btn" text_style "tm_btn_text" action SetField(tm_ui, "help_open", False)

# ---------------------- попап: диагностика ----------------------
screen tm_diag_popup():
    modal True
    zorder 300
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000d0"
        action SetField(tm_ui, "diag_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 780
            ysize 470
            padding (24, 20)
            side "t c b":
                vbox:
                    spacing 8
                    hbox:
                        spacing 10
                        use tm_icon("bug", 32)
                        text "Диагностика статов и действий" style "tm_h" yalign 0.5
                    if tm_ui.diag:
                        text ("Найдено проблем: %d" % len(tm_ui.diag)) style "tm_warn"
                        text "[[X] — не работает, [[!] — читается, но пусто (None)." style "tm_dim"
                    null height 4
                if not tm_ui.diag:
                    frame:
                        background None
                        xfill True
                        yfill True
                        use tm_empty("party", "Проблем не найдено: все пути статов читаются, код действий компилируется.")
                else:
                    viewport:
                        scrollbars "vertical"
                        style_prefix "tm"
                        mousewheel True
                        yfill True
                        xfill True
                        vbox:
                            spacing 6
                            for _p in tm_ui.diag:
                                text "[_p!q]" style "tm_label" size 18
                hbox:
                    xalign 1.0
                    textbutton "Закрыть" style "tm_btn" text_style "tm_btn_text" action SetField(tm_ui, "diag_open", False)

