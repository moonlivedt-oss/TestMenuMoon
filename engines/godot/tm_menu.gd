extends CanvasLayer
## TestMenuMoon для игр на Godot 4 (4.0 – 4.7). Подключается автозагрузкой из override.cfg
## рядом с .exe игры (engines/godot/inject.py), саму игру и .pck не меняет.
##
## Всё находит само: переменные глобальных объектов игры (autoload), переменные Dialogic,
## сцены Dialogic (.dtl) с их условиями. Shift+T / F9 — открыть, Esc — закрыть. Пока меню
## открыто, игра на паузе (клики и клавиши в неё не уходят).

const TABS = [["vars", "Переменные", "stats"], ["unlock", "Открытое", "key"],
		["story", "Сюжет", "story"], ["game", "Игра", "stopwatch"], ["scan", "Поиск", "scanner"],
		["help", "Справка", "question"]]
const ACCENT = Color("#38e0c8")
const BG = Color("#10141d")
const BG2 = Color("#161b26")
const BG3 = Color("#1e2432")
const TXT = Color("#e7ebf2")
const DIM = Color("#8b93a3")
const BAD = Color("#ff6b6b")
const GOOD = Color("#5ad469")
const SKIP_METHODS = ["save", "load", "delete", "create", "import", "export", "encode", "decode", "sync", "update", "deferred", "level",
		"get", "is", "has", "set", "on", "print", "quit", "free", "queue", "emit", "connect", "notification"]

var base_dir = ""
var words = {}
var generic = {}
var inflect = []
var stems = {}

var ui_root: Control
var win: PanelContainer
var body: VBoxContainer
var tab_buttons = {}
var tip_label: Label
var font: Font
var icons = {}

var tab = "vars"
var opened = false
var prev_paused = false
var prev_dialogic_paused = false
var step = 1
var filter_text = ""
var frozen = {}            # путь -> значение
var show_service = false
var confirm_key = ""
var scan_old = {}
var scan_cands = []
var scan_msg = "Нажми «Снимок», поиграй и возвращайся сужать."
var story_filter = ""
var speed = 1.0            # темп игры (Engine.time_scale) из вкладки «Игра»
var speed_label: Label     # значок темпа в углу, пока он не ×1
var show_fps = false       # счётчик FPS в углу экрана
var fps_label: Label
var places = []            # точки телепорта игрока: {"name", "scene", "pos"}

var _usage = null           # смысл переменных по сценам Dialogic (кэш)
var _chars = null           # персонажи Dialogic: ключ -> имя
var _timelines = null


func _ready() -> void:
	layer = 120
	process_mode = Node.PROCESS_MODE_ALWAYS
	base_dir = get_script().resource_path.get_base_dir()
	_load_words()
	font = SystemFont.new()
	font.font_names = PackedStringArray(["Segoe UI", "Arial", "DejaVu Sans", "Noto Sans"])
	_build_ui()
	ui_root.visible = false
	_profile_load()
	var st = OS.get_environment("TM_SELFTEST")
	if st != "":
		_selftest(st)


# ------------------------------------------------------------------ данные
func _load_words() -> void:
	var f = FileAccess.open(base_dir.path_join("tm_words.json"), FileAccess.READ)
	if f == null:
		return
	var d = JSON.parse_string(f.get_as_text())
	if typeof(d) != TYPE_DICTIONARY:
		return
	words = d.get("words", {})
	for g in d.get("generic", []):
		generic[g] = true
	inflect = d.get("inflect", [])
	for s in d.get("stems", []):
		stems[s] = true


func _autoloads() -> Array:
	# [[имя, узел]] глобальных объектов игры со своими переменными (без Dialogic и меню)
	var out = []
	for p in ProjectSettings.get_property_list():
		var n: String = p["name"]
		if not n.begins_with("autoload/"):
			continue
		var name = n.substr(9)
		if name == "Dialogic" or name == "TestMenu":
			continue
		var node = get_node_or_null("/root/" + name)
		if node == null or node.get_script() == null:
			continue
		out.append([name, node])
	return out


