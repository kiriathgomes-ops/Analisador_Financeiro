#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor_SMC_Regras.py
===================
Motor de regras SMC/ICT SEM IA com Filtro de Volume Real, Expansão e Níveis Institucionais (POC/VWAP do dia anterior).

Detecta:
- Swing High / Swing Low
- BOS (Break of Structure) e CHoCH (Change of Character)
- Fair Value Gaps (FVG) com filtro de expansão e volume real
- Order Blocks (OB) validados por volume/impulso e confluência com POC
- Liquidez (equal highs / equal lows + POC institucional de ontem)

Entrada: lista/DataFrame de candles OHLCV
Saída: JSON estruturado compatível com o pipeline
      (Coletas/AnaliseGraficaSMC_Regras.json)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# ============================================================
# FIX: FORÇA UTF-8 NO TERMINAL WINDOWS
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ============================================================
# CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVOS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"

if not COLETAS_DIR.exists():
    alt = BASE_DIR.parent / "Coletas"
    if alt.exists():
        COLETAS_DIR = alt

FILE_MT5_DADOS = COLETAS_DIR / "Dados_MT5_v2_2.json"
ARQUIVO_SAIDA = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"


@dataclass
class ConfigSMC:
    swing_left: int = 2
    swing_right: int = 2
    fvg_min_pontos: float = 20.0
    eq_tol_pontos: float = 15.0
    max_niveis: int = 12
    max_fvgs: int = 8
    max_obs: int = 6
    lookback: int = 120
    
    # CONFIGURAÇÕES PARA FILTRO DE VOLUME E EXPANSÃO
    vol_ma_period: int = 20
    vol_factor_min: float = 1.2
    expansion_factor_min: float = 1.3


CONFIG = ConfigSMC()


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    idx: int = 0


@dataclass
class Swing:
    idx: int
    preco: float
    tipo: str  # "HIGH" | "LOW"
    time: str = ""


@dataclass
class FVG:
    tipo: str  # "COMPRA" | "VENDA"
    superior: float
    inferior: float
    idx: int
    time: str = ""
    preenchido: bool = False


@dataclass
class OrderBlock:
    tipo: str  # "COMPRA" | "VENDA"
    high: float
    low: float
    preco_ref: float
    idx: int
    time: str = ""


@dataclass
class EventoEstrutura:
    tipo: str  # "BOS" | "CHOCH"
    direcao: str  # "ALTA" | "BAIXA"
    preco: float
    idx: int
    time: str = ""


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def normalizar_candles(dados: Any) -> List[Candle]:
    rows: List[Any] = []
    if hasattr(dados, "to_dict") and hasattr(dados, "columns"):
        try:
            rows = dados.to_dict(orient="records")
        except Exception:
            rows = list(dados)
    else:
        rows = list(dados)

    candles: List[Candle] = []
    for row in rows:
        if isinstance(row, dict):
            o = row.get("open", row.get("Open", row.get("o")))
            h = row.get("high", row.get("High", row.get("h")))
            l = row.get("low", row.get("Low", row.get("l")))
            c = row.get("close", row.get("Close", row.get("c")))
            t = row.get("time", row.get("Time", row.get("datetime", row.get("date", ""))))
            vol = row.get("real_volume", row.get("volume", row.get("Volume", row.get("tick_volume", 0))))
        elif isinstance(row, (list, tuple)) and len(row) >= 5:
            if isinstance(row[0], (int, float)) and len(row) >= 5 and not isinstance(row[1], str):
                t, o, h, l, c = "", row[0], row[1], row[2], row[3]
                vol = row[4] if len(row) > 4 else 0
            else:
                t = row[0]
                o, h, l, c = row[1], row[2], row[3], row[4]
                vol = row[5] if len(row) > 5 else 0
        else:
            continue

        o, h, l, c = _to_float(o), _to_float(h), _to_float(l), _to_float(c)
        if h <= 0 or l <= 0 or c <= 0:
            continue
        if h < l:
            h, l = l, h

        candles.append(
            Candle(
                time=str(t) if t is not None else "",
                open=o,
                high=h,
                low=l,
                close=c,
                volume=_to_float(vol),
                idx=len(candles),
            )
        )

    return candles


