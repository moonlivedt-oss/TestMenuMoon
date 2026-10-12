#!/usr/bin/env python3
"""ДАННЫЕ манифеста тест-меню (правится GUI-студией studio.py или руками).
Логика (ROOTS / автопоиск лаунчера) — в games.py, который импортирует отсюда."""

G = 'C:/Games'
ACCENT = '#38e0c8'

GAMES = {

1: {
    'title': 'TEST MENU | Moonlight Academy',
    'root': 'C:/Games/MoonlightAcademy/game',
    'status': "пример: новелла на Ren'Py со статами, действиями и твиком",
    'tweak': 'example_debug.rpy',
    "stats": [
        ('— Герой —', ''),
        ('Деньги', 'money', '0', ''),
        ('Здоровье', 'hp', '0', '100'),
        ('День', 'day'),
        ('— Персонажи —', ''),
        ('Mira | симпатия', 'mira_love', '0', '10'),
        ('Lena | доверие', 'lena.trust', '0', '10'),
    ],
    "actions": [
        ('Деньги +100', 'money += 100'),
        ('Выдать зелье', 'inventory["potion"] = inventory.get("potion", 0) + 1'),
        ('Следующий день', 'day += 1'),
    ],
},
2: {
    'title': 'TEST MENU | Star Harbor',
    'root': 'C:/Games/StarHarbor',
    'status': 'пример: RPG Maker MZ (данные — в рантайме)',
    "stats": [

    ],
    "actions": [

    ],
},
3: {
    'title': 'TEST MENU | Pixel Bakery',
    'root': 'C:/Games/PixelBakery',
    'status': 'пример: HTML5-игра',
    "stats": [

    ],
    "actions": [

    ],
},
}
