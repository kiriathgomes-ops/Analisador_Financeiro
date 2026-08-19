# ============================================================
# ARQUIVO: Coletor.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados (BACEN SGS 10813 + TV + B3 WIN Separados)
#         Engine de Rotação Temporal de Memória e
#         Geração do Arquivo Unificado dos 24 Ativos Mapeados.
# MODIFICAÇÃO FINAL: Integração com MT5 para capturar o LAST TICK (WIN)
#                    apenas dentro da janela de ajuste (19:00 - 08:50).
#
# ATUALIZAÇÃO 16/08/2026:
#   - Integração prioritária com Coletor_MT5_v2_2 (seleção dinâmica de contrato)
#   - Fallback automático para o coletor antigo (Coletor_MT5.py)
#   - Preservação total da V1 (nenhum arquivo antigo foi removido)
#   - ROTAÇÃO EXPANDIDA PARA 12 ARQUIVOS (0, 5, 10, ..., 55 min) → 60 min de histórico
#
# ATUALIZAÇÃO 18/08/2026:
#   - Substituição de coletas TradingView por Finnhub (ativos mais estáveis)
#   - Inclusão de novos ativos B3 via MetaTrader 5 (VALE3, PETR4, ITUB4, BBAS3, BBDC4, B3SA3)
#   - Mantida toda a estrutura original (rotação, RAM/ROM, unificado, janela de ajuste)
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
# CONFIGURAÇÕES GERAIS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
os.makedirs(COLETAS_DIR, exist_ok=True)

load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# ============================================================
# ARQUIVOS DE ROTAÇÃO TEMPORAL (12 arquivos - 60 min de histórico)
# ============================================================

ARQUIVOS_ROM = [
    os.path.join(COLETAS_DIR, f"Coleta_rom-{i}.json") for i in range(0, 60, 5)
]
FILE_ROM0 = ARQUIVOS_ROM[0]

FILE_RAM = os.path.join(COLETAS_DIR, "Coleta_ram.json")
FILE_UNIFICADO = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")

# Arquivos gerados pelos coletores MT5 (v1 e v2.2)
FILE_MT5 = os.path.join(COLETAS_DIR, "Dados_MT5.json")
FILE_MT5_V2 = os.path.join(COLETAS_DIR, "Dados_MT5_v2_2.json")

# Geração dinâmica do ticker de minério de ferro (2º mês)
ANO_ATUAL = datetime.now().year
TICKER_FEF2 = f"SGX:FEFU{ANO_ATUAL}"

# ============================================================
# LISTA DE ATIVOS COLETADOS VIA TRADINGVIEW SCANNER
# ============================================================

TICKERS_TRADINGVIEW = [
    "BMFBOVESPA:DI1F2027",
    "BMFBOVESPA:DI1F2029",
    "TVC:VIX",
    "SGX:FEF1!",
    TICKER_FEF2,
    "NYMEX:CL1!",
    "CME_MINI:ES1!",
    "CME_MINI:NQ1!",
    "TVC:DXY",
    "FX_IDC:USDMXN",
    "TVC:GOLD",
    "FX_IDC:USDBRL",
]

# ============================================================
# ATIVOS COLETADOS VIA FINNHUB (substituem parte do TradingView)
# ============================================================

ATIVOS_FINNHUB = [
    {"ativo": "AMEX:EWZ", "ticker_coleta": "EWZ", "id_fixo": "EWZ", "categoria": "Índices Globais"},
    {"ativo": "NYSE:VALE", "ticker_coleta": "VALE", "id_fixo": "VALE_ADR", "categoria": "ADRs B3"},
    {"ativo": "NYSE:PBR", "ticker_coleta": "PBR", "id_fixo": "PETR_ADR", "categoria": "ADRs B3"},
    {"ativo": "NYSE:ITUB", "ticker_coleta": "ITUB", "id_fixo": "ITUB_ADR", "categoria": "ADRs B3"},
    {"ativo": "OTC:BDORY", "ticker_coleta": "BDORY", "id_fixo": "BBAS_ADR", "categoria": "ADRs B3"},
    {"ativo": "NYSE:BBD", "ticker_coleta": "BBD", "id_fixo": "BBD_ADR", "categoria": "ADRs B3"},
    {"ativo": "OTC:BOLSY", "ticker_coleta": "BOLSY", "id_fixo": "B3_ADR", "categoria": "ADRs B3"},
]

