# ============================================================================
#  Test Menu Moon — перевод реплик через AutoTranslator (без OCR)
# ============================================================================
#  Текст берётся прямо из движка (хук config.say_menu_text_filter), переводится
#  запущенным на этом же ПК AutoTranslator (HTTP-мост на 127.0.0.1:47811) и
#  показывается В САМОЙ ИГРЕ — в её окне диалога и в меню выбора.
#
#  Скорость:
#    * Ren'Py заранее «предсказывает» следующие реплики — они уходят на перевод
#      в фоне, и к моменту клика перевод обычно уже готов;
#    * «Перевести всю игру заранее» — все реплики сценария переводятся в фоне
#      пачками и складываются в словарь game/tm_tl/<язык>.json; дальше игра
#      работает мгновенно и даже без запущенного AutoTranslator.
#
#  Теги {i}/{w}/{color=..} и подстановки [name] переводчик не трогает (их
#  защищает AutoTranslator) — сломанная разметка не уронит игру: если перевод
#  подозрительный, показывается оригинал.
#
#  Shift+L — показать/скрыть оригинал реплики сверху.
#  Настройки — в тест-меню (Shift+T) -> «Настройки» -> «Перевод». Работает и без
#  тест-меню: тогда всё по умолчанию (перевод вкл., вся игра переводится в фоне).
# ============================================================================

