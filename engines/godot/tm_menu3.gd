extends CanvasLayer
# Тест-меню для Godot 3 (GDScript 1). Ставится тем же override.cfg, что и меню Godot 4
# (engines/godot/inject.py сам выбирает файл по версии .pck), но проще: переменные
# глобальных объектов (автозагрузок), правка и заморозка, темп игры, шаг кадра, FPS,
# полёт и «сквозь стены». Shift+T / F9 — открыть, Esc — закрыть; пока меню открыто,
# игра на паузе.

const ACCENT = Color("#38e0c8")
const BG = Color("#10141d")
const BG2 = Color("#1e2432")
const TXT = Color("#e7ebf2")
const DIM = Color("#8b93a3")
const WARN = Color("#f0b429")

var root
var body
var tab = "vars"
var opened = false
var prev_paused = false
var frozen = {}            # путь -> удерживаемое значение
var filter_text = ""
var step = 1
var speed = 1.0
var show_fps = false
var fps_label = null
var speed_label = null
var fly_on = false
var noclip_on = false
var fly_node = null
var saved_layers = {}
var edit_path = ""
var font_data = null
var filter_edit = null
var fonts = {}


func _ready():
	layer = 120
	pause_mode = Node.PAUSE_MODE_PROCESS
	var f = File.new()
	for p in ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]:
		if f.file_exists(p):
			font_data = DynamicFontData.new()
			font_data.font_path = p
			break
	_build_ui()
	root.visible = false


# ------------------------------------------------------------------ данные
func _autoloads():
	var out = []
	for p in ProjectSettings.get_property_list():
		var n = p["name"]
		if not n.begins_with("autoload/"):
			continue
		var name = n.substr(9, n.length() - 9)
		if name == "TestMenu" or not has_node("/root/" + name):
			continue
		var node = get_node("/root/" + name)
		if node.get_script() != null:
			out.append([name, node])
	return out


func _scalar(v):
	var t = typeof(v)
	return t == TYPE_INT or t == TYPE_REAL or t == TYPE_BOOL or t == TYPE_STRING


