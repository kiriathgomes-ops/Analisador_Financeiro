import json
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd

ROOT = Path(__file__).resolve().parent
JSON_MT5 = ROOT / "Coletas" / "Dados_MT5_v2_2.json"

def load_contrato():
    if not JSON_MT5.exists():
        print(f"[ERRO] JSON não encontrado: {JSON_MT5}")
        return None
    with open(JSON_MT5, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[JSON] chaves root: {list(data.keys())}")
    candidatos = []
    def find(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                np = f"{path}.{k}" if path else k
                if any(s in k.lower() for s in ["contrato", "principal", "simbolo", "symbol", "ativo"]):
                    candidatos.append((np, v))
                find(v, np)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                find(v, f"{path}[{i}]")
    find(data)
    for p, v in candidatos:
        print(f"[JSON] candidato {p} = {v!r}")
    return None

def test_mt5():
    if not mt5.initialize():
        print(f"[ERRO] mt5.initialize falhou: {mt5.last_error()}")
        return False
    print("[OK] MT5 inicializado")
    print(f"[INFO] terminal: {mt5.terminal_info()}")
    print(f"[INFO] account: {mt5.account_info()}")
    return True

def test_symbol(sym):
    info = mt5.symbol_info(sym)
    if info is None:
        print(f"[SYMBOL] {sym}: NÃO ENCONTRADO (last_error={mt5.last_error()})")
        return False
    print(f"[SYMBOL] {sym}: " + str(info))
    if not info.visible:
        if not mt5.symbol_select(sym, True):
            print(f"[SYMBOL] {sym}: falha ao selecionar (last_error={mt5.last_error()})")
            return False
        print(f"[SYMBOL] {sym}: selecionado agora")
    return True

def test_bars(sym, qtd=100):
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, qtd)
    if rates is None or len(rates) == 0:
        print(f"[BARS] {sym} qtd={qtd}: NENHUMA BARRA (last_error={mt5.last_error()})")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"[BARS] {sym} qtd={qtd}: {len(df)} barras, de {df['time'].iloc[0]} até {df['time'].iloc[-1]}")
    return df

def test_range(sym, dt_ini, dt_fim):
    rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M5, dt_ini, dt_fim)
    if rates is None or len(rates) == 0:
        print(f"[RANGE] {sym} {dt_ini} -> {dt_fim}: NENHUMA BARRA (last_error={mt5.last_error()})")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"[RANGE] {sym} {dt_ini} -> {dt_fim}: {len(df)} barras, de {df['time'].iloc[0]} até {df['time'].iloc[-1]}")
    # Mostra barras entre 09:00 e 14:00 (para pegar 10:00 B3 se servidor for UTC+3)
    janela = df[(df['time'].dt.hour >= 9) & (df['time'].dt.hour <= 14)]
    if not janela.empty:
        print(f"[RANGE] {sym} janela 09-14h:\n{janela[['time','open','high','low','close','tick_volume']].to_string(index=False)}")
    return df

def test_tick_time(sym):
    tick = mt5.symbol_info_tick(sym)
    if tick:
        dt_tick = datetime.fromtimestamp(tick.time)
        print(f"[TZ] {sym} tick.time={tick.time} -> {dt_tick} | local now={datetime.now()} | diff={datetime.now() - dt_tick}")

def main():
    contrato = load_contrato()
    if not test_mt5():
        return
    symbols = [contrato, "WINZ26", "WIN$", "WINV26"] if contrato else ["WINZ26", "WIN$", "WINV26"]
    symbols = list(dict.fromkeys([s for s in symbols if s]))
    print(f"\n[SÍMBOLOS A TESTAR] {symbols}\n")

    for sym in symbols:
        test_symbol(sym)
        test_tick_time(sym)

    print("\n--- TESTE qtd=100 vs qtd=500 ---")
    for sym in symbols:
        test_bars(sym, 100)
        test_bars(sym, 500)

    print("\n--- TESTE RANGE 21/09 e 22/09 (09:00-14:00) ---")
    for sym in symbols:
        for dia in [datetime(2026,9,21), datetime(2026,9,22)]:
            ini = dia.replace(hour=9, minute=0)
            fim = dia.replace(hour=14, minute=0)
            test_range(sym, ini, fim)

    mt5.shutdown()

if __name__ == "__main__":
    main()