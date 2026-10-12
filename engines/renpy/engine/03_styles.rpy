# ============================ styles ============================
style tm_shade is default:
    background Solid("#00000000")

style tm_panel is default:
    background Frame(Solid(TM_TOK["bg_panel"] + "f7"), 0, 0)

style tm_border is default:
    background Frame(Solid(tm_accent), 0, 0)

style tm_header_bg is default:
    background Solid(tm_accent)

style tm_footer_bg is default:
    background Solid(TM_TOK["bg_window"])

style tm_tabbar_bg is default:
    background Solid(TM_TOK["bg_card"])

style tm_tab_btn is default:
    padding (7, 8, 8, 8)              # 7 вкладок со значками должны влезать в окно
    background Solid("#00000000")
    hover_background Solid(TM_TOK["tint_2"])
    selected_background Solid(TM_TOK["tint_1"])

style tm_tab_text is default:
    font tm_font
    size 20
    color TM_TOK["text_hint"]
    hover_color TM_TOK["text_bright"]
    selected_color TM_TOK["text_bright"]
    selected_bold True

style tm_btn is default:
    padding (14, 7)
    background Frame(Solid(TM_TOK["tint_2"]), 8, 8)
    hover_background Frame(Solid(tm_accent), 8, 8)

style tm_btn_text is default:
    font tm_font
    size 20
    color TM_TOK["text"]
    hover_color TM_TOK["on_accent"]

style tm_pm_btn is default:
    xsize 44
    ysize 40
    background Frame(Solid(TM_TOK["tint_2"]), 8, 8)
    hover_background Frame(Solid(tm_accent), 8, 8)

style tm_pm_text is default:
    font tm_font
    size 26
    color TM_TOK["text"]
    hover_color TM_TOK["on_accent"]
    insensitive_color "#ffffff2a"
    xalign 0.5
    yalign 0.5

style tm_head_btn is default:
    padding (12, 6)
    background Frame(Solid(TM_TOK["on_accent"] + "55"), 8, 8)
    hover_background Frame(Solid(TM_TOK["on_accent"]), 8, 8)

style tm_head_btn_text is default:
    font tm_font
    size 18
    color TM_TOK["on_accent"]
    hover_color TM_TOK["text_bright"]
    bold True

style tm_label is default:
    font tm_font
    size 20
    color TM_TOK["text"]

style tm_value is default:
    font tm_font
    size 22
    color tm_accent
    bold True

style tm_dim is default:
    font tm_font
    size 17
    color TM_TOK["text_hint"]

style tm_foot is default:
    font tm_font
    size 16
    color TM_TOK["text_off"]

style tm_h is default:
    font tm_font
    size 25
    color TM_TOK["text_bright"]
    bold True

style tm_bar is default:
    xsize 320
    ysize 26
    left_bar Solid(tm_accent)
    right_bar Solid(TM_TOK["tint_3"])
    thumb None

style tm_seg is default:
    padding (16, 8)
    background Frame(Solid(TM_TOK["tint_2"]), 8, 8)
    hover_background Frame(Solid(TM_TOK["tint_3"]), 8, 8)
    selected_background Frame(Solid(tm_accent), 8, 8)

style tm_seg_text is default:
    font tm_font
    size 19
    color TM_TOK["text_dim"]
    hover_color TM_TOK["text_bright"]
    selected_color TM_TOK["on_accent"]
    selected_bold True

style tm_filter_frame is default:
    background Frame(Solid(TM_TOK["tint_2"]), 6, 6)
    padding (10, 6)

style tm_filter_text is default:
    font tm_font
    size 18
    color TM_TOK["text"]

style tm_head_title is default:
    font tm_font
    size 23
    color TM_TOK["on_accent"]
    bold True

# Свой скроллбар для всех списков меню: со стилем игры он мог быть чужим, а в играх
# без gui-стилей vscrollbar растягивался на всю ширину и прятал содержимое.
style tm_vscrollbar is vscrollbar:
    xsize 8
    xmaximum 8
    base_bar Frame(Solid(TM_TOK["tint_1"]), 0, 0)
    thumb Frame(Solid(TM_TOK["tint_4"]), 0, 0)
    hover_thumb Frame(Solid(tm_accent), 0, 0)
    thumb_offset 0
    top_gutter 0
    bottom_gutter 0
    unscrollable "hide"

style tm_side is side:
    spacing 6

style tm_bad is default:
    font tm_font
    size 20
    color TM_TOK["err"]
    bold True

style tm_warn is default:
    font tm_font
    size 20
    color TM_TOK["warn"]
    bold True

style tm_hud_frame is default:
    background Frame(Solid(TM_TOK["bg_window"] + "d8"), 0, 0)
    padding (16, 10)
    xalign 1.0
    xoffset -16
    yoffset 16

style tm_hud_label is default:
    font tm_font
    size 17
    color TM_TOK["text_dim"]
    outlines [(1, "#00000080", 0, 0)]

style tm_hud_value is tm_hud_label:
    color tm_accent
    bold True

style tm_hint_frame is default:
    background Frame(Solid(TM_TOK["bg_window"] + "e6"), 0, 0)
    padding (20, 14)
    xpos 16
    ypos 16
    xmaximum 640

style tm_hint_h is default:
    font tm_font
    size 19
    color tm_accent
    bold True

style tm_hint_choice is default:
    font tm_font
    size 18
    color TM_TOK["text_bright"]
    bold True
    yalign 0.5

style tm_hint_hidden is tm_hint_choice:
    color TM_TOK["warn"]

style tm_hint_note is default:
    font tm_font
    size 15
    color TM_TOK["warn"]

style tm_hint_eff is default:
    font tm_font
    size 16
    color TM_TOK["text_dim"]

style tm_icon_btn is default:
    xsize 40
    ysize 40
    background Frame(Solid(TM_TOK["tint_2"]), 8, 8)
    hover_background Frame(Solid(tm_accent), 8, 8)
    selected_background Frame(Solid(tm_accent), 8, 8)

style tm_icon_text is default:
    font tm_font
    size 19
    color TM_TOK["text_dim"]
    hover_color TM_TOK["on_accent"]
    selected_color TM_TOK["on_accent"]
    xalign 0.5
    yalign 0.5

# поле ввода-кнопка: щелчок делает поле активным (в Ren'Py печатать можно только в одно
# поле экрана — раньше на «Сюжете» работало лишь первое из трёх)
style tm_name_btn is default:
    padding (6, 2, 6, 2)
    background None
    hover_background Frame(Solid(TM_TOK["tint_2"]), 6, 6)

style tm_field is default:
    padding (10, 6)
    background Frame(Solid(TM_TOK["tint_2"]), 6, 6)
    hover_background Frame(Solid(TM_TOK["tint_3"]), 6, 6)
    selected_background Frame(Solid(TM_TOK["accent"] + "40"), 6, 6)

style tm_tip is default:
    font tm_font
    size 16
    color TM_TOK["text_dim"]

style tm_ico_label is default:
    font tm_font
    size 20
    color TM_TOK["text"]
    hover_color TM_TOK["on_accent"]
    selected_color TM_TOK["on_accent"]
    insensitive_color TM_TOK["tint_4"]
    yalign 0.5

