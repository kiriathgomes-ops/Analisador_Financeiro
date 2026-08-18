import json
import requests
from datetime import datetime

# Mapeamento exato de ativos conforme você visualiza no TradingView
ATIVOS_TV = [
    # Câmbio e Juros
    {"ticker_tv": "BCB:PTAX", "categoria": "Câmbio", "id_fixo": "USD_PTAX"},
    {"ticker_tv": "FX_IDC:USDBRL", "categoria": "Câmbio", "id_fixo": "USDBRL"},
    {"ticker_tv": "FX_IDC:USDMXN", "categoria": "Câmbio", "id_fixo": "USDMXN"},
    {"ticker_tv": "TVC:DXY", "categoria": "Câmbio", "id_fixo": "DXY"},
    
    # Futuros B3
    {"ticker_tv": "BMFBOVESPA:WIN1!", "categoria": "Futuros B3", "id_fixo": "INDICE_FUT"},
    {"ticker_tv": "BMFBOVESPA:WDO1!", "categoria": "Futuros B3", "id_fixo": "DOLAR_FUT"},
    {"ticker_tv": "BMFBOVESPA:DI1F2027", "categoria": "Juros DI", "id_fixo": "DI_2027"},
    {"ticker_tv": "BMFBOVESPA:DI1F2029", "categoria": "Juros DI", "id_fixo": "DI_2029"},
    
    # Volatilidade e Commodities
    {"ticker_tv": "TVC:VIX", "categoria": "Volatilidade", "id_fixo": "VIX"},
    {"ticker_tv": "SGX:FEF1!", "categoria": "Commodities", "id_fixo": "MINERIO_FEF1"},
    {"ticker_tv": "SGX:FEF2!", "categoria": "Commodities", "id_fixo": "MINERIO_FEF2"},
    {"ticker_tv": "NYMEX:CL1!", "categoria": "Commodities", "id_fixo": "PETROLEO_WTI"},
    {"ticker_tv": "TVC:GOLD", "categoria": "Commodities", "id_fixo": "OURO_SPOT"},
    
    # Índices Internacionais
    {"ticker_tv": "AMEX:EWZ", "categoria": "Índices Globais", "id_fixo": "EWZ"},
    {"ticker_tv": "CME_MINI:ES1!", "categoria": "Índices Globais", "id_fixo": "SP500_FUT"},
    {"ticker_tv": "CME_MINI:NQ1!", "categoria": "Índices Globais", "id_fixo": "NASDAQ_FUT"},
    
    # ADRs
    {"ticker_tv": "NYSE:VALE", "categoria": "ADRs B3", "id_fixo": "VALE_ADR"},
    {"ticker_tv": "NYSE:PBR", "categoria": "ADRs B3", "id_fixo": "PETR_ADR"},
    {"ticker_tv": "NYSE:ITUB", "categoria": "ADRs B3", "id_fixo": "ITUB_ADR"},
    {"ticker_tv": "OTC:BDORY", "categoria": "ADRs B3", "id_fixo": "BDORY_ADR"},
    {"ticker_tv": "NYSE:BBD", "categoria": "ADRs B3", "id_fixo": "BBD_ADR"},
    {"ticker_tv": "OTC:BOLSY", "categoria": "ADRs B3", "id_fixo": "BOLSY_ADR"}
]

def coletar_ptax():
    """Busca a PTAX oficial no Banco Central"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/1?formato=json"
        res = requests.get(url, timeout=5).json()
        return float(res[0]["valor"])
    except Exception:
        return None

def coletar_tradingview_scanner():
    """Consulta diretamente a API do Scanner do TradingView sem bibliotecas de terceiros"""
    url = "https://scanner.tradingview.com/global/scan"
    
    symbols = [item["ticker_tv"] for item in ATIVOS_TV if item["ticker_tv"] != "BCB:PTAX"]
    
    payload = {
        "symbols": {"tickers": symbols},
        "columns": ["close", "open", "high", "low", "change", "volume"]
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        
        # Mapeia resposta por ticker
        resultados = {}
        for row in data.get("data", []):
            ticker = row["s"]
            d = row["d"]
            resultados[ticker] = {
                "close": d[0],
                "open": d[1],
                "high": d[2],
                "low": d[3],
                "change_percent": d[4],
                "volume": d[5]
            }
        return resultados
    except Exception as e:
        print(f"Erro ao acessar TradingView Scanner: {e}")
        return {}

def executar_coleta():
    tv_dados = coletar_tradingview_scanner()
    ptax_val = coletar_ptax()

    coletas = []

    # 1. Adiciona PTAX
    coletas.append({
        "ativo": "USD_PTAX",
        "fonte": "BACEN_SGS_10813",
        "timestamp": datetime.now().isoformat(),
        "status": "OK" if ptax_val else "ERRO",
        "dados_reais": {
            "close": ptax_val,
            "open": None, "high": None, "low": None, "change_percent": None, "volume": None
        }
    })

    # 2. Processa os ativos do TradingView
    for item in ATIVOS_TV:
        ticker = item["ticker_tv"]
        if ticker == "BCB:PTAX":
            continue

        dados = tv_dados.get(ticker)
        if dados:
            coletas.append({
                "ativo": ticker,
                "fonte": "TRADINGVIEW_SCANNER",
                "timestamp": datetime.now().isoformat(),
                "status": "OK",
                "dados_reais": dados
            })
        else:
            coletas.append({
                "ativo": ticker,
                "fonte": "TRADINGVIEW_SCANNER",
                "timestamp": datetime.now().isoformat(),
                "status": "SEM_DADOS",
                "dados_reais": None
            })

    output = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "TV_DIRECT_SCANNER",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": "Coleta_TV_Padronizada.json"
        },
        "coletas": coletas
    }

    return output

if __name__ == "__main__":
    resultado = executar_coleta()
    with open("Coleta_TV_Padronizada.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("Coleta concluída com sucesso e alinhada ao TradingView!")