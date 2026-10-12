#!/usr/bin/env python3
"""Генерация 9-slice UI-тайлов для Ren'Py тест-меню (чёткие скругления через PIL).

Пишет PNG в assets/tm_ui/. Белые тайлы (ring/head/btn) тонируются в акцент рантаймом
движка через TintMatrix — поэтому per-game акцент сохраняется. Тёмные тайлы
(panel/foot) нейтральны. Радиусы = insets для Frame() (см. R/RB ниже, движок обязан
использовать те же числа).

Запуск:  python tools/gen_ui_frames.py     (тайлы в assets/tm_ui/ + макет _mockup.png)
"""
import os
from PIL import Image, ImageDraw, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "tm_ui"))

R = 26          # радиус углов панели/шапки/футера  (= Frame inset)
RB = 13         # радиус кнопок/чипов                (= Frame inset)
STROKE = 3      # толщина акцентного кольца
PANEL_TOP = (26, 32, 46)      # верх градиента панели
PANEL_BOT = (14, 18, 27)      # низ
FOOT = (11, 14, 20)           # футер


def rounded_mask(w, h, rad, corners=(True, True, True, True)):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    rad = min(rad, min(w, h) // 2)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=rad, fill=255, corners=corners)
    return m


def _vgrad(w, h, top, bot):
    g = Image.new("RGBA", (w, h))
    px = g.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
        for x in range(w):
            px[x, y] = c
    return g


def gen_panel():
    w = h = 2 * R + 10
    g = _vgrad(w, h, PANEL_TOP, PANEL_BOT)
    g.putalpha(rounded_mask(w, h, R))
    return g


def gen_head():
    w = h = 2 * R + 10
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    img.putalpha(rounded_mask(w, h, R, corners=(True, True, False, False)))
    return img


def gen_foot():
    w = h = 2 * R + 10
    img = Image.new("RGBA", (w, h), FOOT + (255,))
    img.putalpha(rounded_mask(w, h, R, corners=(False, False, True, True)))
    return img


def gen_ring():
    w = h = 2 * R + 12
    outer = rounded_mask(w, h, R)
    inner = rounded_mask(w - 2 * STROKE, h - 2 * STROKE, max(1, R - STROKE))
    inv = Image.new("L", (w, h), 0)
    inv.paste(inner, (STROKE, STROKE))
    ringmask = ImageChops.subtract(outer, inv)
    white = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    white.putalpha(ringmask)
    return white


def gen_btn():
    w = h = 2 * RB + 8
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    img.putalpha(rounded_mask(w, h, RB))
    return img


def nine_slice(tile, inset, tw, th):
    """9-slice: углы фикс, края и центр растягиваются. inset — int или (l,t,r,b)."""
    l, t, r, b = (inset, inset, inset, inset) if isinstance(inset, int) else inset
    W, Hh = tile.size
    out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    tcw, tch = tw - l - r, th - t - b
    out.alpha_composite(tile.crop((0, 0, l, t)), (0, 0))
    out.alpha_composite(tile.crop((W - r, 0, W, t)), (tw - r, 0))
    out.alpha_composite(tile.crop((0, Hh - b, l, Hh)), (0, th - b))
    out.alpha_composite(tile.crop((W - r, Hh - b, W, Hh)), (tw - r, th - b))
    out.alpha_composite(tile.crop((l, 0, W - r, t)).resize((tcw, t)), (l, 0))
    out.alpha_composite(tile.crop((l, Hh - b, W - r, Hh)).resize((tcw, b)), (l, th - b))
    out.alpha_composite(tile.crop((0, t, l, Hh - b)).resize((l, tch)), (0, t))
    out.alpha_composite(tile.crop((W - r, t, W, Hh - b)).resize((r, tch)), (tw - r, t))
    out.alpha_composite(tile.crop((l, t, W - r, Hh - b)).resize((tcw, tch)), (l, t))
    return out


def tint(img, hexc):
    r, g, b = (int(hexc[k:k + 2], 16) for k in (1, 3, 5))
    out = Image.new("RGBA", img.size, (r, g, b, 0))
    out.putalpha(img.getchannel("A"))
    return out


def _rgb(hexc):
    return tuple(int(hexc[k:k + 2], 16) for k in (1, 3, 5))


def save_all():
    os.makedirs(OUT, exist_ok=True)
    tiles = {"tm_panel": gen_panel(), "tm_head": gen_head(),
             "tm_foot": gen_foot(), "tm_ring": gen_ring(), "tm_btn": gen_btn()}
    for name, img in tiles.items():
        img.save(os.path.join(OUT, name + ".png"))
    return tiles


def mockup(tiles, accent="#38e0c8", path=None):
    """Собрать превью меню из тайлов 9-slice — как это сделает Ren'Py Frame."""
    W, H = 720, 470
    ox, oy = 30, 30
    scene = Image.new("RGBA", (W + 60, H + 60), (10, 13, 19, 255))
    ac = _rgb(accent)
    scene.alpha_composite(nine_slice(tint(tiles["tm_ring"], accent), R, W + 6, H + 6), (ox - 3, oy - 3))
    scene.alpha_composite(nine_slice(tiles["tm_panel"], R, W, H), (ox, oy))
    HEADH, FOOTH = 56, 40
    scene.alpha_composite(nine_slice(tint(tiles["tm_head"], accent), (R, R, R, 6), W, HEADH), (ox, oy))
    scene.alpha_composite(nine_slice(tiles["tm_foot"], (R, 6, R, R), W, FOOTH), (ox, oy + H - FOOTH))
    d = ImageDraw.Draw(scene)
    ink = (7, 17, 15)
    d.text((ox + 22, oy + 16), "TEST MENU", fill=ink)
    d.text((ox + 22, oy + 30), "game_4  |  Ren'Py", fill=ink)
    d.rectangle((ox, oy + HEADH, ox + W, oy + HEADH + 40), fill=(22, 27, 38, 255))
    for i, t in enumerate(["Перемотка", "Характеристики", "Действия", "Сканер", "Настройки"]):
        d.text((ox + 22 + i * 135, oy + HEADH + 15), t, fill=(200, 205, 214))
    d.rectangle((ox, oy + HEADH + 40, ox + W, oy + HEADH + 42), fill=ac + (255,))
    yy = oy + HEADH + 66
    for name, val in [("Деньги", "1250"), ("Сила", "42"), ("Энергия", "80")]:
        d.text((ox + 26, yy + 9), name, fill=(231, 235, 242))
        d.rounded_rectangle((ox + W - 214, yy + 4, ox + W - 140, yy + 34), radius=8,
                            fill=ac + (40,), outline=ac + (110,))
        d.text((ox + W - 198, yy + 12), val, fill=ac + (255,))
        for j, s in enumerate(["-", "+", "*"]):
            bx = ox + W - 128 + j * 40
            b2 = tint(nine_slice(tiles["tm_btn"], RB, 34, 34), "#ffffff")
            b2.putalpha(b2.getchannel("A").point(lambda a: int(a * 0.10)))
            scene.alpha_composite(b2, (bx, yy + 1))
            d.text((bx + 14, yy + 9), s, fill=(231, 235, 242))
        yy += 52
    d.text((ox + 18, oy + H - FOOTH + 13), "Shift+T - меню  |  тяни за шапку", fill=(91, 99, 115))
    p = path or os.path.join(OUT, "_mockup.png")
    scene.convert("RGB").save(p)
    return p


if __name__ == "__main__":
    t = save_all()
    print("tiles ->", OUT)
    print("mockup ->", mockup(t))