def aplicar_lookback(candles: List[Candle], lookback: int) -> List[Candle]:
    if lookback and lookback > 0 and len(candles) > lookback:
        slice_c = candles[-lookback:]
        for i, c in enumerate(slice_c):
            c.idx = i
        return slice_c
    return candles


def calcular_metricas_medias(candles: List[Candle], idx_atual: int, periodo: int = CONFIG.vol_ma_period) -> Tuple[float, float]:
    inicio = max(0, idx_atual - periodo)
    janela = candles[inicio:idx_atual]
    
    if not janela:
        return 0.0, 0.0

    media_vol = sum(c.volume for c in janela) / len(janela)
    media_corpo = sum(abs(c.close - c.open) for c in janela) / len(janela)

    return media_vol, media_corpo


def e_candle_expansao(candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG) -> bool:
    corpo = abs(candle.close - candle.open)
    vol_ok = (candle.volume >= media_vol * config.vol_factor_min) if media_vol > 0 else False
    corpo_ok = (corpo >= media_corpo * config.expansion_factor_min) if media_corpo > 0 else False

    if media_vol == 0:
        return corpo_ok

    return vol_ok or corpo_ok

#############
def calcular_poc_vwap(candles: List[Candle], ativo: str) -> Dict[str, float]:
    """
    Calcula a VWAP e a POC (Point of Control) real do dia anterior,
    distribuindo o volume de cada candle entre sua Mínima e Máxima (Volume Profile correto).
    """
    if len(candles) < 20:
        return {"poc": 0.0, "vwap": 0.0}
        
    df = pd.DataFrame([c.__dict__ for c in candles])
    df['time_dt'] = pd.to_datetime(df['time'])
    df['date'] = df['time_dt'].dt.date
    
    datas_unicas = sorted(df['date'].unique())
    hoje = datetime.now().date()
    
    # Filtra apenas dias estritamente anteriores a hoje (funciona no pré-pregão e pregão aberto)
    datas_passadas = [d for d in datas_unicas if d < hoje]
    
    if datas_passadas:
        data_alvo = datas_passadas[-1]
    elif datas_unicas:
        data_alvo = datas_unicas[-1]
    else:
        return {"poc": 0.0, "vwap": 0.0}
        
    df_ontem = df[df['date'] == data_alvo].copy()
    
    if df_ontem.empty:
        df_ontem = df

    # 1. Cálculo da VWAP padrão institucional
    df_ontem['preco_tipico'] = (df_ontem['high'] + df_ontem['low'] + df_ontem['close']) / 3
    df_ontem['vol_financeiro'] = df_ontem['preco_tipico'] * df_ontem['volume']
    
    vol_total = df_ontem['volume'].sum()
    vwap = df_ontem['vol_financeiro'].sum() / vol_total if vol_total > 0 else 0.0
    
    # 2. Cálculo da POC usando Perfil de Volume Distribuído (High-Low)
    tick_size = 5 if "WIN" in ativo else 0.5
    profile_dict = {}
    
    for _, row in df_ontem.iterrows():
        h = row['high']
        l = row['low']
        v = row['volume']
        
        if h <= 0 or l <= 0 or v <= 0:
            continue
            
        if h < l:
            h, l = l, h
            
        # Distribui o volume uniformemente entre o Low e o High da vela
        bins_candle = np.arange(
            np.floor(l / tick_size) * tick_size, 
            np.ceil(h / tick_size) * tick_size + tick_size, 
            tick_size
        )
        
        if len(bins_candle) > 0:
            vol_por_bin = v / len(bins_candle)
            for b in bins_candle:
                b_rounded = round(float(b), 1)
                profile_dict[b_rounded] = profile_dict.get(b_rounded, 0.0) + vol_por_bin

    # A verdadeira POC é o preço com o maior acúmulo volumétrico distribuído
    if profile_dict:
        poc = max(profile_dict, key=profile_dict.get)
    else:
        poc = 0.0

    return {"poc": float(poc), "vwap": round(float(vwap), 1)}