# ============================================================
# ATIVOS B3 COLETADOS VIA METATRADER 5 (ações diretas)
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
# MAPEAMENTO DE TICKERS PARA NOMES AMIGÁVEIS (JSON UNIFICADO)
# ============================================================

MAPEAMENTO_TICKERS = {
    "USD_PTAX": "USD_PTAX",
    "B3_AJUSTE_WIN": "WIN_AJUSTE",
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "BMFBOVESPA:DI1F2027": "DI1_2027",
    "BMFBOVESPA:DI1F2029": "DI1_2029",
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
# FUNÇÕES AUXILIARES
# ============================================================

def esta_na_janela_ajuste() -> bool:
    """Retorna True se o horário atual estiver dentro da janela de ajuste (19:00 - 08:50)."""
    agora = datetime.now().time()
    return agora >= time(19, 0, 0) or agora <= time(8, 50, 0)

# ============================================================
# COLETORES DE DADOS
# ============================================================

# ---- BACEN PTAX (com fallback TradingView) ----

def coletar_bacen_ptax():
    """Coleta a taxa PTAX oficial via API SGS do BACEN (série 10813). Fallback para TradingView."""
    timestamp = datetime.now().isoformat()
    url_sgs = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req_sgs = urllib.request.Request(
        url_sgs,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )

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

    # Fallback: TradingView Scanner
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

# ---- AJUSTE OFICIAL (somente na janela) ----

def coletar_ajuste_oficial():
    """
    Coleta o preço de ajuste oficial do WIN (B3_AJUSTE_WIN) apenas entre 19:00 e 08:50.
    Fora desse horário, retorna o último valor salvo em cache (RAM/ROM0).
    """
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()
    hora_inicio = time(19, 0, 0)
    hora_fim = time(8, 50, 0)

    # --- FORA DA JANELA: busca cache ---
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
        # Se não encontrou cache
        return [{
            "ativo": "B3_AJUSTE_WIN",
            "fonte": "NENHUM_DADO",
            "timestamp": timestamp,
            "status": "FORA_JANELA_SEM_CACHE",
            "dados_reais": None,
        }]

    # --- DENTRO DA JANELA: coleta ao vivo via TradingView direct ---
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

# ---- TRADINGVIEW SCANNER (demais ativos) ----

def coletar_tradingview():
    """Coleta os ativos da lista TICKERS_TRADINGVIEW via API Scanner do TradingView."""
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

# ---- FINNHUB (ADRs e ETF) ----

def coletar_finnhub():
    """Coleta ativos via API Finnhub (EWZ + ADRs B3). Requer chave no .env."""
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
                        "open": None,
                        "high": None,
                        "low": None,
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

# ---- AÇÕES B3 VIA METATRADER 5 ----

def coletar_mt5_acoes_b3():
    """Coleta as ações B3 (VALE3, PETR4, etc.) via MetaTrader 5."""
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
            if info and tick:
                prev_close = float(getattr(info, "session_close", 0.0))
                preco = float(tick.last if tick.last > 0 else (tick.bid if tick.bid > 0 else tick.ask))
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
                            "open": None,
                            "high": None,
                            "low": None,
                            "change_percent": var_pct,
                            "volume": None,
                            "var_abs": var_abs,
                            "fechamento_anterior": prev_close,
                        },
                    })
                else:
                    resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "SEM_DADOS", "dados_reais": None})
            else:
                resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "ERRO", "dados_reais": None})
    finally:
        mt5.shutdown()
    return resultados

