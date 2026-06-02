import os as _o, sys as _s, hashlib as _h, base64 as _b, hmac as _m


def _d(_x):
    return _b.b64decode(_x).decode("utf-8")



_c = (
    "cGc6OnNhbHQ6Og==",          # 0
    "UEdfQUNUSVZBVElPTg==",      # 1
    "Ty1UWUFONjQ=",              # 2
    "MjAyNg==",                  # 3
    "UG9zdHVyZS1HdWFyZC1BSQ==",  # 4
    "CltQb3N0dXJlLUd1YXJkLUFJXSDnkrDlooPjga7jgrvjg4Pjg4jjgqLjg4Pjg5fjgYzlrozkuobjgZfjgabjgYTjgb7jgZvjgpPjgIIKICDotbfli5Xjg4jjg7zjgq/jg7MgKFBHX0FDVElWQVRJT04pIOOBjOacquioreWumuOAgeOBvuOBn+OBr+S4jeato+OBp+OBmeOAggogIOato+OBl+OBhOODiOODvOOCr+ODs+OCkueSsOWig+WkieaVsOOBq+ioreWumuOBl+OBpuOBi+OCieWGjeWun+ihjOOBl+OBpuOBj+OBoOOBleOBhOOAggogIOOCu+ODg+ODiOOCouODg+ODl+aJi+mghuOBr+acrOOCouODl+ODquOBruS9nOiAheOBq+OBlOeiuuiqjeOBj+OBoOOBleOBhOOAggoK",  # 5
    "cGc6OnNlY3JldDo6",          # 6
)

_v = "d0f2669dec81d6826249bf12c96709d2cdde6e0d56c2efb21a2f7ce4a894a52f"


def _g(_r):
    return _h.sha256((_d(_c[0]) + _r).encode("utf-8")).hexdigest()


def _q():
    _r = _o.environ.get(_d(_c[1]), "")
    return bool(_r) and _m.compare_digest(_g(_r), _v)


def _p():
    _l = "=" * 50
    print(_l)
    print("  " + _d(_c[4]))
    print("  Created by " + _d(_c[2]) + "   (c) " + _d(_c[3]))
    print(_l)


def verify_environment():
    if not _q():
        _s.stderr.write(_d(_c[5]))
        _s.exit(1)
    _p()

def secret_key():
    _r = _o.environ.get(_d(_c[1]), "")
    return _h.sha256((_d(_c[6]) + _r).encode("utf-8")).hexdigest()


token_digest = _g

verify_environment()
