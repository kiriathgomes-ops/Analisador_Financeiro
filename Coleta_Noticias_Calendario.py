# ============================================================
# ARQUIVO: Coleta_Noticias_Calendario.py
# MOTIVO: Coletar eventos econômicos Brasil e EUA (2 e 3 estrelas)
# FONTE: TradingView Economic Calendar API (Sem necessidade de Playwright)
# ============================================================
#
# Descrição:
#   Este script consulta a API pública do calendário econômico do TradingView
#   para obter eventos de alto e médio impacto (2 e 3 estrelas) para Brasil e EUA.
#   Gera dois arquivos JSON:
#     1. Noticias_Calendario_0900.json → alerta específico para eventos
#        brasileiros de 3 estrelas às 09:00 (horário de Brasília).
#     2. Noticias_Calendario.json → lista completa de todos os eventos
#        de 2 e 3 estrelas para Brasil e EUA.
#
# ============================================================

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÕES DE DIRETÓRIOS E ARQUIVOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

FILE_OUTPUT_0900 = os.path.join(COLETAS_DIR, "Noticias_Calendario_0900.json")
FILE_OUTPUT_GERAL = os.path.join(COLETAS_DIR, "Noticias_Calendario.json")

HORA_ALERTA = "09:00"   # Horário de Brasília para o alerta especial

# ============================================================
# CONSULTA À API DO TRADINGVIEW
# ============================================================

