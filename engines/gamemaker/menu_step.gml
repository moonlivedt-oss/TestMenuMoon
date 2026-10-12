// TEST MENU - Step: Shift+T / F9 toggles; while open other instances are deactivated (paused).
if ((keyboard_check(vk_shift) && keyboard_check_pressed(ord("T"))) || keyboard_check_pressed(vk_f9)) {
    tm_open = !tm_open;
    if (tm_open) {
        tm_names = variable_instance_get_names(global);
        array_sort(tm_names, true);
        instance_deactivate_all(true);
    } else {
        instance_activate_all();
    }
}

// frozen globals: the game cannot change them
var _k = ds_map_find_first(tm_frozen);
while (!is_undefined(_k)) {
    variable_global_set(_k, tm_frozen[? _k]);
    _k = ds_map_find_next(tm_frozen, _k);
}
if (!tm_open) exit;

if (keyboard_check_pressed(vk_tab)) { tm_tab = (tm_tab + 1) mod 3; tm_sel = 0; tm_top = 0; tm_msg = ""; }
var _n = 3;
if (tm_tab == 0) _n = array_length(tm_names);
if (tm_tab == 1) _n = array_length(tm_rooms);
if (keyboard_check_pressed(vk_down)) tm_sel = min(tm_sel + 1, _n - 1);
if (keyboard_check_pressed(vk_up)) tm_sel = max(tm_sel - 1, 0);
if (keyboard_check_pressed(vk_pagedown)) tm_sel = min(tm_sel + 15, _n - 1);
if (keyboard_check_pressed(vk_pageup)) tm_sel = max(tm_sel - 15, 0);
tm_sel = max(tm_sel, 0);
if (tm_sel < tm_top) tm_top = tm_sel;
if (tm_sel >= tm_top + 22) tm_top = tm_sel - 21;
var _mul = 1;
if (keyboard_check(vk_shift)) _mul = 10;

if (tm_tab == 0 && _n > 0) {
    var _nm = tm_names[tm_sel];
    var _v = variable_global_get(_nm);
    if (is_bool(_v)) {
        if (keyboard_check_pressed(vk_enter) || keyboard_check_pressed(vk_left) || keyboard_check_pressed(vk_right))
            variable_global_set(_nm, !_v);
    } else if (is_real(_v) || is_numeric(_v)) {
        if (keyboard_check_pressed(vk_right)) variable_global_set(_nm, _v + tm_step * _mul);
        if (keyboard_check_pressed(vk_left)) variable_global_set(_nm, _v - tm_step * _mul);
        if (keyboard_check_pressed(vk_enter)) {
            var _s = get_string("Value of " + _nm, string(_v));
            if (_s != "") variable_global_set(_nm, real(_s));
        }
    } else if (is_string(_v)) {
        if (keyboard_check_pressed(vk_enter)) variable_global_set(_nm, get_string("Value of " + _nm, _v));
    }
    if (keyboard_check_pressed(ord("F"))) {
        if (ds_map_exists(tm_frozen, _nm)) ds_map_delete(tm_frozen, _nm);
        else tm_frozen[? _nm] = variable_global_get(_nm);
    } else if (ds_map_exists(tm_frozen, _nm)) {
        tm_frozen[? _nm] = variable_global_get(_nm);   // edit of a frozen value = new held value
    }
    if (keyboard_check_pressed(ord("1"))) tm_step = 1;
    if (keyboard_check_pressed(ord("2"))) tm_step = 10;
    if (keyboard_check_pressed(ord("3"))) tm_step = 100;
}

if (tm_tab == 1 && _n > 0 && keyboard_check_pressed(vk_enter)) {
    tm_open = false;
    instance_activate_all();
    room_goto(tm_rooms[tm_sel]);
}

if (tm_tab == 2) {
    if (tm_sel == 0) {
        if (keyboard_check_pressed(vk_right)) tm_speed_i = min(tm_speed_i + 1, array_length(tm_speeds) - 1);
        if (keyboard_check_pressed(vk_left)) tm_speed_i = max(tm_speed_i - 1, 0);
        game_set_speed(tm_base_fps * tm_speeds[tm_speed_i], gamespeed_fps);
    }
    if (tm_sel == 1 && keyboard_check_pressed(vk_enter) && room_exists(room_next(room))) {
        tm_open = false; instance_activate_all(); room_goto_next();
    }
    if (tm_sel == 2 && keyboard_check_pressed(vk_enter) && room_exists(room_previous(room))) {
        tm_open = false; instance_activate_all(); room_goto_previous();
    }
}
