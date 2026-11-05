# _dry_calc2_excepts.py — valida fix do pivo + 3 except blindados
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

captured = []


class _Cap(logging.Handler):
    def emit(self, r):
        if r.levelno >= logging.WARNING:
            captured.append(r.getMessage())


import CalculadoraEstimativaAbertura as col

col.logger.addHandler(_Cap())
col.logger.setLevel(logging.WARNING)

tmp = Path(tempfile.mkdtemp())


# ===== T0: LastTick_Congelado REAL -> OHLC ontem correto =====
print("== T0: LastTick_Congelado real (producao) ==")
ohlc = col._carregar_ohlc_ontem_lasttick()
print(f"   OHLC retornado: {ohlc}")
assert ohlc, "LastTick retornou vazio"
assert abs(ohlc["high"] - 169355.0) < 1.0, ohlc["high"]
assert abs(ohlc["low"] - 166470.0) < 1.0, ohlc["low"]
assert abs(ohlc["close"] - 168035.0) < 1.0, ohlc["close"]
print(f"   OK H=169355 L=166470 C=168035")

# pivos esperados: PP=167953.33 R1=169436.67 R2=170838.33 S1=166551.67 S2=165068.33
pp = (ohlc["high"] + ohlc["low"] + ohlc["close"]) / 3
assert abs(pp - 167953.33) < 1.0, pp
print(f"   OK PP calculado = {pp:.2f}")


# ===== T1: except carregar_niveis_institucionais_smc =====
print("== T1: SMC JSON corrompido ==")
bad_smc = tmp / "smc.json"
bad_smc.write_text("{not valid json", encoding="utf-8")
orig = col.FILE_SMC_DADOS
col.FILE_SMC_DADOS = bad_smc
try:
    r = col.carregar_niveis_institucionais_smc()
    assert r == {"poc_ontem": 0.0, "vwap_ontem": 0.0}, r
    print(f"   OK fallback={r}")
finally:
    col.FILE_SMC_DADOS = orig


# ===== T2: except _carregar_cache_var =====
print("== T2: cache var corrompido ==")
bad_cache = tmp / "cache.json"
bad_cache.write_text("{not valid json", encoding="utf-8")
orig = col.FILE_CACHE_VAR_TEORICA
col.FILE_CACHE_VAR_TEORICA = bad_cache
try:
    r = col._carregar_cache_var()
    assert r == {}, r
    print(f"   OK fallback={r}")
finally:
    col.FILE_CACHE_VAR_TEORICA = orig


# ===== T3: except _resolver_var_teorica no round(float(cache_ajuste)) =====
print("== T3: cache com ajuste invalido (string) ==")
bad_ajuste = tmp / "cache2.json"
bad_ajuste.write_text(
    json.dumps(
        {
            "data_ref": "2026-11-04",
            "ajuste": "NOPE",
            "variacao_teorica_pct": 0.5,
            "timestamp_geracao": "2026-11-04T07:00:00",
        }
    ),
    encoding="utf-8",
)
orig = col.FILE_CACHE_VAR_TEORICA
col.FILE_CACHE_VAR_TEORICA = bad_ajuste
try:
    var, do_cache, ts = col._resolver_var_teorica("2026-11-04", 167551.0, 0.9)
    assert var == 0.9 and do_cache is False, (var, do_cache)
    print(f"   OK var={var} do_cache={do_cache}")
finally:
    col.FILE_CACHE_VAR_TEORICA = orig


# ===== T4: LastTick_Congelado ausente -> cai para proximo fallback =====
print("== T4: LastTick_Congelado ausente ==")
orig = col.FILE_LASTTICK_CONGELADO
col.FILE_LASTTICK_CONGELADO = tmp / "missing.json"
try:
    r = col._carregar_ohlc_ontem_lasttick()
    assert r == {}, r
    print(f"   OK fallback vazio (pivo tentara WIN_AJUSTE/MT5 legado)")
finally:
    col.FILE_LASTTICK_CONGELADO = orig


# ===== T5: LastTick_Congelado corrompido =====
print("== T5: LastTick_Congelado corrompido ==")
bad_lt = tmp / "lt.json"
bad_lt.write_text("{not valid json", encoding="utf-8")
orig = col.FILE_LASTTICK_CONGELADO
col.FILE_LASTTICK_CONGELADO = bad_lt
try:
    r = col._carregar_ohlc_ontem_lasttick()
    assert r == {}, r
    print(f"   OK fallback vazio")
finally:
    col.FILE_LASTTICK_CONGELADO = orig


# ===== resumo =====
print(f"\n== WARNINGs capturados: {len(captured)} ==")
for i, m in enumerate(captured, 1):
    print(f"   {i}. {m[:120]}")

esperadas = [
    "Falha lendo SMC",
    "Falha lendo cache var teorica",
    "Cache com ajuste invalido",
    "LastTick_Congelado.json ausente",
    "Falha lendo LastTick_Congelado",
]
faltando = [e for e in esperadas if not any(e in m for m in captured)]
if faltando:
    print(f"\n[FALHA] Nao dispararam: {faltando}")
    sys.exit(1)

shutil.rmtree(tmp, ignore_errors=True)
print("\n[OK] Fix pivot validado + 5 except blindados dispararam")