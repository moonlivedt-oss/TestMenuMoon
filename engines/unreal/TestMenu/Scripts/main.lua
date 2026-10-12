--[[
  TestMenuMoon для игр на Unreal Engine 4/5 (мод UE4SS).

  Меню здесь — горячие клавиши (у Lua-модов UE4SS нет своего окна в игре). Ответы пишутся
  в окно UE4SS (оно открывается рядом с игрой) и, если игра это не вырезала, на экран.
  Значения игры смотреть и править — вкладка Live View в том же окне UE4SS.

  Ctrl+Shift+H — справка и состояние, статы игрока
  Ctrl+Shift+1…5 — скорость ×0.25, ×0.5, ×1, ×2, ×5;  Ctrl+Shift+0 — пауза / продолжить
  Ctrl+Shift+G — бессмертие;  Ctrl+Shift+F — полёт;  Ctrl+Shift+N — сквозь стены
  Ctrl+Shift+P — запомнить место;  Ctrl+Shift+O — к последнему месту;  Ctrl+Shift+I — по кругу
  Ctrl+Shift+S — сохранить профиль (темп и режимы ставятся сами при запуске);  Ctrl+Shift+D — удалить
--]]
local UEHelpers = require("UEHelpers")

local MOD_DIR = (debug.getinfo(1, "S").source:gsub("^@", ""):gsub("[\\/]Scripts[\\/]main%.lua$", ""))
local PROFILE = MOD_DIR .. "\\profile.txt"
local MODS = { ModifierKey.CONTROL, ModifierKey.SHIFT }

local state = { speed = 1.0, paused = false, god = false, fly = false, ghost = false }
local places, placeIdx = {}, 0

local function say(msg)
    print("[TestMenu] " .. msg .. "\n")
    pcall(function()
        local pc = UEHelpers.GetPlayerController()
        UEHelpers.GetKismetSystemLibrary():PrintString(pc, "TestMenu: " .. msg, true, false,
            { R = 0.22, G = 0.88, B = 0.78, A = 1.0 }, 3.0, UEHelpers.FindOrAddFName("None"))
    end)
end

local function pc()
    local ok, c = pcall(UEHelpers.GetPlayerController)
    if ok and c and c:IsValid() then return c end
    return nil
end

local function pawn()
    local c = pc()
    if c and c.Pawn and c.Pawn:IsValid() then return c.Pawn end
    return nil
end

local function cheat(name)
    local c = pc()
    if not c then return false end
    local cm = c.CheatManager
    if not cm or not cm:IsValid() then
        say("нет CheatManager (мод CheatManagerEnablerMod включается после загрузки уровня)")
        return false
    end
    cm[name](cm)
    return true
end

-- ---------------------------------------------------------------- скорость
local function applySpeed()
    local k = state.paused and 0.0001 or state.speed
    local ok, err = pcall(function()
        UEHelpers.GetGameplayStatics():SetGlobalTimeDilation(UEHelpers.GetWorldContextObject(), k)
    end)
    if not ok then say("скорость не меняется: " .. tostring(err)) end
end

local function setSpeed(k)
    state.speed, state.paused = k, false
    ExecuteInGameThread(function() applySpeed(); say("скорость ×" .. k) end)
end

-- ---------------------------------------------------------------- режимы
local function setGod(on)
    local p = pawn()
    if not p then say("игрок не найден") return end
    p.bCanBeDamaged = not on
    state.god = on
    say(on and "бессмертие ВКЛ" or "бессмертие выкл")
end

local function setMove(kind, on)
    -- полёт и сквозь стены — команды CheatManager; выключение обоих — Walk
    if on then
        if cheat(kind == "fly" and "Fly" or "Ghost") then state[kind] = true end
    else
        if cheat("Walk") then state.fly, state.ghost = false, false end
    end
    say((kind == "fly" and "полёт " or "сквозь стены ") .. (state[kind] and "ВКЛ" or "выкл"))
end

-- ---------------------------------------------------------------- точки
local function vec(v) return { X = v.X, Y = v.Y, Z = v.Z } end
local function fmt(v) return string.format("(%.0f, %.0f, %.0f)", v.X, v.Y, v.Z) end