###

def detectar_swings(candles: List[Candle], left: int = CONFIG.swing_left, right: int = CONFIG.swing_right) -> List[Swing]:
    swings: List[Swing] = []
    n = len(candles)
    if n < left + right + 1:
        return swings

    for i in range(left, n - right):
        window = candles[i - left : i + right + 1]
        highs = [c.high for c in window]
        lows = [c.low for c in window]
        mid = candles[i]

        if mid.high >= max(highs) and highs.count(mid.high) == 1:
            swings.append(Swing(idx=i, preco=mid.high, tipo="HIGH", time=mid.time))
        if mid.low <= min(lows) and lows.count(mid.low) == 1:
            swings.append(Swing(idx=i, preco=mid.low, tipo="LOW", time=mid.time))

    return swings


def detectar_bos_choch(candles: List[Candle], swings: List[Swing]) -> Tuple[List[EventoEstrutura], str]:
    eventos: List[EventoEstrutura] = []
    if len(swings) < 4 or len(candles) < 5:
        return eventos, "LATERAL"

    highs = [s for s in swings if s.tipo == "HIGH"]
    lows = [s for s in swings if s.tipo == "LOW"]

    bias = "LATERAL"
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1].preco > highs[-2].preco
        hl = lows[-1].preco > lows[-2].preco
        lh = highs[-1].preco < highs[-2].preco
        ll = lows[-1].preco < lows[-2].preco
        if hh and hl:
            bias = "ALTA"
        elif lh and ll:
            bias = "BAIXA"

    last_high: Optional[Swing] = None
    last_low: Optional[Swing] = None
    tendencia_atual = bias if bias != "LATERAL" else "LATERAL"

    for s in swings:
        if s.tipo == "HIGH":
            if last_high:
                for c in candles[s.idx :]:
                    if c.close > last_high.preco:
                        tipo_ev = "BOS" if tendencia_atual == "ALTA" else "CHOCH"
                        eventos.append(EventoEstrutura(tipo=tipo_ev, direcao="ALTA", preco=last_high.preco, idx=c.idx, time=c.time))
                        tendencia_atual = "ALTA"
                        break
            last_high = s

        if s.tipo == "LOW":
            if last_low:
                for c in candles[s.idx :]:
                    if c.close < last_low.preco:
                        tipo_ev = "BOS" if tendencia_atual == "BAIXA" else "CHOCH"
                        eventos.append(EventoEstrutura(tipo=tipo_ev, direcao="BAIXA", preco=last_low.preco, idx=c.idx, time=c.time))
                        tendencia_atual = "BAIXA"
                        break
            last_low = s

    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias


def detectar_fvg(candles: List[Candle], config: ConfigSMC = CONFIG) -> List[FVG]:
    fvgs: List[FVG] = []
    n = len(candles)
    if n < 3:
        return fvgs

    for i in range(2, n):
        c0, c1, c2 = candles[i - 2], candles[i - 1], candles[i]
        media_vol, media_corpo = calcular_metricas_medias(candles, i - 1, config.vol_ma_period)
        impulso_valido = e_candle_expansao(c1, media_vol, media_corpo, config)

        if not impulso_valido:
            continue

        if c2.low > c0.high and (c2.low - c0.high) >= config.fvg_min_pontos:
            fvgs.append(FVG(tipo="COMPRA", superior=c2.low, inferior=c0.high, idx=i, time=c2.time))

        if c2.high < c0.low and (c0.low - c2.high) >= config.fvg_min_pontos:
            fvgs.append(FVG(tipo="VENDA", superior=c0.low, inferior=c2.high, idx=i, time=c2.time))

    for fvg in fvgs:
        for c in candles[fvg.idx + 1 :]:
            if fvg.tipo == "COMPRA" and c.low <= fvg.inferior:
                fvg.preenchido = True
                break
            if fvg.tipo == "VENDA" and c.high >= fvg.superior:
                fvg.preenchido = True
                break

    return fvgs


