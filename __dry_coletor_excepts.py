# _dry_coletor_excepts.py — forca os 7 except blindados do Coletor_MT5_v2_2
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

captured = []


class _Capture(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            captured.append(record.getMessage())


class _FakeMT5:
    TIMEFRAME_D1 = 1
    BOOK_TYPE_BUY = 1
    BOOK_TYPE_SELL = 2

    overrides = {}

    @classmethod
    def reset(cls):
        cls.overrides = {}

    @classmethod
    def _call(cls, name, *args, **kwargs):
        if name not in cls.overrides:
            return None
        v = cls.overrides[name]
        if isinstance(v, Exception):
            raise v
        if callable(v) and not isinstance(v, type):
            return v(*args, **kwargs)
        return v

    @classmethod
    def initialize(cls):
        return True

    @classmethod
    def shutdown(cls):
        return True

    @classmethod
    def last_error(cls):
        return (0, "ok")

    @classmethod
    def terminal_info(cls):
        return SimpleNamespace(connected=True, company="FakeBroker")

    @classmethod
    def account_info(cls):
        return SimpleNamespace(login=12345)

    @classmethod
    def version(cls):
        return (500, 0, 0)

    @classmethod
    def symbol_info(cls, name):
        return cls._call("symbol_info", name)

    @classmethod
    def symbol_info_tick(cls, name):
        return cls._call("symbol_info_tick", name)

    @classmethod
    def symbols_get(cls, group=None):
        return cls._call("symbols_get", group)

    @classmethod
    def symbol_select(cls, name, enable=True):
        return True

    @classmethod
    def copy_rates_from_pos(cls, *a):
        return cls._call("copy_rates_from_pos", *a)

    @classmethod
    def market_book_add(cls, name):
        return cls._call("market_book_add", name)

    @classmethod
    def market_book_get(cls, name):
        return cls._call("market_book_get", name)

    @classmethod
    def market_book_release(cls, name):
        return cls._call("market_book_release", name)


sys.modules["MetaTrader5"] = _FakeMT5

import Coletor_MT5_v2_2 as col

col.logger.addHandler(_Capture())
col.logger.setLevel(logging.WARNING)


class _RateObj:
    def __init__(self, values, dtype_names, fail_str=False):
        self._values = values
        self.dtype = SimpleNamespace(names=dtype_names)
        self._fail_str = fail_str
        self._idx = {n: i for i, n in enumerate(dtype_names)}

    def __getitem__(self, k):
        if isinstance(k, str):
            if self._fail_str:
                raise KeyError(f"simulado str: {k}")
            return self._values[self._idx[k]]
        return self._values[k]

    def __len__(self):
        return len(self._values)


# ===== T1: _monta_info expiration_time invalido =====
print("== T1: _monta_info expiration_time invalido ==")
_FakeMT5.reset()


class _Sym:
    def __init__(self, name, exp):
        self.name = name
        self.expiration_time = exp
        self.session_volume = 100


_sym_bad = _Sym("WIND26", "NOPE")
_FakeMT5.overrides["symbols_get"] = lambda group=None: [_sym_bad]
_FakeMT5.overrides["symbol_info_tick"] = SimpleNamespace(
    volume=10, bid=1.0, ask=2.0, last=1.5
)
contratos = col.obter_contratos("WIN")
assert len(contratos) == 1, contratos
assert contratos[0]["expiracao"] is None
print(f"   OK contratos={len(contratos)} exp=None")


# ===== T2: obter_contratos symbols_get(group) falha =====
print("== T2: obter_contratos symbols_get(group) falha ==")
_FakeMT5.reset()


def _sym_get(group=None):
    if group is not None:
        raise ValueError("boom group")
    return None


_FakeMT5.overrides["symbols_get"] = _sym_get
_FakeMT5.overrides["symbol_info"] = None
contratos = col.obter_contratos("XYZ")
assert contratos == [], contratos
print(f"   OK contratos={len(contratos)} (sem crash)")


# ===== T3: obter_preco_teorico price_theoretical invalido =====
print("== T3: obter_preco_teorico price_theoretical invalido ==")
_FakeMT5.reset()
_FakeMT5.overrides["symbol_info"] = SimpleNamespace(price_theoretical="NOPE")
val = col.obter_preco_teorico("WINZ26")
assert val is None
print(f"   OK preco_teorico={val}")


def _fake_sel(prefixo, criterio="expiracao"):
    principal = {
        "nome": "WINZ26",
        "expiracao": col.datetime(2030, 1, 1),
        "volume": 100,
        "session_volume": 100,
        "bid": 1.0,
        "ask": 2.0,
        "last": 1.5,
    }
    return principal, [principal]


_orig_sel = col.selecionar_contrato


# ===== T4: coletar_ativo OHLC inner =====
print("== T4: coletar_ativo OHLC inner ==")
_FakeMT5.reset()
_FakeMT5.overrides["symbol_info"] = SimpleNamespace(
    session_close=0, price_theoretical=None
)
_FakeMT5.overrides["symbol_info_tick"] = SimpleNamespace(
    volume=10.0, bid=1.0, ask=2.0, last=1.5
)
_bad = _RateObj(
    [0, 100.0, 110.0, 90.0, 105.0, 50.0],
    ("time", "open", "high", "low", "close", "tick_volume"),
    fail_str=True,
)
_FakeMT5.overrides["copy_rates_from_pos"] = [_bad]
_FakeMT5.overrides["market_book_add"] = False

col.selecionar_contrato = _fake_sel
try:
    dados = col.coletar_ativo(
        "WIN", {"prefixo": "WIN", "descricao": "teste", "criterio": "expiracao"}
    )
    assert dados["open"] == 100.0
    assert dados["high"] == 110.0
    assert dados["close"] == 105.0
    print(f"   OK open={dados['open']} high={dados['high']} close={dados['close']}")
finally:
    col.selecionar_contrato = _orig_sel


# ===== T5: coletar_ativo prev_close inner =====
print("== T5: coletar_ativo prev_close inner ==")
_FakeMT5.reset()
_FakeMT5.overrides["symbol_info"] = SimpleNamespace(
    session_close=0, price_theoretical=None
)
_FakeMT5.overrides["symbol_info_tick"] = SimpleNamespace(
    volume=10.0, bid=1.0, ask=2.0, last=1.5
)
_good = _RateObj(
    [0, 100.0, 110.0, 90.0, 105.0, 50.0],
    ("time", "open", "high", "low", "close", "tick_volume"),
    fail_str=False,
)
_bad_prev = _RateObj(
    [0, 1.0, 2.0, 3.0, 104.0, 5.0],
    ("time", "open", "high", "low", "close", "tick_volume"),
    fail_str=True,
)
_FakeMT5.overrides["copy_rates_from_pos"] = [_bad_prev, _good]
_FakeMT5.overrides["market_book_add"] = False

col.selecionar_contrato = _fake_sel
try:
    dados = col.coletar_ativo(
        "WIN", {"prefixo": "WIN", "descricao": "teste", "criterio": "expiracao"}
    )
    assert dados["prev_close"] == 104.0, dados["prev_close"]
    print(f"   OK prev_close={dados['prev_close']}")
finally:
    col.selecionar_contrato = _orig_sel


# ===== T6: _rotacionar_historico getmtime OSError =====
print("== T6: _rotacionar_historico getmtime OSError ==")
tmp_hist = Path(tempfile.mkdtemp())
orig_hist = col.HISTORICO_DIR
orig_arch = col.HISTORICO_ARQUIVO_DIR
orig_getmtime = os.path.getmtime

col.HISTORICO_DIR = str(tmp_hist)
col.HISTORICO_ARQUIVO_DIR = str(tmp_hist / "arquivo")
(tmp_hist / "MT5_v2_2_20260101_120000_000000.json").write_text("{}")


def _broken_getmtime(p):
    raise OSError("simulado getmtime")


os.path.getmtime = _broken_getmtime
try:
    col._rotacionar_historico()
    print("   OK rotacao nao crashou")
finally:
    os.path.getmtime = orig_getmtime
    col.HISTORICO_DIR = orig_hist
    col.HISTORICO_ARQUIVO_DIR = orig_arch
    shutil.rmtree(tmp_hist, ignore_errors=True)


# ===== T7: obter_book outer =====
print("== T7: obter_book outer ==")
_FakeMT5.reset()
_FakeMT5.overrides["market_book_add"] = True
_FakeMT5.overrides["market_book_get"] = ValueError("boom book")
_FakeMT5.overrides["market_book_release"] = True

book = col.obter_book("WINZ26")
assert book["disponivel"] is False
print(f"   OK disponivel={book['disponivel']}")


# ===== resumo =====
print(f"\n== WARNINGs capturados: {len(captured)} ==")
for i, msg in enumerate(captured, 1):
    print(f"   {i}. {msg}")

esperadas = [
    "Falha convertendo expiration_time",
    "symbols_get(group=",
    "Falha lendo price_theoretical",
    "Fallback OHLC por indice",
    "Fallback prev_close por indice",
    "Falha lendo mtime",
    "Erro inesperado em obter_book",
]
faltando = [e for e in esperadas if not any(e in m for m in captured)]
if faltando:
    print(f"\n[FALHA] Nao dispararam: {faltando}")
    sys.exit(1)
print("\n[OK] Todos os 7 except blindados dispararam e logaram WARNING")