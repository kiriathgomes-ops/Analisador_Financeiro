# ============================================================
# ARQUIVO: Coletor.py
# DATA: 30/07/2026 | Atualizado 31/08/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Ingestão de Dados (BACEN SGS 10813 + TV + B3 WIN/WDO Separados)
#         Engine de Rotação Temporal de Memória e
#         Geração do Arquivo Unificado dos Ativos Mapeados.
#
# ATUALIZAÇÃO 01/09/2026 (Fase 0):
#   - WIN_FUT SEMPRE MT5 ao vivo
#   - WIN_LAST_TICK: MT5 só FORA do pregão + grava LastTick_Congelado.json
#   - No pregão: LAST lido do arquivo fixo (não depende da rotação ROM)
#   - Idem WDO
# ============================================================

from __future__ import annotations

import json
import os
import shutil
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BASE_DIR,
    COLETAS_DIR,
    ARQUIVOS_ROM,
    FILE_ROM0,
    FILE_RAM,
    FILE_UNIFICADO,
    FILE_MT5,
    FILE_MT5_V2,
    FILE_LAST_TICK_CONGELADO,
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
    esta_fora_do_pregao,
    JANELA_AJUSTE_INICIO,
    JANELA_AJUSTE_FIM,
)

# Compatibilidade: paths como str para código legado
BASE_DIR = str(BASE_DIR)
COLETAS_DIR = str(COLETAS_DIR)
ARQUIVOS_ROM = [str(p) for p in ARQUIVOS_ROM]
FILE_ROM0 = str(FILE_ROM0)
FILE_RAM = str(FILE_RAM)
FILE_UNIFICADO = str(FILE_UNIFICADO)
FILE_MT5 = str(FILE_MT5)
FILE_MT5_V2 = str(FILE_MT5_V2)
FILE_LAST_TICK_CONGELADO = str(FILE_LAST_TICK_CONGELADO)

for _cfg in ATIVOS_FINNHUB + ATIVOS_MT5_B3:
    if "id_interno" in _cfg and "id_limpo" not in _cfg:
        _cfg["id_limpo"] = _cfg["id_interno"]

os.makedirs(COLETAS_DIR, exist_ok=True)


# ------------------------------------------------------------
# HTTP Session (pool + retry leve)
# ------------------------------------------------------------
def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


_HTTP = _build_session()


