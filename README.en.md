# Test Menu Moon

[![tests](https://github.com/moonlivedt-oss/TestMenuMoon/actions/workflows/tests.yml/badge.svg)](https://github.com/moonlivedt-oss/TestMenuMoon/actions/workflows/tests.yml)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

[Русский](README.md) | **English**

![Test Menu Moon](docs/cover.webp)

A test menu and cheats for games of any genre. Installed into a game with one click, opened in
the game with **Shift+T** (spare key **F9**): edit variables, freeze them, search values like
ArtMoney, a change log, game speed, frame stepping and an FPS counter, teleport, choice hints,
auto-play for testers. The menu is in Russian or English. Plus a PyQt6 studio: a game library
(a whole folder of games at once), a remote to control a game from a second monitor, and a save
editor.

| Engine | What gets installed | In-game menu |
|---|---|---|
| **Ren'Py** 6.99 – 8.x (py2 and py3) | `.rpy` files in `game/` | the fullest: 7 tabs, choice hints, auto-play, change log |
| **RPG Maker MV / MZ** | plugin `js/plugins/TM_Menu.js` | values, party, modes, maps, "who changes this switch" |
| **HTML5** (Phaser, Construct 2/3, GDevelop, custom engines) | a `<script>` block in `index.html` | values, "where it changes", speed, frame step, scanner, saves |
| **Twine / SugarCube** | a `<script>` block in the story | story variables, scanner, saves |
| **Godot 4 and 3** | an autoload via `override.cfg` | variables, Dialogic (4), speed, frame step, fly, noclip |
| **Unity IL2CPP** | BepInEx 6 + UnityExplorer + plugin | object fields, freeze, speed, frame step, teleport |
| **Unity Mono** (x64 and x86) | BepInEx 5 + UnityExplorer + plugin built for the game | same |
| **Unreal Engine 4 / 5** | UE4SS + Lua mod | keys: speed, god mode, fly, teleport; Live View |
| **GameMaker 2.3+** | a GML menu object inside `data.win` (UndertaleModTool) | global variables, freeze, rooms, speed |

Everything put into a game is removed with one click (`--remove`); modified game files
(`index.html`, `plugins.js`, `data.win`, `package.nw`) keep their originals next to them (`.tm_bak`).

> For single-player games. The installer refuses online games with anti-cheat (EasyAntiCheat,
> BattlEye and the like): that gets accounts banned.

## Screenshots

Test visual novel "Moonlight Academy" (background and character are from The Question demo
shipped with the Ren'Py SDK). The screenshots show the Russian interface.

| Choice hints (hidden options visible too) | Variables with readable names |
|---|---|
| ![Choice hints](docs/screenshots/renpy_choice_hints.webp) | ![Variables](docs/screenshots/renpy_variables.webp) |
| **Story**: hints, choice history, on-screen buttons | **Test**: auto-play and routes |
| ![Story](docs/screenshots/renpy_story.webp) | ![Test](docs/screenshots/renpy_test.webp) |
| **Rewind**: rollback, quick slots, skip | **Settings** |
| ![Rewind](docs/screenshots/renpy_rewind.webp) | ![Settings](docs/screenshots/renpy_settings.webp) |

RPG Maker ("Star Harbor") and an HTML5 game ("Pixel Bakery"):

| RPG Maker: values and "where" | RPG Maker: the "Game" tab |
|---|---|
| ![RPG Maker values](docs/screenshots/rpgmaker_values.webp) | ![RPG Maker game](docs/screenshots/rpgmaker_game.webp) |
| **HTML5**: game variables found at runtime | **HTML5**: speed, profile |
| ![HTML5 values](docs/screenshots/web_values.webp) | ![HTML5 game](docs/screenshots/web_game.webp) |

The studio and the save editor:

![Studio](docs/screenshots/studio.webp)
![Save editor](docs/screenshots/save_editor.webp)

## Quick start

```
pip install -r requirements.txt     # PyQt6, only for the studio
python studio.py                    # or Запуск.bat
```

Without Python: `TestMenuStudio.exe` in the project root (build it with `python tools/build_exe.py`,
PyInstaller is required). Python and PyQt6 are inside the .exe; project files (`engines/`,
`assets/`, `tools/`, the manifest) are taken from next to it.

In the studio: **"Quick install into any game…"** → pick the game folder → start the game →
**Shift+T**. The engine is detected automatically. With many games, use **"Game library…"**:
pick a folder and the studio finds every game, shows its engine and menu state (none / outdated /
current) and installs, updates or removes the menu for the checked games at once. On start the
studio checks that folder and the manifest games by itself and shows an "Update" bar if a menu is
outdated somewhere. The same from the console:

```
python tm.py quick "C:/Games/SomeGame"            # game folder, its game/ or the .exe
python tm.py quick --remove "C:/Games/SomeGame"
python tm.py library "C:/Games"                   # every game in a folder: engine and state
python tm.py library "C:/Games" --install         # install where missing or outdated
```

On first start the studio shows a tour (repeat it with the "Тур" button). In the game, the
question mark button in the menu header (or F1) opens "How to use the menu" with all keys.

Mod loaders for Unity, Unreal and GameMaker are downloaded once: `python tools/fetch_unity_tools.py`
(BepInEx 5/6, UnityExplorer, UE4SS, UndertaleModTool CLI, AssetRipper, Cpp2IL into `tools/unity/`,
not tracked by git).

## Remote: the game on a second monitor

The **"Пульт…"** (Remote) button in the studio and **"Studio remote"** in the game menu (web menus:
the "Game" tab, Ren'Py: "Settings"): game values show up in the studio window and are changed
there (edit, freeze, speed, frame step) while the menu doesn't cover the game. The link is HTTP on
`127.0.0.1:47820`, this computer only. Works for HTML5, RPG Maker, Twine and Ren'Py.

## Ren'Py: what the menu does

- **Rewind**: history rollback (×1/×10, mouse wheel), 3 quick slots, instant skip (unread text
  too), auto-forward, text speed; before any jump the menu saves a "Before jump" slot by itself;
  a log of recent lines with rollback to any of them.
- **Variables**: edit stats (−/+ with a step, input, `+50`, `*2`, `=-5`), toggles, freezing
  (`=`, `≥`, `≤`), favorites, a HUD over the game, "changed since last time" marks, undo (Ctrl+Z).
  Sources: **data** (a list from the manifest) and **auto**: the menu finds game variables, class
  objects, dicts and lists by itself. Readable names: `alice_love` → "Alice | Love" (character
  name + word dictionary + labels from dialogue); the grey line shows where the value changes and
  which thresholds the script checks. **Change log**: what the game, the menu, a freeze or the
  remote changed, when and at which label (the full log goes into the tester report).
- **Give / Code**: actions from the manifest (items, money) and your own Python code.
- **Search**: like ArtMoney, but by variable names: snapshot → changes → narrowing.
- **Story**: choice hints (**Shift+H**: what each option changes, options hidden by a condition
  with a "choose" button, the option's code), choice history with real changes, game screen
  buttons, jump to a label and line search, scene replay, "Where am I", gallery and `persistent`.
- **Test**: auto-play (new options / random / first, a "game waits for the player" watchdog),
  routes (record choices and replay them after a game update), line and scene coverage, unseen
  scenes and "how to get there", bug notes (**Shift+B**: text + place + screenshot).
- **Settings**: menu language (Русский / English), studio remote, appearance, HUD, menu key,
  tester report, "Remove menu traces".
- **Game profile**: "to profile" on freezes makes them apply on every start.
- Line translation via [AutoTranslatorMoon](https://github.com/moonlivedt-oss/AutoTranslatorMoon)
  (`zzz_testmenu_translate.rpy`): text goes to the translator on this PC, the translation appears
  right in the dialogue window.

Works on Ren'Py 6.99 – 8.5 (checked by lint and by running on 6.99.14, 7.3.5, 7.4.11, 7.8.7,
8.0.3, 8.5.3; lint on 8.5.3 and 7.8.7 also runs in CI). The window scales to the game resolution.

English in the Ren'Py menu is switched on in "Settings" and doesn't touch the game's own language:
the translation goes through `config.replace_text` and replaces only strings that match menu
strings exactly.

## Other engines

**RPG Maker MV/MZ.** "Values": gold, variables and switches (with a **"where"** button: which events
on which maps change and check them), items, the party (level, HP/MP/TP, EXP, parameters). "Game":
speed (pause … ×5), modes: through walls, no random battles, party immortality, free skills,
EXP ×10, click to teleport; a map list with jumps; teleport points; profile. "Give": win the
battle, escape, save anywhere, teleport by map ID and coordinates.

**HTML5.** Variables are found at runtime: Construct 2 global variables, Construct 3 global and
instance variables (DOM mode or a `runtime` exposed by a project script; not available in worker
mode), GDevelop game and scene variables, Phaser 3 `registry` and scene `data`, and in other games
page globals and their fields 3 levels deep. The **"where"** button on a value traces writes for
15 seconds: which game functions change the value (with the call stack). Game speed works by
replacing time (`performance.now`, `Date.now`, `requestAnimationFrame`). A packed `package.nw` of
nw.js games is unpacked into a folder (the archive stays as `package.nw.tm_bak`).

**Shared by the web menus** (HTML5, RPG Maker, Twine). "Game": **frame step** while paused
(exactly 1/60 s of game time; for RPG Maker one scene update), **FPS in the corner**, the remote,
the menu language. "Saves" (Сохранения): `localStorage` keys and IndexedDB records (localforage and others);
JSON and LZString-compressed data (RPG Maker MV in a browser, SugarCube) are unfolded into a list
of fields, edited by input or toggle, then "Write edits". The original of a key is kept before the
first write: "Restore original". "Values": a change log (who changed it: the game, the menu, a
freeze, the remote).

**Godot 4.** A GDScript menu is attached as an autoload from `override.cfg` (the game and its
`.pck` are untouched): global objects, Dialogic variables and `.dtl` scenes with conditions,
unlockables, speed (`Engine.time_scale`), frame step and FPS, player teleport, fly (the game stops
moving the hero, the arrow keys do) and noclip, profile. **Godot 3** gets its own simpler GDScript 1
menu: autoload variables, freezing, speed, frame step, FPS, fly, noclip. Neither menu has been run
yet: there is no Godot runtime on the developer's machine.

**Unity.** IL2CPP: BepInEx 6, plugin `engines/unity/plugin` (`dotnet build -c Release`, references
in `tools/unity/refs`). Mono: BepInEx 5, the plugin `engines/unity/mono` is built **at install
time** by the system `csc.exe` right against the game's own libraries, so it fits any Unity version.
Tabs: main (stat fields), all variables, game (speed, frame step, FPS, profile, teleport), search.
32-bit Mono games get the BepInEx 5 x86 loader. F7 opens UnityExplorer.

**Unreal 4/5.** UE4SS + a Lua mod. Lua mods have no in-game window, so the menu is keys; replies and
player stats go to the UE4SS window, which also has Live View with all objects:
Ctrl+Shift+H help; 1…5 speed; 0 pause; G god mode; F fly; N noclip; P / O / I teleport points;
S / D save / delete profile (all with Ctrl+Shift).

**GameMaker 2.3+.** UndertaleModTool CLI adds a GML menu object to `data.win` (placed in the first
room, persistent). Shift+T / F9 opens the menu, Tab switches pages: global variables (arrows,
Enter to input, F to freeze), rooms (Enter to go), game (speed). The menu text is English: the
default GameMaker font has no Cyrillic. Not yet tested on a real game.

## Save editor

The "Сохранения…" (Saves) button in the studio or `python tm.py saves [file]`. A game's saves are
found automatically.

- **Ren'Py** `.save` (py2 and py3): store values: numbers, flags, strings, object fields, dicts,
  lists. The game's classes aren't needed: the pickle is parsed into stubs and written back in the
  same shape. Ren'Py 8.1+ saves are re-signed with this computer's key, so the game doesn't ask
  whether to trust the save.
- **Ren'Py `persistent`** (gallery, endings, unlocks between playthroughs): fields except internal
  `_…` ones. Edited fields get "now" as their change time, so the edit survives when Ren'Py merges
  the copies from `game/saves` and `%APPDATA%/RenPy`. A signed (8.1+) persistent is re-signed; if
  that's impossible, writing is refused, because Ren'Py would throw the whole file away.
- **RPG Maker MV** `.rpgsave` and **MZ** `.rmmzsave`: names of variables, switches, items and
  heroes come from the game's `data/*.json`.
- **Unity**: PlayerPrefs from the registry and JSON saves in `AppData/LocalLow`.
- **Godot**: JSON and ConfigFile in `user://`. Any JSON via "Открыть файл…" (Open file).
- **Snapshot and compare**: "Snapshot" before a scene, "Compare with snapshot" after it shows
  which values the scene changed; "Compare with file…" compares two saves directly. In the
  console: `tm.py saves A --diff B`.

Before the first write a copy `<file>.tm_bak` is kept next to the file.

## Studio

`python studio.py` (PyQt6, dark theme): the game list with install state and engine badge, stat and
action editors, data checks, Ren'Py lint, launching the game, the whole pipeline in one click, stat
candidates with readable names, quick install, the game library, the remote, the save editor. The
studio interface is in Russian.

## Manifest and pipeline (for your own games)

Your games live in `tmkit/games_data.py` (edited by the studio; not tracked by git, the first start
copies the example `tmkit/games_example.py` with test games). Per game: `title`, `root` (the
`game/` folder), `status`, `stats`, `actions`, optional `accent` and `tweak`.

```python
("Money", "money", "0", "")                           # a stat with min / max limits
("Strength", "state.player_stats.physical_level", "1", "4")
("Intimacy", 'state.get_girl("Mira").intimacy')       # through an object method
("— Skills —", "")                                    # a section divider
("Money +100", "money += 100")                        # an action: code in the game store
```

**Tweaks** (the `tweak` field): a file from `tweaks/` with Ren'Py code for a particular game; it is
appended to the data file and installed and removed together with the menu. Example:
`tweaks/example_debug.rpy`.

The pipeline for Ren'Py game N (the studio does the same with buttons):

```
python tm.py collect N    # unpack .rpa + decompile .rpyc (needs unrpyc in ./unrpyc)
python tm.py curate N     # stat and inventory candidates
python tm.py gen N        # the data file from the manifest
python tm.py deploy N     # put the menu into the game
python tm.py verify N     # lint + install check
python tm.py all N        # everything in a row;  list / doctor / validate / uninstall: see --help
```

Work area paths can be overridden with `TM_BUILD`, `TM_ANA_BASE`, `TM_CAND_DIR`.

## Layout

```
tm.py                    CLI: collect / curate / gen / deploy / verify / quick / library / saves …
studio.py                starts the studio (code in tmstudio/)
tmstudio/                the studio: theme, tabs, window, library, remote, tour, save_editor
tmkit/                   logic without GUI: manifest, engine registry, generation, install, analysis,
                         game library, remote bridge; saves/ holds save formats
engines/
  renpy/engine/          the Ren'Py menu by sections (00_setup … 13_lang); the game gets them
                         joined into one file, zzz_testmenu_engine.rpy
  renpy/                 lang_en.json (English; tools/gen_renpy_lang.py builds 13_lang.rpy),
                         zzz_testmenu_translate.rpy (line translation via AutoTranslatorMoon)
  _shared/               tm_tokens.json, the one set of colors and sizes for the menus and the studio
                         (tools/gen_tokens.py builds 00_tokens.rpy, tm_tokens.js, tmstudio/tokens.py);
                         the web menu core (tm_menu_core.js), language (tm_lang.js), icons, the
                         shared <script> block (tm_webinject.py), HTML encodings, module loader (tm_load.py)
  rpgmaker, web, twine   menu adapter (tm_menu.js) + installer (inject.py) + scan.py
  godot                  tm_menu.gd (Godot 4), tm_menu3.gd (Godot 3), installer, .pck reader
  unity, unreal          C# menu (plugin: IL2CPP, mono: Mono) / Lua + installers
  gamemaker              GML menu + UndertaleModTool script + installer
tweaks/                  game tweaks (example: example_debug.rpy)
tools/                   tool downloads, .exe build, Ren'Py lint for CI, generators
tests/                   tests by topic (test_manifest, test_renpy, test_engines, test_saves,
                         test_studio) + helpers.py;  python tests/run.py
docs/                    cover and screenshots for the README
```

## Tests

`python tests/run.py` (or `python tests/run.py saves` for tests with that word in their name):
160+ tests on the standard library only (pytest-compatible): manifest, generation, install and
removal for every engine, save formats (including an LZString check against the reference),
the web core, the Ren'Py engine, translation completeness. The Mono plugin build and Unreal install
tests run when `tools/unity` is downloaded. CI is GitHub Actions on Windows: tests on Python
3.10 – 3.12, `ruff check` and menu lint on real Ren'Py 8.5.3 and 7.8.7 (`tools/ci_renpy_lint.py`).

## Third-party components

Downloaded separately and not part of the repository: [BepInEx](https://github.com/BepInEx/BepInEx),
[UnityExplorer](https://github.com/sinai-dev/UnityExplorer),
[RE-UE4SS](https://github.com/UE4SS-RE/RE-UE4SS),
[UndertaleModTool](https://github.com/UnderminersTeam/UndertaleModTool),
[AssetRipper](https://github.com/AssetRipper/AssetRipper),
[Cpp2IL](https://github.com/SamboyCoding/Cpp2IL), [unrpyc](https://github.com/CensoredUsername/unrpyc).
`tmkit/lzstring.py` is a port of [lz-string](https://github.com/pieroxy/lz-string) (MIT).

## License

[MIT](LICENSE). The screenshots in `docs/screenshots` were taken on test games; their background
and character come from The Question demo (Ren'Py SDK) and are not covered by the project license.
The cover `docs/cover.webp` is from the [image library](https://github.com/moonlivedt-oss/photosMOONprojects).
