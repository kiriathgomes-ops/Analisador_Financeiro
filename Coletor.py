# ============================================================
# ARQUIVO: Coletor.py
# VERSÃO: 2.8 (Turbo) - Coleta Contínua (Pré, Regular e Pós-Market)
# ============================================================

from __future__ import annotations

import json
import os
import shutil
import ssl
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BASE_DIR, COLETAS_DIR, ARQUIVOS_ROM, FILE_ROM0, FILE_RAM, FILE_UNIFICADO,
    FILE_MT5_V2, FILE_LAST_TICK_CONGELADO, FINNHUB_API_KEY, TICKERS_TRADINGVIEW,
    ATIVOS_FINNHUB, ATIVOS_MT5_B3, MAPEAMENTO_TICKERS, TIMEOUT_TRADINGVIEW,
    TIMEOUT_FINNHUB, TIMEOUT_BACEN, esta_na_janela_ajuste, esta_fora_do_pregao,
    JANELA_AJUSTE_INICIO, JANELA_AJUSTE_FIM,
)

BASE_DIR = str(BASE_DIR)
COLETAS_DIR = str(COLETAS_DIR)
ARQUIVOS_ROM = [str(p) for p in ARQUIVOS_ROM]
FILE_ROM0 = str(FILE_ROM0)
FILE_RAM = str(FILE_RAM)
FILE_UNIFICADO = str(FILE_UNIFICADO)
FILE_MT5_V2 = str(FILE_MT5_V2)
FILE_LAST_TICK_CONGELADO = str(FILE_LAST_TICK_CONGELADO)

for _cfg in ATIVOS_FINNHUB + ATIVOS_MT5_B3:
    if "id_interno" in _cfg and "id_limpo" not in _cfg:
        _cfg["id_limpo"] = _cfg["id_interno"]

os.makedirs(COLETAS_DIR, exist_ok=True)

def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=["GET", "POST"])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session

_HTTP = _build_session()


def capturar_last_do_mt5() -> dict:
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
                        resultado[prefixo] = {"contrato": contrato, "last": float(last), "timestamp": timestamp, "fonte": "MT5_v2.2"}
            if resultado:
                if "WIN" in resultado: print(f"   ✅ Last WIN via MT5: {resultado['WIN']['last']} ({resultado['WIN']['contrato']})")
                if "WDO" in resultado: print(f"   ✅ Last WDO via MT5: {resultado['WDO']['last']} ({resultado['WDO']['contrato']})")
                return resultado
        except Exception as e:
            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}")
    return resultado


