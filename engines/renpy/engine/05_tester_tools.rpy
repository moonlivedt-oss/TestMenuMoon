# ==================== инструменты тестера: история, экраны, «где я», отчёт ====================
init -3 python:

    # ---------------- окно ввода значения / имени (вместо renpy.input в новом контексте) ----------------
    # Раньше «ввод» прятал меню и открывал отдельный экран игры; теперь — окошко поверх меню:
    # Enter применяет, Esc закрывает, ошибка показывается тут же.
    class _TmEditValue(FieldInputValue):
        def enter(self):
            tm_edit_apply()
            return None

    tm_edit_iv = _TmEditValue(tm_ui, "edit_text", default=True, returnable=False)

    def tm_input(path):
        cur = tm_get(path)
        tm_ui.edit = ("value", path)
        tm_ui.edit_text = u"" if cur is None else tm_str(cur)
        tm_ui.edit_err = u""
        _tm_edit_focus()

    def tm_rename(path, cur_name):
        tm_ui.edit = ("name", path)
        tm_ui.edit_text = tm_str(cur_name)
        tm_ui.edit_err = u""
        _tm_edit_focus()

    def _tm_edit_focus():
        try:
            renpy.set_editable_input_value(tm_edit_iv, True)
        except Exception:
            pass
        renpy.restart_interaction()

    def tm_edit_close():
        if tm_ui.edit and tm_ui.edit[0] == "bug" and tm_ui.bug_shot:
            try:
                import os
                os.remove(tm_ui.bug_shot)       # заметку отменили — скриншот не нужен
            except Exception:
                pass
            tm_ui.bug_shot = None
        tm_ui.edit = None
        tm_ui.edit_err = u""
        renpy.restart_interaction()

    _TM_REL_RE = _tm_re.compile(u"^([-+*/×÷])\\s*(\\d+(?:[.,]\\d+)?)$")

    def tm_rel_value(cur, raw):
        # «+50», «-10», «*2», «/2» — от текущего значения; None — ввод не относительный
        m = _TM_REL_RE.match(raw)
        if not m:
            return None
        op, n = m.group(1), float(m.group(2).replace(",", "."))
        if op == u"+":
            v = cur + n
        elif op == u"-":
            v = cur - n
        elif op in (u"*", u"×"):
            v = cur * n
        else:
            v = cur / n
        return v if isinstance(cur, float) else int(round(v))

    def tm_parse_value(cur, raw):
        # текст -> значение того же типа, что сейчас; ValueError, если не разобрать
        if isinstance(cur, bool):
            low = raw.lower()
            if low in ("1", "true", u"да", "yes", "on", u"вкл"):
                return True
            if low in ("0", "false", u"нет", "no", "off", u"выкл"):
                return False
            raise ValueError(raw)
        if isinstance(cur, float):
            return float(raw.replace(",", "."))
        if isinstance(cur, _TM_NUM):
            try:
                return int(raw)                 # без потери точности на больших числах
            except ValueError:
                return int(float(raw.replace(",", ".")))
        return raw

    def tm_edit_apply():
        if not tm_ui.edit:
            return
        kind, path = tm_ui.edit
        raw = (tm_ui.edit_text or u"").strip()
        if kind == "name":
            tm_ui.edit = None
            tm_set_name(path, raw)
            return
        if kind == "char":
            tm_ui.edit = None
            tm_char_rename(path, raw)
            return
        if kind == "bug":
            tm_ui.edit = None
            tm_bug_save(raw)
            return
        if raw == "":
            tm_ui.edit_err = u"Пусто — введи значение или нажми Esc"
            renpy.restart_interaction()
            return
        cur = tm_get(path)
        if isinstance(cur, _TM_NUM) and not isinstance(cur, bool):
            if raw.startswith("="):
                raw = raw[1:].strip()           # «=-5» — точное значение, не «минус 5»
            else:
                try:
                    rel = tm_rel_value(cur, raw)
                except (ValueError, ZeroDivisionError, OverflowError):
                    tm_ui.edit_err = u"Не получилось: %s" % raw
                    renpy.restart_interaction()
                    return
                if rel is not None:
                    tm_ui.edit = None
                    tm_set(path, rel)
                    return
        try:
            val = tm_parse_value(cur, raw)
        except (ValueError, OverflowError):     # OverflowError: int(float("inf"))
            tm_ui.edit_err = (u"Нужно да/нет" if isinstance(cur, bool) else u"Не число: %s" % raw)
            renpy.restart_interaction()
            return
        tm_ui.edit = None
        tm_set(path, val)

    # ---------------- история выборов: что каждый выбор реально изменил ----------------
    # Обёртка над renpy.exports.menu (её вызывает оператор menu): до выбора — снимок значений,
    # после — на следующем взаимодействии сравнение. Работает на 6.99–8.x (аргументы — как есть).
    TM_HIST_MAX = 60

    def _tm_hist_finish(after=None):
        p = tm_ui.hist_pending
        tm_ui.hist_pending = None
        if not p:
            return
        text, where, before = p
        if after is None:
            try:
                after = tm_scan_collect("all")
            except Exception:
                return
        eff = []
        for k in sorted(after.keys()):
            if k in before:
                try:
                    if before[k] != after[k]:
                        eff.append((k, before[k], after[k]))
                except Exception:
                    pass
        tm_ui.history.append({"text": text, "where": where, "eff": eff[:16], "more": max(0, len(eff) - 16)})
        del tm_ui.history[:-TM_HIST_MAX]

    def _tm_menu_wrap(items, *args, **kwargs):
        snap = None
        if tm_pref("tm_history", True) and not store.main_menu:
            try:
                snap = tm_scan_collect("all")
            except Exception:
                snap = None
            if tm_ui.hist_pending:              # выбор сразу за выбором — прошлый закрываем этим снимком
                _tm_hist_finish(snap)
        rv = _TM_NOPICK
        if tm_ui.auto and not store.main_menu:
            try:
                rv = _tm_auto_menu(items, args, kwargs)
            except Exception as e:
                tm_auto_stop(u"ошибка выбора: %s" % e, "bad")
                rv = _TM_NOPICK
        if rv is _TM_NOPICK:
            rv = renpy.exports._tm_menu_orig(items, *args, **kwargs)
        raw = None
        for it in items:
            try:
                if rv is not None and it[-1] == rv and it[0]:
                    raw = it[0]
                    break
            except Exception:
                pass
        if raw is not None and not store.main_menu:
            _tm_route_add(raw)
        if snap is not None and raw is not None:
            try:
                fn, ln = renpy.get_filename_line()
                tm_ui.hist_pending = (_tm_short(tm_choice_text(raw), 50), tm_label_at(fn, ln) or u"", snap)
            except Exception:
                pass
        return rv

    def _tm_install_menu_wrap():
        try:
            ex = renpy.exports
            if getattr(ex, "_tm_menu_orig", None) is None:
                ex._tm_menu_orig = ex.menu
            ex.menu = _tm_menu_wrap
        except Exception:
            pass

    _tm_install_menu_wrap()

    def tm_eff_text(path, old, new):
        # «Anna | симпатия +2» / «флаг: выкл → ВКЛ» / «место: дом → парк»
        nice = tm_nice(path, path)[0]
        if (isinstance(old, _TM_NUM) and isinstance(new, _TM_NUM)
                and not isinstance(old, bool) and not isinstance(new, bool)):
            d = new - old
            if isinstance(d, float):
                d = round(d, 3)
            return (u"%s %s%s" % (nice, u"+" if d > 0 else u"−", tm_str(abs(d)))), ("up" if d > 0 else "down")
        if isinstance(new, bool):
            return u"%s: %s" % (nice, u"ВКЛ" if new else u"выкл"), "set"
        return u"%s: %s → %s" % (nice, _tm_short(old, 14), _tm_short(new, 14)), "set"

    def tm_hist_markup(h):
        # эффекты выбора цветом: рост — зелёным, падение — красным
        parts = []
        for p, o, n in h["eff"]:
            t, k = tm_eff_text(p, o, n)
            parts.append(u"{color=%s}%s{/color}" % (TM_HINT_COLORS.get(k, "#c7ccd4"), tm_q(t)))
        if h.get("more"):
            parts.append(u"… и ещё %d" % h["more"])
        return u"   ".join(parts)

    def tm_hist_clear():
        tm_ui.history = []
        renpy.restart_interaction()

    # ---------------- подсказки: условие скрытого варианта с текущими значениями ----------------
    def tm_cond_now(cond):
        # «сейчас: money = 40, met_anna = выкл» — значения имён из условия
        if not cond:
            return u""
        seen, parts = set(), []
        for m in _TM_COND_NAME.finditer(_tm_re.sub(r'"[^"]*"|\'[^\']*\'', "", cond)):
            name = m.group(1)
            if name in _TM_KEYWORDS or name.split(".")[0] in _TM_KEYWORDS or name in seen:
                continue
            seen.add(name)
            ok, v = tm_probe(name)
            if not ok or callable(v):
                continue
            parts.append(u"%s = %s" % (name, (u"ВКЛ" if v else u"выкл") if isinstance(v, bool) else _tm_short(v, 12)))
            if len(parts) >= 4:
                break
        return (u"сейчас: " + u", ".join(parts)) if parts else u""

    # ---------------- подсказки: режимы спойлеров ----------------
    TM_SPOIL_MODES = (("full", u"полностью"), ("sign", u"только знак"), ("click", u"по щелчку"))

    def tm_spoil():
        m = tm_pref("tm_spoil", "full")
        return m if m in dict(TM_SPOIL_MODES) else "full"

    def tm_set_spoil(m):
        store.persistent.tm_spoil = m
        renpy.restart_interaction()

    def tm_hint_sign(effs):
        # «только знак»: + − = → без имён и чисел
        if not effs:
            return u"{color=#5b6373}без изменений{/color}"
        sym = {"up": u"+", "down": u"−", "set": u"=", "call": u"ƒ", "go": u"→"}
        return u" ".join(u"{color=%s}%s{/color}" % (TM_HINT_COLORS.get(k, "#c7ccd4"), sym.get(k, u"-")) for k, _t in effs)

    def tm_peek_toggle(key):
        if key in tm_ui.peek:
            tm_ui.peek.discard(key)
        else:
            tm_ui.peek.add(key)
        renpy.restart_interaction()

    # ---------------- кнопки на экранах (call screen, карты, imagebutton) ----------------
    # Обход показанных экранов: кнопки и их действия (Jump, Call, SetVariable, SetField,
    # SetDict, Function, Return…). Показ эффекта и нажатие из меню.
    _TM_SCR_SKIP = ("say", "quick_menu", "notify", "nvl", "skip_indicator", "choice", "ctc",
                    "window", "_", "tm_", "tmtr", "zz_")

    def tm_screens():
        # [(имя экрана, displayable)] показанных экранов игры
        out = []
        try:
            sl = renpy.exports.scene_lists()
            layers = list(getattr(config, "layers", []) or []) + list(getattr(config, "top_layers", []) or [])
            for layer in layers:
                for e in sl.layers.get(layer, ()) or ():
                    d = getattr(e, "displayable", None)
                    nm = getattr(d, "screen_name", None)
                    if not nm:
                        continue
                    name = nm[0] if isinstance(nm, tuple) else nm
                    if not isinstance(name, _TM_STR) or name.startswith(_TM_SCR_SKIP):
                        continue
                    out.append((name, d))
        except Exception:
            pass
        return out

    def _tm_btn_label(d):
        # подпись кнопки: её текст, иначе имя картинки
        texts, imgs = [], []

        def walk(x, depth):
            if x is None or depth > 8 or len(texts) > 3:
                return
            t = getattr(x, "text", None)
            if isinstance(t, (_TM_LIST, tuple)) and t and isinstance(t[0], _TM_STR):
                texts.append(u"".join(s for s in t if isinstance(s, _TM_STR)))
                return
            nm = getattr(x, "name", None)
            if isinstance(nm, tuple) and nm and all(isinstance(s, _TM_STR) for s in nm):
                imgs.append(u" ".join(nm))
            fn = getattr(x, "filename", None)
            if isinstance(fn, _TM_STR):
                imgs.append(fn.split("/")[-1].rsplit(".", 1)[0])
            try:
                kids = x.visit()
            except Exception:
                kids = ()
            for k in kids or ():
                walk(k, depth + 1)

        walk(getattr(d, "child", None), 0)
        if texts:
            s = u" ".join(texts)
            try:
                s = renpy.filter_text_tags(s, allow=[])
            except Exception:
                pass
            return _tm_short(s, 34)
        if imgs:
            return _tm_short(imgs[0], 34)
        return u"кнопка"

    def tm_act_text(a, depth=0):
        # действие кнопки -> короткий понятный текст
        if a is None or depth > 3:
            return u""
        if isinstance(a, (_TM_LIST, tuple)):
            parts = [tm_act_text(x, depth + 1) for x in a]
            return u"; ".join(p for p in parts if p)
        cn = type(a).__name__
        g = lambda n: getattr(a, n, None)
        try:
            if cn == "Jump":
                return u"→ %s" % tm_str(g("label"))
            if cn == "Call":
                return u"call %s" % tm_str(g("label"))
            if cn == "Return":
                v = g("value")
                return u"вернуть %s" % _tm_short(v, 18) if v is not None else u"закрыть экран"
            if cn in ("SetField", "SetVariable"):
                obj, fld = g("object"), g("field") or g("name")
                own = obj is None or obj is renpy.store or getattr(obj, "__name__", "") in ("store", "renpy.store")
                tgt = tm_str(fld) if own else u"%s.%s" % (type(obj).__name__, tm_str(fld))
                return u"%s = %s" % (tgt, _tm_short(g("value"), 16))
            if cn in ("SetDict",):
                return u"[%s] = %s" % (_tm_short(g("key"), 14), _tm_short(g("value"), 16))
            if cn in ("SetScreenVariable", "SetLocalVariable"):
                return u"%s = %s (экран)" % (tm_str(g("name")), _tm_short(g("value"), 16))
            if cn.startswith("Toggle") and cn not in ("ToggleScreen",):
                return u"переключить %s" % tm_str(g("field") or g("variable") or g("name") or g("dict") or "")
            if cn in ("Show", "ShowMenu", "ShowTransient", "ToggleScreen", "Hide"):
                return u"экран %s" % tm_str(g("screen") or g("screen_name") or "")
            if cn == "Function":
                f = g("callable")
                fa = g("args") or ()
                return u"%s(%s)" % (getattr(f, "__name__", u"?"), _tm_short(u", ".join(tm_str(x) for x in fa), 24))
            if cn in ("NullAction", "With"):
                return u""
        except Exception:
            pass
        return cn

    def tm_screen_buttons(only=None, limit=60):
        # [(экран, подпись, действие-текст, действие, доступна?)]
        out = []

        def walk(d, scr, depth):
            if d is None or depth > 40 or len(out) >= limit:
                return
            if isinstance(d, renpy.display.behavior.Button):
                act = getattr(d, "action", None)
                if act is None:
                    act = getattr(d, "clicked", None)
                if act is not None:
                    try:
                        sens = bool(renpy.display.behavior.is_sensitive(act))
                    except Exception:
                        sens = True
                    txt = tm_act_text(act)
                    if txt:
                        out.append((scr, _tm_btn_label(d), txt, act, sens))
                return
            try:
                kids = d.visit()
            except Exception:
                return
            for k in kids or ():
                walk(k, scr, depth + 1)

        for name, d in tm_screens():
            if only and name != only:
                continue
            walk(d, name, 0)
        return out

    def tm_press(act):
        # нажать кнопку экрана из меню (возврат значения закрывает call screen, как обычный щелчок)
        tm_safety_save()
        store.tm_ui.open = False
        return renpy.display.behavior.run(act)

    def tm_cur_call_screen():
        # имя экрана, если игра стоит на `call screen` (развилка-карта, песочница)
        try:
            node = renpy.game.script.lookup(renpy.game.context().current)
        except Exception:
            return None
        line = (getattr(node, "line", "") or "") if isinstance(node, renpy.ast.UserStatement) else ""
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "call" and parts[1] == "screen":
            return parts[2].split("(")[0]
        return None

    # ---------------- чистка журнала отката от старых экранных переменных меню ----------------
    # Старые версии меню держали в переменных экранов узел сценария (_tm_node), действия кнопок
    # и словарь сканера. Они попали в журнал отката сейвов, и пересохранение такого сейва падало
    # с RecursionError. После загрузки заменяем эти значения на None (экран пересчитает сам).
    _TM_SCOPE_BAD = frozenset(("_tm_node", "_act", "_bs", "_sb", "_s", "_cands"))

    def _tm_scrub_bad(k, v):
        if isinstance(v, renpy.ast.Node):
            return True
        return k in _TM_SCOPE_BAD and not isinstance(v, (_TM_STR, _TM_NUM, type(None)))

    def _tm_scrub_log():
        n = 0
        try:
            log = renpy.game.log
            entries = list(getattr(log, "log", None) or [])
            if getattr(log, "current", None) is not None:
                entries.append(log.current)
        except Exception:
            return 0
        for rb in entries:
            for ent in list(getattr(rb, "objects", None) or []):
                try:
                    obj, state = ent[0], ent[1]
                except Exception:
                    continue
                if isinstance(obj, _TM_DICT):
                    for k in [k for k in list(obj.keys()) if isinstance(k, _TM_STR) and _tm_scrub_bad(k, obj[k])]:
                        _TM_DICT.__setitem__(obj, k, None)
                        n += 1
                if isinstance(state, _TM_LIST):
                    for i, kv in enumerate(state):
                        if (isinstance(kv, tuple) and len(kv) == 2 and isinstance(kv[0], _TM_STR)
                                and _tm_scrub_bad(kv[0], kv[1])):
                            state[i] = (kv[0], None)
                            n += 1
        return n

    # ---------------- данные для экранов: только простые значения ----------------
    # Переменные экранов ($ x = ..., for x in ...) Ren'Py пишет в журнал отката и в сейв.
    # Узлы сценария, действия кнопок и большие словари туда класть нельзя: узел Menu тянет
    # по .next весь сценарий (RecursionError при сохранении), снимок сканера раздувает сейв.
    def tm_cur_menu_name():
        n = tm_cur_menu()
        return None if n is None else n.name

    def tm_menu_hints_name(name):
        try:
            node = renpy.game.script.lookup(name)
        except Exception:
            return []
        return tm_menu_hints(node) if isinstance(node, renpy.ast.Menu) else []

    def tm_screen_rows(only=None, limit=60, key=None):
        # [(номер, экран, подпись, действие-текст, доступна?)]; сами действия — в сессии
        rows = tm_screen_buttons(only, limit)
        if key:
            renpy.session["tm_btn_" + key] = [r[3] for r in rows]
        return [(i, r[0], r[1], r[2], r[4]) for i, r in enumerate(rows)]

    def tm_press_n(key, n):
        acts = renpy.session.get("tm_btn_" + key) or []
        if n >= len(acts):
            tm_note(u"Кнопка уже не на экране", "warn")
            return
        return tm_press(acts[n])

    def tm_scan_view():
        # сводка сканера для экрана: до 80 строк (путь, было, стало)
        s = _tm_scan()
        cands = s["cands"]
        rows = []
        if len(cands) <= 80:
            rows = [(p, s["old"].get(p), s["cur"].get(p)) for p in cands]
        return {"mode": s["mode"], "hist": bool(s.get("hist")), "msg": s["msg"],
                "n": len(cands), "rows": rows}

    # ---------------- «Где я» ----------------
    def tm_where_info():
        # [(заголовок, текст)] — место в сценарии, стек вызовов, экраны, последний выбор
        out = []
        try:
            fn, ln = renpy.get_filename_line()
            lbl = tm_label_at(fn, ln)
            out.append((u"Место", u"%s : %s%s" % (fn, ln, (u"   метка " + lbl) if lbl else u"")))
        except Exception as e:
            out.append((u"Место", u"не удалось: %s" % e))
        try:
            node = renpy.game.script.lookup(renpy.game.context().current)
            if isinstance(node, renpy.ast.Say):
                out.append((u"Реплика", _tm_short((node.who + u": " if node.who else u"") + (node.what or u""), 90)))
            else:
                out.append((u"Оператор", type(node).__name__ + (u"  " + _tm_short(getattr(node, "line", u""), 60) if getattr(node, "line", None) else u"")))
        except Exception:
            pass
        stack = []
        try:
            for name in reversed(renpy.get_return_stack()):
                try:
                    n = renpy.game.script.lookup(name)
                    lb = tm_label_at(n.filename, n.linenumber)
                    stack.append(u"%s:%d%s" % (n.filename.split("/")[-1], n.linenumber, (u" (" + lb + u")") if lb else u""))
                except Exception:
                    stack.append(tm_str(name))
        except Exception:
            pass
        out.append((u"Стек call", u"  ←  ".join(stack) if stack else u"пуст (сцена не вызвана через call)"))
        scr = [n for n, _d in tm_screens()]
        out.append((u"Экраны", u", ".join(scr) if scr else u"только стандартные"))
        imgs, snd = tm_scene_now()
        out.append((u"Картинки", imgs or u"нет"))
        if snd:
            out.append((u"Звук", snd))
        if tm_ui.history:
            h = tm_ui.history[-1]
            out.append((u"Последний выбор", u"«%s»%s" % (h["text"], (u" в " + h["where"]) if h["where"] else u"")))
        if tm_ui.frozen:
            out.append((u"Заморожено", u", ".join(u"%s %s %s" % (tm_nice(p, p)[0], tm_freeze_sign(p), tm_str(v))
                                                  for p, v in tm_ui.frozen.items())))
        return out

    def tm_where_am_i():
        tm_ui.where_open = True
        renpy.restart_interaction()

    # ---------------- повтор сцены (Replay) ----------------
    def tm_replay(name):
        # сцена проигрывается в отдельном контексте; переменные игры потом возвращаются как были
        name = (name or "").strip()
        if not renpy.has_label(name):
            tm_note(u"Метки нет: %s" % name, "warn")
            return
        store.tm_ui.open = False
        try:
            (getattr(renpy, "call_replay", None) or renpy.game.call_replay)(name)
        except Exception as e:
            tm_note(u"Повтор: %s" % e, "bad")

    def tm_label_go(name):
        if tm_ui.jump_mode == "replay":
            tm_replay(name)
        else:
            tm_jump(name)

    # ---------------- отчёт тестера ----------------
    def tm_report_text():
        import time
        L = []
        L.append(u"Отчёт тест-меню: %s" % tm_str(getattr(store, "tm_title", u"")))
        L.append(u"%s   %s" % (tm_engine_tag(), time.strftime("%Y-%m-%d %H:%M:%S")))
        L.append(u"")
        L.append(u"== Где я")
        for t, v in tm_where_info():
            L.append(u"  %s: %s" % (t, v))
        L.append(u"")
        L.append(u"== История выборов (%d)" % len(tm_ui.history))
        for h in tm_ui.history:
            L.append(u"  «%s»%s" % (h["text"], (u"  [" + h["where"] + u"]") if h["where"] else u""))
            for p, o, n in h["eff"]:
                L.append(u"      %s   (%s: %s -> %s)" % (tm_eff_text(p, o, n)[0], p, tm_str(o), tm_str(n)))
            if h.get("more"):
                L.append(u"      … и ещё %d" % h["more"])
        L.append(u"")
        L.append(u"== Журнал изменений (%d)" % len(getattr(tm_ui, "changelog", [])))
        for _t, _n, _ch, _who, _wh in reversed(tm_log_rows(TM_LOG_MAX)):
            L.append(u"  %s  %s: %s  [%s]%s" % (_t, _n, _ch, _who, (u"  @" + _wh) if _wh else u""))
        L.append(u"")
        cov = tm_coverage()
        L.append(u"== Покрытие (за все партии на этом компьютере)")
        L.append(u"  реплики: %s;  сцены: %s;  варианты выбора: %s"
                 % (tm_cov_text(cov["say"]), tm_cov_text(cov["label"]), tm_cov_text(cov["choice"])))
        L.append(u"")
        L.append(u"== Маршрут этой партии (%s): %d выборов"
                 % (u"с начала игры" if tm_ui.route_start == "start" else u"с загрузки сейва", tm_route_now()))
        for r in tm_ui.route_rec:
            L.append(u"  «%s»" % _tm_short(tm_choice_text(r[0]), 70))
        if tm_ui.auto_log:
            L.append(u"")
            L.append(u"== Последнее авто-прохождение")
            for x in tm_ui.auto_log:
                L.append(u"  " + x)
        nb = tm_bug_count()
        if nb:
            L.append(u"")
            L.append(u"== Заметки о багах: %d (tm_bugs/tm_bugs.md)" % nb)
        L.append(u"")
        L.append(u"== Правки из меню (%d)" % len(tm_ui.journal))
        for p, o, n in tm_ui.journal:
            L.append(u"  %s: %s -> %s" % (p, tm_str(o), tm_str(n)))
        L.append(u"")
        L.append(u"== Избранное и HUD")
        for p in list(tm_ui.favs) + [w[1] for w in tm_ui.watch if w[1] not in tm_ui.favs]:
            ok, v = tm_probe(p)
            L.append(u"  %s = %s   (%s)" % (tm_nice(p, p)[0], tm_str(v) if ok else u"нет", p))
        return u"\n".join(L) + u"\n"

    def tm_write_report():
        import io, os, time
        try:
            base = getattr(config, "basedir", ".") or "."
            path = os.path.join(base, time.strftime("tm_report_%Y%m%d_%H%M%S.txt"))
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(tm_report_text())
            tm_note(u"Отчёт: " + path)
        except Exception as e:
            tm_note(u"Не удалось записать отчёт: %s" % e, "bad")

    # ---------------- клавиши меню ----------------
    # Shift+T — всегда; запасная клавиша выбирается (F9 у UnRen и многих игр — быстрая загрузка).
    # (F7/F8 у Ren'Py — профилирование в режиме разработчика, F11 — полный экран)
    TM_ALT_KEYS = ((u"F9", "K_F9"), (u"F10", "K_F10"), (u"F6", "K_F6"), (u"нет", ""))

    def _tm_key_taken(k):
        try:
            for name, keys in config.keymap.items():
                if name != "tm_toggle_key" and keys and k in keys:
                    return True
        except Exception:
            pass
        return False

    def tm_alt_key():
        k = tm_pref("tm_alt_key", None)
        if k is not None:
            return k
        for k in ("K_F9", "K_F10"):        # F9 занята игрой (UnRen: быстрая загрузка) — F10
            if not _tm_key_taken(k):
                return k
        return ""

    def tm_keys_text():
        k = tm_alt_key()
        return u"Shift+T" + ((u" / " + k[2:]) if k else u"")

    def tm_set_alt_key(k):
        store.persistent.tm_alt_key = k
        tm_register()
        renpy.restart_interaction()

    # ---------------- мини-режим ----------------
    def tm_minimize():
        tm_ui.open = False
        tm_ui.mini = True
        renpy.restart_interaction()

    def tm_unminimize():
        tm_ui.mini = False
        _tm_open_menu()

    # ---------------- HUD: угол и вспышки изменений ----------------
    TM_HUD_CORNERS = (("tl", u"слева сверху"), ("tr", u"справа сверху"), ("bl", u"слева снизу"), ("br", u"справа снизу"))

    def tm_hud_corner():
        c = tm_pref("tm_hud_corner", "tr")
        return c if c in dict(TM_HUD_CORNERS) else "tr"

    def tm_set_hud_corner(c):
        store.persistent.tm_hud_corner = c
        renpy.restart_interaction()

    def _tm_hud_track():
        # на каждом взаимодействии: что из HUD изменилось с прошлого раза -> вспышка «+2»
        tm_ui.tick += 1
        for _l, p in tm_ui.watch:
            ok, v = tm_probe(p)
            if not ok:
                continue
            last = tm_ui.hud_last.get(p)
            tm_ui.hud_last[p] = v
            if (last is not None and isinstance(v, _TM_NUM) and isinstance(last, _TM_NUM)
                    and not isinstance(v, bool) and v != last):
                d = v - last
                if isinstance(d, float):
                    d = round(d, 3)
                tm_ui.hud_flash[p] = (d, tm_now())

    def tm_hud_flash(p):
        f = tm_ui.hud_flash.get(p)
        if not f or tm_now() - f[1] > 2.8:
            return None
        d = f[0]
        return ((u"+%s" % tm_str(d)) if d > 0 else (u"−%s" % tm_str(-d)), "#5ad469" if d > 0 else "#ff6b6b")

    # ---------------- состояние меню между запусками: game/tm_state.json ----------------
    # Избранное, HUD, шаг, вкладка, позиция окна, добавленные из «Поиска» — в файле рядом
    # с игрой (не в persistent и не в сейвах; удаление меню убирает и его).
    def _tm_state_path():
        import os
        return os.path.join(config.gamedir, "tm_state.json")

    def _tm_state_dict():
        return {"favs": list(tm_ui.favs), "watch": [list(w) for w in tm_ui.watch],
                "hud_on": bool(tm_ui.hud_on), "step": tm_ui.stat_step, "tab": tm_ui.tab,
                "win_pos": list(tm_ui.win_pos) if tm_ui.win_pos else None,
                "extra": [list(e) for e in tm_ui.extra], "jump_mode": tm_ui.jump_mode,
                "routes": list(tm_ui.routes), "chars": dict(tm_ui.char_names),
                "auto_mode": tm_ui.auto_mode, "auto_limit": tm_ui.auto_limit,
                "profile": tm_ui.profile}

    def _tm_state_load():
        import io, json, os
        try:
            p = _tm_state_path()
            if not os.path.exists(p):
                return
            with io.open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            return
        if not isinstance(d, _TM_DICT):
            return
        try:
            tm_ui.favs = [x for x in d.get("favs") or [] if isinstance(x, _TM_STR)]
            tm_ui.watch = [tuple(w) for w in d.get("watch") or [] if len(w) == 2][:12]
            tm_ui.hud_on = bool(d.get("hud_on", True))
            if d.get("step") in (1, 5, 10, 50):
                tm_ui.stat_step = d["step"]
            if d.get("tab") in ("rewind", "stats", "actions", "scanner", "story", "checklist", "settings"):
                tm_ui.tab = d["tab"]
            wp = d.get("win_pos")
            tm_ui.win_pos = (int(wp[0]), int(wp[1])) if wp and len(wp) == 2 else None
            tm_ui.extra = [tuple(e) for e in d.get("extra") or [] if len(e) == 2]
            if d.get("jump_mode") in ("jump", "replay"):
                tm_ui.jump_mode = d["jump_mode"]
            tm_ui.routes = [r for r in d.get("routes") or []
                            if isinstance(r, _TM_DICT) and isinstance(r.get("choices"), _TM_LIST)][-12:]
            ch = d.get("chars") or {}
            tm_ui.char_names = dict((k, v) for k, v in ch.items()
                                    if isinstance(k, _TM_STR) and isinstance(v, _TM_STR)) if isinstance(ch, _TM_DICT) else {}
            if d.get("auto_mode") in ("new", "random", "first"):
                tm_ui.auto_mode = d["auto_mode"]
            if d.get("auto_limit") in (10, 30, 100, 0):
                tm_ui.auto_limit = d["auto_limit"]
            _tm_profile_load(d.get("profile"))
        except Exception:
            pass
        tm_ui.state_sig = _tm_state_json()

    # ---------------- профиль игры: заморозки, которые ставятся сами при каждом запуске ----------------
    def _tm_profile_load(pr):
        if not isinstance(pr, _TM_DICT):
            return
        fr = pr.get("frozen") or {}
        md = pr.get("modes") or {}
        if not isinstance(fr, _TM_DICT) or not isinstance(md, _TM_DICT):
            return
        fr = dict((k, v) for k, v in fr.items() if isinstance(k, _TM_STR) and isinstance(v, (_TM_NUM, _TM_STR)))
        tm_ui.profile = {"frozen": fr, "modes": dict((k, v) for k, v in md.items() if k in fr and v in ("eq", "ge", "le"))}
        for k, v in fr.items():
            tm_ui.frozen.setdefault(k, v)
            tm_ui.freeze_mode.setdefault(k, tm_ui.profile["modes"].get(k, "eq"))

    def tm_profile_save():
        tm_ui.profile = {"frozen": dict(tm_ui.frozen), "modes": dict(tm_ui.freeze_mode)}
        _tm_state_save()
        tm_note(u"Профиль: %d заморозок будут ставиться сами при каждом запуске" % len(tm_ui.frozen), "ok")
        renpy.restart_interaction()

    def tm_profile_clear():
        tm_ui.profile = {}
        _tm_state_save()
        tm_note(u"Профиль игры удалён (текущие заморозки остались)", "ok")
        renpy.restart_interaction()

    def tm_profile_size():
        return len((getattr(tm_ui, "profile", None) or {}).get("frozen") or {})

    def _tm_state_json():
        import json
        try:
            return tm_str(json.dumps(_tm_state_dict(), ensure_ascii=True, sort_keys=True, indent=1))
        except Exception:
            return None

    def _tm_state_save():
        s = _tm_state_json()
        if s is None or s == tm_ui.state_sig:
            return
        tm_ui.state_sig = s
        try:
            import io
            with io.open(_tm_state_path(), "w", encoding="utf-8") as f:
                f.write(s)
        except Exception:
            pass

    # ---------------- убрать следы меню (перед удалением) ----------------
    def tm_purge():
        # быстрые слоты, tm_state.json, ключи persistent.tm_* (оформление, справка, клавиша)
        n = 0
        for i in (0, 1, 2, 3):
            try:
                if renpy.can_load("tm_quick_%d" % i):
                    renpy.unlink_save("tm_quick_%d" % i)
                    n += 1
            except Exception:
                pass
        try:
            import os
            if os.path.exists(_tm_state_path()):
                os.remove(_tm_state_path())
                n += 1
        except Exception:
            pass
        try:
            for k in list(vars(store.persistent).keys()):
                if isinstance(k, _TM_STR) and k.startswith("tm_") and k != "tm_names":
                    setattr(store.persistent, k, None)
                    n += 1
            renpy.save_persistent()
        except Exception:
            pass
        for var in list(tm_ui.char_names.keys()):
            tm_char_rename(var, u"")             # вернуть персонажам их имена
        tm_ui.favs = []; tm_ui.watch = []; tm_ui.extra = []; tm_ui.slots = None
        tm_ui.routes = []
        tm_ui.state_sig = _tm_state_json()     # не писать файл заново сразу после удаления
        tm_note(u"Следы меню убраны: %d. Свои имена переменных (tm_names.json) оставлены." % n)

