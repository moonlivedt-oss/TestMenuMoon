# ============================ styles ============================
style tm_shade is default:
    background Solid("#00000000")

style tm_panel is default:
    background Frame(Solid("#10141df7"), 0, 0)

style tm_border is default:
    background Frame(Solid(tm_accent), 0, 0)

style tm_header_bg is default:
    background Solid(tm_accent)

style tm_footer_bg is default:
    background Solid("#0b0e14")

style tm_tabbar_bg is default:
    background Solid("#161b26")

style tm_tab_btn is default:
    padding (7, 8, 8, 8)              # 7 вкладок со значками должны влезать в окно
    background Solid("#00000000")
    hover_background Solid("#ffffff10")
    selected_background Solid("#ffffff0c")

style tm_tab_text is default:
    font tm_font
    size 20
    color "#8b93a3"
    hover_color "#ffffff"
    selected_color "#ffffff"
    selected_bold True

style tm_btn is default:
    padding (14, 7)
    background Frame(Solid("#ffffff12"), 8, 8)
    hover_background Frame(Solid(tm_accent), 8, 8)

style tm_btn_text is default:
    font tm_font
    size 20
    color "#e7ebf2"
    hover_color "#0a0c10"

style tm_pm_btn is default:
    xsize 44
    ysize 40
    background Frame(Solid("#ffffff12"), 8, 8)
    hover_background Frame(Solid(tm_accent), 8, 8)

style tm_pm_text is default:
    font tm_font
    size 26
    color "#e7ebf2"
    hover_color "#0a0c10"
    insensitive_color "#ffffff2a"
    xalign 0.5
    yalign 0.5

style tm_head_btn is default:
    padding (12, 6)
    background Frame(Solid("#0a0c1055"), 8, 8)
    hover_background Frame(Solid("#0a0c10"), 8, 8)

style tm_head_btn_text is default:
    font tm_font
    size 18
    color "#0a0c10"
    hover_color "#ffffff"
    bold True

style tm_label is default:
    font tm_font
    size 20
    color "#e7ebf2"

style tm_value is default:
    font tm_font
    size 22
    color tm_accent
    bold True

style tm_dim is default:
    font tm_font
    size 17
    color "#8b93a3"

style tm_foot is default:
    font tm_font
    size 16
    color "#5b6373"

style tm_h is default:
    font tm_font
    size 25
    color "#ffffff"
    bold True

style tm_bar is default:
    xsize 320
    ysize 26
    left_bar Solid(tm_accent)
    right_bar Solid("#ffffff1e")
    thumb None

style tm_seg is default:
    padding (16, 8)
    background Frame(Solid("#ffffff10"), 8, 8)
    hover_background Frame(Solid("#ffffff20"), 8, 8)
    selected_background Frame(Solid(tm_accent), 8, 8)

style tm_seg_text is default:
    font tm_font
    size 19
    color "#c7ccd4"
    hover_color "#ffffff"
    selected_color "#0a0c10"
    selected_bold True

style tm_filter_frame is default:
    background Frame(Solid("#ffffff10"), 6, 6)
    padding (10, 6)

style tm_filter_text is default:
    font tm_font
    size 18
    color "#e7ebf2"

style tm_head_title is default:
    font tm_font
    size 23
    color "#0a0c10"
    bold True

# Свой скроллбар для всех списков меню: со стилем игры он мог быть чужим, а в играх
# без gui-стилей vscrollbar растягивался на всю ширину и прятал содержимое.
style tm_vscrollbar is vscrollbar:
    xsize 8
    xmaximum 8
    base_bar Frame(Solid("#ffffff0d"), 0, 0)
    thumb Frame(Solid("#ffffff3a"), 0, 0)
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
    color "#ff6b6b"
    bold True

style tm_warn is default:
    font tm_font
    size 20
    color "#ffb454"
    bold True

style tm_hud_frame is default:
    background Frame(Solid("#0b0e14d8"), 0, 0)
    padding (16, 10)
    xalign 1.0
    xoffset -16
    yoffset 16

style tm_hud_label is default:
    font tm_font
    size 17
    color "#c7ccd4"
    outlines [(1, "#00000080", 0, 0)]

style tm_hud_value is tm_hud_label:
    color tm_accent
    bold True

style tm_hint_frame is default:
    background Frame(Solid("#0b0e14e6"), 0, 0)
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
    color "#ffffff"
    bold True
    yalign 0.5

style tm_hint_hidden is tm_hint_choice:
    color "#ffb454"

style tm_hint_note is default:
    font tm_font
    size 15
    color "#ffb454"

style tm_hint_eff is default:
    font tm_font
    size 16
    color "#c7ccd4"

style tm_icon_btn is default:
    xsize 40
    ysize 40
    background Frame(Solid("#ffffff12"), 8, 8)
    hover_background Frame(Solid(tm_accent), 8, 8)
    selected_background Frame(Solid(tm_accent), 8, 8)

style tm_icon_text is default:
    font tm_font
    size 19
    color "#c7ccd4"
    hover_color "#0a0c10"
    selected_color "#0a0c10"
    xalign 0.5
    yalign 0.5

# поле ввода-кнопка: щелчок делает поле активным (в Ren'Py печатать можно только в одно
# поле экрана — раньше на «Сюжете» работало лишь первое из трёх)
style tm_name_btn is default:
    padding (6, 2, 6, 2)
    background None
    hover_background Frame(Solid("#ffffff10"), 6, 6)

style tm_field is default:
    padding (10, 6)
    background Frame(Solid("#ffffff10"), 6, 6)
    hover_background Frame(Solid("#ffffff1c"), 6, 6)
    selected_background Frame(Solid("#38e0c840"), 6, 6)

style tm_tip is default:
    font tm_font
    size 16
    color "#c7ccd4"

style tm_ico_label is default:
    font tm_font
    size 20
    color "#e7ebf2"
    hover_color "#0a0c10"
    selected_color "#0a0c10"
    insensitive_color "#ffffff40"
    yalign 0.5

