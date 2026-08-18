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

# Diretório de coletas do seu sistema
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
FILE_MT5_V2 = os.path.join(COLETAS_DIR, "Dados_MT5_v2_2.json")
FILE_MT5_V1 = os.path.join(COLETAS_DIR, "Dados_MT5.json")

# Mapeamento de tickers (Adicionados WIN e WDO para compatibilidade)
MAPEAMENTO_ATIVOS = {
    "VALE": {"tv": "NYSE:VALE", "fh": "VALE", "mt5": None},
    "PETR4": {"tv": "NYSE:PBR", "fh": "PBR", "mt5": None},
    "ITUB4": {"tv": "NYSE:ITUB", "fh": "ITUB", "mt5": None},
    "BBAS3": {"tv": "OTC:BDORY", "fh": "BDORY", "mt5": None},
    "BBDC4": {"tv": "NYSE:BBD", "fh": "BBD", "mt5": None},
    "B3SA3": {"tv": "OTC:BOLSY", "fh": "BOLSY", "mt5": None},
    "EWZ": {"tv": "AMEX:EWZ", "fh": "EWZ", "mt5": None},
    # Ativos B3 / MT5
    "WIN_FUT": {"tv": "BMFBOVESPA:WIN1!", "fh": None, "mt5": "WIN"},
    "WDO_FUT": {"tv": "BMFBOVESPA:WDO1!", "fh": None, "mt5": "WDO"},
}

# ------------------------------------------------------------
# 1. COLETOR TRADINGVIEW
# ------------------------------------------------------------
def coletar_tradingview_ativos():
    url = "https://scanner.tradingview.com/global/scan"
    tv_tickers = [v["tv"] for v in MAPEAMENTO_ATIVOS.values() if v["tv"]]
    
    payload = {"symbols": {"tickers": tv_tickers}, "columns": ["close", "change"]}
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

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
                    for nome_amigavel, config in MAPEAMENTO_ATIVOS.items():
                        if config["tv"] == ticker_tv:
                            resultados[nome_amigavel] = {
                                "Preco_TV": float(vals[0]),
                                "Var_%_TV": float(vals[1]) if vals[1] is not None else 0.0
                            }
    except Exception as e:
        print(f"[ERRO TradingView]: {e}")
    return resultados

# ------------------------------------------------------------
# 2. COLETOR FINNHUB
# ------------------------------------------------------------
def coletar_single_finnhub(ticker_fh):
    if not FINNHUB_API_KEY or not ticker_fh:
        return None
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker_fh}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if 'c' in data and data['c'] != 0:
            return {
                'Preco_FH': float(data['c']),
                'Var_%_FH': round(float(data['dp']), 2)
            }
    except Exception as e:
        pass
    return None

def coletar_finnhub_ativos():
    resultados = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(coletar_single_finnhub, cfg["fh"]): nome
            for nome, cfg in MAPEAMENTO_ATIVOS.items() if cfg["fh"]
        }
        for future in futures:
            nome = futures[future]
            data = future.result()
            if data:
                resultados[nome] = data
    return resultados

# ------------------------------------------------------------
# 3. COLETOR METATRADER 5 (Leitura do cache v2.2 ou v1)
# ------------------------------------------------------------
def coletar_mt5_ativos():
    """Lê os últimos preços salvos do WIN e WDO capturados pelo MT5"""
    resultados = {}
    
    # Tenta v2.2
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                dados = json.load(f).get("ativos", {})
                if "WIN" in dados and dados["WIN"].get("last"):
                    resultados["WIN_FUT"] = {"Preco_MT5": float(dados["WIN"]["last"])}
                if "WDO" in dados and dados["WDO"].get("last"):
                    resultados["WDO_FUT"] = {"Preco_MT5": float(dados["WDO"]["last"])}
                return resultados
        except Exception:
            pass

    # Fallback v1
    if os.path.exists(FILE_MT5_V1):
        try:
            with open(FILE_MT5_V1, "r", encoding="utf-8") as f:
                contratos = json.load(f).get("contratos", {})
                for c_nome, c_info in contratos.items():
                    if "WIN" in c_nome and "WIN_FUT" not in resultados:
                        if c_info.get("last"): resultados["WIN_FUT"] = {"Preco_MT5": float(c_info["last"])}
                    if "WDO" in c_nome and "WDO_FUT" not in resultados:
                        if c_info.get("last"): resultados["WDO_FUT"] = {"Preco_MT5": float(c_info["last"])}
        except Exception:
            pass

    return resultados

# ------------------------------------------------------------
# 4. EXECUTOR PARALELO MULTI-FONTE
# ------------------------------------------------------------
def executar_coleta_comparativa():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Coletando TradingView, Finnhub e MT5 em paralelo...")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futuro_tv = executor.submit(coletar_tradingview_ativos)
        futuro_fh = executor.submit(coletar_finnhub_ativos)
        futuro_mt5 = executor.submit(coletar_mt5_ativos)
        
        dados_tv = futuro_tv.result()
        dados_fh = futuro_fh.result()
        dados_mt5 = futuro_mt5.result()

    linhas = []
    for nome, cfg in MAPEAMENTO_ATIVOS.items():
        tv_info = dados_tv.get(nome, {})
        fh_info = dados_fh.get(nome, {})
        mt5_info = dados_mt5.get(nome, {})

        preco_tv = tv_info.get("Preco_TV", None)
        preco_fh = fh_info.get("Preco_FH", None)
        preco_mt5 = mt5_info.get("Preco_MT5", None)

        # Cálculo de diferença de preço (se aplicável)
        diff_tv_mt5 = None
        if preco_tv and preco_mt5:
            diff_tv_mt5 = round(abs(preco_tv - preco_mt5), 2)

        linhas.append({
            "Ativo": nome,
            "Preco_TradingView": preco_tv,
            "Preco_Finnhub": preco_fh,
            "Preco_MT5": preco_mt5,
            "Diff_(TV_vs_MT5)": diff_tv_mt5,
            "Var_%_TV": tv_info.get("Var_%_TV", None),
            "Var_%_FH": fh_info.get("Var_%_FH", None)
        })

    return pd.DataFrame(linhas)

if __name__ == "__main__":
    df_resultado = executar_coleta_comparativa()
    print("\n=== TABELA COMPARATIVA DE ATIVOS (TV vs FINNHUB vs MT5) ===")
    print(df_resultado.to_string(index=False))