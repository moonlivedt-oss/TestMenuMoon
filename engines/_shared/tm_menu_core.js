/* ============================================================================
 *  UNIVERSAL TEST MENU — общий UI-ядро (движко-независимое).
 *  Читает window.TM_ADAPTER (задаётся адаптером конкретного движка) и рисует
 *  оверлей: вкладки Значения / Сканер / Экшены, перетаскивание, анимации, тосты.
 *
 *  Контракт адаптера TM_ADAPTER:
 *    accent   : "#rrggbb"
 *    title    : "Название движка"
 *    ready()  : bool — доступны ли данные игры
 *    stats()  : [ { title, rows:[ { name, type:'num'|'bool'|'str', get(), set(v) } ] } ]
 *    nums()   : { имя: число }              — числа для сканера
 *    actions(): [ { label, desc?, run() } ] — кнопки-экшены
 *    footMissing : строка для футера, когда ready()===false
 *    onClose()? : вызывается при закрытии меню (сбросить «залипший» ввод игры)
 *  Необязательное — вкладка «Игра» (появляется, если есть хоть что-то из этого):
 *    speed    : true — скорость игры через подмену времени (performance.now, Date.now,
 *               requestAnimationFrame); function(k) — своя реализация движка (k = 0 — пауза)
 *    cheats() : [ { label, desc?, get(), set(bool) } ] — режимы-переключатели
 *    places   : { here(): {name, ...} | null, go(p) } — точки телепорта (хранятся в localStorage)
 *    jumps    : { title, load(cb) } — cb([{ name, hint?, go() }]): список мест для перехода (карты)
 *  У строки «Значений» может быть where(cb) — cb([строки]): где игра меняет и проверяет значение.
 * ==========================================================================*/
