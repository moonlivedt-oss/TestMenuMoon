"""Разбор pickle Ren'Py без классов игры: заглушки вместо классов, тот же pickle при записи.

Классы игры и движка в студии не загрузить, поэтому pickle разбирается на заглушки:
каждая запоминает модуль, имя, аргументы и состояние и сериализуется обратно так же.
Разрешены только безопасные встроенные фабрики (_SAFE) — сейв не может выполнить код.
"""

import pickle, sys, types

from tmkit.saves.core import _txt

_STUBS = {}
_SAFE = {
    ("builtins", n)
    for n in (
        "set",
        "frozenset",
        "list",
        "dict",
        "tuple",
        "object",
        "bytes",
        "bytearray",
        "complex",
        "slice",
        "range",
        "int",
        "float",
        "str",
        "bool",
    )
}
_SAFE |= {
    ("copyreg", "_reconstructor"),
    ("copyreg", "__newobj__"),
    ("_codecs", "encode"),
    ("collections", "OrderedDict"),
    ("collections", "defaultdict"),
    ("collections", "deque"),
    ("datetime", "datetime"),
    ("datetime", "date"),
    ("datetime", "time"),
    ("datetime", "timedelta"),
    ("decimal", "Decimal"),
    ("fractions", "Fraction"),
}


def _stub_state(o):
    """Состояние заглушки в той же форме, в какой оно пришло из сейва."""
    dd = o.__dict__
    if "_tm_state" in dd:
        return dd["_tm_state"]
    shape = dd.get("_tm_shape")
    if shape:
        _k, none_dict, dkeys, skeys = shape
        return (None if none_dict else {k: dd[k] for k in dkeys if k in dd}, {k: dd[k] for k in skeys if k in dd})
    d = {k: v for k, v in dd.items() if not _txt(k).startswith("_tm_")}
    return d or None


def _stub(module, name):
    key = (module, name)
    if key in _STUBS:
        return _STUBS[key]
    base = (
        list
        if "List" in name
        else dict
        if "Dict" in name
        else set
        if "Set" in name
        else object
    )

    def __new__(cls, *args, **kw):
        o = base.__new__(cls) if base is not object else object.__new__(cls)
        o.__dict__["_tm_args"] = args
        return o

    def __init__(self, *args, **kw):
        self.__dict__["_tm_call"] = True
        if base is set and args:
            set.update(self, args[0])

    def __setstate__(self, state):
        # запоминаем форму состояния: dict, (dict|None, слоты) или что-то своё — так же и запишем
        if (
            isinstance(state, tuple)
            and len(state) == 2
            and (state[0] is None or isinstance(state[0], dict))
            and isinstance(state[1], dict)
        ):
            self.__dict__["_tm_shape"] = ("slots", state[0] is None,
                                          tuple((state[0] or {}).keys()), tuple(state[1].keys()))
            self.__dict__.update(state[0] or {})
            self.__dict__.update(state[1])
        elif isinstance(state, dict):
            self.__dict__.update(state)
        elif state is not None:
            self.__dict__["_tm_state"] = state

    def __reduce_ex__(self, proto):
        state = _stub_state(self)
        if base is set:
            return (type(self), (list(self),), state)
        li = iter(self) if base is list else None
        di = iter(dict.items(self)) if base is dict else None
        if self.__dict__.get("_tm_call"):
            return (type(self), self.__dict__.get("_tm_args", ()), state, li, di)
        import copyreg

        return (
            copyreg.__newobj__,
            (type(self),) + tuple(self.__dict__.get("_tm_args", ())),
            state,
            li,
            di,
        )

    cls = type(
        name.split(".")[-1],
        (base,),
        {
            "__new__": __new__,
            "__init__": __init__,
            "__setstate__": __setstate__,
            "__reduce_ex__": __reduce_ex__,
            "__module__": module,
            "__qualname__": name,
            "_tm_stub": True,  # метка для _Unpickler._old / _Pickler.save (старые классы py2)
        },
    )
    if base is dict:
        cls.__hash__ = object.__hash__
    if base in (list, set):
        cls.__hash__ = object.__hash__
    _STUBS[key] = cls
    return cls