def detectar_order_blocks(candles: List[Candle], swings: List[Swing], config: ConfigSMC = CONFIG) -> List[OrderBlock]:
    obs: List[OrderBlock] = []
    n = len(candles)
    if n < 5 or len(swings) < 2:
        return obs

    for s in swings[-8:]:
        i = s.idx
        if i < 1 or i >= n - 1:
            continue

        cand = candles[i]
        prev = candles[i - 1]
        ob_cand = prev if (prev.close < prev.open if s.tipo == "LOW" else prev.close > prev.open) else cand

        media_vol, media_corpo = calcular_metricas_medias(candles, i, config.vol_ma_period)
        candle_saida = candles[i + 1] if (i + 1) < n else cand
        tem_expansao = e_candle_expansao(candle_saida, media_vol, media_corpo, config)

        if not tem_expansao:
            continue

        if s.tipo == "LOW":
            if any(c.close > cand.high for c in candles[i + 1 : min(i + 4, n)]):
                obs.append(OrderBlock(tipo="COMPRA", high=ob_cand.high, low=ob_cand.low, preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1), idx=ob_cand.idx, time=ob_cand.time))

        if s.tipo == "HIGH":
            if any(c.close < cand.low for c in candles[i + 1 : min(i + 4, n)]):
                obs.append(OrderBlock(tipo="VENDA", high=ob_cand.high, low=ob_cand.low, preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1), idx=ob_cand.idx, time=ob_cand.time))

    unicos: List[OrderBlock] = []
    for ob in obs:
        if not any(abs(ob.preco_ref - u.preco_ref) < 10 for u in unicos):
            unicos.append(ob)
    return unicos


def detectar_liquidez(swings: List[Swing], tol: float = CONFIG.eq_tol_pontos) -> Dict[str, List[float]]:
    bsl: List[float] = []
    ssl: List[float] = []

    highs = [s for s in swings if s.tipo == "HIGH"]
    lows = [s for s in swings if s.tipo == "LOW"]

    for i in range(len(highs)):
        for j in range(i + 1, len(highs)):
            if abs(highs[i].preco - highs[j].preco) <= tol:
                nivel = round((highs[i].preco + highs[j].preco) / 2, 1)
                if not any(abs(nivel - x) <= tol for x in bsl):
                    bsl.append(nivel)

    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            if abs(lows[i].preco - lows[j].preco) <= tol:
                nivel = round((lows[i].preco + lows[j].preco) / 2, 1)
                if not any(abs(nivel - x) <= tol for x in ssl):
                    ssl.append(nivel)

    bsl.sort(reverse=True)
    ssl.sort()
    return {"bsl": bsl[:6], "ssl": ssl[:6]}


