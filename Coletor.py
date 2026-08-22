# ============================================================
# ARQUIVO: Coletor.py
# DATA: 19/08/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados Completa (BACEN SGS + Finnhub + MT5 Futuros/Ações)
# ATUALIZAÇÕES:
#   1. Ciclo unificado de conexão MT5 (sem reconexões desnecessárias).
#   2. Registro dedicado para WIN_PREV_CLOSE gravado no JSON ROM.
#   3. Rotação temporal em 12 arquivos (60 minutos de histórico).
# ============================================================

import json
import os
import shutil
import ssl
import sys
import urllib.request
from datetime import datetime, time

import MetaTrader5 as mt5
import requests
from dotenv import load_dotenv

# ============================================================
# CONFIGURAÇÕES GERAIS E AMBIENTE
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
os.makedirs(COLETAS_DIR, exist_ok=True)

# Carrega variáveis de ambiente (.env) para autenticações externas (ex: Finnhub)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# ============================================================
# ARQUIVOS DE ROTAÇÃO TEMPORAL E ARMAZENAMENTO LOCAL
# FREQUÊNCIA DE ROTAÇÃO: A cada execução do script (intervalos tipicamente de 5 min)
# ARMAZENAMENTO: Histórico rolante de 12 arquivos (representando os últimos 60 minutos)
# ============================================================

ARQUIVOS_ROM = [
    os.path.join(COLETAS_DIR, f"Coleta_rom-{i}.json") for i in range(0, 60, 5)
]
FILE_ROM0 = ARQUIVOS_ROM[0] # Arquivo mais recente (0 min)

FILE_RAM = os.path.join(COLETAS_DIR, "Coleta_ram.json")
FILE_UNIFICADO = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")

# Arquivos gerados por coletores auxiliares do MetaTrader 5
FILE_MT5 = os.path.join(COLETAS_DIR, "Dados_MT5.json")
FILE_MT5_V2 = os.path.join(COLETAS_DIR, "Dados_MT5_v2_2.json")

# Ticker dinâmico do Minério de Ferro no Cingapura Exchange (SGX) ajustado para o ano corrente
ANO_ATUAL = datetime.now().year
TICKER_FEF2 = f"SGX:FEFU{ANO_ATUAL}"

# ============================================================
# FONTE 1: TRADINGVIEW SCANNER API
# FREQUÊNCIA: Coletado em tempo real em toda execução do pipeline
# ORIGEM: Bolsas Globais (B3, NYMEX, CME, CBOE, SGX, Forex) via TradingView
# ============================================================

TICKERS_TRADINGVIEW = [
    "BMFBOVESPA:DI1F2027", # Juros Futuros B3 (Vencimento 2027)
    "BMFBOVESPA:DI1F2029", # Juros Futuros B3 (Vencimento 2029)
    "TVC:VIX",            # Índice de Volatilidade (CBOE)
    "SGX:FEF1!",          # Minério de Ferro 62% - Contrato Vigente (SGX)
    TICKER_FEF2,          # Minério de Ferro 62% - Contrato 2º Mês (SGX)
    "NYMEX:CL1!",         # Petróleo WTI Futuro (NYMEX)
    "CME_MINI:ES1!",      # S&P 500 E-mini Futuro (CME)
    "CME_MINI:NQ1!",      # Nasdaq 100 E-mini Futuro (CME)
    "TVC:DXY",            # Dollar Index (Força global do USD)
    "FX_IDC:USDMXN",      # Par Forex Dólar / Peso Mexicano
    "TVC:GOLD",           # Ouro Spot (Contrato de Dólar/Onça-Troj)
    "FX_IDC:USDBRL",      # Par Forex Dólar / Real Brasileiro
]

# ============================================================
# FONTE 2: FINNHUB API (MERCADO NORTE-AMERICANO)
# FREQUÊNCIA: Coletado em tempo real em toda execução do pipeline
# ORIGEM: APIs de mercado das bolsas americanas (NYSE, NASDAQ, AMEX, OTC)
# ============================================================