func _script_vars(node: Object) -> Array:
	var out = []
	var sc = node.get_script()
	if sc == null:
		return out
	for p in sc.get_script_property_list():
		if p["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE:
			out.append(p["name"])
	return out


func _dialogic() -> Node:
	return get_node_or_null("/root/Dialogic")


func _dialogic_vars() -> Dictionary:
	# плоский словарь «Папка.имя» -> значение из состояния Dialogic
	var out = {}
	var d = _dialogic()
	if d == null:
		return out
	var info = d.get("current_state_info")
	if typeof(info) != TYPE_DICTIONARY:
		return out
	_flatten(info.get("variables", {}), "", out)
	return out


func _flatten(v, prefix: String, out: Dictionary) -> void:
	if typeof(v) == TYPE_DICTIONARY:
		for k in v:
			_flatten(v[k], (prefix + "." + str(k)) if prefix != "" else str(k), out)
	elif typeof(v) in [TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_STRING, TYPE_STRING_NAME]:
		out[prefix] = v


class Entry:
	var path = ""          # «Stats.money», «Progress.character_progress.boss», «dlg:State.day»
	var label = ""         # исходное имя для подписи
	var kind = "num"       # num / flag / str
	var source = "auto"    # auto (глобальный объект) / dlg (Dialogic)


func _entries() -> Array:
	# все значения игры: переменные autoload (и элементы их словарей) + Dialogic
	var out = []
	var seen = {}
	for al in _autoloads():
		var aname: String = al[0]
		var node: Node = al[1]
		for prop in _script_vars(node):
			var v = node.get(prop)
			var path = aname + "." + prop
			if typeof(v) == TYPE_DICTIONARY:
				for k in v:
					if typeof(v[k]) in [TYPE_INT, TYPE_FLOAT, TYPE_BOOL]:
						out.append(_entry(path + "." + str(k), prop + "." + str(k), v[k], "auto"))
			elif typeof(v) in [TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_STRING]:
				if typeof(v) == TYPE_STRING and v.length() > 60:
					continue
				out.append(_entry(path, prop, v, "auto"))
				seen[path] = true
	var dv = _dialogic_vars()
	for k in dv:
		if seen.has(k) or _mirror_of(k) != "":
			continue        # зеркало переменной глобального объекта — правим оригинал
		out.append(_entry("dlg:" + k, k, dv[k], "dlg"))
	return out


func _entry(path: String, label: String, v, source: String) -> Entry:
	var e = Entry.new()
	e.path = path
	e.label = label
	e.source = source
	e.kind = "flag" if typeof(v) == TYPE_BOOL else ("str" if typeof(v) in [TYPE_STRING, TYPE_STRING_NAME] else "num")
	return e


func _mirror_of(dpath: String) -> String:
	# переменная Dialogic, которая лишь зеркалит значение глобального объекта:
	#   «Progress.character_boss» -> Progress.character_progress["boss"]  (папка = объект)
	#   «State.money»             -> GameState.state["money"]             (папка = словарь)
	#   «Progress.unlocked_X»     -> массив Progress.unlocked             (вкладка «Открытое»)
	var parts = dpath.split(".")
	if parts.size() != 2:
		return ""
	var node = get_node_or_null("/root/" + parts[0])
	if node != null and node.get_script() != null:
		for prop in _script_vars(node):
			var v = node.get(prop)
			if typeof(v) == TYPE_ARRAY and parts[1].begins_with(prop + "_"):
				return parts[0] + "." + prop
			if typeof(v) != TYPE_DICTIONARY:
				continue
			var head: String = prop.split("_")[0]
			for k in v:
				if parts[1] == str(k) or parts[1] == prop + "_" + str(k) or parts[1] == head + "_" + str(k):
					return parts[0] + "." + prop + "." + str(k)
	for al in _autoloads():
		for prop in _script_vars(al[1]):
			var v = al[1].get(prop)
			if typeof(v) == TYPE_DICTIONARY and prop.to_lower() == parts[0].to_lower() and v.has(parts[1]):
				return al[0] + "." + prop + "." + parts[1]
	return ""


func get_value(path: String):
	if path.begins_with("dlg:"):
		return _dialogic_vars().get(path.substr(4))
	var parts = path.split(".")
	var node = get_node_or_null("/root/" + parts[0])
	if node == null:
		return null
	var v = node.get(parts[1])
	if parts.size() > 2 and typeof(v) == TYPE_DICTIONARY:
		return v.get(parts[2], v.get(int(parts[2]) if parts[2].is_valid_int() else parts[2]))
	return v


func set_value(path: String, value) -> void:
	var d = _dialogic()
	if path.begins_with("dlg:"):
		if d and d.get("VAR") and d.VAR.has_method("set_variable"):
			d.VAR.set_variable(path.substr(4), value)
		return
	var parts = path.split(".")
	var node = get_node_or_null("/root/" + parts[0])
	if node == null:
		return
	var cur = node.get(parts[1])
	if parts.size() > 2 and typeof(cur) == TYPE_DICTIONARY:
		var key = parts[2]
		if not cur.has(key) and key.is_valid_int():
			key = int(key)
		cur[key] = value
		_sync_dialogic(parts[0], [parts[1] + "_" + parts[2], parts[1].split("_")[0] + "_" + parts[2], parts[2]], value)
		_sync_dialogic(parts[1].capitalize().replace(" ", ""), [parts[2]], value)
		if node.has_method("sync_to_dialogic"):
			node.call("sync_to_dialogic")
		return
	if typeof(cur) == TYPE_INT:
		value = int(value)
	elif typeof(cur) == TYPE_FLOAT:
		value = float(value)
	# сеттер игры (set_money) — он же обновит переменные диалогов
	if node.has_method("set_" + parts[1]):
		node.call("set_" + parts[1], value)
	else:
		node.set(parts[1], value)
	_sync_dialogic(parts[0], [parts[1]], value)
	if node.has_method("sync_to_dialogic"):
		node.call("sync_to_dialogic")


func _sync_dialogic(folder: String, names: Array, value) -> void:
	var dv = _dialogic_vars()
	var d = _dialogic()
	if d == null or not d.get("VAR") or not d.VAR.has_method("set_variable"):
		return
	for n in names:
		if dv.has(folder + "." + n):
			d.VAR.set_variable(folder + "." + n, value)


# ------------------------------------------------------------------ имена и смысл
func _tokens(text: String) -> Array:
	var out = []
	var rx = RegEx.new()
	rx.compile("([a-z0-9])([A-Z])")
	var s = rx.sub(text, "$1_$2", true).to_lower()
	var sp = RegEx.new()
	sp.compile("[^0-9a-z\\x{00c0}-\\x{ffff}]+")
	for t in sp.sub(s, " ", true).split(" ", false):
		if not t.is_valid_int():
			out.append(t)
	return out


func _word(tok: String) -> String:
	if words.has(tok):
		return words[tok]
	var best = ""
	for k in words:
		if k.length() >= 4 and tok.begins_with(k) and k.length() > best.length():
			if stems.has(k) or inflect.has(tok.substr(k.length())):
				best = k
	return words[best] if best != "" else ""


func characters() -> Dictionary:
	# персонажи Dialogic: «mom» -> отображаемое имя (с подстановкой {MomName})
	if _chars != null:
		return _chars
	_chars = {}
	var dir = DirAccess.open("res://dialogic/characters")
	if dir == null:
		return _chars
	for f in dir.get_files():
		f = f.trim_suffix(".remap")
		if not f.ends_with(".dch"):
			continue
		var key = f.get_basename().to_lower()
		var name = key.capitalize()
		var res = load("res://dialogic/characters/" + f)
		if res and res.get("display_name"):
			name = str(res.display_name)
		if name.contains("{"):
			var rx = RegEx.new()
			rx.compile("\\{([\\w\\.]+)\\}")
			var m = rx.search(name)
			var d = _dialogic()
			if m and d and d.get("VAR") and d.VAR.has_method("get_variable"):
				var v = d.VAR.get_variable(m.get_string(1), "", true)
				if str(v) != "":
					name = rx.sub(name, str(v))
		_chars[key] = name
	return _chars


func nice(e: Entry) -> String:
	var label = e.label
	var chars = characters()
	var toks = _tokens(label)
	var who = ""
	# составной ключ персонажа (sons_friend, gym_buddy) — по склейке соседних токенов
	for n in [3, 2, 1]:
		for i in range(toks.size() - n + 1):
			var key = "_".join(toks.slice(i, i + n))
			if chars.has(key) and who == "":
				who = chars[key]
				toks = toks.slice(0, i) + toks.slice(i + n)
	var out = []
	var hit = false
	for t in toks:
		if generic.has(t):
			continue
		var w = _word(t)
		hit = hit or w != ""
		out.append(w if w != "" else t)
	var title = " ".join(out)
	if title == "":
		title = label
	title = title.substr(0, 1).to_upper() + title.substr(1)
	return (who + " | " + title) if who != "" else title


func _dtl_files() -> Array:
	if _timelines != null:
		return _timelines
	_timelines = []
	_collect_dtl("res://dialogic", _timelines)
	_timelines.sort()
	return _timelines


func _collect_dtl(path: String, out: Array) -> void:
	var dir = DirAccess.open(path)
	if dir == null:
		return
	for f in dir.get_files():
		f = f.trim_suffix(".remap")
		if f.ends_with(".dtl"):
			out.append(path.path_join(f))
	for sub in dir.get_directories():
		_collect_dtl(path.path_join(sub), out)


func usage() -> Dictionary:
	# по сценам Dialogic: {«Папка.имя»: {"chk": [[оп, число, сцена]], "set": [[текст, сцена]]}}
	if _usage != null:
		return _usage
	_usage = {}
	var cmp = RegEx.new()
	cmp.compile("\\{([\\w\\.]+)\\}\\s*(>=|<=|==|!=|>|<)\\s*(-?\\d+(?:\\.\\d+)?)")
	var bare = RegEx.new()
	bare.compile("(?:if|elif|\\[if)\\s+!?\\{([\\w\\.]+)\\}")
	var setr = RegEx.new()
	setr.compile("set\\s+\\{([\\w\\.]+)\\}\\s*(\\+=|-=|=)\\s*([^\\n\\]]+)")
	for path in _dtl_files():
		var f = FileAccess.open(path, FileAccess.READ)
		if f == null:
			continue
		var text = f.get_as_text()
		var scene: String = path.get_file().get_basename()
		for m in cmp.search_all(text):
			_use(m.get_string(1))["chk"].append([m.get_string(2), float(m.get_string(3)), scene])
		for m in bare.search_all(text):
			_use(m.get_string(1))["chk"].append(["", 0.0, scene])
		for m in setr.search_all(text):
			_use(m.get_string(1))["set"].append([m.get_string(2) + " " + m.get_string(3).strip_edges().left(14), scene])
	return _usage


func _use(name: String) -> Dictionary:
	if not _usage.has(name):
		_usage[name] = {"chk": [], "set": []}
	return _usage[name]


func _usage_key(e: Entry) -> String:
	if e.source == "dlg":
		return e.path.substr(4)
	var parts = e.path.split(".")
	if parts.size() == 3:
		# словарь: ищем, как его зеркало называется в Dialogic
		for cand in [parts[1] + "_" + parts[2], parts[1].split("_")[0] + "_" + parts[2], parts[2]]:
			if usage().has(parts[0] + "." + cand):
				return parts[0] + "." + cand
		var folder: String = parts[1].capitalize().replace(" ", "")
		if usage().has(folder + "." + parts[2]):
			return folder + "." + parts[2]
	return parts[0] + "." + parts[1]


func meaning(e: Entry) -> String:
	var u = usage().get(_usage_key(e))
	if u == null:
		return "в сценах не проверяется"
	var parts = []
	var need = []
	for c in u["chk"]:
		if c[0] != "":
			need.append(c)
	need.sort_custom(func(a, b): return a[1] < b[1])
	if need.size() > 0:
		var c = need[0]
		parts.append("нужно %s %s → %s" % [c[0].replace(">=", "≥").replace("<=", "≤"), _num(c[1]), c[2]])
	elif u["chk"].size() > 0:
		parts.append("проверяется: " + u["chk"][0][2])
	if u["set"].size() > 0:
		parts.append("меняется: %s (%s)" % [u["set"][0][0], u["set"][0][1]])
	var scenes = {}
	for c in u["chk"]:
		scenes[c[2]] = true
	if scenes.size() > 1:
		parts.append("сцен: %d" % scenes.size())
	return "; ".join(parts)


func thresholds(e: Entry) -> Array:
	var u = usage().get(_usage_key(e))
	var out = []
	if u == null:
		return out
	for c in u["chk"]:
		var n: float = c[1]
		if c[0] in [">=", "=="] and not out.has(n):
			out.append(n)
		elif c[0] == ">" and not out.has(n + 1):
			out.append(n + 1)
	out.sort()
	return out


func _num(x: float) -> String:
	return str(int(x)) if x == floor(x) else str(x)


func group_of(e: Entry, name: String) -> String:
	if name.contains(" | "):
		return name.split(" | ")[0]
	var toks = _tokens(e.label)
	var used = usage().has(_usage_key(e))
	for t in toks:
		if t in ["money", "cash", "gold", "coin", "coins", "dollar", "credit"]:
			return "Деньги"
	for t in toks:
		if t in ["day", "days", "daytime", "week", "time", "hour", "month", "year"]:
			return "Время"
	if e.kind == "num" and (used or e.source == "auto"):
		return "Статы"
	if e.kind == "flag" and used:
		return "Сюжетные флаги"
	if e.kind == "str":
		return "Строки"
	return "Служебное"


# ------------------------------------------------------------------ интерфейс
func _build_ui() -> void:
	ui_root = Control.new()
	ui_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	ui_root.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(ui_root)
	var shade = ColorRect.new()
	shade.color = Color(0.02, 0.03, 0.05, 0.8)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_STOP
	ui_root.add_child(shade)

	win = PanelContainer.new()
	win.add_theme_stylebox_override("panel", _box(BG, 16, ACCENT, 2))
	ui_root.add_child(win)
	var col = VBoxContainer.new()
	col.add_theme_constant_override("separation", 0)
	win.add_child(col)

	# шапка
	var head = PanelContainer.new()
	var hb = _box(ACCENT, 0)
	hb.corner_radius_top_left = 14
	hb.corner_radius_top_right = 14
	hb.content_margin_left = 16
	hb.content_margin_right = 12
	hb.content_margin_top = 8
	hb.content_margin_bottom = 8
	head.add_theme_stylebox_override("panel", hb)
	col.add_child(head)
	var hrow = HBoxContainer.new()
	head.add_child(hrow)
	hrow.add_child(_icon("logo", 32))
	var title = _label("TEST MENU", 22, Color("#07110f"))
	hrow.add_child(title)
	var sub = _label("  " + str(ProjectSettings.get_setting("application/config/name", "")) + " | Godot " + Engine.get_version_info()["string"], 15, Color("#07110f99"))
	sub.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hrow.add_child(sub)
	var close = _button("Закрыть", func(): toggle(false))
	hrow.add_child(close)

	# вкладки
	var tabs = HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 4)
	var tabs_panel = PanelContainer.new()
	var tb = _box(BG2, 0)
	tb.content_margin_left = 8
	tb.content_margin_top = 6
	tb.content_margin_bottom = 6
	tabs_panel.add_theme_stylebox_override("panel", tb)
	tabs_panel.add_child(tabs)
	col.add_child(tabs_panel)
	for t in TABS:
		var b = _button(t[1], func(): _set_tab(t[0]), t[2])
		b.toggle_mode = true
		tab_buttons[t[0]] = b
		tabs.add_child(b)

	# содержимое
	var scroll = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var pad = MarginContainer.new()
	pad.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for side in ["left", "right", "top", "bottom"]:
		pad.add_theme_constant_override("margin_" + side, 18 if side in ["left", "right"] else 12)
	body = VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 6)
	pad.add_child(body)
	scroll.add_child(pad)
	col.add_child(scroll)

	# футер: подсказка
	var foot = PanelContainer.new()
	var fb = _box(Color("#0b0e14"), 0)
	fb.corner_radius_bottom_left = 14
	fb.corner_radius_bottom_right = 14
	fb.content_margin_left = 16
	fb.content_margin_top = 6
	fb.content_margin_bottom = 6
	foot.add_theme_stylebox_override("panel", fb)
	tip_label = _label("Shift+T / F9 — меню   |   Esc — закрыть   |   наведи на кнопку — подсказка", 14, DIM)
	foot.add_child(tip_label)
	col.add_child(foot)


