# ---------------------- вкладка: перемотка ----------------------
screen tm_tab_rewind():
    $ _sl = tm_slots()
    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 18

            # --- назад ---
            vbox:
                spacing 8
                text "Перемотка назад" style "tm_h"
                text "Откат истории вместе с переменными. Колесо мыши вверх делает то же и без меню." style "tm_dim"
                hbox:
                    spacing 14
                    use tm_btn2("back", "Назад ×10", Function(tm_rollback, 10), "Откатить 10 шагов истории")
                    use tm_btn2("back", "Назад ×1", Function(tm_rollback, 1), "Откатить один шаг истории")
                    use tm_btn2("skip", "Вперёд ×1", RollForward(), "Вернуться вперёд после отката (те же выборы)")

            # --- лог реплик: откат прямо к нужной ---
            vbox:
                spacing 6
                text "Последние реплики" style "tm_h"
                $ _dl = tm_dialog_log(10)
                if not _dl:
                    text "История реплик пуста (или игра её отключила)." style "tm_dim"
                for _dw, _dt, _di in _dl:
                    hbox:
                        spacing 10
                        textbutton "сюда":
                            style "tm_seg" text_style "tm_seg_text"
                            text_size 15
                            padding (10, 3)
                            yalign 0.5
                            sensitive (_di is not None)
                            tooltip "Откатить игру к этой реплике (вместе с переменными)"
                            action RollbackToIdentifier(_di)
                        text tm_q(_dw) style "tm_dim" size 16 min_width 150 yalign 0.5
                        text tm_q(_dt) style "tm_label" size 17 yalign 0.5 xmaximum 640

            use tm_sep

            # --- быстрые слоты ---
            vbox:
                spacing 8
                text "Быстрые слоты" style "tm_h"
                text "Мгновенное сохранение/загрузка. Отдельные от обычных сейвов игры." style "tm_dim"
                for _sn in (1, 2, 3):
                    hbox:
                        spacing 12
                        text ("Слот %d" % _sn) style "tm_label" yalign 0.5 min_width 90
                        use tm_btn2("save", "Сохранить", Function(tm_quick_save, _sn), "Сохранить игру в слот %d" % _sn)
                        use tm_btn2("load", "Загрузить", Function(tm_quick_load, _sn), "Загрузить слот %d" % _sn, _sl[_sn][0])
                        text _sl[_sn][1] style "tm_dim" yalign 0.5
                if _sl[0][0]:
                    hbox:
                        spacing 12
                        text "Перед прыжком" style "tm_label" yalign 0.5 min_width 90
                        use tm_btn2("load", "Вернуться", Function(tm_quick_load, 0), "Сейв, сделанный автоматически перед переходом к метке, реплике или скрытому выбору")
                        text _sl[0][1] style "tm_dim" yalign 0.5

            use tm_sep

            # --- журнал правок ---
            vbox:
                spacing 8
                hbox:
                    spacing 12
                    text "Правки из меню" style "tm_h" yalign 0.5
                    if tm_ui.journal:
                        textbutton "отменить последнюю" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Ctrl+Z" action Function(tm_undo)
                        textbutton ("Точно? Ещё раз" if tm_ui.confirm == "undo_all" else "отменить все (%d)" % len(tm_ui.journal)):
                            style "tm_seg" text_style "tm_seg_text"
                            yalign 0.5
                            selected (tm_ui.confirm == "undo_all")
                            tooltip "Вернуть все значения, изменённые из меню, как были"
                            action Function(tm_confirm, "undo_all", tm_undo_all)
                if not tm_ui.journal:
                    text "Пока ничего не меняли. Каждая правка значения запоминается и отменяется (Ctrl+Z)." style "tm_dim"
                else:
                    for _jp, _jo, _jn in reversed(tm_ui.journal[-8:]):
                        hbox:
                            spacing 12
                            text tm_q(_tm_short(tm_nice(_jp, _jp)[0], 34)) style "tm_label" size 18 min_width 360
                            text (tm_fmt(_jo, 14) + u"  →  " + tm_fmt(_jn, 14)) style "tm_value" size 18

            use tm_sep

            # --- вперёд / авто-пропуск ---
            vbox:
                spacing 8
                text "Пропуск вперёд" style "tm_h"
                text "Кнопка ниже мгновенно проматывает весь текст, в том числе непрочитанный. Либо зажмите Ctrl; Tab включает/выключает скип." style "tm_dim"
                hbox:
                    spacing 14
                    use tm_btn2("skip", "Скип всего текста", [SetField(tm_ui, "open", False), Function(tm_start_skip, "fast")], "Мгновенный скип до следующего выбора (настройки скипа потом вернутся)")
                    textbutton ("Авто-пропуск: ВКЛ" if _preferences.afm_enable else "Авто-пропуск: выкл"):
                        style "tm_btn" text_style "tm_btn_text"
                        tooltip "Реплики листаются сами (скорость — ползунком ниже)"
                        action [ToggleField(_preferences, "afm_enable"), SetField(tm_ui, "open", False)]
                hbox:
                    spacing 14
                    textbutton ("Ctrl пропускает и непрочитанное: ВКЛ" if _preferences.skip_unseen else "Ctrl пропускает и непрочитанное: выкл"):
                        style "tm_seg" text_style "tm_seg_text"
                        selected _preferences.skip_unseen
                        tooltip "Это настройка самой игры «Пропускать непрочитанное» — она останется и без меню"
                        action Function(tm_toggle_skip_unseen)

                null height 4
                # скорость авто-пропуска
                hbox:
                    spacing 14
                    text "Скорость авто-пропуска" style "tm_label" yalign 0.5 min_width 300
                    bar value Preference("auto-forward time") style "tm_bar" yalign 0.5
                text "Правее — быстрее авто-переход между репликами." style "tm_dim"

                null height 4
                # скорость появления текста
                hbox:
                    spacing 14
                    text "Скорость текста" style "tm_label" yalign 0.5 min_width 300
                    bar value Preference("text speed") style "tm_bar" yalign 0.5
                text "Правее — текст появляется быстрее (в самом правом — мгновенно)." style "tm_dim"