ATIVOS_FINNHUB = [
    {"ativo": "AMEX:EWZ", "ticker_coleta": "EWZ", "id_fixo": "EWZ", "categoria": "Índices Globais"},    # ETF iShares MSCI Brazil
    {"ativo": "NYSE:VALE", "ticker_coleta": "VALE", "id_fixo": "VALE_ADR", "categoria": "ADRs B3"},     # ADR da Vale na NYSE
    {"ativo": "NYSE:PBR", "ticker_coleta": "PBR", "id_fixo": "PETR_ADR", "categoria": "ADRs B3"},      # ADR da Petrobras na NYSE
    {"ativo": "NYSE:ITUB", "ticker_coleta": "ITUB", "id_fixo": "ITUB_ADR", "categoria": "ADRs B3"},     # ADR do Itaú Unibanco
    {"ativo": "OTC:BDORY", "ticker_coleta": "BDORY", "id_fixo": "BBAS_ADR", "categoria": "ADRs B3"},    # ADR do Banco do Brasil
    {"ativo": "NYSE:BBD", "ticker_coleta": "BBD", "id_fixo": "BBD_ADR", "categoria": "ADRs B3"},       # ADR do Bradesco
    {"ativo": "OTC:BOLSY", "ticker_coleta": "BOLSY", "id_fixo": "B3_ADR", "categoria": "ADRs B3"},     # ADR da B3 SA
]

# ============================================================
# FONTE 3: METATRADER 5 (AÇÕES A VISTA DA B3)
# FREQUÊNCIA: Coletado durante o horário de pregão / execução
# ORIGEM: Terminal local MetaTrader 5 conectado à corretora B3
# ============================================================

ATIVOS_MT5_B3 = [
    {"ativo": "VALE3", "ticker_coleta": "VALE3", "id_fixo": "VALE3", "categoria": "Ações B3"},
    {"ativo": "PETR4", "ticker_coleta": "PETR4", "id_fixo": "PETR4", "categoria": "Ações B3"},
    {"ativo": "ITUB4", "ticker_coleta": "ITUB4", "id_fixo": "ITUB4", "categoria": "Ações B3"},
    {"ativo": "BBAS3", "ticker_coleta": "BBAS3", "id_fixo": "BBAS3", "categoria": "Ações B3"},
    {"ativo": "BBDC4", "ticker_coleta": "BBDC4", "id_fixo": "BBDC4", "categoria": "Ações B3"},
    {"ativo": "B3SA3", "ticker_coleta": "B3SA3", "id_fixo": "B3SA3", "categoria": "Ações B3"},
]

# ============================================================
# DICIONÁRIO DE PADRONIZAÇÃO DE TICKERS
# Mapeia identificadores das APIs para nomes amigáveis no JSON unificado
# ============================================================

MAPEAMENTO_TICKERS = {
    "USD_PTAX": "USD_PTAX",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "WIN_PREV_CLOSE": "WIN_PREV_CLOSE",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
    "DI1_FUT": "DI1_FUT",
    "TVC:VIX": "VIX",
    "SGX:FEF1!": "IRON_ORE",
    "SGX:FEF2!": "IRON_ORE_2M",
    "NYMEX:CL1!": "CRUDE_OIL",
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BOLSY": "B3_ADR",
    "AMEX:EWZ": "EWZ",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:DXY": "DXY",
    "FX_IDC:USDMXN": "USD_MXN",
    "TVC:GOLD": "GOLD",
    "FX_IDC:USDBRL": "USD_BRL",
    "WIN_LAST_TICK": "WIN_LAST_TICK",
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBAS3": "BBAS3",
    "BBDC4": "BBDC4",
    "B3SA3": "B3SA3",
}

# ============================================================
# FUNÇÕES AUXILIARES DE JANELA TEMPORAL
# ============================================================