func _layout() -> void:
	var vs = get_viewport().get_visible_rect().size
	var w: float = min(vs.x * 0.86, 1100.0 * vs.y / 1080.0 * 1.2)
	var h: float = vs.y * 0.84
	win.size = Vector2(w, h)
	win.position = (vs - win.size) / 2.0


func _box(c: Color, r: int, border := Color(0, 0, 0, 0), bw := 0) -> StyleBoxFlat:
	var s = StyleBoxFlat.new()
	s.bg_color = c
	s.set_corner_radius_all(r)
	if bw > 0:
		s.border_color = border
		s.set_border_width_all(bw)
	s.content_margin_left = 0
	return s


func _label(text: String, size := 17, color := TXT) -> Label:
	var l = Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return l


func _button(text: String, cb: Callable, ico := "", tip := "") -> Button:
	var b = Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_override("font", font)
	b.add_theme_font_size_override("font_size", 16)
	b.add_theme_color_override("font_color", TXT)
	b.add_theme_color_override("font_hover_color", Color("#07110f"))
	b.add_theme_color_override("font_pressed_color", Color("#07110f"))
	var n = _box(BG3, 9)
	n.content_margin_left = 10
	n.content_margin_right = 10
	n.content_margin_top = 4
	n.content_margin_bottom = 4
	var hv: StyleBoxFlat = n.duplicate()
	hv.bg_color = ACCENT
	b.add_theme_stylebox_override("normal", n)
	b.add_theme_stylebox_override("hover", hv)
	b.add_theme_stylebox_override("pressed", hv)
	b.add_theme_stylebox_override("hover_pressed", hv)
	if ico != "":
		var t = _tex(ico)
		if t:
			b.icon = t
			b.expand_icon = false
			b.add_theme_constant_override("icon_max_width", 22)
	if tip != "":
		b.mouse_entered.connect(func(): tip_label.text = tip)
		b.mouse_exited.connect(func(): tip_label.text = "Shift+T / F9 — меню   |   Esc — закрыть")
	b.pressed.connect(cb)
	return b


