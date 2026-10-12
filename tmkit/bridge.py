"""Мост «игра <-> студия» (пульт): значения, заморозки, темп и шаг кадра со второго монитора.

Студия держит HTTP-сервер на 127.0.0.1:47820. Меню в игре (веб-ядро, Ren'Py, Godot), если в
нём включён «Пульт в студии», раз в ~0.7 с шлёт POST /sync со своим состоянием и забирает
команды. Только localhost; HTTP, а не WebSocket — клиенту хватает того, что есть в любом
движке (fetch, urllib, HTTPRequest).

Состояние игры (JSON):
    {"id": "…", "title": "…", "engine": "web|renpy|godot|…", "caps": ["set", "freeze", "speed", "step"],
     "speed": 1, "rows": [{"k": ключ, "sec": раздел, "name": имя, "type": "num|bool|str", "v": значение,
                           "fz": заморожено}]}
Ответ: {"cmds": [{"op": "set|freeze|unfreeze|speed|step", "k": ключ, "v": значение}]}
Команда доставляется один раз (localhost: потерь нет), игра применяет их по порядку.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 47820
STALE = 5.0  # с какого молчания игра считается отключённой (с)


class Bridge:
    def __init__(self, port=PORT):
        self.port = port
        self.clients = {}  # id -> {"state": dict, "seen": время, "cmds": [..]}
        self.lock = threading.Lock()
        self.server = None
        self.error = None

    # ---------------------------------------------------------- сервер
    def start(self):
        """Поднять сервер в фоне. -> True; False — порт занят (self.error — почему)."""
        if self.server is not None:
            return True
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_a):  # без вывода в консоль на каждый запрос
                pass

            def _send(self, code, obj):
                body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):  # preflight браузера
                self._send(204, {})

            def do_GET(self):
                if self.path.startswith("/ping"):
                    self._send(200, {"ok": True, "app": "TestMenuMoon"})
                else:
                    self._send(404, {"error": "нет такого пути"})

            def do_POST(self):
                if not self.path.startswith("/sync"):
                    self._send(404, {"error": "нет такого пути"})
                    return
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                    state = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
                except (ValueError, UnicodeDecodeError):
                    self._send(400, {"error": "не JSON"})
                    return
                self._send(200, {"cmds": bridge._sync(state)})

        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        except OSError as e:
            self.error = str(e)
            return False
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return True

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    # ---------------------------------------------------------- состояние
    def _sync(self, state):
        cid = str(state.get("id") or "?")
        with self.lock:
            c = self.clients.setdefault(cid, {"cmds": []})
            c["state"] = state
            c["seen"] = time.time()
            cmds, c["cmds"] = c["cmds"], []
        return cmds

    def games(self):
        """[(id, состояние, на связи)] — новые сверху; отключённые больше минуты — убраны."""
        now = time.time()
        with self.lock:
            for cid in [k for k, c in self.clients.items() if now - c.get("seen", 0) > 60]:
                del self.clients[cid]
            out = [(cid, c.get("state", {}), now - c.get("seen", 0) < STALE) for cid, c in self.clients.items()]
        out.sort(key=lambda x: -self.clients.get(x[0], {}).get("seen", 0))
        return out

    def send(self, cid, op, k=None, v=None):
        cmd = {"op": op}
        if k is not None:
            cmd["k"] = k
        if v is not None:
            cmd["v"] = v
        with self.lock:
            if cid in self.clients:
                self.clients[cid]["cmds"].append(cmd)
                return True
        return False