# ---- WIN_WDO_FUT VIA METATRADER 5 (substitui TradingView) ----
def coletar_futuro_mt5(prefixo: str, ativo_bruto: str) -> dict:
    """
    Coleta o preço do contrato principal de um futuro B3 via MT5.
    prefixo: "WIN" ou "WDO"
    ativo_bruto: "BMFBOVESPA:WIN1!" ou "BMFBOVESPA:WDO1!"
    Retorna no formato padrão do Coletor.py (mesmo da Finnhub).
    """
    timestamp = datetime.now().isoformat()

    # 1. Tenta via Coletor_MT5_v2_2 (se disponível)
    try:
        from Coletor_MT5_v2_2 import executar_coleta_mt5_v2
        dados = executar_coleta_mt5_v2()
        if dados and dados.get("status") == "OK":
            ativos = dados.get("ativos", {})
            info = ativos.get(prefixo, {})
            if info.get("last"):
                prev_close = info.get("prev_close") or info.get("session_close")
                if prev_close is None:
                    contrato = info.get("contrato_principal")
                    if contrato:
                        mt5_ok = mt5.initialize()
                        if mt5_ok:
                            try:
                                info_sym = mt5.symbol_info(contrato)
                                if info_sym:
                                    prev_close = float(getattr(info_sym, "session_close", 0.0))
                            except:
                                pass
                            finally:
                                mt5.shutdown()
                close_val = float(info["last"])
                var_abs = round(close_val - prev_close, 2) if prev_close else 0.0
                var_pct = round(((close_val / prev_close) - 1) * 100, 2) if prev_close and prev_close > 0 else 0.0
                return {
                    "ativo": ativo_bruto,
                    "fonte": "MT5_v2.2",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": close_val,
                        "open": float(info.get("open")) if info.get("open") else None,
                        "high": float(info.get("high")) if info.get("high") else None,
                        "low": float(info.get("low")) if info.get("low") else None,
                        "change_percent": var_pct,
                        "volume": float(info.get("volume")) if info.get("volume") else None,
                        "var_abs": var_abs,
                        "fechamento_anterior": prev_close,
                    },
                }
    except (ImportError, Exception):
        pass

    # 2. Tenta leitura direta do MT5 (tick + candle diário)
    mt5_ok = mt5.initialize()
    if mt5_ok:
        try:
            # Lista de possíveis contratos (ajuste conforme necessidade)
            # Usa o prefixo dinâmico: ex: "WINV26", "WDOZ26" etc.
            # Vamos buscar todos os contratos com o prefixo e selecionar o mais próximo
            simbolos = mt5.symbols_get()
            if simbolos:
                candidatos = []
                for s in simbolos:
                    nome = s.name
                    if nome.startswith(prefixo) and "$" not in nome and "@" not in nome:
                        # Filtra opções
                        if "C" in nome[len(prefixo):] or "P" in nome[len(prefixo):]:
                            continue
                        expiracao = getattr(s, "expiration_time", 0)
                        if expiracao and expiracao > datetime.now().timestamp():
                            tick = mt5.symbol_info_tick(nome)
                            if tick and tick.last > 0:
                                candidatos.append((nome, expiracao, tick, s))
                if candidatos:
                    # Ordena por data de expiração (mais próximo primeiro)
                    candidatos.sort(key=lambda x: x[1])
                    nome, _, tick, info_sym = candidatos[0]
                    prev_close = float(getattr(info_sym, "session_close", 0.0))
                    close_val = float(tick.last)
                    var_abs = round(close_val - prev_close, 2) if prev_close else 0.0
                    var_pct = round(((close_val / prev_close) - 1) * 100, 2) if prev_close and prev_close > 0 else 0.0
                    rates = mt5.copy_rates_from_pos(nome, mt5.TIMEFRAME_D1, 0, 1)
                    open_val = float(rates[0][1]) if rates is not None and len(rates) > 0 else None
                    high_val = float(rates[0][2]) if rates is not None and len(rates) > 0 else None
                    low_val = float(rates[0][3]) if rates is not None and len(rates) > 0 else None
                    volume = float(tick.volume) if tick.volume else None
                    return {
                        "ativo": ativo_bruto,
                        "fonte": "MetaTrader5_Direto",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": close_val,
                            "open": open_val,
                            "high": high_val,
                            "low": low_val,
                            "change_percent": var_pct,
                            "volume": volume,
                            "var_abs": var_abs,
                            "fechamento_anterior": prev_close,
                        },
                    }
        except Exception as e:
            print(f"⚠️ Erro ao ler {prefixo} do MT5: {e}")
        finally:
            mt5.shutdown()

    # 3. Fallback: arquivos de cache (v2.2 e v1)
    for file_path in [FILE_MT5_V2, FILE_MT5]:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                if "ativos" in dados:
                    info = dados["ativos"].get(prefixo, {})
                    if info.get("last"):
                        prev_close = info.get("prev_close") or info.get("session_close") or 0.0
                        close_val = float(info["last"])
                        var_abs = round(close_val - prev_close, 2) if prev_close else 0.0
                        var_pct = round(((close_val / prev_close) - 1) * 100, 2) if prev_close and prev_close > 0 else 0.0
                        return {
                            "ativo": ativo_bruto,
                            "fonte": "MT5_CACHE_v2",
                            "timestamp": timestamp,
                            "status": "OK",
                            "dados_reais": {
                                "close": close_val,
                                "open": None,
                                "high": None,
                                "low": None,
                                "change_percent": var_pct,
                                "volume": None,
                                "var_abs": var_abs,
                                "fechamento_anterior": prev_close,
                            },
                        }
                if "contratos" in dados:
                    for nome_contrato, info in dados["contratos"].items():
                        if nome_contrato.startswith(prefixo):
                            last = info.get("last")
                            if last:
                                return {
                                    "ativo": ativo_bruto,
                                    "fonte": "MT5_CACHE_v1",
                                    "timestamp": timestamp,
                                    "status": "OK",
                                    "dados_reais": {
                                        "close": float(last),
                                        "open": None,
                                        "high": None,
                                        "low": None,
                                        "change_percent": 0.0,
                                        "volume": None,
                                        "var_abs": 0.0,
                                        "fechamento_anterior": 0.0,
                                    },
                                }
            except Exception:
                continue

    # Se nada funcionou
    return {
        "ativo": ativo_bruto,
        "fonte": "MT5",
        "timestamp": timestamp,
        "status": "ERRO",
        "dados_reais": None,
    }