# ------------------------------------------------------------
# LAST MT5 (leitura de arquivo já coletado)
# ------------------------------------------------------------
def capturar_last_do_mt5() -> dict:
    """
    Extrai o 'last' dos contratos principais de WIN e WDO.

    Prioridade:
      1. Dados_MT5_v2_2.json
      2. Dados_MT5.json (legado)
    """
    resultado: dict = {}

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
                    print(
                        f"   ✅ Last WIN via MT5 v2.2: "
                        f"{resultado['WIN']['last']} ({resultado['WIN']['contrato']})"
                    )
                if "WDO" in resultado:
                    print(
                        f"   ✅ Last WDO via MT5 v2.2: "
                        f"{resultado['WDO']['last']} ({resultado['WDO']['contrato']})"
                    )
                return resultado

        except Exception as e:
            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}. Tentando formato antigo...")

    if not os.path.exists(FILE_MT5):
        print("[AVISO] Nenhum arquivo MT5 encontrado (v2.2 nem v1).")
        return resultado

    try:
        with open(FILE_MT5, "r", encoding="utf-8") as f:
            dados = json.load(f)

        contratos = dados.get("contratos", {})
        timestamp = dados.get("timestamp", datetime.now().isoformat())
        mapeamento_contratos = {
            "WIN": ["WINQ26", "WINV26", "WINZ26"],
            "WDO": ["WDOQ26", "WDOV26", "WDOZ26", "WDOU26"],
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
            print(
                f"   ✅ Last WIN via MT5 v1: "
                f"{resultado['WIN']['last']} ({resultado['WIN']['contrato']})"
            )
        if "WDO" in resultado:
            print(
                f"   ✅ Last WDO via MT5 v1: "
                f"{resultado['WDO']['last']} ({resultado['WDO']['contrato']})"
            )
        return resultado

    except Exception as e:
        print(f"[ERRO] Falha ao ler Dados_MT5.json: {e}")
        return {}


# ------------------------------------------------------------
# Finnhub (paralelo)
# ------------------------------------------------------------
def coletar_finnhub() -> List[Dict[str, Any]]:
    timestamp = datetime.now().isoformat()
    if not FINNHUB_API_KEY:
        print("⚠️ [AVISO] FINNHUB_API_KEY ausente no .env")
        return []

    def _um(cfg: dict) -> dict:
        ticker = cfg["ticker_coleta"]
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        try:
            res = _HTTP.get(url, timeout=TIMEOUT_FINNHUB or 5).json()
            if "error" in res:
                return {
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "ERRO",
                    "dados_reais": None,
                }
            if "c" in res and res["c"] != 0:
                return {
                    "ativo": cfg["ativo"],
                    "fonte": "FINNHUB",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": float(res["c"]),
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": round(float(res.get("dp", 0.0)), 2),
                        "volume": None,
                        "var_abs": round(float(res.get("d", 0.0)), 2),
                        "fechamento_anterior": float(res.get("pc", 0.0)),
                    },
                }
            return {
                "ativo": cfg["ativo"],
                "fonte": "FINNHUB",
                "timestamp": timestamp,
                "status": "SEM_DADOS",
                "dados_reais": None,
            }
        except Exception as e:
            print(f"❌ Finnhub ({ticker}): {e}")
            return {
                "ativo": cfg["ativo"],
                "fonte": "FINNHUB",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            }

    workers = min(8, max(1, len(ATIVOS_FINNHUB)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_um, ATIVOS_FINNHUB))


# ------------------------------------------------------------
# Ações B3 via MT5
# ------------------------------------------------------------
def coletar_mt5_acoes_b3(mt5_ja_inicializado: bool = False) -> List[Dict[str, Any]]:
    timestamp = datetime.now().isoformat()
    resultados: List[Dict[str, Any]] = []

    own_init = False
    if not mt5_ja_inicializado:
        if not mt5.initialize():
            print("⚠️ MT5 não inicializou para ações B3")
            return resultados
        own_init = True

    try:
        for cfg in ATIVOS_MT5_B3:
            symbol = cfg["ticker_coleta"]
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)

            if not info or not tick:
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "MetaTrader5",
                    "timestamp": timestamp,
                    "status": "ERRO",
                    "dados_reais": None,
                })
                continue

            prev_close = float(getattr(info, "session_close", 0.0) or 0.0)
            preco = float(
                tick.last if tick.last > 0 else (tick.bid if tick.bid > 0 else tick.ask)
            )

            if preco <= 0:
                resultados.append({
                    "ativo": cfg["ativo"],
                    "fonte": "MetaTrader5",
                    "timestamp": timestamp,
                    "status": "SEM_DADOS",
                    "dados_reais": None,
                })
                continue

            var_pct = (
                round(((preco / prev_close) - 1) * 100, 2) if prev_close > 0 else 0.0
            )
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
                    "var_abs": round(preco - prev_close, 2) if prev_close > 0 else 0.0,
                    "fechamento_anterior": prev_close,
                },
            })
    finally:
        if own_init:
            mt5.shutdown()

    return resultados