func _tex(name: String) -> Texture2D:
	if icons.has(name):
		return icons[name]
	var img = Image.load_from_file(base_dir.path_join("ic/" + name + ".png"))
	var t: Texture2D = ImageTexture.create_from_image(img) if img else null
	icons[name] = t
	return t


func _icon(name: String, px: int) -> Control:
	var r = TextureRect.new()
	r.texture = _tex(name)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.custom_minimum_size = Vector2(px, px)
	return r


func _clear() -> void:
	for c in body.get_children():
		body.remove_child(c)
		c.queue_free()


func _row() -> HBoxContainer:
	var r = HBoxContainer.new()
	r.add_theme_constant_override("separation", 8)
	body.add_child(r)
	return r


func _heading(text: String, ico := "") -> void:
	var r = _row()
	if ico != "":
		r.add_child(_icon(ico, 28))
	r.add_child(_label(text, 21))


func _section(text: String, extra: Control = null) -> void:
	var r = _row()
	r.add_child(_label(text, 16, ACCENT))
	if extra:
		r.add_child(extra)


func _set_tab(t: String) -> void:
	tab = t
	confirm_key = ""
	refresh()


func refresh() -> void:
	if not opened:
		return
	for k in tab_buttons:
		tab_buttons[k].button_pressed = (k == tab)
	_clear()
	match tab:
		"vars":
			_tab_vars()
		"unlock":
			_tab_unlock()
		"story":
			_tab_story()
		"game":
			_tab_game()
		"scan":
			_tab_scan()
		_:
			_tab_help()