def esta_na_janela_ajuste() -> bool:
    """
    REGRA TEMPORAL: Verifica se o horário de execução está entre 19:00 e 08:50 (Overnight/Ajuste).
    Usado para decidir se deve consultar o ajuste oficial ou reaproveitar dados do cache.
    """
    agora = datetime.now().time()
    return agora >= time(19, 0, 0) or agora <= time(8, 50, 0)

# ============================================================
# COLETORES DE DADOS POR FONTE
# ============================================================

def coletar_bacen_ptax():
    """
    FONTE PRIMÁRIA: Banco Central do Brasil - API SGS (Série 10813 - PTAX de Fechamento Diário).
    FONTE DE FALLBACK: TradingView (FX_IDC:USDBRL) caso a API do BACEN falhe.
    FREQUÊNCIA DE ATUALIZAÇÃO DO BACEN: Atualizado pelo BACEN 4 vezes ao dia e consolidado após as 13:10.
    """
    timestamp = datetime.now().isoformat()
    url_sgs = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"

    # Ignora verificação SSL para evitar bloqueios de certificado do BCB
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req_sgs = urllib.request.Request(
        url_sgs,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )

    # Tentativa de Coleta Oficial BACEN
    try:
        with urllib.request.urlopen(req_sgs, context=ctx, timeout=10) as response:
            if response.getcode() == 200:
                res = json.loads(response.read().decode("utf-8"))
                if res:
                    ultimo_valor = float(res[-1]["valor"].replace(",", "."))
                    return {
                        "ativo": "USD_PTAX",
                        "fonte": "BACEN_SGS_10813",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": ultimo_valor,
                            "open": None,
                            "high": None,
                            "low": None,
                            "change_percent": None,
                            "volume": None,
                        },
                    }
    except Exception as e:
        print(f"[AVISO] Falha na API SGS Bacen: {e}. Executando fallback...")

    # Fallback: Coleta cotação do Dólar Comercial via TradingView se o BACEN estiver indisponível
    try:
        payload = {"symbols": {"tickers": ["FX_IDC:USDBRL"]}, "columns": ["close"]}
        req_tv = urllib.request.Request(
            "https://scanner.tradingview.com/global/scan",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req_tv, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            vals = res.get("data", [])[0].get("d", [])
            if vals and vals[0] is not None:
                return {
                    "ativo": "USD_PTAX",
                    "fonte": "TRADINGVIEW_FALLBACK",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {"close": float(vals[0]), "open": None, "high": None, "low": None,
                                    "change_percent": None, "volume": None},
                }
    except Exception:
        pass

    return {
        "ativo": "USD_PTAX",
        "fonte": "BACEN_API",
        "timestamp": timestamp,
        "status": "SEM_DADOS",
        "dados_reais": None,
    }

def coletar_ajuste_oficial():
    """
    FONTE: TradingView (BMFBOVESPA:WIN1!) - Ativo B3_AJUSTE_WIN.
    REGRA TEMPORAL / QUANDO OCORRE:
      - Entre 19:00 e 08:50: Executa requisição HTTP para coletar o Preço de Ajuste oficial calculado pela B3 no fim do dia.
      - Entre 08:51 e 18:59 (Fora da janela): Não faz requisição externa; reusa o valor gravado nos arquivos de cache (FILE_RAM / FILE_ROM0).
    """
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()
    hora_inicio = time(19, 0, 0)
    hora_fim = time(8, 50, 0)

    # REGRA: Fora do horário estipulado, busca nos arquivos de cache local
    if hora_fim < hora_atual < hora_inicio:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Fora da janela de ajuste. Buscando cache...")
        for arquivo_cache in [FILE_RAM, FILE_ROM0]:
            if os.path.exists(arquivo_cache):
                try:
                    with open(arquivo_cache, 'r', encoding='utf-8') as f:
                        dados_cache = json.load(f)
                        for item in dados_cache.get("coletas", []):
                            if item.get("ativo") == "B3_AJUSTE_WIN":
                                item["fonte"] = "CACHE_DISCO (Fora da janela)"
                                item["timestamp"] = timestamp
                                return [item]
                except:
                    continue
        return [{
            "ativo": "B3_AJUSTE_WIN",
            "fonte": "NENHUM_DADO",
            "timestamp": timestamp,
            "status": "FORA_JANELA_SEM_CACHE",
            "dados_reais": None,
        }]

    # REGRA: Dentro da janela de ajuste (19:00 as 08:50), realiza a coleta na API
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Dentro da janela. Coletando ajuste da API...")
    url = f"https://scanner.tradingview.com/symbol?symbol=BMFBOVESPA:WIN1!&fields=close,change"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            close_val = res.get("close")
            change_val = res.get("change", 0.0)
            return [{
                "ativo": "B3_AJUSTE_WIN",
                "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                "timestamp": timestamp,
                "status": "OK" if close_val is not None else "ERRO",
                "dados_reais": {
                    "close": float(close_val) if close_val is not None else None,
                    "open": None,
                    "high": None,
                    "low": None,
                    "change_percent": float(change_val) if change_val is not None else 0.0,
                    "volume": None,
                },
            }]
    except Exception as e:
        print(f"   ❌ Erro ao coletar ajuste: {e}")
        return [{
            "ativo": "B3_AJUSTE_WIN",
            "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
            "timestamp": timestamp,
            "status": "ERRO",
            "dados_reais": None,
        }]

def coletar_tradingview():
    """
    FONTE: API Scanner do TradingView (endpoint global/scan).
    QUANDO OCORRE: Toda vez que o script é rodado.
    DADOS OBTIDOS: Preço de fechamento/último, Abertura, Máxima, Mínima, Variação (%) e Volume dos ativos em TICKERS_TRADINGVIEW.
    """
    url = "https://scanner.tradingview.com/global/scan"
    timestamp = datetime.now().isoformat()
    payload = {
        "symbols": {"tickers": TICKERS_TRADINGVIEW},
        "columns": ["close", "open", "high", "low", "change", "volume"],
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            resultados = []
            for item in res.get("data", []):
                ticker = item.get("s")
                vals = item.get("d", [])
                ticker_chave = "SGX:FEF2!" if ticker == TICKER_FEF2 else ticker
                if len(vals) >= 5 and vals[0] is not None:
                    close = float(vals[0])
                    change_pct = float(vals[4]) if vals[4] is not None else 0.0
                    resultados.append({
                        "ativo": ticker_chave,
                        "fonte": "TRADINGVIEW_SCANNER",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": close,
                            "open": float(vals[1]) if vals[1] is not None else None,
                            "high": float(vals[2]) if vals[2] is not None else None,
                            "low": float(vals[3]) if vals[3] is not None else None,
                            "change_percent": change_pct,
                            "volume": float(vals[5]) if len(vals) > 5 and vals[5] is not None else None,
                        },
                    })
            return resultados
    except Exception as e:
        print(f"[ERRO] Falha na coleta TradingView: {e}")
        return []

def coletar_finnhub():
    """
    FONTE: API Finnhub (endpoint /quote).
    QUANDO OCORRE: Toda vez que o script é rodado (desde que haja FINNHUB_API_KEY no arquivo .env).
    DADOS OBTIDOS: Cotação em tempo real das ADRs brasileiras em NY e do ETF EWZ (Preço, Variação %, Fechamento Anterior).
    """
    timestamp = datetime.now().isoformat()
    resultados = []
    if not FINNHUB_API_KEY:
        print("⚠️ [AVISO] Chave FINNHUB_API_KEY não encontrada.")
        return resultados

    for cfg in ATIVOS_FINNHUB:
        ticker = cfg["ticker_coleta"]
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        try:
            response = requests.get(url, timeout=5)
            res = response.json()
            if "error" in res:
                print(f"⚠️ Erro Finnhub ({ticker}): {res['error']}")
                resultados.append({"ativo": cfg["ativo"], "fonte": "FINNHUB", "timestamp": timestamp, "status": "ERRO", "dados_reais": None})
                continue
            if "c" in res and res["c"] != 0:
                preco = float(res["c"])
                var_pct = round(float(res.get("dp", 0.0)), 2)
                var_abs = round(float(res.get("d", 0.0)), 2)
                fechamento_ant = float(res.get("pc", 0.0))
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": preco,
                        "open": float(res.get("o")) if res.get("o") else None,
                        "high": float(res.get("h")) if res.get("h") else None,
                        "low": float(res.get("l")) if res.get("l") else None,
                        "change_percent": var_pct,
                        "volume": None,
                        "var_abs": var_abs,
                        "fechamento_anterior": fechamento_ant,
                    },
                })
            else:
                resultados.append({"ativo": cfg["ativo"], "fonte": "FINNHUB", "timestamp": timestamp, "status": "SEM_DADOS", "dados_reais": None})
        except Exception as e:
            print(f"❌ Erro requisição Finnhub ({ticker}): {e}")
            resultados.append({"ativo": cfg["ativo"], "fonte": "FINNHUB", "timestamp": timestamp, "status": "ERRO", "dados_reais": None})
    return resultados

