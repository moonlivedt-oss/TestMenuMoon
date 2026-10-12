// TEST MENU - Draw GUI
if (!tm_open) exit;
var _w = display_get_gui_width();
var _h = display_get_gui_height();
// TM_TOKENS_START: цвета из engines/_shared/tm_tokens.json (python tools/gen_tokens.py)
var _acc = make_color_rgb(56, 224, 200);
var _txt = make_color_rgb(231, 235, 242);
var _dim = make_color_rgb(154, 163, 180);
var _warn = make_color_rgb(255, 180, 84);
var _frozen = make_color_rgb(159, 216, 255);
// TM_TOKENS_END
draw_set_alpha(0.86);
draw_set_color(c_black);
draw_rectangle(0, 0, _w, _h, false);
draw_set_alpha(1);
draw_set_font(-1);
draw_set_halign(fa_left);
draw_set_valign(fa_top);
draw_set_color(_acc);
var _tabs = ["Globals", "Rooms", "Game"];
draw_text(24, 14, "TEST MENU  |  " + _tabs[tm_tab] + "   (Tab: next page)   speed x" + string(tm_speeds[tm_speed_i]));
draw_set_color(_dim);
var _help = "Up/Down select, Left/Right -/+ (Shift x10), Enter edit, F freeze, 1/2/3 step 1/10/100, Shift+T close";
if (tm_tab == 1) _help = "Up/Down select, Enter go to room, Shift+T close";
if (tm_tab == 2) _help = "Left/Right change speed, Enter on a room line to jump, Shift+T close";
draw_text(24, 34, _help);
var _y = 62;
var _lh = 20;
if (tm_tab == 0) {
    var _n = array_length(tm_names);
    if (_n == 0) draw_text(24, _y, "No global variables.");
    for (var _i = tm_top; _i < min(_n, tm_top + 22); _i += 1) {
        var _nm = tm_names[_i];
        var _v = variable_global_get(_nm);
        var _vs = "";
        if (is_bool(_v)) _vs = _v ? "true" : "false";
        else if (is_real(_v) || is_numeric(_v) || is_string(_v)) _vs = string(_v);
        else _vs = "<" + typeof(_v) + ">";
        if (string_length(_vs) > 40) _vs = string_copy(_vs, 1, 40) + "...";
        draw_set_color(_i == tm_sel ? _acc : _txt);
        draw_text(24, _y, (_i == tm_sel ? "> " : "  ") + _nm);
        draw_set_color(ds_map_exists(tm_frozen, _nm) ? _frozen : (_i == tm_sel ? _acc : _dim));
        draw_text(_w * 0.5, _y, _vs + (ds_map_exists(tm_frozen, _nm) ? "   [frozen]" : ""));
        _y += _lh;
    }
    draw_set_color(_dim);
    draw_text(24, _h - 28, string(_n) + " globals, step " + string(tm_step));
}
if (tm_tab == 1) {
    var _n = array_length(tm_rooms);
    for (var _i = tm_top; _i < min(_n, tm_top + 22); _i += 1) {
        draw_set_color(_i == tm_sel ? _acc : (tm_rooms[_i] == room ? _warn : _txt));
        draw_text(24, _y, (_i == tm_sel ? "> " : "  ") + room_get_name(tm_rooms[_i]) + (tm_rooms[_i] == room ? "   (here)" : ""));
        _y += _lh;
    }
}
if (tm_tab == 2) {
    var _rows = ["Game speed: x" + string(tm_speeds[tm_speed_i]) + "  (fps " + string(game_get_speed(gamespeed_fps)) + ")",
                 "Next room", "Previous room"];
    for (var _i = 0; _i < 3; _i += 1) {
        draw_set_color(_i == tm_sel ? _acc : _txt);
        draw_text(24, _y, (_i == tm_sel ? "> " : "  ") + _rows[_i]);
        _y += _lh;
    }
    draw_set_color(_dim);
    draw_text(24, _y + 10, "Current room: " + room_get_name(room) + "   FPS: " + string(fps));
}
draw_set_color(_txt);