func _filter_box(current: String, cb: Callable, hint: String) -> LineEdit:
	var le = LineEdit.new()
	le.text = current
	le.placeholder_text = hint
	le.custom_minimum_size = Vector2(320, 0)
	le.add_theme_font_override("font", font)
	le.add_theme_font_size_override("font_size", 16)
	le.text_submitted.connect(func(t): cb.call(t))
	return le


# ------------------------------------------------------------------ вкладка: переменные
func _tab_vars() -> void:
	var top = _row()
	top.add_child(_label("Переменные", 21))
	top.add_child(_filter_box(filter_text, func(t): filter_text = t; refresh(), "фильтр по имени, Enter"))
	var sp = Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(sp)
	top.add_child(_label("шаг", 15, DIM))
	for s in [1, 5, 10, 50]:
		var b = _button(str(s), func(): step = s; refresh())
		b.toggle_mode = true
		b.button_pressed = step == s
		top.add_child(b)

	var groups = {}
	var q = filter_text.strip_edges().to_lower()
	for e in _entries():
		var name = nice(e)
		if q != "" and not (q in name.to_lower() or q in e.path.to_lower()):
			continue
		var g = group_of(e, name)
		if not groups.has(g):
			groups[g] = []
		groups[g].append([e, name])
	var fixed = ["Деньги", "Время", "Статы", "Сюжетные флаги", "Строки", "Служебное"]
	var order = []
	for g in groups:
		if not g in fixed:
			order.append(g)
	order.sort()
	for g in fixed:
		if groups.has(g):
			order.append(g)
	if order.is_empty():
		body.add_child(_label("Ничего не найдено. Начни игру — переменные появятся.", 16, DIM))
	for g in order:
		var items: Array = groups[g]
		items.sort_custom(func(a, b): return a[1] < b[1])
		var extra: Control = null
		if g == "Служебное" and q == "":
			extra = _button("свернуть" if show_service else "показать", func(): show_service = not show_service; refresh())
		_section("%s  %d" % [g, items.size()], extra)
		if g == "Служебное" and q == "" and not show_service:
			continue
		for it in items:
			_var_row(it[0], it[1])


func _var_row(e: Entry, name: String) -> void:
	var v = get_value(e.path)
	var r = _row()
	var names = VBoxContainer.new()
	names.custom_minimum_size = Vector2(330, 0)
	names.add_theme_constant_override("separation", 0)
	names.add_child(_label(name, 17))
	var m = meaning(e)
	var small = _label((e.path.trim_prefix("dlg:") + " | " + m), 12, DIM)
	small.clip_text = true
	small.custom_minimum_size = Vector2(330, 0)
	names.add_child(small)
	r.add_child(names)
	var val = _label(str(v), 18, ACCENT)
	val.custom_minimum_size = Vector2(110, 0)
	r.add_child(val)
	if e.kind == "num":
		r.add_child(_button("−", func(): set_value(e.path, get_value(e.path) - step); refresh(), "", "Уменьшить на шаг"))
		r.add_child(_button("+", func(): set_value(e.path, get_value(e.path) + step); refresh(), "", "Увеличить на шаг"))
		var le = LineEdit.new()
		le.placeholder_text = "ввод"
		le.custom_minimum_size = Vector2(90, 0)
		le.add_theme_font_override("font", font)
		le.text_submitted.connect(func(t):
			if t.is_valid_float():
				set_value(e.path, float(t))
			refresh())
		r.add_child(le)
		var fz = _button("", func(): _freeze(e.path); refresh(), "snow", "Заморозить: игра не сможет изменить значение")
		fz.toggle_mode = true
		fz.button_pressed = frozen.has(e.path)
		r.add_child(fz)
		for t in thresholds(e):
			if typeof(v) in [TYPE_INT, TYPE_FLOAT] and t > v:
				r.add_child(_button(_num(t), func(): set_value(e.path, t); refresh(), "target", "Поставить %s — порог из условий сцен" % _num(t)))
				break
	elif e.kind == "flag":
		r.add_child(_button("ВКЛ" if v else "выкл", func(): set_value(e.path, not get_value(e.path)); refresh()))
	else:
		var le = LineEdit.new()
		le.text = str(v)
		le.custom_minimum_size = Vector2(220, 0)
		le.add_theme_font_override("font", font)
		le.text_submitted.connect(func(t): set_value(e.path, t); refresh())
		r.add_child(le)


func _freeze(path: String) -> void:
	if frozen.has(path):
		frozen.erase(path)
	else:
		frozen[path] = get_value(path)


# ------------------------------------------------------------------ вкладка: открытое
func _unlock_owner() -> Array:
	# [узел, имя массива] — глобальный объект со списком открытого (unlocked)
	for al in _autoloads():
		for prop in _script_vars(al[1]):
			if "unlock" in prop and typeof(al[1].get(prop)) == TYPE_ARRAY:
				return [al[0], al[1], prop]
	return []