def analisar_smc(dados_candles: Any, ativo: str = "WIN", timeframe: str = "5m", config: ConfigSMC = CONFIG) -> Dict[str, Any]:
    candles = normalizar_candles(dados_candles)
    
    # Coleta de Métricas Institucionais (POC e VWAP de ONTEM) antes do lookback estrutural
    inst_niveis = calcular_poc_vwap(candles, ativo)
    poc = inst_niveis["poc"]
    vwap = inst_niveis["vwap"]

    candles = aplicar_lookback(candles, config.lookback)

    if len(candles) < 10:
        return {
            "timestamp": datetime.now().isoformat(),
            "ativo": ativo,
            "timeframe": timeframe,
            "fonte": "regras_smc",
            "erro": "Candles insuficientes (mínimo 10)",
            "bias_direcional": "LATERAL",
            "direcao_estrutura": "LATERAL",
            "bos": False,
            "choch": False,
            "confianca_visual": 0,
        }

    swings = detectar_swings(candles, config.swing_left, config.swing_right)
    eventos, bias = detectar_bos_choch(candles, swings)
    
    fvgs = detectar_fvg(candles, config)
    obs = detectar_order_blocks(candles, swings, config)
    liq = detectar_liquidez(swings, config.eq_tol_pontos)

    bos = any(e.tipo == "BOS" for e in eventos[-3:])
    choch = any(e.tipo == "CHOCH" for e in eventos[-3:])

    fvgs_abertos = [f for f in fvgs if not f.preenchido][-config.max_fvgs :]
    obs = obs[-config.max_obs :]

    preco_atual = candles[-1].close

    # Confluência Institucional de Order Block com POC do dia anterior
    ob_confluente = False
    if obs:
        ob_recente = obs[-1]
        distancia_poc = abs(ob_recente.preco_ref - poc)
        if ("WIN" in ativo and distancia_poc <= 100) or ("WDO" in ativo and distancia_poc <= 10):
            ob_confluente = True

    estruturas: List[str] = []
    for s in swings[-config.max_niveis :]:
        label = "Swing High" if s.tipo == "HIGH" else "Swing Low"
        estruturas.append(f"{s.preco:.0f}: {label}")

    for ob in obs:
        estruturas.append(f"{ob.preco_ref:.0f}: OB {ob.tipo} ({ob.low:.0f}-{ob.high:.0f})")

    for fvg in fvgs_abertos:
        estruturas.append(f"{(fvg.superior + fvg.inferior) / 2:.0f}: FVG {fvg.tipo} ({fvg.inferior:.0f}-{fvg.superior:.0f})")

    liquidez_txt: List[str] = [f"POC Institucional (Ontem): {poc:.0f}", f"VWAP (Ontem): {vwap:.0f}"]
    for p in liq["bsl"]:
        liquidez_txt.append(f"BSL: {p:.0f} (equal highs / liquidez de compra acima)")
    for p in liq["ssl"]:
        liquidez_txt.append(f"SSL: {p:.0f} (equal lows / liquidez de venda abaixo)")

    cenarios: List[str] = []
    if bias == "BAIXA":
        res = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        fvg_v = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
        zona = res.preco_ref if res else (fvg_v.superior if fvg_v else preco_atual)
        alvo = liq["ssl"][0] if liq["ssl"] else preco_atual * 0.99
        cenarios.append(f"Cenário Vendedor: rejeição na região {zona:.0f} (OB/FVG validado por volume) visando {alvo:.0f}.")
    elif bias == "ALTA":
        dem = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        fvg_c = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
        zona = dem.preco_ref if dem else (fvg_c.inferior if fvg_c else preco_atual)
        alvo = liq["bsl"][0] if liq["bsl"] else preco_atual * 1.01
        cenarios.append(f"Cenário Comprador: defesa na região {zona:.0f} (OB/FVG validado por volume) visando {alvo:.0f}.")
    else:
        cenarios.append("Cenário Lateral: aguardar BOS com fechamento fora da faixa recente.")

    conf = 40
    if bias in ("ALTA", "BAIXA"):
        conf += 20
    if bos:
        conf += 15
    if choch:
        conf += 5
    if fvgs_abertos:
        conf += 10
    if obs:
        conf += 10
    if ob_confluente:
        conf += 15  # Bônus institucional por alinhar OB com a POC de ontem
    conf = min(95, conf)

    entrada, stop = None, None
    alvos: List[float] = []

    if bias == "BAIXA" and obs:
        ob_v = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        if ob_v:
            entrada = round(ob_v.low, 0)
            stop = round(ob_v.high + 50, 0)
            if liq["ssl"]:
                alvos = [round(x, 0) for x in liq["ssl"][:2]]
    elif bias == "ALTA" and obs:
        ob_c = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        if ob_c:
            entrada = round(ob_c.high, 0)
            stop = round(ob_c.low - 50, 0)
            if liq["bsl"]:
                alvos = [round(x, 0) for x in liq["bsl"][:2]]

    return {
        "timestamp": datetime.now().isoformat(),
        "ativo": ativo,
        "timeframe": timeframe,
        "fonte": "regras_smc",
        "preco_atual": preco_atual,
        "timeframes_identificados": timeframe,
        "bias_direcional": bias,
        "direcao_estrutura": bias,
        "bos": bos,
        "choch": choch,
        "confianca_visual": conf,
        "niveis_institucionais": {
            "poc_ontem": poc,
            "vwap_ontem": vwap,
            "ob_alinhado_com_poc": ob_confluente
        },
        "order_blocks": [{"tipo": o.tipo, "preco": o.preco_ref, "high": o.high, "low": o.low} for o in obs],
        "fair_value_gaps": [{"tipo": f.tipo, "superior": f.superior, "inferior": f.inferior, "preenchido": f.preenchido} for f in fvgs_abertos],
        "liquidez": liq,
        "eventos_estrutura": [{"tipo": e.tipo, "direcao": e.direcao, "preco": e.preco, "time": e.time} for e in eventos[-6:]],
        "swings_recentes": [{"tipo": s.tipo, "preco": s.preco, "time": s.time} for s in swings[-10:]],
        "estruturas_coletadas": estruturas[-config.max_niveis :],
        "liquidez_relevante": liquidez_txt,
        "zonas_de_interesse_e_cenarios": cenarios,
        "entrada_sugerida": entrada,
        "stop_sugerido": stop,
        "alvos": alvos,
        "metadados": {
            "n_candles": len(candles),
            "n_swings": len(swings),
            "n_fvgs_abertos": len(fvgs_abertos),
            "n_obs": len(obs),
            "filtro_volume_real_aplicado": True,
            "config": asdict(config),
        },
    }