# ---------------------- вкладка: характеристики ----------------------
screen tm_tab_stats():
    $ _mode = tm_stats_mode()
    $ _rows, _page, _pages, _total = tm_stat_rows(tm_ui.stat_filter)
    $ _acc = tm_acc()
    vbox:
        spacing 12
        fixed:
            xfill True
            ysize 44
            hbox:
                spacing 10
                yalign 0.5
                text "Значения" style "tm_h" yalign 0.5
                null width 6
                # источник: data-файл игры или авто-поиск (переключатель — только если data есть)
                if getattr(store, "tm_stats", None):
                    textbutton "из data" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (_mode == "data") tooltip "Список статов, заданный для этой игры в студии" action Function(tm_set_stats_mode, "data")
                textbutton "авто" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (_mode == "auto") tooltip "Меню само нашло переменные игры" action Function(tm_set_stats_mode, "auto")
                if _mode == "auto":
                    use tm_icobtn("back", Function(tm_auto_rebuild), tip="Пересобрать список (игра могла завести новые переменные)", alt="R")
                use tm_icobtn("bug", Function(tm_diag_run), tip="Проверить: все ли пути читаются и в границах", alt="?")
                use tm_icobtn("download", Function(tm_values_export), tip="Сохранить значения списка и избранного в tm_values.json (папка игры) — для переноса в другую партию", alt="S")
                use tm_icobtn("upload", Function(tm_values_import), tip="Загрузить значения из tm_values.json: те же переменные получат сохранённые значения (Ctrl+Z отменяет)", alt="L")
                if tm_ui.journal:
                    $ _jp, _jo, _jn = tm_ui.journal[-1]
                    textbutton ("отменить (%d)" % len(tm_ui.journal)):
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        tooltip (u"Ctrl+Z — вернуть %s = %s" % (tm_nice(_jp, _jp)[0], tm_fmt(_jo, 20)))
                        action Function(tm_undo)
                if tm_ui.frozen:
                    button:
                        style "tm_seg"
                        yalign 0.5
                        tooltip "Снять все заморозки"
                        action Function(tm_freeze_clear)
                        hbox:
                            spacing 6
                            use tm_icon("snow", 22)
                            text ("%d  снять" % len(tm_ui.frozen)) style "tm_seg_text" yalign 0.5
                    textbutton "в профиль":
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        tooltip "Профиль игры: эти заморозки будут ставиться сами при каждом запуске"
                        action Function(tm_profile_save)
                if tm_profile_size():
                    textbutton ("профиль %d: убрать" % tm_profile_size()):
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        tooltip "Удалить профиль игры (текущие заморозки не снимаются)"
                        action Function(tm_profile_clear)
            hbox:
                spacing 8
                xalign 1.0
                yalign 0.5
                text "шаг" style "tm_dim" yalign 0.5
                for s in (1, 5, 10, 50):
                    textbutton "[s]":
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        selected (tm_ui.stat_step == s)
                        tooltip "Шаг кнопок − и +"
                        action SetField(tm_ui, "stat_step", s)

        # --- фильтр + страницы ---
        hbox:
            spacing 10
            use tm_icon("scanner", 26)
            use tm_field("stat_filter", 300, 30)
            if tm_ui.stat_filter:
                use tm_icobtn("close", [SetField(tm_ui, "stat_filter", ""), SetField(tm_ui, "stat_page", 0)], tip="Очистить фильтр", alt="X")
            text ("найдено: %d" % _total) style "tm_dim" yalign 0.5
            textbutton ("журнал: %d" % len(getattr(tm_ui, "changelog", []))):
                style "tm_seg" text_style "tm_seg_text"
                yalign 0.5
                tooltip "Журнал изменений: что, когда и где поменяли игра, меню или заморозка"
                action SetField(tm_ui, "log_open", True)
            if tm_ui.deltas:
                textbutton ("изменённые: %d" % len(tm_ui.deltas)):
                    style "tm_seg" text_style "tm_seg_text"
                    yalign 0.5
                    selected tm_ui.only_changed
                    tooltip "Только то, что игра изменила с прошлого открытия меню"
                    action Function(tm_toggle_only_changed)
            if _pages > 1:
                textbutton "‹" style "tm_icon_btn" text_style "tm_icon_text" sensitive (_page > 0) action Function(tm_stat_page, -1)
                text ("%d / %d" % (_page + 1, _pages)) style "tm_dim" yalign 0.5
                textbutton "›" style "tm_icon_btn" text_style "tm_icon_text" sensitive (_page < _pages - 1) action Function(tm_stat_page, 1)

        use tm_sep

        if not _rows:
            if tm_ui.only_changed:
                use tm_empty("search", "Среди переменных списка изменённых нет (изменилось что-то вне списка — ищи на вкладке «Поиск»).")
            elif tm_ui.stat_filter:
                use tm_empty("search", "Ничего не найдено по фильтру.")
            else:
                use tm_empty("think", "Переменных не найдено. Начни игру (авто-поиск видит переменные текущей партии) или найди нужное на вкладке «Поиск».")
        else:
            viewport:
                scrollbars "vertical"
                style_prefix "tm"
                mousewheel True
                yfill True
                xfill True
                vbox:
                    spacing 6
                    for _r in _rows:
                        $ label, path = _r[0], _r[1]
                        if not path:
                            null height 4
                            hbox:
                                spacing 12
                                text "[label!q]" style "tm_dim" size 18 color _acc yalign 0.5
                                if len(_r) > 2 and _r[2] == "svc":
                                    textbutton ("свернуть" if tm_ui.show_service else "показать"):
                                        style "tm_seg" text_style "tm_seg_text"
                                        yalign 0.5
                                        tooltip "Переменные, которые сценарий не меняет и не проверяет"
                                        action Function(tm_toggle_service)
                        else:
                            $ _ok, val = tm_probe(path)
                            $ _num = isinstance(val, _TM_NUM) and not isinstance(val, bool)
                            $ _lt, _out, _cdn, _cup = tm_stat_view(path, val) if _num else (u"", False, True, True)
                            $ _nice, _mean, _tip = tm_row_info(label, path)
                            hbox:
                                spacing 8
                                use tm_icobtn("star", Function(tm_fav_toggle, path), sel=tm_is_fav(path), tip="Избранное: закрепить наверху списка (запоминается для этой игры)", alt="*")
                                use tm_icobtn("eye", Function(tm_watch_toggle, label, path), sel=tm_watched(path), tip="Показывать в HUD поверх игры", alt="o")
                                button:
                                    style "tm_name_btn"
                                    xsize 270
                                    yalign 0.5
                                    tooltip _tip
                                    action Function(tm_rename, path, _nice)
                                    vbox:
                                        text tm_q(_tm_short(_nice, 30)) style "tm_label"
                                        text tm_q(_tm_short(_mean if _nice == path else (path + u" | " + _mean), 40)) style "tm_dim" size 14 layout "nobreak"
                                $ _dt = tm_delta_text(path)
                                hbox:
                                    xminimum 200
                                    spacing 8
                                    yalign 0.5
                                    if not _ok:
                                        text "путь не найден" style "tm_bad" yalign 0.5
                                    elif val is None:
                                        text "None" style "tm_warn" yalign 0.5
                                    else:
                                        text tm_fmt(val, 12) style ("tm_warn" if _out else "tm_value") yalign 0.5
                                    if _dt:
                                        text tm_q(_dt[0]) style "tm_dim" size 15 color _dt[1] bold True yalign 0.5
                                    if _lt:
                                        text tm_q(_lt) style "tm_dim" size 15 color (TM_TOK["warn"] if _out else TM_TOK["text_off"]) yalign 0.5
                                if isinstance(val, bool):
                                    textbutton ("ВКЛ" if val else "выкл"):
                                        style "tm_btn" text_style "tm_btn_text"
                                        action Function(tm_toggle, path)
                                    use tm_icobtn("snow", Function(tm_freeze_toggle, path), sel=(path in tm_ui.frozen), tip="Заморозить флаг: игра не сможет его переключить", alt="*")
                                elif _num:
                                    textbutton "−" style "tm_pm_btn" text_style "tm_pm_text" sensitive _cdn tooltip ("Уже минимум" if not _cdn else "Уменьшить на шаг") action Function(tm_add, path, -tm_ui.stat_step)
                                    textbutton "+" style "tm_pm_btn" text_style "tm_pm_text" sensitive _cup tooltip ("Уже максимум" if not _cup else "Увеличить на шаг") action Function(tm_add, path, tm_ui.stat_step)
                                    textbutton "ввод" style "tm_btn" text_style "tm_btn_text" tooltip "Ввести точное значение" action Function(tm_input, path)
                                    use tm_icobtn("snow", Function(tm_freeze_toggle, path), sel=(path in tm_ui.frozen), tip="Заморозить: игра не сможет изменить значение", alt="*")
                                    if path in tm_ui.frozen:
                                        textbutton tm_freeze_sign(path):
                                            style "tm_pm_btn" text_style "tm_pm_text"
                                            tooltip "Вид заморозки (щёлкни, чтобы сменить): = ровно это значение, ≥ не меньше, ≤ не больше"
                                            action Function(tm_freeze_cycle, path)
                                    $ _nt = tm_next_threshold(path, val)
                                    if _nt is not None:
                                        use tm_icobtn("target", Function(tm_to_threshold, path, _nt), tip=(u"Поставить %s — следующий порог из условий сценария" % _nt), alt=">")
                                elif _ok:
                                    textbutton "изменить" style "tm_btn" text_style "tm_btn_text" action Function(tm_input, path)
                                    if isinstance(val, _TM_STR):
                                        use tm_icobtn("snow", Function(tm_freeze_toggle, path), sel=(path in tm_ui.frozen), tip="Заморозить строку: игра не сможет её изменить", alt="*")

