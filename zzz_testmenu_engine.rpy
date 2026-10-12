# =====================================================================
#  UNIVERSAL TEST MENU  —  shared engine  (drop-in, идентичен для всех игр)
#  Открыть/закрыть:  Shift+T   (запасная клавиша: F9)
#  Подсказки к выборам: Shift+H
#  Вкладки: Перемотка | Переменные | Выдать | Поиск | Сюжет | Настройки
#  (значки — game/tm_ui/ic/*.png; нет папки — вкладки просто без значков)
#  Окно можно перетаскивать за шапку. Клики/клавиши в игру не проходят.
#  data-файл (zzz_testmenu_data.rpy: заголовок / акцент / статы / действия)
#  НЕ обязателен: без него статы находятся автоматически (режим «авто»).
# =====================================================================

# ---- щедрый rollback + разрешённый скип ----
# Настройки игрока (_preferences) здесь НЕ трогаем: они живут в persistent и остались бы
# изменёнными после удаления меню. Скип непрочитанного включается только на время скипа
# из меню (tm_start_skip) или явно переключателем на вкладке «Перемотка».
init 999 python:
    try:
        # Откат включён, но глубина — разумная: НЕ больше, чем нужно для «Назад ×10».
        # Раньше тут стояло 100000: журнал отката рос бесконечно и целиком писался в
        # каждый сейв (в большой игре — 300 МБ несжатого журнала, 31 МБ файл),
        # автосейв замирал на секунды, игра лагала. Значения игры, если они больше, не трогаем.
        config.rollback_enabled = True
        config.hard_rollback_limit = max(int(config.hard_rollback_limit or 0), 128)
        config.rollback_length = max(int(config.rollback_length or 0), 128)
    except Exception:
        pass
    try:
        # Скип разрешён всегда (Ctrl / Tab), даже если игра его отключила.
        # Alt клавишей скипа больше не назначаем: Alt+Tab и Alt+Enter запускали пропуск.
        config.allow_skipping = True
        config.fast_skipping = True
        if (not getattr(config, "skip_delay", 0)) or config.skip_delay > 40:
            config.skip_delay = 20
    except Exception:
        pass

# ---- дефолты заголовка/акцента (data-файл переопределит) ----
init -10 python:
    if not hasattr(store, "tm_title"):
        store.tm_title = "TEST MENU"
    if not hasattr(store, "tm_accent"):
        store.tm_accent = "#38e0c8"
    if not hasattr(store, "tm_stats"):
        store.tm_stats = []
    if not hasattr(store, "tm_actions"):
        store.tm_actions = []

    class _TmUI(NoRollback):
        # NoRollback: поля не откатываются. Объект создаётся на init и его привязка
        # не меняется, поэтому в сохранения он тоже не попадает.
        def __init__(self):
            self.open = False
            self.tab = "rewind"
            self.stat_step = 1
            self.win_pos = None       # (x, y) окна после перетаскивания; None = по центру
            self.diag_open = False
            self.diag = []
            self.stat_filter = ""
            self.act_filter = ""
            self.give_qty = 1
            self.scan_val = ""        # сканер: поле поиска по значению
            self.jump_label = ""      # настройки: поле «перейти к метке»
            self.extra = []           # статы, добавленные из сканера: [(метка, путь)]
            self.frozen = {}          # заморозка: путь -> удерживаемое значение
            self.profile = {}         # профиль игры: {"frozen": {путь: значение}, "modes": {путь: вид}}
            self.stats_mode = None    # "data" | "auto"; None = data, если он задан, иначе авто
            self.stat_page = 0
            self.watch = []           # HUD наблюдения: [(метка, путь)]
            self.hud_on = True
            self.find_text = ""       # сюжет: поиск реплики по тексту
            self.flag_filter = ""     # сюжет: фильтр persistent-флагов
            self.confirm = ""         # ключ действия, ждущего подтверждения вторым кликом
            self.accent = None        # текущий акцент (не в store: иначе он писался в каждый сейв)
            self.slots = None         # кэш «пусто / время» быстрых слотов (диск не на каждый кадр)
            self.skip_restore = None  # настройки скипа игрока до скипа из меню — вернуть после
            self.help_open = False    # окно «Как пользоваться» (само открывается в первый раз)
            self.show_service = False # авто-список: показать группу «Служебное»
            self.journal = []         # правки из меню: [(путь, было, стало)] — для отмены
            self.favs = []            # избранное: пути, закреплённые наверху «Переменных»
            self.seen = None          # значения при прошлом открытии меню: {путь: значение}
            self.deltas = {}          # что изменилось с прошлого открытия: {путь: (было, стало)}
            self.only_changed = False # «Переменные»: показать только изменённые
            self.freeze_mode = {}     # заморозка: путь -> "eq" (ровно) | "ge" (не меньше) | "le" (не больше)
            self.mini = False         # мини-режим: плашка с кнопками поверх игры
            self.toasts = []          # свои уведомления: [(время, текст, вид)]
            self.tick = 0             # номер взаимодействия (для вспышек HUD)
            self.hud_last = {}        # HUD: прошлое значение пути
            self.hud_flash = {}       # HUD: путь -> (изменение, время)
            self.history = []         # история выборов: [{"text", "where", "eff"}]
            self.hist_pending = None  # выбор сделан, эффект ещё не посчитан: (текст, где, снимок)
            self.edit = None          # окно ввода: ("value" | "name", путь) или None
            self.edit_text = ""
            self.edit_err = ""
            self.where_open = False   # окно «Где я»
            self.jump_mode = "jump"   # «Сюжет»: метка — прыжок или повтор сцены (Replay)
            self.peek = set()         # подсказки «по щелчку»: открытые варианты (узел, индекс)
            self.state_sig = None     # последний записанный tm_state.json (пишем только изменения)
            # --- вкладка «Тест» (2026-10-06) ---
            self.auto = None          # авто-прохождение: dict (режим, лимит, стоп-условия, маршрут) или None
            self.auto_mode = "new"    # стратегия выбора: new | random | first
            self.auto_limit = 30      # сколько выборов сделать (0 — без ограничения)
            self.auto_stop_label = "" # остановиться на этой метке
            self.auto_stop_unseen = False  # остановиться на первой непрочитанной реплике
            self.auto_log = []        # что сделало последнее авто-прохождение: [текст]
            self.route_rec = []       # выборы текущей партии: [(текст варианта, точка отката)]
            self.route_start = ""     # откуда записан: "start" — с начала игры, "save" — с загрузки
            self.routes = []          # сохранённые маршруты: [{"name", "choices"}]
            self.scene_filter = ""    # «Тест»: фильтр сцен
            self.scene_open = ""      # «Тест»: сцена, у которой раскрыто «откуда сюда»
            self.scene_all = False    # «Тест»: показывать и просмотренные сцены
            self.code_peek = set()    # подсказки: варианты с раскрытым кодом (узел, индекс)
            self.code_text = ""       # «Код»: строка Python
            self.code_hist = []       # «Код»: [(код, результат, ошибка?)]
            self.hud_expr = ""        # «Настройки»: выражение для HUD
            self.char_names = {}      # свои имена персонажей: {переменная: имя}
            self.char_orig = {}       # исходные имена переименованных: {переменная: имя}
            self.bug_shot = None      # скриншот к заметке о баге (снят до открытия окна)
            self.bug_pending = False  # меню спрятано, через кадр снимаем экран для заметки
            self.label_prev = None    # чужой config.label_callback (цепочка)

    tm_ui = _TmUI()

    def tm_acc():
        # акцент для экранов: тема (tm_ui.accent) -> data-файл -> по умолчанию
        return tm_ui.accent or getattr(store, "tm_accent", None) or "#38e0c8"

# Встроенный в Ren'Py шрифт с кириллицей — не зависим от шрифта игры.
define tm_font = "DejaVuSans.ttf"

# Состояние самого меню (открыто/вкладка/шаг/фильтры/заморозка) — в объекте tm_ui
# (см. _TmUI ниже), состояние сканера — в renpy.session. Ни то ни другое НЕ пишется
# в сейвы и НЕ откатывается: раньше «Назад» откатывал и флаг «меню открыто», и меню
# закрывалось после каждого шага перемотки.

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
        if path in tm_ui.frozen:        # правка замороженного стата = новое удерживаемое значение
            tm_ui.frozen[path] = value
        # своя правка — не «изменение игрой»: базовый снимок обновляем, отметку убираем
        if tm_ui.seen is not None:
            tm_ui.seen[path] = value
        tm_ui.deltas.pop(path, None)

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

