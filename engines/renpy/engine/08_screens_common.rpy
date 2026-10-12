# Окно меню и панели масштабируются под разрешение игры: вёрстка рассчитана на 1080p,
# в 720p-игре всё уменьшается в 2/3 (раньше окно занимало почти весь экран).
init -4 python:
    def tm_k():
        try:
            k = float(config.screen_height) / 1080.0
        except Exception:
            k = 1.0
        return max(0.5, min(2.0, k))

transform tm_zoomer(z=1.0):
    zoom z

# появление окна меню и всплывающих панелей
transform tm_pop(z=1.0):
    zoom z
    on show:
        alpha 0.0
        yoffset 12
        easein 0.14 alpha 1.0 yoffset 0
    on hide:
        easeout 0.10 alpha 0.0

# ---------------------- общие кусочки ----------------------
# значок из tm_ui/ic (64 px) нужного размера; нет файла — ничего не рисуем
screen tm_icon(name, px=26):
    $ _ic = tm_ic(name)
    if _ic:
        add _ic zoom (px / 64.0) yalign 0.5

# кнопка-значок: картинка, а без значков — запасной символ текстом
screen tm_icobtn(name, act, sel=False, tip="", alt="", sens=True):
    button:
        style "tm_icon_btn"
        selected sel
        sensitive sens
        tooltip tip
        action act
        if tm_ic(name):
            add tm_ic(name) zoom 0.44 align (0.5, 0.5)
        else:
            text alt style "tm_icon_text"

# кнопка «значок + подпись»
screen tm_btn2(name, label, act, tip="", sens=True, sel=False):
    button:
        style "tm_btn"
        sensitive sens
        selected sel
        tooltip tip
        action act
        hbox:
            spacing 8
            use tm_icon(name, 24)
            text label style "tm_ico_label"

# поле ввода: щелчок по полю делает его активным (см. style tm_field)
screen tm_field(field, w=300, n=30):
    $ _iv = FieldInputValue(tm_ui, field)
    button:
        style "tm_field"
        xsize w
        action _iv.Enable()
        input value _iv style "tm_filter_text" length n copypaste True

screen tm_sep():
    frame:
        xfill True
        ysize 1
        background Solid("#ffffff14")

# пустое состояние: маскот + пояснение
screen tm_empty(mascot, msg):
    hbox:
        spacing 18
        $ _m = tm_mascot(mascot)
        if _m:
            add _m zoom 0.5 yalign 0.5
        text msg style "tm_dim" yalign 0.5 xmaximum 640

screen tm_overlay():
    zorder 190
    if tm_ui.open:
        use tm_menu
    elif not main_menu:
        if tm_pref("tm_hints", True):
            # в переменных экрана — только имя узла: экранные переменные пишутся в журнал
            # отката и в сейв, а узел сценария тянет за собой весь сценарий по цепочке .next
            # (сейв большой игры падал с RecursionError)
            $ _tm_mn = tm_cur_menu_name()
            if _tm_mn is not None:
                use tm_hints_panel(_tm_mn)
            else:
                $ _tm_cs = tm_cur_call_screen()
                if _tm_cs:
                    use tm_screen_hints(_tm_cs)
        if tm_ui.watch and tm_ui.hud_on:
            use tm_hud
        if tm_ui.mini:
            use tm_mini
        if tm_ui.auto:
            use tm_auto_badge
    if tm_ui.bug_pending:
        # меню уже спрятано — через пару кадров снимаем экран игры для заметки о баге
        timer 0.12 action Function(tm_bug_capture)
    if not main_menu:
        use tm_toasts

# ---------------------- плашка «идёт авто-прохождение» ----------------------
screen tm_auto_badge():
    frame at tm_zoomer(tm_k()):
        style "tm_hud_frame"
        xalign 0.5
        xoffset 0
        yalign 1.0
        yoffset -12
        padding (14, 6)
        hbox:
            spacing 10
            use tm_icon("rocket", 24)
            text tm_q(tm_auto_badge_text()) style "tm_hud_label"
            text (tm_keys_text() + u" — стоп") style "tm_hud_label" color "#8b93a3"

# ---------------------- свои уведомления ----------------------
transform tm_toast_fx(z=1.0):
    zoom z
    alpha 0.0
    yoffset -8
    easein 0.15 alpha 1.0 yoffset 0
    pause 2.6
    linear 0.5 alpha 0.0

screen tm_toasts():
    $ _ts = tm_toasts_live()
    if _ts:
        vbox:
            xalign 0.5
            ypos int((70 if tm_ui.mini else 10) * tm_k())
            spacing 6
            for _t, _msg, _kind in _ts:
                # цветная полоса слева = отступ внешней рамки, высота — по тексту
                frame at tm_toast_fx(tm_k()):
                    xalign 0.5
                    background Solid(TM_TOAST_COLORS.get(_kind, "#38e0c8"))
                    padding (6, 0, 0, 0)
                    frame:
                        background Solid("#0b0e14f2")
                        padding (14, 9, 18, 9)
                        text tm_q(_msg) style "tm_tip" size 18 xmaximum 900