func _all_unlockables(owner: Array) -> Array:
	var names = {}
	if owner.size() > 0:
		for x in owner[1].get(owner[2]):
			names[str(x)] = true
		for prop in _script_vars(owner[1]):
			var v = owner[1].get(prop)
			if prop != owner[2] and "unlock" in prop and typeof(v) == TYPE_ARRAY:
				for x in v:
					names[str(x)] = true
	var rx = RegEx.new()
	rx.compile("unlock:([\\w|]+)|\\{\\w+\\.unlocked_(\\w+)\\}")
	for path in _dtl_files():
		var f = FileAccess.open(path, FileAccess.READ)
		if f:
			for m in rx.search_all(f.get_as_text()):
				var n = m.get_string(1) if m.get_string(1) != "" else m.get_string(2)
				if not n.contains("|"):
					names[n] = true
	var out = names.keys()
	out.sort()
	return out


func _tab_unlock() -> void:
	_heading("Открытое", "key")
	var owner = _unlock_owner()
	if owner.is_empty():
		body.add_child(_label("Списка открытого в этой игре не нашлось — смотри «Переменные» (сюжетные флаги).", 16, DIM))
		return
	body.add_child(_label("Список «%s.%s»: включи, чтобы открыть (одежда, игрушки, события). Проверяется в сценах — см. подсказку." % [owner[0], owner[2]], 14, DIM))
	var have: Array = owner[1].get(owner[2])
	for n in _all_unlockables(owner):
		var on: bool = have.has(n)
		var r = _row()
		var lbl = VBoxContainer.new()
		lbl.custom_minimum_size = Vector2(420, 0)
		var e = Entry.new()
		e.label = n
		e.source = "dlg"
		e.path = "dlg:" + owner[0] + ".unlocked_" + n
		lbl.add_child(_label(nice(e), 17))
		lbl.add_child(_label(n + " | " + meaning(e), 12, DIM))
		r.add_child(lbl)
		r.add_child(_button("открыто" if on else "закрыто", func(): _toggle_unlock(owner, n); refresh()))


func _toggle_unlock(owner: Array, n: String) -> void:
	var node: Node = owner[1]
	var arr: Array = node.get(owner[2])
	if arr.has(n):
		if node.has_method("lock"):
			node.call("lock", n)
		else:
			arr.erase(n)
			_sync_dialogic(owner[0], ["unlocked_" + n], false)
	else:
		if node.has_method("unlock"):
			node.call("unlock", n)
		else:
			arr.append(n)
			_sync_dialogic(owner[0], ["unlocked_" + n], true)


# ------------------------------------------------------------------ вкладка: сюжет
func _game_actions() -> Array:
	# методы глобальных объектов без аргументов, похожие на действия (next_day, next_daytime…)
	var out = []
	for al in _autoloads():
		var sc = al[1].get_script()
		for m in sc.get_script_method_list():
			var name: String = m["name"]
			if name.begins_with("_") or m["args"].size() > 0:
				continue
			var head: String = name.split("_")[0]
			if head in SKIP_METHODS or name in out:
				continue
			out.append([al[0], name])
	return out


func _tab_story() -> void:
	_heading("Действия игры", "actions")
	body.add_child(_label("Функции самой игры без параметров (например, следующий день). Второй щелчок — выполнить.", 14, DIM))
	var r = _row()
	var n = 0
	for a in _game_actions():
		var key: String = a[0] + "." + a[1]
		var label = nice(_entry(key, a[1], 0, "auto"))
		var b = _button(("Точно? " if confirm_key == key else "") + label, func(): _run_action(key, a), "", key)
		r.add_child(b)
		n += 1
		if n % 4 == 0:
			r = _row()
	if n == 0:
		r.add_child(_label("не найдено", 15, DIM))

	_heading("Сцены диалогов", "story")
	body.add_child(_label("Запуск любой сцены Dialogic. Текущая сцена прервётся; лучше сохраниться заранее.", 14, DIM))
	var top = _row()
	top.add_child(_filter_box(story_filter, func(t): story_filter = t; refresh(), "фильтр сцен, Enter"))
	var q = story_filter.strip_edges().to_lower()
	for path in _dtl_files():
		var scene: String = path.get_file().get_basename()
		if q != "" and not q in scene.to_lower():
			continue
		var rr = _row()
		var l = _label(scene, 16)
		l.custom_minimum_size = Vector2(380, 0)
		rr.add_child(l)
		rr.add_child(_button("запустить", func(): _start_timeline(path), "rocket"))


func _run_action(key: String, a: Array) -> void:
	if confirm_key != key:
		confirm_key = key
		refresh()
		return
	confirm_key = ""
	var node = get_node_or_null("/root/" + a[0])
	if node:
		node.call(a[1])
	refresh()


func _start_timeline(path: String) -> void:
	var d = _dialogic()
	if d == null:
		return
	toggle(false)
	d.start(path)


# ------------------------------------------------------------------ вкладка: поиск
func _numeric_snapshot() -> Dictionary:
	var out = {}
	for e in _entries():
		var v = get_value(e.path)
		if typeof(v) in [TYPE_INT, TYPE_FLOAT]:
			out[e.path] = v
	return out