# ------------------------------------------------------------
# TRADINGVIEW: PRE, REGULAR E POST MARKET
# ------------------------------------------------------------
def _coletar_tv_adr(ticker_tv: str) -> Dict[str, Any]:
    url = (
        f"https://scanner.tradingview.com/symbol?"
        f"symbol={ticker_tv}&fields=close,change,premarket_close,premarket_change,postmarket_close,postmarket_change"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            
        close_val = res.get("close")
        change_val = res.get("change")
        pre_close = res.get("premarket_close")
        pre_change = res.get("premarket_change")
        post_close = res.get("postmarket_close")
        post_change = res.get("postmarket_change")

        # Prioridade: Pós-Market > Pré-Market > Regular
        if post_close is not None and float(post_close) > 0 and post_change is not None:
            final_close, final_change, tipo = post_close, post_change, "POST"
        elif pre_close is not None and float(pre_close) > 0 and pre_change is not None:
            final_close, final_change, tipo = pre_close, pre_change, "PRE"
        else:
            final_close, final_change, tipo = close_val, change_val, "REGULAR"

        if final_close is None or float(final_close) <= 0: return None
        if final_change is None: return None

        if tipo != "REGULAR":
            print(f"      [TV] {ticker_tv}: {tipo}-market ({final_change:+.2f}%)")

        return {"c": float(final_close), "d": 0.0, "dp": float(final_change), "pc": 0.0, "t": 0}
    except Exception as e:
        print(f"      [TV] {ticker_tv}: erro {e}")
        return None


def coletar_finnhub() -> List[Dict[str, Any]]:
    timestamp = datetime.now().isoformat()

    def _um(cfg: dict) -> dict:
        ticker = cfg["ticker_coleta"]
        ticker_tv = cfg["ativo"]
        
        _tv = _coletar_tv_adr(ticker_tv)
        if _tv is not None:
            print(f"   ✅ TV OK para {ticker}: {_tv['dp']:+.2f}%")
            return {"ativo": cfg["ativo"], "fonte": "TRADINGVIEW", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": _tv["c"], "open": None, "high": None, "low": None, "change_percent": round(_tv["dp"], 2), "volume": None, "var_abs": 0.0, "fechamento_anterior": 0.0}}

        if not FINNHUB_API_KEY:
            return {"ativo": cfg["ativo"], "fonte": "NENHUMA", "timestamp": timestamp, "status": "ERRO", "dados_reais": None}

        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
        try:
            res = _HTTP.get(url, timeout=TIMEOUT_FINNHUB or 5).json()
            if "c" in res and res["c"] != 0:
                return {"ativo": cfg["ativo"], "fonte": "FINNHUB", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": float(res["c"]), "open": None, "high": None, "low": None, "change_percent": round(float(res.get("dp", 0)), 2), "volume": None, "var_abs": round(float(res.get("d", 0)), 2), "fechamento_anterior": float(res.get("pc", 0))}}
            return {"ativo": cfg["ativo"], "fonte": "FINNHUB", "timestamp": timestamp, "status": "SEM_DADOS", "dados_reais": None}
        except Exception as e:
            return {"ativo": cfg["ativo"], "fonte": "FINNHUB", "timestamp": timestamp, "status": "ERRO", "dados_reais": None}

    with ThreadPoolExecutor(max_workers=min(8, len(ATIVOS_FINNHUB))) as ex:
        return list(ex.map(_um, ATIVOS_FINNHUB))


# ------------------------------------------------------------
# AÇÕES B3 VIA MT5 (Mercado Interno)
# ------------------------------------------------------------
def coletar_mt5_acoes_b3(mt5_ja_inicializado: bool = False) -> List[Dict[str, Any]]:
    timestamp = datetime.now().isoformat()
    resultados: List[Dict[str, Any]] = []
    own_init = False
    if not mt5_ja_inicializado:
        if not mt5.initialize(): return resultados
        own_init = True
    try:
        for cfg in ATIVOS_MT5_B3:
            symbol = cfg["ticker_coleta"]
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if not info or not tick:
                resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "ERRO", "dados_reais": None})
                continue
            prev_close = float(getattr(info, "session_close", 0.0) or 0.0)
            preco = float(tick.last if tick.last > 0 else (tick.bid if tick.bid > 0 else tick.ask))
            if preco <= 0:
                resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "SEM_DADOS", "dados_reais": None})
                continue
            var_pct = round(((preco / prev_close) - 1) * 100, 2) if prev_close > 0 else 0.0
            resultados.append({"ativo": cfg["ativo"], "fonte": "MetaTrader5", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": preco, "open": None, "high": None, "low": None, "change_percent": var_pct, "volume": None, "var_abs": round(preco - prev_close, 2) if prev_close > 0 else 0.0, "fechamento_anterior": prev_close}})
    finally:
        if own_init: mt5.shutdown()
    return resultados


# ------------------------------------------------------------
# BACEN PTAX E BRAPI (Ajuste e Fechamento Oficial B3)
# ------------------------------------------------------------
def _fetch_url_com_retry(url: str, ctx=None, data: bytes = None, tentativas: int = 3, timeout: int = 10, headers: dict = None) -> bytes:
    headers = headers or {"User-Agent": "Mozilla/5.0"}
    for tent in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            if ctx is not None:
                with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp: return resp.read()
            else:
                with urllib.request.urlopen(req, timeout=timeout) as resp: return resp.read()
        except Exception as e:
            if tent == tentativas: raise e
            time.sleep(2 ** (tent - 1))

def coletar_bacen_ptax() -> dict:
    timestamp = datetime.now().isoformat()
    url_sgs = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/5?formato=json"
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    try:
        res = json.loads(_fetch_url_com_retry(url_sgs, ctx=ctx, tentativas=3, timeout=TIMEOUT_BACEN or 10).decode("utf-8"))
        if res: return {"ativo": "USD_PTAX", "fonte": "BACEN", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": float(res[-1]["valor"].replace(",", ".")), "open": None, "high": None, "low": None, "change_percent": None, "volume": None}}
    except: pass
    return {"ativo": "USD_PTAX", "fonte": "BACEN", "timestamp": timestamp, "status": "SEM_DADOS", "dados_reais": None}

def _descobrir_contrato_win() -> str:
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f: contrato = ((json.load(f).get("ativos") or {}).get("WIN", {}).get("contrato_principal"))
            if contrato and str(contrato).upper().startswith("WIN"): return str(contrato).upper()
        except: pass
    return "WINV26"

def _descobrir_contrato_wdo() -> str:
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f: contrato = ((json.load(f).get("ativos") or {}).get("WDO", {}).get("contrato_principal"))
            if contrato and str(contrato).upper().startswith("WDO"): return str(contrato).upper()
        except: pass
    return "WDOU26"

def coletar_ajuste_brapi() -> List[dict]:
    timestamp = datetime.now().isoformat()
    saida: List[dict] = []
    try:
        url = f"https://brapi.dev/api/v2/futures/quote?symbols={_descobrir_contrato_win()},{_descobrir_contrato_wdo()}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp: dados = json.loads(resp.read().decode("utf-8"))
    except: return []
    
    for item in dados.get("quotes", []) or []:
        symbol = str(item.get("symbol", "")).upper()
        prefixo = "WIN" if symbol.startswith("WIN") else ("WDO" if symbol.startswith("WDO") else None)
        if not prefixo: continue
        
        if item.get("settlement"):
            saida.append({"ativo": f"B3_AJUSTE_{prefixo}", "fonte": "BRAPI", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": float(item["settlement"]), "open": None, "high": None, "low": None, "change_percent": None, "volume": None}})
        if item.get("close"):
            saida.append({"ativo": f"B3_FECHAMENTO_{prefixo}", "fonte": "BRAPI", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": float(item["close"]), "open": None, "high": None, "low": None, "change_percent": None, "volume": None}})
    return saida

def coletar_ajuste_oficial(silencioso: bool = False) -> List[dict]:
    timestamp = datetime.now().isoformat()
    hora_atual = datetime.now().time()
    if JANELA_AJUSTE_FIM < hora_atual < JANELA_AJUSTE_INICIO: return []
    def _um(item: dict) -> dict:
        url = f"https://scanner.tradingview.com/symbol?symbol={item['ticker']}&fields=close"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_TRADINGVIEW or 10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return {"ativo": item["ativo"], "fonte": "TV", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": float(res["close"]) if res.get("close") else None, "open": None, "high": None, "low": None, "change_percent": None, "volume": None}}
        except: return {"ativo": item["ativo"], "fonte": "TV", "timestamp": timestamp, "status": "ERRO", "dados_reais": None}
    with ThreadPoolExecutor(max_workers=2) as ex: return list(ex.map(_um, [{"ativo": "B3_AJUSTE_WIN", "ticker": "BMFBOVESPA:WIN1!"}, {"ativo": "B3_AJUSTE_WDO", "ticker": "BMFBOVESPA:WDO1!"}]))

def coletar_tradingview() -> List[dict]:
    url = "https://scanner.tradingview.com/global/scan"
    timestamp = datetime.now().isoformat()
    try:
        data = json.dumps({"symbols": {"tickers": TICKERS_TRADINGVIEW}, "columns": ["close", "open", "high", "low", "change", "volume"]}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_TRADINGVIEW or 10) as resp:
            resultados = []
            for item in json.loads(resp.read().decode("utf-8")).get("data", []):
                vals = item.get("d", [])
                if len(vals) >= 5 and vals[0] is not None:
                    resultados.append({"ativo": item.get("s"), "fonte": "TRADINGVIEW", "timestamp": timestamp, "status": "OK", "dados_reais": {"close": float(vals[0]), "open": float(vals[1]) if vals[1] else None, "high": float(vals[2]) if vals[2] else None, "low": float(vals[3]) if vals[3] else None, "change_percent": float(vals[4]) if vals[4] else 0.0, "volume": float(vals[5]) if len(vals) > 5 and vals[5] else None}})
            return resultados
    except: return []


# ------------------------------------------------------------
# ROTAÇÃO E UNIFICADO
# ------------------------------------------------------------
def executar_rotacao_memoria(is_ram_mode: bool = False) -> str:
    if is_ram_mode: return FILE_RAM
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Rotação de memória (12 slots)...")
    for i in range(len(ARQUIVOS_ROM) - 1, 0, -1):
        origem, destino = ARQUIVOS_ROM[i - 1], ARQUIVOS_ROM[i]
        if os.path.exists(origem):
            try: os.replace(origem, destino)
            except OSError: shutil.copy2(origem, destino)
    return ARQUIVOS_ROM[0]

def gerar_arquivo_unificado(coletas: List[dict]) -> None:
    ativos_map = {}
    for item in coletas:
        ativo_raw, dados = item.get("ativo"), (item.get("dados_reais") or {})
        nome = MAPEAMENTO_TICKERS.get(ativo_raw, ativo_raw)
        ativos_map[nome] = {"preco": float(dados.get("close") or 0.0), "variacao_pct": float(dados.get("change_percent") or 0.0), "ticker_original": ativo_raw, "status": item.get("status", "OK"), "fonte": item.get("fonte") or "DESCONHECIDA", "timestamp_coleta": item.get("timestamp")}
    with open(FILE_UNIFICADO, "w", encoding="utf-8") as f: json.dump({"metadata": {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "total_ativos": len(ativos_map)}, "ativos": ativos_map}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ Unificado: {FILE_UNIFICADO}")

def _montar_win_wdo_mt5(coletas: List[dict]) -> bool:
    mt5_json = {}
    if os.path.exists(FILE_MT5_V2):
        try:
            with open(FILE_MT5_V2, "r", encoding="utf-8") as f: mt5_json = json.load(f)
        except: pass
    lasts = capturar_last_do_mt5()
    ativos_mt5 = (mt5_json.get("ativos") or {})
    ts = datetime.now().isoformat()
    fora_pregao = esta_fora_do_pregao()
    montou = False
    fech_brapi = {item["ativo"]: float((item.get("dados_reais") or {}).get("close")) for item in coletas if item.get("ativo") in ("B3_FECHAMENTO_WIN", "B3_FECHAMENTO_WDO") and item.get("status") == "OK" and (item.get("dados_reais") or {}).get("close")}
    freeze_map = {}
    cache_itens = []
    if not fora_pregao:
        if os.path.exists(FILE_LAST_TICK_CONGELADO):
            try:
                with open(FILE_LAST_TICK_CONGELADO, "r", encoding="utf-8") as f: freeze_map = json.load(f).get("ticks") or {}
            except: pass
        if not freeze_map:
            for arq in (FILE_RAM, FILE_ROM0):
                if os.path.exists(arq):
                    try:
                        with open(arq, "r", encoding="utf-8") as f: cache_itens = json.load(f).get("coletas") or []
                        if cache_itens: break
                    except: pass

    for prefixo, (ativo_last, ativo_fut) in {"WIN": ("WIN_LAST_TICK", "BMFBOVESPA:WIN1!"), "WDO": ("WDO_LAST_TICK", "BMFBOVESPA:WDO1!")}.items():
        info = ativos_mt5.get(prefixo) or {}
        last_val = (lasts.get(prefixo) or {}).get("last") or info.get("last")
        if (last_val is None or float(last_val) <= 0) and fech_brapi.get(f"B3_FECHAMENTO_{prefixo}"):
            last_val = fech_brapi[f"B3_FECHAMENTO_{prefixo}"]
            print(f"   🔄 {prefixo}: MT5 sem last — usando brapi")

        if last_val is not None and float(last_val) > 0:
            last_val, last_real = float(last_val), float(last_val)
            close_d1 = info.get("close")
            if close_d1 and float(close_d1) > 0: last_real = float(close_d1)
            prev_c, var_pct = info.get("prev_close") or info.get("session_close"), info.get("change_percent")
            bid, ask = info.get("bid"), info.get("ask")
            if var_pct is None and prev_c and float(prev_c) > 0: var_pct = round(((last_val / float(prev_c)) - 1) * 100, 4)
            last_fut = last_val
            if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) and bid > 0 and ask > 0 and (last_fut < bid or last_fut > ask):
                last_fut = round((float(bid) + float(ask)) / 2.0, 1)
            
            ohlc_fut = {"close": last_fut, "open": info.get("open"), "high": info.get("high"), "low": info.get("low"), "change_percent": var_pct, "volume": info.get("volume_d1") or info.get("volume"), "fechamento_anterior": float(prev_c) if prev_c else None}
            ohlc_last = dict(ohlc_fut)
            ohlc_last["close"] = last_real
            if prev_c and float(prev_c) > 0: ohlc_last["change_percent"] = round(((last_real / float(prev_c)) - 1) * 100, 4)

            coletas.append({"ativo": ativo_fut, "fonte": "MT5", "timestamp": ts, "status": "OK", "dados_reais": ohlc_fut})
            if prefixo == "WIN": montou = True

            if fora_pregao:
                coletas.append({"ativo": ativo_last, "fonte": "MT5", "timestamp": ts, "status": "OK", "dados_reais": ohlc_last})
                if "ticks_para_congelar" not in locals(): ticks_para_congelar = {}
                ticks_para_congelar[ativo_last] = coletas[-1]
            else:
                frozen = freeze_map.get(ativo_last)
                if frozen and (frozen.get("dados_reais") or {}).get("close"):
                    frozen["timestamp"], frozen["fonte"] = ts, "CONGELADO"
                    coletas.append(frozen)
                else:
                    for it in cache_itens:
                        if it.get("ativo") == ativo_last:
                            it["timestamp"], it["fonte"] = ts, "CACHE"
                            coletas.append(it)
                            break
    if fora_pregao and locals().get("ticks_para_congelar"):
        atual = {}
        if os.path.exists(FILE_LAST_TICK_CONGELADO):
            try:
                with open(FILE_LAST_TICK_CONGELADO, "r", encoding="utf-8") as f: atual = json.load(f).get("ticks") or {}
            except: pass
        atual.update(ticks_para_congelar)
        with open(FILE_LAST_TICK_CONGELADO, "w", encoding="utf-8") as f:
            json.dump({"timestamp_congelamento": datetime.now().isoformat(), "fonte": "MT5", "ticks": atual}, f, ensure_ascii=False, indent=2)
    return montou


# ------------------------------------------------------------
# PIPELINE PRINCIPAL
# ------------------------------------------------------------
def executar_pipeline_coleta() -> None:
    t0 = datetime.now()
    is_ram = "--ram" in sys.argv
    arquivo_destino = executar_rotacao_memoria(is_ram)
    print(f"[{t0.strftime('%H:%M:%S')}] Iniciando coleta paralela...")

    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_ptax = ex.submit(coletar_bacen_ptax)
        fut_ajuste_brapi = ex.submit(coletar_ajuste_brapi)
        fut_ajuste_tv = ex.submit(coletar_ajuste_oficial, True)
        fut_tv = ex.submit(coletar_tradingview)
        fut_fh = ex.submit(coletar_finnhub)
        ptax, ajustes_brapi, ajustes_tv, tv_dados, finnhub_dados = fut_ptax.result(), fut_ajuste_brapi.result(), fut_ajuste_tv.result(), fut_tv.result(), fut_fh.result()

    coletas: List[dict] = []
    if ajustes_brapi: coletas.extend(ajustes_brapi)
    else: coletas.extend(ajustes_tv)
    coletas.extend([ptax] + tv_dados + finnhub_dados)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando MT5 (WIN_FUT sempre)...")
    try:
        from Coletor_MT5_v2_2 import executar_coleta_mt5_v2
        executar_coleta_mt5_v2()
    except: pass

    coletas.extend(coletar_mt5_acoes_b3())
    _montar_win_wdo_mt5(coletas)

    with open(arquivo_destino, "w", encoding="utf-8") as f: json.dump({"metadata_coleta": {"timestamp_coleta": datetime.now().isoformat(), "total_ativos": len(coletas), "fora_do_pregao": esta_fora_do_pregao()}, "coletas": coletas}, f, ensure_ascii=False, separators=(",", ":"))
    if not is_ram:
        with open(FILE_RAM, "w", encoding="utf-8") as f: json.dump({"metadata_coleta": {"timestamp_coleta": datetime.now().isoformat(), "total_ativos": len(coletas), "fora_do_pregao": esta_fora_do_pregao()}, "coletas": coletas}, f, ensure_ascii=False, separators=(",", ":"))
    
    gerar_arquivo_unificado(coletas)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Coleta OK | {len(coletas)} itens | {'FORA' if esta_fora_do_pregao() else 'DENTRO'} do pregão")

if __name__ == "__main__":
    print("=" * 60)
    print(" COLETOR TURBO v2.8 — Coleta Contínua (Pre/Regular/Post)")
    print("=" * 60)
    executar_pipeline_coleta()