# ---------------------- мини-режим: плашка с кнопками поверх игры ----------------------
screen tm_mini():
    $ _sl = tm_slots()
    frame at tm_zoomer(tm_k()):
        style "tm_hud_frame"
        xalign 0.5
        xoffset 0
        yoffset 12
        padding (10, 8)
        hbox:
            spacing 6
            use tm_icobtn("logo", Function(tm_unminimize), alt="TM")
            use tm_icobtn("back", Function(tm_rollback, 1), alt="<")
            use tm_icobtn("save", Function(tm_quick_save, 1), alt="S")
            use tm_icobtn("load", Function(tm_quick_load, 1), sens=_sl[1][0], alt="L")
            use tm_icobtn("skip", Function(tm_start_skip, "fast"), alt=">>")
            use tm_icobtn("eye", ToggleField(tm_ui, "hud_on"), sel=tm_ui.hud_on, alt="o")
            use tm_icobtn("close", SetField(tm_ui, "mini", False), alt="X")

# ---------------------- HUD наблюдения (не ловит клики) ----------------------
transform tm_flash_fx:
    alpha 1.0
    pause 2.2
    linear 0.6 alpha 0.0

screen tm_hud():
    $ _c = tm_hud_corner()
    frame at tm_zoomer(tm_k()):
        style "tm_hud_frame"
        xalign (0.0 if _c in ("tl", "bl") else 1.0)
        yalign (1.0 if _c in ("bl", "br") else 0.0)
        xoffset (16 if _c in ("tl", "bl") else -16)
        yoffset (-200 if _c in ("bl", "br") else 16)
        vbox:
            spacing 2
            for _l, _p in tm_ui.watch:
                $ _ok, _v = tm_probe(_p)
                $ _fl = tm_hud_flash(_p)
                hbox:
                    spacing 12
                    text tm_q(_tm_short(tm_nice(_l, _p)[0], 26)) style "tm_hud_label" min_width 210
                    text (tm_fmt(_v, 16) if _ok else u"—") style "tm_hud_value"
                    if _p in tm_ui.frozen:
                        if tm_ic("snow"):
                            add tm_ic("snow") zoom 0.3 yalign 0.5
                        else:
                            text "*" style "tm_hud_label" color "#9fd8ff"
                    if _fl:
                        text _fl[0] style "tm_hud_value" color _fl[1] at tm_flash_fx

# ---------------------- подсказки к выборам ----------------------
screen tm_hints_panel(node):
    # node — имя узла выбора (не сам узел: см. tm_overlay)
    $ _hs = tm_menu_hints_name(node)
    $ _show_hidden = tm_pref("tm_hints_hidden", True)
    $ _sp = tm_spoil()
    frame at tm_zoomer(tm_k()):
        style "tm_hint_frame"
        vbox:
            spacing 10
            hbox:
                spacing 10
                use tm_icon("hint", 26)
                text "Подсказки выбора" style "tm_hint_h" yalign 0.5
                text "Shift+H — скрыть" style "tm_foot" yalign 0.5
            for _i, _lbl, _cond, _effs in _hs:
                $ _vis = tm_cond_ok(_cond)
                if _vis or _show_hidden:
                    vbox:
                        spacing 2
                        hbox:
                            spacing 10
                            text tm_q(_tm_short(tm_choice_text(_lbl), 46)) style ("tm_hint_choice" if _vis else "tm_hint_hidden")
                            if not _vis:
                                textbutton "выбрать":
                                    style "tm_seg" text_style "tm_seg_text"
                                    text_size 15
                                    padding (10, 3)
                                    yalign 0.5
                                    action Function(tm_pick_choice, node, _i)
                            textbutton "код":
                                style "tm_seg" text_style "tm_seg_text"
                                text_size 14
                                padding (8, 2)
                                yalign 0.5
                                selected ((node, _i) in tm_ui.code_peek)
                                action Function(tm_code_toggle, (node, _i))
                        if (node, _i) in tm_ui.code_peek:
                            frame:
                                background Solid("#ffffff0a")
                                padding (10, 6)
                                text tm_q(tm_choice_code(node, _i)) style "tm_hint_eff" size 14 color "#9aa3b5"
                        if not _vis:
                            text (u"скрыт, условие: " + tm_q(_tm_short(_cond, 52))) style "tm_hint_note"
                            $ _now = tm_cond_now(_cond)
                            if _now:
                                text tm_q(_now) style "tm_hint_note" color "#c7a978"
                        if _sp == "full" or (node, _i) in tm_ui.peek:
                            text tm_hint_markup(_effs) style "tm_hint_eff"
                        elif _sp == "sign":
                            text tm_hint_sign(_effs) style "tm_hint_eff" size 20
                        else:
                            textbutton "показать последствия":
                                style "tm_seg" text_style "tm_seg_text"
                                text_size 14
                                padding (10, 2)
                                action Function(tm_peek_toggle, (node, _i))

# ---------------------- подсказки на экранах-развилках (call screen) ----------------------
screen tm_screen_hints(scr):
    $ _bs = tm_screen_rows(scr, 14)
    if _bs:
        frame at tm_zoomer(tm_k()):
            style "tm_hint_frame"
            vbox:
                spacing 6
                hbox:
                    spacing 10
                    use tm_icon("hint", 26)
                    text ("Кнопки экрана " + tm_q(scr)) style "tm_hint_h" yalign 0.5
                    text "Shift+H — скрыть" style "tm_foot" yalign 0.5
                for _bn, _scr, _lbl, _txt, _sens in _bs:
                    hbox:
                        spacing 10
                        text tm_q(_lbl) style ("tm_hint_choice" if _sens else "tm_hint_hidden") size 16 min_width 200
                        text tm_q(_tm_short(_txt, 50)) style "tm_hint_eff"