(function () {
  if (window.__TM_MENU__) return;
  var A = window.TM_ADAPTER;
  if (!A) { console.warn("[TM] нет TM_ADAPTER — ядро меню не запущено"); return; }
  window.__TM_MENU__ = true;

  var ACCENT = A.accent || "#38e0c8";
  var step = 1, tab = "vals";
  var overlay = null, winEl = null, bodyEl = null;
  var scanSnap = {}, scanCands = null, scanMsg = "Нажми «Снимок», измени что-то в игре, затем сужай.";
  var filter = "", winPos = null;
  // «живые» значения: пока меню открыто, показанные числа догоняют игру (таймеры,
  // события) без переоткрытия; frozen — заморозка: имя строки -> удерживаемое значение
  var live = [], liveTimer = null, frozen = {};

  // --- запоминание шага/вкладки/позиции окна между открытиями ---
  var LSKEY = "tm_menu_" + (A.title || "x");
  function saveState() { try { localStorage.setItem(LSKEY, JSON.stringify({ step: step, tab: tab, pos: winPos })); } catch (e) {} }
  function loadState() { try { var s = JSON.parse(localStorage.getItem(LSKEY) || "{}"); if ([1, 10, 100].indexOf(s.step) >= 0) step = s.step; if (["vals", "game", "scan", "act"].indexOf(s.tab) >= 0) tab = s.tab; if (s.pos) winPos = s.pos; } catch (e) {} }
  function hasGameTab() { return true; }   // там же профиль игры — нужен любому движку
  var jumpList = null, jumpFilter = "";

  // --- скорость игры: виртуальное время. Движки HTML5 считают кадр по performance.now
  // или по метке requestAnimationFrame — подменяем обе (и Date.now), темп = k.
  var speed = 1, TIME = null;
  function timeSpeed(k) {
    if (!TIME) {
      var pn = performance.now.bind(performance), dn = Date.now, raf = window.requestAnimationFrame;
      TIME = { k: 1, pn: pn, rBase: pn(), vBase: pn() };
      var virt = function () { return TIME.vBase + (pn() - TIME.rBase) * TIME.k; };
      TIME.virt = virt;
      try { performance.now = virt; } catch (e) {}
      Date.now = function () { return dn() + Math.round(virt() - pn()); };
      if (raf) window.requestAnimationFrame = function (cb) { return raf.call(window, function () { cb(virt()); }); };
    }
    // смена темпа без скачка: виртуальное время продолжается с того же места
    TIME.vBase = TIME.virt(); TIME.rBase = TIME.pn(); TIME.k = k;
  }
  function setSpeed(k) {
    try { if (typeof A.speed === "function") A.speed(k); else timeSpeed(k); speed = k; }
    catch (e) { console.error("[TM] скорость", e); toast("Скорость не меняется", true); return; }
    var b = document.getElementById("tm-speed");
    if (k === 1) { if (b) b.remove(); return; }
    if (!b) { b = el("div"); b.id = "tm-speed"; document.body.appendChild(b); }
    b.textContent = k === 0 ? "ПАУЗА" : "×" + k;
  }
  // точки телепорта: localStorage, свои у каждого движка/игры
  var PKEY = LSKEY + "_places_" + (location.pathname || "");
  function loadPlaces() { try { return JSON.parse(localStorage.getItem(PKEY) || "[]"); } catch (e) { return []; } }
  function savePlaces(a) { try { localStorage.setItem(PKEY, JSON.stringify(a)); } catch (e) {} }

  // --- профиль игры: темп, включённые режимы и заморозки, которые ставятся сами при запуске
  var FKEY = LSKEY + "_profile_" + (location.pathname || "");
  function loadProfile() { try { return JSON.parse(localStorage.getItem(FKEY) || "null"); } catch (e) { return null; } }
  function profileNow() {
    var p = { speed: speed, cheats: {}, frozen: {} };
    (A.cheats ? A.cheats() || [] : []).forEach(function (c) { try { if (c.get()) p.cheats[c.label] = true; } catch (e) {} });
    Object.keys(frozen).forEach(function (k) { p.frozen[k] = frozen[k].v; });
    return p;
  }
  // строки «Значений» по ключу заморозки «раздел/имя»
  function rowsByKey() {
    var out = {};
    (A.stats() || []).forEach(function (sec) {
      (sec.rows || []).forEach(function (r) { out[(sec.title || "") + "/" + r.name] = r; });
    });
    return out;
  }
  function applyProfile(p) {
    if (p.speed != null && p.speed !== 1) setSpeed(p.speed);
    (A.cheats ? A.cheats() || [] : []).forEach(function (c) { if (p.cheats && p.cheats[c.label]) { try { c.set(true); } catch (e) {} } });
    var rows = Object.keys(p.frozen || {}).length ? rowsByKey() : {}, n = 0;
    Object.keys(p.frozen || {}).forEach(function (k) {
      var r = rows[k];
      if (!r) return;
      frozen[k] = { v: p.frozen[k], set: r.set, get: r.get };
      n++;
    });
    if (n) startTick();
    return n;
  }
  function notice(msg) {
    var b = el("div", null, msg);
    b.style.cssText = "position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:2147482999;background:" + ACCENT +
      ";color:#07110f;font:700 13px 'Segoe UI',sans-serif;padding:7px 16px;border-radius:10px;pointer-events:none";
    document.body.appendChild(b);
    setTimeout(function () { b.remove(); }, 3500);
  }
  // ждём, пока игра загрузит данные (до минуты), и ставим профиль один раз
  (function autoProfile() {
    var p = loadProfile(), tries = 0;
    if (!p) return;
    var t = setInterval(function () {
      var ok = false;
      try { ok = A.ready() && document.body; } catch (e) {}
      if (!ok && ++tries < 120) return;
      clearInterval(t);
      if (ok) { var n = applyProfile(p); notice("TEST MENU: профиль игры применён" + (n ? " (заморозок: " + n + ")" : "")); }
    }, 500);
  })();

  // ------------------------------------------------------------------ стиль
  function injectCss() {
    if (document.getElementById("tm-style")) return;
    var s = document.createElement("style");
    s.id = "tm-style";
    s.textContent = [
      "@keyframes tmFade{from{opacity:0}to{opacity:1}}",
      "@keyframes tmPop{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}",
      "#tm-ov{position:fixed;inset:0;z-index:2147483000;background:radial-gradient(1200px 820px at 50% 28%,rgba(8,12,20,.7),rgba(4,6,11,.84));",
      "backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);display:flex;align-items:center;",
      "justify-content:center;animation:tmFade .16s ease;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}",
      "#tm-win{width:min(720px,94vw);max-height:84vh;display:flex;flex-direction:column;",
      "background:linear-gradient(180deg,rgba(22,27,38,.98),rgba(15,19,28,.98));border:1px solid " + ACCENT + "4d;border-radius:20px;overflow:hidden;",
      "color:#e7ebf2;box-shadow:0 32px 90px -20px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.04) inset,0 0 64px -24px " + ACCENT + "aa;",
      "animation:tmPop .2s cubic-bezier(.2,.7,.3,1)}",
      "#tm-head{background:linear-gradient(135deg," + ACCENT + "," + ACCENT + "d0);color:#07110f;",
      "padding:14px 16px;display:flex;gap:12px;align-items:center;cursor:move;user-select:none;",
      "box-shadow:inset 0 1px 0 rgba(255,255,255,.28)}",
      "#tm-head .dot{flex:none;margin-right:30px;width:9px;height:9px;border-radius:50%;background:#07110f66;box-shadow:15px 0 0 #07110f40,30px 0 0 #07110f26}",
      "#tm-head .t{flex:1;font-weight:800;font-size:16px;letter-spacing:.3px}",
      "#tm-head .t small{display:block;font-weight:600;font-size:11px;opacity:.68;letter-spacing:.2px}",
      "#tm-head button{background:#07110f26;color:#07110f;border:0;border-radius:9px;width:32px;height:29px;",
      "cursor:pointer;font-weight:800;font-size:14px;transition:background .12s}",
      "#tm-head button:hover{background:#07110f45}",
      "#tm-tabs{display:flex;gap:5px;padding:7px;background:#0d111a;border-bottom:1px solid #ffffff0d}",
      "#tm-tabs button{flex:1;background:transparent;color:#8b93a3;border:0;border-radius:11px;padding:9px 8px;cursor:pointer;",
      "font-size:13px;font-weight:700;transition:all .14s}",
      "#tm-tabs button:hover{color:#e7ebf2;background:#ffffff0a}",
      "#tm-tabs button.on{color:#07110f;background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc)}",
      "#tm-tools{display:flex;gap:8px;align-items:center;padding:9px 16px;background:#0b0e14;",
      "font-size:12px;color:#8b93a3;flex-wrap:wrap;border-bottom:1px solid #ffffff08}",
      "#tm-tools .seg{display:inline-flex;background:#ffffff0d;border-radius:10px;padding:3px;gap:2px}",
      "#tm-tools .seg button{background:transparent;color:#c7ccd4;border:0;border-radius:8px;padding:4px 12px;",
      "cursor:pointer;font-size:12px;font-weight:700;transition:all .12s}",
      "#tm-tools .seg button.on{background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);color:#07110f}",
      "#tm-body{overflow:auto;padding:8px 12px 12px;scrollbar-width:thin;scrollbar-color:#313a4c transparent}",
      "#tm-win button:focus-visible,.tm-finput:focus-visible{outline:2px solid " + ACCENT + ";outline-offset:2px}",
      "#tm-head button:focus-visible{outline-color:#0a0c10}",
      "@media(prefers-reduced-motion:reduce){#tm-ov,#tm-win{animation:none}#tm-win *,.tm-row,.tm-act,.tm-row .ctrl button{transition:none!important}.tm-act:hover,.tm-row .ctrl button:hover{transform:none}}",
      ".tm-filter{padding:2px 2px 10px;position:sticky;top:-10px;background:rgba(20,25,35,.98);z-index:1}",
      ".tm-finput{width:100%;box-sizing:border-box;background:#0b0e14;border:1px solid #313a4c;border-radius:10px;",
      "color:#e7ebf2;padding:9px 12px;font-size:13px;outline:none;transition:border-color .12s,box-shadow .12s}",
      ".tm-finput:focus{border-color:" + ACCENT + ";box-shadow:0 0 0 3px " + ACCENT + "22}",
      ".tm-sec{color:" + ACCENT + ";font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;",
      "margin:16px 6px 8px;display:flex;align-items:center;gap:10px}",
      ".tm-sec::after{content:'';flex:1;height:1px;background:linear-gradient(90deg," + ACCENT + "40,transparent)}",
      ".tm-row{display:flex;gap:10px;align-items:center;padding:9px 11px;border-radius:11px;transition:background .12s,box-shadow .12s}",
      ".tm-row:hover{background:#ffffff0a;box-shadow:inset 2px 0 0 " + ACCENT + "}",
      ".tm-row .k{flex:1;font-size:13.5px;word-break:break-word}",
      ".tm-row .v{font-family:'Consolas','SF Mono',monospace;font-size:13px;font-weight:800;color:" + ACCENT + ";",
      "background:" + ACCENT + "1c;border:1px solid " + ACCENT + "33;padding:3px 10px;border-radius:8px;min-width:58px;text-align:right}",
      ".tm-row .ctrl{display:flex;gap:5px}",
      ".tm-row .ctrl button{background:linear-gradient(180deg,#232a38,#191f2c);color:#e7ebf2;border:1px solid #313a4c;border-radius:9px;min-width:32px;height:32px;",
      "padding:0 9px;cursor:pointer;font-size:14px;font-weight:700;transition:all .1s}",
      ".tm-ico{width:18px;height:18px;vertical-align:middle;pointer-events:none}",
      ".tm-row .ctrl button.on{background:" + ACCENT + ";color:#07110f;border-color:" + ACCENT + "}",
      ".tm-row .ctrl button:hover{background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);color:#07110f;border-color:" + ACCENT + ";transform:translateY(-1px)}",
      ".tm-msg{color:#c7ccd4;font-size:13px;padding:8px 6px;line-height:1.4}",
      ".tm-msg b{color:" + ACCENT + "}",
      ".tm-scanbar{display:flex;flex-wrap:wrap;gap:6px;padding:6px 4px}",
      ".tm-scanbar button{background:linear-gradient(180deg,#232a38,#191f2c);color:#e7ebf2;border:1px solid #313a4c;border-radius:9px;padding:8px 13px;cursor:pointer;font-size:12.5px;font-weight:600;transition:all .1s}",
      ".tm-scanbar button:hover{background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);color:#07110f;border-color:" + ACCENT + "}",
      ".tm-up{color:#5ad469}.tm-down{color:#ff6b6b}",
      ".tm-act{padding:13px 15px;margin:7px 4px;border-radius:13px;background:linear-gradient(180deg,#ffffff0d,#ffffff05);border:1px solid #ffffff12;border-left:3px solid " + ACCENT + "80;",
      "cursor:pointer;transition:all .14s}",
      ".tm-act:hover{background:" + ACCENT + "1f;border-color:" + ACCENT + "80;border-left-color:" + ACCENT + ";transform:translateY(-2px);box-shadow:0 12px 26px -12px " + ACCENT + "aa}",
      ".tm-act .l{font-size:14px;font-weight:700}",
      ".tm-act .d{font-size:11.5px;color:#8b93a3;margin-top:4px;font-family:'Consolas',monospace}",
      "#tm-foot{padding:10px 16px;background:#080b11;color:#5b6373;font-size:11.5px;border-top:1px solid #ffffff0a}",
      "#tm-foot kbd{background:#1e2432;border:1px solid #313a4c;border-radius:6px;padding:1px 6px;font-size:11px;color:#c7ccd4}",
      "#tm-toast{position:absolute;left:50%;bottom:60px;transform:translateX(-50%);background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);",
      "color:#07110f;font-weight:800;font-size:13px;padding:9px 20px;border-radius:12px;opacity:0;",
      "transition:opacity .2s;pointer-events:none;box-shadow:0 10px 30px -8px " + ACCENT + "aa}",
      "#tm-toast.err{background:#ff5b5b;color:#160404}",
      "#tm-speed{position:fixed;right:12px;top:10px;z-index:2147482999;background:" + ACCENT + ";color:#07110f;font:800 13px 'Segoe UI',sans-serif;",
      "padding:4px 10px;border-radius:9px;pointer-events:none;box-shadow:0 6px 18px -6px #000a}",
      "#tm-body::-webkit-scrollbar{width:11px}#tm-body::-webkit-scrollbar-thumb{background:#313a4c;border-radius:6px;border:3px solid transparent;background-clip:padding-box}",
      "#tm-body::-webkit-scrollbar-thumb:hover{background:" + ACCENT + ";background-clip:padding-box}"
    ].join("");
    document.head.appendChild(s);
  }

  // ------------------------------------------------------------------ helpers
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function mkBtn(parent, label, fn) { var b = el("button", null, label); b.addEventListener("click", fn); parent.appendChild(b); return b; }
  // кнопка-значок из TM_ICONS (tm_icons.js, data-URI); без значков — текстовая подпись
  function mkIco(parent, ico, alt, fn, tip, text) {
    var src = (typeof TM_ICONS !== "undefined" && TM_ICONS) ? TM_ICONS[ico] : null;
    var b = mkBtn(parent, src ? null : (text ? (alt ? alt + " " : "") + text : alt), fn);
    if (src) {
      var im = el("img", "tm-ico"); im.src = src; im.alt = alt; b.appendChild(im);
      if (text) b.appendChild(document.createTextNode(" " + text));
    }
    if (tip) b.title = tip;
    return b;
  }
  function fmt(v, type) {
    if (type === "bool") return v ? "ВКЛ" : "выкл";
    // дробные (координаты, таймеры) — не длиннее 3 знаков после точки
    if (typeof v === "number" && v % 1 !== 0) return String(Math.round(v * 1000) / 1000);
    return String(v);
  }

  function section(list, title) { list.appendChild(el("div", "tm-sec", title)); }
  function row(list, name, valStr) {
    var r = el("div", "tm-row");
    r.appendChild(el("div", "k", name));
    var v = el("div", "v", valStr); r.appendChild(v);
    var ctrl = el("div", "ctrl"); r.appendChild(ctrl);
    list.appendChild(r);
    return { row: r, ctrl: ctrl, setV: function (s) { v.textContent = s; } };
  }

  var toastTimer = null;
  function toast(msg, isErr) {
    if (!overlay) return;
    var t = overlay.querySelector("#tm-toast");
    if (!t) { t = el("div", null, ""); t.id = "tm-toast"; overlay.appendChild(t); }
    t.className = isErr ? "err" : "";
    t.textContent = msg; t.style.opacity = "1";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.style.opacity = "0"; }, 1100);
  }

  // ------------------------------------------------------------------ вкладки
  function applyFilter(list) {
    var q = filter;
    Array.prototype.forEach.call(list.querySelectorAll(".tm-row"), function (r) {
      var k = r.querySelector(".k");
      if (!k) return;
      r.style.display = (!q || k.textContent.toLowerCase().indexOf(q) >= 0) ? "" : "none";
    });
  }

  function renderVals(list) {
    var secs = A.stats() || [];
    if (!secs.length) { list.appendChild(el("div", "tm-msg", A.footMissing || "Данные недоступны.")); return; }

    var fbar = el("div", "tm-filter");
    var inp = el("input", "tm-finput");
    inp.type = "text"; inp.placeholder = "фильтр по имени…"; inp.value = filter;
    inp.addEventListener("input", function () { filter = inp.value.toLowerCase(); applyFilter(list); });
    fbar.appendChild(inp); list.appendChild(fbar);

    secs.forEach(function (sec) {
      if (sec.title) section(list, sec.title);
      (sec.rows || []).forEach(function (r) {
        var h = row(list, r.name, fmt(r.get(), r.type));
        var fkey = (sec.title || "") + "/" + r.name;
        function rf() { h.setV(fmt(r.get(), r.type)); }
        // правка замороженного значения = новое удерживаемое значение
        function put(v) { r.set(v); if (frozen[fkey]) frozen[fkey].v = r.get(); rf(); }
        live.push(rf);
        if (r.where) mkBtn(h.ctrl, "где", function () {
          toast("Ищу в событиях игры…");
          r.where(function (lines) { showInfo(r.name, lines); });
        }).title = "Где игра меняет и проверяет это значение";
        if (r.type === "num") {
          mkBtn(h.ctrl, "−", function () { put(r.get() - step); });
          mkBtn(h.ctrl, "+", function () { put(r.get() + step); });
          mkIco(h.ctrl, "edit", "ввод", function () { var v = prompt(r.name + ":", String(r.get())); if (v !== null && v.trim() !== "" && !isNaN(Number(v))) put(Number(v)); }, "Ввести значение");
          var fb = mkIco(h.ctrl, "snow", "стоп", function () {
            if (frozen[fkey]) delete frozen[fkey]; else frozen[fkey] = { v: r.get(), set: r.set, get: r.get };
            fb.className = frozen[fkey] ? "on" : "";
          });
          fb.title = "Заморозить: игра не сможет изменить значение";
          if (frozen[fkey]) { frozen[fkey].set = r.set; frozen[fkey].get = r.get; fb.className = "on"; }
        } else if (r.type === "bool") {
          mkIco(h.ctrl, "swap", "вкл/выкл", function () { r.set(!r.get()); rf(); }, "Переключить");
        } else {
          mkIco(h.ctrl, "edit", "ввод", function () { var v = prompt(r.name + ":", String(r.get())); if (v !== null) { r.set(v); rf(); } }, "Ввести значение");
        }
      });
    });
    applyFilter(list);
  }

  // окно-справка поверх вкладки: «← назад» возвращает список
  function showInfo(title, lines) {
    if (!bodyEl) return;
    live = [];
    bodyEl.innerHTML = "";
    var bar = el("div", "tm-scanbar");
    mkBtn(bar, "← назад", rerender);
    bodyEl.appendChild(bar);
    section(bodyEl, title);
    lines.forEach(function (l) { bodyEl.appendChild(el("div", "tm-msg", l)); });
  }

  function scanNarrow(mode) {
    if (!scanCands) { scanMsg = "Сначала «Снимок»."; return; }
    var cur = A.nums(), keep = [];
    scanCands.forEach(function (k) {
      var a = scanSnap[k], b = cur[k];
      if (a == null || b == null) return;
      var ok = mode === "changed" ? b !== a : mode === "same" ? b === a : mode === "up" ? b > a : mode === "down" ? b < a : false;
      if (ok) keep.push(k);
    });
    scanCands = keep; scanSnap = cur; scanMsg = "Осталось кандидатов: <b>" + keep.length + "</b>";
  }
  function renderScan(list) {
    var bar = el("div", "tm-scanbar");
    mkIco(bar, "camera", "", function () { scanSnap = A.nums(); scanCands = Object.keys(scanSnap); scanMsg = "Снимок: <b>" + scanCands.length + "</b> числовых. Измени в игре и сужай."; rerender(); }, "Запомнить текущие числа", "Снимок");
    mkBtn(bar, "изменились", function () { scanNarrow("changed"); rerender(); });
    mkBtn(bar, "не изменились", function () { scanNarrow("same"); rerender(); });
    mkBtn(bar, "больше ▲", function () { scanNarrow("up"); rerender(); });
    mkBtn(bar, "меньше ▼", function () { scanNarrow("down"); rerender(); });
    mkBtn(bar, "сброс", function () { scanSnap = {}; scanCands = null; scanMsg = "Сброшено."; rerender(); });
    list.appendChild(bar);
    var m = el("div", "tm-msg"); m.innerHTML = scanMsg; list.appendChild(m);
    if (scanCands && scanCands.length && scanCands.length <= 60) {
      var cur = A.nums();
      scanCands.slice().sort().forEach(function (k) {
        var o = scanSnap[k], c = cur[k];
        var h = row(list, k, "");
        var vv = h.row.querySelector(".v");
        vv.textContent = o + " → " + c;
        if (c > o) vv.className = "v tm-up"; else if (c < o) vv.className = "v tm-down";
      });
    } else if (scanCands && scanCands.length > 60) {
      list.appendChild(el("div", "tm-msg", "Слишком много (" + scanCands.length + ") — сужай кнопками выше."));
    }
  }

  function renderActions(list) {
    (A.actions() || []).forEach(function (a) {
      var card = el("div", "tm-act");
      card.appendChild(el("div", "l", a.label));
      if (a.desc) card.appendChild(el("div", "d", a.desc));
      card.addEventListener("click", function () {
        try { a.run(); toast("Готово"); if (tab !== "act") rerender(); }
        catch (e) { toast("Ошибка", true); console.error("[TM]", e); }
      });
      list.appendChild(card);
    });
  }

  function renderGame(list) {
    if (A.speed) {
      section(list, "Скорость игры");
      var bar = el("div", "tm-scanbar");
      [[0, "пауза"], [0.25, "×0.25"], [0.5, "×0.5"], [1, "×1"], [2, "×2"], [3, "×3"], [5, "×5"]].forEach(function (d) {
        var b = mkBtn(bar, d[1], function () { setSpeed(d[0]); rerender(); });
        if (d[0] === speed) { b.style.background = ACCENT; b.style.color = "#07110f"; }
      });
      list.appendChild(bar);
      list.appendChild(el("div", "tm-msg", "Ускорение — пропускать бои и прогулки, замедление и пауза — разглядеть и успеть. Значок в углу показывает темп, пока он не ×1."));
    }
    var ch = A.cheats ? (A.cheats() || []) : [];
    if (ch.length) {
      section(list, "Режимы");
      ch.forEach(function (c) {
        var h = row(list, c.label, fmt(c.get(), "bool"));
        if (c.desc) h.row.title = c.desc;
        function rf() { h.setV(fmt(c.get(), "bool")); }
        live.push(rf);
        mkIco(h.ctrl, "swap", "вкл/выкл", function () { try { c.set(!c.get()); } catch (e) { toast("Ошибка", true); console.error("[TM]", e); } rf(); }, c.desc || "Переключить");
      });
    }
    if (A.jumps) {
      section(list, A.jumps.title || "Переходы");
      if (!jumpList) {
        var jb = el("div", "tm-scanbar");
        mkBtn(jb, "Показать список", function () {
          toast("Загружаю…");
          A.jumps.load(function (rows) { jumpList = rows; if (tab === "game") rerender(); });
        });
        list.appendChild(jb);
      } else {
        var jf = el("input", "tm-finput");
        jf.placeholder = "фильтр…"; jf.value = jumpFilter;
        jf.addEventListener("input", function () {
          jumpFilter = jf.value.toLowerCase();
          Array.prototype.forEach.call(list.querySelectorAll(".tm-jump"), function (r) {
            r.style.display = r.textContent.toLowerCase().indexOf(jumpFilter) >= 0 ? "" : "none";
          });
        });
        list.appendChild(jf);
        jumpList.forEach(function (j) {
          var h = row(list, j.name, "");
          h.row.classList.add("tm-jump");
          h.row.querySelector(".v").remove();
          if (j.hint) h.row.title = j.hint;
          mkBtn(h.ctrl, "перейти", function () { try { j.go(); close(); } catch (e) { toast("Не вышло", true); console.error("[TM]", e); } });
          if (jumpFilter && j.name.toLowerCase().indexOf(jumpFilter) < 0) h.row.style.display = "none";
        });
      }
    }
    section(list, "Профиль игры");
    var pr = loadProfile(), prb = el("div", "tm-scanbar");
    mkBtn(prb, "Сохранить профиль", function () {
      try { localStorage.setItem(FKEY, JSON.stringify(profileNow())); toast("Профиль сохранён"); } catch (e) { toast("Не сохранить", true); }
      rerender();
    }).title = "Темп, включённые режимы и заморозки будут ставиться сами при каждом запуске игры";
    if (pr) mkBtn(prb, "Удалить профиль", function () { try { localStorage.removeItem(FKEY); } catch (e) {} rerender(); });
    list.appendChild(prb);
    list.appendChild(el("div", "tm-msg", pr
      ? "Сейчас в профиле: темп ×" + pr.speed + ", режимов " + Object.keys(pr.cheats || {}).length + ", заморозок " + Object.keys(pr.frozen || {}).length + ". Ставится сам при запуске игры."
      : "Профиля нет. Включи нужное (темп, режимы, заморозки во «Значениях») и нажми «Сохранить профиль»."));
    if (A.places) {
      section(list, "Точки телепорта");
      var pb = el("div", "tm-scanbar");
      mkBtn(pb, "Запомнить место", function () {
        var p = null;
        try { p = A.places.here(); } catch (e) { console.error("[TM]", e); }
        if (!p) { toast("Место сейчас не определить", true); return; }
        var a = loadPlaces(); a.push(p); savePlaces(a); rerender();
      });
      list.appendChild(pb);
      var pl = loadPlaces();
      if (!pl.length) list.appendChild(el("div", "tm-msg", "Пусто. Встань в нужное место и нажми «Запомнить место» — потом сюда можно вернуться одной кнопкой."));
      pl.forEach(function (p, i) {
        var h = row(list, p.name || ("точка " + (i + 1)), "");
        h.row.querySelector(".v").remove();
        mkBtn(h.ctrl, "сюда", function () {
          try { A.places.go(p); close(); } catch (e) { toast("Не вышло", true); console.error("[TM]", e); }
        });
        mkBtn(h.ctrl, "×", function () { var a = loadPlaces(); a.splice(i, 1); savePlaces(a); rerender(); }).title = "Удалить точку";
      });
    }
  }

  // Раз в 400 мс: вернуть замороженные значения и обновить показанные. Заморозка
  // работает и при закрытом меню — таймер живёт, пока есть хоть одно замороженное.
  function tick() {
    var any = false;
    Object.keys(frozen).forEach(function (k) {
      any = true;
      try { if (A.ready() && frozen[k].get() !== frozen[k].v) frozen[k].set(frozen[k].v); } catch (e) {}
    });
    if (overlay && (tab === "vals" || tab === "game")) live.forEach(function (f) { try { f(); } catch (e) {} });
    if (!overlay && !any) { clearInterval(liveTimer); liveTimer = null; }
  }
  function startTick() { if (!liveTimer) liveTimer = setInterval(tick, 400); }

  function rerender() {
    if (!bodyEl) return;
    live = [];
    bodyEl.innerHTML = "";
    if (!A.ready()) { bodyEl.appendChild(el("div", "tm-msg", A.footMissing || "Данные игры недоступны.")); return; }
    if (tab === "game" && !hasGameTab()) tab = "vals";
    if (tab === "vals") renderVals(bodyEl);
    else if (tab === "game") renderGame(bodyEl);
    else if (tab === "scan") renderScan(bodyEl);
    else renderActions(bodyEl);
  }

  // ------------------------------------------------------------------ drag
  // Не дать окну уехать за край (сохранённая позиция + сменившийся размер окна игры).
  function clampWin() {
    if (!winEl || winEl.style.position !== "fixed") return;
    var r = winEl.getBoundingClientRect();
    var l = Math.min(Math.max(r.left, 80 - r.width), window.innerWidth - 80);
    var t = Math.min(Math.max(r.top, 0), window.innerHeight - 48);
    winEl.style.left = l + "px"; winEl.style.top = t + "px";
  }

  function enableDrag(head) {
    head.addEventListener("pointerdown", function (e) {
      if (e.target.closest("button")) return;
      var rect = winEl.getBoundingClientRect();
      var dx = e.clientX - rect.left, dy = e.clientY - rect.top;
      winEl.style.position = "fixed"; winEl.style.margin = "0";
      winEl.style.left = rect.left + "px"; winEl.style.top = rect.top + "px";
      function move(ev) { if (!winEl) return; winEl.style.left = (ev.clientX - dx) + "px"; winEl.style.top = (ev.clientY - dy) + "px"; }
      // capture: оверлей глушит всплытие событий мыши (см. open), до document они не дойдут
      function up() {
        document.removeEventListener("pointermove", move, true); document.removeEventListener("pointerup", up, true);
        if (!winEl) return;
        clampWin();
        winPos = { left: winEl.style.left, top: winEl.style.top }; saveState();
      }
      document.addEventListener("pointermove", move, true); document.addEventListener("pointerup", up, true);
      e.preventDefault();
    });
  }

  // ------------------------------------------------------------------ окно
  function close() {
    if (!overlay) return;
    overlay.remove(); overlay = null; winEl = bodyEl = null;
    if (A.onClose) { try { A.onClose(); } catch (e) { console.error("[TM]", e); } }
  }

  // Мышь/тач по оверлею не должны доходить до игры: движки слушают document
  // (RPG Maker по клику сквозь меню отправлял героя в точку под курсором).
  var SWALLOW = ["mousedown", "mouseup", "mousemove", "click", "dblclick", "contextmenu", "wheel",
                 "touchstart", "touchmove", "touchend", "pointerdown", "pointerup", "pointermove"];
  function swallow(e) { e.stopPropagation(); }

  function open() {
    injectCss();
    loadState();
    overlay = el("div"); overlay.id = "tm-ov";
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    SWALLOW.forEach(function (n) { overlay.addEventListener(n, swallow); });
    winEl = el("div"); winEl.id = "tm-win";

    var head = el("div"); head.id = "tm-head";
    head.appendChild(el("span", "dot"));
    var t = el("div", "t"); t.innerHTML = "TEST MENU<small>" + (A.title || "") + "</small>"; head.appendChild(t);
    mkBtn(head, "X", close).title = "Закрыть";
    winEl.appendChild(head);
    enableDrag(head);

    var tabs = el("div"); tabs.id = "tm-tabs";
    [["vals", "Значения"], ["game", "Игра"], ["scan", "Сканер"], ["act", "Экшены"]].forEach(function (d) {
      if (d[0] === "game" && !hasGameTab()) return;
      var b = mkBtn(tabs, d[1], function () { tab = d[0]; Array.prototype.forEach.call(tabs.children, function (o) { o.className = ""; }); b.className = "on"; saveState(); rerender(); });
      if (d[0] === tab) b.className = "on";
    });
    winEl.appendChild(tabs);

    var tools = el("div"); tools.id = "tm-tools";
    tools.appendChild(el("span", null, "шаг:"));
    var seg = el("div", "seg");
    [1, 10, 100].forEach(function (s) {
      var b = mkBtn(seg, "×" + s, function () { step = s; Array.prototype.forEach.call(seg.children, function (o) { o.className = ""; }); b.className = "on"; saveState(); });
      if (s === step) b.className = "on";
    });
    tools.appendChild(seg);
    winEl.appendChild(tools);

    bodyEl = el("div"); bodyEl.id = "tm-body"; winEl.appendChild(bodyEl);

    var foot = el("div"); foot.id = "tm-foot";
    foot.innerHTML = A.ready()
      ? "<kbd>Shift</kbd>+<kbd>T</kbd> меню | <kbd>Esc</kbd> закрыть | тяни за шапку"
      : (A.footMissing || "Данные игры недоступны.");
    winEl.appendChild(foot);

    overlay.appendChild(winEl);
    document.body.appendChild(overlay);
    if (winPos && winPos.left) { winEl.style.position = "fixed"; winEl.style.margin = "0"; winEl.style.left = winPos.left; winEl.style.top = winPos.top; clampWin(); }
    rerender();
    startTick();
  }

  function toggle() { if (overlay) close(); else open(); }
  function isTyping(e) {
    var t = e.target;
    return !!t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
  }
  // Один перехватчик на window (capture): хоткей меню + пока меню открыто, клавиши
  // не уходят в игру (иначе стрелки двигали героя, а буквы в фильтре жали OK/отмену).
  window.addEventListener("keydown", function (e) {
    // e.code — чтобы Shift+T работал и в русской раскладке; заглавная «T» в поле ввода — это текст
    var hot = e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey && (e.code === "KeyT" || e.key === "T" || e.key === "t");
    if (hot && !isTyping(e)) { e.preventDefault(); e.stopPropagation(); toggle(); return; }
    if (!overlay) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    e.stopPropagation();
  }, true);
  ["keyup", "keypress"].forEach(function (n) {
    window.addEventListener(n, function (e) { if (overlay) e.stopPropagation(); }, true);
  });
})();
