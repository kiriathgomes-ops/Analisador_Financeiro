import os
import json
import urllib.request
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')

# Mapeamento de tickers comuns para comparativo direto entre TradingView e Finnhub
# Chave: Ticker amigável | Valor: (Ticker TradingView, Ticker Finnhub)
MAPEAMENTO_ADRS = {
    "VALE": ("NYSE:VALE", "VALE"),
    "PETR4": ("NYSE:PBR", "PBR"),
    "ITUB4": ("NYSE:ITUB", "ITUB"),
    "BBAS3": ("OTC:BDORY", "BDORY"),
    "BBDC4": ("NYSE:BBD", "BBD"),
    "B3SA3": ("OTC:BOLSY", "BOLSY"),
    "EWZ": ("AMEX:EWZ", "EWZ"),
}

# ------------------------------------------------------------
# 1. COLETOR TRADINGVIEW (Baseado no seu Coletor.py)
# ------------------------------------------------------------
def coletar_tradingview_adrs():
    """Coleta cotações via TradingView Scanner API"""
    url = "https://scanner.tradingview.com/global/scan"
    
    # Inverte para busca rápida
    tv_tickers = [v[0] for v in MAPEAMENTO_ADRS.values()]
    
    payload = {
        "symbols": {"tickers": tv_tickers},
        "columns": ["close", "change"],
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    resultados = {}
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            for item in res.get("data", []):
                ticker_tv = item.get("s")
                vals = item.get("d", [])
                
                if len(vals) >= 2 and vals[0] is not None:
                    # Relaciona com o nome amigável
                    for nome_amigavel, (tv_symbol, _) in MAPEAMENTO_ADRS.items():
                        if tv_symbol == ticker_tv:
                            resultados[nome_amigavel] = {
                                "Preco_TV": float(vals[0]),
                                "Var_%_TV": float(vals[1]) if vals[1] is not None else 0.0
                            }
    except Exception as e:
        print(f"[ERRO] Falha na coleta TradingView: {e}")
        
    return resultados

# ------------------------------------------------------------
# 2. COLETOR FINNHUB (Baseado no seu segundo coletor)
# ------------------------------------------------------------
def coletar_single_finnhub(ticker_fh):
    if not FINNHUB_API_KEY:
        return None
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker_fh}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if 'c' in data and data['c'] != 0:
            return {
                'Preco_Finnhub': float(data['c']),
                'Var_%_Finnhub': round(float(data['dp']), 2)
            }
    except Exception as e:
        print(f"Erro Finnhub ({ticker_fh}): {e}")
    return None

def coletar_finnhub_adrs():
    """Coleta cotações via Finnhub usando ThreadPoolExecutor interno"""
    resultados = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(coletar_single_finnhub, fh_symbol): nome_amigavel
            for nome_amigavel, (_, fh_symbol) in MAPEAMENTO_ADRS.items()
        }
        for future in futures:
            nome_amigavel = futures[future]
            data = future.result()
            if data:
                resultados[nome_amigavel] = data
    return resultados

# ------------------------------------------------------------
# 3. EXECUTOR PARALELO E COMPARADOR
# ------------------------------------------------------------
def executar_coleta_comparativa():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Disparando coletas paralelas (TradingView vs Finnhub)...")
    
    # Dispara as duas fontes em threads simultâneas
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_tv = executor.submit(coletar_tradingview_adrs)
        futuro_fh = executor.submit(coletar_finnhub_adrs)
        
        dados_tv = futuro_tv.result()
        dados_fh = futuro_fh.result()

    # Consolidação em uma única estrutura de dados
    linhas = []
    for nome_amigavel in MAPEAMENTO_ADRS.keys():
        tv_info = dados_tv.get(nome_amigavel, {})
        fh_info = dados_fh.get(nome_amigavel, {})

        preco_tv = tv_info.get("Preco_TV", None)
        preco_fh = fh_info.get("Preco_Finnhub", None)
        
        # Cálculo da divergência de preço entre as duas APIs
        divergencia = None
        if preco_tv and preco_fh:
            divergencia = round(abs(preco_tv - preco_fh), 4)

        linhas.append({
            "Ativo": nome_amigavel,
            "Preco_TradingView": preco_tv,
            "Var_%_TV": tv_info.get("Var_%_TV", None),
            "Preco_Finnhub": preco_fh,
            "Var_%_Finnhub": fh_info.get("Var_%_Finnhub", None),
            "Diff_Preco": divergencia
        })

    df_comparativo = pd.DataFrame(linhas)
    return df_comparativo

if __name__ == "__main__":
    df_resultado = executar_coleta_comparativa()
    print("\n=== TABELA COMPARATIVA DE ADRS (TRADINGVIEW vs FINNHUB) ===")
    print(df_resultado.to_string(index=False))