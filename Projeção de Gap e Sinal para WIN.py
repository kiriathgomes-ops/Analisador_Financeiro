import os
import requests
import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
FINNHUB_KEY = os.getenv('FINNHUB_API_KEY')

# Pesos de influência para o WIN Futuro na abertura
PESOS_WIN = {
    'EWZ': 0.35,   # ETF Brasil em NY
    'SPY': 0.25,   # S&P 500 Futuro/Pré-market
    'VALE': 0.20,  # ADR Vale
    'PBR': 0.20    # ADR Petrobras
}

def obter_variacao_finnhub(ticker):
    """Puxa a variação % do pré-market/fechamento do ticker no Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if 'dp' in res and res['dp'] is not None:
            return round(res['dp'], 2)
    except Exception as e:
        print(f"Erro Finnhub ({ticker}): {e}")
    return 0.0

def calcular_gap_win_futuro():
    """Calcula a variação teórica (%) e a projeção em PONTOS para o WIN."""
    if not mt5.initialize():
        print("Erro ao inicializar MetaTrader 5")
        return

    # 1. Coleta a variação dos ativos externos
    variacoes = {}
    var_teorica_pct = 0.0

    for ticker, peso in PESOS_WIN.items():
        var_pct = obter_variacao_finnhub(ticker)
        variacoes[ticker] = var_pct
        var_teorica_pct += var_pct * peso

    var_teorica_pct = round(var_teorica_pct, 2)

    # 2. Puxa o último fechamento do WIN no MT5
    # Use o ticker atual do contrato (ex: WINV26) ou a série histórica WIN$
    info_win = mt5.symbol_info("WIN$")
    if not info_win:
        info_win = mt5.symbol_info("WINV26") # Exemplo de contrato vigente

    preco_fechamento = info_win.session_close if info_win else 0

    # 3. Calcula a estimativa de preço de abertura e GAP em pontos
    if preco_fechamento > 0:
        preco_abertura_estimado = preco_fechamento * (1 + (var_teorica_pct / 100))
        gap_pontos_estimado = round(preco_abertura_estimado - preco_fechamento)
    else:
        gap_pontos_estimado = 0
        preco_abertura_estimado = 0

    # 4. Classificação do Viés
    if var_teorica_pct >= 0.30:
        vies = "COMPRADO (GAP DE ALTA)"
    elif var_teorica_pct <= -0.30:
        vies = "VENDIDO (GAP DE BAIXA)"
    else:
        vies = "NEUTRO (GAP PEQUENO / SEM TENDÊNCIA)"

    mt5.shutdown()

    return {
        'Fechamento_Anterior_WIN': preco_fechamento,
        'Var_Teorica_Projetada_%': var_teorica_pct,
        'Gap_Estimado_Pontos': gap_pontos_estimado,
        'Preco_Abertura_Projetado': round(preco_abertura_estimado),
        'Vies_Abertura': vies,
        'Detalhes_Ativos': variacoes
    }

if __name__ == "__main__":
    resultado = calcular_gap_win_futuro()
    print("=== PROJEÇÃO DE ABERTURA DO WIN FUTURO (09:00) ===")
    for k, v in resultado.items():
        print(f"{k}: {v}")