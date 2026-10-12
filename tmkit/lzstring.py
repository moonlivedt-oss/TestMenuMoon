"""LZString (compressToBase64 / decompressFromBase64) — формат сохранений RPG Maker MV (.rpgsave).

Порт lz-string 1.4 (pieroxy, MIT): тот же алгоритм LZW со словарём и выводом по 6 бит
в алфавит Base64. Работает со строками Python (символы UTF-16 кодов < 0x10000 — как в JS;
суррогатные пары JSON игры приходят уже как отдельные коды через json.dumps(ensure_ascii)).
"""

_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_REV = {c: i for i, c in enumerate(_KEY)}


def _compress(uncompressed, bits, char_of):
    if uncompressed is None:
        return ""
    dictionary = {}
    to_create = set()
    w = ""
    enlarge_in = 2
    dict_size = 3
    num_bits = 2
    out = []
    val = 0
    pos = 0

    def write(value, nbits):
        nonlocal val, pos
        for _ in range(nbits):
            val = (val << 1) | (value & 1)
            if pos == bits - 1:
                pos = 0
                out.append(char_of(val))
                val = 0
            else:
                pos += 1
            value >>= 1

    def write_w():
        nonlocal enlarge_in, num_bits
        if w in to_create:
            code = ord(w[0])
            if code < 256:
                write(0, num_bits)
                write(code, 8)
            else:
                write(1, num_bits)
                write(code, 16)
            enlarge_in -= 1
            if enlarge_in == 0:
                enlarge_in = 2**num_bits
                num_bits += 1
            to_create.discard(w)
        else:
            write(dictionary[w], num_bits)
        enlarge_in -= 1
        if enlarge_in == 0:
            enlarge_in = 2**num_bits
            num_bits += 1

    for c in uncompressed:
        if c not in dictionary:
            dictionary[c] = dict_size
            dict_size += 1
            to_create.add(c)
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            write_w()
            dictionary[wc] = dict_size
            dict_size += 1
            w = c
    if w != "":
        write_w()
    write(2, num_bits)  # конец потока
    while True:
        val <<= 1
        if pos == bits - 1:
            out.append(char_of(val))
            break
        pos += 1
    return "".join(out)


def _decompress(length, reset_value, get_next):
    dictionary = {0: 0, 1: 1, 2: 2}
    enlarge_in = 4
    dict_size = 4
    num_bits = 3
    data_val = get_next(0)
    data_pos = reset_value
    data_index = 1
    result = []

    def read(nbits):
        nonlocal data_val, data_pos, data_index
        bits = 0
        power = 1
        maxpower = 2**nbits
        while power != maxpower:
            resb = data_val & data_pos
            data_pos >>= 1
            if data_pos == 0:
                data_pos = reset_value
                data_val = get_next(data_index)
                data_index += 1
            if resb > 0:
                bits |= power
            power <<= 1
        return bits

    nxt = read(2)
    if nxt == 0:
        c = chr(read(8))
    elif nxt == 1:
        c = chr(read(16))
    else:
        return ""
    dictionary[3] = c
    w = c
    result.append(c)
    while True:
        if data_index > length:
            return ""
        c = read(num_bits)
        if c == 0:
            dictionary[dict_size] = chr(read(8))
            dict_size += 1
            c = dict_size - 1
            enlarge_in -= 1
        elif c == 1:
            dictionary[dict_size] = chr(read(16))
            dict_size += 1
            c = dict_size - 1
            enlarge_in -= 1
        elif c == 2:
            return "".join(result)
        if enlarge_in == 0:
            enlarge_in = 2**num_bits
            num_bits += 1
        if c in dictionary:
            entry = dictionary[c]
        elif c == dict_size:
            entry = w + w[0]
        else:
            return None
        result.append(entry)
        dictionary[dict_size] = w + entry[0]
        dict_size += 1
        enlarge_in -= 1
        w = entry
        if enlarge_in == 0:
            enlarge_in = 2**num_bits
            num_bits += 1


def _units(s):
    # строка JS — коды UTF-16: символ вне BMP идёт двумя суррогатами
    if all(ord(ch) < 0x10000 for ch in s):
        return s
    b = s.encode("utf-16-le", "surrogatepass")
    return "".join(chr(b[i] | (b[i + 1] << 8)) for i in range(0, len(b), 2))


def _join(s):
    try:
        return s.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    except UnicodeDecodeError:
        return s  # одиночный суррогат — оставляем как есть


def compress_to_base64(s):
    res = _compress(_units(s), 6, lambda a: _KEY[a])
    return res + "=" * ((4 - len(res) % 4) % 4)


def decompress_from_base64(s):
    s = s.strip()
    if not s:
        return ""
    out = _decompress(len(s), 32, lambda i: _REV[s[i]] if i < len(s) else 0)
    return _join(out) if out else out