def coletar_mt5_acoes_b3():
    """
    FONTE: MetaTrader 5 (Conexão direta com a corretora local na B3).
    QUANDO OCORRE: Executado no ciclo do pipeline. Requer terminal MT5 aberto/instalado.
    DADOS OBTIDOS: Dados de Tick e Candle Diário (OHLCV + Fechamento Anterior) para as principais ações da B3 (VALE3, PETR4, etc.).
    """
    timestamp = datetime.now().isoformat()
    resultados = []
    
    if not mt5.initialize():
        print("⚠️ [AVISO] Não foi possível inicializar o MT5 para ações B3.")
        return resultados

    try:
        for cfg in ATIVOS_MT5_B3:
            symbol = cfg["ticker_coleta"]
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            
            # Obtém barra diária (TIMEFRAME_D1) para extrair Abertura, Máxima, Mínima e Volume
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 1)

            if info and tick:
                prev_close = float(getattr(info, "session_close", 0.0))
                preco = float(tick.last if tick.last > 0 else (tick.bid if tick.bid > 0 else tick.ask))
                
                open_val = float(rates[0][1]) if rates is not None and len(rates) > 0 else None
                high_val = float(rates[0][2]) if rates is not None and len(rates) > 0 else None
                low_val = float(rates[0][3]) if rates is not None and len(rates) > 0 else None
                volume_val = float(rates[0][5]) if rates is not None and len(rates) > 0 else None

                if preco > 0:
                    var_pct = round(((preco / prev_close) - 1) * 100, 2) if prev_close > 0 else 0.0
                    var_abs = round(preco - prev_close, 2) if prev_close > 0 else 0.0
                    resultados.append({
                        "ativo": cfg["ativo"],
                        "fonte": "MetaTrader5",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": preco,
                            "open": open_val,
                            "high": high_val,
                            "low": low_val,
                            "change_percent": var_pct,
                            "volume": volume_val,
                            "var_abs": var_abs,
                            "fechamento_anterior": prev_close,
                        },
                    })
                else:
                    resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "SEM_DADOS", "dados_reais": None})
            else:
                resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "ERRO", "dados_reais": None})
    finally:
        pass
    return resultados

