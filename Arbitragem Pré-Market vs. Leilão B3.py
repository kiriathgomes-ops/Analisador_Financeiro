import os
import requests
import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
FINNHUB_KEY = os.getenv('FINNHUB_API_KEY')

# Mapeamento: Ticker B3 -> Ticker ADR em NY
MAPEAMENTO_ADR = {
    'VALE3': 'VALE',
    'PETR4': 'PBR-A',
    'PETR3': 'PBR',
    'ITUB4': 'ITUB',
    'BBDC4': 'BBD'
}

def obter_variacao_adr_ny(ticker_adr):
    """Coleta o preço do pré-market/fechamento da ADR no Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker_adr}&token={FINNHUB_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if 'c' in res and 'pc' in res and res['pc'] > 0:
            var_pct = res['dp'] # Variação percentual (%)
            return var_pct
    except Exception as e:
        print(f"Erro Finnhub ({ticker_adr}): {e}")
    return None

def obter_preco_leilao_b3(ticker_b3):
    """Coleta o preço indicativo do leilão no MT5."""
    tick = mt5.symbol_info_tick(ticker_b3)
    symbol_info = mt5.symbol_info(ticker_b3)
    
    if tick is None or symbol_info is None:
        return None, None
    
    # O preço do leilão no MT5 costuma ser indicado no tick 'last' 
    # e o fechamento do dia anterior em 'session_close'
    preco_leilao = tick.last
    preco_fechamento_anterior = symbol_info.session_close
    
    if preco_fechamento_anterior > 0:
        var_leilao_pct = ((preco_leilao / preco_fechamento_anterior) - 1) * 100
        return preco_leilao, round(var_leilao_pct, 2)
    
    return preco_leilao, 0.0

def analisar_descasamento_leilao(limiar_spread=0.8):
    """
    Compara as variações das ADRs vs Leilão B3.
    limiar_spread: Diferença mínima em % para considerar oportunidade.
    """
    if not mt5.initialize():
        print("Falha ao inicializar MetaTrader 5")
        return
    
    relatorio = []

    for ticker_b3, ticker_adr in MAPEAMENTO_ADR.items():
        var_adr = obter_variacao_adr_ny(ticker_adr)
        preco_leilao, var_b3 = obter_preco_leilao_b3(ticker_b3)
        
        if var_adr is not None and var_b3 is not None:
            # Spread = Variação em NY - Variação Indicativa na B3
            spread = var_adr - var_b3
            
            sinal = "NEUTRO"
            if spread >= limiar_spread:
                sinal = "COMPRA B3 (Ação atrasada em relação à ADR)"
            elif spread <= -limiar_spread:
                sinal = "VENDA B3 (Ação esticada em relação à ADR)"
                
            relatorio.append({
                'Acao_B3': ticker_b3,
                'Preco_Leilao': preco_leilao,
                'Var_B3_%': var_b3,
                'ADR_NY': ticker_adr,
                'Var_ADR_%': var_adr,
                'Spread_%': round(spread, 2),
                'Sinal': sinal
            })

    mt5.shutdown()
    
    df = pd.DataFrame(relatorio)
    return df

# Exemplo de execução (ideal rodar entre 09:50 e 09:59)
if __name__ == "__main__":
    df_resultado = analisar_descasamento_leilao(limiar_spread=0.5)
    print(df_resultado.to_string(index=False))