func _tab_scan() -> void:
	_heading("Найти переменную", "scanner")
	body.add_child(_label("Как ArtMoney, но по именам: «Снимок» → поиграй (потрать деньги, подними стат) → сужай.", 14, DIM))
	var r = _row()
	r.add_child(_button("Снимок", func(): scan_old = _numeric_snapshot(); scan_cands = scan_old.keys(); scan_msg = "Снимок: %d чисел. Поиграй и сужай." % scan_cands.size(); refresh(), "camera"))
	for m in [["изменились", "changed"], ["не изменились", "same"], ["больше", "up"], ["меньше", "down"]]:
		r.add_child(_button(m[0], func(): _narrow(m[1]); refresh()))
	body.add_child(_label(scan_msg, 16, ACCENT))
	if scan_cands.size() > 0 and scan_cands.size() <= 60:
		var all = {}
		for e in _entries():
			all[e.path] = e
		for p in scan_cands:
			var rr = _row()
			var e: Entry = all.get(p)
			var l = _label(nice(e) if e else p, 16)
			l.custom_minimum_size = Vector2(360, 0)
			rr.add_child(l)
			rr.add_child(_label("%s → %s" % [str(scan_old.get(p)), str(get_value(p))], 16, ACCENT))


func _narrow(mode: String) -> void:
	if scan_old.is_empty():
		scan_msg = "Сначала «Снимок»."
		return
	var now = _numeric_snapshot()
	var keep = []
	for p in scan_cands:
		if not now.has(p):
			continue
		var a = scan_old[p]
		var b = now[p]
		if (mode == "changed" and a != b) or (mode == "same" and a == b) or (mode == "up" and b > a) or (mode == "down" and b < a):
			keep.append(p)
	scan_cands = keep
	scan_old = now
	scan_msg = "Осталось: %d" % keep.size() + ("" if keep.size() <= 60 else " (покажу, когда будет ≤ 60)")


# ------------------------------------------------------------------ вкладка: игра
func _player() -> Node:
	var t = get_tree()
	for g in ["player", "Player"]:
		for n in t.get_nodes_in_group(g):
			if n is Node2D or n is Node3D:
				return n
	var cs = t.current_scene
	if cs:
		for nm in ["Player", "player", "Hero", "hero", "PlayerCharacter"]:
			var n = cs.find_child(nm, true, false)
			if n is Node2D or n is Node3D:
				return n
	return null


func _set_speed(k: float) -> void:
	speed = k
	Engine.time_scale = k
	if speed_label == null:
		speed_label = _label("", 18, Color("#07110f"))
		var sb = _box(ACCENT, 9)
		sb.content_margin_left = 10
		sb.content_margin_right = 10
		speed_label.add_theme_stylebox_override("normal", sb)
		speed_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
		speed_label.offset_left = -150
		speed_label.offset_right = -12
		speed_label.offset_top = 10
		speed_label.offset_bottom = 44
		add_child(speed_label)
	speed_label.text = "ПАУЗА" if k == 0.0 else "×" + _num(k)
	speed_label.visible = k != 1.0


# шаг кадра на паузе: один кадр с темпом 1 (и без паузы дерева, если меню открыто), затем
# снова пауза. process_frame приходит до _process узлов — поэтому ждём начала второго кадра.
func _frame_step() -> void:
	_set_speed(0.0)
	var was_paused = get_tree().paused
	get_tree().paused = false
	Engine.time_scale = 1.0
	await get_tree().process_frame
	await get_tree().process_frame
	Engine.time_scale = speed
	get_tree().paused = was_paused


func _set_fps(on: bool) -> void:
	show_fps = on
	if fps_label == null:
		fps_label = _label("", 16, ACCENT)
		var sb = _box(Color("#0b0e14e6"), 9)
		sb.content_margin_left = 10
		sb.content_margin_right = 10
		fps_label.add_theme_stylebox_override("normal", sb)
		fps_label.set_anchors_preset(Control.PRESET_TOP_LEFT)
		fps_label.offset_left = 12
		fps_label.offset_top = 10
		add_child(fps_label)
	fps_label.visible = on


func _tab_game() -> void:
	_heading("Игра", "stopwatch")
	_section("Скорость игры")
	var r = _row()
	for s in [[0.0, "пауза"], [0.25, "×0.25"], [0.5, "×0.5"], [1.0, "×1"], [2.0, "×2"], [3.0, "×3"], [5.0, "×5"]]:
		var b = _button(s[1], func(): _set_speed(s[0]); refresh())
		if is_equal_approx(speed, s[0]):
			b.add_theme_color_override("font_color", ACCENT)
		r.add_child(b)
	var hint = _label("Темп включится, когда закроешь меню (пока меню открыто, игра на паузе). Пока он не ×1, в углу виден значок.", 14, DIM)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	hint.custom_minimum_size = Vector2(760, 0)
	body.add_child(hint)
	var rs = _row()
	rs.add_child(_button("Шаг кадра", func(): _frame_step(); refresh(), "",
			"Игра на паузе продвигается ровно на один кадр — разглядеть анимацию или баг"))
	var fb = _button("FPS в углу: вкл" if show_fps else "FPS в углу: выкл", func(): _set_fps(not show_fps); refresh())
	if show_fps:
		fb.add_theme_color_override("font_color", ACCENT)
	rs.add_child(fb)
	rs.add_child(_label("сейчас %d кадров/с" % Engine.get_frames_per_second(), 14, DIM))
	_section("Профиль игры")
	var has_pr = FileAccess.file_exists(_profile_path())
	var rp = _row()
	rp.add_child(_button("Сохранить профиль", func(): _profile_save(true); refresh(), "save",
			"Темп и заморозки будут ставиться сами при каждом запуске игры"))
	if has_pr:
		rp.add_child(_button("Удалить профиль", func(): _profile_save(false); refresh(), "trash"))
	body.add_child(_label("Профиль есть: ставится сам при запуске." if has_pr else
			"Профиля нет: выбери темп, заморозь нужное во «Переменных» и нажми «Сохранить профиль».", 14, DIM))
	_section("Игрок и точки телепорта")
	var p = _player()
	if p == null:
		body.add_child(_label("Игрок не найден: нет узла в группе player и узла Player / Hero в текущей сцене.", 15, DIM))
		return
	var r2 = _row()
	var l = _label("%s: %s" % [p.name, str(p.global_position)], 16)
	l.custom_minimum_size = Vector2(460, 0)
	r2.add_child(l)
	r2.add_child(_button("Запомнить место", func(): _remember(p); refresh(), "pin", "Точки живут до выхода из игры"))
	for i in places.size():
		var pl = places[i]
		var rr = _row()
		var pn = _label(pl["name"], 16)
		pn.custom_minimum_size = Vector2(460, 0)
		rr.add_child(pn)
		rr.add_child(_button("сюда", func(): _teleport(pl)))
		rr.add_child(_button("×", func(): places.remove_at(i); refresh()))


