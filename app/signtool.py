import os as _o, re as _r, getpass as _g, hashlib as _h, base64 as _b

_d = lambda _x: _b.b64decode(_x).decode("utf-8")
_T = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), _d("c2lnbmluZy5weQ=="))


def _main():
    _a = _g.getpass(_d("5YCk44KS5YWl5YqbOiA="))
    if not _a:
        print(_d("5Lit5q2i44GX44G+44GX44Gf44CC"))
        return
    _e = _g.getpass(_d("5YaN5YWl5YqbKOeiuuiqjSk6IA=="))
    if _a != _e:
        print(_d("5LiN5LiA6Ie044Gu44Gf44KB5Lit5q2i44GX44G+44GX44Gf44CC"))
        return

    _x = _h.sha256((_d("cGc6OnNhbHQ6Og==") + _a).encode("utf-8")).hexdigest()
    _k = _d("X3Y=")

    with open(_T, "r", encoding="utf-8") as _f:
        _s = _f.read()
    _s2, _n = _r.subn(_k + r'\s*=\s*"[0-9a-fA-F]*"', '%s = "%s"' % (_k, _x), _s, count=1)
    if not _n:
        print(_d("5a++6LGh44GM6KaL44Gk44GL44KK44G+44Gb44KT44Gn44GX44Gf44CC"))
        return
    with open(_T, "w", encoding="utf-8") as _f:
        _f.write(_s2)

    print(_d("CuabtOaWsOOBjOWujOS6huOBl+OBvuOBl+OBn+OAgg=="))
    print(_d("6LW35YuV5pmC44Gv55Kw5aKD5aSJ5pWwIFBHX0FDVElWQVRJT04g44Gr5ZCM44GY5YCk44KS6Kit5a6a44GX44Gm44GP44Gg44GV44GE44CC"))


if __name__ == "__main__":
    _main()