# ---------------------- вкладка: действия ----------------------
screen tm_tab_actions():
    $ _acc = tm_acc()
    vbox:
        spacing 10
        # ---- свой код ----
        hbox:
            spacing 10
            use tm_icon("code", 30)
            text "Свой код" style "tm_h" yalign 0.5
            text "выражение — покажет значение, команда — выполнит (money += 100). Enter — выполнить" style "tm_dim" size 15 yalign 0.5
        hbox:
            spacing 10
            button:
                style "tm_field"
                xsize 720
                action tm_code_iv.Enable()
                input value tm_code_iv style "tm_filter_text" length 300 copypaste True
            textbutton "Выполнить" style "tm_btn" text_style "tm_btn_text" tooltip "Выполнить в пространстве игры (как консоль Ren'Py)" action Function(tm_code_run)
        if tm_ui.code_hist:
            vbox:
                spacing 2
                for _cc, _cr, _cb in reversed(tm_ui.code_hist[-4:]):
                    hbox:
                        spacing 10
                        textbutton tm_q(_tm_short(_cc, 40)):
                            style "tm_name_btn"
                            text_style "tm_dim"
                            text_size 15
                            tooltip "Выполнить ещё раз"
                            action Function(tm_code_again, _cc)
                        text tm_q(_cr) style ("tm_bad" if _cb else "tm_value") size 15 yalign 0.5 xmaximum 560

        use tm_sep

        # ---- готовые действия игры ----
        fixed:
            xfill True
            ysize 44
            hbox:
                spacing 10
                yalign 0.5
                use tm_icon("coins", 32)
                text "Выдача" style "tm_h" yalign 0.5
            if tm_actions:
                hbox:
                    spacing 10
                    xalign 1.0
                    yalign 0.5
                    text "кол-во" style "tm_dim" yalign 0.5
                    for q in (1, 5, 10, 25):
                        textbutton "×[q]":
                            style "tm_seg" text_style "tm_seg_text"
                            selected (tm_ui.give_qty == q)
                            tooltip "Сколько раз выполнить действие"
                            action SetField(tm_ui, "give_qty", q)

        if not tm_actions:
            use tm_empty("sleep", "Готовых действий для этой игры нет — их задают в студии (вкладка «Действия»). Свой код выше работает всегда.")
        else:
            hbox:
                spacing 10
                use tm_icon("scanner", 26)
                use tm_field("act_filter", 320, 24)
                if tm_ui.act_filter:
                    use tm_icobtn("close", SetField(tm_ui, "act_filter", ""), tip="Очистить фильтр", alt="X")
            $ _qa = tm_ui.act_filter.strip().lower()
            viewport:
                scrollbars "vertical"
                style_prefix "tm"
                mousewheel True
                yfill True
                xfill True
                vbox:
                    spacing 8
                    for label, code in tm_actions:
                        if not code:
                            if not _qa:
                                null height 6
                                text "[label!q]" style "tm_dim" size 18 color _acc
                        elif (not _qa) or (_qa in label.lower()):
                            textbutton "[label!q]":
                                style "tm_btn" text_style "tm_btn_text"
                                tooltip _tm_short(code, 90)
                                action Function(tm_run, code, tm_ui.give_qty)

