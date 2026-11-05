# _dry_cache_excepts.py — dispara os 4 except blindados e confirma WARNING
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

import cache_candles as cc

captured = []


class _Capture(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            captured.append(record.getMessage())


cc.logger.addHandler(_Capture())
cc.logger.setLevel(logging.WARNING)

# ============ T1: _rate_para_dict com 'time' invalido ============
print("== T1: _rate_para_dict 'time' invalido ==")


class _Dtype:
    names = ()


class _FakeRate(dict):
    dtype = _Dtype()


rate = _FakeRate({"time": "NOPE", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5})
d = cc._rate_para_dict(rate)
print(f"   OK fallback -> time={d['time']!r}")

# ============ T2: _detectar_gaps com 'time' invalido ============
print("== T2: _detectar_gaps 'time' invalido ==")
gaps = cc._detectar_gaps(
    [
        {"time": "2026-11-04T10:00:00-03:00"},
        {"time": "INVALID"},
        {"time": "2026-11-04T10:10:00-03:00"},
    ],
    5,
)
print(f"   OK gaps={gaps} (esperado [])")

# ============ T3: _limpar_arquivo_antigo com unlink falhando ============
print("== T3: _limpar_arquivo_antigo unlink falhando ==")
tmp = Path(tempfile.mkdtemp())
orig_dir = cc.ARQUIVO_DIR
try:
    cc.ARQUIVO_DIR = tmp
    f = tmp / "fake.json"
    f.write_text("{}")
    os.utime(f, (0, 0))  # mtime = 1970 -> "antigo"
    orig_unlink = Path.unlink

    def _broken_unlink(self, *a, **kw):
        raise PermissionError("simulado")

    Path.unlink = _broken_unlink
    try:
        n = cc._limpar_arquivo_antigo()
        print(f"   OK removidos={n} (esperado 0)")
    finally:
        Path.unlink = orig_unlink
finally:
    cc.ARQUIVO_DIR = orig_dir
    shutil.rmtree(tmp, ignore_errors=True)

# ============ T4: _obter_com_mt5_aberto gap_min invalido ============
print("== T4: _obter_com_mt5_aberto gap_min invalido ==")


class _FakeMT5:
    @staticmethod
    def symbol_info(sym):
        class _I:
            visible = True

        return _I()

    @staticmethod
    def symbol_select(sym, b):
        return True


sys.modules["MetaTrader5"] = _FakeMT5

antigos = [
    {
        "time": f"2026-11-04T{h:02d}:{m:02d}:00-03:00",
        "open": 1,
        "high": 1,
        "low": 1,
        "close": 1,
        "volume": 1,
    }
    for h in range(10, 14)
    for m in range(0, 60, 5)
]  # 48 candles validos
antigos[-1]["time"] = "INVALID"  # ultimo invalido -> forca except do gap_min

novos = [
    {
        "time": f"2026-11-04T14:{m:02d}:00-03:00",
        "open": 1,
        "high": 1,
        "low": 1,
        "close": 1,
        "volume": 1,
    }
    for m in range(0, 60, 5)
]  # 12 candles validos

cc._ler_cache = lambda p: {"candles": antigos}
cc._resolver_contrato_real = lambda s: "WINZ26"
cc._arquivar_contratos_antigos = lambda c, t: 0
cc._fetch_mt5 = lambda s, t, q: novos
cc._salvar_cache = lambda p, c, t, cs: print(f"   _salvar_cache: {len(cs)} candles")

try:
    candles, contrato = cc._obter_com_mt5_aberto("WIN$", 5, 30)
    print(f"   OK contrato={contrato} n={len(candles)} (esperado 30)")
finally:
    del sys.modules["MetaTrader5"]

# ============ Resumo ============
print(f"\n== WARNINGs capturados: {len(captured)} ==")
for i, msg in enumerate(captured, 1):
    print(f"   {i}. {msg}")

# Sanity check por mensagem (prova que cada except blindado disparou)
esperadas = [
    "Falha convertendo time do rate",       # T1
    "Falha parseando time no _detectar_gaps",  # T2
    "Falha limpando cache arquivado",       # T3
    "Falha calculando gap_min",             # T4
    "Falha verificando obsolescencia",      # bonus: T4 dispara essa tambem
]
faltando = [e for e in esperadas if not any(e in m for m in captured)]
if faltando:
    print(f"\n[FALHA] Nao dispararam: {faltando}")
    sys.exit(1)
print("\n[OK] Todos os except blindados dispararam e logaram WARNING")
