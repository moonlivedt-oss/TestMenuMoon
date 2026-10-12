# ==================== тема + утилиты (редактор внешнего вида) ====================
init -4 python:
    # Пресеты для вкладки «Настройки»
    TM_ACCENTS = [
        ("Бирюза", TM_TOK["accent"]), ("Голубой", "#4aa8ff"), ("Розовый", "#ff6b9d"),
        ("Зелёный", TM_TOK["ok"]), ("Оранж", "#ff9f43"), ("Фиолет", "#b06bff"),
        ("Красный", "#ff5c5c"), ("Белый", TM_TOK["text"]),
    ]
    TM_OPACITY = [("70%", "b3"), ("85%", "d9"), ("95%", "f2"), ("100%", "ff")]
    TM_SCALES = [("S", 0.9), ("M", 1.0), ("L", 1.15)]

    # Базовые размеры шрифтов (для масштабирования)
    _TM_BASE_SIZES = {
        "tm_label": 20, "tm_value": 22, "tm_dim": 17, "tm_h": 25,
        "tm_btn_text": 20, "tm_tab_text": 20, "tm_pm_text": 26,
        "tm_foot": 16, "tm_head_btn_text": 18, "tm_head_title": 23, "tm_icon_text": 19,
        "tm_hud_label": 17, "tm_hint_h": 19, "tm_hint_choice": 18, "tm_hint_note": 15,
        "tm_hint_eff": 16, "tm_tip": 16, "tm_ico_label": 20,
    }

    def tm_pref(name, default):
        v = getattr(store.persistent, name, None)
        return default if v is None else v

    def tm_hex_alpha(a, aa):
        # "#abc" / "#aabbcc" + альфа "40" -> "#aabbcc40"
        s = (a or TM_TOK["accent"]).lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        return "#" + s[:6] + aa

    def tm_can_tint():
        # TintMatrix / matrixcolor — с Ren'Py 7.4 и только на GL2; на старых сборках и
        # GL1-фолбэке первая же тонировка роняла всю тему («Тема: ошибка» на каждом старте)
        if getattr(store, "TintMatrix", None) is None:
            return False
        try:
            return bool(renpy.version_tuple[:2] >= (7, 4))
        except Exception:
            return False

    def tm_win_size():
        # размер окна (в вёрстке 1080p) растёт с крупным шрифтом, чтобы вкладки не вылезали
        f = max(1.0, float(tm_pref("tm_scale", 1.0)))
        return int(1000 * f), int(660 * f)

    def _tm_theme_part(fn):
        try:
            fn()
            return True
        except Exception:
            return False

    def tm_apply_theme():
        # Применяет акцент/прозрачность/масштаб к стилям и перестраивает их вживую.
        # Каждая часть — в своём try: сбой тонировки не отменяет масштаб шрифтов и т.п.
        a  = tm_pref("tm_accent", None) or getattr(store, "tm_accent", None) or TM_TOK["accent"]
        op = tm_pref("tm_opacity", "f7")
        try:
            sc = float(tm_pref("tm_scale", 1.0))
        except Exception:
            sc = 1.0
        tm_ui.accent = a        # не store.tm_accent: та переменная попадала в каждый сейв

        def _accent():
            style.tm_value.color = a
            style.tm_hud_value.color = a
            style.tm_hint_h.color = a
            style.tm_bar.left_bar = Solid(a)
            style.tm_vscrollbar.hover_thumb = Frame(Solid(a), 0, 0)
            style.tm_field.selected_background = Frame(Solid(tm_hex_alpha(a, "40")), 6, 6)

        def _fonts():
            for sname, base in _TM_BASE_SIZES.items():
                getattr(style, sname).size = int(round(base * sc))

        tint = tm_can_tint() and renpy.loadable("tm_ui/tm_panel.png")
        ok = _tm_theme_part(_accent)
        ok = _tm_theme_part(lambda: _tm_theme_frames(a, op, tint)) and ok
        if not ok:
            _tm_theme_part(lambda: _tm_theme_frames(a, op, False))   # без тонировки
        _tm_theme_part(_fonts)
        _tm_theme_part(renpy.style.rebuild)
        try:
            renpy.session["tm_theme_mark"] = style.tm_panel.background
        except Exception:
            pass

    def _tm_theme_check():
        # Ren'Py после start_callbacks ещё раз собирает стили и сбрасывает правки темы
        # (на 8.5 окно оставалось с квадратным Solid-фолбэком). Метка — объект фона панели:
        # не совпал — тема слетела, накладываем заново (с ограничением на число попыток).
        try:
            if style.tm_panel.background is renpy.session.get("tm_theme_mark"):
                return
            n = renpy.session.get("tm_theme_tries", 0)
            if n >= 30:
                return
            renpy.session["tm_theme_tries"] = n + 1
            tm_apply_theme()
        except Exception:
            pass

    def _tm_theme_frames(a, op, tint):
        # --- фоны: скруглённые 9-slice тайлы (assets -> game/tm_ui), иначе Solid-фолбэк ---
        if tint:
            try:
                _opa = int(op, 16) / 255.0
            except Exception:
                _opa = 0.97
            _bt = "tm_ui/tm_btn.png"
            _idle = Frame(Transform(_bt, alpha=0.07), 13, 13)
            _acc = Frame(Transform(_bt, matrixcolor=TintMatrix(a)), 13, 13)
            style.tm_border.background = Frame(Transform("tm_ui/tm_ring.png", matrixcolor=TintMatrix(a)), 26, 26)
            style.tm_panel.background = Frame(Transform("tm_ui/tm_panel.png", alpha=_opa), 26, 26)
            style.tm_header_bg.background = Frame(Transform("tm_ui/tm_head.png", matrixcolor=TintMatrix(a)), 26, 26, 26, 6)
            style.tm_footer_bg.background = Frame("tm_ui/tm_foot.png", 26, 6, 26, 26)
            style.tm_btn.background = _idle
            style.tm_btn.hover_background = _acc
            style.tm_pm_btn.background = _idle
            style.tm_pm_btn.hover_background = _acc
            style.tm_seg.background = _idle
            style.tm_seg.hover_background = Frame(Transform(_bt, alpha=0.13), 13, 13)
            style.tm_seg.selected_background = _acc
            style.tm_tab_btn.hover_background = _idle
            style.tm_filter_frame.background = _idle
            style.tm_field.background = _idle
            style.tm_field.hover_background = Frame(Transform(_bt, alpha=0.13), 13, 13)
            style.tm_icon_btn.background = _idle
            style.tm_icon_btn.hover_background = _acc
            style.tm_icon_btn.selected_background = _acc
            style.tm_hud_frame.background = Frame(Transform("tm_ui/tm_panel.png", alpha=0.86), 26, 26)
            style.tm_hint_frame.background = Frame(Transform("tm_ui/tm_panel.png", alpha=0.92), 26, 26)
            style.tm_head_btn.background = Frame(Transform(_bt, matrixcolor=TintMatrix(TM_TOK["on_accent"]), alpha=0.16), 13, 13)
            style.tm_head_btn.hover_background = Frame(Transform(_bt, matrixcolor=TintMatrix(TM_TOK["on_accent"]), alpha=0.34), 13, 13)
        else:
            style.tm_header_bg.background = Solid(a)
            style.tm_border.background = Frame(Solid(a), 0, 0)
            style.tm_btn.hover_background = Frame(Solid(a), 8, 8)
            style.tm_pm_btn.hover_background = Frame(Solid(a), 8, 8)
            style.tm_icon_btn.hover_background = Frame(Solid(a), 8, 8)
            style.tm_icon_btn.selected_background = Frame(Solid(a), 8, 8)
            style.tm_seg.selected_background = Frame(Solid(a), 8, 8)
            style.tm_panel.background = Frame(Solid(TM_TOK["bg_panel"] + op), 0, 0)

    # ---------------- значки (game/tm_ui/ic/*.png из библиотеки картинок) ----------------
    def tm_ic(name):
        # путь значка или None — тогда экран рисует только подпись (старые установки без ic/)
        p = "tm_ui/ic/%s.png" % name
        c = renpy.session.get("tm_ic")
        if c is None:
            c = renpy.session["tm_ic"] = {}
        if p not in c:
            try:
                c[p] = bool(renpy.loadable(p))
            except Exception:
                c[p] = False
        return p if c[p] else None

    def tm_mascot(name):
        p = "tm_ui/m/%s.png" % name
        try:
            return p if renpy.loadable(p) else None
        except Exception:
            return None

    def tm_set_accent(hexc):
        store.persistent.tm_accent = hexc
        tm_apply_theme()
        renpy.restart_interaction()

    def tm_set_opacity(op):
        store.persistent.tm_opacity = op
        tm_apply_theme()
        renpy.restart_interaction()

    def tm_set_scale(sc):
        store.persistent.tm_scale = sc
        tm_apply_theme()
        renpy.restart_interaction()

    def tm_theme_reset():
        store.persistent.tm_accent = None
        store.persistent.tm_opacity = None
        store.persistent.tm_scale = None
        store.tm_ui.win_pos = None
        tm_apply_theme()
        renpy.restart_interaction()

    def tm_engine_tag():
        try:
            return u"Ren'Py %s" % ".".join(str(x) for x in renpy.version_tuple[:3])
        except Exception:
            return u""

    # «Как пользоваться»: (значок, заголовок, текст). Без [ ] и { } — это теги/подстановки Ren'Py.
    TM_HELP = [
        ("logo", u"Как открыть",
         u"Shift+T или запасная клавиша (F9, выбирается в «Настройках») — открыть и закрыть, Esc — закрыть. "
         u"Окно перетаскивается за шапку. «свернуть» — мини-плашка поверх игры: откат, слот 1, скип, HUD. "
         u"Наведи курсор на кнопку — внизу окна появится подсказка."),
        ("rewind", u"Перемотка",
         u"Откат назад и вперёд, лог последних реплик — «сюда» откатывает прямо к нужной. Три быстрых слота "
         u"(Shift+F5 — сохранить в слот 1, Shift+F9 — загрузить), мгновенный скип текста. Перед переходами меню "
         u"само сохраняет слот «Перед прыжком». Журнал правок: любую правку можно отменить, Ctrl+Z — последнюю."),
        ("stats", u"Значения",
         u"Статы игры с понятными именами, по группам. Звезда — в избранное (наверху списка), глаз — в HUD. "
         u"Цветная отметка +2 или −50 рядом со значением — игра изменила его с прошлого открытия меню, "
         u"кнопка «изменённые» оставит только такие. Снежинка — заморозить; знак рядом меняет вид: "
         u"= ровно, ≥ не меньше, ≤ не больше. Мишень — следующий порог из условий сценария. "
         u"Щелчок по имени — дать своё. В окне ввода +50, -10, *2 — от текущего значения, =-5 — точное. "
         u"Значения можно сохранить в файл и загрузить в другой партии. PgUp и PgDn листают страницы."),
        ("actions", u"Выдача / Код",
         u"Готовые действия игры (если их задали в студии) и свой Python-код: выражение покажет значение, "
         u"команда выполнится. Enter — выполнить."),
        ("scanner", u"Поиск",
         u"Не нашёл переменную? «Снимок», поиграй и вернись: «изменились», «больше», «меньше», "
         u"«изменилось на» (потратил 50 — введи -50) оставят подходящие. «Шаг назад» отменяет сужение."),
        ("story", u"Сюжет",
         u"Shift+H — подсказки к выборам и к кнопкам экранов-развилок; у скрытого варианта видны текущие "
         u"значения из условия, «код» показывает, что стоит за вариантом в сценарии. История выборов — "
         u"что каждый выбор реально изменил. Кнопки на экране — что делают и «нажать». Метка: прыжок "
         u"или повтор сцены. Поиск находит и реплики, и варианты выбора. Персонажам можно дать свои имена."),
        ("checklist", u"Тест",
         u"Авто-прохождение: меню само листает текст и отвечает на выборы (новые варианты, случайно или "
         u"первый), останавливается на метке, на новой реплике или когда игра ждёт игрока. Маршруты: выборы "
         u"партии записываются, сохранённый маршрут меню пройдёт само. Покрытие — сколько реплик, сцен и "
         u"вариантов уже видели; непросмотренные сцены — с переходом и «откуда сюда попадают». "
         u"Shift+B — заметка о баге: текст, место, картинки и скриншот в tm_bugs/tm_bugs.md."),
        ("settings", u"Настройки",
         u"Цвет, прозрачность, размер, HUD и его угол (можно добавить любое выражение), клавиша меню, "
         u"консоль (Shift+O), «Где я», отчёт тестера в файл, «Убрать следы меню» перед удалением."),
        ("question", u"Эта справка",
         u"Открывается кнопкой со знаком вопроса в шапке меню."),
    ]

    def tm_tabs():
        # (ключ, подпись, подсказка) видимых вкладок; «Выдача» — только если у игры есть действия.
        # Значок вкладки — tm_ui/ic/<ключ>.png.
        tabs = [("rewind", u"Перемотка", u"Откат, лог реплик, быстрые слоты, скип текста"),
                ("stats", u"Значения", u"Статы игры: правка, заморозка, HUD")]
        if getattr(store, "tm_actions", None):
            tabs.append(("actions", u"Выдача", u"Предметы, деньги и прочее кодом игры; свой Python-код"))
        else:
            tabs.append(("actions", u"Код", u"Свой Python-код в игре: значение или команда"))
        tabs += [("scanner", u"Поиск", u"Найти неизвестную переменную: снимок и сужение"),
                 ("story", u"Сюжет", u"Подсказки выборов, переход к метке и реплике, галерея, персонажи"),
                 ("checklist", u"Тест", u"Авто-прохождение, маршруты, покрытие, непросмотренные сцены, заметки о багах"),
                 ("settings", u"Настройки", u"Цвет, прозрачность, размер, HUD, консоль")]
        return tabs

    def tm_toggle_dev():
        config.developer = not config.developer
        tm_note("Консоль разработчика (Shift+O): " + ("ВКЛ" if config.developer else "выкл"))
        renpy.restart_interaction()

    def tm_jump(name):
        # Прыжок на метку сценария (как jump в консоли), меню при этом закрывается.
        name = (name or "").strip()
        if not name:
            tm_note("Введи имя метки")
            return
        if not renpy.has_label(name):
            tm_note("Метки нет: %s" % name)
            return
        tm_safety_save()
        store.tm_ui.open = False
        tm_note(u"Переход: %s  (вернуться — «Перед прыжком» на вкладке «Перемотка»)" % name)
        renpy.jump(name)

    # ---------------- индекс сценария (метки, реплики) — один раз за сессию ----------------
    def _tm_script_nodes():
        try:
            nodes = renpy.game.script.all_stmts
            if nodes:
                return nodes
        except Exception:
            pass
        try:
            return list(renpy.game.script.namemap.values())
        except Exception:
            return []

    def _tm_index():
        idx = renpy.session.get("tm_index")
        if idx is not None:
            return idx
        labels = {}     # файл -> [(строка, имя)]
        says = []       # (текст в нижнем регистре, имя узла, файл, строка, кто, текст)
        seen = set()
        for n in _tm_script_nodes():
            if id(n) in seen:
                continue
            seen.add(id(n))
            try:
                if isinstance(n, renpy.ast.Label):
                    if isinstance(n.name, _TM_STR) and not n.name.startswith("_"):
                        labels.setdefault(n.filename, []).append((n.linenumber, n.name))
                elif isinstance(n, renpy.ast.Say):
                    if n.filename.startswith("renpy/common") or "zzz_testmenu" in n.filename:
                        continue
                    w = n.what or ""
                    says.append((w.lower(), n.name, n.filename, n.linenumber, n.who or "", w))
                elif isinstance(n, renpy.ast.Menu):
                    # варианты выбора тоже ищутся: «как попасть к выбору X» — переход на сам выбор
                    if n.filename.startswith("renpy/") or "zzz_testmenu" in n.filename:
                        continue
                    for item in n.items:
                        if item[0] and item[2] is not None:
                            w = tm_choice_text(item[0])
                            says.append((w.lower(), n.name, n.filename, n.linenumber, u"выбор", w))
            except Exception:
                continue
        for v in labels.values():
            v.sort()
        says.sort(key=lambda s: (s[2], s[3]))
        idx = {"labels": labels, "says": says}
        renpy.session["tm_index"] = idx
        return idx

    def tm_label_at(fn, ln):
        # ближайшая метка выше строки ln в файле fn
        best = None
        for line, name in _tm_index()["labels"].get(fn, ()):
            if line <= ln:
                best = name
            else:
                break
        return best

    def tm_find_lines(q, limit=30):
        q = (q or "").strip().lower()
        if len(q) < 3:
            return []
        out = []
        for low, name, fn, ln, who, what in _tm_index()["says"]:
            if q in low:
                out.append((name, fn, ln, who, what))
                if len(out) >= limit:
                    break
        return out

    def tm_goto_node(name):
        # прыжок прямо на реплику (узел сценария); стек call не восстанавливается —
        # поэтому перед прыжком страховочный сейв (если метка вызвана через call, её
        # return уведёт в главное меню, и тогда можно вернуться из слота)
        try:
            renpy.game.script.lookup(name)
        except Exception:
            tm_note("Узел сценария не найден")
            return
        tm_safety_save()
        store.tm_ui.open = False
        tm_note(u"Переход к реплике  (вернуться — «Перед прыжком» на вкладке «Перемотка»)")
        renpy.jump(name)

    # ---------------- подсказки выборов: что изменит каждый вариант ----------------
    # Анализ AST блока выбора (работает и с .rpyc без исходников): $-строки
    # (x += 1, y -= 2, z = ...), вызовы функций, jump/call + один уровень
    # внутрь целевой метки, if-ветки. Скрытые варианты (if-условие ложно) видны
    # и выбираются кнопкой.
    import re as _tm_re
    _TM_ASSIGN_RE = _tm_re.compile(r'^([A-Za-z_][\w\.]*(?:\[[^\]]+\])*(?:\.\w+)*)\s*(\+=|-=|\*=|/=|=)(?!=)\s*(.+)$')
    _TM_CALL_RE = _tm_re.compile(r'^([A-Za-z_][\w\.]*)\s*\(.*\)$')
    TM_HINT_MAX = 10
    TM_HINT_DEPTH = 1
    # пользовательские операторы, не меняющие состояние игры
    _TM_US_SKIP = ("show", "hide", "scene", "play", "stop", "queue", "voice", "pause",
                   "window", "nvl", "with", "camera", "sound", "music", "image", "center")

    def _tm_short(s, n=34):
        s = tm_str(s).strip()
        return s if len(s) <= n else s[:n - 1] + u"…"

    def _tm_src_stmts(src):
        for line in (src or "").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ";" in line and '"' not in line and "'" not in line:
                for part in line.split(";"):
                    if part.strip():
                        yield part.strip()
            else:
                yield line

    def _tm_effect(stmt):
        m = _TM_ASSIGN_RE.match(stmt)
        if m:
            name, op, expr = m.groups()
            if name.startswith("store."):
                name = name[6:]
            if name.startswith(("_", "renpy.", "tm_", "config.", "gui.", "preferences.")):
                return None
            expr = _tm_short(expr, 22)
            if op == "+=":
                return ("down", "%s %s" % (name, expr)) if expr.startswith("-") else ("up", "%s +%s" % (name, expr))
            if op == "-=":
                return ("down", u"%s −%s" % (name, expr))
            if op == "*=":
                return ("set", u"%s ×%s" % (name, expr))
            if op == "/=":
                return ("set", u"%s ÷%s" % (name, expr))
            return ("set", "%s = %s" % (name, expr))
        m = _TM_CALL_RE.match(stmt)
        if m:
            fn = m.group(1)
            last = fn.rsplit(".", 1)[-1]
            if (fn.startswith(("renpy.", "_", "store._", "tm_")) or fn in ("pass", "print")
                    or last.startswith(("show_", "hide_", "play_", "stop_", "notify", "pause"))):
                return None             # визуал/звук — не последствия выбора
            return ("call", _tm_short(stmt, 40))
        return None

    def _tm_walk_block(block, out, depth, seen, prefix):
        # -> True, если блок завершается переходом (дальше по нему не идём)
        for node in block or ():
            if len(out) >= TM_HINT_MAX:
                return True
            try:
                if isinstance(node, renpy.ast.Python):
                    for st in _tm_src_stmts(node.code.source):
                        e = _tm_effect(st)
                        if e:
                            out.append((e[0], prefix + e[1]))
                elif isinstance(node, renpy.ast.If):
                    # если все ветки (с «иначе») уходят переходом — после if ничего не будет
                    all_go = True
                    has_else = False
                    for cond, blk in node.entries:
                        cond = cond or "True"
                        if cond.strip() == "True":
                            has_else = True
                        p = prefix + (u"если %s: " % _tm_short(cond, 20) if cond.strip() != "True" else u"иначе: ")
                        if not _tm_walk_block(blk, out, depth, seen, p):
                            all_go = False
                    if all_go and has_else:
                        return True
                elif isinstance(node, renpy.ast.Jump):
                    if node.expression:
                        out.append(("go", prefix + u"→ (вычисляемый переход)"))
                    else:
                        out.append(("go", prefix + u"→ " + node.target))
                        _tm_follow(node.target, out, depth, seen, prefix)
                    return True
                elif isinstance(node, renpy.ast.Call):
                    if not node.expression:
                        out.append(("go", prefix + "call " + node.label))
                        _tm_follow(node.label, out, depth, seen, prefix)
                elif isinstance(node, renpy.ast.Menu):
                    out.append(("go", prefix + u"→ ещё один выбор"))
                    return True
                elif isinstance(node, renpy.ast.Return):
                    return True
                elif isinstance(node, renpy.ast.UserStatement):
                    line = (getattr(node, "line", "") or "").strip()
                    if line and line.split()[0] not in _TM_US_SKIP:
                        out.append(("call", prefix + _tm_short(line, 40)))
            except Exception:
                continue
        return False

    def _tm_follow(label, out, depth, seen, prefix):
        if depth >= TM_HINT_DEPTH or label in seen:
            return
        seen.add(label)
        try:
            node = renpy.game.script.lookup(label)
        except Exception:
            return
        _tm_walk_block(getattr(node, "block", None), out, depth + 1, seen, prefix)

    def tm_cur_menu():
        # Menu-узел, на котором игра стоит прямо сейчас (или None)
        try:
            node = renpy.game.script.lookup(renpy.game.context().current)
        except Exception:
            return None
        return node if isinstance(node, renpy.ast.Menu) else None

    def tm_choice_text(label):
        s = label
        try:
            s = renpy.substitute(s)
        except Exception:
            pass
        try:
            s = renpy.filter_text_tags(s, allow=[])
        except Exception:
            pass
        return s

    def tm_menu_hints(node):
        # [(индекс, текст, условие, [(вид, текст)])] — кэш по имени узла
        cache = renpy.session.get("tm_hints")
        if cache is None:
            cache = renpy.session["tm_hints"] = {}
        key = node.name
        if key in cache:
            return cache[key]
        res = []
        for i, item in enumerate(node.items):
            label, cond, block = item[0], item[1], item[2]
            if block is None:
                continue
            effs = []
            if _tm_walk_block(block, effs, 0, set(), "") is True and len(effs) >= TM_HINT_MAX:
                effs.append(("go", u"…"))
            res.append((i, label, cond, effs))
        cache[key] = res
        return res

    def tm_cond_ok(cond):
        if not cond or cond.strip() == "True":
            return True
        try:
            return bool(renpy.python.py_eval(cond))
        except Exception:
            return False

    TM_HINT_COLORS = {"up": TM_TOK["ok"], "down": TM_TOK["err"], "set": TM_TOK["info"], "call": TM_TOK["call"], "go": TM_TOK["text_hint"]}

    def tm_hint_markup(effs):
        if not effs:
            return u"{color=#5b6373}без изменений{/color}"
        return u"   ".join(u"{color=%s}%s{/color}" % (TM_HINT_COLORS.get(k, TM_TOK["text_dim"]), tm_q(t)) for k, t in effs)

    def tm_pick_choice(node_name, i):
        # выбрать вариант напрямую (в т.ч. скрытый условием): переход на первый узел блока
        try:
            node = renpy.game.script.lookup(node_name)
            block = node.items[i][2]
            target = block[0].name
        except Exception as e:
            tm_note("Выбор: %s" % e)
            return
        tm_safety_save()
        store.tm_ui.open = False
        renpy.jump(target)

    def tm_toggle_hints():
        store.persistent.tm_hints = not tm_pref("tm_hints", True)
        tm_note("Подсказки к выборам: " + ("ВКЛ" if store.persistent.tm_hints else "выкл"))
        renpy.restart_interaction()

    def tm_toggle_pref(name, default):
        setattr(store.persistent, name, not tm_pref(name, default))
        renpy.restart_interaction()

    # ---------------- галерея / persistent ----------------
    def tm_confirm(key, fn, *args):
        # двухкликовое подтверждение для необратимого: первый клик взводит, второй исполняет
        if tm_ui.confirm == key:
            tm_ui.confirm = ""
            fn(*args)
        else:
            tm_ui.confirm = key
        renpy.restart_interaction()

    def tm_unlock_all():
        # «всё просмотрено»: метки (Replay), картинки (Gallery), музыка (Music Room)
        nl = ni = na = 0
        try:
            for name in renpy.get_all_labels():
                if isinstance(name, _TM_STR) and not name.startswith("_"):
                    renpy.mark_label_seen(name); nl += 1
        except Exception:
            pass
        try:
            for name in list(renpy.display.image.images.keys()):
                renpy.mark_image_seen(name); ni += 1
        except Exception:
            pass
        try:
            for fn in renpy.list_files():
                if fn.lower().endswith((".ogg", ".mp3", ".wav", ".opus", ".flac")):
                    renpy.mark_audio_seen(fn); na += 1
        except Exception:
            pass
        try:
            renpy.save_persistent()
        except Exception:
            pass
        tm_note("Открыто: меток %d, картинок %d, звуков %d" % (nl, ni, na))

    def tm_persistent_flags(q):
        # (путь, значение) для bool/чисел в persistent — флаги галерей, концовок, бонусов
        q = (q or "").strip().lower()
        try:
            d = vars(store.persistent)
        except Exception:
            return []
        out = []
        for k in sorted(d.keys()):
            if not isinstance(k, _TM_STR) or k.startswith("_") or k.startswith("tm_"):
                continue
            v = d[k]
            if isinstance(v, _TM_NUM) and (not q or q in k.lower()):
                out.append(("persistent." + k, v))
        return out[:60]

    def tm_screenshot():
        import os, time
        try:
            base = getattr(config, "basedir", ".") or "."
            path = os.path.join(base, "tm_shot_%d.png" % int(time.time()))
            renpy.screenshot(path)
            tm_note("Скриншот сохранён: " + path)
        except Exception as e:
            tm_note("Скриншот: %s" % e)

