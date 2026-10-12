# RPG Maker MV/MZ — тест-меню (PoC)

Третий движок. MV/MZ — браузерный/NW.js рантайм: переменные в `$gameVariables`,
переключатели в `$gameSwitches`, деньги в `$gameParty`. Меню внедряется `<script>`-ом
в `index.html` игры.

## Файлы
- `tm_menu.js` — **адаптер данных** (`TM_ADAPTER`: золото/переменные/переключатели через
  `$gameParty`/`$gameVariables`/`$gameSwitches`). Графика/логика — в общем
  `../_shared/tm_menu_core.js` (вкладки **Значения/Сканер/Экшены**, перетаскивание, анимации);
  инжектор склеивает адаптер+ядро в один `<script>`.
- `inject.py` — внедрить/убрать меню. Принимает папку игры или `index.html`; ищет веб-часть
  в корне, `www/`, `package.nw/`, `package.nw/www/`. Основной способ — **штатный плагин**:
  `js/plugins/TM_Menu.js` (ASCII, значки + адаптер + ядро) и строка `TM_Menu` последней в
  `js/plugins.js` (оригинал — `plugins.js.tm_bak`). `index.html` не трогается; старый
  `<script>`-блок, если был, убирается. Игра в `package.nw`-архиве: архив переименовывается
  в `package.nw.tm_bak` и распаковывается в папку `package.nw` (NW.js понимает оба вида);
  при снятии меню папка остаётся — в ней уже могут быть сейвы. Нет `plugins.js` (демо,
  нестандартные сборки) — запасной `<script>` в `index.html`. Ресурсы, вшитые в `.exe`
  (Enigma Virtual Box), нужно сначала распаковать.
- `scan.py` — статический скан `data/*.json`: имена переменных/переключателей и предметов
  (см. ниже). Аналог `curate_dump` для Ren'Py, но без эвристик — имена лежат готовыми.
- `demo.html` — заглушка рантайма RPG Maker: открой в браузере и жми Shift+T.

## Как попробовать
Открой `demo.html` в браузере → **Shift+T**.

## На реальной игре
```
python inject.py path/to/game_folder            # внедрить/обновить
python inject.py path/to/game_folder --remove    # убрать
```

## Скан имён (data/*.json)
```
python scan.py path/to/game_folder      # или .../data, или .../www/data
```
Печатает кандидатов-подсказки: `$gameVariables.value(N)` / `$gameSwitches.value(N)`
с человекочитаемыми именами из `System.json`, id+имена предметов/оружия/брони из
`Items/Weapons/Armors.json` (для `$gameParty.gainItem`) и валюту (`$gameParty.gainGold`).
Индекс 0 и безымянные слоты отсеиваются.

## Отличие от Ren'Py
Значения (`$gameVariables`, `$gameParty`) правятся в рантайме, поэтому extract/generate
не нужны. Но **имена** переменных и предметов лежат в `data/*.json` — их достаёт `scan`
(шаги движка: `scan`, `deploy`, `uninstall`; см. `tmkit/engines.py`).