def capturar_last_do_mt5() -> dict:
    """
    FONTE: Arquivo local gerado pelo coletor MT5 (`Dados_MT5_v2_2.json`).
    QUANDO OCORRE: Chamado especificamente durante a janela de ajuste para extrair o último tick gravado do Mini Índice (WIN).
    """
    resultado = {}

    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            timestamp = dados.get("timestamp", datetime.now().isoformat())
            win_info = dados.get("ativos", {}).get("WIN", {})
            if win_info.get("status") == "OK" or win_info.get("last") is not None:
                last = win_info.get("last")
                contrato = win_info.get("contrato_principal")
                if last is not None and last > 0 and contrato:
                    resultado["WIN"] = {
                        "contrato": contrato,
                        "last": float(last),
                        "timestamp": timestamp,
                        "fonte": "MT5_v2.2",
                    }
                    print(f"   ✅ Last WIN via MT5 v2.2: {last} ({contrato})")
                    return resultado
        except Exception as e:
            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}")

    return resultado

# ============================================================
# ENGINE DE ROTAÇÃO TEMPORAL E PIPELINE PRINCIPAL
# ============================================================

def executar_rotacao_memoria(is_ram_mode=False):
    """
    ROTAÇÃO TEMPORAL DE ARQUIVOS (GERENCIAMENTO DE HISTÓRICO):
    QUANDO OCORRE: Em cada execução do script (a menos que a flag --ram esteja ativa).
    COMO FUNCIONA: Desloca o histórico de 12 arquivos (Coleta_rom-0.json até Coleta_rom-55.json).
                   O arquivo 0 é empurrado para o 1 (5 min atrás), o 1 para o 2 (10 min atrás) e assim por diante.
    """
    if is_ram_mode:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Modo RAM ativado. Ignorando rotação.")
        return FILE_RAM

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executando rotação de memória (12 arquivos)...")
    for i in range(len(ARQUIVOS_ROM) - 1, 0, -1):
        origem = ARQUIVOS_ROM[i - 1]
        destino = ARQUIVOS_ROM[i]
        if os.path.exists(origem):
            shutil.copy2(origem, destino)
    return ARQUIVOS_ROM[0]

