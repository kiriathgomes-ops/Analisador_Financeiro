import os
import time
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

ARQUIVO_LOG_LEILAO = "historico_leilao_win.csv"

def obter_dados_completos_win():
    if not mt5.initialize():
        return None

    symbol = "WIN$"
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if info is None or tick is None:
        mt5.shutdown()
        return None

    fechamento_ant = getattr(info, 'session_close', 0.0)
    ajuste_ant = getattr(info, 'session_price_settlement', 0.0)
    
    # Fallback via candle D1 de ontem se o ajuste nativo estiver 0.0
    if ajuste_ant == 0.0:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 1, 1)
        if rates is not None and len(rates) > 0:
            ajuste_ant = float(rates[0]['close'])

    preco_leilao = tick.last

    dados = {
        "Data_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Ativo": info.name,
        "Horario_Tick_MT5": pd.to_datetime(tick.time, unit='s').strftime("%Y-%m-%d %H:%M:%S"),
        "Fechamento_Anterior": fechamento_ant,
        "Preco_Ajuste_Referencia": ajuste_ant,
        "Ultimo_Preco_Leilao": preco_leilao,
        "Bid": tick.bid,
        "Ask": tick.ask,
        "Gap_vs_Fechamento_Pts": round(preco_leilao - fechamento_ant) if fechamento_ant > 0 else 0,
        "Gap_vs_Ajuste_Pts": round(preco_leilao - ajuste_ant) if ajuste_ant > 0 else 0
    }

    mt5.shutdown()
    return dados

def monitorar_e_salvar_leilao(intervalo_segundos=1):
    """
    Roda em loop contínuo capturando e salvando as variações do leilão no CSV.
    """
    print(f"Iniciando gravação de leilão no arquivo: {ARQUIVO_LOG_LEILAO}")
    
    try:
        while True:
            dados = obter_dados_completos_win()
            if dados:
                df = pd.DataFrame([dados])
                
                # Cria o CSV com cabeçalho na primeira vez ou faz append
                escrever_cabecalho = not os.path.exists(ARQUIVO_LOG_LEILAO)
                df.to_csv(ARQUIVO_LOG_LEILAO, mode='a', header=escrever_cabecalho, index=False)
                
                print(f"[{dados['Data_Hora']}] Leilão: {dados['Ultimo_Preco_Leilao']} | "
                      f"Gap Fech: {dados['Gap_vs_Fechamento_Pts']} pts | "
                      f"Gap Ajuste: {dados['Gap_vs_Ajuste_Pts']} pts")
            
            time.sleep(intervalo_segundos)
    except KeyboardInterrupt:
        print("\nMonitoramento encerrado pelo usuário.")

if __name__ == "__main__":
    monitorar_e_salvar_leilao(intervalo_segundos=2)