# ---- LAST TICK (captura dos arquivos MT5, somente na janela) ----

def capturar_last_do_mt5() -> dict:
    """
    Extrai o último tick (last) do WIN a partir dos arquivos gerados pelos coletores MT5.
    Prioridade: Dados_MT5_v2_2.json → Dados_MT5.json.
    Retorna dicionário com contrato, last, timestamp e fonte.
    """
    resultado = {}

    # 1. Formato v2.2
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

    # 2. Formato v1
    if os.path.exists(FILE_MT5):
        try:
            with open(FILE_MT5, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            contratos = dados.get("contratos", {})
            timestamp = dados.get("timestamp", datetime.now().isoformat())
            for contrato in ["WINQ26", "WINV26", "WINZ26"]:
                if contrato in contratos:
                    last = contratos[contrato].get("last")
                    if last is not None and last > 0:
                        resultado["WIN"] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v1",
                        }
                        print(f"   ✅ Last WIN via MT5 v1: {last} ({contrato})")
                        return resultado
        except Exception as e:
            print(f"[ERRO] Falha ao ler Dados_MT5.json: {e}")

    print("[AVISO] Nenhum arquivo MT5 com last encontrado.")
    return resultado

# ============================================================
# ENGINE DE ROTAÇÃO TEMPORAL
# ============================================================