class _Call(dict):
    """Несостоявшийся вызов из pickle: func(*args) — при записи тот же REDUCE (с элементами,
    если pickle потом наполнял результат как словарь или список)."""

    def __init__(self, func, args):
        super().__init__()
        self.func, self.args, self.items_list = func, args, []

    def __call__(self, *a, **k):
        return None

    def append(self, x):
        self.items_list.append(x)

    def extend(self, xs):
        self.items_list.extend(xs)

    def __setstate__(self, state):
        self.state = state

    __hash__ = object.__hash__

    def __reduce_ex__(self, proto):
        return (self.func, tuple(self.args), getattr(self, "state", None),
                iter(self.items_list) if self.items_list else None,
                iter(dict.items(self)) if len(self) else None)


def _deep(fn, *args):
    """pickle на чистом Python рекурсивен, а журнал Ren'Py глубокий (цепочки узлов):
    выполняем в потоке с большим стеком и высоким пределом рекурсии."""
    import threading

    box = {}

    def run():
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(200000)
        try:
            box["v"] = fn(*args)
        except BaseException as e:
            box["e"] = e
        finally:
            sys.setrecursionlimit(old)

    prev = threading.stack_size(256 * 1024 * 1024 - 4096)
    try:
        t = threading.Thread(target=run)
        t.start()
        t.join()
    finally:
        threading.stack_size(prev)
    if "e" in box:
        raise box["e"]
    return box["v"]


class _Unpickler(pickle._Unpickler):
    """Чистый Python-разборщик: свои find_class и пометка объектов старых классов py2 (OBJ/INST)."""

    dispatch = dict(pickle._Unpickler.dispatch)

    def find_class(self, module, name):
        m = {"__builtin__": "builtins", "copy_reg": "copyreg"}.get(module, module)
        if (m, name) in _SAFE:
            return super().find_class(m, name)
        return _stub(module, name)

    def _old(self, op):
        op(self)
        o = self.stack[-1]
        if getattr(type(o), "_tm_stub", False):
            o.__dict__["_tm_old"] = True

    def _reduce(self):
        # вызов, который в студии не выполнить (метод объекта игры как фабрика defaultdict
        # и т.п.), — запоминаем как есть и при записи повторяем тот же REDUCE
        args = self.stack.pop()
        func = self.stack[-1]
        try:
            self.stack[-1] = func(*args)
        except Exception:
            self.stack[-1] = _Call(func, args)

    dispatch[pickle.REDUCE[0]] = _reduce
    dispatch[pickle.OBJ[0]] = lambda self: self._old(pickle._Unpickler.load_obj)
    dispatch[pickle.INST[0]] = lambda self: self._old(pickle._Unpickler.load_inst)


class _Pickler(pickle._Pickler):
    """Объект старого класса py2 пишется снова через OBJ: у таких классов нет __new__."""

    def save(self, obj, save_persistent_id=True):
        if getattr(type(obj), "_tm_stub", False) and obj.__dict__.get("_tm_old"):
            x = self.memo.get(id(obj))
            if x is not None:
                self.write(self.get(x[0]))
                return
            self.write(pickle.MARK)
            self.save(type(obj))
            self.write(pickle.OBJ)
            self.memoize(obj)
            state = _stub_state(obj) or {}
            self.save(state)
            self.write(pickle.BUILD)
            return
        super().save(obj, save_persistent_id)


def _register_stubs():
    """Модули-заглушки в sys.modules: pickle при записи проверяет, что класс находится по имени."""
    added = []
    for (module, name), cls in _STUBS.items():
        parts = module.split(".")
        for i in range(1, len(parts) + 1):
            mn = ".".join(parts[:i])
            if mn not in sys.modules:
                sys.modules[mn] = types.ModuleType(mn)
                added.append(mn)
        setattr(sys.modules[module], name.split(".")[-1], cls)
    return added