func _entries():
	# [[путь, значение]]: переменные скриптов автозагрузок (и словари на один уровень)
	var out = []
	for a in _autoloads():
		var node = a[1]
		for p in node.get_script().get_script_property_list():
			if not (p["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE):
				continue
			var v = node.get(p["name"])
			var path = a[0] + "." + p["name"]
			if _scalar(v):
				out.append([path, v])
			elif typeof(v) == TYPE_DICTIONARY and v.size() <= 200:
				for k in v:
					if _scalar(v[k]):
						out.append([path + "." + str(k), v[k]])
	return out


func get_value(path):
	var parts = path.split(".")
	if not has_node("/root/" + parts[0]):
		return null
	var v = get_node("/root/" + parts[0]).get(parts[1])
	if parts.size() > 2 and typeof(v) == TYPE_DICTIONARY:
		if v.has(parts[2]):
			return v[parts[2]]
		if parts[2].is_valid_integer() and v.has(int(parts[2])):
			return v[int(parts[2])]
		return null
	return v


func set_value(path, value):
	var parts = path.split(".")
	if not has_node("/root/" + parts[0]):
		return
	var node = get_node("/root/" + parts[0])
	var cur = node.get(parts[1])
	if parts.size() > 2 and typeof(cur) == TYPE_DICTIONARY:
		var key = parts[2]
		if not cur.has(key) and key.is_valid_integer():
			key = int(key)
		cur[key] = _like(cur.get(key), value)
		return
	value = _like(cur, value)
	if node.has_method("set_" + parts[1]):
		node.call("set_" + parts[1], value)
	else:
		node.set(parts[1], value)


func _like(cur, value):
	# новое значение — того же типа, что было (ввод приходит строкой)
	match typeof(cur):
		TYPE_INT:
			return int(float(str(value)))
		TYPE_REAL:
			return float(str(value))
		TYPE_BOOL:
			return value == true or str(value).to_lower() in ["true", "1", "да"]
		TYPE_STRING:
			return str(value)
	return value


# ------------------------------------------------------------------ окно
func _font(size):
	if font_data == null:
		return null
	if not fonts.has(size):
		var f = DynamicFont.new()
		f.font_data = font_data
		f.size = size
		fonts[size] = f
	return fonts[size]


func _style(c, r, border = Color(0, 0, 0, 0), bw = 0):
	var sb = StyleBoxFlat.new()
	sb.bg_color = c
	sb.set_corner_radius_all(r)
	sb.border_color = border
	sb.set_border_width_all(bw)
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 5
	sb.content_margin_bottom = 5
	return sb


func _label(text, size = 17, color = TXT):
	var l = Label.new()
	l.text = text
	l.add_color_override("font_color", color)
	var f = _font(size)
	if f:
		l.add_font_override("font", f)
	return l


func _button(text, method, binds = [], tip = ""):
	var b = Button.new()
	b.text = text
	b.hint_tooltip = tip
	b.focus_mode = Control.FOCUS_NONE
	var f = _font(16)
	if f:
		b.add_font_override("font", f)
	b.add_stylebox_override("normal", _style(BG2, 8))
	b.add_stylebox_override("hover", _style(BG2, 8, ACCENT, 1))
	b.add_stylebox_override("pressed", _style(ACCENT, 8))
	b.add_color_override("font_color", TXT)
	b.connect("pressed", self, method, binds)
	return b


func _row():
	var r = HBoxContainer.new()
	r.add_constant_override("separation", 8)
	body.add_child(r)
	return r


func _build_ui():
	root = Control.new()
	root.anchor_right = 1
	root.anchor_bottom = 1
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(root)
	var shade = ColorRect.new()
	shade.color = Color(0, 0, 0, 0.55)
	shade.anchor_right = 1
	shade.anchor_bottom = 1
	root.add_child(shade)
	var panel = PanelContainer.new()
	var sb = _style(BG, 14, ACCENT, 2)
	sb.content_margin_left = 18
	sb.content_margin_right = 18
	sb.content_margin_top = 14
	sb.content_margin_bottom = 14
	panel.add_stylebox_override("panel", sb)
	panel.anchor_left = 0.08
	panel.anchor_top = 0.06
	panel.anchor_right = 0.92
	panel.anchor_bottom = 0.94
	root.add_child(panel)
	var v = VBoxContainer.new()
	v.add_constant_override("separation", 10)
	panel.add_child(v)
	var head = HBoxContainer.new()
	head.add_constant_override("separation", 8)
	v.add_child(head)
	head.add_child(_label("TEST MENU  |  Godot " + str(Engine.get_version_info()["string"]), 20, ACCENT))
	var gap = Control.new()
	gap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(gap)
	head.add_child(_button("Переменные", "_set_tab", ["vars"]))
	head.add_child(_button("Игра", "_set_tab", ["game"]))
	head.add_child(_button("X", "toggle", [false], "Закрыть (Esc)"))
	var sc = ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.scroll_horizontal_enabled = false
	v.add_child(sc)
	body = VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_constant_override("separation", 6)
	sc.add_child(body)
	v.add_child(_label("Shift+T / F9 — меню    Esc — закрыть    пока меню открыто, игра на паузе", 14, DIM))


func toggle(on):
	if on == opened:
		return
	opened = on
	root.visible = on
	if on:
		prev_paused = get_tree().paused
		get_tree().paused = true
		refresh()
	else:
		get_tree().paused = prev_paused
		edit_path = ""


func _set_tab(t):
	tab = t
	edit_path = ""
	refresh()


func refresh():
	for c in body.get_children():
		body.remove_child(c)
		c.queue_free()
	if tab == "game":
		_tab_game()
	else:
		_tab_vars()


# ------------------------------------------------------------------ «Переменные»
func _tab_vars():
	var top = _row()
	top.add_child(_label("шаг:", 16, DIM))
	for s in [1, 10, 100]:
		var b = _button("×" + str(s), "_on_step", [s])
		if s == step:
			b.add_color_override("font_color", ACCENT)
		top.add_child(b)
	var fl = LineEdit.new()
	fl.placeholder_text = "фильтр по имени…"
	fl.text = filter_text
	fl.rect_min_size = Vector2(260, 0)
	fl.connect("text_changed", self, "_on_filter")
	top.add_child(fl)
	filter_edit = fl
	if edit_path != "":
		var er = _row()
		er.add_child(_label(edit_path + " =", 16, ACCENT))
		var le = LineEdit.new()
		le.text = str(get_value(edit_path))
		le.rect_min_size = Vector2(320, 0)
		le.connect("text_entered", self, "_on_edit_done")
		er.add_child(le)
		er.add_child(_button("отмена", "_on_edit_cancel"))
		le.call_deferred("grab_focus")
	var es = _entries()
	if es.empty():
		body.add_child(_label("У игры нет глобальных объектов (автозагрузок) со своими переменными.", 16, DIM))
		return
	var shown = 0
	for e in es:
		var path = e[0]
		if filter_text != "" and path.to_lower().find(filter_text.to_lower()) < 0:
			continue
		shown += 1
		if shown > 400:
			body.add_child(_label("Показаны первые 400 — сузь фильтром.", 15, DIM))
			break
		_var_row(path, e[1])


func _var_row(path, v):
	var r = _row()
	var n = _label(path, 16)
	n.rect_min_size = Vector2(380, 0)
	n.clip_text = true
	r.add_child(n)
	var val = _label(str(v), 16, WARN if frozen.has(path) else ACCENT)
	val.rect_min_size = Vector2(150, 0)
	r.add_child(val)
	var t = typeof(v)
	if t == TYPE_INT or t == TYPE_REAL:
		r.add_child(_button("−", "_on_add", [path, -1]))
		r.add_child(_button("+", "_on_add", [path, 1]))
	if t == TYPE_BOOL:
		r.add_child(_button("вкл/выкл", "_on_flip", [path]))
	else:
		r.add_child(_button("ввод", "_on_edit", [path]))
	r.add_child(_button("снять" if frozen.has(path) else "стоп", "_on_freeze", [path], "Заморозить: игра не сможет изменить значение"))


func _on_step(s):
	step = s
	refresh()


func _on_filter(t):
	filter_text = t
	call_deferred("_refilter")


func _refilter():
	# список пересобирается, а поле фильтра — новое: вернуть ему фокус и курсор
	refresh()
	if filter_edit != null:
		filter_edit.grab_focus()
		filter_edit.caret_position = filter_text.length()


func _on_add(path, sign):
	_put(path, get_value(path) + sign * step)


func _on_flip(path):
	_put(path, not get_value(path))


func _on_edit(path):
	edit_path = path
	refresh()


func _on_edit_done(text):
	if edit_path != "":
		_put(edit_path, text)
	edit_path = ""
	refresh()


func _on_edit_cancel():
	edit_path = ""
	refresh()


func _put(path, value):
	set_value(path, value)
	if frozen.has(path):
		frozen[path] = get_value(path)
	refresh()


func _on_freeze(path):
	if frozen.has(path):
		frozen.erase(path)
	else:
		frozen[path] = get_value(path)
	refresh()


# ------------------------------------------------------------------ «Игра»
func _tab_game():
	body.add_child(_label("Скорость игры", 18, ACCENT))
	var r = _row()
	for s in [[0.0, "пауза"], [0.25, "×0.25"], [0.5, "×0.5"], [1.0, "×1"], [2.0, "×2"], [3.0, "×3"], [5.0, "×5"]]:
		var b = _button(s[1], "_on_speed", [s[0]])
		if is_equal_approx(speed, s[0]):
			b.add_color_override("font_color", ACCENT)
		r.add_child(b)
	body.add_child(_label("Темп включится, когда закроешь меню (пока меню открыто, игра на паузе).", 15, DIM))
	var rs = _row()
	rs.add_child(_button("Шаг кадра", "_frame_step", [], "Игра на паузе продвигается ровно на один кадр"))
	rs.add_child(_button("FPS в углу: вкл" if show_fps else "FPS в углу: выкл", "_on_fps"))
	rs.add_child(_label("сейчас %d кадров/с" % Engine.get_frames_per_second(), 15, DIM))
	body.add_child(_label("Игрок", 18, ACCENT))
	var p = _player()
	if p == null:
		body.add_child(_label("Игрок не найден: нет узла в группе player и узла Player / Hero в текущей сцене.", 15, DIM))
		return
	body.add_child(_label("%s: %s" % [p.name, str(p.global_transform.origin if p is Spatial else p.global_position)], 16))
	var rf = _row()
	rf.add_child(_button("Полёт: вкл" if fly_on else "Полёт: выкл", "_on_fly", [], "Игра не двигает героя; стрелки — движение, Shift — быстрее, в 3D PageUp / PageDown — высота"))
	rf.add_child(_button("Сквозь стены: вкл" if noclip_on else "Сквозь стены: выкл", "_on_noclip", [], "Слои столкновений героя обнуляются"))


func _on_speed(k):
	_set_speed(k)
	refresh()


func _on_fps():
	show_fps = not show_fps
	if fps_label == null:
		fps_label = _label("", 16, ACCENT)
		fps_label.rect_position = Vector2(12, 10)
		add_child(fps_label)
	fps_label.visible = show_fps
	refresh()


func _set_speed(k):
	speed = k
	Engine.time_scale = k
	if speed_label == null:
		speed_label = _label("", 18, ACCENT)
		speed_label.anchor_left = 1
		speed_label.anchor_right = 1
		speed_label.margin_left = -140
		speed_label.margin_top = 10
		add_child(speed_label)
	speed_label.text = "ПАУЗА" if k == 0.0 else "×" + str(k)
	speed_label.visible = k != 1.0


func _frame_step():
	# один кадр с темпом 1 и без паузы дерева, затем снова пауза (idle_frame — до кадра)
	_set_speed(0.0)
	var was = get_tree().paused
	get_tree().paused = false
	Engine.time_scale = 1.0
	yield(get_tree(), "idle_frame")
	yield(get_tree(), "idle_frame")
	Engine.time_scale = speed
	get_tree().paused = was


func _player():
	var t = get_tree()
	for g in ["player", "Player"]:
		for n in t.get_nodes_in_group(g):
			if n is Node2D or n is Spatial:
				return n
	var cs = t.current_scene
	if cs:
		for nm in ["Player", "player", "Hero", "hero", "PlayerCharacter"]:
			var n = cs.find_node(nm, true, false)
			if n is Node2D or n is Spatial:
				return n
	return null


func _on_fly():
	var p = _player()
	if p == null:
		return
	if fly_on and is_instance_valid(fly_node):
		fly_node.set_physics_process(true)
	fly_on = not fly_on
	fly_node = p if fly_on else null
	if fly_on:
		p.set_physics_process(false)
	refresh()


func _on_noclip():
	var p = _player()
	if p == null or not (p is CollisionObject2D or p is CollisionObject):
		return
	noclip_on = not noclip_on
	if noclip_on:
		saved_layers[p] = [p.collision_layer, p.collision_mask]
		p.collision_layer = 0
		p.collision_mask = 0
	elif saved_layers.has(p):
		p.collision_layer = saved_layers[p][0]
		p.collision_mask = saved_layers[p][1]
		saved_layers.erase(p)
	refresh()


# ------------------------------------------------------------------ каждый кадр
func _process(delta):
	for p in frozen:
		if get_value(p) != frozen[p]:
			set_value(p, frozen[p])
	if show_fps and fps_label != null:
		fps_label.text = "FPS %d" % Engine.get_frames_per_second()
	if fly_on and is_instance_valid(fly_node) and not opened:
		var dt = delta / Engine.time_scale if Engine.time_scale > 0.0 else 1.0 / 60.0
		var d = Vector2(Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left"),
				Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up"))
		var fast = Input.is_key_pressed(KEY_SHIFT)
		if fly_node is Node2D:
			fly_node.global_position += d * (900.0 if fast else 320.0) * dt
		else:
			var up = (1.0 if Input.is_key_pressed(KEY_PAGEUP) else 0.0) - (1.0 if Input.is_key_pressed(KEY_PAGEDOWN) else 0.0)
			fly_node.global_translate(Vector3(d.x, up, d.y) * (18.0 if fast else 6.0) * dt)


func _input(event):
	if event is InputEventKey and event.pressed and not event.echo:
		if (event.scancode == KEY_T and event.shift) or event.scancode == KEY_F9:
			var f = root.get_focus_owner()
			if not (opened and f is LineEdit):
				toggle(not opened)
				get_tree().set_input_as_handled()
				return
		if opened and event.scancode == KEY_ESCAPE:
			toggle(false)
			get_tree().set_input_as_handled()
