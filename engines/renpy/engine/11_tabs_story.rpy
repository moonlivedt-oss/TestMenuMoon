# ---------------------- вкладка: сюжет ----------------------
screen tm_tab_story():
    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 14

            # ---- подсказки выборов ----
            hbox:
                spacing 10
                use tm_icon("hint", 30)
                text "Подсказки к выборам" style "tm_h" yalign 0.5
            text "Когда на экране выбор, слева сверху видно, что изменит каждый вариант (+/− переменные, переходы). Варианты, скрытые условием, тоже видны — их можно выбрать." style "tm_dim"
            hbox:
                spacing 12
                textbutton ("Подсказки: ВКЛ" if tm_pref("tm_hints", True) else "Подсказки: выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected tm_pref("tm_hints", True)
                    action Function(tm_toggle_hints)
                textbutton ("Скрытые варианты: видны" if tm_pref("tm_hints_hidden", True) else "Скрытые варианты: нет"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected tm_pref("tm_hints_hidden", True)
                    action Function(tm_toggle_pref, "tm_hints_hidden", True)
                text "Shift+H" style "tm_dim" yalign 0.5
            hbox:
                spacing 8
                text "Последствия:" style "tm_dim" yalign 0.5
                for _sk, _sl in TM_SPOIL_MODES:
                    textbutton _sl:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_spoil() == _sk)
                        tooltip "Сколько подсказка выдаёт заранее: всё, только знак +/−, или по щелчку на варианте"
                        action Function(tm_set_spoil, _sk)

            use tm_sep

            # ---- история выборов ----
            hbox:
                spacing 10
                use tm_icon("story", 30)
                text "История выборов" style "tm_h" yalign 0.5
                textbutton ("запись: ВКЛ" if tm_pref("tm_history", True) else "запись: выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    yalign 0.5
                    selected tm_pref("tm_history", True)
                    tooltip "Запоминать выборы и то, что каждый реально изменил (за эту сессию)"
                    action Function(tm_toggle_pref, "tm_history", True)
                if tm_ui.history:
                    textbutton "очистить" style "tm_seg" text_style "tm_seg_text" yalign 0.5 action Function(tm_hist_clear)
            if not tm_ui.history:
                text "Сделай выбор в игре — здесь появится, что он изменил на самом деле (снимок до и после)." style "tm_dim"
            for _h in reversed(tm_ui.history[-12:]):
                vbox:
                    spacing 2
                    hbox:
                        spacing 10
                        text tm_q(u"«%s»" % _h["text"]) style "tm_label" size 18
                        if _h["where"]:
                            text tm_q(_h["where"]) style "tm_dim" size 14 yalign 0.5
                    if not _h["eff"]:
                        text "ничего не изменил (или изменил то, что меню не видит)" style "tm_dim" size 15
                    else:
                        text tm_hist_markup(_h) style "tm_hint_eff" xmaximum 900

            use tm_sep

            # ---- кнопки экранов ----
            $ _sb = tm_screen_rows(None, 40, "tab")
            hbox:
                spacing 10
                use tm_icon("target", 30)
                text "Кнопки на экране" style "tm_h" yalign 0.5
            text "Кнопки показанных экранов игры (карты, телефон, call screen) и что они делают. «нажать» — как щелчок, перед этим сохраняется «Перед прыжком»." style "tm_dim"
            if not _sb:
                text "Сейчас на экране нет кнопок игры с действиями." style "tm_dim" size 15
            for _bn, _scr, _lbl, _txt, _sens in _sb:
                hbox:
                    spacing 10
                    text tm_q(_scr) style "tm_dim" size 14 min_width 140 yalign 0.5
                    text tm_q(_lbl) style ("tm_label" if _sens else "tm_dim") size 17 min_width 230 yalign 0.5
                    text tm_q(_tm_short(_txt, 46)) style "tm_hint_eff" min_width 330 yalign 0.5
                    textbutton "нажать" style "tm_seg" text_style "tm_seg_text" yalign 0.5 action Function(tm_press_n, "tab", _bn)

            use tm_sep

            # ---- навигация ----
            hbox:
                spacing 12
                use tm_icon("target", 30)
                text "Навигация" style "tm_h" yalign 0.5
                use tm_btn2("pin", "Где я", Function(tm_where_am_i), "Файл, строка и метка текущего места")
            text "Перед переходом меню само сохраняет игру в слот «Перед прыжком» (вкладка «Перемотка»)." style "tm_dim"
            hbox:
                spacing 10
                text "Метка" style "tm_label" yalign 0.5 min_width 110
                use tm_field("jump_label", 340, 60)
                textbutton ("Повторить" if tm_ui.jump_mode == "replay" else "Перейти") style "tm_btn" text_style "tm_btn_text" action Function(tm_label_go, tm_ui.jump_label)
                textbutton "прыжок" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (tm_ui.jump_mode == "jump") tooltip "Перейти на метку: игра продолжится оттуда" action SetField(tm_ui, "jump_mode", "jump")
                textbutton "повтор" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (tm_ui.jump_mode == "replay") tooltip "Повтор сцены, как в галерее: посмотреть и вернуться сюда же, переменные игры не меняются. Выход — End Replay в меню игры" action SetField(tm_ui, "jump_mode", "replay")
            $ _labs = tm_labels(tm_ui.jump_label)
            if _labs:
                hbox:
                    box_wrap True
                    spacing 8
                    for _ln in _labs:
                        textbutton "[_ln!q]" style "tm_seg" text_style "tm_seg_text" action Function(tm_label_go, _ln)

            hbox:
                spacing 10
                text "Реплика" style "tm_label" yalign 0.5 min_width 110
                use tm_field("find_text", 340, 60)
                text "от 3 букв — переход прямо к строке" style "tm_dim" yalign 0.5
            $ _found = tm_find_lines(tm_ui.find_text)
            if _found:
                vbox:
                    spacing 4
                    for _nm, _fn, _ln, _who, _what in _found:
                        button:
                            style "tm_btn"
                            xfill True
                            action Function(tm_goto_node, _nm)
                            hbox:
                                spacing 12
                                text ("%s:%d" % (_fn.split("/")[-1], _ln)) style "tm_btn_text" size 15 color "#8b93a3" min_width 190 yalign 0.5
                                text tm_q(_tm_short((_who + ": " if _who else "") + _what, 70)) style "tm_btn_text" size 17 yalign 0.5
            elif len(tm_ui.find_text.strip()) >= 3:
                text "Не найдено." style "tm_dim"

            use tm_sep

            # ---- галерея / persistent ----
            hbox:
                spacing 10
                use tm_icon("trophy", 30)
                text "Галерея и флаги" style "tm_h" yalign 0.5
            text "«Открыть галерею» отмечает всё просмотренным: Replay-сцены, Gallery и Music Room стандартного вида. Меняет persistent игры навсегда." style "tm_dim"
            use tm_btn2("trophy", ("Точно? Нажми ещё раз" if tm_ui.confirm == "unlock" else "Открыть всю галерею"), Function(tm_confirm, "unlock", tm_unlock_all), "Второй щелчок подтверждает", sel=(tm_ui.confirm == "unlock"))
            hbox:
                spacing 10
                text "Persistent" style "tm_label" yalign 0.5 min_width 110
                use tm_field("flag_filter", 340, 30)
                text "флаги концовок, галерей, бонусов" style "tm_dim" yalign 0.5
            $ _flags = tm_persistent_flags(tm_ui.flag_filter)
            if not _flags:
                text "Числовых и булевых persistent-переменных не найдено." style "tm_dim"
            for _p, _v in _flags:
                hbox:
                    spacing 8
                    text tm_q(_tm_short(_p[11:], 32)) style "tm_label" yalign 0.5 min_width 340
                    text tm_fmt(_v, 12) style "tm_value" yalign 0.5 min_width 130
                    if isinstance(_v, bool):
                        textbutton ("ВКЛ" if _v else "выкл") style "tm_btn" text_style "tm_btn_text" action Function(tm_toggle, _p)
                    else:
                        textbutton "−" style "tm_pm_btn" text_style "tm_pm_text" action Function(tm_add, _p, -tm_ui.stat_step)
                        textbutton "+" style "tm_pm_btn" text_style "tm_pm_text" action Function(tm_add, _p, tm_ui.stat_step)
                        textbutton "ввод" style "tm_btn" text_style "tm_btn_text" action Function(tm_input, _p)

            use tm_sep

            # ---- персонажи: свои имена ----
            hbox:
                spacing 10
                use tm_icon("stats", 30)
                text "Персонажи" style "tm_h" yalign 0.5
            text "Своё имя персонажа в репликах (запоминается для этой игры, «Убрать следы меню» вернёт исходные). Если игра хранит персонажа внутри своих объектов, имя попадёт и в её сейв." style "tm_dim"
            $ _chs = tm_characters()
            if not _chs:
                text "Персонажей с постоянным именем не найдено." style "tm_dim" size 15
            hbox:
                box_wrap True
                spacing 8
                for _cv, _cn, _cown in _chs:
                    textbutton tm_q(_tm_short(_cn, 20)):
                        style "tm_seg" text_style "tm_seg_text"
                        selected _cown
                        tooltip (u"%s — щёлкни, чтобы переименовать" % _cv)
                        action Function(tm_edit_char, _cv)

# ---------------------- вкладка: тест ----------------------
# В переменных экрана — только строки и числа (они пишутся в журнал отката и в сейв).
screen tm_tab_test():
    $ _cov = tm_coverage()
    $ _say, _lab, _chc = tuple(_cov["say"]), tuple(_cov["label"]), tuple(_cov["choice"])
    $ _cov = None
    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 12

            # ---- авто-прохождение ----
            hbox:
                spacing 10
                use tm_icon("rocket", 30)
                text "Авто-прохождение" style "tm_h" yalign 0.5
            text "Меню само листает текст и отвечает на выборы: проверить, что игра не падает, и открыть новые ветки. Перед стартом — сейв «Перед прыжком». Остановить — клавиша меню." style "tm_dim"
            hbox:
                spacing 8
                text "Выбирать:" style "tm_dim" yalign 0.5 min_width 150
                for _mk, _ml in TM_AUTO_MODES:
                    textbutton _ml:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_ui.auto_mode == _mk)
                        tooltip "Новые — сначала варианты, которых ещё ни разу не выбирали (за все партии): так быстрее растёт покрытие"
                        action SetField(tm_ui, "auto_mode", _mk)
            hbox:
                spacing 8
                text "Выборов:" style "tm_dim" yalign 0.5 min_width 150
                for _lk, _ll in TM_AUTO_LIMITS:
                    textbutton _ll:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_ui.auto_limit == _lk)
                        action SetField(tm_ui, "auto_limit", _lk)
            hbox:
                spacing 8
                text "Стоп на метке:" style "tm_dim" yalign 0.5 min_width 150
                use tm_field("auto_stop_label", 260, 60)
                textbutton ("на новой реплике: стоп" if tm_ui.auto_stop_unseen else "на новой реплике: дальше"):
                    style "tm_seg" text_style "tm_seg_text"
                    yalign 0.5
                    selected tm_ui.auto_stop_unseen
                    tooltip "Остановиться на первой реплике, которую ещё ни разу не видели, — «довези до нового контента»"
                    action ToggleField(tm_ui, "auto_stop_unseen")
            hbox:
                spacing 12
                use tm_btn2("rocket", "Запустить", Function(tm_auto_start), "Пошло: меню закроется, игра поедет сама")
                if tm_ui.auto_log:
                    textbutton "очистить журнал" style "tm_seg" text_style "tm_seg_text" yalign 0.5 action SetField(tm_ui, "auto_log", [])
            for _al in tm_ui.auto_log[-6:]:
                text tm_q(_al) style "tm_dim" size 15

            use tm_sep

            # ---- маршруты ----
            hbox:
                spacing 10
                use tm_icon("flag", 30)
                text "Маршруты" style "tm_h" yalign 0.5
            text "Выборы партии записываются сами (с начала игры или с загрузки сейва; откат стирает отменённые). Сохрани маршрут — после обновления игры или в новой партии меню пройдёт те же выборы само." style "tm_dim"
            $ _rn = tm_route_now()
            hbox:
                spacing 12
                text (u"Сейчас: %d выб. (%s)" % (_rn, u"с начала игры" if tm_ui.route_start == "start" else u"с загрузки сейва")) style "tm_label" yalign 0.5
                use tm_btn2("save", "Сохранить маршрут", Function(tm_route_save), "Запомнить выборы этой партии", sens=(_rn > 0))
            for _ri, _rname, _rprev, _rstart in tm_route_rows():
                hbox:
                    spacing 10
                    vbox:
                        xminimum 560
                        text tm_q(_rname) style "tm_label" size 18
                        text tm_q((u"с начала игры | " if _rstart == "start" else u"с сейва | ") + _rprev) style "tm_dim" size 14
                    textbutton "пройти" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Начни новую игру (или загрузи тот же сейв) и нажми — выборы сделаются сами" action Function(tm_route_play, _ri)
                    textbutton ("точно?" if tm_ui.confirm == "route%d" % _ri else "удалить") style "tm_seg" text_style "tm_seg_text" yalign 0.5 action Function(tm_confirm, "route%d" % _ri, tm_route_del, _ri)

            use tm_sep

            # ---- покрытие ----
            hbox:
                spacing 10
                use tm_icon("trophy", 30)
                text "Покрытие" style "tm_h" yalign 0.5
            text "Сколько игры уже видели на этом компьютере (за все партии)." style "tm_dim"
            for _cl, _cp in ((u"Реплики", _say), (u"Сцены (метки)", _lab), (u"Варианты выбора", _chc)):
                hbox:
                    spacing 14
                    text _cl style "tm_label" yalign 0.5 min_width 220
                    bar value StaticValue(tm_cov_part(_cp), 1.0) style "tm_bar" xsize 260 ysize 14 yalign 0.5
                    text tm_cov_text(_cp) style "tm_dim" yalign 0.5

            use tm_sep

            # ---- сцены ----
            $ _srows, _stotal = tm_scene_rows(tm_ui.scene_filter, tm_ui.scene_all)
            hbox:
                spacing 10
                use tm_icon("story", 30)
                text "Сцены" style "tm_h" yalign 0.5
                textbutton "непросмотренные" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (not tm_ui.scene_all) action SetField(tm_ui, "scene_all", False)
                textbutton "все" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected tm_ui.scene_all action SetField(tm_ui, "scene_all", True)
                use tm_field("scene_filter", 220, 40)
                text ("найдено: %d" % _stotal) style "tm_dim" yalign 0.5
            text "«откуда» — какие переходы ведут в сцену и при каких условиях или выборах (кнопки экранов-карт сюда не попадают)." style "tm_dim" size 15
            if not _srows:
                use tm_empty("party", "Непросмотренных сцен нет — или ничего не подходит под фильтр.")
            for _sn, _sw, _ss in _srows:
                hbox:
                    spacing 8
                    if _ss and tm_ic("ok"):
                        add tm_ic("ok") zoom 0.3 yalign 0.5
                    else:
                        null width 19
                    text tm_q(_tm_short(_sn, 34)) style ("tm_dim" if _ss else "tm_label") size 17 min_width 330 yalign 0.5
                    text tm_q(_sw) style "tm_dim" size 14 min_width 190 yalign 0.5
                    textbutton "перейти" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Прыжок на метку (перед этим — сейв «Перед прыжком»)" action Function(tm_jump, _sn)
                    textbutton "повтор" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Повтор сцены без последствий" action Function(tm_replay, _sn)
                    textbutton "откуда" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (tm_ui.scene_open == _sn) action Function(tm_scene_toggle, _sn)
                if tm_ui.scene_open == _sn:
                    $ _refs = tm_scene_refs(_sn)
                    frame:
                        background Solid("#ffffff0a")
                        padding (14, 6)
                        xfill True
                        vbox:
                            spacing 2
                            if not _refs:
                                text "Переходов сюда нет: сцена идёт сразу после предыдущей по тексту или вызывается кодом/кнопкой экрана." style "tm_dim" size 15
                            for _rf in _refs:
                                text tm_q(_rf) style "tm_hint_eff" size 15

            use tm_sep

            # ---- заметки о багах ----
            hbox:
                spacing 10
                use tm_icon("bug", 30)
                text "Заметки о багах" style "tm_h" yalign 0.5
            $ _nb = tm_bug_count()
            text ((u"Записано заметок: %d — tm_bugs/tm_bugs.md в папке игры. " % _nb if _nb else u"") + u"Shift+B в любой момент игры: текст, место, реплика, картинки, звук и скриншот.") style "tm_dim"
            hbox:
                spacing 12
                use tm_btn2("bug", "Заметка о баге", Function(tm_bug_request), "Спрятать меню, снять экран игры и записать заметку (Shift+B)")
                use tm_btn2("story", "Отчёт тестера", Function(tm_write_report), "Где я, покрытие, маршрут, история выборов, правки — в файл")

