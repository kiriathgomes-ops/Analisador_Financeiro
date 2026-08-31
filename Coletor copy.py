# ============================================================
# ARQUIVO: Coletor.py
# DATA: 30/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados (BACEN SGS 10813 + TV + B3 WIN/WDO Separados)
#         Engine de Rotação Temporal de Memória e
#         Geração do Arquivo Unificado dos Ativos Mapeados.
# MODIFICAÇÃO FINAL: Integração com MT5 para capturar o LAST TICK (WIN/WDO)
#                    apenas dentro da janela de ajuste (19:00 - 08:50).
#
# ATUALIZAÇÃO 16/08/2026:
#   - Integração prioritária com Coletor_MT5_v2_2 (seleção dinâmica de contrato)
#   - Fallback automático para o coletor antigo (Coletor_MT5.py)
#   - Preservação total da V1 (nenhum arquivo antigo foi removido)
#   - ROTAÇÃO EXPANDIDA PARA 12 ARQUIVOS (0, 5, 10, ..., 55 min) → 60 min de histórico
#
# ATUALIZAÇÃO 18/08/2026 (Opção A):
#   - ADRs + EWZ passam a ser coletados via Finnhub (mais estável)
#   - Futuros ES e NQ CONTINUAM via TradingView (preços reais dos futuros)
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
from pathlib import Path

import MetaTrader5 as mt5
import requests

# ------------------------------------------------------------
# CONFIGURAÇÃO CENTRALIZADA (A2 — config.py)
# ------------------------------------------------------------
from config import (
    BASE_DIR,
    COLETAS_DIR,
    ARQUIVOS_ROM,
    FILE_ROM0,
    FILE_RAM,
    FILE_UNIFICADO,
    FILE_MT5,
    FILE_MT5_V2,
    FINNHUB_API_KEY,
    TICKER_FEF2,
    TICKERS_TRADINGVIEW,
    ATIVOS_FINNHUB,
    ATIVOS_MT5_B3,
    MAPEAMENTO_TICKERS,
    TIMEOUT_TRADINGVIEW,
    TIMEOUT_FINNHUB,
    TIMEOUT_BACEN,
    esta_na_janela_ajuste,
    JANELA_AJUSTE_INICIO,
    JANELA_AJUSTE_FIM,
)

# Compatibilidade: paths como str para código legado (os.path / open)
BASE_DIR = str(BASE_DIR)
COLETAS_DIR = str(COLETAS_DIR)
ARQUIVOS_ROM = [str(p) for p in ARQUIVOS_ROM]
FILE_ROM0 = str(FILE_ROM0)
FILE_RAM = str(FILE_RAM)
FILE_UNIFICADO = str(FILE_UNIFICADO)
FILE_MT5 = str(FILE_MT5)
FILE_MT5_V2 = str(FILE_MT5_V2)

# Alias id_limpo ← id_interno (config usa id_interno)
for _cfg in ATIVOS_FINNHUB + ATIVOS_MT5_B3:
    if "id_interno" in _cfg and "id_limpo" not in _cfg:
        _cfg["id_limpo"] = _cfg["id_interno"]

os.makedirs(COLETAS_DIR, exist_ok=True)
ANO_ATUAL = datetime.now().year

# TICKERS_TRADINGVIEW, ATIVOS_FINNHUB, ATIVOS_MT5_B3, MAPEAMENTO_TICKERS
# e esta_na_janela_ajuste() vêm de config.py (A2).