# ---------------------- вкладка: сканер ----------------------
screen tm_tab_scanner():
    $ _s = tm_scan_view()
    vbox:
        spacing 10
        fixed:
            xfill True
            ysize 44
            text "Найти переменную" style "tm_h" yalign 0.5
            hbox:
                spacing 10
                xalign 1.0
                yalign 0.5
                text "тип" style "tm_dim" yalign 0.5
                for _m, _lbl in [("num", "числа"), ("str", "строки"), ("all", "всё")]:
                    textbutton "[_lbl]":
                        style "tm_seg" text_style "tm_seg_text"
                        selected (_s["mode"] == _m)
                        action Function(tm_scan_set_mode, _m)
        text "Как ArtMoney, но по именам: снимок → измени стат в игре (закрой меню, поиграй) → «изменились». Повторяй, пока не останется искомое. Затем «в Переменные»." style "tm_dim"

        hbox:
            spacing 10
            use tm_btn2("camera", "Снимок / сброс", Function(tm_scan_snapshot), "Запомнить все значения игры сейчас")
            use tm_btn2("close", "Очистить", Function(tm_scan_reset), "Забыть снимок и кандидатов")
            use tm_btn2("back", "Шаг назад", Function(tm_scan_back), "Отменить последнее сужение", sens=_s["hist"])

        hbox:
            spacing 10
            textbutton "изменились" style "tm_seg" text_style "tm_seg_text" tooltip "Оставить то, что поменялось с прошлого шага" action Function(tm_scan_narrow, "changed")
            textbutton "не изменились" style "tm_seg" text_style "tm_seg_text" tooltip "Оставить то, что осталось прежним" action Function(tm_scan_narrow, "same")
            textbutton "стало больше" style "tm_seg" text_style "tm_seg_text" action Function(tm_scan_narrow, "up")
            textbutton "стало меньше" style "tm_seg" text_style "tm_seg_text" action Function(tm_scan_narrow, "down")

        hbox:
            spacing 10
            text "Значение:" style "tm_dim" yalign 0.5
            use tm_field("scan_val", 170, 24)
            textbutton "= равно" style "tm_btn" text_style "tm_btn_text" tooltip "Оставить переменные с ровно таким значением" action Function(tm_scan_equals, tm_ui.scan_val)
            textbutton "содержит" style "tm_btn" text_style "tm_btn_text" tooltip "Строки, в которых есть этот текст" action Function(tm_scan_contains, tm_ui.scan_val)
            textbutton "изменилось на" style "tm_btn" text_style "tm_btn_text" tooltip "Разница с прошлым шагом ровно это число (потратил 50 — введи -50)" action Function(tm_scan_by, tm_ui.scan_val)
            textbutton "в имени" style "tm_btn" text_style "tm_btn_text" tooltip "Переменные, в имени (пути) которых есть этот текст: money, love, girls" action Function(tm_scan_name, tm_ui.scan_val)

        use tm_sep
        $ _msg = _s["msg"]
        $ _trail = tm_scan_trail()
        hbox:
            spacing 16
            text "[_msg!q]" style "tm_value" size 19
            if _trail and u"→" in _trail:
                text tm_q(_trail) style "tm_dim" size 16 yalign 0.5

        if not _s["n"]:
            use tm_empty("wait", "Кандидатов пока нет. Нажми «Снимок», поиграй и возвращайся сужать.")
        elif _s["n"] > 80:
            $ _n = _s["n"]
            text "Слишком много ([_n]). Сужай кнопками выше, пока не станет ≤ 80." style "tm_dim"
        else:
            viewport:
                scrollbars "vertical"
                style_prefix "tm"
                mousewheel True
                yfill True
                xfill True
                vbox:
                    spacing 6
                    for _p, _o, _c in _s["rows"]:
                        $ _nm = tm_nice(_p, _p)[0]
                        hbox:
                            spacing 10
                            vbox:
                                yalign 0.5
                                xminimum 390
                                text tm_q(_tm_short(_nm, 36)) style "tm_label" size 18
                                if _nm != _p:
                                    text tm_q(_tm_short(_p, 48)) style "tm_dim" size 14
                            text (tm_fmt(_o, 9) + u" → " + tm_fmt(_c, 9)) style "tm_value" size 18 yalign 0.5 min_width 180
                            textbutton "ввод" style "tm_btn" text_style "tm_btn_text" action Function(tm_input, _p)
                            textbutton "в Переменные" style "tm_btn" text_style "tm_btn_text" tooltip (u"Закрепить на вкладке «Переменные» под именем «%s» (до выхода из игры; имя можно сменить щелчком)" % _nm) action Function(tm_scan_add, _p)