def gerar_arquivo_unificado(coletas):
    """
    CONSOLIDADO FINAL:
    Gera o arquivo `DadosAtivosUnificados.json` limpando os tickers e organizando preços
    e variações de todas as fontes em um único objeto de leitura rápida.
    """
    ativos_map = {}
    for item in coletas:
        if not item:
            continue
        ativo_raw = item.get("ativo")
        dados_reais = item.get("dados_reais") or {}
        nome_limpo = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)
        preco = dados_reais.get("close", 0.0) or 0.0
        var = dados_reais.get("change_percent", 0.0) or 0.0
        ativos_map[nome_limpo] = {
            "preco": float(preco),
            "variacao_pct": float(var),
            "ticker_original": ativo_raw,
            "status": item.get("status", "OK"),
        }
    estrutura = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_ativos": len(ativos_map),
        },
        "ativos": ativos_map,
    }
    with open(FILE_UNIFICADO, "w", encoding="utf-8") as f:
        json.dump(estrutura, f, indent=4, ensure_ascii=False)
    print(f"✅ Arquivo unificado salvo em: {FILE_UNIFICADO}")

def executar_pipeline_coleta():
    """
    FLUXO DE EXECUÇÃO DO PIPELINE:
    Orquestra a chamada de todos os coletores e salva os resultados no disco/memória.
    """
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando extração de dados brutos...")
    coletas = []

    # 1. COLETA: PTAX Oficial / Dólar (BACEN SGS)
    coletas.append(coletar_bacen_ptax())

    # 2. COLETA: Ajuste Oficial de Mini Índice (TradingView - Janela das 19:00 às 08:50)
    coletas.extend(coletar_ajuste_oficial())

    # 3. COLETA: Índices Globais, Commodities e Forex (TradingView Scanner API)
    coletas.extend(coletar_tradingview())

    # 4. COLETA: ADRs Brasileiras na BMF/NYSE e EWZ (Finnhub API)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando via Finnhub...")
    coletas.extend(coletar_finnhub())

    # ------------------------------------------------------------
    # 5. COLETA METATRADER 5 (1 ÚNICO CICLO DE CONEXÃO INTEGRADA)
    # ------------------------------------------------------------
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executando coleta unificada MT5...")
    
    # 5.1 FUTUROS B3: Importa o módulo externo 'Coletor_MT5_v2_2' para obter cotações de WIN, WDO e DI1
    dados_futuros_mt5 = {}
    try:
        from Coletor_MT5_v2_2 import executar_coleta_mt5_v2
        res_v2 = executar_coleta_mt5_v2()
        if res_v2 and res_v2.get("status") == "OK":
            dados_futuros_mt5 = res_v2.get("ativos", {})
    except Exception as e:
        print(f"⚠️ Falha na execução do Coletor_MT5_v2_2: {e}")

    # Mapeia e estrutura os contratos futuros obtidos da rotina MT5
    mapeamento_futuros = [
        ("WIN", "BMFBOVESPA:WIN1!"),
        ("WDO", "BMFBOVESPA:WDO1!"),
        ("DI1", "DI1_FUT")
    ]

    for prefixo, ativo_bruto in mapeamento_futuros:
        info = dados_futuros_mt5.get(prefixo, {})
        last_val = info.get("last")
        if last_val:
            close_val = float(last_val)
            prev_close = info.get("prev_close") or info.get("session_close") or 0.0
            var_abs = round(close_val - prev_close, 2) if prev_close else 0.0
            var_pct = round(((close_val / prev_close) - 1) * 100, 2) if prev_close and prev_close > 0 else 0.0
            
            # Registro padrão do Ativo Futuro
            coletas.append({
                "ativo": ativo_bruto,
                "fonte": "MT5_v2.2",
                "timestamp": datetime.now().isoformat(),
                "status": "OK",
                "dados_reais": {
                    "close": close_val,
                    "open": float(info.get("open")) if info.get("open") is not None else None,
                    "high": float(info.get("high")) if info.get("high") is not None else None,
                    "low": float(info.get("low")) if info.get("low") is not None else None,
                    "change_percent": var_pct,
                    "volume": float(info.get("volume")) if info.get("volume") is not None else None,
                    "var_abs": var_abs,
                    "fechamento_anterior": prev_close,
                },
            })

            # Registro dedicado especificamente para guardar o FECHAMENTO ANTERIOR do WIN
            if prefixo == "WIN" and prev_close > 0:
                coletas.append({
                    "ativo": "WIN_PREV_CLOSE",
                    "fonte": "MT5_v2.2",
                    "timestamp": datetime.now().isoformat(),
                    "status": "OK",
                    "dados_reais": {
                        "close": float(prev_close),
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": 0.0,
                        "volume": None,
                        "var_abs": 0.0,
                        "fechamento_anterior": float(prev_close),
                    },
                })

    # 5.2 AÇÕES B3: Coleta cotações à vista (VALE3, PETR4, etc.) via MT5
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando ações B3 via MT5...")
    coletas.extend(coletar_mt5_acoes_b3())

    # Encerra com segurança a instância da biblioteca do MetaTrader 5
    try:
        mt5.shutdown()
    except Exception:
        pass

    # 6. COLETA: Último Tick (LAST TICK) do WIN na janela de ajuste (se ativo)
    if esta_na_janela_ajuste():
        lasts = capturar_last_do_mt5()
        if lasts and "WIN" in lasts:
            coletas.append({
                "ativo": "WIN_LAST_TICK",
                "fonte": lasts["WIN"].get("fonte", "MT5"),
                "timestamp": datetime.now().isoformat(),
                "status": "OK",
                "dados_reais": {
                    "close": lasts["WIN"]["last"],
                    "open": None,
                    "high": None,
                    "low": None,
                    "change_percent": None,
                    "volume": None,
                },
            })

    # ============================================================
    # GRAVAÇÃO DOS DADOS NOS ARQUIVOS JSON
    # ============================================================
    conteudo_saida = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "RAM" if is_ram else "PADRAO_ROTATIVO",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": os.path.basename(arquivo_destino),
        },
        "coletas": coletas,
    }

    # Salva no arquivo rotativo correspondente (Coleta_rom-X.json)
    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)

    # Mantém uma cópia atualizada em Coleta_ram.json (se não estiver em modo RAM exclusivo)
    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)

    # Gera a visualização unificada consolidada
    gerar_arquivo_unificado(coletas)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline concluído com sucesso!")

if __name__ == "__main__":
    executar_pipeline_coleta()