# ---------------------- вкладка: вид и инструменты ----------------------
screen tm_tab_settings():
    python:
        _cur_accent = tm_acc()
        _cur_op = tm_pref("tm_opacity", "f7")
        _cur_sc = float(tm_pref("tm_scale", 1.0))

    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 18

            # ---- Перевод реплик (модуль zzz_testmenu_translate.rpy, если положен) ----
            if renpy.has_screen("tmtr_settings"):
                use tmtr_settings
                use tm_sep

            # ---- Пульт в студии ----
            hbox:
                spacing 10
                use tm_icon("rocket", 30)
                text "Пульт в студии" style "tm_h" yalign 0.5
            hbox:
                spacing 12
                textbutton ("Пульт: ВКЛ" if _tm_bridge.on else "Пульт: выкл"):
                    style "tm_btn" text_style "tm_btn_text"
                    selected _tm_bridge.on
                    tooltip "Значения и заморозки — из окна «Пульт» студии, не открывая меню поверх игры"
                    action Function(tm_bridge_set, not _tm_bridge.on)
                if _tm_bridge.on:
                    text ("связь со студией есть" if _tm_bridge.ok else "жду студию: открой в ней «Пульт»") style "tm_dim" yalign 0.5
            use tm_sep

            # ---- Внешний вид ----
            hbox:
                spacing 10
                use tm_icon("palette", 30)
                text "Внешний вид" style "tm_h" yalign 0.5

            hbox:
                spacing 12
                text "Цвет акцента" style "tm_label" yalign 0.5 min_width 220
                hbox:
                    spacing 10
                    for _name, _hex in TM_ACCENTS:
                        frame:
                            padding (3, 3)
                            background (Frame(Solid("#ffffff"), 4, 4) if _cur_accent == _hex else Solid("#00000000"))
                            button:
                                xysize (40, 40)
                                background Frame(Solid(_hex), 6, 6)
                                tooltip _name
                                action Function(tm_set_accent, _hex)

            hbox:
                spacing 12
                text "Прозрачность окна" style "tm_label" yalign 0.5 min_width 220
                hbox:
                    spacing 8
                    for _lbl, _op in TM_OPACITY:
                        textbutton "[_lbl]":
                            style "tm_seg" text_style "tm_seg_text"
                            selected (_cur_op == _op)
                            action Function(tm_set_opacity, _op)

            hbox:
                spacing 12
                text "Размер шрифта" style "tm_label" yalign 0.5 min_width 220
                hbox:
                    spacing 8
                    for _lbl, _sc in TM_SCALES:
                        textbutton "[_lbl]":
                            style "tm_seg" text_style "tm_seg_text"
                            selected (abs(_cur_sc - _sc) < 0.001)
                            tooltip "Окно растёт вместе со шрифтом"
                            action Function(tm_set_scale, _sc)

            hbox:
                spacing 12
                textbutton "Окно в центр" style "tm_btn" text_style "tm_btn_text" action Function(tm_reset_pos)
                textbutton "Сбросить оформление" style "tm_btn" text_style "tm_btn_text" action Function(tm_theme_reset)

            use tm_sep

            # ---- HUD ----
            hbox:
                spacing 10
                use tm_icon("eye", 30)
                text "HUD наблюдения" style "tm_h" yalign 0.5
            text "Значения, отмеченные глазом на вкладке «Переменные», видны поверх игры справа сверху и обновляются вживую." style "tm_dim"
            hbox:
                spacing 12
                textbutton ("HUD: ВКЛ" if tm_ui.hud_on else "HUD: выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected tm_ui.hud_on
                    action ToggleField(tm_ui, "hud_on")
                textbutton ("Очистить HUD (%d)" % len(tm_ui.watch)):
                    style "tm_btn" text_style "tm_btn_text"
                    sensitive bool(tm_ui.watch)
                    action Function(tm_watch_clear)
            hbox:
                spacing 8
                text "Угол" style "tm_dim" yalign 0.5
                for _ck, _cl in TM_HUD_CORNERS:
                    textbutton _cl:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_hud_corner() == _ck)
                        action Function(tm_set_hud_corner, _ck)
            text "При изменении значения рядом на пару секунд вспыхивает разница: +2, −50." style "tm_dim" size 15
            hbox:
                spacing 10
                text "Выражение" style "tm_label" yalign 0.5 min_width 140
                use tm_field("hud_expr", 420, 120)
                textbutton "+ в HUD" style "tm_btn" text_style "tm_btn_text" tooltip "Любое выражение игры: money + bank, len(inventory), day % 7" action Function(tm_hud_add_expr)

            use tm_sep

            # ---- Клавиши ----
            hbox:
                spacing 10
                use tm_icon("key", 30)
                text "Клавиша меню" style "tm_h" yalign 0.5
            text "Shift+T работает всегда. Запасная клавиша — на выбор (F9 во многих играх и у UnRen — быстрая загрузка; если она занята, по умолчанию F10)." style "tm_dim"
            hbox:
                spacing 8
                text "Запасная:" style "tm_dim" yalign 0.5
                for _kl, _kk in TM_ALT_KEYS:
                    textbutton _kl:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_alt_key() == _kk)
                        action Function(tm_set_alt_key, _kk)

            use tm_sep

            # ---- Инструменты тестера ----
            hbox:
                spacing 10
                use tm_icon("console", 30)
                text "Инструменты тестера" style "tm_h" yalign 0.5
            text "Консоль разработчика открывается по Shift+O (переменные, jump, любые команды). Скриншот кладётся в папку игры." style "tm_dim"
            hbox:
                spacing 12
                textbutton ("Консоль (Shift+O): ВКЛ" if config.developer else "Консоль (Shift+O): выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected bool(config.developer)
                    action Function(tm_toggle_dev)
                use tm_btn2("pin", "Где я", Function(tm_where_am_i), "Файл, строка, метка, стек вызовов, экраны")
                use tm_btn2("camera", "Скриншот", Function(tm_screenshot), "Сохранить снимок экрана в папку игры")
            hbox:
                spacing 12
                use tm_btn2("story", "Отчёт тестера", Function(tm_write_report), "Файл в папке игры: где я, история выборов с изменениями, правки из меню, избранное")
                use tm_btn2("close", ("Точно? Нажми ещё раз" if tm_ui.confirm == "purge" else "Убрать следы меню"), Function(tm_confirm, "purge", tm_purge), "Перед удалением меню: быстрые слоты, tm_state.json и настройки меню в persistent", sel=(tm_ui.confirm == "purge"))
