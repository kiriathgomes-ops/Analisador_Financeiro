import MetaTrader5 as mt5
from datetime import datetime
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def testar_candles():
    if not mt5.initialize():
        print(f"❌ Falha ao inicializar MT5: {mt5.last_error()}")
        return

    # Tenta o contrato Z26 e o contínuo WIN$ para garantir
    simbolos = ["WINZ26", "WIN$"]
    
    for simbolo in simbolos:
        print("=" * 60)
        print(f"🔎 BUSCANDO DADOS PARA: {simbolo}")
        print("=" * 60)
        
        info = mt5.symbol_info(simbolo)
        if info is None:
            print(f"⚠️ Símbolo {simbolo} não encontrado na corretora.\n")
            continue
            
        if not info.visible:
            mt5.symbol_select(simbolo, True)

        # Pega os últimos 120 candles de M1 (2 horas atrás até agora)
        rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M1, 0, 120)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Sem dados para {simbolo}. last_error={mt5.last_error()}\n")
            continue

        print(f"Total de candles M1 baixados: {len(rates)}\n")
        print(f"{'DATA/HORA':<20} | {'OPEN':<10} | {'HIGH':<10} | {'LOW':<10} | {'CLOSE':<10} | {'VOL':<8}")
        print("-" * 75)

        # Imprime apenas os últimos 30 candles para não poluir a tela
        for r in rates[-30:]:
            dt = datetime.fromtimestamp(r['time'])
            # Filtra apenas o horário de interesse (09:45 até agora)
            if dt.hour >= 9:
                print(f"{dt.strftime('%d/%m/%Y %H:%M:%S'):<20} | {r['open']:<10.0f} | {r['high']:<10.0f} | {r['low']:<10.0f} | {r['close']:<10.0f} | {r['tick_volume']:<8}")
        print("\n")

    mt5.shutdown()

if __name__ == "__main__":
    testar_candles()
    