# ------------------------------------------------------------
# FUNÇÃO PARA CAPTURAR LAST DO MT5
# ------------------------------------------------------------
def capturar_last_do_mt5() -> dict:
    """
    Extrai o 'last' dos contratos principais de WIN e WDO.

    Prioridade de leitura:
      1. Dados_MT5_v2_2.json  (formato novo - seleção dinâmica por volume/vencimento)
      2. Dados_MT5.json       (formato antigo - lista fixa)

    Retorna dict no formato:
      {
        "WIN": {"contrato": "WINV26", "last": 128450.0, "timestamp": "..."},
        "WDO": {"contrato": "WDOV26", "last": 5.432, "timestamp": "..."}
      }
    """
    resultado = {}

    # ----------------------------------------------------------
    # 1. Tenta o formato novo (v2.2) — preferencial
    # ----------------------------------------------------------
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                dados = json.load(f)

            timestamp = dados.get("timestamp", datetime.now().isoformat())
            ativos = dados.get("ativos", {})

            for prefixo in ("WIN", "WDO"):
                info_ativo = ativos.get(prefixo, {})
                if info_ativo.get("status") == "OK" or info_ativo.get("last") is not None:
                    last = info_ativo.get("last")
                    contrato = info_ativo.get("contrato_principal")
                    if last is not None and last > 0 and contrato:
                        resultado[prefixo] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v2.2",
                        }

            if resultado:
                if "WIN" in resultado:
                    print(f"   ✅ Last WIN via MT5 v2.2: {resultado['WIN']['last']} ({resultado['WIN']['contrato']})")
                if "WDO" in resultado:
                    print(f"   ✅ Last WDO via MT5 v2.2: {resultado['WDO']['last']} ({resultado['WDO']['contrato']})")
                return resultado

        except Exception as e:
            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}. Tentando formato antigo...")

    # ----------------------------------------------------------
    # 2. Fallback: formato antigo (Dados_MT5.json)
    # ----------------------------------------------------------
    if not os.path.exists(FILE_MT5):
        print("[AVISO] Nenhum arquivo MT5 encontrado (v2.2 nem v1). Não será possível capturar o last.")
        return resultado

    try:
        with open(FILE_MT5, "r", encoding="utf-8") as f:
            dados = json.load(f)

        contratos = dados.get("contratos", {})
        timestamp = dados.get("timestamp", datetime.now().isoformat())

        # Lista de prioridade do formato antigo (mantida por compatibilidade)
        mapeamento_contratos = {
            "WIN": ["WINQ26", "WINV26", "WINZ26"],
            "WDO": ["WDOQ26", "WDOV26", "WDOZ26"],
        }

        for ativo, lista in mapeamento_contratos.items():
            for contrato in lista:
                if contrato in contratos:
                    info = contratos[contrato]
                    last = info.get("last")
                    if last is not None and last > 0:
                        resultado[ativo] = {
                            "contrato": contrato,
                            "last": float(last),
                            "timestamp": timestamp,
                            "fonte": "MT5_v1",
                        }
                        break

        if "WIN" in resultado:
            print(f"   ✅ Last WIN via MT5 v1: {resultado['WIN']['last']} ({resultado['WIN']['contrato']})")
        if "WDO" in resultado:
            print(f"   ✅ Last WDO via MT5 v1: {resultado['WDO']['last']} ({resultado['WDO']['contrato']})")

        return resultado

    except Exception as e:
        print(f"[ERRO] Falha ao ler Dados_MT5.json (formato antigo): {e}")
        return {}


# ------------------------------------------------------------
# FUNÇÕES DE COLETA FINNHUB (ADRs + EWZ)
# ------------------------------------------------------------
def coletar_finnhub():
    """
    Coleta os ativos configurados em ATIVOS_FINNHUB via API Finnhub.
    Retorna lista no mesmo formato das outras funções de coleta do Coletor.py.
    """
    timestamp = datetime.now().isoformat()
    resultados = []

    if not FINNHUB_API_KEY:
        print("⚠️ [AVISO] Chave 'FINNHUB_API_KEY' não encontrada no arquivo .env")
        return resultados

    for cfg in ATIVOS_FINNHUB:
        ticker = cfg["ticker_coleta"]
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"

        try:
            response = requests.get(url, timeout=5)
            res = response.json()

            if "error" in res:
                print(f"⚠️ Erro de API Finnhub ({ticker}): {res['error']}")
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "ERRO",
                    "dados_reais": None,
                })
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
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "SEM_DADOS",
                    "dados_reais": None,
                })

        except Exception as e:
            print(f"❌ Erro de requisição Finnhub ({ticker}): {e}")
            resultados.append({
                "ativo": cfg["ativo"],
                "fonte": "FINNHUB",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            })

    return resultados