def executar_rotacao_memoria(is_ram_mode=False):
    """
    Executa a rotação dos 12 arquivos (janela móvel de 60 minutos).
    Se is_ram_mode=True, retorna o caminho do arquivo RAM sem rotacionar.
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
            print(f"  └─ Rotação: {os.path.basename(origem)} ──> {os.path.basename(destino)}")
        else:
            print(f"  └─ Aviso: {os.path.basename(origem)} não encontrado, pulando.")
    return ARQUIVOS_ROM[0]

# ============================================================
# GERADOR DO ARQUIVO UNIFICADO
# ============================================================

def gerar_arquivo_unificado(coletas):
    """Gera o arquivo DadosAtivosUnificados.json com os preços e variações dos ativos."""
    ativos_map = {}
    for item in coletas:
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

# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def executar_pipeline_coleta():
    """Executa todas as etapas de coleta, rotação e geração do unificado."""
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando extração de dados brutos...")
    coletas = []

    # 1. BACEN PTAX
    coletas.append(coletar_bacen_ptax())

    # 2. Ajuste Oficial (condicional)
    coletas.extend(coletar_ajuste_oficial())

    # 3. TradingView Scanner (demais ativos)
    coletas.extend(coletar_tradingview())

    # 4. Finnhub (ADRs + ETF)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando via Finnhub...")
    finnhub_dados = coletar_finnhub()
    coletas.extend(finnhub_dados)
    print(f"   ✅ Finnhub: {len([d for d in finnhub_dados if d.get('status') == 'OK'])} ativos OK")

    # 5. Ações B3 via MT5
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando ações B3 via MetaTrader 5...")
    mt5_b3_dados = coletar_mt5_acoes_b3()
    coletas.extend(mt5_b3_dados)
    print(f"   ✅ MT5 Ações B3: {len([d for d in mt5_b3_dados if d.get('status') == 'OK'])} ativos OK")

    # 5.5 Coleta dos futuros B3 via MT5 (WIN e WDO)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando WIN_FUT via MT5...")
    win_fut = coletar_futuro_mt5("WIN", "BMFBOVESPA:WIN1!")
    if win_fut and win_fut.get("status") == "OK":
        coletas.append(win_fut)
        print(f"   ✅ WIN_FUT MT5: {win_fut['dados_reais']['close']}")
    else:
        print("   ⚠️ WIN_FUT MT5 falhou. Adicionando com status ERRO.")
        coletas.append(win_fut)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando WDO_FUT via MT5...")
    wdo_fut = coletar_futuro_mt5("WDO", "BMFBOVESPA:WDO1!")
    if wdo_fut and wdo_fut.get("status") == "OK":
        coletas.append(wdo_fut)
        print(f"   ✅ WDO_FUT MT5: {wdo_fut['dados_reais']['close']}")
    else:
        print("   ⚠️ WDO_FUT MT5 falhou. Adicionando com status ERRO.")
        coletas.append(wdo_fut)
    
    # 6. LAST TICK (apenas na janela de ajuste)
    if esta_na_janela_ajuste():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Capturando LAST TICK via MT5...")
        # Tenta executar o coletor v2.2 para gerar o arquivo atualizado
        mt5_ok = False
        try:
            from Coletor_MT5_v2_2 import executar_coleta_mt5_v2
            dados_mt5 = executar_coleta_mt5_v2()
            if dados_mt5 and dados_mt5.get("status") == "OK":
                print("   ✅ MT5 v2.2 coletado com sucesso.")
                mt5_ok = True
        except ImportError:
            print("   ⚠️ Módulo Coletor_MT5_v2_2 não encontrado.")
        except Exception as e:
            print(f"   ⚠️ Erro ao executar Coletor_MT5_v2_2: {e}")

        if not mt5_ok:
            try:
                from Coletor_MT5 import executar_coleta_mt5
                dados_mt5 = executar_coleta_mt5()
                if dados_mt5 and dados_mt5.get("status") == "OK":
                    print("   ✅ MT5 v1 (fallback) coletado com sucesso.")
            except Exception as e:
                print(f"   ⚠️ Erro ao executar Coletor_MT5 (v1): {e}")

        # Extrai o last dos arquivos
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
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fora da janela. LAST TICK NÃO coletado.")

    # Monta estrutura de saída
    conteudo_saida = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "RAM" if is_ram else "PADRAO_ROTATIVO",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": os.path.basename(arquivo_destino),
        },
        "coletas": coletas,
    }

    # Grava arquivo de rotação
    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)

    # Grava RAM (cópia independente)
    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)
        print(f"✅ Cópia independente gerada em: {FILE_RAM}")

    # Gera o unificado
    gerar_arquivo_unificado(coletas)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coleta e Unificação concluídas!")
    print(f"Total de itens processados: {len(coletas)} | Arquivo: {os.path.basename(arquivo_destino)}\n")

# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    print("============================================================")
    print(" FASE 1 & 2: MOTOR DE INGESTÃO E ROTAÇÃO DE DADOS")
    print(" (TradingView + Finnhub + MT5 Ações B3 + LAST TICK)")
    print("============================================================")
    executar_pipeline_coleta()