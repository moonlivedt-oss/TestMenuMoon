// TEST MENU (TestMenuMoon) - Create. GameMaker 2.3+, GML; text in English:
// the default GameMaker font has no Cyrillic.
if (instance_number(object_index) > 1) { instance_destroy(); exit; }
tm_open = false;
tm_tab = 0;            // 0 globals, 1 rooms, 2 game
tm_sel = 0;
tm_top = 0;
tm_step = 1;
tm_names = [];
tm_frozen = ds_map_create();
tm_speeds = [0.25, 0.5, 1, 2, 3, 5];
tm_speed_i = 2;
tm_base_fps = game_get_speed(gamespeed_fps);
tm_msg = "";
tm_rooms = [];
var _r = 0;
while (room_exists(_r)) { array_push(tm_rooms, _r); _r += 1; }