# ------------------------------------------------------------
# FUNÇÃO DE COLETA DOS NOVOS ATIVOS B3 VIA METATRADER 5
# ------------------------------------------------------------
def coletar_mt5_acoes_b3():
    """
    Coleta as ações B3 listadas em ATIVOS_MT5_B3 via MetaTrader 5.
    Retorna lista no formato padrão do Coletor.py.
    """
    timestamp = datetime.now().isoformat()
    resultados = []

    mt5_ok = mt5.initialize()
    if not mt5_ok:
        print("⚠️ [AVISO] Não foi possível inicializar o MetaTrader 5 para ações B3.")
        return resultados

    try:
        for cfg in ATIVOS_MT5_B3:
            symbol = cfg["ticker_coleta"]
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)

            if info and tick:
                prev_close = float(getattr(info, "session_close", 0.0))
                preco = float(
                    tick.last
                    if tick.last > 0
                    else float(tick.bid if tick.bid > 0 else tick.ask)
                )

                if preco > 0:
                    var_pct = (
                        round(((preco / prev_close) - 1) * 100, 2)
                        if prev_close > 0
                        else 0.0
                    )
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
                    resultados.append({
                        "ativo": cfg["ativo"],
                        "fonte": "MetaTrader5",
                        "timestamp": timestamp,
                        "status": "SEM_DADOS",
                        "dados_reais": None,
                    })
            else:
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "MetaTrader5",
                    "timestamp": timestamp,
                    "status": "ERRO",
                    "dados_reais": None,
                })
    finally:
        mt5.shutdown()

    return resultados


# ------------------------------------------------------------
# FUNÇÕES DE COLETA DE DADOS (FASE 1)
# ------------------------------------------------------------