def salvar_resultado(resultado: Dict[str, Any], caminho: Optional[Path] = None) -> Path:
    caminho = caminho or ARQUIVO_SAIDA
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    return caminho


def _candidatos_simbolo(symbol: str) -> List[str]:
    s = (symbol or "").strip().upper()
    candidatos: List[str] = []

    def add(x: str):
        if x and x not in candidatos:
            candidatos.append(x)

    add(symbol)
    add(s)

    if s.startswith("WIN") or s in ("", "WIN", "WIN$"):
        for c in ("WIN$", "WIN$N", "WIN@N", "WIN", "WINc"):
            add(c)
        meses = "FGHJKMNQUVXZ"
        ano = datetime.now().year % 100
        for m in meses:
            add(f"WIN{m}{ano:02d}")
            add(f"WIN{m}{ano + 1:02d}")

    if FILE_MT5_DADOS.exists():
        try:
            with open(FILE_MT5_DADOS, "r", encoding="utf-8") as f:
                data = json.load(f)
            contratos = data.get("contratos", {})
            if isinstance(contratos, dict):
                for nome in contratos.keys():
                    add(str(nome))
        except Exception:
            pass

    return candidatos


def carregar_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 300) -> Tuple[List[Dict[str, Any]], str]:
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise RuntimeError("MetaTrader5 não instalado.") from e

    if not mt5.initialize():
        raise RuntimeError(f"Falha ao inicializar MT5: {mt5.last_error()}")

    tf_map = {1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15}
    tf = tf_map.get(timeframe_min, mt5.TIMEFRAME_M5)

    candidatos = _candidatos_simbolo(symbol)
    rates, simbolo_ok = None, None

    for sym in candidatos:
        info = mt5.symbol_info(sym)
        if info is None:
            continue
        if not info.visible:
            mt5.symbol_select(sym, True)

        r = mt5.copy_rates_from_pos(sym, tf, 0, qtd)
        if r is not None and len(r) > 0:
            rates = r
            simbolo_ok = sym
            break

    if rates is None or simbolo_ok is None:
        mt5.shutdown()
        raise RuntimeError(f"Sem dados no MT5 para o símbolo informado: {symbol}")

    out = []
    for r in rates:
        v_real = 0.0
        try:
            if "real_volume" in r.dtype.names:
                v_real = float(r["real_volume"])
        except Exception:
            pass
            
        if v_real <= 0:
            try:
                if "tick_volume" in r.dtype.names:
                    v_real = float(r["tick_volume"])
            except Exception:
                pass

        out.append({
            "time": datetime.fromtimestamp(r["time"]).isoformat(),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": v_real,
        })

    mt5.shutdown()
    return out, simbolo_ok