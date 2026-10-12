# ============================ helpers ============================
init -5 python:

    def tm_get(path):
        try:
            return renpy.python.py_eval(path)
        except Exception:
            return None

    def tm_str(v):
        # Значение -> текст без сюрпризов: float без хвоста 0.30000000000000004,
        # py2-байты с не-ASCII не роняют форматирование.
        if isinstance(v, float):
            return repr(round(v, 4))
        try:
            return u"%s" % (v,)
        except Exception:
            return repr(v)

    def tm_q(v):
        # Экранирует [ и { : иначе Ren'Py примет их в ЗНАЧЕНИИ за подстановку/тег и
        # упадёт (строки игры вида "[name]", "{b}" или путь d["key"] в тексте).
        return tm_str(v).replace("[", "[[").replace("{", "{{")

    def tm_fmt(v, limit=28):
        # Значение для узкой колонки: длинное обрезается, спецсимволы экранируются.
        s = tm_str(v)
        if len(s) > limit:
            s = s[:limit - 1] + u"…"
        return tm_q(s)

    def _tm_assign(path, value):
        # Присваивание самим Python (цель разбирает компилятор): ключи со скобками и точками
        # в кавычках (d["a[b"], d["v.1"]) и пути через вызовы работают без ручного разбора.
        ex = getattr(renpy.python, "py_exec", None)
        if ex is None:
            return _tm_assign_split(path, value)
        st = renpy.store
        st._tm_assign_v = value
        try:
            ex("%s = _tm_assign_v" % path)
            return
        except SyntaxError:
            pass
        finally:
            try:
                del st._tm_assign_v
            except Exception:
                pass
        _tm_assign_split(path, value)

    def _tm_assign_split(path, value):
        # запасной путь для старых сборок без py_exec
        if path.endswith("]"):
            base, key = path[:-1].rsplit("[", 1)
            obj = renpy.python.py_eval(base)
            obj[renpy.python.py_eval(key)] = value
        elif "." in path:
            base, attr = path.rsplit(".", 1)
            setattr(renpy.python.py_eval(base), attr, value)
        else:
            setattr(renpy.store, path, value)

    def tm_set(path, value):
        if isinstance(value, _TM_NUM) and not isinstance(value, bool):
            lim = tm_clamp(path, value)
            if lim != value:
                lo, hi = tm_limits(path)
                tm_note(u"Упёрлось в границу (%s): %s" % (tm_lim_text(lo, hi), tm_str(lim)), "warn")
                value = lim
        had, old = tm_probe(path)
        try:
            _tm_assign(path, value)
        except Exception as e:
            tm_note(u"Не удалось изменить %s: %s" % (path, e), "bad")
            return
        _tm_journal_add(path, old if had else None, value)
        _tm_after_edit(path, value)
        renpy.restart_interaction()

    def _tm_after_edit(path, value):
        _tm_log_src(path, u"меню")
        if path in tm_ui.frozen:        # правка замороженного стата = новое удерживаемое значение
            tm_ui.frozen[path] = value
        # своя правка — не «изменение игрой»: базовый снимок обновляем, отметку убираем
        if tm_ui.seen is not None:
            tm_ui.seen[path] = value
        tm_ui.deltas.pop(path, None)

    # ---------------- журнал изменений: кто, когда и где менял значения ----------------
    # На каждом взаимодействии сверяются отслеживаемые пути (статы data/авто, избранное,
    # HUD, заморозки). Изменение без пометки — «игра»; правку из меню и возврат заморозкой
    # помечают _tm_after_edit и _tm_apply_frozen. Только скаляры: их можно хранить как есть.
    TM_LOG_MAX = 300
    TM_LOG_PATHS = 300

    def _tm_log_src(path, who):
        try:
            tm_ui.log_src[path] = who
        except Exception:
            pass

    def _tm_log_paths():
        ps = []
        for r in tm_all_stats():
            if r[1] and r[1] not in ps:
                ps.append(r[1])
            if len(ps) >= TM_LOG_PATHS:
                break
        for p in list(tm_ui.frozen) + [w[1] for w in tm_ui.watch] + list(tm_ui.favs):
            if p not in ps:
                ps.append(p)
        return ps

    def _tm_log_where():
        try:
            fn, ln = renpy.get_filename_line()
            return tm_label_at(fn, ln) or (u"%s:%d" % (fn, ln))
        except Exception:
            return u""

    def _tm_log_tick():
        if store.main_menu or not hasattr(tm_ui, "changelog"):
            return
        try:
            paths = _tm_log_paths()
        except Exception:
            return
        prev, src = tm_ui.log_prev, tm_ui.log_src
        now, where = tm_now(), None
        for p in paths:
            had, v = tm_probe(p)
            if not had or not (isinstance(v, (_TM_NUM, _TM_STR, bool)) or v is None):
                continue
            if p in prev:
                old = prev[p]
                try:
                    same = old == v and type(old) is type(v)
                except Exception:
                    same = True
                if not same:
                    if where is None:
                        where = _tm_log_where()
                    tm_ui.changelog.append((now, where, p, old, v, src.pop(p, u"игра")))
            prev[p] = v
        src.clear()
        del tm_ui.changelog[:-TM_LOG_MAX]

    def tm_log_rows(limit=60):
        # строки окна журнала, новые сверху: (время, имя, было -> стало, кто, где)
        import time
        out = []
        for t, where, p, old, new, who in reversed(tm_ui.changelog[-limit:]):
            out.append((time.strftime("%H:%M:%S", time.localtime(t)), tm_nice(p, p)[0],
                        tm_str(old) + u" → " + tm_str(new), who, where))
        return out

    def tm_log_clear():
        tm_ui.changelog = []
        renpy.restart_interaction()

    # ---------------- журнал правок и отмена ----------------
    def _tm_journal_add(path, old, new):
        try:
            if old == new and type(old) is type(new):
                return
        except Exception:
            pass
        tm_ui.journal.append((path, old, new))
        del tm_ui.journal[:-100]

    def tm_undo():
        if not tm_ui.journal:
            tm_note(u"Отменять нечего", "warn")
            return
        path, old, new = tm_ui.journal.pop()
        try:
            _tm_assign(path, old)
        except Exception as e:
            tm_note(u"Не удалось отменить %s: %s" % (path, e), "bad")
            return
        _tm_after_edit(path, old)
        tm_note(u"Отменено: %s = %s" % (tm_nice(path, path)[0], tm_str(old)))
        renpy.restart_interaction()

    def tm_undo_all():
        n = 0
        while tm_ui.journal:
            path, old, new = tm_ui.journal.pop()
            try:
                _tm_assign(path, old)
                _tm_after_edit(path, old)
                n += 1
            except Exception:
                pass
        tm_note(u"Отменено правок: %d" % n)
        renpy.restart_interaction()

    # ---------------- свои уведомления (тосты) ----------------
    # В части игр экран notify сломан или перекрашен; тосты рисуются оверлеем меню.
    # Где оверлей скрыт (главное меню, меню игры) — обычный renpy.notify.
    TM_TOAST_LIFE = 3.4

    def tm_now():
        import time
        return time.time()

    def tm_note(msg, kind=None):
        msg = tm_str(msg)
        if kind is None:
            low = msg.lower()
            if low.startswith((u"ошибка", u"не удалось", u"не число", u"нельзя")):
                kind = "bad"
            elif low.startswith((u"упёрлось", u"слот пуст", u"введи", u"сначала", u"уже", u"метки нет")):
                kind = "warn"
            else:
                kind = "ok"
        hidden = (store.main_menu or getattr(store, "suppress_overlay", False)
                  or getattr(store, "_menu", False))
        if hidden:
            try:
                renpy.notify(msg)
            except Exception:
                pass
            return
        now = tm_now()
        tm_ui.toasts = [t for t in tm_ui.toasts if now - t[0] < TM_TOAST_LIFE][-3:] + [(now, msg, kind)]
        try:
            renpy.restart_interaction()
        except Exception:
            pass

    def tm_toasts_live():
        now = tm_now()
        return [t for t in tm_ui.toasts if now - t[0] < TM_TOAST_LIFE]

    TM_TOAST_COLORS = {"ok": "#38e0c8", "warn": "#ffb454", "bad": "#ff6b6b"}

    # ---------------- границы статов (min / max) ----------------
    # В data-файле строка стата: ("Метка", "путь") или ("Метка", "путь", "min", "max").
    # Граница — число или выражение игры ("state.player_stats.focus_level_max"), пусто = нет.
    # Без явного max движок ищет соседнюю переменную <имя>_max / max_<имя>.
    # Через границы проходит всё: −/+, ввод, заморозка (tm_set -> tm_clamp).
    def _tm_limit_specs():
        data = getattr(store, "tm_stats", None) or []
        key = (id(data), len(data))
        c = renpy.session.get("tm_limits")
        if c is None or c[0] != key:
            d = {}
            for r in data:
                if len(r) >= 4 and r[1] and (r[2] or r[3]):
                    d[r[1]] = (r[2], r[3])
            c = (key, d)
            renpy.session["tm_limits"] = c
        return c[1]

    def _tm_eval_limit(spec):
        if spec is None or spec == "":
            return None
        if isinstance(spec, _TM_NUM) and not isinstance(spec, bool):
            return spec
        sp = tm_str(spec).strip()
        try:
            return int(sp)
        except ValueError:
            pass
        try:
            return float(sp.replace(",", "."))
        except ValueError:
            pass
        ok, v = tm_probe(sp)
        if ok and isinstance(v, _TM_NUM) and not isinstance(v, bool):
            return v
        return None

    def _tm_auto_max(path):
        # focus_level -> focus_level_max / max_focus_level (рядом, на том же объекте)
        if path.endswith("]") or path.endswith("_max"):
            return None
        if "." in path:
            base, name = path.rsplit(".", 1)
            base += "."
        else:
            base, name = "", path
        if name.startswith("max_"):
            return None
        for cand in (base + name + "_max", base + "max_" + name):
            ok, v = tm_probe(cand)
            if ok and isinstance(v, _TM_NUM) and not isinstance(v, bool):
                return v
        return None

    def tm_limits(path):
        # (min, max) — числа или None
        spec = _tm_limit_specs().get(path)
        lo = hi = None
        if spec:
            lo, hi = _tm_eval_limit(spec[0]), _tm_eval_limit(spec[1])
        if hi is None:
            hi = _tm_auto_max(path)
        return lo, hi

    def tm_clamp(path, v):
        lo, hi = tm_limits(path)
        r = v
        if lo is not None and r < lo:
            r = lo
        if hi is not None and r > hi:
            r = hi
        if r is not v and not isinstance(v, float):
            # целый стат при дробной границе: внутрь диапазона (min 1.5 -> 2, max 4.5 -> 4)
            try:
                import math
                r = int(math.ceil(r)) if (lo is not None and r == lo) else int(math.floor(r))
            except Exception:
                pass
        return r

    def tm_lim_text(lo, hi):
        if lo is not None and hi is not None:
            return u"%s…%s" % (tm_str(lo), tm_str(hi))
        if hi is not None:
            return u"≤ %s" % tm_str(hi)
        if lo is not None:
            return u"≥ %s" % tm_str(lo)
        return u""

    def tm_stat_view(path, val):
        # (подпись границ, вне границ?, можно −, можно +) для строки стата
        lo, hi = tm_limits(path)
        out = False
        try:
            out = (lo is not None and val < lo) or (hi is not None and val > hi)
        except Exception:
            pass
        can_dn = lo is None or val > lo
        can_up = hi is None or val < hi
        return tm_lim_text(lo, hi), out, can_dn, can_up

    def tm_stats_mode():
        # "data" — список из data-файла, "auto" — найденный движком сам (любая игра).
        if tm_ui.stats_mode in ("data", "auto"):
            return tm_ui.stats_mode
        return "data" if getattr(store, "tm_stats", None) else "auto"

    def tm_set_stats_mode(mode):
        tm_ui.stats_mode = mode
        tm_ui.stat_page = 0
        renpy.restart_interaction()

    def tm_all_stats():
        # активный источник (data / авто) + добавленные из сканера (живут до выхода из игры)
        if tm_stats_mode() == "auto":
            base = tm_auto_stats()
        else:
            base = list(getattr(store, "tm_stats", []) or [])
        return base + list(tm_ui.extra)

    # ---------------- авто-статы: меню полезно в ЛЮБОЙ игре, без data-файла ----------------
    # Источники имён: `default`-переменные игры + всё, что игра меняла в store во время
    # игры (ever_been_changed — ловит старый стиль `$ money = 0` в label start).
    # Обходим объекты/dict/списки на 2 уровня: girls[0].affection, stats["charm"].
    TM_AUTO_MAX = 800
    TM_STAT_WORDS = (
        "love", "affect", "lust", "corrupt", "trust", "money", "gold", "cash", "coin",
        "point", "stat", "strength", "charm", "intel", "dex", "wis", "luck", "relat",
        "xp", "exp", "level", "lvl", "energy", "health", "hp", "mana", "karma", "arous",
        "submi", "domin", "respect", "friend", "mood", "sanity", "fame", "reput", "skill",
        "stamina", "obed", "lewd", "intim", "desire", "horn", "slut", "confid", "courage",
        "stress", "fatigue", "hunger", "score", "influen", "loyal", "jealous", "suspic",
        "attract", "passion", "romance", "fitness", "power", "willpower", "dominance",
    )
    # имена, которые Ren'Py сам пишет в store во время игры
    TM_AUTO_SKIP = frozenset((
        "save_name", "main_menu", "mouse_visible", "suppress_overlay", "default_mouse",
        "nvl_list", "menu", "say", "narrator", "adv", "nvl", "centered", "vcentered",
        "extend", "name_only", "predict_say", "predict_menu", "quick_menu", "layout",
        "_window", "_last_say_who", "_last_say_what", "_last_raw_what", "_history",
        "_history_list", "_menu", "_in_replay", "_side_image_attributes",
        "_return", "_args", "_kwargs", "_rollback", "_skipping", "_dismiss_pause",
    ))

    def _tm_key(k):
        # ключ dict -> кусок пути, читаемый обратно py_eval (без py2-префикса u'..')
        if isinstance(k, _TM_STR):
            if '"' not in k and "\\" not in k and "\n" not in k:
                return u'"%s"' % (k,)
            return repr(k)
        return "%d" % k

    def _tm_plain_obj(v):
        # объект игры с полями (не класс, не функция, не модуль, не тип Ren'Py)
        if isinstance(v, type) or callable(v):
            return False
        cls = getattr(v, "__class__", None) or type(v)      # py2: и old-style классы
        mod = getattr(cls, "__module__", "") or ""
        if mod.startswith("renpy") or mod.startswith("pygame") or mod in ("builtins", "__builtin__", "types"):
            return False
        return isinstance(getattr(v, "__dict__", None), _TM_DICT)

    def _tm_auto_walk(v, path, label, depth, out, seen):
        if len(out) >= TM_AUTO_MAX:
            return
        if isinstance(v, bool):
            out.append(("flag", label, path)); return
        if isinstance(v, _TM_NUM):
            out.append(("num", label, path)); return
        if isinstance(v, _TM_STR):
            if depth == 0 and len(v) <= 80:
                out.append(("str", label, path))
            return
        if depth >= 2:
            return
        if isinstance(v, _TM_DICT):
            try:
                items = sorted(v.items(), key=lambda kv: tm_str(kv[0]))[:48]
            except Exception:
                return
            for k, sub in items:
                if isinstance(k, _TM_STR):
                    if k.startswith("_") or "/" in k or "\\" in k:
                        continue            # ключи-пути файлов — служебные словари
                elif not isinstance(k, _TM_NUM) or isinstance(k, (bool, float)):
                    continue
                kp = _tm_key(k)
                _tm_auto_walk(sub, "%s[%s]" % (path, kp), "%s[%s]" % (label, tm_str(k)), depth + 1, out, seen)
            return
        if isinstance(v, _TM_LIST):
            if len(v) > 24:
                return
            for n, sub in enumerate(v):
                # girls[0] -> «girls[Anna]», если у объекта есть строковое имя
                nm = getattr(sub, "name", None) if _tm_plain_obj(sub) else None
                lab = "%s[%s]" % (label, nm if isinstance(nm, _TM_STR) and nm else n)
                _tm_auto_walk(sub, "%s[%d]" % (path, n), lab, depth + 1, out, seen)
            return
        if _tm_plain_obj(v):
            if id(v) in seen:
                return
            seen.add(id(v))
            for k in sorted(vars(v).keys()):
                if not isinstance(k, _TM_STR) or k.startswith("_"):
                    continue
                _tm_auto_walk(vars(v)[k], "%s.%s" % (path, k), "%s.%s" % (label, k), depth + 1, out, seen)

    def _tm_auto_roots():
        names = []
        seen = set()
        try:
            for d in renpy.ast.default_statements:
                if getattr(d, "store", "store") == "store" and d.varname not in seen:
                    seen.add(d.varname)
                    names.append(d.varname)
        except Exception:
            pass
        try:
            changed = getattr(renpy.python.store_dicts["store"], "ever_been_changed", ())
            for n in sorted(x for x in changed if isinstance(x, _TM_STR)):
                if n not in seen:
                    seen.add(n)
                    names.append(n)
        except Exception:
            pass
        # объекты классов самой игры, созданные в init python (state = GameState()):
        # их поля меняются «внутри», и имя не попадает ни в default, ни в changed
        try:
            ns = vars(renpy.store)
            for n in sorted(ns.keys()):
                if n not in seen and isinstance(n, _TM_STR) and _tm_game_obj(ns[n]):
                    seen.add(n)
                    names.append(n)
        except Exception:
            pass
        return [n for n in names
                if not n.startswith(("_", "tm_", "tmtr"))
                and n not in TM_SCAN_SKIP_TOP and n not in TM_AUTO_SKIP]

    def _tm_game_obj(v):
        # экземпляр класса, объявленного в скриптах игры (модуль store / store.*)
        if not _tm_plain_obj(v):
            return False
        cls = getattr(v, "__class__", None) or type(v)
        mod = getattr(cls, "__module__", "") or ""
        return mod == "store" or mod.startswith("store.")

    _TM_NOT_STAT = ("statement", "status", "station", "static", "state", "start", "string",
                    "stream", "struct", "intro", "interface", "interact", "internal", "intern",
                    "point_and_click", "level_select", "chapter", "hpos", "expand", "expected")

    def _tm_auto_score(path):
        # слово-стат в начале «токена» имени: alice_love, playerMoney, stats["charm"]
        low = path.lower()
        for bad in _TM_NOT_STAT:
            low = low.replace(bad, " ")
        toks = [t for t in _tm_re.split(r"[^a-z0-9]+", low) if t]
        return any(t.startswith(w) or t.endswith(w) for t in toks for w in TM_STAT_WORDS)

    def tm_auto_rebuild():
        renpy.session["tm_auto"] = None
        tm_ui.stat_page = 0
        renpy.restart_interaction()

    def tm_auto_stats():
        # кэш в session: пересобирается при каждом открытии меню (новые переменные игры)
        cached = renpy.session.get("tm_auto")
        if cached is not None:
            return cached
        ns = vars(renpy.store)
        out = []
        seen = set()
        for name in _tm_auto_roots():
            if name not in ns:
                continue
            try:
                _tm_auto_walk(ns[name], name, name, 0, out, seen)
            except Exception:
                continue
        # группы по смыслу (персонажи, деньги, время, статы, флаги, строки, служебное),
        # внутри — по важности: проверяется в условиях > меняется в выборах > меняется
        groups = {}
        for kind, lab, path in out:
            try:
                g = tm_group_of(kind, lab, path)
                sc = tm_score(kind, path)
            except Exception:
                g, sc = u"Служебное", 0
            groups.setdefault(g, []).append((sc, lab, path))
        fixed = [u"Деньги", u"Время", u"Статы", u"Инвентарь", u"Сюжетные флаги", u"Строки", u"Служебное"]
        people = sorted((g for g in groups if g not in fixed),
                        key=lambda g: (-sum(x[0] for x in groups[g]), g))
        rows = []
        for g in people + [g for g in fixed if g in groups]:
            items = sorted(groups[g], key=lambda x: (-x[0], tm_nice(x[1], x[2])[0].lower()))
            key = "svc" if g == u"Служебное" else ""
            rows.append((u"%s  %d" % (g, len(items)), "", key))
            rows.extend((lab, path, key) for _s, lab, path in items)
        renpy.session["tm_auto"] = rows
        return rows

    def tm_toggle_service():
        tm_ui.show_service = not tm_ui.show_service
        tm_ui.stat_page = 0
        renpy.restart_interaction()

    # ---------------- строки вкладки статов: фильтр + страницы ----------------
    TM_PAGE = 40

    def tm_stat_rows(q):
        # -> (строки текущей страницы, номер страницы, всего страниц, всего статов)
        rows = tm_all_stats()
        q = (q or "").strip().lower()
        if tm_ui.only_changed:
            # только то, что игра изменила с прошлого открытия меню
            rows = [r for r in rows if r[1] and tm_delta(r[1]) is not None]
        elif tm_ui.favs and not q:
            # избранное — отдельной группой наверху (в своих группах строки тоже остаются)
            labels = dict((r[1], r[0]) for r in rows if r[1])
            fav = [(labels.get(p, p), p, "fav") for p in tm_ui.favs]
            rows = [(u"Избранное  %d" % len(fav), "", "fav")] + fav + rows
        if q:
            # и по понятному имени, и по пути; свёрнутое «Служебное» тоже ищется
            rows = [r for r in rows if r[1] and (q in tm_str(r[0]).lower() or q in r[1].lower()
                                                  or q in tm_nice(r[0], r[1])[0].lower())]
        elif not tm_ui.show_service:
            rows = [r for r in rows if not (r[1] and len(r) > 2 and r[2] == "svc")]
        total = len([r for r in rows if r[1]])
        pages = max(1, (len(rows) + TM_PAGE - 1) // TM_PAGE)
        page = max(0, min(tm_ui.stat_page, pages - 1))
        return rows[page * TM_PAGE:(page + 1) * TM_PAGE], page, pages, total

    def tm_stat_page(delta):
        tm_ui.stat_page = max(0, tm_ui.stat_page + delta)
        renpy.restart_interaction()

    # ---------------- избранное ----------------
    def tm_is_fav(path):
        return path in tm_ui.favs

    def tm_fav_toggle(path):
        if path in tm_ui.favs:
            tm_ui.favs.remove(path)
        else:
            tm_ui.favs.append(path)
        renpy.restart_interaction()

    # ---------------- «изменилось с прошлого открытия меню» ----------------
    def tm_delta(path):
        d = tm_ui.deltas
        if not d:
            return None
        return d.get(path) or d.get(_tm_norm(path))

    def tm_delta_text(path):
        # (текст, цвет) отметки у значения: +2 / −50 / «изм.»
        d = tm_delta(path)
        if d is None:
            return None
        old, new = d
        if (isinstance(old, _TM_NUM) and isinstance(new, _TM_NUM)
                and not isinstance(old, bool) and not isinstance(new, bool)):
            diff = new - old
            if isinstance(diff, float):
                diff = round(diff, 3)
            return ((u"+%s" % tm_str(diff)) if diff > 0 else (u"−%s" % tm_str(-diff)),
                    "#5ad469" if diff > 0 else "#ff6b6b")
        return u"изм.", "#6cb6ff"

    def _tm_take_seen():
        # при открытии меню: сравнить с прошлым открытием, запомнить текущее
        try:
            cur = tm_scan_collect("all")
        except Exception:
            return
        base = tm_ui.seen
        d = {}
        if base is not None:
            for p, v in cur.items():
                if p in base:
                    try:
                        if base[p] != v:
                            d[p] = (base[p], v)
                    except Exception:
                        pass
        tm_ui.deltas = d
        tm_ui.seen = cur
        if not d:
            tm_ui.only_changed = False

    def tm_toggle_only_changed():
        tm_ui.only_changed = not tm_ui.only_changed
        tm_ui.stat_page = 0
        renpy.restart_interaction()

    # ---------------- HUD наблюдения: выбранные значения поверх игры ----------------
    def tm_watched(path):
        return any(p == path for _l, p in tm_ui.watch)

    def tm_watch_toggle(label, path):
        if tm_watched(path):
            tm_ui.watch = [w for w in tm_ui.watch if w[1] != path]
        else:
            if len(tm_ui.watch) >= 12:
                tm_note("В HUD не больше 12 значений")
                return
            tm_ui.watch.append((label, path))
            tm_ui.hud_on = True
        renpy.restart_interaction()

    def tm_watch_clear():
        tm_ui.watch = []
        renpy.restart_interaction()

    # ---------------- заморозка значений ----------------
    # Замороженный стат возвращается к удерживаемому значению перед каждым взаимодействием
    # и ~20 раз в секунду (config.periodic_callbacks) — игра может менять его сколько угодно.
    # Три вида: «=» ровно это значение, «≥» не меньше, «≤» не больше.
    TM_FREEZE_MODES = (("eq", u"="), ("ge", u"≥"), ("le", u"≤"))

    def tm_freeze_toggle(path):
        if path in tm_ui.frozen:
            del tm_ui.frozen[path]
            tm_ui.freeze_mode.pop(path, None)
        else:
            ok, v = tm_probe(path)
            # числа, флаги и строки (флаг «уже встречались», имя локации и т.п.)
            if not ok or not isinstance(v, (_TM_NUM, _TM_STR)):
                tm_note(u"Заморозить можно число, флаг или строку", "warn")
                return
            num = isinstance(v, _TM_NUM) and not isinstance(v, bool)
            tm_ui.frozen[path] = tm_clamp(path, v) if num else v
            tm_ui.freeze_mode[path] = "eq"
        renpy.restart_interaction()

    def tm_freeze_cycle(path):
        v = tm_ui.frozen.get(path)
        if not isinstance(v, _TM_NUM) or isinstance(v, bool):
            tm_ui.freeze_mode[path] = "eq"      # ≥ / ≤ — только для чисел
            renpy.restart_interaction()
            return
        keys = [k for k, _s in TM_FREEZE_MODES]
        cur = tm_ui.freeze_mode.get(path, "eq")
        tm_ui.freeze_mode[path] = keys[(keys.index(cur) + 1) % len(keys)] if cur in keys else "eq"
        renpy.restart_interaction()

    def tm_freeze_sign(path):
        return dict(TM_FREEZE_MODES).get(tm_ui.freeze_mode.get(path, "eq"), u"=")

    def tm_freeze_clear():
        tm_ui.frozen.clear()
        tm_ui.freeze_mode.clear()
        renpy.restart_interaction()

    def _tm_apply_frozen():
        for path, v in list(tm_ui.frozen.items()):
            m = tm_ui.freeze_mode.get(path, "eq")
            if not isinstance(v, _TM_NUM) or isinstance(v, bool):
                m = "eq"
            try:
                cur = renpy.python.py_eval(path)
                if (cur != v) if m == "eq" else ((cur < v) if m == "ge" else (cur > v)):
                    _tm_assign(path, v)
                    _tm_log_src(path, u"заморозка")
            except Exception:
                pass                    # главное меню / другой сейв: пути может не быть

    def _tm_periodic():
        # заморозка между взаимодействиями: игра, меняющая стат в экранах/таймерах,
        # видит удерживаемое значение почти сразу; сторож авто-прохождения
        if tm_ui.auto:
            _tm_auto_watch()
        if tm_ui.frozen and not store.main_menu:
            _tm_apply_frozen()

    def tm_labels(q, limit=40):
        # Метки сценария, в имени которых есть q (для «Перейти к метке»).
        q = (q or "").strip().lower()
        if not q:
            return []
        try:
            names = renpy.get_all_labels()
        except Exception:
            return []
        hits = [n for n in names
                if isinstance(n, _TM_STR) and not n.startswith("_") and q in n.lower()]
        return sorted(hits)[:limit]

    def tm_add(path, delta):
        cur = tm_get(path)
        if isinstance(cur, bool):
            tm_set(path, not cur)
        elif isinstance(cur, _TM_NUM):
            newv = cur + delta
            tm_set(path, newv if isinstance(cur, float) else int(newv))
        else:
            tm_note("%s не число (%r)" % (path, cur))

    def tm_toggle(path):
        tm_set(path, not bool(tm_get(path)))

    def tm_run(code, times=1):
        # Выполняет строку-код игры в пространстве store (выдать предмет, деньги и т.п.)
        # `times` раз подряд — для «шаг ×N» на вкладке действий.
        # Исполняем компилятором Ren'Py (py_exec): в py2-играх те же флаги, что у кода игры
        # (деление, unicode-литералы). Временные имена циклов (_i, _k, _v…) после прогона
        # убираем — но только НОВЫЕ: раньше удалялась и функция Ren'Py _p, и игра падала.
        ns = vars(renpy.store)
        before = set(ns.keys())
        ex = getattr(renpy.python, "py_exec", None)
        try:
            for _ in range(max(1, int(times))):
                if ex is not None:
                    ex(code)
                else:
                    exec(code, ns)
        except Exception as e:
            tm_note("Ошибка: %s" % e)
            return
        finally:
            for _tmp in ("_i", "_u", "_k", "_v", "_n", "_it", "_tmp"):
                if _tmp not in before:
                    ns.pop(_tmp, None)
        tm_note("Готово" if times == 1 else "Готово ×%d" % times)
        renpy.restart_interaction()

    def tm_quick_save(n):
        # Сохраняем с закрытым меню, чтобы при загрузке оно не всплывало.
        slot = "tm_quick_%d" % n
        was_open, was_diag, was_help = store.tm_ui.open, store.tm_ui.diag_open, store.tm_ui.help_open
        store.tm_ui.open = False
        store.tm_ui.diag_open = False
        store.tm_ui.help_open = False
        try:
            renpy.save(slot, extra_info=("Перед прыжком" if n == 0 else "Быстрый слот %d" % n))
            if n:
                tm_note("Сохранено в быстрый слот %d" % n)
        except Exception as e:
            tm_note("Сохранение: %s" % e)
        finally:
            store.tm_ui.open, store.tm_ui.diag_open = was_open, was_diag
            store.tm_ui.help_open = was_help
            store.tm_ui.slots = None

    def tm_quick_load(n):
        slot = "tm_quick_%d" % n
        if not renpy.can_load(slot):
            tm_note("Слот пуст")
            return
        store.tm_ui.open = False   # состояние меню не в сейве — закрываем сами
        store.tm_ui.slots = None
        renpy.load(slot)   # раскручивает контекст и грузит

    def tm_safety_save():
        # Перед рискованным (прыжок к метке/реплике, скрытый вариант выбора) — слот 0
        # «перед прыжком»: вернуться можно с вкладки «Перемотка».
        if store.main_menu:
            return
        tm_quick_save(0)

    def tm_slots():
        # {n: (можно загрузить, «пусто» / время)} для слотов 0..3; диск читаем один раз
        # за открытие меню, а не на каждой перерисовке экрана
        if tm_ui.slots is None:
            import time
            d = {}
            for n in (0, 1, 2, 3):
                slot = "tm_quick_%d" % n
                try:
                    t = renpy.slot_mtime(slot)
                except Exception:
                    t = None
                try:
                    can = bool(renpy.can_load(slot))
                except Exception:
                    can = False
                d[n] = (can, (time.strftime("%d.%m  %H:%M:%S", time.localtime(t)) if t else u"пусто"))
            tm_ui.slots = d
        return tm_ui.slots

    def tm_slot_info(n):
        return tm_slots()[n][1]

    # ---------------- сканер переменных (ArtMoney-стиль, но по путям) ----------------
    # Состояние держим в renpy.session — оно НЕ пишется в сейвы и НЕ откатывается,
    # так что большие словари-снимки не раздувают сохранения игрока.
    TM_SCAN_MAX = 5000
    TM_SCAN_DEPTH = 4
    TM_SCAN_LIST_MAX = 64     # списки длиннее не обходим (логи, история и т.п.)
    TM_SCAN_SKIP_TOP = frozenset((
        "config", "renpy", "store", "persistent", "gui", "preferences", "_preferences",
        "build", "achievement", "director", "layout", "updater", "iap", "nvl_list",
        "PY2", "main_menu", "save_name", "mouse_visible", "suppress_overlay",
    ))
    try:
        _TM_NUM = (int, long, float)        # py2: включаем long
    except NameError:
        _TM_NUM = (int, float)
    try:
        _TM_STR = basestring                # py2: str + unicode
    except NameError:
        _TM_STR = str
    # В сторе Ren'Py list/dict подменены на RevertableList/Dict: проверка «это list» ложна
    # для обычных списков (config.interact_callbacks, json) и для __dict__ объектов.
    try:
        import builtins as _tm_bi
    except ImportError:
        import __builtin__ as _tm_bi
    _TM_LIST = _tm_bi.list
    import types as _tm_types
    _TM_MODULE = _tm_types.ModuleType
    _TM_DICT = _tm_bi.dict

    def _tm_scan():
        s = renpy.session.get("tm_scan")
        if s is None:
            s = {"old": {}, "cur": {}, "cands": [], "mode": "num", "hist": [],
                 "msg": "Нажми «Снимок», затем измени что-то в игре и сужай."}
            renpy.session["tm_scan"] = s
        return s

    def _tm_scan_is_leaf(v, mode):
        if isinstance(v, _TM_NUM):          # bool — подкласс int, тоже сюда
            return mode in ("num", "all")
        if isinstance(v, _TM_STR):
            return mode in ("str", "all") and 0 < len(v) <= 120
        return False

    def _tm_scan_walk(v, path, depth, out, seen, mode):
        if len(out) >= TM_SCAN_MAX:
            return
        if _tm_scan_is_leaf(v, mode):
            if v == v:                      # NaN не равен сам себе — «меняется» всегда
                out[path] = v
            return
        if depth >= TM_SCAN_DEPTH or isinstance(v, _TM_MODULE):
            return                          # модули (import в init python) — не данные игры
        if depth >= TM_SCAN_DEPTH:
            return
        if isinstance(v, _TM_DICT):
            try:
                items = list(v.items())
            except Exception:
                return
            for k, sub in items:
                if isinstance(k, _TM_STR):
                    if k.startswith("__"):
                        continue
                elif not isinstance(k, _TM_NUM) or isinstance(k, (bool, float)):
                    continue        # ключи — только строки и целые (путь должен читаться обратно)
                _tm_scan_walk(sub, "%s[%s]" % (path, _tm_key(k)), depth + 1, out, seen, mode)
            return
        if isinstance(v, _TM_LIST):
            # статы нередко лежат списком: stats[0], girls[2].love
            if len(v) <= TM_SCAN_LIST_MAX:
                for n, sub in enumerate(v):
                    _tm_scan_walk(sub, "%s[%d]" % (path, n), depth + 1, out, seen, mode)
            return
        mod = getattr(type(v), "__module__", "") or ""
        if mod.startswith("renpy") or mod.startswith("pygame"):
            return
        d = getattr(v, "__dict__", None)
        if isinstance(d, _TM_DICT):
            oid = id(v)
            if oid in seen:
                return
            seen.add(oid)
            for k in sorted(d.keys()):
                if k.startswith("__"):
                    continue
                sub = d[k]
                # листовое значение фиксируем даже при имени с _ (напр. inventory._money),
                # но вглубь _служебных ОБЪЕКТОВ не ныряем.
                if _tm_scan_is_leaf(sub, mode) or not k.startswith("_"):
                    _tm_scan_walk(sub, "%s.%s" % (path, k), depth + 1, out, seen, mode)

    def tm_scan_collect(mode=None):
        out = {}
        seen = set()
        mode = mode or _tm_scan()["mode"]
        ns = vars(renpy.store)
        for name in sorted(ns.keys()):
            if name.startswith(("_", "tm_", "TM_", "tmtr")):
                continue
            if name in TM_SCAN_SKIP_TOP:
                continue
            try:
                _tm_scan_walk(ns[name], name, 0, out, seen, mode)
            except Exception:
                continue
        return out

    def tm_scan_set_mode(mode):
        s = _tm_scan()
        s["mode"] = mode
        s["old"] = {}; s["cur"] = {}; s["cands"] = []; s["hist"] = []
        s["msg"] = "Режим: %s. Нажми «Снимок»." % {"num": "числа", "str": "строки", "all": "всё"}.get(mode, mode)
        renpy.restart_interaction()

    def tm_scan_snapshot():
        s = _tm_scan()
        cur = tm_scan_collect()
        s["old"] = dict(cur); s["cur"] = cur; s["cands"] = sorted(cur.keys()); s["hist"] = []
        s["msg"] = "Снимок: %d переменных. Измени в игре и жми «изменились»." % len(cur)
        if len(cur) >= TM_SCAN_MAX:
            # раньше обрезка была молчаливой — нужной переменной могло не оказаться в снимке
            s["msg"] += " (снимок обрезан на %d — часть переменных в него не попала)" % TM_SCAN_MAX
        renpy.restart_interaction()

    def tm_scan_narrow(mode):
        s = _tm_scan()
        base = s["cur"]
        if not base:
            tm_note("Сначала «Снимок»")
            return
        cur = tm_scan_collect()
        keep = []; old = {}
        for p in s["cands"]:
            a = base.get(p); b = cur.get(p)
            if a is None or b is None:
                continue
            try:
                if mode == "changed": ok = (b != a)
                elif mode == "same": ok = (b == a)
                elif mode == "up": ok = (b > a)
                elif mode == "down": ok = (b < a)
                else: ok = False
            except Exception:
                ok = False
            if ok:
                keep.append(p); old[p] = a
        _tm_scan_push(s)
        s["old"] = old; s["cur"] = cur; s["cands"] = keep
        s["msg"] = "Осталось кандидатов: %d" % len(keep)
        renpy.restart_interaction()

    def tm_scan_equals(text):
        s = _tm_scan()
        text = (text or "").strip()
        if text == "":
            tm_note("Введи значение")
            return
        cur = tm_scan_collect()
        src = s["cands"] if s["cands"] else sorted(cur.keys())
        try:
            n = float(text); numeric = True
        except Exception:
            numeric = False
        keep = []
        for p in src:
            v = cur.get(p)
            if numeric and isinstance(v, _TM_NUM) and not isinstance(v, bool) and v == n:
                keep.append(p)
            elif (not numeric) and isinstance(v, _TM_STR) and v == text:
                keep.append(p)
        _tm_scan_push(s)
        s["old"] = dict((p, cur.get(p)) for p in keep); s["cur"] = cur; s["cands"] = keep
        s["msg"] = "Равно «%s»: %d кандидатов" % (text, len(keep))
        renpy.restart_interaction()

    def tm_scan_contains(text):
        s = _tm_scan()
        text = (text or "").strip()
        if text == "":
            tm_note("Введи текст")
            return
        low = text.lower()
        cur = tm_scan_collect()
        src = s["cands"] if s["cands"] else sorted(cur.keys())
        keep = [p for p in src if isinstance(cur.get(p), _TM_STR) and low in cur.get(p).lower()]
        _tm_scan_push(s)
        s["old"] = dict((p, cur.get(p)) for p in keep); s["cur"] = cur; s["cands"] = keep
        s["msg"] = "Содержит «%s»: %d кандидатов" % (text, len(keep))
        renpy.restart_interaction()

    def tm_scan_name(text):
        # «имя содержит»: переменные, в пути которых есть текст (money -> money, girls[0].money_spent)
        s = _tm_scan()
        low = (text or "").strip().lower()
        if not low:
            tm_note(u"Введи часть имени переменной", "warn")
            return
        cur = tm_scan_collect()
        src = s["cands"] if s["cands"] else sorted(cur.keys())
        keep = [p for p in src if low in p.lower()]
        _tm_scan_push(s)
        s["old"] = dict((p, cur.get(p)) for p in keep); s["cur"] = cur; s["cands"] = keep
        s["msg"] = u"Имя содержит «%s»: %d кандидатов" % (text.strip(), len(keep))
        renpy.restart_interaction()

    def _tm_scan_push(s):
        # шаг сужения можно отменить: храним до 8 прошлых состояний
        h = s.setdefault("hist", [])
        h.append((s["old"], s["cur"], s["cands"], s["msg"]))
        del h[:-8]

    def tm_scan_back():
        s = _tm_scan()
        h = s.get("hist") or []
        if not h:
            tm_note(u"Шагов назад нет", "warn")
            return
        s["old"], s["cur"], s["cands"], s["msg"] = h.pop()
        renpy.restart_interaction()

    def tm_scan_trail():
        # «5000 → 120 → 3»: сколько кандидатов было после каждого шага
        s = _tm_scan()
        nums = [len(x[2]) for x in (s.get("hist") or []) if x[2]] + ([len(s["cands"])] if s["cands"] else [])
        return u" → ".join(u"%d" % n for n in nums)

    def tm_scan_by(text):
        # «изменилось на N»: разница с прошлым шагом ровно N (−N — уменьшилось)
        s = _tm_scan()
        if not s["cur"]:
            tm_note(u"Сначала «Снимок»", "warn")
            return
        try:
            n = float((text or "").strip().replace(",", "."))
        except ValueError:
            tm_note(u"Введи число, например 5 или -50", "warn")
            return
        if n == int(n):
            n = int(n)
        base = s["cur"]
        cur = tm_scan_collect()
        keep = []; old = {}
        for p in s["cands"]:
            a = base.get(p); b = cur.get(p)
            if (isinstance(a, _TM_NUM) and isinstance(b, _TM_NUM)
                    and not isinstance(a, bool) and not isinstance(b, bool) and abs((b - a) - n) < 1e-6):
                keep.append(p); old[p] = a
        _tm_scan_push(s)
        s["old"] = old; s["cur"] = cur; s["cands"] = keep
        s["msg"] = u"Изменилось на %s: %d кандидатов" % (tm_str(n), len(keep))
        renpy.restart_interaction()

    def tm_scan_reset():
        s = _tm_scan()
        s["old"] = {}; s["cur"] = {}; s["cands"] = []; s["hist"] = []
        s["msg"] = "Сброшено. Нажми «Снимок»."
        renpy.restart_interaction()

    def tm_scan_add(path):
        if any(r[1] == path for r in tm_all_stats()):
            tm_note(u"Уже в «Переменных»: %s" % tm_nice(path, path)[0])
            return
        tm_ui.extra.append((path, path))
        tm_note(u"Добавлено в «Переменные»: %s" % tm_nice(path, path)[0])
        renpy.restart_interaction()

    def tm_probe(path):
        # (ok, value): ok=False, если путь не резолвится (для подсветки).
        try:
            return (True, renpy.python.py_eval(path))
        except Exception:
            return (False, None)

    def tm_diag_run():
        # Прогоняет все статы (чтение пути) и действия (компиляция кода) без побочных
        # эффектов и собирает список проблем. Действия не исполняются — только компиляция.
        probs = []
        for r in tm_all_stats():
            label, path = r[0], r[1]
            if not path:
                continue
            ok, v = tm_probe(path)
            if not ok:
                probs.append("[X] стат «%s»: путь не читается" % label)
            elif v is None:
                probs.append("[!] стат «%s»: None (путь читается, но пусто)" % label)
            elif isinstance(v, _TM_NUM) and not isinstance(v, bool):
                lo, hi = tm_limits(path)
                if (lo is not None and v < lo) or (hi is not None and v > hi):
                    probs.append("[!] стат «%s» = %s вне границ %s" % (label, tm_str(v), tm_lim_text(lo, hi)))
            if len(r) >= 4:
                for spec in (r[2], r[3]):
                    if spec and _tm_eval_limit(spec) is None:
                        probs.append("[X] стат «%s»: граница «%s» не вычисляется в число" % (label, spec))
        for label, code in list(getattr(store, "tm_actions", []) or []):
            if not code:
                continue
            try:
                compile(code, "<tm_action>", "exec")
            except SyntaxError as e:
                probs.append("[X] действие «%s»: синтаксис — %s" % (label, e.msg))
        store.tm_ui.diag = probs
        store.tm_ui.diag_open = True
        renpy.restart_interaction()

    def tm_rollback(n=1):
        try:
            renpy.rollback(checkpoints=int(n), force=True, greedy=True)
        except Exception as e:
            tm_note("Rollback: %s" % e)

    def tm_enable_skip():
        # Разрешаем скип всего текста (и прочитанного, и нового) — на время этого скипа.
        # Прежние настройки игрока запоминаем и возвращаем, когда скип кончится
        # (_tm_on_interact): иначе они навсегда оставались изменёнными в persistent.
        try:
            config.allow_skipping = True
            config.fast_skipping = True
            store._skipping = True
            if tm_ui.skip_restore is None:
                tm_ui.skip_restore = (_preferences.skip_unseen, _preferences.skip_after_choices)
            _preferences.skip_unseen = True
            _preferences.skip_after_choices = True
        except Exception:
            pass

    def tm_restore_skip_prefs():
        if tm_ui.skip_restore is None or renpy.config.skipping:
            return
        try:
            _preferences.skip_unseen, _preferences.skip_after_choices = tm_ui.skip_restore
        except Exception:
            pass
        tm_ui.skip_restore = None

    def tm_toggle_skip_unseen():
        # явный переключатель игрока: Ctrl пропускает и непрочитанное (настройка самой игры)
        _preferences.skip_unseen = not _preferences.skip_unseen
        renpy.restart_interaction()

    def tm_start_skip(mode="fast"):
        # Мгновенный старт скипа, минуя проверки чувствительности Skip().
        # mode="fast" — без задержек (config.skip_delay игнорируется).
        tm_enable_skip()
        try:
            renpy.config.skipping = mode
            renpy.restart_interaction()
        except Exception as e:
            tm_note("Skip: %s" % e)

    def tm_on_dragged(drags, drop):
        # Запоминаем позицию окна после перетаскивания за шапку. Окно прижимается к
        # экрану: за край нельзя утащить больше, чем оставить полосу шапки видимой.
        try:
            d = drags[0]
            k = tm_k()
            w, h = tm_win_size()
            sw, sh = config.screen_width, config.screen_height
            keep = int(160 * k)
            x = max(keep - int(w * k), min(int(d.x), sw - keep))
            y = max(0, min(int(d.y), sh - int(56 * k)))
            if (x, y) != (int(d.x), int(d.y)):
                d.snap(x, y, 0.15)
            store.tm_ui.win_pos = (x, y)
        except Exception:
            pass

    def tm_reset_pos():
        store.tm_ui.win_pos = None
        renpy.restart_interaction()