def coletar_bacen_ptax():
    """Coleta a PTAX oficial no Bacen via API SGS (Série 10813) com fallback via TradingView."""
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
        with urllib.request.urlopen(
            req_sgs, context=ctx, timeout=10
        ) as response:
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

    # Fallback TradingView
    try:
        url_tv = "https://scanner.tradingview.com/global/scan"
        payload = {
            "symbols": {"tickers": ["FX_IDC:USDBRL"]},
            "columns": ["close"],
        }
        req_tv = urllib.request.Request(
            url_tv,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
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
                    "dados_reais": {
                        "close": float(vals[0]),
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
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
    Coleta os valores de Ajuste Oficial APENAS entre 19:00 e 08:50.
    Fora desse horário, busca o último valor salvo no cache (RAM/ROM) para não quebrar o sistema.
    """
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()

    # Limites de horário (Brasília) — centralizados em config.py
    hora_inicio = JANELA_AJUSTE_INICIO  # 19:00
    hora_fim = JANELA_AJUSTE_FIM        # 08:50

    # --- LÓGICA DE HORÁRIO ---
    # Se estiver entre 08:50 e 19:00, NÃO faz a coleta ao vivo
    if hora_fim < hora_atual < hora_inicio:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Fora da janela de ajuste (19:00 - 08:50). Buscando último cache...")
        
        # Tenta carregar o último ajuste salvo no arquivo de RAM (ou ROM0)
        cache_encontrado = []
        for arquivo_cache in [FILE_RAM, FILE_ROM0]:
            if os.path.exists(arquivo_cache):
                try:
                    with open(arquivo_cache, 'r', encoding='utf-8') as f:
                        dados_cache = json.load(f)
                        itens = dados_cache.get("coletas", [])
                        # Filtra os ajustes
                        for item in itens:
                            if item.get("ativo") in ["B3_AJUSTE_WIN", "B3_AJUSTE_WDO"]:
                                cache_encontrado.append(item)
                    if cache_encontrado:
                        break
                except:
                    continue
        
        if cache_encontrado:
            # Retorna os dados do cache, mas marca a fonte como "CACHE"
            for item in cache_encontrado:
                item["fonte"] = "CACHE_DISCO (Fora da janela)"
                item["timestamp"] = timestamp
            return cache_encontrado
        else:
            print("   ⚠️ Nenhum cache de ajuste encontrado. Retornando dados vazios.")
            return [
                {
                    "ativo": "B3_AJUSTE_WIN",
                    "fonte": "NENHUM_DADO",
                    "timestamp": timestamp,
                    "status": "FORA_JANELA_SEM_CACHE",
                    "dados_reais": None
                },
                {
                    "ativo": "B3_AJUSTE_WDO",
                    "fonte": "NENHUM_DADO",
                    "timestamp": timestamp,
                    "status": "FORA_JANELA_SEM_CACHE",
                    "dados_reais": None
                }
            ]

    # --- SE ESTIVER DENTRO DA JANELA (19:00 até 08:50) ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Dentro da janela de ajuste. Coletando da API...")
    headers = {"User-Agent": "Mozilla/5.0"}

    simbolos = [
        {"ativo": "B3_AJUSTE_WIN", "ticker": "BMFBOVESPA:WIN1!"},
        {"ativo": "B3_AJUSTE_WDO", "ticker": "BMFBOVESPA:WDO1!"},
    ]

    resultados = []
    for item in simbolos:
        url = f"https://scanner.tradingview.com/symbol?symbol={item['ticker']}&fields=close,change"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                close_val = res.get("close")
                change_val = res.get("change", 0.0)

                resultados.append({
                    "ativo": item["ativo"],
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
                })
        except Exception as e:
            print(f"   ❌ Erro ao coletar {item['ativo']}: {e}")
            resultados.append({
                "ativo": item["ativo"],
                "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            })
    
    return resultados


def coletar_tradingview():
    """
    Coleta os ativos mapeados via Scanner API Oculta do TradingView.
    Inclui os futuros ES e NQ (preços reais).
    ADRs e EWZ foram movidos para Finnhub.
    """
    url = "https://scanner.tradingview.com/global/scan"
    timestamp = datetime.now().isoformat()

    payload = {
        "symbols": {"tickers": TICKERS_TRADINGVIEW},
        "columns": ["close", "open", "high", "low", "change", "volume"],
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)

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

                    resultados.append(
                        {
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
                        }
                    )

            return resultados
    except Exception as e:
        print(f"[ERRO] Falha na coleta TradingView: {e}")
        return []


# ------------------------------------------------------------
# ENGINE DE ROTAÇÃO E FORMATADOR UNIFICADO
# ------------------------------------------------------------

def executar_rotacao_memoria(is_ram_mode=False):
    """
    Executa a rotação temporal dos 12 arquivos (0, 5, 10, ..., 55 min).
    - Se is_ram_mode for True, apenas retorna o caminho do RAM (sem rotação).
    - Caso contrário, desloca os arquivos do mais antigo para o mais recente.
    """
    if is_ram_mode:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Modo RAM ativado. Ignorando rotação temporal."
        )
        return FILE_RAM

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Executando rotação de memória física (Janela Móvel - 12 arquivos)..."
    )

    # Percorre de trás para frente (do mais antigo para o mais recente)
    for i in range(len(ARQUIVOS_ROM) - 1, 0, -1):
        origem = ARQUIVOS_ROM[i - 1]
        destino = ARQUIVOS_ROM[i]
        if os.path.exists(origem):
            shutil.copy2(origem, destino)
            print(f"  └─ Rotação: {os.path.basename(origem)} ──> {os.path.basename(destino)}")
        else:
            print(f"  └─ Aviso: {os.path.basename(origem)} não encontrado, pulando.")

    return ARQUIVOS_ROM[0]


def gerar_arquivo_unificado(coletas):
    """Gera o arquivo DadosAtivosUnificados.json com as chaves tratadas dos ativos."""
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

    estrutura_unificada = {
        "metadata": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_ativos": len(ativos_map),
        },
        "ativos": ativos_map,
    }

    with open(FILE_UNIFICADO, "w", encoding="utf-8") as f:
        json.dump(estrutura_unificada, f, indent=4, ensure_ascii=False)

    print(f"✅ Arquivo unificado salvo em: {FILE_UNIFICADO}")


# ------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# ------------------------------------------------------------

def executar_pipeline_coleta():
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando extração de dados brutos..."
    )

    coletas = []

    # 1. Extração BACEN PTAX
    ptax = coletar_bacen_ptax()
    coletas.append(ptax)

    # 2. Extração Ajustes
    ajustes = coletar_ajuste_oficial()
    coletas.extend(ajustes)

    # 3. Extração TradingView Scanner (inclui ES e NQ reais)
    tv_dados = coletar_tradingview()
    coletas.extend(tv_dados)

    # 4. Extração Finnhub (somente ADRs + EWZ)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando via Finnhub (ADRs + EWZ)...")
    finnhub_dados = coletar_finnhub()
    coletas.extend(finnhub_dados)
    print(f"   ✅ Finnhub: {len([d for d in finnhub_dados if d.get('status') == 'OK'])} ativos OK")

    # 5. Novos ativos B3 via MetaTrader 5
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando ações B3 via MetaTrader 5...")
    mt5_b3_dados = coletar_mt5_acoes_b3()
    coletas.extend(mt5_b3_dados)
    print(f"   ✅ MT5 Ações B3: {len([d for d in mt5_b3_dados if d.get('status') == 'OK'])} ativos OK")

    # ------------------------------------------------------------
    # 6. Se estiver na janela de ajuste, capturar LAST via MT5
    #    Prioridade: Coletor_MT5_v2_2 → fallback Coletor_MT5 (v1)
    # ------------------------------------------------------------
    if esta_na_janela_ajuste():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Capturando LAST TICK via MT5...")

        # 6.1 Tenta o coletor v2.2 (seleção dinâmica de contrato)
        mt5_ok = False
        try:
            from Coletor_MT5_v2_2 import executar_coleta_mt5_v2
            dados_mt5 = executar_coleta_mt5_v2()
            status_mt5 = (dados_mt5 or {}).get("status")
            if status_mt5 == "OK":
                print("   ✅ MT5 v2.2 coletado com sucesso.")
                mt5_ok = True
            elif status_mt5 == "OFFLINE":
                print("   ⚠️ MT5 offline — usando cache de LAST/FUT se disponível.")
            else:
                print(f"   ⚠️ Coleta MT5 v2.2 status={status_mt5!r}.")
        except ImportError:
            print("   ⚠️ Módulo Coletor_MT5_v2_2 não encontrado.")
        except KeyboardInterrupt:
            print("   ⚠️ Coleta MT5 interrompida pelo usuário.")
            raise
        except Exception as e:
            print(f"   ⚠️ Erro ao executar Coletor_MT5_v2_2: {e}")

        # 6.2 Fallback para o coletor antigo (v1) se o v2.2 falhou
        if not mt5_ok:
            try:
                from Coletor_MT5 import executar_coleta_mt5
                dados_mt5 = executar_coleta_mt5()
                if dados_mt5 and dados_mt5.get("status") == "OK":
                    print("   ✅ MT5 v1 (fallback) coletado com sucesso.")
                else:
                    print("   ⚠️ Falha também no coletor MT5 v1. Tentando ler arquivo existente.")
            except ImportError:
                print("   ⚠️ Módulo Coletor_MT5 (v1) também não encontrado. Tentando ler arquivo existente.")
            except Exception as e:
                print(f"   ⚠️ Erro ao executar Coletor_MT5 (v1): {e}")

        # 6.3 Extrai lasts + OHLC e monta WIN_FUT / WDO_FUT a partir do MT5
        lasts = capturar_last_do_mt5()
        mt5_json = {}
        if os.path.exists(FILE_MT5_V2):
            try:
                with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                    mt5_json = json.load(f)
            except Exception:
                mt5_json = {}
        ativos_mt5 = (mt5_json.get("ativos") or {}) if isinstance(mt5_json, dict) else {}

        timestamp_atual = datetime.now().isoformat()

        # Mapa: chave MT5 → (ativo_last, ativo_futuro_bruto para MAPEAMENTO_TICKERS)
        mapa_mt5 = {
            "WIN": ("WIN_LAST_TICK", "BMFBOVESPA:WIN1!"),
            "WDO": ("WDO_LAST_TICK", "BMFBOVESPA:WDO1!"),
        }

        for prefixo, (ativo_last, ativo_fut) in mapa_mt5.items():
            info = ativos_mt5.get(prefixo) or {}
            last_val = None
            if lasts and prefixo in lasts:
                last_val = lasts[prefixo].get("last")
                fonte_usada = lasts[prefixo].get("fonte", "MT5_v2.2")
            else:
                last_val = info.get("last")
                fonte_usada = "MT5_v2.2"

            if last_val is None or float(last_val or 0) <= 0:
                continue

            last_val = float(last_val)
            open_v = info.get("open")
            high_v = info.get("high")
            low_v = info.get("low")
            # close do futuro: last (mais atual) ou close D1
            close_v = last_val
            vol_v = info.get("volume_d1") or info.get("volume")
            var_pct = info.get("change_percent")
            prev_c = info.get("prev_close") or info.get("session_close")

            if var_pct is None and prev_c and float(prev_c or 0) > 0:
                var_pct = round(((last_val / float(prev_c)) - 1) * 100, 4)

            # LAST TICK (overnight / referência)
            coletas.append({
                "ativo": ativo_last,
                "fonte": fonte_usada,
                "timestamp": timestamp_atual,
                "status": "OK",
                "dados_reais": {
                    "close": last_val,
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "change_percent": var_pct,
                    "volume": vol_v,
                    "fechamento_anterior": prev_c,
                },
            })

            # WIN_FUT / WDO_FUT via MT5 (substitui TradingView WIN1!/WDO1!)
            # Inclui OHLC D1 para pivots na CalculadoraEstimativaAbertura
            coletas.append({
                "ativo": ativo_fut,
                "fonte": "MT5_v2.2",
                "timestamp": timestamp_atual,
                "status": "OK",
                "dados_reais": {
                    "close": close_v,
                    "open": float(open_v) if open_v is not None else None,
                    "high": float(high_v) if high_v is not None else None,
                    "low": float(low_v) if low_v is not None else None,
                    "change_percent": var_pct,
                    "volume": float(vol_v) if vol_v is not None else None,
                    "fechamento_anterior": float(prev_c) if prev_c else None,
                },
            })
            print(
                f"   ✅ {prefixo}_FUT via MT5: last={last_val} "
                f"OHLC=({open_v}/{high_v}/{low_v}) var={var_pct}"
            )
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fora da janela de ajuste. LAST TICK / FUT MT5 NÃO coletado ao vivo.")
        # Fora da janela: tenta reutilizar WIN_FUT/WDO_FUT e lasts do cache ROM/RAM
        for arquivo_cache in [FILE_RAM, FILE_ROM0]:
            if not os.path.exists(arquivo_cache):
                continue
            try:
                with open(arquivo_cache, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                for item in cache.get("coletas", []):
                    if item.get("ativo") in (
                        "WIN_LAST_TICK", "WDO_LAST_TICK",
                        "BMFBOVESPA:WIN1!", "BMFBOVESPA:WDO1!",
                    ):
                        item = dict(item)
                        item["fonte"] = f"CACHE_DISCO ({os.path.basename(arquivo_cache)})"
                        item["timestamp"] = datetime.now().isoformat()
                        coletas.append(item)
                if any(c.get("ativo") == "WIN_LAST_TICK" for c in coletas):
                    print(f"   ✅ WIN/WDO FUT+LAST reutilizados do cache ({os.path.basename(arquivo_cache)})")
                    break
            except Exception as e:
                print(f"   ⚠️ Cache FUT/LAST ({arquivo_cache}): {e}")

    # Monta estrutura da coleta bruta
    conteudo_saida = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "RAM" if is_ram else "PADRAO_ROTATIVO",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": os.path.basename(arquivo_destino),
        },
        "coletas": coletas,
    }

    # Grava Coleta de Rotação
    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)

    # Grava RAM (cópia independente da mais recente)
    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo_saida, f, indent=2, ensure_ascii=False)
        print(f"✅ Cópia independente gerada em: {FILE_RAM}")

    # Gera unificado
    gerar_arquivo_unificado(coletas)

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Coleta e Unificação concluídas com sucesso!"
    )
    print(
        f"Total de itens processados: {len(coletas)} | Arquivo: {os.path.basename(arquivo_destino)}\n"
    )


if __name__ == "__main__":
    print("============================================================")
    print(" FASE 1 & 2: MOTOR DE INGESTÃO E ROTAÇÃO DE DADOS")
    print(" (TradingView + Finnhub ADRs/EWZ + MT5 Ações B3 + LAST TICK)")
    print("============================================================")
    executar_pipeline_coleta()