# ------------------------------------------------------------
# BACEN PTAX
# ------------------------------------------------------------
def coletar_bacen_ptax() -> dict:
    timestamp = datetime.now().isoformat()
    url_sgs = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url_sgs, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT_BACEN or 10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res:
                valor = float(res[-1]["valor"].replace(",", "."))
                return {
                    "ativo": "USD_PTAX",
                    "fonte": "BACEN_SGS_10813",
                    "timestamp": timestamp,
                    "status": "OK",
                    "dados_reais": {
                        "close": valor,
                        "open": None,
                        "high": None,
                        "low": None,
                        "change_percent": None,
                        "volume": None,
                    },
                }
    except Exception as e:
        print(f"[AVISO] Bacen SGS: {e}. Fallback TV...")

    try:
        payload = {"symbols": {"tickers": ["FX_IDC:USDBRL"]}, "columns": ["close"]}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://scanner.tradingview.com/global/scan",
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
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


# ------------------------------------------------------------
# Ajuste oficial (TV) — só na janela 19:00–08:50
# ------------------------------------------------------------
def coletar_ajuste_oficial() -> List[dict]:
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()

    if JANELA_AJUSTE_FIM < hora_atual < JANELA_AJUSTE_INICIO:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fora da janela de ajuste. Cache...")
        for arquivo_cache in (FILE_RAM, FILE_ROM0):
            if not os.path.exists(arquivo_cache):
                continue
            try:
                with open(arquivo_cache, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                encontrados = [
                    item
                    for item in dados.get("coletas", [])
                    if item.get("ativo") in ("B3_AJUSTE_WIN", "B3_AJUSTE_WDO")
                ]
                if encontrados:
                    saida = []
                    for item in encontrados:
                        item = dict(item)
                        item["fonte"] = "CACHE_DISCO (Fora da janela)"
                        item["timestamp"] = timestamp
                        saida.append(item)
                    return saida
            except Exception:
                continue
        return [
            {
                "ativo": "B3_AJUSTE_WIN",
                "fonte": "NENHUM_DADO",
                "timestamp": timestamp,
                "status": "FORA_JANELA_SEM_CACHE",
                "dados_reais": None,
            },
            {
                "ativo": "B3_AJUSTE_WDO",
                "fonte": "NENHUM_DADO",
                "timestamp": timestamp,
                "status": "FORA_JANELA_SEM_CACHE",
                "dados_reais": None,
            },
        ]

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dentro da janela. Coletando ajuste TV...")
    simbolos = [
        {"ativo": "B3_AJUSTE_WIN", "ticker": "BMFBOVESPA:WIN1!"},
        {"ativo": "B3_AJUSTE_WDO", "ticker": "BMFBOVESPA:WDO1!"},
    ]

    def _um(item: dict) -> dict:
        url = (
            f"https://scanner.tradingview.com/symbol?"
            f"symbol={item['ticker']}&fields=close,change"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_TRADINGVIEW or 10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                close_val = res.get("close")
                change_val = res.get("change", 0.0)
                return {
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
                }
        except Exception as e:
            print(f"   ❌ Ajuste {item['ativo']}: {e}")
            return {
                "ativo": item["ativo"],
                "fonte": "TRADINGVIEW_DIRECT_SYMBOL",
                "timestamp": timestamp,
                "status": "ERRO",
                "dados_reais": None,
            }

    with ThreadPoolExecutor(max_workers=2) as ex:
        return list(ex.map(_um, simbolos))


# ------------------------------------------------------------
# TradingView Scanner (batch)
# ------------------------------------------------------------
def coletar_tradingview() -> List[dict]:
    url = "https://scanner.tradingview.com/global/scan"
    timestamp = datetime.now().isoformat()
    payload = {
        "symbols": {"tickers": TICKERS_TRADINGVIEW},
        "columns": ["close", "open", "high", "low", "change", "volume"],
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_TRADINGVIEW or 10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            resultados = []
            for item in res.get("data", []):
                ticker = item.get("s")
                vals = item.get("d", [])
                ticker_chave = "SGX:FEF2!" if ticker == TICKER_FEF2 else ticker
                if len(vals) >= 5 and vals[0] is not None:
                    resultados.append({
                        "ativo": ticker_chave,
                        "fonte": "TRADINGVIEW_SCANNER",
                        "timestamp": timestamp,
                        "status": "OK",
                        "dados_reais": {
                            "close": float(vals[0]),
                            "open": float(vals[1]) if vals[1] is not None else None,
                            "high": float(vals[2]) if vals[2] is not None else None,
                            "low": float(vals[3]) if vals[3] is not None else None,
                            "change_percent": float(vals[4]) if vals[4] is not None else 0.0,
                            "volume": (
                                float(vals[5])
                                if len(vals) > 5 and vals[5] is not None
                                else None
                            ),
                        },
                    })
            return resultados
    except Exception as e:
        print(f"[ERRO] TradingView Scanner: {e}")
        return []


# ------------------------------------------------------------
# Rotação e unificado
# ------------------------------------------------------------
def executar_rotacao_memoria(is_ram_mode: bool = False) -> str:
    if is_ram_mode:
        return FILE_RAM

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"Rotação de memória (12 slots)..."
    )
    for i in range(len(ARQUIVOS_ROM) - 1, 0, -1):
        origem = ARQUIVOS_ROM[i - 1]
        destino = ARQUIVOS_ROM[i]
        if os.path.exists(origem):
            try:
                os.replace(origem, destino)
            except OSError:
                shutil.copy2(origem, destino)
    return ARQUIVOS_ROM[0]


def gerar_arquivo_unificado(coletas: List[dict]) -> None:
    ativos_map: Dict[str, Any] = {}
    for item in coletas:
        ativo_raw = item.get("ativo")
        dados = item.get("dados_reais") or {}
        nome = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)
        ativos_map[nome] = {
            "preco": float(dados.get("close") or 0.0),
            "variacao_pct": float(dados.get("change_percent") or 0.0),
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
        json.dump(estrutura, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ Unificado: {FILE_UNIFICADO}")


# ------------------------------------------------------------
# Montagem WIN_FUT / WIN_LAST_TICK a partir do MT5
# + arquivo fixo LastTick_Congelado.json (Fase 0)
# ------------------------------------------------------------
def _carregar_cache_coletas(*arquivos: str) -> list:
    """Lê itens de coletas dos arquivos de cache (ordem de prioridade)."""
    for arq in arquivos:
        if not os.path.exists(arq):
            continue
        try:
            with open(arq, "r", encoding="utf-8") as f:
                cache = json.load(f)
            itens = cache.get("coletas") or []
            if itens:
                return list(itens)
        except Exception as e:
            print(f"   ⚠️ Cache {os.path.basename(arq)}: {e}")
    return []


def _item_cache_por_ativo(itens: list, ativo: str) -> Optional[dict]:
    for item in itens:
        if item.get("ativo") == ativo:
            return dict(item)
    return None


def _carregar_last_tick_congelado() -> dict:
    """
    Lê Coletas/LastTick_Congelado.json.
    Retorno: {"WIN_LAST_TICK": {...item coleta...}, "WDO_LAST_TICK": {...}}
    """
    if not os.path.exists(FILE_LAST_TICK_CONGELADO):
        return {}
    try:
        with open(FILE_LAST_TICK_CONGELADO, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ticks") or {}
    except Exception as e:
        print(f"   ⚠️ Leitura LastTick_Congelado: {e}")
        return {}


def _salvar_last_tick_congelado(ticks: Dict[str, dict]) -> None:
    """
    Persiste snapshot de LAST fora do pregão.
    ticks: {"WIN_LAST_TICK": item, "WDO_LAST_TICK": item}
    """
    if not ticks:
        return
    # merge com existente para não apagar WDO se só veio WIN
    atual = _carregar_last_tick_congelado()
    atual.update(ticks)
    payload = {
        "timestamp_congelamento": datetime.now().isoformat(),
        "fonte": "MT5_v2.2",
        "ticks": atual,
    }
    try:
        with open(FILE_LAST_TICK_CONGELADO, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"   💾 LastTick_Congelado.json atualizado ({', '.join(ticks.keys())})")
    except Exception as e:
        print(f"   ⚠️ Falha ao gravar LastTick_Congelado: {e}")


def _montar_win_wdo_mt5(coletas: List[dict]) -> bool:
    """
    WIN_FUT / WDO_FUT:
        SEMPRE a partir do MT5 (candle/preço atual).

    WIN_LAST_TICK / WDO_LAST_TICK:
        - FORA do pregão → MT5 ao vivo + grava LastTick_Congelado.json
        - NO pregão     → lê arquivo fixo (fallback: RAM/ROM se arquivo ausente)

    Retorna True se montou pelo menos WIN_FUT fresco do MT5.
    """
    mt5_json: dict = {}
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f:
                mt5_json = json.load(f)
        except Exception as e:
            print(f"   ⚠️ Leitura MT5 v2.2: {e}")

    lasts = capturar_last_do_mt5()
    ativos_mt5 = (mt5_json.get("ativos") or {}) if isinstance(mt5_json, dict) else {}
    ts = datetime.now().isoformat()
    fora_pregao = esta_fora_do_pregao()
    montou_win_fut = False
    ticks_para_congelar: Dict[str, dict] = {}

    freeze_map = _carregar_last_tick_congelado() if not fora_pregao else {}
    cache_itens: list = []
    if not fora_pregao and not freeze_map:
        cache_itens = _carregar_cache_coletas(FILE_RAM, FILE_ROM0)

    mapa = {
        "WIN": ("WIN_LAST_TICK", "BMFBOVESPA:WIN1!"),
        "WDO": ("WDO_LAST_TICK", "BMFBOVESPA:WDO1!"),
    }

    for prefixo, (ativo_last, ativo_fut) in mapa.items():
        info = ativos_mt5.get(prefixo) or {}
        last_val = (lasts.get(prefixo) or {}).get("last") or info.get("last")

        # ---------- FUT: sempre MT5 ----------
        if last_val is not None and float(last_val or 0) > 0:
            last_val = float(last_val)
            open_v = info.get("open")
            high_v = info.get("high")
            low_v = info.get("low")
            prev_c = info.get("prev_close") or info.get("session_close")
            var_pct = info.get("change_percent")
            vol_v = info.get("volume_d1") or info.get("volume")
            bid = info.get("bid")
            ask = info.get("ask")

            if var_pct is None and prev_c and float(prev_c or 0) > 0:
                var_pct = round(((last_val / float(prev_c)) - 1) * 100, 4)

            if (
                isinstance(bid, (int, float))
                and isinstance(ask, (int, float))
                and bid > 0
                and ask > 0
                and (last_val < bid or last_val > ask)
            ):
                mid = round((float(bid) + float(ask)) / 2.0, 1)
                print(
                    f"   ⚠️ {prefixo} last={last_val} fora do spread "
                    f"[{bid},{ask}] → mid={mid}"
                )
                last_val = mid

            ohlc = {
                "close": last_val,
                "open": float(open_v) if open_v is not None else None,
                "high": float(high_v) if high_v is not None else None,
                "low": float(low_v) if low_v is not None else None,
                "change_percent": var_pct,
                "volume": float(vol_v) if vol_v is not None else None,
                "fechamento_anterior": float(prev_c) if prev_c else None,
            }
            contrato = (
                info.get("contrato_principal")
                or (lasts.get(prefixo) or {}).get("contrato")
            )

            coletas.append({
                "ativo": ativo_fut,
                "fonte": "MT5_v2.2",
                "timestamp": ts,
                "status": "OK",
                "dados_reais": dict(ohlc),
            })
            print(
                f"   ✅ {prefixo}_FUT SEMPRE ({contrato}): last={last_val} "
                f"OHLC=({ohlc['open']}/{ohlc['high']}/{ohlc['low']}) var={var_pct}"
            )
            if prefixo == "WIN":
                montou_win_fut = True

            # ---------- LAST_TICK ----------
            if fora_pregao:
                item_last = {
                    "ativo": ativo_last,
                    "fonte": "MT5_v2.2",
                    "timestamp": ts,
                    "status": "OK",
                    "dados_reais": dict(ohlc),
                }
                coletas.append(item_last)
                ticks_para_congelar[ativo_last] = item_last
                print(f"   ✅ {ativo_last} MT5 ao vivo (fora do pregão)")
            else:
                frozen = freeze_map.get(ativo_last)
                if frozen and (frozen.get("dados_reais") or {}).get("close"):
                    item = dict(frozen)
                    item["fonte"] = "LAST_TICK_CONGELADO (arquivo fixo)"
                    item["timestamp"] = ts
                    item["status"] = item.get("status") or "OK"
                    coletas.append(item)
                    preco = (item.get("dados_reais") or {}).get("close")
                    print(f"   🧊 {ativo_last} CONGELADO (arquivo) close={preco}")
                else:
                    cached = _item_cache_por_ativo(cache_itens, ativo_last)
                    if cached and (cached.get("dados_reais") or {}).get("close"):
                        cached = dict(cached)
                        cached["fonte"] = "CACHE_DISCO_CONGELADO (pregão; fallback)"
                        cached["timestamp"] = ts
                        coletas.append(cached)
                        preco = (cached.get("dados_reais") or {}).get("close")
                        print(f"   🧊 {ativo_last} CONGELADO (cache fallback) close={preco}")
                    else:
                        print(
                            f"   ⚠️ {ativo_last}: sem arquivo fixo nem cache — "
                            f"chave ausente neste ciclo"
                        )
        else:
            print(f"   ⚠️ {prefixo}: sem last MT5 para FUT")
            if not fora_pregao:
                frozen = freeze_map.get(ativo_last)
                if frozen:
                    item = dict(frozen)
                    item["fonte"] = "LAST_TICK_CONGELADO (arquivo; sem FUT MT5)"
                    item["timestamp"] = ts
                    coletas.append(item)
                    print(f"   🧊 {ativo_last} CONGELADO (só arquivo)")
                else:
                    cached = _item_cache_por_ativo(cache_itens, ativo_last)
                    if cached:
                        cached = dict(cached)
                        cached["fonte"] = "CACHE_DISCO_CONGELADO (pregão; sem FUT)"
                        cached["timestamp"] = ts
                        coletas.append(cached)
                        print(f"   🧊 {ativo_last} CONGELADO (só cache)")

    if fora_pregao and ticks_para_congelar:
        _salvar_last_tick_congelado(ticks_para_congelar)

    return montou_win_fut


def _reutilizar_cache_last_fut(coletas: List[dict]) -> None:
    """Fallback fora do pregão se MT5 falhar totalmente."""
    # tenta arquivo fixo primeiro
    freeze = _carregar_last_tick_congelado()
    added = False
    for ativo in ("WIN_LAST_TICK", "WDO_LAST_TICK"):
        item = freeze.get(ativo)
        if item:
            item = dict(item)
            item["fonte"] = f"LAST_TICK_CONGELADO (MT5 offline)"
            item["timestamp"] = datetime.now().isoformat()
            coletas.append(item)
            added = True
    if added:
        print("   ✅ LAST do arquivo fixo (MT5 offline)")
        return

    itens = _carregar_cache_coletas(FILE_RAM, FILE_ROM0)
    if not itens:
        return
    for ativo in (
        "WIN_LAST_TICK",
        "WDO_LAST_TICK",
        "BMFBOVESPA:WIN1!",
        "BMFBOVESPA:WDO1!",
    ):
        item = _item_cache_por_ativo(itens, ativo)
        if item:
            item["fonte"] = f"CACHE_DISCO ({item.get('fonte', 'N/A')})"
            item["timestamp"] = datetime.now().isoformat()
            coletas.append(item)
            added = True
    if added:
        print("   ✅ Cache LAST/FUT reutilizado (MT5 offline)")


# ------------------------------------------------------------
# Pipeline principal
# ------------------------------------------------------------
def executar_pipeline_coleta() -> None:
    t0 = datetime.now()
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)

    print(f"[{t0.strftime('%H:%M:%S')}] Iniciando coleta paralela...")

    coletas: List[dict] = []

    # --- Fontes HTTP independentes em paralelo ---
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_ptax = ex.submit(coletar_bacen_ptax)
        fut_ajuste = ex.submit(coletar_ajuste_oficial)
        fut_tv = ex.submit(coletar_tradingview)
        fut_fh = ex.submit(coletar_finnhub)

        ptax = fut_ptax.result()
        ajustes = fut_ajuste.result()
        tv_dados = fut_tv.result()
        finnhub_dados = fut_fh.result()

    coletas.append(ptax)
    coletas.extend(ajustes)
    coletas.extend(tv_dados)
    coletas.extend(finnhub_dados)

    ok_fh = sum(1 for d in finnhub_dados if d.get("status") == "OK")
    print(
        f"   ✅ Finnhub: {ok_fh} OK | TV: {len(tv_dados)} | "
        f"Ajustes: {len(ajustes)}"
    )

    # --- MT5: sempre coleta v2.2 (WIN_FUT precisa estar fresco) ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando MT5 (WIN_FUT sempre)...")
    mt5_ok = False
    try:
        from Coletor_MT5_v2_2 import executar_coleta_mt5_v2

        dados_mt5 = executar_coleta_mt5_v2()
        if (dados_mt5 or {}).get("status") == "OK":
            mt5_ok = True
            print("   ✅ MT5 v2.2 OK")
        else:
            print(f"   ⚠️ MT5 v2.2 status={(dados_mt5 or {}).get('status')!r}")
    except Exception as e:
        print(f"   ⚠️ MT5 v2.2: {e}")

    # Ações B3
    mt5_b3 = coletar_mt5_acoes_b3()
    coletas.extend(mt5_b3)
    print(
        f"   ✅ MT5 B3: "
        f"{sum(1 for d in mt5_b3 if d.get('status') == 'OK')} OK"
    )

    # Monta WIN_FUT (sempre) + WIN_LAST_TICK (vivo fora / congelado no pregão)
    montou = _montar_win_wdo_mt5(coletas)

    if not montou and not mt5_ok and esta_fora_do_pregao():
        print("   ⚠️ MT5 falhou fora do pregão — tentando cache LAST/FUT")
        _reutilizar_cache_last_fut(coletas)

    # Persistência (JSON compacto)
    conteudo = {
        "metadata_coleta": {
            "timestamp_coleta": datetime.now().isoformat(),
            "modo_execucao": "RAM" if is_ram else "PADRAO_ROTATIVO",
            "total_ativos_solicitados": len(coletas),
            "arquivo_gerado": os.path.basename(arquivo_destino),
            "latencia_ms": int((datetime.now() - t0).total_seconds() * 1000),
            "fora_do_pregao": esta_fora_do_pregao(),
        },
        "coletas": coletas,
    }

    with open(arquivo_destino, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, separators=(",", ":"))

    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, ensure_ascii=False, separators=(",", ":"))
        print(f"✅ RAM: {FILE_RAM}")

    gerar_arquivo_unificado(coletas)

    elapsed = (datetime.now() - t0).total_seconds()
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Coleta OK | "
        f"{len(coletas)} itens | {elapsed:.2f}s | "
        f"{'FORA' if esta_fora_do_pregao() else 'DENTRO'} do pregão"
    )


if __name__ == "__main__":
    print("=" * 60)
    print(" COLETOR — WIN_FUT sempre | LAST arquivo fixo (Fase 0)")
    print("=" * 60)
    executar_pipeline_coleta()