init -900 python:
    import json as _tmtr_json
    import os as _tmtr_os
    import re as _tmtr_re
    import struct as _tmtr_struct
    import threading as _tmtr_threading
    import time as _tmtr_time
    try:
        import urllib.request as _tmtr_url
    except ImportError:
        import urllib2 as _tmtr_url
    try:
        import builtins as _tmtr_bi
    except ImportError:
        import __builtin__ as _tmtr_bi
    try:
        _TMTR_STR = basestring
    except NameError:
        _TMTR_STR = str
    import renpy.display.predict as _tmtr_predict

    def _tmtr_cfg(name, default=None):
        # на старых Ren'Py неизвестный config.* бросает Exception, а не AttributeError
        try:
            return getattr(config, name)
        except Exception:
            return default

    TMTR_PORT = 47811
    TMTR_LIVE_WAIT = 1.6      # сколько ждём перевод реплики, которой нет в словаре, с
    TMTR_BULK_LINES = 40      # размер пачки фонового перевода (строк / символов)
    TMTR_BULK_CHARS = 2500

    _TMTR_LETTER = _tmtr_re.compile(u"[^\\W\\d_]", _tmtr_re.UNICODE)
    _TMTR_TAG = _tmtr_re.compile(u"\\{[^{}]*\\}")

    class _TmtrState(NoRollback):
        """Всё состояние перевода; NoRollback — не откатывается и не пишется в сейвы."""

        def __init__(self):
            self.tr = _tmtr_bi.dict()          # оригинал -> перевод
            self.lang = None                   # язык словаря в памяти
            self.lock = _tmtr_threading.Lock()
            self.cv = _tmtr_threading.Condition()
            self.queue = _tmtr_bi.list()       # тексты для живого перевода
            self.pending = _tmtr_bi.dict()     # текст -> Event (перевод в пути)
            self.online = None                 # None — ещё не знаем
            self.down_until = 0.0              # мост недоступен — не долбимся до этого времени
            self.info = _tmtr_bi.dict()
            self.worker = None
            self.bulk = _tmtr_bi.dict(state="idle", done=0, total=0, msg=u"")
            self.bulk_thread = None
            self.bulk_stop = False
            self.unsaved = 0
            self.last_src = u""
            self.rev = _tmtr_bi.dict()         # показанный перевод -> оригинал (для Shift+L)
            self.cyr_ok = None                 # шрифт игры умеет кириллицу?
            self.connecting = False
            self.last_connect = 0.0
            self.user_stopped = False          # «Стоп» в меню — сам не перезапускаем
            self.fix_seen = 0                  # последняя забранная правка из окна AutoTranslator
            self.fix_busy = False
            self.fixes = 0                     # сколько правок пришло за сессию

    tmtr = _TmtrState()

    for _k, _v in (("tmtr_on", True), ("tmtr_orig", False), ("tmtr_font", "auto"),
                   ("tmtr_bulk", True)):
        if getattr(persistent, _k) is None:
            setattr(persistent, _k, _v)

    # ---------------- словарь на диске ----------------
    def _tmtr_dirs():
        dirs = []
        for base in (_tmtr_cfg("gamedir", None), _tmtr_cfg("savedir", None)):
            if base:
                dirs.append(_tmtr_os.path.join(base, "tm_tl"))
        return dirs

    def _tmtr_load(lang):
        d = _tmtr_bi.dict()
        for folder in reversed(_tmtr_dirs()):     # gamedir важнее savedir
            path = _tmtr_os.path.join(folder, "%s.json" % lang)
            try:
                with open(path, "rb") as f:
                    data = _tmtr_json.loads(f.read().decode("utf-8"))
                if isinstance(data, _tmtr_bi.dict):
                    d.update(data)
            except Exception:
                pass
        with tmtr.lock:
            tmtr.tr = d
            tmtr.lang = lang
            tmtr.unsaved = 0

    def tmtr_save():
        if not tmtr.lang:
            return
        with tmtr.lock:
            data = _tmtr_json.dumps(tmtr.tr, ensure_ascii=True, sort_keys=True, indent=0)
            tmtr.unsaved = 0
        for folder in _tmtr_dirs():               # в папку игры; нет прав — в сейвы
            try:
                if not _tmtr_os.path.isdir(folder):
                    _tmtr_os.makedirs(folder)
                path = _tmtr_os.path.join(folder, "%s.json" % tmtr.lang)
                tmp = path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data.encode("utf-8"))
                if _tmtr_os.path.exists(path):
                    _tmtr_os.remove(path)
                _tmtr_os.rename(tmp, path)
                return
            except Exception:
                continue

    # ---------------- связь с AutoTranslator ----------------
    _tmtr_opener = _tmtr_url.build_opener(_tmtr_url.ProxyHandler({}))  # localhost — мимо прокси

    def _tmtr_http(path, payload=None, timeout=4.0):
        data = None
        headers = {}
        if payload is not None:
            data = _tmtr_json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = _tmtr_url.Request("http://127.0.0.1:%d%s" % (TMTR_PORT, path), data, headers)
        r = _tmtr_opener.open(req, timeout=timeout)
        try:
            return _tmtr_json.loads(r.read().decode("utf-8"))
        finally:
            r.close()

    def _tmtr_game_name():
        for v in (_tmtr_cfg("name", None), _tmtr_cfg("window_title", None)):
            if v:
                return v
        return _tmtr_os.path.basename(_tmtr_cfg("basedir", "") or "") or u"game"

    def _tmtr_mark_down(sec):
        tmtr.online = False
        tmtr.down_until = _tmtr_time.time() + sec

    def tmtr_connect():
        """Узнать у AutoTranslator язык перевода (в фоне); подгрузить словарь."""
        if tmtr.connecting or _tmtr_time.time() - tmtr.last_connect < 5.0:
            return
        tmtr.connecting = True
        tmtr.last_connect = _tmtr_time.time()

        def run():
            try:
                info = _tmtr_http("/info", timeout=2.0)
                tmtr.info = info
                tmtr.online = True
                tmtr.down_until = 0.0
                lang = info.get("target") or "ru"
                if lang != tmtr.lang:
                    if tmtr.lang and tmtr.unsaved:
                        tmtr_save()
                    _tmtr_load(lang)
                persistent.tmtr_lang = lang
                _tmtr_hello()
                _tmtr_check_fixes(info.get("fix_rev"))
                if persistent.tmtr_bulk and persistent.tmtr_on and not tmtr.user_stopped:
                    tmtr_bulk_start()
            except Exception:
                _tmtr_mark_down(10.0)
            finally:
                tmtr.connecting = False

        t = _tmtr_threading.Thread(target=run)
        t.daemon = True
        t.start()

    def _tmtr_names():
        # имена персонажей игры — AutoTranslator их не переводит (Lucky не станет «Счастливчиком»)
        out = []
        try:
            adv = renpy.character.ADVCharacter
            for v in _tmtr_bi.list(vars(renpy.store).values()):
                nm = getattr(v, "name", None) if isinstance(v, adv) else None
                if (isinstance(nm, _TMTR_STR) and nm.strip() and len(nm) <= 40
                        and "[" not in nm and "{" not in nm and nm.strip() not in out):
                    out.append(nm.strip())
        except Exception:
            pass
        return out[:200]

    def _tmtr_hello():
        # AutoTranslator v2: «игра подключилась» — имена, размер словаря, прогресс (старый — 404)
        try:
            _tmtr_http("/hello", {"game": _tmtr_game_name(), "names": _tmtr_names(),
                                  "dict": len(tmtr.tr), "total": tmtr.bulk.get("total", 0)},
                       timeout=2.0)
        except Exception:
            pass

    # ---------------- правки перевода из окна AutoTranslator ----------------
    def _tmtr_check_fixes(rev):
        # в каждом ответе моста — номер последней правки; новый номер -> забрать правки
        try:
            rev = int(rev or 0)
        except Exception:
            return
        if rev <= tmtr.fix_seen or tmtr.fix_busy or not tmtr.lang:
            return
        tmtr.fix_busy = True
        try:
            res = _tmtr_http("/fixes?game=%s&since=%d&lang=%s" % (
                _tmtr_quote(_tmtr_game_name()), tmtr.fix_seen, _tmtr_quote(tmtr.lang)), timeout=3.0)
            items = res.get("items") or []
            with tmtr.lock:
                for pair in items:
                    if len(pair) == 2 and pair[0] and pair[1]:
                        tmtr.tr[pair[0]] = pair[1]
                        tmtr.unsaved += 1
            tmtr.fixes += len(items)
            tmtr.fix_seen = max(tmtr.fix_seen, int(res.get("rev") or rev))
            if items:
                tmtr_save()
        except Exception:
            pass
        finally:
            tmtr.fix_busy = False

    try:
        from urllib.parse import quote as _tmtr_quote_raw
    except ImportError:
        from urllib import quote as _tmtr_quote_raw

    def _tmtr_quote(s):
        if not isinstance(s, bytes):
            s = s.encode("utf-8")
        return _tmtr_quote_raw(s, safe="")

    # ---------------- живой перевод (текущая и предсказанные реплики) ----------------
    def _tmtr_live_loop():
        while True:
            with tmtr.cv:
                while not tmtr.queue:
                    tmtr.cv.wait()
                batch = tmtr.queue[:24]
                del tmtr.queue[:24]
            try:
                res = _tmtr_http("/translate", {"texts": batch, "game": _tmtr_game_name()},
                                 timeout=8.0)
                out = res.get("tr") or []
                tmtr.online = True
                _tmtr_check_fixes(res.get("fix_rev"))
                if res.get("target") and res.get("target") != tmtr.lang:
                    out = []          # язык в AutoTranslator сменили — словарь не мешаем
                    tmtr_connect()
                with tmtr.lock:
                    for src, dst in zip(batch, out):
                        if dst:
                            tmtr.tr[src] = dst
                            tmtr.unsaved += 1
            except Exception:
                _tmtr_mark_down(8.0)
            for src in batch:
                ev = tmtr.pending.pop(src, None)
                if ev is not None:
                    ev.set()
            if tmtr.unsaved >= 25:
                tmtr_save()

    def _tmtr_request(text, front=False):
        """Поставить текст в очередь перевода. Возвращает Event или None."""
        if text in tmtr.tr:
            return None
        ev = tmtr.pending.get(text)
        if ev is not None:
            if front:
                with tmtr.cv:
                    if text in tmtr.queue:
                        tmtr.queue.remove(text)
                        tmtr.queue.insert(0, text)
            return ev
        if _tmtr_time.time() < tmtr.down_until:
            if tmtr.online is False and not tmtr.connecting:
                tmtr_connect()        # вдруг AutoTranslator уже запустили
            return None
        if tmtr.worker is None:
            tmtr.worker = _tmtr_threading.Thread(target=_tmtr_live_loop)
            tmtr.worker.daemon = True
            tmtr.worker.start()
        ev = _tmtr_threading.Event()
        tmtr.pending[text] = ev
        with tmtr.cv:
            if front:
                tmtr.queue.insert(0, text)
            else:
                tmtr.queue.append(text)
            tmtr.cv.notify()
        return ev

    # ---------------- шрифт: умеет ли он кириллицу ----------------
    def _tmtr_cmap_has(data, cp):
        u16 = lambda o: _tmtr_struct.unpack(">H", data[o:o + 2])[0]
        u32 = lambda o: _tmtr_struct.unpack(">I", data[o:o + 4])[0]
        base = u32(12) if data[:4] == b"ttcf" else 0
        cmap = None
        for i in range(u16(base + 4)):
            rec = base + 12 + 16 * i
            if data[rec:rec + 4] == b"cmap":
                cmap = u32(rec + 8)
                break
        if cmap is None:
            return False
        for i in range(u16(cmap + 2)):
            off = cmap + u32(cmap + 4 + 8 * i + 4)
            fmt = u16(off)
            if fmt == 4:
                segx2 = u16(off + 6)
                ends = off + 14
                starts = ends + segx2 + 2
                for s in range(segx2 // 2):
                    if u16(ends + 2 * s) >= cp:
                        if u16(starts + 2 * s) <= cp:
                            return True
                        break
            elif fmt == 12:
                for g in range(u32(off + 12)):
                    o = off + 16 + 12 * g
                    if u32(o) <= cp <= u32(o + 4):
                        return True
        return False

    def _tmtr_font_ok(fn):
        if not isinstance(fn, _TMTR_STR):
            return True               # FontGroup и т.п. — доверяем игре
        try:
            f = renpy.file(fn)
            try:
                data = f.read()
            finally:
                f.close()
            return _tmtr_cmap_has(data, 0x0414)   # «Д»
        except Exception:
            return False

    def _tmtr_fonts_ok():
        fonts = []
        for name in ("say_dialogue", "default", "choice_button_text", "menu_choice"):
            try:
                fonts.append(getattr(getattr(style, name), "font"))
            except Exception:
                pass
        try:
            fonts.append(store.gui.text_font)
        except Exception:
            pass
        seen = set()
        for fn in fonts:
            if fn is None or fn in seen:
                continue
            seen.add(fn)
            if not _tmtr_font_ok(fn):
                return False
        return True

    def _tmtr_wrap(tr):
        mode = persistent.tmtr_font or "auto"
        if mode == "game" or not any(ord(ch) > 0x24F for ch in tr):
            return tr
        if mode == "auto":
            if tmtr.cyr_ok is None:
                tmtr.cyr_ok = _tmtr_fonts_ok()
            if tmtr.cyr_ok:
                return tr
        return u"{font=DejaVuSans.ttf}" + tr + u"{/font}"

    # ---------------- сам фильтр реплик ----------------
    def _tmtr_filter(what):
        try:
            if not persistent.tmtr_on or not what or not isinstance(what, _TMTR_STR):
                return what
            if tmtr.lang is None:
                _tmtr_load(persistent.tmtr_lang or "ru")
                tmtr_connect()
            predicting = getattr(_tmtr_predict, "predicting", False)
            tr = tmtr.tr.get(what)
            if tr is None:
                if not _TMTR_LETTER.search(_TMTR_TAG.sub(u"", what)):
                    return what
                if predicting:
                    _tmtr_request(what)          # заранее, без ожидания
                    return what
                tmtr.last_src = what
                ev = _tmtr_request(what, front=True)
                if ev is not None:
                    ev.wait(TMTR_LIVE_WAIT)
                tr = tmtr.tr.get(what)
                if tr is None:
                    return what
            elif not predicting:
                tmtr.last_src = what
            shown = _tmtr_wrap(tr)
            if not predicting:
                if len(tmtr.rev) > 400:
                    tmtr.rev.clear()
                tmtr.rev[shown] = what
            return shown
        except Exception:
            return what

    def _tmtr_chained(what):
        what = _tmtr_filter(what)
        prev = getattr(_tmtr_chained, "prev", None)
        return prev(what) if prev is not None else what

    _tmtr_chained._tmtr = True

    # ---------------- перевод всей игры заранее ----------------
    def _tmtr_collect():
        try:
            nodes = renpy.game.script.all_stmts or _tmtr_bi.list(renpy.game.script.namemap.values())
        except Exception:
            return []
        out = []
        seen = set()
        for n in nodes:
            try:
                if isinstance(n, renpy.ast.Say):
                    texts = [n.what]
                elif isinstance(n, renpy.ast.Menu):
                    texts = [it[0] for it in n.items]
                else:
                    continue
                fn = "/" + (n.filename or "").replace("\\", "/")
                if "/renpy/common" in fn or "zzz_testmenu" in fn or "/tl/" in fn:
                    continue
                for t in texts:
                    if (isinstance(t, _TMTR_STR) and t not in seen
                            and _TMTR_LETTER.search(_TMTR_TAG.sub(u"", t))):
                        seen.add(t)
                        out.append(t)
            except Exception:
                continue
        return out

    def _tmtr_bulk_run():
        b = tmtr.bulk
        try:
            texts = _tmtr_collect()
            todo = [t for t in texts if t not in tmtr.tr]
            b.update(state="run", total=len(texts), done=len(texts) - len(todo), msg=u"")
            chunk = []
            size = 0
            flushes = 0
            i = 0
            while i <= len(todo):
                t = todo[i] if i < len(todo) else None
                if t is not None and (not chunk or (len(chunk) < TMTR_BULK_LINES
                                                    and size + len(t) < TMTR_BULK_CHARS)):
                    chunk.append(t)
                    size += len(t)
                    i += 1
                    continue
                if not chunk:
                    break
                if tmtr.bulk_stop or not persistent.tmtr_on:
                    b["state"] = "stopped"
                    break
                ok = False
                for attempt in range(4):
                    try:
                        res = _tmtr_http("/translate", {"texts": chunk, "bulk": True,
                                                        "game": _tmtr_game_name(),
                                                        "done": b["done"], "total": b["total"]},
                                         timeout=60.0)
                        _tmtr_check_fixes(res.get("fix_rev"))
                        if res.get("target") and res.get("target") != tmtr.lang:
                            b.update(state="error", msg=u"в AutoTranslator сменился язык")
                            tmtr_connect()
                            return
                        with tmtr.lock:
                            for src, dst in zip(chunk, res.get("tr") or []):
                                if dst:
                                    tmtr.tr[src] = dst
                        ok = True
                        break
                    except Exception as e:
                        b["msg"] = u"повтор: %s" % e
                        _tmtr_time.sleep(3.0 * (attempt + 1))
                if not ok:
                    b.update(state="error", msg=u"AutoTranslator не отвечает")
                    _tmtr_mark_down(15.0)
                    break
                b["done"] += len(chunk)
                b["msg"] = u""
                chunk = []
                size = 0
                flushes += 1
                if flushes % 5 == 0:
                    tmtr_save()
            if b["state"] == "run":
                b["state"] = "done"
        except Exception as e:
            b.update(state="error", msg=u"%s" % e)
        finally:
            tmtr_save()
            tmtr.bulk_thread = None

    def tmtr_bulk_start():
        if tmtr.bulk_thread is not None:
            return
        tmtr.bulk_stop = False
        tmtr.user_stopped = False
        tmtr.bulk.update(state="run", msg=u"")
        tmtr.bulk_thread = _tmtr_threading.Thread(target=_tmtr_bulk_run)
        tmtr.bulk_thread.daemon = True
        tmtr.bulk_thread.start()

    def tmtr_bulk_stop():
        tmtr.bulk_stop = True
        tmtr.user_stopped = True

    def tmtr_clear():
        with tmtr.lock:
            tmtr.tr = _tmtr_bi.dict()
        tmtr.bulk.update(state="idle", done=0, total=0, msg=u"")
        tmtr_save()
        renpy.notify(u"Словарь перевода очищен")

    def tmtr_set_font(mode):
        persistent.tmtr_font = mode
        tmtr.cyr_ok = None
        renpy.restart_interaction()

    def tmtr_toggle_orig():
        persistent.tmtr_orig = not persistent.tmtr_orig
        renpy.restart_interaction()

    def tmtr_plain(s):
        """Оригинал для показа: без тегов разметки ({{ остаётся буквальной скобкой)."""
        s = (s or u"").replace(u"{{", u"\0")
        s = _TMTR_TAG.sub(u"", s)
        return s.replace(u"\0", u"{{").replace(u"[", u"[[")

    def tmtr_current_src():
        """Оригинал реплики, которая сейчас на экране (варианты выбора не в счёт)."""
        shown = getattr(store, "_last_say_what", None)
        if not shown:
            return u""
        return tmtr.rev.get(shown) or (shown if shown == tmtr.last_src else u"")

    def tmtr_status():
        if tmtr.online:
            i = tmtr.info
            return u"AutoTranslator подключён: %s → %s, %s%s" % (
                i.get("source", "?"), i.get("target", "?"),
                u"онлайн" if i.get("engine") == "online" else u"офлайн",
                (u"; правок из окна: %d" % tmtr.fixes) if tmtr.fixes else u"")
        if tmtr.online is False:
            return u"AutoTranslator не запущен — перевод только из словаря"
        return u"Подключаюсь к AutoTranslator…"

    _tmtr_keymap = renpy.Keymap(tmtr_orig_key=tmtr_toggle_orig)

    def tmtr_register():
        try:
            cur = config.say_menu_text_filter
            if not getattr(cur, "_tmtr", False):
                _tmtr_chained.prev = cur
                config.say_menu_text_filter = _tmtr_chained
            config.keymap.setdefault("tmtr_orig_key", [])
            if "shift_K_l" not in config.keymap["tmtr_orig_key"]:
                config.keymap["tmtr_orig_key"].append("shift_K_l")
            if _tmtr_keymap not in config.underlay:
                config.underlay.append(_tmtr_keymap)
            if "tmtr_overlay" not in config.overlay_screens:
                config.overlay_screens.append("tmtr_overlay")
        except Exception:
            pass

    def _tmtr_on_start():
        tmtr_register()
        if tmtr.online is None:
            tmtr_connect()

    for _cb in ("start_callbacks", "after_load_callbacks"):
        _lst = _tmtr_cfg(_cb, None)
        if isinstance(_lst, _tmtr_bi.list) and _tmtr_on_start not in _lst:
            _lst.append(_tmtr_on_start)

    def _tmtr_atexit():
        if tmtr.unsaved:
            tmtr_save()

    import atexit as _tmtr_atexit_mod
    _tmtr_atexit_mod.register(_tmtr_atexit)
    _lst = _tmtr_cfg("quit_callbacks", None)
    if isinstance(_lst, _tmtr_bi.list) and _tmtr_atexit not in _lst:
        _lst.append(_tmtr_atexit)

# Регистрация после init всех файлов игры (её init мог переприсвоить фильтр/оверлеи).
init 999 python:
    tmtr_register()
    _tmtr_load(persistent.tmtr_lang or "ru")
    tmtr_connect()

# ---------------- поверх игры: оригинал (Shift+L) и прогресс перевода игры ----------------
screen tmtr_overlay():
    zorder 190
    $ _tmtr_src = tmtr_current_src() if (persistent.tmtr_on and persistent.tmtr_orig) else u""
    if _tmtr_src and not main_menu:
        frame:
            xalign 0.5
            ypos 12
            xmaximum 0.8
            padding (16, 8)
            background Solid("#000000b8")
            text tmtr_plain(_tmtr_src):
                size 22
                color "#e8e8ee"
                font "DejaVuSans.ttf"
    if persistent.tmtr_on and tmtr.bulk.get("state") == "run" and tmtr.bulk.get("total"):
        text (u"Перевод игры: %d%%" % (100 * tmtr.bulk["done"] // max(1, tmtr.bulk["total"]))):
            xalign 0.0
            ypos 6
            xoffset 10
            size 16
            color "#ffffffaa"
            outlines [(1, "#00000099", 0, 0)]
            font "DejaVuSans.ttf"

# ---------------- раздел в тест-меню: «Настройки» -> «Перевод» ----------------
screen tmtr_settings():
    python:
        _tb = tmtr.bulk
        _tb_state = _tb.get("state")
        _tb_total = _tb.get("total", 0)
    hbox:
        spacing 10
        use tm_icon("hint", 30)
        text "Перевод реплик" style "tm_h" yalign 0.5
    text "Реплики и варианты выбора переводит AutoTranslator (должен быть запущен) — перевод показывается прямо в окне диалога. Shift+L — оригинал сверху. Неудачный перевод можно исправить в окне AutoTranslator (карандаш) — правка придёт сюда; имена персонажей не переводятся." style "tm_dim"
    text tmtr_status() style "tm_dim"
    hbox:
        spacing 12
        textbutton ("Перевод: ВКЛ" if persistent.tmtr_on else "Перевод: выкл"):
            style "tm_seg" text_style "tm_seg_text"
            selected bool(persistent.tmtr_on)
            tooltip "Выключенный — со следующей реплики снова оригинал"
            action ToggleField(persistent, "tmtr_on")
        textbutton ("Оригинал сверху: ВКЛ" if persistent.tmtr_orig else "Оригинал сверху: выкл"):
            style "tm_seg" text_style "tm_seg_text"
            selected bool(persistent.tmtr_orig)
            tooltip "То же, что Shift+L"
            action Function(tmtr_toggle_orig)
    hbox:
        spacing 12
        text "Шрифт перевода" style "tm_label" yalign 0.5 min_width 220
        hbox:
            spacing 8
            for _lbl, _m, _tip in (("Авто", "auto", "Шрифт игры, а если в нём нет кириллицы — DejaVu"),
                                   ("DejaVu", "dejavu", "Всегда DejaVu Sans (точно с кириллицей)"),
                                   ("Шрифт игры", "game", "Никогда не менять шрифт")):
                textbutton _lbl:
                    style "tm_seg" text_style "tm_seg_text"
                    selected (persistent.tmtr_font == _m)
                    tooltip _tip
                    action Function(tmtr_set_font, _m)
    hbox:
        spacing 12
        if _tb_state == "run":
            textbutton ("Перевожу игру: %d / %d" % (_tb.get("done", 0), _tb_total)):
                style "tm_btn" text_style "tm_btn_text"
                tooltip "Нажми, чтобы остановить"
                action Function(tmtr_bulk_stop)
        else:
            textbutton "Перевести всю игру заранее":
                style "tm_btn" text_style "tm_btn_text"
                tooltip "Все реплики сценария — в словарь game/tm_tl; потом всё мгновенно"
                action Function(tmtr_bulk_start)
        textbutton ("Сам при запуске: да" if persistent.tmtr_bulk else "Сам при запуске: нет"):
            style "tm_seg" text_style "tm_seg_text"
            selected bool(persistent.tmtr_bulk)
            tooltip "Доводить перевод всей игры в фоне при каждом запуске"
            action ToggleField(persistent, "tmtr_bulk")
        textbutton "Очистить словарь":
            style "tm_btn" text_style "tm_btn_text"
            tooltip "Например, после смены движка перевода"
            action Function(tmtr_clear)
    text ("В словаре: %d строк%s" % (len(tmtr.tr), ("  |  " + _tb.get("msg")) if _tb.get("msg") else "")) style "tm_dim"