def consultar_api_tradingview(data_inicio: str, data_fim: str) -> list:
    """
    Consulta a API pública de calendário econômico do TradingView.

    Parâmetros:
        data_inicio (str): Data de início no formato YYYY-MM-DD.
        data_fim (str): Data de fim no formato YYYY-MM-DD.

    Retorna:
        list: Lista de eventos brutos retornados pela API.
              Retorna lista vazia em caso de erro.
    """
    url = "https://economic-calendar.tradingview.com/events"
    params = f"?from={data_inicio}T00:00:00.000Z&to={data_fim}T23:59:59.000Z&countries=BR,US"

    req = urllib.request.Request(
        url + params,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 200:
                dados = json.loads(response.read().decode("utf-8"))
                return dados.get("result", [])
    except Exception as e:
        print(f"[ERRO API TRADINGVIEW] Falha na requisição: {e}")
        return []

    return []

# ============================================================
# PROCESSAMENTO DOS EVENTOS
# ============================================================

def processar_eventos(eventos_raw: list) -> tuple:
    """
    Processa os eventos brutos da API, aplicando filtros e classificações.

    Parâmetros:
        eventos_raw (list): Lista de eventos brutos da API.

    Retorna:
        tuple: (eventos_geral, eventos_0900)
            - eventos_geral: todos os eventos de 2 e 3 estrelas (Brasil e EUA)
            - eventos_0900: eventos brasileiros de 3 estrelas às 09:00
    """
    eventos_geral = []
    eventos_0900 = []

    # Palavras-chave para classificação manual (3 estrelas - alto impacto)
    TERMOS_3_ESTRELAS = [
        "inflation rate", "ipca", "cpi", "ppi",
        "interest rate", "selic", "fed interest rate", "fomc", "copom",
        "non farm payrolls", "unemployment rate",
        "gdp", "pib", "pnad", "caged",
        "core cpi", "pce price index",
    ]

    # Palavras-chave para classificação manual (2 estrelas - médio impacto)
    TERMOS_2_ESTRELAS = [
        "retail sales", "industrial production", "pmi",
        "trade balance", "balance of trade",
        "consumer confidence", "business confidence",
        "s&p global", "fgv", "igp-m",
        "durable goods", "building permits",
    ]

    for item in eventos_raw:
        try:
            # Identificação do país
            country = item.get("country", "")
            if country == "BR":
                moeda = "BRL"
                pais = "Brazil"
            elif country == "US":
                moeda = "USD"
                pais = "United States"
            else:
                continue

            nome_evento = item.get("title", "")
            nome_lower = nome_evento.lower()

            # Classificação original da API: -1 = 1★, 0 = 2★, 1 = 3★
            importance_raw = item.get("importance", -1)
            if importance_raw == 1:
                estrelas = 3
            elif importance_raw == 0:
                estrelas = 2
            else:
                estrelas = 1

            # Ajuste manual por palavras-chave (corrige subavaliações da API)
            if any(term in nome_lower for term in TERMOS_3_ESTRELAS):
                estrelas = 3
            elif estrelas < 2 and any(term in nome_lower for term in TERMOS_2_ESTRELAS):
                estrelas = 2

            # Filtra apenas eventos de 2 ou 3 estrelas
            if estrelas < 2:
                continue

            # Conversão do horário (UTC → Brasília)
            date_utc_str = item.get("date", "")
            hora_br = ""
            if date_utc_str:
                dt_utc = datetime.fromisoformat(date_utc_str.replace("Z", "+00:00"))
                dt_br = dt_utc - timedelta(hours=3)
                hora_br = dt_br.strftime("%H:%M")

            # Valores (atual, previsão, anterior)
            atual = str(item.get("actual", "")) if item.get("actual") is not None else ""
            previsao = str(item.get("forecast", "")) if item.get("forecast") is not None else ""
            anterior = str(item.get("previous", "")) if item.get("previous") is not None else ""

            # Monta o dicionário do evento
            item_evento = {
                "hora": hora_br,
                "pais": pais,
                "moeda": moeda,
                "evento": nome_evento,
                "importancia": estrelas,
                "anterior": anterior,
                "previsao": previsao,
                "atual": atual,
            }

            eventos_geral.append(item_evento)

            # Alerta especial: Brasil + 3 estrelas + horário 09:00
            if pais == "Brazil" and estrelas == 3 and hora_br.startswith(HORA_ALERTA):
                eventos_0900.append(item_evento)

        except Exception:
            continue

    return eventos_geral, eventos_0900

# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def obter_noticias_hoje(data_alvo: str = None) -> tuple:
    """
    Obtém o calendário econômico para a data alvo (hoje por padrão).

    Parâmetros:
        data_alvo (str, opcional): Data no formato YYYY-MM-DD.
                                   Se None, usa a data atual.

    Retorna:
        tuple: (res_geral, res_0900)
            - res_geral: dicionário completo com todos os eventos.
            - res_0900: dicionário com o alerta específico para 09:00.
    """
    if data_alvo is None:
        data_referencia = datetime.now().strftime("%Y-%m-%d")
    else:
        data_referencia = data_alvo

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Coletando calendário via TradingView API para: {data_referencia}..."
    )

    eventos_raw = consultar_api_tradingview(data_referencia, data_referencia)
    print(f"[DEBUG] Eventos brutos retornados pela API: {len(eventos_raw)}")

    eventos_geral, eventos_0900 = processar_eventos(eventos_raw)

    timestamp_iso = datetime.now().isoformat()

    # Arquivo 1: alerta específico para 09:00
    res_0900 = {
        "metadata": {
            "fonte": "TradingView API",
            "timestamp": timestamp_iso,
            "data_referencia": data_referencia,
        },
        "alerta_noticia_0900": {
            "tem_evento_3_estrelas": len(eventos_0900) > 0,
            "quantidade_eventos": len(eventos_0900),
            "eventos": eventos_0900,
        },
    }

    # Arquivo 2: calendário completo
    res_geral = {
        "metadata": {
            "fonte": "TradingView API",
            "timestamp": timestamp_iso,
            "data_referencia": data_referencia,
            "filtros": "Brasil e EUA (2 e 3 Estrelas)",
        },
        "calendario_eventos": {
            "quantidade_eventos": len(eventos_geral),
            "eventos": eventos_geral,
        },
    }

    # Garante que a pasta de saída existe
    os.makedirs(COLETAS_DIR, exist_ok=True)

    with open(FILE_OUTPUT_0900, "w", encoding="utf-8") as f1:
        json.dump(res_0900, f1, indent=2, ensure_ascii=False)

    with open(FILE_OUTPUT_GERAL, "w", encoding="utf-8") as f2:
        json.dump(res_geral, f2, indent=2, ensure_ascii=False)

    return res_geral, res_0900

# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    data_argumento = None

    # Suporte ao argumento --data YYYY-MM-DD
    if len(sys.argv) > 1:
        if "--data" in sys.argv:
            idx = sys.argv.index("--data")
            if idx + 1 < len(sys.argv):
                data_argumento = sys.argv[idx + 1]
        else:
            data_argumento = sys.argv[1]

    res_geral, res_0900 = obter_noticias_hoje(data_alvo=data_argumento)

    data_exibida = res_geral["metadata"]["data_referencia"]

    # Exibe resumo no console
    print()
    print("============================================================")
    print(f" CALENDÁRIO ECONÔMICO BRASIL E EUA - TRADINGVIEW ({data_exibida})")
    print("============================================================")
    print(
        f" Total de eventos 2/3★ (BRL/USD): {res_geral['calendario_eventos']['quantidade_eventos']}"
    )

    if res_0900["alerta_noticia_0900"]["tem_evento_3_estrelas"]:
        print(" Alerta 3 Estrelas BR às 09:00 : SIM ⚠️")
    else:
        print(" Alerta 3 Estrelas BR às 09:00 : NÃO 🟢")

    print("============================================================")
    print(f" Arquivo 1 gerado: {FILE_OUTPUT_0900}")
    print(f" Arquivo 2 gerado: {FILE_OUTPUT_GERAL}")
    print("============================================================")
    print()