# ------------------------------------------------------------------ профиль игры
# Темп и заморозки, которые ставятся сами при каждом запуске (tm_profile.json рядом с меню).
func _profile_path() -> String:
	return base_dir.path_join("tm_profile.json")


func _profile_load() -> void:
	if not FileAccess.file_exists(_profile_path()):
		return
	var f = FileAccess.open(_profile_path(), FileAccess.READ)
	var d = JSON.parse_string(f.get_as_text()) if f else null
	if typeof(d) != TYPE_DICTIONARY:
		return
	if d.has("speed") and float(d["speed"]) != 1.0:
		_set_speed(float(d["speed"]))
	var fr = d.get("frozen", {})
	if typeof(fr) == TYPE_DICTIONARY:
		for p in fr:
			frozen[p] = fr[p]           # тип приведёт set_value по текущему значению игры


func _profile_save(on: bool) -> void:
	if not on:
		DirAccess.remove_absolute(_profile_path())
		return
	var f = FileAccess.open(_profile_path(), FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({"speed": speed, "frozen": frozen}, " "))
		f.close()


func _remember(p) -> void:
	var sc = get_tree().current_scene
	var scene = sc.scene_file_path.get_file().get_basename() if sc else ""
	places.append({"name": "%s  %s" % [scene, str(p.global_position)], "scene": scene, "pos": p.global_position})


func _teleport(pl: Dictionary) -> void:
	var p = _player()
	if p == null or typeof(p.global_position) != typeof(pl["pos"]):
		return
	p.global_position = pl["pos"]
	if "velocity" in p:
		p.velocity = p.velocity * 0
	toggle(false)


# ------------------------------------------------------------------ вкладка: справка
func _tab_help() -> void:
	_heading("Как пользоваться", "question")
	for t in [
		["Открыть и закрыть", "Shift+T или F9, Esc — закрыть. Пока меню открыто, игра на паузе."],
		["Переменные", "Всё, что игра хранит: деньги, статы, прогресс персонажей, переменные диалогов. Серая строка — где значение проверяется в сценах и что нужно. Мишень — поставить порог из условий. Снежинка — заморозить."],
		["Открытое", "Список разблокировок игры (одежда, предметы, события) — включай и выключай."],
		["Сюжет", "Действия самой игры (следующий день, время суток) и запуск любой сцены диалогов."],
		["Игра", "Скорость игры (пауза, ×0.25 … ×5) и точки телепорта игрока (узел в группе player или Player в сцене)."],
		["Поиск", "Если нужной переменной не видно по имени: снимок → поиграй → «изменились»."],
		["Сохранения", "Меню ничего не сохраняет само. Перед экспериментами сохранись в игре."],
	]:
		var r = _row()
		var v = VBoxContainer.new()
		v.add_child(_label(t[0], 17, ACCENT))
		var d = _label(t[1], 15, DIM)
		d.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		d.custom_minimum_size = Vector2(760, 0)
		v.add_child(d)
		r.add_child(v)


# ------------------------------------------------------------------ открыть / закрыть
func toggle(on: bool) -> void:
	if on == opened:
		return
	opened = on
	var d = _dialogic()
	if on:
		prev_paused = get_tree().paused
		get_tree().paused = true
		if d and "paused" in d:
			prev_dialogic_paused = d.paused
			d.paused = true
		_usage = null
		_chars = null
		_layout()
		ui_root.visible = true
		refresh()
	else:
		ui_root.visible = false
		get_tree().paused = prev_paused
		if d and "paused" in d:
			d.paused = prev_dialogic_paused


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var k: int = event.keycode
		if (k == KEY_T and event.shift_pressed) or k == KEY_F9:
			var f = get_viewport().gui_get_focus_owner()
			if not (opened and f is LineEdit):
				toggle(not opened)
				get_viewport().set_input_as_handled()
				return
		if opened and k == KEY_ESCAPE:
			toggle(false)
			get_viewport().set_input_as_handled()


func _process(_delta: float) -> void:
	if show_fps and fps_label != null:
		fps_label.text = "FPS %d" % Engine.get_frames_per_second()
	for p in frozen:
		if get_value(p) != frozen[p]:
			set_value(p, frozen[p])


# ------------------------------------------------------------------ самопроверка (скриншоты)
func _selftest(out_dir: String) -> void:
	await get_tree().create_timer(2.5).timeout
	var report = []
	for e in _entries():
		report.append("%s | %s | %s | %s" % [e.path, nice(e), meaning(e), str(thresholds(e))])
	report.append("actions: " + str(_game_actions()))
	report.append("timelines: %d, chars: %s" % [_dtl_files().size(), str(characters())])
	var owner = _unlock_owner()
	report.append("unlock owner: " + (str(owner[0]) + "." + str(owner[2]) if owner.size() else "-"))
	var f = FileAccess.open(out_dir.path_join("tm_report.txt"), FileAccess.WRITE)
	f.store_string("\n".join(report))
	f.close()
	toggle(true)
	for t in TABS:
		_set_tab(t[0])
		await get_tree().create_timer(0.6).timeout
		if DisplayServer.get_name() != "headless":       # без окна — только прогон вкладок
			get_viewport().get_texture().get_image().save_png(out_dir.path_join("tm_%s.png" % t[0]))
	show_service = true
	_set_tab("vars")
	await get_tree().create_timer(0.4).timeout
	get_tree().quit()
