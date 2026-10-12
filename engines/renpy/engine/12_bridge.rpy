
# ==================== пульт в студии: игра <-> студия по HTTP (tmkit/bridge.py) ====================
# Включается в «Настройках» («Пульт в студии»), запоминается в tm_state.json. Сеть — в своём
# потоке (раз в 0.7 с, без студии — раз в 3 с); store трогает только главный поток: состояние
# собирается и команды применяются в периодическом колбэке меню (_tm_periodic).
init -3 python:
    import threading as _tmb_threading
    import json as _tmb_json
    try:
        import urllib.request as _tmb_url
    except ImportError:
        import urllib2 as _tmb_url

    TMB_PORT = 47820

    class _TmBridge(object):
        def __init__(self):
            self.on = False
            self.ok = False
            self.out = None           # последнее состояние для студии (JSON-байты)
            self.cmds = []            # команды студии, ждущие главного потока
            self.lock = _tmb_threading.Lock()
            self.thread = None
            self.err = None           # последняя ошибка связи (для отладки)
            self.next_state = 0.0
            import random
            self.id = "renpy-%08x" % random.getrandbits(32)

    _tm_bridge = _TmBridge()
    _tmb_opener = _tmb_url.build_opener(_tmb_url.ProxyHandler({}))  # localhost — мимо прокси

    def _tmb_loop():
        import time
        b = _tm_bridge
        while b.on:
            data = b.out
            wait = 3.0
            if data is not None:
                try:
                    req = _tmb_url.Request("http://127.0.0.1:%d/sync" % TMB_PORT, data,
                                           {"Content-Type": "application/json"})
                    r = _tmb_opener.open(req, timeout=2.0)
                    try:
                        ans = _tmb_json.loads(r.read().decode("utf-8"))
                    finally:
                        r.close()
                    cmds = ans.get("cmds") or []
                    if cmds:
                        with b.lock:
                            b.cmds.extend(cmds)
                    b.ok = True
                    wait = 0.7
                except Exception as e:
                    b.ok = False
                    b.err = repr(e)
            time.sleep(wait)
        b.thread = None

    def tm_bridge_set(on, redraw=True):
        b = _tm_bridge
        b.on = bool(on)
        tm_ui.bridge = b.on
        if b.on and b.thread is None:
            b.thread = _tmb_threading.Thread(target=_tmb_loop)
            b.thread.daemon = True
            b.thread.start()
        if redraw:
            renpy.restart_interaction()

    def _tmb_state():
        rows = []
        for r in tm_all_stats():
            if not r[1]:
                continue
            had, v = tm_probe(r[1])
            if not had or not (isinstance(v, (_TM_NUM, _TM_STR, bool))):
                continue
            t = "bool" if isinstance(v, bool) else ("num" if isinstance(v, _TM_NUM) else "str")
            rows.append({"k": r[1], "sec": "", "name": tm_str(tm_nice(r[0], r[1])[0]), "type": t,
                         "v": v if t != "str" else tm_str(v), "fz": r[1] in tm_ui.frozen})
            if len(rows) >= 400:
                break
        title = getattr(store, "tm_title", None) or getattr(config, "name", "") or u"Ren'Py"
        return {"id": _tm_bridge.id, "title": tm_str(title), "engine": tm_str(renpy.version()),
                "caps": ["set", "freeze"], "rows": rows}

    def _tmb_apply(c):
        op, k = c.get("op"), c.get("k")
        if not k:
            return
        had, cur = tm_probe(k)
        if not had:
            return
        if op == "set":
            v = c.get("v")
            try:
                if isinstance(cur, bool):
                    v = v in (True, 1, "true", "1")
                elif isinstance(cur, _TM_NUM):
                    f = float(v)
                    v = int(f) if not isinstance(cur, float) and f == int(f) else f
                else:
                    v = tm_str(v)
            except Exception:
                return
            tm_set(k, v)
            _tm_log_src(k, u"пульт")
        elif op == "freeze":
            tm_ui.frozen[k] = cur
        elif op == "unfreeze":
            tm_ui.frozen.pop(k, None)
            tm_ui.freeze_mode.pop(k, None)

    def _tm_bridge_periodic():
        b = _tm_bridge
        if not b.on or store.main_menu:
            return
        import time
        now = time.time()
        if now >= b.next_state:
            b.next_state = now + 0.7
            try:
                b.out = _tmb_json.dumps(_tmb_state()).encode("utf-8")
            except Exception:
                pass
        if b.cmds:
            with b.lock:
                cmds, b.cmds = b.cmds, []
            for c in cmds:
                try:
                    _tmb_apply(c)
                except Exception:
                    pass
            renpy.restart_interaction()
