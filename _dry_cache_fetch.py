# _dry_cache_fetch.py — dry-run funcional de cache_candles.py (NAO grava em disco)
import sys
import cache_candles as cc

# --- Patches para dry-run: log em vez de efeito colateral ---
def _fake_salvar(path, contrato, tf_min, candles):
    print(f"[DRY] _salvar_cache chamado -> {path.name} | contrato={contrato} | tf={tf_min}m | n={len(candles)}")

def _fake_arquivar(contrato, tf_min):
    print(f"[DRY] _arquivar_contratos_antigos chamado -> contrato={contrato} | tf={tf_min}m")
    return 0

cc._salvar_cache = _fake_salvar
cc._arquivar_contratos_antigos = _fake_arquivar

print("[DRY] Chamando obter_candles('WIN$', 5, 60) com patches ativos...")
candles, contrato = cc.obter_candles("WIN$", 5, 60)
print(f"[DRY] Contrato real: {contrato}")
print(f"[DRY] Candles retornados: {len(candles)}")
if candles:
    print(f"[DRY] Primeiro: {candles[0]['time']}")
    print(f"[DRY] Ultimo:   {candles[-1]['time']}")
    print(f"[DRY] Ultimo close: {candles[-1]['close']}")
    print(f"[DRY] Ultimo volume: {candles[-1]['volume']}")
else:
    print("[DRY] AVISO: nenhum candle retornado (MT5 fechado? simbolo ausente?)")

print("[DRY] Fim — nada foi gravado em Coletas/cache/")
sys.exit(0)