# ==================== тема + утилиты (редактор внешнего вида) ====================
init -4 python:
    # Пресеты для вкладки «Настройки»
    TM_ACCENTS = [
        ("Бирюза", "#38e0c8"), ("Голубой", "#4aa8ff"), ("Розовый", "#ff6b9d"),
        ("Зелёный", "#5ad469"), ("Оранж", "#ff9f43"), ("Фиолет", "#b06bff"),
        ("Красный", "#ff5c5c"), ("Белый", "#e7ebf2"),
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
        s = (a or "#38e0c8").lstrip("#")
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
        a  = tm_pref("tm_accent", None) or getattr(store, "tm_accent", None) or "#38e0c8"
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
            style.tm_head_btn.background = Frame(Transform(_bt, matrixcolor=TintMatrix("#07110f"), alpha=0.16), 13, 13)
            style.tm_head_btn.hover_background = Frame(Transform(_bt, matrixcolor=TintMatrix("#07110f"), alpha=0.34), 13, 13)
        else:
            style.tm_header_bg.background = Solid(a)
            style.tm_border.background = Frame(Solid(a), 0, 0)
            style.tm_btn.hover_background = Frame(Solid(a), 8, 8)
            style.tm_pm_btn.hover_background = Frame(Solid(a), 8, 8)
            style.tm_icon_btn.hover_background = Frame(Solid(a), 8, 8)
            style.tm_icon_btn.selected_background = Frame(Solid(a), 8, 8)
            style.tm_seg.selected_background = Frame(Solid(a), 8, 8)
            style.tm_panel.background = Frame(Solid("#10141d" + op), 0, 0)

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
        ("stats", u"Переменные",
         u"Статы игры с понятными именами, по группам. Звезда — в избранное (наверху списка), глаз — в HUD. "
         u"Цветная отметка +2 или −50 рядом со значением — игра изменила его с прошлого открытия меню, "
         u"кнопка «изменённые» оставит только такие. Снежинка — заморозить; знак рядом меняет вид: "
         u"= ровно, ≥ не меньше, ≤ не больше. Мишень — следующий порог из условий сценария. "
         u"Щелчок по имени — дать своё. В окне ввода +50, -10, *2 — от текущего значения, =-5 — точное. "
         u"Значения можно сохранить в файл и загрузить в другой партии. PgUp и PgDn листают страницы."),
        ("actions", u"Выдать / Код",
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
        # (ключ, подпись, подсказка) видимых вкладок; «Выдать» — только если у игры есть действия.
        # Значок вкладки — tm_ui/ic/<ключ>.png.
        tabs = [("rewind", u"Перемотка", u"Откат, лог реплик, быстрые слоты, скип текста"),
                ("stats", u"Переменные", u"Статы игры: правка, заморозка, HUD")]
        if getattr(store, "tm_actions", None):
            tabs.append(("actions", u"Выдать", u"Предметы, деньги и прочее кодом игры; свой Python-код"))
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

    TM_HINT_COLORS = {"up": "#5ad469", "down": "#ff6b6b", "set": "#6cb6ff", "call": "#d6b8ff", "go": "#8b93a3"}

    def tm_hint_markup(effs):
        if not effs:
            return u"{color=#5b6373}без изменений{/color}"
        return u"   ".join(u"{color=%s}%s{/color}" % (TM_HINT_COLORS.get(k, "#c7ccd4"), tm_q(t)) for k, t in effs)

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

# ============================ hotkey (глобально) ============================
# ==================== смысл переменных: имена, «что делает», пороги ====================
# Понятное имя (персонаж + перевод слов имени + подпись из реплик), где переменная меняется
# и где проверяется (по AST сценария, работает и с .rpyc), пороги условий, группы по смыслу.
# Словарь TM_WORDS — единственный: студия (tmkit/naming.py) читает его из этого файла,
# поэтому он должен оставаться литералом { u"слово": u"перевод", ... } с «}» на своей строке.
init -4 python:
    TM_WORDS = {
        u"love": u"симпатия", u"affection": u"привязанность", u"affect": u"привязанность",
        u"lust": u"страсть", u"corruption": u"развращённость", u"corrupt": u"развращённость",
        u"trust": u"доверие", u"money": u"деньги", u"cash": u"деньги", u"gold": u"золото",
        u"coin": u"монеты", u"coins": u"монеты", u"dollar": u"доллары", u"credit": u"кредиты",
        u"point": u"очки", u"points": u"очки", u"strength": u"сила", u"str": u"сила",
        u"charm": u"обаяние", u"charisma": u"обаяние", u"cha": u"обаяние",
        u"intelligence": u"интеллект", u"intel": u"интеллект", u"int": u"интеллект",
        u"smart": u"ум", u"dex": u"ловкость", u"agility": u"ловкость", u"wis": u"мудрость",
        u"wisdom": u"мудрость", u"luck": u"удача", u"relationship": u"отношения",
        u"relation": u"отношения", u"relat": u"отношения", u"rel": u"отношения",
        u"xp": u"опыт", u"exp": u"опыт", u"experience": u"опыт", u"level": u"уровень",
        u"lvl": u"уровень", u"energy": u"энергия", u"health": u"здоровье", u"hp": u"здоровье",
        u"mana": u"мана", u"mp": u"мана", u"karma": u"карма", u"arousal": u"возбуждение",
        u"arous": u"возбуждение", u"horny": u"возбуждение", u"submission": u"покорность",
        u"submissive": u"покорность", u"submi": u"покорность", u"dominance": u"доминирование",
        u"domin": u"доминирование", u"respect": u"уважение", u"friendship": u"дружба",
        u"friend": u"дружба", u"mood": u"настроение", u"happiness": u"счастье",
        u"happy": u"счастье", u"sanity": u"рассудок", u"fame": u"слава",
        u"reputation": u"репутация", u"reput": u"репутация", u"rep": u"репутация",
        u"skill": u"навык", u"stamina": u"выносливость", u"obedience": u"послушание",
        u"obed": u"послушание", u"lewd": u"пошлость", u"intimacy": u"близость",
        u"intim": u"близость", u"desire": u"желание", u"slut": u"распущенность",
        u"confidence": u"уверенность", u"confid": u"уверенность", u"courage": u"смелость",
        u"stress": u"стресс", u"fatigue": u"усталость", u"tired": u"усталость",
        u"hunger": u"голод", u"thirst": u"жажда", u"score": u"счёт",
        u"influence": u"влияние", u"influen": u"влияние", u"loyalty": u"верность",
        u"loyal": u"верность", u"jealousy": u"ревность", u"jealous": u"ревность",
        u"suspicion": u"подозрение", u"suspic": u"подозрение", u"attraction": u"влечение",
        u"attract": u"влечение", u"passion": u"страсть", u"romance": u"романтика",
        u"fitness": u"форма", u"power": u"сила", u"willpower": u"сила воли",
        u"day": u"день", u"days": u"дни", u"week": u"неделя", u"weekday": u"день недели",
        u"month": u"месяц", u"year": u"год", u"time": u"время", u"hour": u"час",
        u"hours": u"часы", u"minute": u"минуты", u"daytime": u"время суток",
        u"chapter": u"глава", u"episode": u"эпизод", u"count": u"счётчик",
        u"counter": u"счётчик", u"total": u"всего", u"max": u"максимум", u"min": u"минимум",
        u"inventory": u"инвентарь", u"inv": u"инвентарь", u"item": u"предмет",
        u"items": u"предметы", u"key": u"ключ", u"keys": u"ключи", u"met": u"встреча",
        u"meet": u"встреча", u"seen": u"видел", u"saw": u"видел", u"visited": u"был",
        u"visit": u"посещение", u"done": u"сделано", u"finished": u"завершено",
        u"unlocked": u"открыто", u"unlock": u"открыто", u"quest": u"задание",
        u"task": u"задание", u"mission": u"задание", u"progress": u"прогресс",
        u"stage": u"этап", u"step": u"шаг", u"route": u"ветка", u"path": u"путь",
        u"ending": u"концовка", u"end": u"концовка", u"kiss": u"поцелуй",
        u"kissed": u"поцелуй", u"date": u"свидание", u"dated": u"свидание",
        u"sex": u"секс", u"gift": u"подарок", u"gifts": u"подарки", u"talk": u"разговор",
        u"talked": u"разговор", u"work": u"работа", u"job": u"работа", u"salary": u"зарплата",
        u"debt": u"долг", u"bank": u"банк", u"rent": u"аренда", u"food": u"еда",
        u"bonus": u"бонус", u"name": u"имя", u"mom": u"мама", u"mother": u"мама",
        u"dad": u"папа", u"father": u"папа", u"sister": u"сестра", u"sis": u"сестра",
        u"brother": u"брат", u"aunt": u"тётя", u"girlfriend": u"девушка", u"gf": u"девушка",
        u"wife": u"жена", u"teacher": u"учитель", u"boss": u"босс",
        u"location": u"место", u"place": u"место", u"room": u"комната", u"outfit": u"одежда",
        u"clothes": u"одежда", u"photo": u"фото", u"photos": u"фото", u"secret": u"секрет",
        u"choice": u"выбор", u"choices": u"выборы", u"cheat": u"чит", u"bad": u"плохое",
        u"good": u"хорошее", u"angry": u"злость", u"anger": u"злость", u"fear": u"страх",
        u"pain": u"боль", u"pleasure": u"удовольствие", u"naughty": u"шалость",
        u"pervert": u"извращённость", u"perv": u"извращённость", u"shame": u"стыд",
        u"cum": u"оргазм", u"orgasm": u"оргазм", u"virgin": u"девственность",
        u"pregnant": u"беременность", u"preg": u"беременность", u"drunk": u"опьянение",
        u"alcohol": u"алкоголь", u"beer": u"пиво", u"wine": u"вино", u"phone": u"телефон",
        u"car": u"машина", u"house": u"дом", u"home": u"дом", u"school": u"школа",
        u"class": u"урок", u"exam": u"экзамен", u"grade": u"оценка", u"study": u"учёба",
        u"gym": u"спортзал", u"train": u"тренировка", u"training": u"тренировка",
        u"next": u"следующий", u"son": u"сын", u"daughter": u"дочь", u"husband": u"муж",
        u"decency": u"приличие", u"hygiene": u"гигиена", u"buddy": u"приятель",
        u"nerd": u"ботаник", u"student": u"студент", u"college": u"колледж", u"beach": u"пляж",
        u"city": u"город", u"shop": u"магазин", u"chastity": u"пояс верности",
        u"caged": u"в клетке", u"tattoo": u"татуировка", u"piercing": u"пирсинг",
        u"diary": u"дневник", u"storyline": u"сюжетная линия", u"storylines": u"сюжетные линии",
        u"bully": u"хулиган", u"librarian": u"библиотекарь", u"customer": u"клиент",
        u"morning": u"утро", u"cost": u"расход", u"due": u"срок", u"facial": u"на лице",
        u"neighbor": u"сосед", u"neighbors": u"соседи", u"introduced": u"знакомство",
        u"daily": u"за день", u"body": u"тело", u"empathy": u"эмпатия", u"efficient": u"эффективная",
        u"sp": u"очки навыков", u"knows": u"знает", u"happened": u"было",
        # экшен, RPG, выживание: те же правила, что и для статов новелл
        u"ammo": u"патроны", u"bullet": u"патроны", u"bullets": u"патроны", u"clip": u"обойма",
        u"magazine": u"магазин", u"grenade": u"гранаты", u"grenades": u"гранаты",
        u"weapon": u"оружие", u"weapons": u"оружие", u"armor": u"броня", u"armour": u"броня",
        u"shield": u"щит", u"defense": u"защита", u"defence": u"защита", u"def": u"защита",
        u"attack": u"атака", u"atk": u"атака", u"damage": u"урон", u"dmg": u"урон",
        u"crit": u"крит", u"critical": u"крит", u"speed": u"скорость", u"spd": u"скорость",
        u"jump": u"прыжок", u"lives": u"жизни", u"life": u"жизнь", u"kill": u"убийства",
        u"kills": u"убийства", u"death": u"смерти", u"deaths": u"смерти", u"wave": u"волна",
        u"enemy": u"враги", u"enemies": u"враги", u"combo": u"комбо", u"gem": u"кристаллы",
        u"gems": u"кристаллы", u"diamond": u"алмазы", u"diamonds": u"алмазы",
        u"crystal": u"кристаллы", u"crystals": u"кристаллы", u"ore": u"руда", u"wood": u"дерево",
        u"stone": u"камень", u"iron": u"железо", u"potion": u"зелья", u"potions": u"зелья",
        u"fuel": u"топливо", u"oxygen": u"кислород", u"water": u"вода", u"medkit": u"аптечки",
        u"bandage": u"бинты", u"battery": u"батарея", u"lockpick": u"отмычки", u"magic": u"магия",
        u"spell": u"заклинание", u"cooldown": u"перезарядка", u"timer": u"таймер",
        u"distance": u"расстояние", u"vitality": u"живучесть", u"vit": u"живучесть",
        u"endurance": u"стойкость", u"perception": u"восприятие",
        u"accuracy": u"точность", u"resist": u"сопротивление",
        u"upgrade": u"улучшение", u"upgrades": u"улучшения", u"tier": u"уровень", u"rank": u"ранг",
        u"prestige": u"престиж", u"souls": u"души", u"essence": u"эссенция", u"scrap": u"лом",
        u"parts": u"детали", u"material": u"материалы", u"materials": u"материалы",
        u"resource": u"ресурсы", u"resources": u"ресурсы", u"highscore": u"рекорд",
        u"best": u"лучший", u"multiplier": u"множитель", u"mult": u"множитель",
        u"boost": u"усиление", u"regen": u"регенерация", u"chance": u"шанс", u"drop": u"добыча",
        u"loot": u"добыча", u"temperature": u"температура", u"heat": u"жар",
        u"radiation": u"радиация", u"ammunition": u"патроны", u"arrow": u"стрелы",
        u"arrows": u"стрелы", u"bomb": u"бомбы", u"bombs": u"бомбы", u"star": u"звёзды",
        u"stars": u"звёзды",
    }
    # по префиксу слово совпадает, только если остаток — окончание (love-s, kiss-ed, train-ing);
    # у основ (не самостоятельных слов) остаток любой: arous-al, domin-ance, reput-ation
    TM_INFLECT = (u"s", u"es", u"d", u"ed", u"ing", u"ion", u"ions", u"ness", u"ity", u"ment",
                  u"y", u"ies", u"ful", u"al", u"ly", u"ship", u"ance", u"ence", u"ive", u"ant", u"ent")
    TM_STEMS = frozenset((u"arous", u"submi", u"domin", u"reput", u"influen", u"intim", u"confid",
                          u"suspic", u"relat", u"corrupt", u"attract", u"obed", u"intel", u"affect"))
    # служебные слова имён: не переводятся и не попадают в подпись
    TM_GENERIC = frozenset((u"stat", u"stats", u"data", u"var", u"vars", u"game", u"player",
                            u"pc", u"mc", u"store", u"value", u"val", u"info", u"the", u"is",
                            u"has", u"my", u"current", u"cur", u"num", u"lvl", u"character",
                            u"char", u"state", u"flags", u"flag", u"temp"))
    TM_MONEY = frozenset((u"money", u"cash", u"gold", u"coin", u"coins", u"dollar", u"credit",
                          u"gem", u"gems", u"diamond", u"diamonds"))
    TM_INV = frozenset((u"inv", u"inventory", u"item", u"items", u"bag", u"backpack", u"ammo",
                        u"potion", u"potions", u"medkit", u"weapon", u"weapons", u"loot"))
    TM_TIME = frozenset((u"day", u"days", u"week", u"weekday", u"month", u"year", u"time",
                         u"hour", u"hours", u"minute", u"daytime", u"chapter", u"episode"))

    _TM_COND_NUM = _tm_re.compile(
        r'([A-Za-z_][\w\.]*(?:\[[^\]]+\])*(?:\.\w+)*)\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?)')
    _TM_COND_NUM_R = _tm_re.compile(
        r'(-?\d+(?:\.\d+)?)\s*(>=|<=|==|!=|>|<)\s*([A-Za-z_][\w\.]*(?:\[[^\]]+\])*(?:\.\w+)*)')
    _TM_COND_NAME = _tm_re.compile(r'(?<![\w\.\]"\'])([A-Za-z_][\w\.]*(?:\[[^\]]+\])*)')
    _TM_SAY_AFTER = _tm_re.compile(r'\[([A-Za-z_][\w\.]*(?:\[[^\]]+\])*)(?:![a-z]+)?\]\s*([^\W\d_]{3,})', _tm_re.U)
    _TM_SAY_BEFORE = _tm_re.compile(r'([^\W\d_]{3,})\s*:\s*\[([A-Za-z_][\w\.]*(?:\[[^\]]+\])*)(?:![a-z]+)?\]', _tm_re.U)
    _TM_FLIP = {">=": "<=", "<=": ">=", ">": "<", "<": ">", "==": "==", "!=": "!="}
    _TM_KEYWORDS = frozenset(("and", "or", "not", "in", "is", "True", "False", "None", "if",
                              "else", "lambda", "renpy", "store", "persistent", "config"))

    def _tm_norm(path):
        # путь как в авто-списке: без store., кавычки двойные, без пробелов в []
        p = (path or "").strip()
        if p.startswith("store."):
            p = p[6:]
        p = p.replace("'", '"')
        return _tm_re.sub(r'\[\s*([^\]]*?)\s*\]', r'[\1]', p)

    def _tm_ctx_label(node):
        try:
            return tm_label_at(node.filename, node.linenumber)
        except Exception:
            return None

    def _tm_usage():
        # {путь: {"chg": [(вид, текст, где)], "chk": [(оп, число|None, где)], "nchg", "nchk",
        #  "choice": число изменений в выборах, "word": подпись из реплик}} — один раз за сессию
        u = renpy.session.get("tm_usage")
        if u is not None:
            return u
        u = {}
        nodes = _tm_script_nodes()
        own = lambda n: not (n.filename.startswith("renpy/common") or "zzz_testmenu" in n.filename
                             or n.filename.startswith("renpy/"))

        def rec(path):
            p = _tm_norm(path)
            r = u.get(p)
            if r is None:
                r = u[p] = {"chg": [], "chk": [], "nchg": 0, "nchk": 0, "choice": 0, "word": None}
            return r

        # 1) какие узлы лежат внутри варианта выбора -> текст варианта
        in_choice = {}

        def mark(block, text):
            for n in block or ():
                in_choice[id(n)] = text
                if isinstance(n, renpy.ast.Menu):
                    continue                # у вложенного выбора свои варианты
                if isinstance(n, renpy.ast.If):
                    for _c, b in n.entries:
                        mark(b, text)
                elif isinstance(n, renpy.ast.While):
                    mark(n.block, text)

        for n in nodes:
            try:
                if isinstance(n, renpy.ast.Menu) and own(n):
                    for item in n.items:
                        if item[2] is not None and item[0]:
                            mark(item[2], _tm_short(tm_choice_text(item[0]), 30))
            except Exception:
                continue

        def where(n):
            c = in_choice.get(id(n))
            if c:
                return u"«%s»" % c
            lab = _tm_ctx_label(n)
            return (u"сцена %s" % lab) if lab else u""

        def target_of(block):
            # куда ведёт ветка условия: первый jump/call в ней
            for b in block or ():
                if isinstance(b, renpy.ast.Jump) and not b.expression:
                    return u"сцена %s" % b.target
                if isinstance(b, renpy.ast.Call) and not b.expression:
                    return u"сцена %s" % b.label
            return None

        def checks(cond, ctx):
            if not cond or cond.strip() == "True":
                return
            found = set()
            for m in _TM_COND_NUM.finditer(cond):
                name, op, num = m.groups()
                r = rec(name)
                r["nchk"] += 1
                if len(r["chk"]) < 20:
                    r["chk"].append((op, float(num), ctx))
                found.add(_tm_norm(name))
            for m in _TM_COND_NUM_R.finditer(cond):
                num, op, name = m.groups()
                r = rec(name)
                r["nchk"] += 1
                if len(r["chk"]) < 20:
                    r["chk"].append((_TM_FLIP[op], float(num), ctx))
                found.add(_tm_norm(name))
            for m in _TM_COND_NAME.finditer(_tm_re.sub(r'"[^"]*"|\'[^\']*\'', "", cond)):
                name = m.group(1)
                if name in _TM_KEYWORDS or _tm_norm(name) in found or name.split(".")[0] in _TM_KEYWORDS:
                    continue
                r = rec(name)
                r["nchk"] += 1
                if len(r["chk"]) < 20:
                    r["chk"].append((None, None, ctx))

        for n in nodes:
            try:
                if not own(n):
                    continue
                if isinstance(n, renpy.ast.Python):
                    ctx = where(n)
                    for st in _tm_src_stmts(n.code.source):
                        if st.startswith(("if ", "elif ", "while ")):
                            checks(st.split(" ", 1)[1].rstrip(":"), ctx)
                            continue
                        m = _TM_ASSIGN_RE.match(st)
                        if not m:
                            continue
                        name, op, expr = m.groups()
                        r = rec(name)
                        r["nchg"] += 1
                        if id(n) in in_choice:
                            r["choice"] += 1
                        if len(r["chg"]) < 20:
                            r["chg"].append((op, _tm_short(expr, 16), ctx))
                elif isinstance(n, renpy.ast.If):
                    for cond, blk in n.entries:
                        checks(cond, target_of(blk) or where(n))
                elif isinstance(n, renpy.ast.While):
                    checks(n.condition, where(n))
                elif isinstance(n, renpy.ast.Menu):
                    for item in n.items:
                        if item[1] and item[0]:
                            checks(item[1], u"выбор «%s»" % _tm_short(tm_choice_text(item[0]), 30))
                elif isinstance(n, renpy.ast.Say):
                    w = n.what or ""
                    if "[" in w:
                        for m in _TM_SAY_AFTER.finditer(w):
                            r = rec(m.group(1))
                            r["word"] = r["word"] or m.group(2).lower()
                        for m in _TM_SAY_BEFORE.finditer(w):
                            r = rec(m.group(2))
                            r["word"] = r["word"] or m.group(1).lower()
            except Exception:
                continue
        renpy.session["tm_usage"] = u
        return u

    def tm_usage(path):
        return _tm_usage().get(_tm_norm(path))

    # ---------------- персонажи и подписи ----------------
    def _tm_chars():
        # {ключ в нижнем регистре: отображаемое имя}: имя персонажа и имя его переменной
        c = renpy.session.get("tm_chars")
        if c is not None:
            return c
        c = {}
        try:
            adv = renpy.character.ADVCharacter
            for var, v in vars(renpy.store).items():
                if not isinstance(var, _TM_STR) or var.startswith("_") or not isinstance(v, adv):
                    continue
                nm = getattr(v, "name", None)
                if not isinstance(nm, _TM_STR) or not nm.strip() or "[" in nm or "{" in nm:
                    continue
                nm = nm.strip()
                for key in (var.lower(), nm.lower(), nm.split()[0].lower()):
                    if len(key) >= 3:
                        c.setdefault(key, nm)
        except Exception:
            pass
        renpy.session["tm_chars"] = c
        return c

    def _tm_tokens(text):
        # «girls[Anna].loveLevel» -> [("girls", False), ("anna", True), ("love", False), ("level", False)]
        out = []
        for part in _tm_re.split(r'(\[[^\]]*\])', text or ""):
            if not part:
                continue
            is_key = part.startswith("[")
            s = part.strip("[]").strip('"\'')
            s = _tm_re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
            for t in _tm_re.split(u'[^0-9A-Za-z\u00c0-\uffff]+', s):
                if t and (is_key or not t.isdigit()):    # flags[0] -> «Flags: 0»
                    out.append((t.lower(), is_key))
        return out

    def tm_word(tok):
        # перевод токена: точное слово, затем самое длинное слово-префикс (>= 4 букв, см. TM_INFLECT)
        w = TM_WORDS.get(tok)
        if w:
            return w
        best = None
        for k in TM_WORDS:
            if (len(k) >= 4 and tok.startswith(k) and (best is None or len(k) > len(best))
                    and (k in TM_STEMS or tok[len(k):] in TM_INFLECT)):
                best = k
        return TM_WORDS[best] if best else None

    def _tm_obj_name(path):
        # у объекта-владельца есть строковое поле name (anna.love -> Anna)
        # (re.split по пустому совпадению на py2 не режет — берём позиции «.» и «[»)
        cuts = [m.start() for m in _tm_re.finditer(r'[.\[]', path) if m.start() > 0]
        for i in reversed(cuts):
            owner = path[:i]
            try:
                o = renpy.python.py_eval(owner)
            except Exception:
                continue
            if _tm_plain_obj(o):
                nm = getattr(o, "name", None)
                if isinstance(nm, _TM_STR) and nm.strip() and len(nm) <= 30 and "[" not in nm:
                    return nm.strip()
        return None

    _TM_IDENT = _tm_re.compile(r"^[A-Za-z_][\w.\[\]\"']*$")
    _TM_EXPR = _tm_re.compile(r"[\s+\-*/%<>=!,]")       # оператор вне [...] — это выражение, не путь

    def _tm_user_names():
        n = renpy.session.get("tm_names")
        if n is not None:
            return n
        n = {}
        try:
            n.update(getattr(store.persistent, "tm_names", None) or {})
        except Exception:
            pass
        try:
            import json, io, os
            p = os.path.join(config.gamedir, "tm_names.json")
            if os.path.exists(p):
                with io.open(p, encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, _TM_DICT):
                    n.update(d)
        except Exception:
            pass
        renpy.session["tm_names"] = n
        return n

    def tm_nice(label, path):
        # -> (подпись, уверенно?) — для любого стата (кэш по пути)
        cache = renpy.session.get("tm_nice")
        if cache is None:
            cache = renpy.session["tm_nice"] = {}
        key = (label, path)
        if key in cache:
            return cache[key]
        user = _tm_user_names().get(path)
        if user:
            cache[key] = (user, True)
            return cache[key]
        if label and label != path and not _TM_IDENT.match(label):
            cache[key] = (label, True)      # подпись из студии/data уже человеческая
            return cache[key]
        if path and _TM_EXPR.search(_tm_re.sub(r'\[[^\]]*\]', "", path)):
            cache[key] = (label or path, True)  # выражение (HUD: money + hp) — как написано
            return cache[key]
        toks = _tm_tokens(label if label else path)
        chars = _tm_chars()
        who, who_at = None, -1
        for i, (t, _k) in enumerate(toks):
            if t in chars:
                who, who_at = chars[t], i
                break
        if who is None:
            who = _tm_obj_name(path)
            if who:
                low = who.lower()
                for i, (t, _k) in enumerate(toks):
                    if t == low or t == low.split()[0]:
                        who_at = i
                        break
        if who_at >= 0:
            # имя персонажа из подписи убираем; если оно ключ (girls[Anna].love) — и контейнер перед ним
            toks = (toks[who_at + 1:] if toks[who_at][1] else toks[:who_at] + toks[who_at + 1:])
        base, keys, sure = [], [], who is not None
        for t, is_key in toks:
            if t in TM_GENERIC and not is_key:
                continue
            w = tm_word(t)
            sure = sure or bool(w)
            (keys if is_key else base).append(w or t)
        title = u" ".join(base)
        kt = u" ".join(keys)
        title = (title + u": " + kt) if (title and kt) else (title or kt)
        if not sure:
            u = tm_usage(path)
            if u and u["word"]:
                title, sure = u["word"], True
        if not title:
            title = path
        title = title[:1].upper() + title[1:]
        text = (u"%s | %s" % (who, title)) if who else title
        cache[key] = (text, sure)
        return cache[key]

    # ---------------- «что это делает» и пороги ----------------
    _TM_OPS = {"+=": u"+", "-=": u"−", "*=": u"×", "/=": u"÷", "=": u"= "}

    def tm_thresholds(path):
        # числа, которых сценарий требует (>= N, > N, == N) — по возрастанию
        u = tm_usage(path)
        out = set()
        for op, num, _w in (u["chk"] if u else ()):
            if num is None:
                continue
            if op in (">=", "=="):
                out.add(num)
            elif op == ">":
                out.add(num + 1 if num == int(num) else num)
        return sorted(int(x) if x == int(x) else x for x in out)

    def tm_next_threshold(path, cur):
        try:
            return next((t for t in tm_thresholds(path) if t > cur), None)
        except Exception:
            return None

    def tm_meaning(path):
        # -> (короткая строка под именем, полный текст для подсказки)
        u = tm_usage(path)
        if not u or not (u["nchg"] or u["nchk"]):
            s = u"в сценарии не меняется и не проверяется"
            return s, s
        short, full = [], []
        if u["chg"]:
            ex = sorted(u["chg"], key=lambda c: not c[2].startswith(u"«"))
            parts = [u"%s%s %s" % (_TM_OPS.get(op, op), e, w) for op, e, w in ex[:2]]
            more = u["nchg"] - len(parts)
            short.append(u"меняется: " + u", ".join(parts) + (u" и ещё %d" % more if more > 0 else u""))
            full.append(u"Меняется в %d местах: " % u["nchg"]
                        + u"; ".join(u"%s%s %s" % (_TM_OPS.get(op, op), e, w) for op, e, w in ex[:6]))
        need = [(op, num, w) for op, num, w in u["chk"] if num is not None]
        if need:
            need.sort(key=lambda c: c[1])
            fmt = lambda c: u"%s %s → %s" % (c[0].replace(">=", u"≥").replace("<=", u"≤"),
                                              int(c[1]) if c[1] == int(c[1]) else c[1], c[2])
            short.append(u"нужно " + fmt(need[0]))
            full.append(u"Проверяется: " + u"; ".join(fmt(c) for c in need[:6]))
        elif u["nchk"]:
            w = u["chk"][0][2]
            short.append(u"проверяется" + (u": " + w if w else u""))
            full.append(u"Проверяется в %d условиях" % u["nchk"] + (u", например " + w if w else u""))
        return u"; ".join(short), u". ".join(full)

    def tm_score(kind, path):
        # важность для сортировки: проверяется в условиях > меняется в выборах > меняется
        u = tm_usage(path)
        s = 0
        if u:
            s += 4 * min(u["nchk"], 3) + 3 * min(u["choice"], 3) + min(u["nchg"], 5)
        if kind == "num" and _tm_auto_score(path):
            s += 2
        return s

    def tm_group_of(kind, label, path):
        # группа строки авто-списка: персонаж / деньги / время / статы / флаги / строки / служебное
        toks = [t for t, _k in _tm_tokens(label or path)]
        nice, _sure = tm_nice(label, path)
        if u" | " in nice and kind in ("num", "flag"):
            return nice.split(u" | ")[0]
        u = tm_usage(path)
        used = bool(u and (u["nchg"] or u["nchk"]))
        if kind in ("num", "flag") and toks and toks[0] in TM_INV:
            return u"Инвентарь"
        if kind == "num":
            if any(t in TM_MONEY for t in toks):
                return u"Деньги"
            if any(t in TM_TIME for t in toks):
                return u"Время"
            if used or _tm_auto_score(path):
                return u"Статы"
        elif kind == "flag" and used:
            return u"Сюжетные флаги"
        elif kind == "str":
            return u"Строки"
        return u"Служебное"

    def tm_row_info(label, path):
        # (подпись, короткий смысл, полная подсказка) — для строки вкладки и «Поиска»
        nice, sure = tm_nice(label, path)
        short, full = tm_meaning(path)
        tip = full + (u"" if sure else u". Имя — догадка по названию переменной")
        return nice, short, tip + u". Щёлкни по имени, чтобы переименовать."

    def tm_set_name(path, raw):
        # своё имя переменной (пусто — вернуть автоматическое)
        raw = (raw or "").strip().replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
        names = dict(_tm_user_names())
        if raw:
            names[path] = raw
        else:
            names.pop(path, None)
        # имена — в game/tm_names.json (их видит студия), запасной вариант — persistent
        try:
            import json, io, os
            with io.open(os.path.join(config.gamedir, "tm_names.json"), "w", encoding="utf-8") as f:
                f.write(tm_str(json.dumps(names, ensure_ascii=True, indent=1, sort_keys=True)))
        except Exception:
            store.persistent.tm_names = names
        renpy.session["tm_names"] = names
        renpy.session["tm_nice"] = None
        renpy.session["tm_auto"] = None
        renpy.restart_interaction()

    def tm_to_threshold(path, t):
        tm_set(path, t)

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

init python:
    def _tm_open_menu():
        # В главном меню и в меню игры (Esc) оверлеи скрыты: раньше меню «открывалось»
        # невидимо и выскакивало само при возврате в игру.
        if store.main_menu or getattr(store, "suppress_overlay", False) or getattr(store, "_menu", False):
            tm_note(u"Тест-меню доступно в самой игре (%s)" % tm_keys_text())
            return
        if tm_ui.auto:                         # клавиша меню во время авто-прохождения — стоп
            tm_auto_stop(u"вручную")
        store.tm_ui.open = True
        store.tm_ui.mini = False
        store.tm_ui.edit = None
        store.tm_ui.where_open = False
        store.tm_ui.diag_open = False
        store.tm_ui.confirm = ""
        store.tm_ui.help_open = False
        if not getattr(store.persistent, "tm_help_seen", False):
            store.tm_ui.help_open = True        # первый раз — «Как пользоваться»
            store.persistent.tm_help_seen = True
        store.tm_ui.slots = None             # время слотов перечитать один раз
        renpy.session["tm_auto"] = None      # авто-статы: игра могла завести новые переменные
        _tm_take_seen()                      # что игра изменила с прошлого открытия
        if tm_ui.deltas:
            tm_note(u"С прошлого открытия меню изменилось значений: %d (отмечены в «Переменных»)" % len(tm_ui.deltas))
        renpy.restart_interaction()

    def _tm_on_interact():
        _tm_theme_check()
        _tm_apply_frozen()
        if tm_ui.auto:
            _tm_auto_interact()
        else:
            tm_restore_skip_prefs()
        if tm_ui.hist_pending and not store.main_menu:
            _tm_hist_finish()                # эффект выбора: игра дошла до следующей реплики
        if tm_ui.watch:
            _tm_hud_track()
        _tm_state_save()

    _tm_keymap = renpy.Keymap(tm_toggle_key=_tm_open_menu, tm_hints_key=tm_toggle_hints,
                              tm_bug_key=tm_bug_request, tm_qsave_key=_tm_key_qsave,
                              tm_qload_key=_tm_key_qload)

    # свои клавиши: (действие keymap, клавиша) — Shift+B заметка о баге, Shift+F5 / Shift+F9 слот 1
    TM_EXTRA_KEYS = (("tm_hints_key", "shift_K_h"), ("tm_bug_key", "shift_K_b"),
                     ("tm_qsave_key", "shift_K_F5"), ("tm_qload_key", "shift_K_F9"))

    def tm_register():
        # Горячие клавиши, оверлей и колбэк. Повторяется при старте и после загрузки:
        # игра, которая на init 1+ целиком переприсваивает config.underlay / keymap /
        # overlay_screens, иначе молча отключала меню.
        try:
            _alt = tm_alt_key()
            config.keymap["tm_toggle_key"] = ["shift_K_t"] + ([_alt] if _alt else [])
            for _act, _key in TM_EXTRA_KEYS:
                config.keymap.setdefault(_act, [])
                if _key not in config.keymap[_act]:
                    config.keymap[_act].append(_key)
            if _tm_keymap not in config.underlay:
                config.underlay.append(_tm_keymap)
            if "tm_overlay" not in config.overlay_screens:
                config.overlay_screens.append("tm_overlay")
            lst = getattr(config, "interact_callbacks", None)
            if isinstance(lst, _TM_LIST) and _tm_on_interact not in lst:
                lst.append(_tm_on_interact)
            lst = getattr(config, "periodic_callbacks", None)
            if isinstance(lst, _TM_LIST) and _tm_periodic not in lst:
                lst.append(_tm_periodic)
        except Exception:
            pass
        try:
            # переход на метку: стоп авто-прохождения, начало маршрута новой игры.
            # Новые Ren'Py — список label_callbacks, старые — одна функция (встаём в цепочку).
            # renpy.config, а не config: на 6.99 обращение к незнакомой переменной config
            # бросает исключение вместо значения по умолчанию
            rc = renpy.config
            lst = getattr(rc, "label_callbacks", None)
            if isinstance(lst, _TM_LIST):
                if _tm_on_label not in lst:
                    lst.append(_tm_on_label)
            elif getattr(rc, "label_callback", None) is not _tm_label_chain:
                tm_ui.label_prev = getattr(rc, "label_callback", None)
                rc.label_callback = _tm_label_chain
        except Exception:
            pass
        try:
            renpy.clear_keymap_cache()
        except Exception:
            pass
        _tm_install_menu_wrap()

    tm_register()

    def _tm_on_start(why=u"игра перезапустилась (конец игры или выход в меню)"):
        tm_register()
        tm_apply_theme()
        _tm_scrub_log()
        _tm_chars_apply()
        tm_ui.route_rec = []                 # маршрут — с этой загрузки (новая игра: метка start)
        tm_ui.route_start = "save"
        if tm_ui.auto:
            tm_auto_stop(why, "warn")

    def _tm_on_load():
        _tm_on_start(u"загружен сейв")

    # Тема и регистрация — при старте игры (и её перезапуске) и после загрузки.
    for _cb, _fn in (("start_callbacks", _tm_on_start), ("after_load_callbacks", _tm_on_load)):
        _lst = getattr(config, _cb, None)
        if isinstance(_lst, _TM_LIST) and _fn not in _lst:
            _lst.append(_fn)

# Регистрация ещё раз — после init всех файлов игры (её init 1+ мог всё перезаписать;
# zzz_ в имени — наш init 999 идёт последним).
init 999 python:
    tm_register()
    _tm_state_load()                         # избранное, HUD, вкладка — с прошлого запуска
    _tm_chars_apply()                        # свои имена персонажей

# Окно меню и панели масштабируются под разрешение игры: вёрстка рассчитана на 1080p,
# в 720p-игре всё уменьшается в 2/3 (раньше окно занимало почти весь экран).
init -4 python:
    def tm_k():
        try:
            k = float(config.screen_height) / 1080.0
        except Exception:
            k = 1.0
        return max(0.5, min(2.0, k))

transform tm_zoomer(z=1.0):
    zoom z

# появление окна меню и всплывающих панелей
transform tm_pop(z=1.0):
    zoom z
    on show:
        alpha 0.0
        yoffset 12
        easein 0.14 alpha 1.0 yoffset 0
    on hide:
        easeout 0.10 alpha 0.0

# ---------------------- общие кусочки ----------------------
# значок из tm_ui/ic (64 px) нужного размера; нет файла — ничего не рисуем
screen tm_icon(name, px=26):
    $ _ic = tm_ic(name)
    if _ic:
        add _ic zoom (px / 64.0) yalign 0.5

# кнопка-значок: картинка, а без значков — запасной символ текстом
screen tm_icobtn(name, act, sel=False, tip="", alt="", sens=True):
    button:
        style "tm_icon_btn"
        selected sel
        sensitive sens
        tooltip tip
        action act
        if tm_ic(name):
            add tm_ic(name) zoom 0.44 align (0.5, 0.5)
        else:
            text alt style "tm_icon_text"

# кнопка «значок + подпись»
screen tm_btn2(name, label, act, tip="", sens=True, sel=False):
    button:
        style "tm_btn"
        sensitive sens
        selected sel
        tooltip tip
        action act
        hbox:
            spacing 8
            use tm_icon(name, 24)
            text label style "tm_ico_label"

# поле ввода: щелчок по полю делает его активным (см. style tm_field)
screen tm_field(field, w=300, n=30):
    $ _iv = FieldInputValue(tm_ui, field)
    button:
        style "tm_field"
        xsize w
        action _iv.Enable()
        input value _iv style "tm_filter_text" length n copypaste True

screen tm_sep():
    frame:
        xfill True
        ysize 1
        background Solid("#ffffff14")

# пустое состояние: маскот + пояснение
screen tm_empty(mascot, msg):
    hbox:
        spacing 18
        $ _m = tm_mascot(mascot)
        if _m:
            add _m zoom 0.5 yalign 0.5
        text msg style "tm_dim" yalign 0.5 xmaximum 640

screen tm_overlay():
    zorder 190
    if tm_ui.open:
        use tm_menu
    elif not main_menu:
        if tm_pref("tm_hints", True):
            # в переменных экрана — только имя узла: экранные переменные пишутся в журнал
            # отката и в сейв, а узел сценария тянет за собой весь сценарий по цепочке .next
            # (сейв большой игры падал с RecursionError)
            $ _tm_mn = tm_cur_menu_name()
            if _tm_mn is not None:
                use tm_hints_panel(_tm_mn)
            else:
                $ _tm_cs = tm_cur_call_screen()
                if _tm_cs:
                    use tm_screen_hints(_tm_cs)
        if tm_ui.watch and tm_ui.hud_on:
            use tm_hud
        if tm_ui.mini:
            use tm_mini
        if tm_ui.auto:
            use tm_auto_badge
    if tm_ui.bug_pending:
        # меню уже спрятано — через пару кадров снимаем экран игры для заметки о баге
        timer 0.12 action Function(tm_bug_capture)
    if not main_menu:
        use tm_toasts

# ---------------------- плашка «идёт авто-прохождение» ----------------------
screen tm_auto_badge():
    frame at tm_zoomer(tm_k()):
        style "tm_hud_frame"
        xalign 0.5
        xoffset 0
        yalign 1.0
        yoffset -12
        padding (14, 6)
        hbox:
            spacing 10
            use tm_icon("rocket", 24)
            text tm_q(tm_auto_badge_text()) style "tm_hud_label"
            text (tm_keys_text() + u" — стоп") style "tm_hud_label" color "#8b93a3"

# ---------------------- свои уведомления ----------------------
transform tm_toast_fx(z=1.0):
    zoom z
    alpha 0.0
    yoffset -8
    easein 0.15 alpha 1.0 yoffset 0
    pause 2.6
    linear 0.5 alpha 0.0

screen tm_toasts():
    $ _ts = tm_toasts_live()
    if _ts:
        vbox:
            xalign 0.5
            ypos int((70 if tm_ui.mini else 10) * tm_k())
            spacing 6
            for _t, _msg, _kind in _ts:
                # цветная полоса слева = отступ внешней рамки, высота — по тексту
                frame at tm_toast_fx(tm_k()):
                    xalign 0.5
                    background Solid(TM_TOAST_COLORS.get(_kind, "#38e0c8"))
                    padding (6, 0, 0, 0)
                    frame:
                        background Solid("#0b0e14f2")
                        padding (14, 9, 18, 9)
                        text tm_q(_msg) style "tm_tip" size 18 xmaximum 900

# ---------------------- мини-режим: плашка с кнопками поверх игры ----------------------
screen tm_mini():
    $ _sl = tm_slots()
    frame at tm_zoomer(tm_k()):
        style "tm_hud_frame"
        xalign 0.5
        xoffset 0
        yoffset 12
        padding (10, 8)
        hbox:
            spacing 6
            use tm_icobtn("logo", Function(tm_unminimize), alt="TM")
            use tm_icobtn("back", Function(tm_rollback, 1), alt="<")
            use tm_icobtn("save", Function(tm_quick_save, 1), alt="S")
            use tm_icobtn("load", Function(tm_quick_load, 1), sens=_sl[1][0], alt="L")
            use tm_icobtn("skip", Function(tm_start_skip, "fast"), alt=">>")
            use tm_icobtn("eye", ToggleField(tm_ui, "hud_on"), sel=tm_ui.hud_on, alt="o")
            use tm_icobtn("close", SetField(tm_ui, "mini", False), alt="X")

# ---------------------- HUD наблюдения (не ловит клики) ----------------------
transform tm_flash_fx:
    alpha 1.0
    pause 2.2
    linear 0.6 alpha 0.0

screen tm_hud():
    $ _c = tm_hud_corner()
    frame at tm_zoomer(tm_k()):
        style "tm_hud_frame"
        xalign (0.0 if _c in ("tl", "bl") else 1.0)
        yalign (1.0 if _c in ("bl", "br") else 0.0)
        xoffset (16 if _c in ("tl", "bl") else -16)
        yoffset (-200 if _c in ("bl", "br") else 16)
        vbox:
            spacing 2
            for _l, _p in tm_ui.watch:
                $ _ok, _v = tm_probe(_p)
                $ _fl = tm_hud_flash(_p)
                hbox:
                    spacing 12
                    text tm_q(_tm_short(tm_nice(_l, _p)[0], 26)) style "tm_hud_label" min_width 210
                    text (tm_fmt(_v, 16) if _ok else u"—") style "tm_hud_value"
                    if _p in tm_ui.frozen:
                        if tm_ic("snow"):
                            add tm_ic("snow") zoom 0.3 yalign 0.5
                        else:
                            text "*" style "tm_hud_label" color "#9fd8ff"
                    if _fl:
                        text _fl[0] style "tm_hud_value" color _fl[1] at tm_flash_fx

# ---------------------- подсказки к выборам ----------------------
screen tm_hints_panel(node):
    # node — имя узла выбора (не сам узел: см. tm_overlay)
    $ _hs = tm_menu_hints_name(node)
    $ _show_hidden = tm_pref("tm_hints_hidden", True)
    $ _sp = tm_spoil()
    frame at tm_zoomer(tm_k()):
        style "tm_hint_frame"
        vbox:
            spacing 10
            hbox:
                spacing 10
                use tm_icon("hint", 26)
                text "Подсказки выбора" style "tm_hint_h" yalign 0.5
                text "Shift+H — скрыть" style "tm_foot" yalign 0.5
            for _i, _lbl, _cond, _effs in _hs:
                $ _vis = tm_cond_ok(_cond)
                if _vis or _show_hidden:
                    vbox:
                        spacing 2
                        hbox:
                            spacing 10
                            text tm_q(_tm_short(tm_choice_text(_lbl), 46)) style ("tm_hint_choice" if _vis else "tm_hint_hidden")
                            if not _vis:
                                textbutton "выбрать":
                                    style "tm_seg" text_style "tm_seg_text"
                                    text_size 15
                                    padding (10, 3)
                                    yalign 0.5
                                    action Function(tm_pick_choice, node, _i)
                            textbutton "код":
                                style "tm_seg" text_style "tm_seg_text"
                                text_size 14
                                padding (8, 2)
                                yalign 0.5
                                selected ((node, _i) in tm_ui.code_peek)
                                action Function(tm_code_toggle, (node, _i))
                        if (node, _i) in tm_ui.code_peek:
                            frame:
                                background Solid("#ffffff0a")
                                padding (10, 6)
                                text tm_q(tm_choice_code(node, _i)) style "tm_hint_eff" size 14 color "#9aa3b5"
                        if not _vis:
                            text (u"скрыт, условие: " + tm_q(_tm_short(_cond, 52))) style "tm_hint_note"
                            $ _now = tm_cond_now(_cond)
                            if _now:
                                text tm_q(_now) style "tm_hint_note" color "#c7a978"
                        if _sp == "full" or (node, _i) in tm_ui.peek:
                            text tm_hint_markup(_effs) style "tm_hint_eff"
                        elif _sp == "sign":
                            text tm_hint_sign(_effs) style "tm_hint_eff" size 20
                        else:
                            textbutton "показать последствия":
                                style "tm_seg" text_style "tm_seg_text"
                                text_size 14
                                padding (10, 2)
                                action Function(tm_peek_toggle, (node, _i))

# ---------------------- подсказки на экранах-развилках (call screen) ----------------------
screen tm_screen_hints(scr):
    $ _bs = tm_screen_rows(scr, 14)
    if _bs:
        frame at tm_zoomer(tm_k()):
            style "tm_hint_frame"
            vbox:
                spacing 6
                hbox:
                    spacing 10
                    use tm_icon("hint", 26)
                    text ("Кнопки экрана " + tm_q(scr)) style "tm_hint_h" yalign 0.5
                    text "Shift+H — скрыть" style "tm_foot" yalign 0.5
                for _bn, _scr, _lbl, _txt, _sens in _bs:
                    hbox:
                        spacing 10
                        text tm_q(_lbl) style ("tm_hint_choice" if _sens else "tm_hint_hidden") size 16 min_width 200
                        text tm_q(_tm_short(_txt, 50)) style "tm_hint_eff"

# ============================ main menu ============================
screen tm_menu():
    modal True
    zorder 200

    $ _w, _h = tm_win_size()
    $ _acc = tm_acc()
    $ _tip = GetTooltip()

    # --- проглатываем продвижение диалога, пока меню открыто (dismiss + модальность) ---
    key "dismiss" action NullAction()
    key "shift_K_t" action SetField(tm_ui, "open", False)
    if tm_alt_key():
        key tm_alt_key() action SetField(tm_ui, "open", False)
    key "game_menu" action SetField(tm_ui, "open", False)
    key "ctrl_K_z" action Function(tm_undo)
    if tm_ui.tab == "stats":
        key "K_PAGEUP" action Function(tm_stat_page, -1)
        key "K_PAGEDOWN" action Function(tm_stat_page, 1)

    # --- затемнение-ловушка: любой клик мимо окна съедается, в игру не идёт ---
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#05070bcc"
        action NullAction()

    # --- перетаскиваемое окно (хват — за шапку) ---
    draggroup:
        drag:
            drag_name "tm_window"
            draggable True
            drag_handle (0, 0, 1.0, int(56 * tm_k()))
            dragged tm_on_dragged
            if tm_ui.win_pos:
                pos tm_ui.win_pos
            else:
                xalign 0.5
                yalign 0.5

            # тонкая акцентная рамка вокруг окна (масштаб — под разрешение игры)
            frame at tm_pop(tm_k()):
                style "tm_border"
                padding (2, 2)

                frame:
                    style "tm_panel"
                    xsize _w
                    ysize _h

                    # fixed с явным размером: на 6.99 frame отдаёт ребёнку ширину экрана, а не
                    # свою (в 800x600 содержимое обрезалось справа); fixed берёт max(доступно, xsize)
                    fixed:
                        xsize _w
                        ysize _h
                        # side "t c b": шапка+вкладки сверху, футер снизу, контенту — остаток
                        # (раньше vbox + yfill выталкивал футер за пределы окна)
                        side "t c b":
                            vbox:
                                # ---------- шапка (зона перетаскивания) ----------
                                frame:
                                    style "tm_header_bg"
                                    xfill True
                                    padding (16, 8)
                                    fixed:
                                        xfill True
                                        ysize 38
                                        hbox:
                                            spacing 12
                                            yalign 0.5
                                            use tm_icon("logo", 34)
                                            # tm_q: «{» в заголовке игры иначе ломал текст-теги
                                            text tm_q(tm_title) style "tm_head_title" yalign 0.5
                                            text tm_engine_tag() style "tm_head_btn_text" color "#0a0c1099" bold False yalign 0.5
                                        hbox:
                                            spacing 8
                                            xalign 1.0
                                            yalign 0.5
                                            button:
                                                style "tm_head_btn"
                                                padding (6, 3)
                                                tooltip "Как пользоваться меню"
                                                action SetField(tm_ui, "help_open", True)
                                                if tm_ic("question"):
                                                    add tm_ic("question") zoom 0.45 align (0.5, 0.5)
                                                else:
                                                    text "?" style "tm_head_btn_text"
                                            textbutton "в центр":
                                                style "tm_head_btn" text_style "tm_head_btn_text"
                                                tooltip "Вернуть окно в центр экрана"
                                                action Function(tm_reset_pos)
                                            textbutton "свернуть":
                                                style "tm_head_btn" text_style "tm_head_btn_text"
                                                tooltip "Мини-режим: плашка с откатом, слотом 1, скипом и HUD поверх игры — с ней можно играть"
                                                action Function(tm_minimize)
                                            button:
                                                style "tm_head_btn"
                                                padding (6, 3)
                                                tooltip ("Закрыть меню (%s или Esc)" % tm_keys_text())
                                                action SetField(tm_ui, "open", False)
                                                if tm_ic("close"):
                                                    add tm_ic("close") zoom 0.45 align (0.5, 0.5)
                                                else:
                                                    text "X" style "tm_head_btn_text"

                                # ---------- вкладки ----------
                                frame:
                                    style "tm_tabbar_bg"
                                    xfill True
                                    padding (8, 6)
                                    hbox:
                                        spacing 2
                                        for _tk, _tl, _tt in tm_tabs():
                                            button:
                                                style "tm_tab_btn"
                                                selected (tm_ui.tab == _tk)
                                                tooltip _tt
                                                action [SetField(tm_ui, "tab", _tk), SetField(tm_ui, "confirm", "")]
                                                hbox:
                                                    spacing 5
                                                    use tm_icon(_tk, 26)
                                                    text _tl style "tm_tab_text" yalign 0.5
                                frame:
                                    xfill True
                                    ysize 2
                                    background Solid(_acc)

                            # ---------- контент ----------
                            frame:
                                background None
                                xfill True
                                yfill True
                                padding (26, 16, 26, 12)

                                if tm_ui.tab == "rewind":
                                    use tm_tab_rewind
                                elif tm_ui.tab == "stats":
                                    use tm_tab_stats
                                elif tm_ui.tab == "actions":
                                    use tm_tab_actions
                                elif tm_ui.tab == "scanner":
                                    use tm_tab_scanner
                                elif tm_ui.tab == "story":
                                    use tm_tab_story
                                elif tm_ui.tab == "checklist":
                                    use tm_tab_test
                                else:
                                    use tm_tab_settings

                            # ---------- футер: подсказка под курсором, иначе горячие клавиши ----------
                            frame:
                                style "tm_footer_bg"
                                xfill True
                                padding (18, 9)
                                if _tip:
                                    text tm_q(_tip) style "tm_tip"
                                else:
                                    text (tm_keys_text() + "  меню    Shift+H  подсказки    Shift+B  баг    Ctrl+Z  отмена    Esc  закрыть    Ctrl  скип") style "tm_foot"

    # ---------- попапы ----------
    if tm_ui.edit:
        use tm_edit_popup
    elif tm_ui.where_open:
        use tm_where_popup
    elif tm_ui.diag_open:
        use tm_diag_popup
    elif tm_ui.help_open:
        use tm_help_popup

# ---------------------- попап: ввод значения / имени ----------------------
screen tm_edit_popup():
    modal True
    zorder 300
    $ _kind, _path = tm_ui.edit
    # для имени/персонажа/заметки значение не читаем (в переменную экрана попал бы объект игры)
    $ _ok, _cur = tm_probe(_path) if _kind == "value" else (False, None)
    $ _lt = tm_lim_text(*tm_limits(_path)) if (isinstance(_cur, _TM_NUM) and not isinstance(_cur, bool)) else u""
    key "dismiss" action NullAction()
    key "game_menu" action Function(tm_edit_close)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000b0"
        action Function(tm_edit_close)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 760
            padding (24, 20)
            vbox:
                spacing 10
                text {"name": "Своё имя переменной", "char": "Своё имя персонажа", "bug": "Заметка о баге"}.get(_kind, "Новое значение") style "tm_h"
                if _kind == "bug":
                    text "Что не так? Место в сценарии, реплика, картинки, звук и скриншот запишутся сами — в tm_bugs/tm_bugs.md в папке игры." style "tm_dim" size 15
                elif _kind == "char":
                    text tm_q(u"%s — сейчас «%s». Пусто — вернуть исходное имя." % (_path, tm_str(getattr(getattr(store, _path, None), "name", u"")))) style "tm_dim" size 15
                else:
                    text tm_q(_path) style "tm_dim"
                if _kind == "value":
                    hbox:
                        spacing 12
                        text "сейчас:" style "tm_dim" yalign 0.5
                        text tm_fmt(_cur, 40) style "tm_value" yalign 0.5
                        if _lt:
                            text tm_q(u"границы " + _lt) style "tm_dim" yalign 0.5
                    if isinstance(_cur, bool):
                        text "да / нет (или 1 / 0)" style "tm_dim" size 15
                    elif isinstance(_cur, _TM_NUM):
                        text "+50, -10, *2, /2 — от текущего значения; =-5 — точно минус пять" style "tm_dim" size 15
                elif _kind == "name":
                    text "Пусто — вернуть автоматическое имя." style "tm_dim" size 15
                button:
                    style "tm_field"
                    xfill True
                    action tm_edit_iv.Enable()
                    input value tm_edit_iv style "tm_filter_text" size 22 length (240 if _kind == "bug" else 64)
                if tm_ui.edit_err:
                    text tm_q(tm_ui.edit_err) style "tm_bad" size 17
                hbox:
                    xalign 1.0
                    spacing 10
                    text "Enter — применить, Esc — отмена" style "tm_foot" yalign 0.5
                    textbutton "Отмена" style "tm_btn" text_style "tm_btn_text" action Function(tm_edit_close)
                    textbutton "Применить" style "tm_btn" text_style "tm_btn_text" action Function(tm_edit_apply)

# ---------------------- попап: где я ----------------------
screen tm_where_popup():
    modal True
    zorder 300
    $ _info = tm_where_info()
    key "dismiss" action NullAction()
    key "game_menu" action SetField(tm_ui, "where_open", False)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000b0"
        action SetField(tm_ui, "where_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 860
            padding (24, 20)
            vbox:
                spacing 10
                hbox:
                    spacing 10
                    use tm_icon("pin", 32)
                    text "Где я" style "tm_h" yalign 0.5
                for _t, _v in _info:
                    hbox:
                        spacing 14
                        text tm_q(_t) style "tm_dim" min_width 170
                        text tm_q(_v) style "tm_label" size 18 xmaximum 620
                hbox:
                    xalign 1.0
                    spacing 10
                    use tm_btn2("save", "Отчёт в файл", Function(tm_write_report), "Записать отчёт тестера (место, история выборов, правки) в папку игры")
                    textbutton "Закрыть" style "tm_btn" text_style "tm_btn_text" action SetField(tm_ui, "where_open", False)

# ---------------------- попап: как пользоваться ----------------------
screen tm_help_popup():
    modal True
    zorder 300
    key "dismiss" action NullAction()
    key "game_menu" action SetField(tm_ui, "help_open", False)
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000d0"
        action SetField(tm_ui, "help_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 900
            ysize 620
            padding (24, 20)
            fixed:
                xsize 852
                ysize 580
                side "t c b":
                    hbox:
                        spacing 14
                        $ _m = tm_mascot("wave")
                        if _m:
                            add _m zoom 0.42 yalign 0.5
                        vbox:
                            yalign 0.5
                            spacing 4
                            text "Как пользоваться меню" style "tm_h"
                            text "Коротко о каждой вкладке. Колесо мыши — прокрутка." style "tm_dim"
                    viewport:
                        scrollbars "vertical"
                        style_prefix "tm"
                        mousewheel True
                        yfill True
                        xfill True
                        vbox:
                            spacing 14
                            null height 6
                            for _ic, _t, _d in TM_HELP:
                                hbox:
                                    spacing 14
                                    use tm_icon(_ic, 34)
                                    vbox:
                                        spacing 3
                                        text _t style "tm_label" bold True
                                        text _d style "tm_dim" xmaximum 740
                    hbox:
                        xalign 1.0
                        spacing 10
                        text "Справка откроется снова по кнопке со знаком вопроса в шапке" style "tm_foot" yalign 0.5
                        textbutton "Понятно" style "tm_btn" text_style "tm_btn_text" action SetField(tm_ui, "help_open", False)

# ---------------------- попап: диагностика ----------------------
screen tm_diag_popup():
    modal True
    zorder 300
    button:
        style "tm_shade"
        xfill True
        yfill True
        background "#000000d0"
        action SetField(tm_ui, "diag_open", False)
    frame at tm_pop(tm_k()):
        style "tm_border"
        xalign 0.5
        yalign 0.5
        padding (2, 2)
        frame:
            style "tm_panel"
            xsize 780
            ysize 470
            padding (24, 20)
            side "t c b":
                vbox:
                    spacing 8
                    hbox:
                        spacing 10
                        use tm_icon("bug", 32)
                        text "Диагностика статов и действий" style "tm_h" yalign 0.5
                    if tm_ui.diag:
                        text ("Найдено проблем: %d" % len(tm_ui.diag)) style "tm_warn"
                        text "[[X] — не работает, [[!] — читается, но пусто (None)." style "tm_dim"
                    null height 4
                if not tm_ui.diag:
                    frame:
                        background None
                        xfill True
                        yfill True
                        use tm_empty("party", "Проблем не найдено: все пути статов читаются, код действий компилируется.")
                else:
                    viewport:
                        scrollbars "vertical"
                        style_prefix "tm"
                        mousewheel True
                        yfill True
                        xfill True
                        vbox:
                            spacing 6
                            for _p in tm_ui.diag:
                                text "[_p!q]" style "tm_label" size 18
                hbox:
                    xalign 1.0
                    textbutton "Закрыть" style "tm_btn" text_style "tm_btn_text" action SetField(tm_ui, "diag_open", False)

# ---------------------- вкладка: перемотка ----------------------
screen tm_tab_rewind():
    $ _sl = tm_slots()
    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 18

            # --- назад ---
            vbox:
                spacing 8
                text "Перемотка назад" style "tm_h"
                text "Откат истории вместе с переменными. Колесо мыши вверх делает то же и без меню." style "tm_dim"
                hbox:
                    spacing 14
                    use tm_btn2("back", "Назад ×10", Function(tm_rollback, 10), "Откатить 10 шагов истории")
                    use tm_btn2("back", "Назад ×1", Function(tm_rollback, 1), "Откатить один шаг истории")
                    use tm_btn2("skip", "Вперёд ×1", RollForward(), "Вернуться вперёд после отката (те же выборы)")

            # --- лог реплик: откат прямо к нужной ---
            vbox:
                spacing 6
                text "Последние реплики" style "tm_h"
                $ _dl = tm_dialog_log(10)
                if not _dl:
                    text "История реплик пуста (или игра её отключила)." style "tm_dim"
                for _dw, _dt, _di in _dl:
                    hbox:
                        spacing 10
                        textbutton "сюда":
                            style "tm_seg" text_style "tm_seg_text"
                            text_size 15
                            padding (10, 3)
                            yalign 0.5
                            sensitive (_di is not None)
                            tooltip "Откатить игру к этой реплике (вместе с переменными)"
                            action RollbackToIdentifier(_di)
                        text tm_q(_dw) style "tm_dim" size 16 min_width 150 yalign 0.5
                        text tm_q(_dt) style "tm_label" size 17 yalign 0.5 xmaximum 640

            use tm_sep

            # --- быстрые слоты ---
            vbox:
                spacing 8
                text "Быстрые слоты" style "tm_h"
                text "Мгновенное сохранение/загрузка. Отдельные от обычных сейвов игры." style "tm_dim"
                for _sn in (1, 2, 3):
                    hbox:
                        spacing 12
                        text ("Слот %d" % _sn) style "tm_label" yalign 0.5 min_width 90
                        use tm_btn2("save", "Сохранить", Function(tm_quick_save, _sn), "Сохранить игру в слот %d" % _sn)
                        use tm_btn2("load", "Загрузить", Function(tm_quick_load, _sn), "Загрузить слот %d" % _sn, _sl[_sn][0])
                        text _sl[_sn][1] style "tm_dim" yalign 0.5
                if _sl[0][0]:
                    hbox:
                        spacing 12
                        text "Перед прыжком" style "tm_label" yalign 0.5 min_width 90
                        use tm_btn2("load", "Вернуться", Function(tm_quick_load, 0), "Сейв, сделанный автоматически перед переходом к метке, реплике или скрытому выбору")
                        text _sl[0][1] style "tm_dim" yalign 0.5

            use tm_sep

            # --- журнал правок ---
            vbox:
                spacing 8
                hbox:
                    spacing 12
                    text "Правки из меню" style "tm_h" yalign 0.5
                    if tm_ui.journal:
                        textbutton "отменить последнюю" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Ctrl+Z" action Function(tm_undo)
                        textbutton ("Точно? Ещё раз" if tm_ui.confirm == "undo_all" else "отменить все (%d)" % len(tm_ui.journal)):
                            style "tm_seg" text_style "tm_seg_text"
                            yalign 0.5
                            selected (tm_ui.confirm == "undo_all")
                            tooltip "Вернуть все значения, изменённые из меню, как были"
                            action Function(tm_confirm, "undo_all", tm_undo_all)
                if not tm_ui.journal:
                    text "Пока ничего не меняли. Каждая правка значения запоминается и отменяется (Ctrl+Z)." style "tm_dim"
                else:
                    for _jp, _jo, _jn in reversed(tm_ui.journal[-8:]):
                        hbox:
                            spacing 12
                            text tm_q(_tm_short(tm_nice(_jp, _jp)[0], 34)) style "tm_label" size 18 min_width 360
                            text (tm_fmt(_jo, 14) + u"  →  " + tm_fmt(_jn, 14)) style "tm_value" size 18

            use tm_sep

            # --- вперёд / авто-пропуск ---
            vbox:
                spacing 8
                text "Пропуск вперёд" style "tm_h"
                text "Кнопка ниже мгновенно проматывает весь текст, в том числе непрочитанный. Либо зажмите Ctrl; Tab включает/выключает скип." style "tm_dim"
                hbox:
                    spacing 14
                    use tm_btn2("skip", "Скип всего текста", [SetField(tm_ui, "open", False), Function(tm_start_skip, "fast")], "Мгновенный скип до следующего выбора (настройки скипа потом вернутся)")
                    textbutton ("Авто-пропуск: ВКЛ" if _preferences.afm_enable else "Авто-пропуск: выкл"):
                        style "tm_btn" text_style "tm_btn_text"
                        tooltip "Реплики листаются сами (скорость — ползунком ниже)"
                        action [ToggleField(_preferences, "afm_enable"), SetField(tm_ui, "open", False)]
                hbox:
                    spacing 14
                    textbutton ("Ctrl пропускает и непрочитанное: ВКЛ" if _preferences.skip_unseen else "Ctrl пропускает и непрочитанное: выкл"):
                        style "tm_seg" text_style "tm_seg_text"
                        selected _preferences.skip_unseen
                        tooltip "Это настройка самой игры «Пропускать непрочитанное» — она останется и без меню"
                        action Function(tm_toggle_skip_unseen)

                null height 4
                # скорость авто-пропуска
                hbox:
                    spacing 14
                    text "Скорость авто-пропуска" style "tm_label" yalign 0.5 min_width 300
                    bar value Preference("auto-forward time") style "tm_bar" yalign 0.5
                text "Правее — быстрее авто-переход между репликами." style "tm_dim"

                null height 4
                # скорость появления текста
                hbox:
                    spacing 14
                    text "Скорость текста" style "tm_label" yalign 0.5 min_width 300
                    bar value Preference("text speed") style "tm_bar" yalign 0.5
                text "Правее — текст появляется быстрее (в самом правом — мгновенно)." style "tm_dim"

# ---------------------- вкладка: характеристики ----------------------
screen tm_tab_stats():
    $ _mode = tm_stats_mode()
    $ _rows, _page, _pages, _total = tm_stat_rows(tm_ui.stat_filter)
    $ _acc = tm_acc()
    vbox:
        spacing 12
        fixed:
            xfill True
            ysize 44
            hbox:
                spacing 10
                yalign 0.5
                text "Переменные" style "tm_h" yalign 0.5
                null width 6
                # источник: data-файл игры или авто-поиск (переключатель — только если data есть)
                if getattr(store, "tm_stats", None):
                    textbutton "из data" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (_mode == "data") tooltip "Список статов, заданный для этой игры в студии" action Function(tm_set_stats_mode, "data")
                textbutton "авто" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (_mode == "auto") tooltip "Меню само нашло переменные игры" action Function(tm_set_stats_mode, "auto")
                if _mode == "auto":
                    use tm_icobtn("back", Function(tm_auto_rebuild), tip="Пересобрать список (игра могла завести новые переменные)", alt="R")
                use tm_icobtn("bug", Function(tm_diag_run), tip="Проверить: все ли пути читаются и в границах", alt="?")
                use tm_icobtn("download", Function(tm_values_export), tip="Сохранить значения списка и избранного в tm_values.json (папка игры) — для переноса в другую партию", alt="S")
                use tm_icobtn("upload", Function(tm_values_import), tip="Загрузить значения из tm_values.json: те же переменные получат сохранённые значения (Ctrl+Z отменяет)", alt="L")
                if tm_ui.journal:
                    $ _jp, _jo, _jn = tm_ui.journal[-1]
                    textbutton ("отменить (%d)" % len(tm_ui.journal)):
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        tooltip (u"Ctrl+Z — вернуть %s = %s" % (tm_nice(_jp, _jp)[0], tm_fmt(_jo, 20)))
                        action Function(tm_undo)
                if tm_ui.frozen:
                    button:
                        style "tm_seg"
                        yalign 0.5
                        tooltip "Снять все заморозки"
                        action Function(tm_freeze_clear)
                        hbox:
                            spacing 6
                            use tm_icon("snow", 22)
                            text ("%d  снять" % len(tm_ui.frozen)) style "tm_seg_text" yalign 0.5
                    textbutton "в профиль":
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        tooltip "Профиль игры: эти заморозки будут ставиться сами при каждом запуске"
                        action Function(tm_profile_save)
                if tm_profile_size():
                    textbutton ("профиль %d: убрать" % tm_profile_size()):
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        tooltip "Удалить профиль игры (текущие заморозки не снимаются)"
                        action Function(tm_profile_clear)
            hbox:
                spacing 8
                xalign 1.0
                yalign 0.5
                text "шаг" style "tm_dim" yalign 0.5
                for s in (1, 5, 10, 50):
                    textbutton "[s]":
                        style "tm_seg" text_style "tm_seg_text"
                        yalign 0.5
                        selected (tm_ui.stat_step == s)
                        tooltip "Шаг кнопок − и +"
                        action SetField(tm_ui, "stat_step", s)

        # --- фильтр + страницы ---
        hbox:
            spacing 10
            use tm_icon("scanner", 26)
            use tm_field("stat_filter", 300, 30)
            if tm_ui.stat_filter:
                use tm_icobtn("close", [SetField(tm_ui, "stat_filter", ""), SetField(tm_ui, "stat_page", 0)], tip="Очистить фильтр", alt="X")
            text ("найдено: %d" % _total) style "tm_dim" yalign 0.5
            if tm_ui.deltas:
                textbutton ("изменённые: %d" % len(tm_ui.deltas)):
                    style "tm_seg" text_style "tm_seg_text"
                    yalign 0.5
                    selected tm_ui.only_changed
                    tooltip "Только то, что игра изменила с прошлого открытия меню"
                    action Function(tm_toggle_only_changed)
            if _pages > 1:
                textbutton "‹" style "tm_icon_btn" text_style "tm_icon_text" sensitive (_page > 0) action Function(tm_stat_page, -1)
                text ("%d / %d" % (_page + 1, _pages)) style "tm_dim" yalign 0.5
                textbutton "›" style "tm_icon_btn" text_style "tm_icon_text" sensitive (_page < _pages - 1) action Function(tm_stat_page, 1)

        use tm_sep

        if not _rows:
            if tm_ui.only_changed:
                use tm_empty("search", "Среди переменных списка изменённых нет (изменилось что-то вне списка — ищи на вкладке «Поиск»).")
            elif tm_ui.stat_filter:
                use tm_empty("search", "Ничего не найдено по фильтру.")
            else:
                use tm_empty("think", "Переменных не найдено. Начни игру (авто-поиск видит переменные текущей партии) или найди нужное на вкладке «Поиск».")
        else:
            viewport:
                scrollbars "vertical"
                style_prefix "tm"
                mousewheel True
                yfill True
                xfill True
                vbox:
                    spacing 6
                    for _r in _rows:
                        $ label, path = _r[0], _r[1]
                        if not path:
                            null height 4
                            hbox:
                                spacing 12
                                text "[label!q]" style "tm_dim" size 18 color _acc yalign 0.5
                                if len(_r) > 2 and _r[2] == "svc":
                                    textbutton ("свернуть" if tm_ui.show_service else "показать"):
                                        style "tm_seg" text_style "tm_seg_text"
                                        yalign 0.5
                                        tooltip "Переменные, которые сценарий не меняет и не проверяет"
                                        action Function(tm_toggle_service)
                        else:
                            $ _ok, val = tm_probe(path)
                            $ _num = isinstance(val, _TM_NUM) and not isinstance(val, bool)
                            $ _lt, _out, _cdn, _cup = tm_stat_view(path, val) if _num else (u"", False, True, True)
                            $ _nice, _mean, _tip = tm_row_info(label, path)
                            hbox:
                                spacing 8
                                use tm_icobtn("star", Function(tm_fav_toggle, path), sel=tm_is_fav(path), tip="Избранное: закрепить наверху списка (запоминается для этой игры)", alt="*")
                                use tm_icobtn("eye", Function(tm_watch_toggle, label, path), sel=tm_watched(path), tip="Показывать в HUD поверх игры", alt="o")
                                button:
                                    style "tm_name_btn"
                                    xsize 270
                                    yalign 0.5
                                    tooltip _tip
                                    action Function(tm_rename, path, _nice)
                                    vbox:
                                        text tm_q(_tm_short(_nice, 30)) style "tm_label"
                                        text tm_q(_tm_short(_mean if _nice == path else (path + u" | " + _mean), 40)) style "tm_dim" size 14 layout "nobreak"
                                $ _dt = tm_delta_text(path)
                                hbox:
                                    xminimum 200
                                    spacing 8
                                    yalign 0.5
                                    if not _ok:
                                        text "путь не найден" style "tm_bad" yalign 0.5
                                    elif val is None:
                                        text "None" style "tm_warn" yalign 0.5
                                    else:
                                        text tm_fmt(val, 12) style ("tm_warn" if _out else "tm_value") yalign 0.5
                                    if _dt:
                                        text tm_q(_dt[0]) style "tm_dim" size 15 color _dt[1] bold True yalign 0.5
                                    if _lt:
                                        text tm_q(_lt) style "tm_dim" size 15 color ("#ffb454" if _out else "#6b7385") yalign 0.5
                                if isinstance(val, bool):
                                    textbutton ("ВКЛ" if val else "выкл"):
                                        style "tm_btn" text_style "tm_btn_text"
                                        action Function(tm_toggle, path)
                                    use tm_icobtn("snow", Function(tm_freeze_toggle, path), sel=(path in tm_ui.frozen), tip="Заморозить флаг: игра не сможет его переключить", alt="*")
                                elif _num:
                                    textbutton "−" style "tm_pm_btn" text_style "tm_pm_text" sensitive _cdn tooltip ("Уже минимум" if not _cdn else "Уменьшить на шаг") action Function(tm_add, path, -tm_ui.stat_step)
                                    textbutton "+" style "tm_pm_btn" text_style "tm_pm_text" sensitive _cup tooltip ("Уже максимум" if not _cup else "Увеличить на шаг") action Function(tm_add, path, tm_ui.stat_step)
                                    textbutton "ввод" style "tm_btn" text_style "tm_btn_text" tooltip "Ввести точное значение" action Function(tm_input, path)
                                    use tm_icobtn("snow", Function(tm_freeze_toggle, path), sel=(path in tm_ui.frozen), tip="Заморозить: игра не сможет изменить значение", alt="*")
                                    if path in tm_ui.frozen:
                                        textbutton tm_freeze_sign(path):
                                            style "tm_pm_btn" text_style "tm_pm_text"
                                            tooltip "Вид заморозки (щёлкни, чтобы сменить): = ровно это значение, ≥ не меньше, ≤ не больше"
                                            action Function(tm_freeze_cycle, path)
                                    $ _nt = tm_next_threshold(path, val)
                                    if _nt is not None:
                                        use tm_icobtn("target", Function(tm_to_threshold, path, _nt), tip=(u"Поставить %s — следующий порог из условий сценария" % _nt), alt=">")
                                elif _ok:
                                    textbutton "изменить" style "tm_btn" text_style "tm_btn_text" action Function(tm_input, path)
                                    if isinstance(val, _TM_STR):
                                        use tm_icobtn("snow", Function(tm_freeze_toggle, path), sel=(path in tm_ui.frozen), tip="Заморозить строку: игра не сможет её изменить", alt="*")

# ---------------------- вкладка: действия ----------------------
screen tm_tab_actions():
    $ _acc = tm_acc()
    vbox:
        spacing 10
        # ---- свой код ----
        hbox:
            spacing 10
            use tm_icon("code", 30)
            text "Свой код" style "tm_h" yalign 0.5
            text "выражение — покажет значение, команда — выполнит (money += 100). Enter — выполнить" style "tm_dim" size 15 yalign 0.5
        hbox:
            spacing 10
            button:
                style "tm_field"
                xsize 720
                action tm_code_iv.Enable()
                input value tm_code_iv style "tm_filter_text" length 300 copypaste True
            textbutton "Выполнить" style "tm_btn" text_style "tm_btn_text" tooltip "Выполнить в пространстве игры (как консоль Ren'Py)" action Function(tm_code_run)
        if tm_ui.code_hist:
            vbox:
                spacing 2
                for _cc, _cr, _cb in reversed(tm_ui.code_hist[-4:]):
                    hbox:
                        spacing 10
                        textbutton tm_q(_tm_short(_cc, 40)):
                            style "tm_name_btn"
                            text_style "tm_dim"
                            text_size 15
                            tooltip "Выполнить ещё раз"
                            action Function(tm_code_again, _cc)
                        text tm_q(_cr) style ("tm_bad" if _cb else "tm_value") size 15 yalign 0.5 xmaximum 560

        use tm_sep

        # ---- готовые действия игры ----
        fixed:
            xfill True
            ysize 44
            hbox:
                spacing 10
                yalign 0.5
                use tm_icon("coins", 32)
                text "Выдать" style "tm_h" yalign 0.5
            if tm_actions:
                hbox:
                    spacing 10
                    xalign 1.0
                    yalign 0.5
                    text "кол-во" style "tm_dim" yalign 0.5
                    for q in (1, 5, 10, 25):
                        textbutton "×[q]":
                            style "tm_seg" text_style "tm_seg_text"
                            selected (tm_ui.give_qty == q)
                            tooltip "Сколько раз выполнить действие"
                            action SetField(tm_ui, "give_qty", q)

        if not tm_actions:
            use tm_empty("sleep", "Готовых действий для этой игры нет — их задают в студии (вкладка «Действия»). Свой код выше работает всегда.")
        else:
            hbox:
                spacing 10
                use tm_icon("scanner", 26)
                use tm_field("act_filter", 320, 24)
                if tm_ui.act_filter:
                    use tm_icobtn("close", SetField(tm_ui, "act_filter", ""), tip="Очистить фильтр", alt="X")
            $ _qa = tm_ui.act_filter.strip().lower()
            viewport:
                scrollbars "vertical"
                style_prefix "tm"
                mousewheel True
                yfill True
                xfill True
                vbox:
                    spacing 8
                    for label, code in tm_actions:
                        if not code:
                            if not _qa:
                                null height 6
                                text "[label!q]" style "tm_dim" size 18 color _acc
                        elif (not _qa) or (_qa in label.lower()):
                            textbutton "[label!q]":
                                style "tm_btn" text_style "tm_btn_text"
                                tooltip _tm_short(code, 90)
                                action Function(tm_run, code, tm_ui.give_qty)

# ---------------------- вкладка: сканер ----------------------
screen tm_tab_scanner():
    $ _s = tm_scan_view()
    vbox:
        spacing 10
        fixed:
            xfill True
            ysize 44
            text "Найти переменную" style "tm_h" yalign 0.5
            hbox:
                spacing 10
                xalign 1.0
                yalign 0.5
                text "тип" style "tm_dim" yalign 0.5
                for _m, _lbl in [("num", "числа"), ("str", "строки"), ("all", "всё")]:
                    textbutton "[_lbl]":
                        style "tm_seg" text_style "tm_seg_text"
                        selected (_s["mode"] == _m)
                        action Function(tm_scan_set_mode, _m)
        text "Как ArtMoney, но по именам: снимок → измени стат в игре (закрой меню, поиграй) → «изменились». Повторяй, пока не останется искомое. Затем «в Переменные»." style "tm_dim"

        hbox:
            spacing 10
            use tm_btn2("camera", "Снимок / сброс", Function(tm_scan_snapshot), "Запомнить все значения игры сейчас")
            use tm_btn2("close", "Очистить", Function(tm_scan_reset), "Забыть снимок и кандидатов")
            use tm_btn2("back", "Шаг назад", Function(tm_scan_back), "Отменить последнее сужение", sens=_s["hist"])

        hbox:
            spacing 10
            textbutton "изменились" style "tm_seg" text_style "tm_seg_text" tooltip "Оставить то, что поменялось с прошлого шага" action Function(tm_scan_narrow, "changed")
            textbutton "не изменились" style "tm_seg" text_style "tm_seg_text" tooltip "Оставить то, что осталось прежним" action Function(tm_scan_narrow, "same")
            textbutton "стало больше" style "tm_seg" text_style "tm_seg_text" action Function(tm_scan_narrow, "up")
            textbutton "стало меньше" style "tm_seg" text_style "tm_seg_text" action Function(tm_scan_narrow, "down")

        hbox:
            spacing 10
            text "Значение:" style "tm_dim" yalign 0.5
            use tm_field("scan_val", 170, 24)
            textbutton "= равно" style "tm_btn" text_style "tm_btn_text" tooltip "Оставить переменные с ровно таким значением" action Function(tm_scan_equals, tm_ui.scan_val)
            textbutton "содержит" style "tm_btn" text_style "tm_btn_text" tooltip "Строки, в которых есть этот текст" action Function(tm_scan_contains, tm_ui.scan_val)
            textbutton "изменилось на" style "tm_btn" text_style "tm_btn_text" tooltip "Разница с прошлым шагом ровно это число (потратил 50 — введи -50)" action Function(tm_scan_by, tm_ui.scan_val)
            textbutton "в имени" style "tm_btn" text_style "tm_btn_text" tooltip "Переменные, в имени (пути) которых есть этот текст: money, love, girls" action Function(tm_scan_name, tm_ui.scan_val)

        use tm_sep
        $ _msg = _s["msg"]
        $ _trail = tm_scan_trail()
        hbox:
            spacing 16
            text "[_msg!q]" style "tm_value" size 19
            if _trail and u"→" in _trail:
                text tm_q(_trail) style "tm_dim" size 16 yalign 0.5

        if not _s["n"]:
            use tm_empty("wait", "Кандидатов пока нет. Нажми «Снимок», поиграй и возвращайся сужать.")
        elif _s["n"] > 80:
            $ _n = _s["n"]
            text "Слишком много ([_n]). Сужай кнопками выше, пока не станет ≤ 80." style "tm_dim"
        else:
            viewport:
                scrollbars "vertical"
                style_prefix "tm"
                mousewheel True
                yfill True
                xfill True
                vbox:
                    spacing 6
                    for _p, _o, _c in _s["rows"]:
                        $ _nm = tm_nice(_p, _p)[0]
                        hbox:
                            spacing 10
                            vbox:
                                yalign 0.5
                                xminimum 390
                                text tm_q(_tm_short(_nm, 36)) style "tm_label" size 18
                                if _nm != _p:
                                    text tm_q(_tm_short(_p, 48)) style "tm_dim" size 14
                            text (tm_fmt(_o, 9) + u" → " + tm_fmt(_c, 9)) style "tm_value" size 18 yalign 0.5 min_width 180
                            textbutton "ввод" style "tm_btn" text_style "tm_btn_text" action Function(tm_input, _p)
                            textbutton "в Переменные" style "tm_btn" text_style "tm_btn_text" tooltip (u"Закрепить на вкладке «Переменные» под именем «%s» (до выхода из игры; имя можно сменить щелчком)" % _nm) action Function(tm_scan_add, _p)

# ---------------------- вкладка: сюжет ----------------------
screen tm_tab_story():
    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 14

            # ---- подсказки выборов ----
            hbox:
                spacing 10
                use tm_icon("hint", 30)
                text "Подсказки к выборам" style "tm_h" yalign 0.5
            text "Когда на экране выбор, слева сверху видно, что изменит каждый вариант (+/− переменные, переходы). Варианты, скрытые условием, тоже видны — их можно выбрать." style "tm_dim"
            hbox:
                spacing 12
                textbutton ("Подсказки: ВКЛ" if tm_pref("tm_hints", True) else "Подсказки: выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected tm_pref("tm_hints", True)
                    action Function(tm_toggle_hints)
                textbutton ("Скрытые варианты: видны" if tm_pref("tm_hints_hidden", True) else "Скрытые варианты: нет"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected tm_pref("tm_hints_hidden", True)
                    action Function(tm_toggle_pref, "tm_hints_hidden", True)
                text "Shift+H" style "tm_dim" yalign 0.5
            hbox:
                spacing 8
                text "Последствия:" style "tm_dim" yalign 0.5
                for _sk, _sl in TM_SPOIL_MODES:
                    textbutton _sl:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_spoil() == _sk)
                        tooltip "Сколько подсказка выдаёт заранее: всё, только знак +/−, или по щелчку на варианте"
                        action Function(tm_set_spoil, _sk)

            use tm_sep

            # ---- история выборов ----
            hbox:
                spacing 10
                use tm_icon("story", 30)
                text "История выборов" style "tm_h" yalign 0.5
                textbutton ("запись: ВКЛ" if tm_pref("tm_history", True) else "запись: выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    yalign 0.5
                    selected tm_pref("tm_history", True)
                    tooltip "Запоминать выборы и то, что каждый реально изменил (за эту сессию)"
                    action Function(tm_toggle_pref, "tm_history", True)
                if tm_ui.history:
                    textbutton "очистить" style "tm_seg" text_style "tm_seg_text" yalign 0.5 action Function(tm_hist_clear)
            if not tm_ui.history:
                text "Сделай выбор в игре — здесь появится, что он изменил на самом деле (снимок до и после)." style "tm_dim"
            for _h in reversed(tm_ui.history[-12:]):
                vbox:
                    spacing 2
                    hbox:
                        spacing 10
                        text tm_q(u"«%s»" % _h["text"]) style "tm_label" size 18
                        if _h["where"]:
                            text tm_q(_h["where"]) style "tm_dim" size 14 yalign 0.5
                    if not _h["eff"]:
                        text "ничего не изменил (или изменил то, что меню не видит)" style "tm_dim" size 15
                    else:
                        text tm_hist_markup(_h) style "tm_hint_eff" xmaximum 900

            use tm_sep

            # ---- кнопки экранов ----
            $ _sb = tm_screen_rows(None, 40, "tab")
            hbox:
                spacing 10
                use tm_icon("target", 30)
                text "Кнопки на экране" style "tm_h" yalign 0.5
            text "Кнопки показанных экранов игры (карты, телефон, call screen) и что они делают. «нажать» — как щелчок, перед этим сохраняется «Перед прыжком»." style "tm_dim"
            if not _sb:
                text "Сейчас на экране нет кнопок игры с действиями." style "tm_dim" size 15
            for _bn, _scr, _lbl, _txt, _sens in _sb:
                hbox:
                    spacing 10
                    text tm_q(_scr) style "tm_dim" size 14 min_width 140 yalign 0.5
                    text tm_q(_lbl) style ("tm_label" if _sens else "tm_dim") size 17 min_width 230 yalign 0.5
                    text tm_q(_tm_short(_txt, 46)) style "tm_hint_eff" min_width 330 yalign 0.5
                    textbutton "нажать" style "tm_seg" text_style "tm_seg_text" yalign 0.5 action Function(tm_press_n, "tab", _bn)

            use tm_sep

            # ---- навигация ----
            hbox:
                spacing 12
                use tm_icon("target", 30)
                text "Навигация" style "tm_h" yalign 0.5
                use tm_btn2("pin", "Где я", Function(tm_where_am_i), "Файл, строка и метка текущего места")
            text "Перед переходом меню само сохраняет игру в слот «Перед прыжком» (вкладка «Перемотка»)." style "tm_dim"
            hbox:
                spacing 10
                text "Метка" style "tm_label" yalign 0.5 min_width 110
                use tm_field("jump_label", 340, 60)
                textbutton ("Повторить" if tm_ui.jump_mode == "replay" else "Перейти") style "tm_btn" text_style "tm_btn_text" action Function(tm_label_go, tm_ui.jump_label)
                textbutton "прыжок" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (tm_ui.jump_mode == "jump") tooltip "Перейти на метку: игра продолжится оттуда" action SetField(tm_ui, "jump_mode", "jump")
                textbutton "повтор" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (tm_ui.jump_mode == "replay") tooltip "Повтор сцены, как в галерее: посмотреть и вернуться сюда же, переменные игры не меняются. Выход — End Replay в меню игры" action SetField(tm_ui, "jump_mode", "replay")
            $ _labs = tm_labels(tm_ui.jump_label)
            if _labs:
                hbox:
                    box_wrap True
                    spacing 8
                    for _ln in _labs:
                        textbutton "[_ln!q]" style "tm_seg" text_style "tm_seg_text" action Function(tm_label_go, _ln)

            hbox:
                spacing 10
                text "Реплика" style "tm_label" yalign 0.5 min_width 110
                use tm_field("find_text", 340, 60)
                text "от 3 букв — переход прямо к строке" style "tm_dim" yalign 0.5
            $ _found = tm_find_lines(tm_ui.find_text)
            if _found:
                vbox:
                    spacing 4
                    for _nm, _fn, _ln, _who, _what in _found:
                        button:
                            style "tm_btn"
                            xfill True
                            action Function(tm_goto_node, _nm)
                            hbox:
                                spacing 12
                                text ("%s:%d" % (_fn.split("/")[-1], _ln)) style "tm_btn_text" size 15 color "#8b93a3" min_width 190 yalign 0.5
                                text tm_q(_tm_short((_who + ": " if _who else "") + _what, 70)) style "tm_btn_text" size 17 yalign 0.5
            elif len(tm_ui.find_text.strip()) >= 3:
                text "Не найдено." style "tm_dim"

            use tm_sep

            # ---- галерея / persistent ----
            hbox:
                spacing 10
                use tm_icon("trophy", 30)
                text "Галерея и флаги" style "tm_h" yalign 0.5
            text "«Открыть галерею» отмечает всё просмотренным: Replay-сцены, Gallery и Music Room стандартного вида. Меняет persistent игры навсегда." style "tm_dim"
            use tm_btn2("trophy", ("Точно? Нажми ещё раз" if tm_ui.confirm == "unlock" else "Открыть всю галерею"), Function(tm_confirm, "unlock", tm_unlock_all), "Второй щелчок подтверждает", sel=(tm_ui.confirm == "unlock"))
            hbox:
                spacing 10
                text "Persistent" style "tm_label" yalign 0.5 min_width 110
                use tm_field("flag_filter", 340, 30)
                text "флаги концовок, галерей, бонусов" style "tm_dim" yalign 0.5
            $ _flags = tm_persistent_flags(tm_ui.flag_filter)
            if not _flags:
                text "Числовых и булевых persistent-переменных не найдено." style "tm_dim"
            for _p, _v in _flags:
                hbox:
                    spacing 8
                    text tm_q(_tm_short(_p[11:], 32)) style "tm_label" yalign 0.5 min_width 340
                    text tm_fmt(_v, 12) style "tm_value" yalign 0.5 min_width 130
                    if isinstance(_v, bool):
                        textbutton ("ВКЛ" if _v else "выкл") style "tm_btn" text_style "tm_btn_text" action Function(tm_toggle, _p)
                    else:
                        textbutton "−" style "tm_pm_btn" text_style "tm_pm_text" action Function(tm_add, _p, -tm_ui.stat_step)
                        textbutton "+" style "tm_pm_btn" text_style "tm_pm_text" action Function(tm_add, _p, tm_ui.stat_step)
                        textbutton "ввод" style "tm_btn" text_style "tm_btn_text" action Function(tm_input, _p)

            use tm_sep

            # ---- персонажи: свои имена ----
            hbox:
                spacing 10
                use tm_icon("stats", 30)
                text "Персонажи" style "tm_h" yalign 0.5
            text "Своё имя персонажа в репликах (запоминается для этой игры, «Убрать следы меню» вернёт исходные). Если игра хранит персонажа внутри своих объектов, имя попадёт и в её сейв." style "tm_dim"
            $ _chs = tm_characters()
            if not _chs:
                text "Персонажей с постоянным именем не найдено." style "tm_dim" size 15
            hbox:
                box_wrap True
                spacing 8
                for _cv, _cn, _cown in _chs:
                    textbutton tm_q(_tm_short(_cn, 20)):
                        style "tm_seg" text_style "tm_seg_text"
                        selected _cown
                        tooltip (u"%s — щёлкни, чтобы переименовать" % _cv)
                        action Function(tm_edit_char, _cv)

# ---------------------- вкладка: тест ----------------------
# В переменных экрана — только строки и числа (они пишутся в журнал отката и в сейв).
screen tm_tab_test():
    $ _cov = tm_coverage()
    $ _say, _lab, _chc = tuple(_cov["say"]), tuple(_cov["label"]), tuple(_cov["choice"])
    $ _cov = None
    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 12

            # ---- авто-прохождение ----
            hbox:
                spacing 10
                use tm_icon("rocket", 30)
                text "Авто-прохождение" style "tm_h" yalign 0.5
            text "Меню само листает текст и отвечает на выборы: проверить, что игра не падает, и открыть новые ветки. Перед стартом — сейв «Перед прыжком». Остановить — клавиша меню." style "tm_dim"
            hbox:
                spacing 8
                text "Выбирать:" style "tm_dim" yalign 0.5 min_width 150
                for _mk, _ml in TM_AUTO_MODES:
                    textbutton _ml:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_ui.auto_mode == _mk)
                        tooltip "Новые — сначала варианты, которых ещё ни разу не выбирали (за все партии): так быстрее растёт покрытие"
                        action SetField(tm_ui, "auto_mode", _mk)
            hbox:
                spacing 8
                text "Выборов:" style "tm_dim" yalign 0.5 min_width 150
                for _lk, _ll in TM_AUTO_LIMITS:
                    textbutton _ll:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_ui.auto_limit == _lk)
                        action SetField(tm_ui, "auto_limit", _lk)
            hbox:
                spacing 8
                text "Стоп на метке:" style "tm_dim" yalign 0.5 min_width 150
                use tm_field("auto_stop_label", 260, 60)
                textbutton ("на новой реплике: стоп" if tm_ui.auto_stop_unseen else "на новой реплике: дальше"):
                    style "tm_seg" text_style "tm_seg_text"
                    yalign 0.5
                    selected tm_ui.auto_stop_unseen
                    tooltip "Остановиться на первой реплике, которую ещё ни разу не видели, — «довези до нового контента»"
                    action ToggleField(tm_ui, "auto_stop_unseen")
            hbox:
                spacing 12
                use tm_btn2("rocket", "Запустить", Function(tm_auto_start), "Пошло: меню закроется, игра поедет сама")
                if tm_ui.auto_log:
                    textbutton "очистить журнал" style "tm_seg" text_style "tm_seg_text" yalign 0.5 action SetField(tm_ui, "auto_log", [])
            for _al in tm_ui.auto_log[-6:]:
                text tm_q(_al) style "tm_dim" size 15

            use tm_sep

            # ---- маршруты ----
            hbox:
                spacing 10
                use tm_icon("flag", 30)
                text "Маршруты" style "tm_h" yalign 0.5
            text "Выборы партии записываются сами (с начала игры или с загрузки сейва; откат стирает отменённые). Сохрани маршрут — после обновления игры или в новой партии меню пройдёт те же выборы само." style "tm_dim"
            $ _rn = tm_route_now()
            hbox:
                spacing 12
                text (u"Сейчас: %d выб. (%s)" % (_rn, u"с начала игры" if tm_ui.route_start == "start" else u"с загрузки сейва")) style "tm_label" yalign 0.5
                use tm_btn2("save", "Сохранить маршрут", Function(tm_route_save), "Запомнить выборы этой партии", sens=(_rn > 0))
            for _ri, _rname, _rprev, _rstart in tm_route_rows():
                hbox:
                    spacing 10
                    vbox:
                        xminimum 560
                        text tm_q(_rname) style "tm_label" size 18
                        text tm_q((u"с начала игры | " if _rstart == "start" else u"с сейва | ") + _rprev) style "tm_dim" size 14
                    textbutton "пройти" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Начни новую игру (или загрузи тот же сейв) и нажми — выборы сделаются сами" action Function(tm_route_play, _ri)
                    textbutton ("точно?" if tm_ui.confirm == "route%d" % _ri else "удалить") style "tm_seg" text_style "tm_seg_text" yalign 0.5 action Function(tm_confirm, "route%d" % _ri, tm_route_del, _ri)

            use tm_sep

            # ---- покрытие ----
            hbox:
                spacing 10
                use tm_icon("trophy", 30)
                text "Покрытие" style "tm_h" yalign 0.5
            text "Сколько игры уже видели на этом компьютере (за все партии)." style "tm_dim"
            for _cl, _cp in ((u"Реплики", _say), (u"Сцены (метки)", _lab), (u"Варианты выбора", _chc)):
                hbox:
                    spacing 14
                    text _cl style "tm_label" yalign 0.5 min_width 220
                    bar value StaticValue(tm_cov_part(_cp), 1.0) style "tm_bar" xsize 260 ysize 14 yalign 0.5
                    text tm_cov_text(_cp) style "tm_dim" yalign 0.5

            use tm_sep

            # ---- сцены ----
            $ _srows, _stotal = tm_scene_rows(tm_ui.scene_filter, tm_ui.scene_all)
            hbox:
                spacing 10
                use tm_icon("story", 30)
                text "Сцены" style "tm_h" yalign 0.5
                textbutton "непросмотренные" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (not tm_ui.scene_all) action SetField(tm_ui, "scene_all", False)
                textbutton "все" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected tm_ui.scene_all action SetField(tm_ui, "scene_all", True)
                use tm_field("scene_filter", 220, 40)
                text ("найдено: %d" % _stotal) style "tm_dim" yalign 0.5
            text "«откуда» — какие переходы ведут в сцену и при каких условиях или выборах (кнопки экранов-карт сюда не попадают)." style "tm_dim" size 15
            if not _srows:
                use tm_empty("party", "Непросмотренных сцен нет — или ничего не подходит под фильтр.")
            for _sn, _sw, _ss in _srows:
                hbox:
                    spacing 8
                    if _ss and tm_ic("ok"):
                        add tm_ic("ok") zoom 0.3 yalign 0.5
                    else:
                        null width 19
                    text tm_q(_tm_short(_sn, 34)) style ("tm_dim" if _ss else "tm_label") size 17 min_width 330 yalign 0.5
                    text tm_q(_sw) style "tm_dim" size 14 min_width 190 yalign 0.5
                    textbutton "перейти" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Прыжок на метку (перед этим — сейв «Перед прыжком»)" action Function(tm_jump, _sn)
                    textbutton "повтор" style "tm_seg" text_style "tm_seg_text" yalign 0.5 tooltip "Повтор сцены без последствий" action Function(tm_replay, _sn)
                    textbutton "откуда" style "tm_seg" text_style "tm_seg_text" yalign 0.5 selected (tm_ui.scene_open == _sn) action Function(tm_scene_toggle, _sn)
                if tm_ui.scene_open == _sn:
                    $ _refs = tm_scene_refs(_sn)
                    frame:
                        background Solid("#ffffff0a")
                        padding (14, 6)
                        xfill True
                        vbox:
                            spacing 2
                            if not _refs:
                                text "Переходов сюда нет: сцена идёт сразу после предыдущей по тексту или вызывается кодом/кнопкой экрана." style "tm_dim" size 15
                            for _rf in _refs:
                                text tm_q(_rf) style "tm_hint_eff" size 15

            use tm_sep

            # ---- заметки о багах ----
            hbox:
                spacing 10
                use tm_icon("bug", 30)
                text "Заметки о багах" style "tm_h" yalign 0.5
            $ _nb = tm_bug_count()
            text ((u"Записано заметок: %d — tm_bugs/tm_bugs.md в папке игры. " % _nb if _nb else u"") + u"Shift+B в любой момент игры: текст, место, реплика, картинки, звук и скриншот.") style "tm_dim"
            hbox:
                spacing 12
                use tm_btn2("bug", "Заметка о баге", Function(tm_bug_request), "Спрятать меню, снять экран игры и записать заметку (Shift+B)")
                use tm_btn2("story", "Отчёт тестера", Function(tm_write_report), "Где я, покрытие, маршрут, история выборов, правки — в файл")

# ---------------------- вкладка: вид и инструменты ----------------------
screen tm_tab_settings():
    python:
        _cur_accent = tm_acc()
        _cur_op = tm_pref("tm_opacity", "f7")
        _cur_sc = float(tm_pref("tm_scale", 1.0))

    viewport:
        scrollbars "vertical"
        style_prefix "tm"
        mousewheel True
        yfill True
        xfill True
        vbox:
            spacing 18

            # ---- Перевод реплик (модуль zzz_testmenu_translate.rpy, если положен) ----
            if renpy.has_screen("tmtr_settings"):
                use tmtr_settings
                use tm_sep

            # ---- Внешний вид ----
            hbox:
                spacing 10
                use tm_icon("palette", 30)
                text "Внешний вид" style "tm_h" yalign 0.5

            hbox:
                spacing 12
                text "Цвет акцента" style "tm_label" yalign 0.5 min_width 220
                hbox:
                    spacing 10
                    for _name, _hex in TM_ACCENTS:
                        frame:
                            padding (3, 3)
                            background (Frame(Solid("#ffffff"), 4, 4) if _cur_accent == _hex else Solid("#00000000"))
                            button:
                                xysize (40, 40)
                                background Frame(Solid(_hex), 6, 6)
                                tooltip _name
                                action Function(tm_set_accent, _hex)

            hbox:
                spacing 12
                text "Прозрачность окна" style "tm_label" yalign 0.5 min_width 220
                hbox:
                    spacing 8
                    for _lbl, _op in TM_OPACITY:
                        textbutton "[_lbl]":
                            style "tm_seg" text_style "tm_seg_text"
                            selected (_cur_op == _op)
                            action Function(tm_set_opacity, _op)

            hbox:
                spacing 12
                text "Размер шрифта" style "tm_label" yalign 0.5 min_width 220
                hbox:
                    spacing 8
                    for _lbl, _sc in TM_SCALES:
                        textbutton "[_lbl]":
                            style "tm_seg" text_style "tm_seg_text"
                            selected (abs(_cur_sc - _sc) < 0.001)
                            tooltip "Окно растёт вместе со шрифтом"
                            action Function(tm_set_scale, _sc)

            hbox:
                spacing 12
                textbutton "Окно в центр" style "tm_btn" text_style "tm_btn_text" action Function(tm_reset_pos)
                textbutton "Сбросить оформление" style "tm_btn" text_style "tm_btn_text" action Function(tm_theme_reset)

            use tm_sep

            # ---- HUD ----
            hbox:
                spacing 10
                use tm_icon("eye", 30)
                text "HUD наблюдения" style "tm_h" yalign 0.5
            text "Значения, отмеченные глазом на вкладке «Переменные», видны поверх игры справа сверху и обновляются вживую." style "tm_dim"
            hbox:
                spacing 12
                textbutton ("HUD: ВКЛ" if tm_ui.hud_on else "HUD: выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected tm_ui.hud_on
                    action ToggleField(tm_ui, "hud_on")
                textbutton ("Очистить HUD (%d)" % len(tm_ui.watch)):
                    style "tm_btn" text_style "tm_btn_text"
                    sensitive bool(tm_ui.watch)
                    action Function(tm_watch_clear)
            hbox:
                spacing 8
                text "Угол" style "tm_dim" yalign 0.5
                for _ck, _cl in TM_HUD_CORNERS:
                    textbutton _cl:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_hud_corner() == _ck)
                        action Function(tm_set_hud_corner, _ck)
            text "При изменении значения рядом на пару секунд вспыхивает разница: +2, −50." style "tm_dim" size 15
            hbox:
                spacing 10
                text "Выражение" style "tm_label" yalign 0.5 min_width 140
                use tm_field("hud_expr", 420, 120)
                textbutton "+ в HUD" style "tm_btn" text_style "tm_btn_text" tooltip "Любое выражение игры: money + bank, len(inventory), day % 7" action Function(tm_hud_add_expr)

            use tm_sep

            # ---- Клавиши ----
            hbox:
                spacing 10
                use tm_icon("key", 30)
                text "Клавиша меню" style "tm_h" yalign 0.5
            text "Shift+T работает всегда. Запасная клавиша — на выбор (F9 во многих играх и у UnRen — быстрая загрузка; если она занята, по умолчанию F10)." style "tm_dim"
            hbox:
                spacing 8
                text "Запасная:" style "tm_dim" yalign 0.5
                for _kl, _kk in TM_ALT_KEYS:
                    textbutton _kl:
                        style "tm_seg" text_style "tm_seg_text"
                        selected (tm_alt_key() == _kk)
                        action Function(tm_set_alt_key, _kk)

            use tm_sep

            # ---- Инструменты тестера ----
            hbox:
                spacing 10
                use tm_icon("console", 30)
                text "Инструменты тестера" style "tm_h" yalign 0.5
            text "Консоль разработчика открывается по Shift+O (переменные, jump, любые команды). Скриншот кладётся в папку игры." style "tm_dim"
            hbox:
                spacing 12
                textbutton ("Консоль (Shift+O): ВКЛ" if config.developer else "Консоль (Shift+O): выкл"):
                    style "tm_seg" text_style "tm_seg_text"
                    selected bool(config.developer)
                    action Function(tm_toggle_dev)
                use tm_btn2("pin", "Где я", Function(tm_where_am_i), "Файл, строка, метка, стек вызовов, экраны")
                use tm_btn2("camera", "Скриншот", Function(tm_screenshot), "Сохранить снимок экрана в папку игры")
            hbox:
                spacing 12
                use tm_btn2("story", "Отчёт тестера", Function(tm_write_report), "Файл в папке игры: где я, история выборов с изменениями, правки из меню, избранное")
                use tm_btn2("close", ("Точно? Нажми ещё раз" if tm_ui.confirm == "purge" else "Убрать следы меню"), Function(tm_confirm, "purge", tm_purge), "Перед удалением меню: быстрые слоты, tm_state.json и настройки меню в persistent", sel=(tm_ui.confirm == "purge"))
