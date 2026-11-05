# _dry_calc_excepts.py — forca os 3 except blindados + valida fix do pivo
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


# ===== T4: integracao — pivos com dados reais =====
print("== T4: pivos com dados reais (H=170090 L=168390 C=169300) ==")

fake_input = tmp / "validados.json"
fake_input.write_text(
    json.dumps(
        {
            "ativos_validados": [
                {"ativo_id": "WIN_AJUSTE", "open": None, "high": None, "low": None, "close": 167551.0},
                {"ativo_id": "WIN_LAST_TICK", "close": 169300.0},
                {"ativo_id": "EWZ", "change_percent": 0.5},
                {"ativo_id": "SP500_FUT", "change_percent": 0.3},
                {"ativo_id": "VALE_ADR", "change_percent": 0.2},
                {"ativo_id": "PETR_ADR", "change_percent": -0.1},
                {"ativo_id": "DI1_2027", "close": 13.62},
            ]
        }
    ),
    encoding="utf-8",
)

fake_mt5 = tmp / "mt5.json"
fake_mt5.write_text(
    json.dumps(
        {
            "ativos": {
                "WIN": {
                    "open": 169365.0,
                    "high": 170090.0,
                    "low": 168390.0,
                    "close": 169300.0,
                    "prev_close": 168035.0,
                }
            }
        }
    ),
    encoding="utf-8",
)

fake_out = tmp / "estimativa_out.json"
fake_cache = tmp / "cache_out.json"
fake_smc = tmp / "smc_ok.json"

orig_in = col.FILE_INPUT
orig_out = col.FILE_OUTPUT
orig_mt5 = col.FILE_MT5_DADOS
orig_cache = col.FILE_CACHE_VAR_TEORICA
orig_smc = col.FILE_SMC_DADOS

col.FILE_INPUT = str(fake_input)
col.FILE_OUTPUT = str(fake_out)
col.FILE_MT5_DADOS = fake_mt5
col.FILE_CACHE_VAR_TEORICA = fake_cache
col.FILE_SMC_DADOS = fake_smc

try:
    col.processar_calculos_operacionais()
    out = json.loads(fake_out.read_text(encoding="utf-8"))
    piv = out["pivot_points"]["WIN_FUT"]
    print(f"   Pivos: {piv}")
    assert piv.get("PP") is not None, piv
    assert abs(piv["PP"] - 169260.0) < 1.0, piv["PP"]
    assert abs(piv["R1"] - 170130.0) < 1.0, piv["R1"]
    assert abs(piv["S1"] - 168430.0) < 1.0, piv["S1"]
    assert abs(piv["R2"] - 170960.0) < 1.0, piv["R2"]
    assert abs(piv["S2"] - 167560.0) < 1.0, piv["S2"]
    print(f"   OK PP~169260 R1~170130 S1~168430 R2~170960 S2~167560")
finally:
    col.FILE_INPUT = orig_in
    col.FILE_OUTPUT = orig_out
    col.FILE_MT5_DADOS = orig_mt5
    col.FILE_CACHE_VAR_TEORICA = orig_cache
    col.FILE_SMC_DADOS = orig_smc
    shutil.rmtree(tmp, ignore_errors=True)


# ===== resumo =====
print(f"\n== WARNINGs capturados: {len(captured)} ==")
for i, m in enumerate(captured, 1):
    print(f"   {i}. {m}")

esperadas = [
    "Falha lendo SMC",
    "Falha lendo cache var teorica",
    "Cache com ajuste invalido",
]
faltando = [e for e in esperadas if not any(e in m for m in captured)]
if faltando:
    print(f"\n[FALHA] Nao dispararam: {faltando}")
    sys.exit(1)

print("\n[OK] 3 except blindados dispararam + pivos calculados corretamente")