local function remember()
    local p = pawn()
    if not p then say("игрок не найден") return end
    local v = vec(p:K2_GetActorLocation())
    table.insert(places, v)
    placeIdx = #places
    say("место " .. #places .. " запомнено " .. fmt(v))
end

local function goTo(i)
    local p, v = pawn(), places[i]
    if not p or not v then say(#places == 0 and "мест нет: Ctrl+Shift+P — запомнить" or "игрок не найден") return end
    p:K2_SetActorLocation(v, false, {}, true)
    placeIdx = i
    say("телепорт к месту " .. i .. " " .. fmt(v))
end

-- ---------------------------------------------------------------- справка и статы
local STAT = { "health", "hp", "stamina", "mana", "energy", "money", "gold", "coins", "ammo", "level", "xp",
    "exp", "experience", "score", "lives", "armor", "shield", "hunger", "thirst", "oxygen", "speed", "damage" }

local function isStat(name)
    local n = name:lower()
    for _, w in ipairs(STAT) do if n:find(w, 1, true) then return true end end
    return false
end

local function dumpStats(obj, title)
    if not obj or not obj:IsValid() then return end
    local lines = {}
    pcall(function()
        obj:GetClass():ForEachProperty(function(prop)
            local name = prop:GetFName():ToString()
            if isStat(name) then
                local ok, v = pcall(function() return obj[name] end)
                if ok and (type(v) == "number" or type(v) == "boolean") then
                    table.insert(lines, "  " .. name .. " = " .. tostring(v))
                end
            end
        end)
    end)
    if #lines > 0 then print("[TestMenu] " .. title .. ":\n" .. table.concat(lines, "\n") .. "\n") end
end

local function help()
    print("[TestMenu] ---------------------------------------------\n")
    print("[TestMenu] скорость ×" .. state.speed .. (state.paused and " (пауза)" or "") ..
        " | бессмертие " .. (state.god and "ВКЛ" or "выкл") .. " | полёт " .. (state.fly and "ВКЛ" or "выкл") ..
        " | сквозь стены " .. (state.ghost and "ВКЛ" or "выкл") .. " | мест: " .. #places .. "\n")
    print("[TestMenu] Ctrl+Shift: 1-5 скорость, 0 пауза, G бессмертие, F полёт, N сквозь стены,\n")
    print("[TestMenu]   P запомнить место, O к последнему, I по кругу, S сохранить профиль, D удалить профиль\n")
    print("[TestMenu] значения игры — вкладка Live View в этом окне\n")
    local p = pawn()
    dumpStats(p, "статы игрока")
    local c = pc()
    if c then dumpStats(c.PlayerState, "PlayerState") end
    say("справка — в окне UE4SS")
end

-- ---------------------------------------------------------------- профиль
local function saveProfile(on)
    if not on then os.remove(PROFILE) say("профиль удалён") return end
    local f = io.open(PROFILE, "w")
    if not f then say("не записать " .. PROFILE) return end
    f:write(string.format("speed=%s\ngod=%s\nfly=%s\nghost=%s\n", state.speed, tostring(state.god),
        tostring(state.fly), tostring(state.ghost)))
    f:close()
    say("профиль сохранён: ставится сам при запуске")
end

local profile = nil
do
    local f = io.open(PROFILE, "r")
    if f then
        profile = {}
        for line in f:lines() do
            local k, v = line:match("^(%w+)=(.+)$")
            if k then profile[k] = v end
        end
        f:close()
    end
end

-- профиль — когда у игрока появилась пешка (загрузка уровня, возрождение)
RegisterHook("/Script/Engine.PlayerController:ClientRestart", function()
    if not profile then return end
    ExecuteWithDelay(1500, function()
        ExecuteInGameThread(function()
            state.speed = tonumber(profile.speed) or 1.0
            if state.speed ~= 1.0 then applySpeed() end
            if profile.god == "true" then setGod(true) end
            if profile.fly == "true" then setMove("fly", true) elseif profile.ghost == "true" then setMove("ghost", true) end
            say("профиль игры применён")
        end)
    end)
end)

-- ---------------------------------------------------------------- клавиши
local speeds = { [Key.ONE] = 0.25, [Key.TWO] = 0.5, [Key.THREE] = 1.0, [Key.FOUR] = 2.0, [Key.FIVE] = 5.0 }
for key, k in pairs(speeds) do
    RegisterKeyBind(key, MODS, function() setSpeed(k) end)
end
RegisterKeyBind(Key.ZERO, MODS, function()
    state.paused = not state.paused
    ExecuteInGameThread(function() applySpeed(); say(state.paused and "пауза" or "продолжаем") end)
end)
RegisterKeyBind(Key.H, MODS, function() ExecuteInGameThread(help) end)
RegisterKeyBind(Key.G, MODS, function() ExecuteInGameThread(function() setGod(not state.god) end) end)
RegisterKeyBind(Key.F, MODS, function() ExecuteInGameThread(function() setMove("fly", not state.fly) end) end)
RegisterKeyBind(Key.N, MODS, function() ExecuteInGameThread(function() setMove("ghost", not state.ghost) end) end)
RegisterKeyBind(Key.P, MODS, function() ExecuteInGameThread(remember) end)
RegisterKeyBind(Key.O, MODS, function() ExecuteInGameThread(function() goTo(#places) end) end)
RegisterKeyBind(Key.I, MODS, function()
    ExecuteInGameThread(function()
        if #places > 0 then goTo(placeIdx % #places + 1) else say("мест нет: Ctrl+Shift+P — запомнить") end
    end)
end)
RegisterKeyBind(Key.S, MODS, function() saveProfile(true) end)
RegisterKeyBind(Key.D, MODS, function() saveProfile(false) end)

print("[TestMenu] загружен: Ctrl+Shift+H — справка\n")
