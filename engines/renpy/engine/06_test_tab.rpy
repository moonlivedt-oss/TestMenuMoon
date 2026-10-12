# ==================== вкладка «Тест»: авто-прохождение, маршруты, покрытие, сцены ====================
init -3 python:
    import os as _tm_os

    def _tm_own(n):
        # узел из скриптов самой игры (не Ren'Py, не меню, не переводы tl/)
        fn = getattr(n, "filename", "") or ""
        return not (fn.startswith("renpy/") or "zzz_testmenu" in fn or fn.startswith("tl/") or "/tl/" in fn)

    # ---------------- авто-прохождение ----------------
    # Меню проматывает текст скипом и само отвечает на выборы (обёртка _tm_menu_wrap).
    # Сторож (_tm_auto_watch, ~20 раз в секунду) останавливает его, если игра стоит на месте:
    # экран-развилка (call screen), ввод имени, долгая пауза — дальше нужен игрок.
    _TM_NOPICK = object()
    TM_AUTO_MODES = (("new", u"новые варианты"), ("random", u"случайно"), ("first", u"первый"))
    TM_AUTO_LIMITS = ((10, u"10"), (30, u"30"), (100, u"100"), (0, u"без лимита"))
    TM_AUTO_STALL = 6.0

    def tm_auto_start(route=None, name=u""):
        if store.main_menu:
            tm_note(u"Авто-прохождение работает в самой игре", "warn")
            return
        tm_ui.auto = {"route": list(route) if route is not None else None, "name": name,
                      "mode": tm_ui.auto_mode, "left": 0 if route is not None else int(tm_ui.auto_limit or 0),
                      "stop_label": u"" if route is not None else (tm_ui.auto_stop_label or u"").strip(),
                      "stop_unseen": route is None and bool(tm_ui.auto_stop_unseen),
                      "picked": 0, "node": None, "t": tm_now()}
        tm_ui.auto_log = []
        tm_safety_save()
        tm_ui.open = False
        tm_note((u"Маршрут «%s»: пошёл" % name) if route is not None
                else u"Авто-прохождение: пошло (%s — стоп)" % tm_keys_text())
        tm_start_skip("fast")

    def tm_auto_stop(reason=u"", kind="ok"):
        a = tm_ui.auto
        if a is None:
            return
        tm_ui.auto = None
        try:
            renpy.config.skipping = None
        except Exception:
            pass
        msg = (u"Маршрут «%s» остановлен" % a["name"]) if a.get("route") is not None else u"Авто-прохождение остановлено"
        if a.get("picked"):
            msg += u", выборов: %d" % a["picked"]
        if reason:
            msg += u" — " + reason
        tm_ui.auto_log.append(msg)
        tm_note(msg, kind)

    def tm_auto_badge_text():
        a = tm_ui.auto or {}
        if a.get("route") is not None:
            return u"Маршрут «%s»: осталось выборов %d" % (_tm_short(a.get("name") or u"", 30), len(a["route"]))
        return u"Авто-прохождение: выборов %d%s" % (a.get("picked", 0), (u" из %d" % a["left"]) if a.get("left") else u"")

    def _tm_where_short():
        try:
            fn, ln = renpy.get_filename_line()
            lab = tm_label_at(fn, ln)
            return u" (%s:%d%s)" % (fn.split("/")[-1], ln, (u", " + lab) if lab else u"")
        except Exception:
            return u""

    def _tm_auto_menu(items, args, kwargs):
        # -> значение выбранного варианта или _TM_NOPICK (игра покажет выбор сама)
        a = tm_ui.auto
        set_expr = args[0] if args else kwargs.get("set_expr")
        st = None
        if set_expr:
            try:
                st = renpy.python.py_eval(set_expr)
            except Exception:
                st = None
        cands = []
        for it in items:
            try:
                label, cond, value = it[0], it[1], it[-1]
            except Exception:
                continue
            if value is None or not label or (st is not None and label in st):
                continue
            try:
                if not renpy.python.py_eval(cond):
                    continue
            except Exception:
                continue
            cands.append((label, value))
        if not cands:
            return _TM_NOPICK
        try:
            loc = renpy.game.context().current
        except Exception:
            loc = None
        if a.get("route") is not None:
            want = a["route"][0] if a["route"] else u""
            pick = None
            for c in cands:
                if c[0] == want or tm_choice_text(c[0]) == tm_choice_text(want):
                    pick = c
                    break
            if pick is None:
                tm_auto_stop(u"маршрут разошёлся: нет варианта «%s»%s"
                             % (_tm_short(tm_choice_text(want), 40), _tm_where_short()), "warn")
                return _TM_NOPICK
            a["route"].pop(0)
        else:
            import random as _tm_rnd
            if a["mode"] == "first":
                pick = cands[0]
            else:
                pool = cands
                if a["mode"] == "new":
                    # сначала варианты, которых ещё ни разу не выбирали (за все партии)
                    ch = getattr(renpy.game.persistent, "_chosen", None) or {}
                    pool = [c for c in cands if (loc, c[0]) not in ch] or cands
                pick = _tm_rnd.choice(pool)
        label, value = pick
        # как при обычном щелчке: вариант помечается выбранным, menu set пополняется
        try:
            ch = renpy.game.persistent._chosen
            if ch is None:
                ch = renpy.game.persistent._chosen = {}
            if loc is not None:
                ch[(loc, label)] = True
        except Exception:
            pass
        if st is not None:
            try:
                st.append(label)
            except AttributeError:
                try:
                    st.add(label)
                except Exception:
                    pass
        a["picked"] += 1
        a["node"], a["t"] = None, tm_now()
        tm_ui.auto_log.append(u"«%s»%s" % (_tm_short(tm_choice_text(label), 50), _tm_where_short()))
        del tm_ui.auto_log[:-40]
        if a.get("route") is not None:
            if not a["route"]:
                tm_auto_stop(u"маршрут пройден")
        elif a["left"] and a["picked"] >= a["left"]:
            tm_auto_stop(u"лимит выборов")
        return value

    def _tm_auto_watch():
        a = tm_ui.auto
        if not a:
            return
        if store.main_menu:
            tm_auto_stop(u"игра вышла в главное меню", "warn")
            return
        try:
            cur = renpy.game.context().current
        except Exception:
            return
        now = tm_now()
        if cur != a["node"]:
            a["node"], a["t"] = cur, now
            return
        if now - a["t"] > TM_AUTO_STALL:
            cs = tm_cur_call_screen()
            tm_auto_stop(u"игра ждёт игрока" + ((u" на экране " + cs) if cs else u"") + _tm_where_short(), "warn")

    def _tm_auto_interact():
        # на каждом взаимодействии: скип держим включённым, стоп на новой реплике
        a = tm_ui.auto
        if not a or store.main_menu:
            return
        if a.get("stop_unseen"):
            try:
                node = renpy.game.script.lookup(renpy.game.context().current)
                if isinstance(node, renpy.ast.Say) and _tm_own(node) and not renpy.is_seen(ever=True):
                    tm_auto_stop(u"новая реплика" + _tm_where_short())
                    return
            except Exception:
                pass
        try:
            if not renpy.config.skipping:
                tm_enable_skip()
                renpy.config.skipping = "fast"
        except Exception:
            pass

    def _tm_on_label(name, abnormal=False):
        try:
            if name == "start":                 # новая игра — маршрут пишется заново
                tm_ui.route_rec = []
                tm_ui.route_start = "start"
            a = tm_ui.auto
            if a and a.get("stop_label") and name == a["stop_label"]:
                tm_auto_stop(u"дошли до метки " + name)
        except Exception:
            pass

    def _tm_label_chain(name, abnormal):
        # старые Ren'Py: config.label_callback одна функция — встаём в цепочку перед чужой
        _tm_on_label(name, abnormal)
        prev = tm_ui.label_prev
        if prev is not None and prev is not _tm_label_chain:
            prev(name, abnormal)

    # ---------------- маршруты: запись выборов партии и прохождение по записи ----------------
    def _tm_log_id():
        try:
            return renpy.game.log.current.identifier
        except Exception:
            return None

    def _tm_route_prune():
        # откат назад за выбор: его точки отката в журнале больше нет (а журнал не обрезан с начала)
        rec = tm_ui.route_rec
        if not rec:
            return
        try:
            log = renpy.game.log.log
            ids = set(getattr(r, "identifier", None) for r in log)
            first = getattr(log[0], "identifier", None) if log else None
        except Exception:
            return
        while rec and first is not None:
            i = rec[-1][1]
            if i is None or i in ids:
                break
            try:
                if not (i > first):
                    break
            except Exception:
                break
            rec.pop()

    def _tm_route_add(raw):
        _tm_route_prune()
        tm_ui.route_rec.append((raw, _tm_log_id()))
        del tm_ui.route_rec[:-500]

    def tm_route_now():
        _tm_route_prune()
        return len(tm_ui.route_rec)

    def tm_route_save():
        _tm_route_prune()
        ch = [tm_str(r[0]) for r in tm_ui.route_rec]
        if not ch:
            tm_note(u"В этой партии ещё не было выборов", "warn")
            return
        try:
            fn, ln = renpy.get_filename_line()
            lab = tm_label_at(fn, ln) or u"маршрут"
        except Exception:
            lab = u"маршрут"
        name = u"%s | %d выб." % (lab, len(ch))
        tm_ui.routes.append({"name": name, "choices": ch, "start": tm_ui.route_start or "save"})
        del tm_ui.routes[:-12]
        tm_note(u"Маршрут сохранён: " + name)

    def tm_route_play(i):
        try:
            r = tm_ui.routes[i]
        except Exception:
            return
        tm_auto_start(route=r["choices"], name=r["name"])

    def tm_route_del(i):
        try:
            del tm_ui.routes[i]
        except Exception:
            pass
        renpy.restart_interaction()

    def tm_route_rows():
        # [(номер, имя, начало маршрута, откуда)] — для экрана, без самих списков выборов
        return [(i, tm_str(r.get("name", u"")), tm_route_preview(r), r.get("start")) for i, r in enumerate(tm_ui.routes)]

    def tm_route_preview(r, n=3):
        ch = r.get("choices") or []
        s = u" → ".join(_tm_short(tm_choice_text(c), 22) for c in ch[:n])
        return s + (u" → …" if len(ch) > n else u"")

    # ---------------- покрытие: что уже видели на этом компьютере ----------------
    # persistent._seen_ever — просмотренные реплики и метки (за все партии), _chosen — выбранные
    # варианты. Пересчёт — только когда они изменились.
    def tm_coverage():
        p = renpy.game.persistent
        seen = getattr(p, "_seen_ever", None) or {}
        chosen = getattr(p, "_chosen", None) or {}
        key = (len(seen), len(chosen))
        c = renpy.session.get("tm_cov")
        if c is not None and c[0] == key:
            return c[1]
        says, labs, chs = [0, 0], [0, 0], [0, 0]
        scenes = []
        done = set()
        # Ren'Py 8.4+ (config.hash_seen) хранит не имя узла, а его 64-битный хеш
        h64 = getattr(getattr(renpy, "astsupport", None), "hash64", None)

        def is_seen(k):
            if k in seen:
                return True
            if h64 is not None:
                try:
                    return h64(k) in seen
                except Exception:
                    return False
            return False

        # игра на переводе: Ren'Py отмечает просмотренными узлы перевода (tl/<язык>/...),
        # а не оригинальные реплики — реплика просмотрена, если просмотрен её перевод на любом языке
        tl_seen = set()
        try:
            for (ident, _lang), tnode in renpy.game.script.translator.language_translates.items():
                # 8.x: перевод — сам узел TranslateSay; старые версии — Translate с блоком внутри
                if any(is_seen(b.name) for b in [tnode] + list(getattr(tnode, "block", None) or ())):
                    tl_seen.add(ident)
        except Exception:
            pass
        ident_of = {}                       # старый вид (до 8.x): Say внутри узла Translate

        for n in _tm_script_nodes():
            if id(n) in done:
                continue
            done.add(id(n))
            try:
                if not _tm_own(n):
                    continue
                if isinstance(n, renpy.ast.Translate) and getattr(n, "language", None) is None:
                    for b in n.block or ():
                        ident_of[id(b)] = n.identifier
                    continue
                if isinstance(n, renpy.ast.Say):
                    says[1] += 1
                    ident = getattr(n, "identifier", None) or ident_of.get(id(n))
                    says[0] += int(is_seen(n.name) or (ident is not None and ident in tl_seen))
                elif isinstance(n, renpy.ast.Label):
                    nm = n.name
                    if not isinstance(nm, _TM_STR) or nm.startswith("_"):
                        continue
                    s = is_seen(nm)
                    labs[1] += 1
                    labs[0] += int(s)
                    scenes.append((nm, n.filename, n.linenumber, s))
                elif isinstance(n, renpy.ast.Menu):
                    for item in n.items:
                        if item[0] and item[2] is not None:
                            chs[1] += 1
                            chs[0] += int((n.name, item[0]) in chosen)
            except Exception:
                continue
        scenes.sort(key=lambda s: (s[1], s[2]))
        res = {"say": says, "label": labs, "choice": chs, "scenes": scenes}
        renpy.session["tm_cov"] = (key, res)
        return res

    def tm_cov_text(pair):
        a, b = pair
        return (u"%d%%  (%d из %d)" % (100 * a // b, a, b)) if b else u"—"

    def tm_cov_part(pair):
        return (float(pair[0]) / pair[1]) if pair[1] else 0.0

    def tm_scene_rows(q, show_all, limit=40):
        # [(метка, файл:строка, просмотрена)] и сколько всего подходит
        q = (q or "").strip().lower()
        rows = [s for s in tm_coverage()["scenes"] if (show_all or not s[3]) and (not q or q in s[0].lower())]
        return [(s[0], u"%s:%d" % (s[1].split("/")[-1], s[2]), s[3]) for s in rows[:limit]], len(rows)

    def tm_scene_toggle(name):
        tm_ui.scene_open = u"" if tm_ui.scene_open == name else name
        renpy.restart_interaction()

    # ---------------- «откуда сюда попадают»: обратные ссылки на метку ----------------
    def _tm_refs():
        r = renpy.session.get("tm_refs")
        if r is not None:
            return r
        r = {}
        ctx = {}

        def mark(block, text):
            for b in block or ():
                ctx[id(b)] = text

        # all_stmts — в порядке «узел, потом его дети»: условие внешнего блока уже известно
        for n in _tm_script_nodes():
            try:
                if not _tm_own(n):
                    continue
                base = ctx.get(id(n))
                pre = (base + u" → ") if base else u""
                if isinstance(n, renpy.ast.Menu):
                    for item in n.items:
                        if item[0] and item[2] is not None:
                            t = u"выбор «%s»" % _tm_short(tm_choice_text(item[0]), 30)
                            if item[1] and item[1].strip() != "True":
                                t += u" (если %s)" % _tm_short(item[1], 30)
                            mark(item[2], pre + t)
                elif isinstance(n, renpy.ast.If):
                    for cond, blk in n.entries:
                        c = (cond or "True").strip()
                        mark(blk, pre + (u"иначе" if c == "True" else u"если " + _tm_short(c, 36)))
                elif isinstance(n, renpy.ast.While):
                    mark(n.block, pre + u"пока " + _tm_short(n.condition, 30))
                elif isinstance(n, (renpy.ast.Jump, renpy.ast.Call)):
                    if n.expression:
                        continue
                    call = isinstance(n, renpy.ast.Call)
                    tgt = n.label if call else n.target
                    lst = r.setdefault(tgt, [])
                    if len(lst) < 12:
                        lst.append((u"call" if call else u"jump", tm_label_at(n.filename, n.linenumber) or u"?",
                                    base or u"", u"%s:%d" % (n.filename.split("/")[-1], n.linenumber)))
            except Exception:
                continue
        renpy.session["tm_refs"] = r
        return r

    def tm_scene_refs(name):
        # [(текст строки)] — откуда переходят на метку и при каком условии
        out = []
        for kind, frm, cond, where in _tm_refs().get(name, ()):
            out.append(u"%s из %s%s  | %s" % (kind, frm, (u": " + cond) if cond else u"", where))
        return out

    # ---------------- код варианта выбора (что стоит за ним в сценарии) ----------------
    def _tm_code_lines(block, out, ind, depth, limit):
        for n in block or ():
            if len(out) >= limit:
                if out and out[-1] != u"…":
                    out.append(u"…")
                return
            try:
                if isinstance(n, renpy.ast.Python):
                    src = [l.rstrip() for l in (n.code.source or u"").splitlines() if l.strip()]
                    if len(src) == 1:
                        out.append(ind + u"$ " + src[0].strip())
                    else:
                        out.append(ind + u"python:")
                        out.extend(ind + u"    " + l for l in src[:6])
                elif isinstance(n, renpy.ast.Say):
                    out.append(ind + ((n.who + u" ") if n.who else u"") + u'"%s"' % _tm_short(n.what or u"", 44))
                elif isinstance(n, renpy.ast.If):
                    for k, (cond, blk) in enumerate(n.entries):
                        c = (cond or "True").strip()
                        head = u"else:" if (c == "True" and k) else u"%s %s:" % (u"elif" if k else u"if", c)
                        out.append(ind + head)
                        if depth < 3:
                            _tm_code_lines(blk, out, ind + u"    ", depth + 1, limit)
                elif isinstance(n, renpy.ast.Jump):
                    out.append(ind + u"jump " + (u"expression " if n.expression else u"") + tm_str(n.target))
                elif isinstance(n, renpy.ast.Call):
                    out.append(ind + u"call " + (u"expression " if n.expression else u"") + tm_str(n.label))
                elif isinstance(n, renpy.ast.Return):
                    out.append(ind + u"return")
                elif isinstance(n, renpy.ast.Menu):
                    out.append(ind + u"menu: …")
                elif isinstance(n, renpy.ast.UserStatement):
                    out.append(ind + _tm_short(getattr(n, "line", u"") or u"", 60))
                elif isinstance(n, (renpy.ast.Show, renpy.ast.Scene)):
                    im = getattr(n, "imspec", None)
                    nm = u" ".join(im[0]) if im and im[0] else u""
                    out.append(ind + (u"scene " if isinstance(n, renpy.ast.Scene) else u"show ") + nm)
            except Exception:
                continue

    def tm_choice_code(node_name, i):
        # текст кода варианта i выбора node_name (кэш в сессии)
        cache = renpy.session.get("tm_code")
        if cache is None:
            cache = renpy.session["tm_code"] = {}
        key = (node_name, i)
        if key not in cache:
            out = []
            try:
                node = renpy.game.script.lookup(node_name)
                _tm_code_lines(node.items[i][2], out, u"", 0, 16)
            except Exception:
                pass
            cache[key] = u"\n".join(out) or u"(пусто)"
        return cache[key]

    def tm_code_toggle(key):
        if key in tm_ui.code_peek:
            tm_ui.code_peek.discard(key)
        else:
            tm_ui.code_peek.add(key)
        renpy.restart_interaction()

    # ---------------- «что на экране»: картинки и звук (для «Где я», отчёта, заметок) ----------------
    def tm_scene_now():
        imgs, snd = [], []
        try:
            layers = [l for l in (getattr(config, "layers", None) or ["master"])
                      if l not in ("screens", "overlay", "transient")]
            for layer in layers:
                for tag in renpy.get_showing_tags(layer):
                    try:
                        attrs = tuple(renpy.get_attributes(tag, layer) or ())
                    except Exception:
                        attrs = ()
                    s = u" ".join((tm_str(tag),) + tuple(tm_str(a) for a in attrs))
                    imgs.append(s if layer == "master" else u"%s: %s" % (layer, s))
        except Exception:
            pass
        for ch in ("music", "sound", "voice"):
            try:
                f = renpy.music.get_playing(channel=ch)
                if f:
                    snd.append(u"%s: %s" % (ch, tm_str(f).split("/")[-1]))
            except Exception:
                pass
        return u", ".join(imgs[:12]), u", ".join(snd)

    # ---------------- заметка о баге: текст + место + картинки + скриншот ----------------
    # Shift+B или кнопка: окно меню прячется, через кадр снимается экран игры, затем
    # открывается окно ввода. Всё пишется в <папка игры>/tm_bugs/tm_bugs.md.
    def _tm_bug_dir():
        d = _tm_os.path.join(getattr(config, "basedir", ".") or ".", "tm_bugs")
        if not _tm_os.path.isdir(d):
            _tm_os.makedirs(d)
        return d

    def tm_bug_request():
        if store.main_menu or getattr(store, "_menu", False):
            tm_note(u"Заметка о баге — в самой игре", "warn")
            return
        tm_ui.open = False
        tm_ui.bug_pending = True
        renpy.restart_interaction()

    def tm_bug_capture():
        import time
        tm_ui.bug_pending = False
        shot = None
        try:
            shot = _tm_os.path.join(_tm_bug_dir(), time.strftime("bug_%Y%m%d_%H%M%S.png"))
            renpy.screenshot(shot)
            if not _tm_os.path.exists(shot):
                shot = None
        except Exception:
            shot = None
        tm_ui.bug_shot = shot
        _tm_open_menu()
        if tm_ui.open:
            tm_ui.help_open = False
            tm_ui.edit = ("bug", u"")
            tm_ui.edit_text = u""
            tm_ui.edit_err = u""
            _tm_edit_focus()

    def tm_bug_save(text):
        import io, time
        L = [u"", u"## %s — %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), text or u"(без текста)")]
        for t, v in tm_where_info():
            L.append(u"- **%s:** %s" % (t, v))
        if tm_ui.history:
            L.append(u"- **Последние выборы:** " + u" → ".join(u"«%s»" % h["text"] for h in tm_ui.history[-4:]))
        if tm_ui.bug_shot:
            L.append(u"- **Скриншот:** ![](%s)" % _tm_os.path.basename(tm_ui.bug_shot))
        tm_ui.bug_shot = None
        try:
            path = _tm_os.path.join(_tm_bug_dir(), "tm_bugs.md")
            new = not _tm_os.path.exists(path)
            with io.open(path, "a", encoding="utf-8") as f:
                if new:
                    f.write(u"# Заметки тестера: %s\n" % tm_str(getattr(store, "tm_title", u"")))
                f.write(u"\n".join(L) + u"\n")
            tm_note(u"Заметка записана: tm_bugs/tm_bugs.md")
        except Exception as e:
            tm_note(u"Не удалось записать заметку: %s" % e, "bad")

    def tm_bug_count():
        try:
            with open(_tm_os.path.join(getattr(config, "basedir", "."), "tm_bugs", "tm_bugs.md"), "rb") as f:
                return f.read().count(b"\n## ")
        except Exception:
            return 0

    # ---------------- свой Python-код (как консоль, но в окне меню) ----------------
    class _TmCodeValue(FieldInputValue):
        def enter(self):
            tm_code_run()
            return None

    tm_code_iv = _TmCodeValue(tm_ui, "code_text", default=False, returnable=False)

    def tm_code_run():
        code = (tm_ui.code_text or u"").strip()
        if not code:
            tm_note(u"Введи код, например money или money += 100", "warn")
            return
        bad = False
        try:
            try:
                compile(code, "<tm_code>", "eval")
                expr = True
            except SyntaxError:
                expr = False
            if expr:
                v = renpy.python.py_eval(code)
                res = repr(v) if isinstance(v, _TM_STR) else tm_str(v)
            else:
                ex = getattr(renpy.python, "py_exec", None)
                if ex is not None:
                    ex(code)
                else:
                    exec(code, vars(renpy.store))
                res = u"выполнено"
        except Exception as e:
            res, bad = u"%s: %s" % (type(e).__name__, tm_str(e)), True
        tm_ui.code_hist.append((code, _tm_short(res, 160), bad))
        del tm_ui.code_hist[:-8]
        renpy.restart_interaction()

    def tm_code_again(code):
        tm_ui.code_text = code
        tm_code_run()

    # ---------------- выражение в HUD ----------------
    def tm_hud_add_expr():
        e = (tm_ui.hud_expr or u"").strip()
        if not e:
            tm_note(u"Введи выражение, например money + bank или day % 7", "warn")
            return
        try:
            renpy.python.py_eval(e)
        except Exception as ex:
            tm_note(u"Не вычисляется: %s" % ex, "bad")
            return
        if not tm_watched(e):
            tm_watch_toggle(e, e)
        tm_ui.hud_expr = u""
        renpy.restart_interaction()

    # ---------------- лог реплик с откатом к любой ----------------
    def tm_dialog_log(n=12):
        # [(кто, текст, точка отката)] — свежие сверху
        out = []
        for h in reversed(list(getattr(store, "_history_list", None) or [])[-n:]):
            try:
                who = renpy.filter_text_tags(tm_str(h.who or u""), allow=[])
                what = renpy.filter_text_tags(tm_str(h.what or u""), allow=[])
            except Exception:
                who, what = tm_str(getattr(h, "who", u"") or u""), tm_str(getattr(h, "what", u"") or u"")
            out.append((_tm_short(who, 18), _tm_short(what, 70), getattr(h, "rollback_identifier", None)))
        return out

    # ---------------- персонажи: своё имя ----------------
    def tm_characters():
        # [(переменная, имя, своё?)] — персонажи с постоянным именем (не динамическим)
        out = []
        try:
            adv = renpy.character.ADVCharacter
            ns = vars(renpy.store)
            for var in sorted(k for k in ns.keys() if isinstance(k, _TM_STR) and not k.startswith("_")):
                c = ns[var]
                if not isinstance(c, adv) or getattr(c, "dynamic", False):
                    continue
                nm = getattr(c, "name", None)
                if isinstance(nm, _TM_STR) and nm.strip():
                    out.append((var, nm, var in tm_ui.char_names))
        except Exception:
            pass
        return out[:80]

    def tm_edit_char(var):
        tm_ui.edit = ("char", var)
        tm_ui.edit_text = tm_str(tm_ui.char_names.get(var) or getattr(getattr(renpy.store, var, None), "name", u""))
        tm_ui.edit_err = u""
        _tm_edit_focus()

    def tm_char_rename(var, raw):
        c = getattr(renpy.store, var, None)
        if c is None:
            return
        raw = (raw or u"").strip().replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
        orig = tm_ui.char_orig.get(var, c.name)
        if raw and raw != orig:
            tm_ui.char_orig.setdefault(var, c.name)
            tm_ui.char_names[var] = raw
            c.name = raw
            tm_note(u"%s теперь «%s»" % (orig, raw))
        else:
            c.name = orig
            tm_ui.char_names.pop(var, None)
            tm_ui.char_orig.pop(var, None)
            tm_note(u"Имя возвращено: %s" % orig)
        renpy.session["tm_chars"] = None
        renpy.session["tm_nice"] = None
        renpy.session["tm_auto"] = None
        renpy.restart_interaction()

    def _tm_chars_apply():
        # свои имена — после каждого запуска (define пересоздаёт персонажей) и загрузки
        for var, nm in list(tm_ui.char_names.items()):
            c = getattr(renpy.store, var, None)
            if c is not None and isinstance(c, renpy.character.ADVCharacter):
                tm_ui.char_orig.setdefault(var, c.name)
                try:
                    c.name = nm
                except Exception:
                    pass

    # ---------------- перенос значений: сохранить в файл и загрузить ----------------
    # Список «Переменных» (+ избранное) -> <папка игры>/tm_values.json; загрузка — через tm_set:
    # с границами, в журнал правок (Ctrl+Z отменяет). Для переноса статов в новую партию
    # или в обновлённую версию игры.
    def _tm_values_path():
        return _tm_os.path.join(getattr(config, "basedir", ".") or ".", "tm_values.json")

    def tm_values_export():
        import io, json, time
        paths, seen = [], set()
        for p in [r[1] for r in tm_all_stats() if r[1]] + list(tm_ui.favs):
            if p not in seen:
                seen.add(p)
                paths.append(p)
        vals = {}
        for p in paths:
            ok, v = tm_probe(p)
            if ok and isinstance(v, (_TM_NUM, _TM_STR)) and v == v:
                vals[p] = v
        try:
            with io.open(_tm_values_path(), "w", encoding="utf-8") as f:
                f.write(tm_str(json.dumps({"game": tm_str(getattr(store, "tm_title", u"")),
                                           "saved": time.strftime("%Y-%m-%d %H:%M:%S"), "values": vals},
                                          ensure_ascii=True, indent=1, sort_keys=True)))
            tm_note(u"Сохранено значений: %d → tm_values.json (папка игры)" % len(vals))
        except Exception as e:
            tm_note(u"Не удалось сохранить: %s" % e, "bad")

    def tm_values_import():
        import io, json
        try:
            with io.open(_tm_values_path(), encoding="utf-8") as f:
                vals = json.load(f).get("values") or {}
        except Exception:
            tm_note(u"Нет файла tm_values.json — сначала «сохранить значения»", "warn")
            return
        n = skip = 0
        for p in sorted(vals.keys()):
            v = vals[p]
            ok, cur = tm_probe(p)
            if not ok or isinstance(cur, bool) != isinstance(v, bool):
                skip += 1
                continue
            if isinstance(cur, _TM_NUM) and isinstance(v, _TM_NUM):
                v = v if isinstance(cur, bool) else (float(v) if isinstance(cur, float) else int(v))
            elif not (isinstance(cur, _TM_STR) and isinstance(v, _TM_STR)):
                skip += 1
                continue
            if cur == v:
                continue
            tm_set(p, v)
            n += 1
        tm_note(u"Загружено значений: %d, пропущено: %d. Отменить — Ctrl+Z или «отменить все»" % (n, skip))

    # ---------------- горячие клавиши быстрого слота ----------------
    def _tm_key_qsave():
        if store.main_menu or getattr(store, "_menu", False):
            return
        tm_quick_save(1)

    def _tm_key_qload():
        tm_quick_load(1)

