#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor_SMC_Regras.py
===================
Motor de regras SMC/ICT SEM IA — Versão 2.1 (Refatorada + Bugfixes)

Melhorias v2.0:
- Order Blocks validados por BOS/CHoCH posterior
- Cascata de entradas: OB → FVG → Preço atual
- Timezone BRT explícita (MT5 retorna UTC)
- Tick size configurável por ativo (sem hardcode)
- Expansão FORTE (volume AND corpo) vs FRACA (OR)
- Equal Highs/Lows detectados como liquidez confirmada
- Confiança ponderada por pesos (0-100 normalizado)
- Logging estruturado
- Histórico opcional de saídas
- CLI com argparse para execução isolada

Bugfixes v2.1:
- Alvos filtrados pelo lado correto (compra=acima, venda=abaixo)
- Stop mínimo por ATR (evita stop apertado em M5)
- Fallback de OBs brutos quando nenhum valida por BOS/CHoCH
- Filtro de OB mínimo (range < 30 pts = ruído)
- Alerta de divergência Macro × SMC
- Janela de validação OB ampliada (40 candles)
- Distância OB↔POC ampliada (300 WIN / 30 WDO)

Entrada: lista/DataFrame de candles OHLCV
Saída: JSON estruturado em Coletas/AnaliseGraficaSMC_Regras.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
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
# LOGGING ESTRUTURADO
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MotorSMC")

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
HISTORICO_SMC_DIR = COLETAS_DIR / "Historico_SMC"
METRICAS_FILE = COLETAS_DIR / "Metricas_Calculadas.json"

# Timezone Brasil
BRT = timezone(timedelta(hours=-3))


# ============================================================
# CONFIGURAÇÃO
# ============================================================
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

    # Filtro de volume e expansão
    vol_ma_period: int = 20
    vol_factor_min: float = 1.2
    expansion_factor_min: float = 1.3

    # POC/VWAP
    tick_size_default: float = 5.0
    tick_size_map: Dict[str, float] = field(
        default_factory=lambda: {
            "WIN": 5.0,
            "WDO": 0.5,
            "VALE3": 0.01,
            "PETR4": 0.01,
            "ITUB4": 0.01,
            "BBAS3": 0.01,
            "BBDC4": 0.01,
            "B3SA3": 0.01,
            "ES": 0.25,
            "NQ": 0.25,
        }
    )

    # Validação de OB
    ob_validacao_janela: int = 40
    ob_min_range: float = 30.0
    ob_fallback_brutos: bool = True

    # Deduplicação de OBs por ativo (threshold em pontos)
    # WIN tem tick de 5 pts → OBs separados por <50 pts são o mesmo bloco
    # WDO tem tick de 0.5 pts → 5 pts já é generoso
    dedup_ob_dist: Dict[str, float] = field(
        default_factory=lambda: {
            "WIN": 50.0,
            "WDO": 5.0,
        }
    )
    dedup_ob_dist_default: float = 10.0

    # Confluência OB ↔ POC
    ob_poc_dist_win: float = 300.0
    ob_poc_dist_wdo: float = 30.0

    # Stop mínimo (proteção contra ruído M5)
    stop_min_dist: float = 150.0
    stop_atr_mult: float = 0.8
    stop_atr_period: int = 20


CONFIG = ConfigSMC()


# ============================================================
# DATACLASSES
# ============================================================
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
    tipo: str  # "HIGH" | "LOW" | "HIGH_EQ" | "LOW_EQ"
    time: str = ""


@dataclass
class FVG:
    tipo: str
    superior: float
    inferior: float
    idx: int
    time: str = ""
    preenchido: bool = False


@dataclass
class OrderBlock:
    tipo: str
    high: float
    low: float
    preco_ref: float
    idx: int
    time: str = ""
    validado_por: str = ""  # "BOS" | "CHOCH" | "FALLBACK" | ""


@dataclass
class EventoEstrutura:
    tipo: str  # "BOS" | "CHOCH"
    direcao: str  # "ALTA" | "BAIXA"
    preco: float
    idx: int
    time: str = ""


# ============================================================
# HELPERS
# ============================================================
def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _tick_size_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """Retorna o tick size adequado para o ativo."""
    ativo_up = (ativo or "").upper()
    for chave, tick in config.tick_size_map.items():
        if chave in ativo_up:
            return tick
    return config.tick_size_default


def _dedup_dist_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """
    Retorna a distancia minima (em pontos) para considerar dois OBs distintos.

    WIN: 50 pts (blocos muito proximos sao o mesmo OB visto de angulos diferentes)
    WDO: 5 pts
    Default: 10 pts
    """
    ativo_up = (ativo or "").upper()
    for chave, dist in config.dedup_ob_dist.items():
        if chave in ativo_up:
            return dist
    return config.dedup_ob_dist_default


# ============================================================
# NORMALIZAÇÃO DE CANDLES
# ============================================================
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
            if isinstance(row[0], (int, float)) and not isinstance(row[1], str):
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


# ============================================================
# MÉTRICAS DE VOLUME / EXPANSÃO
# ============================================================
def calcular_metricas_medias(
    candles: List[Candle], idx_atual: int, periodo: int = CONFIG.vol_ma_period
) -> Tuple[float, float]:
    inicio = max(0, idx_atual - periodo)
    janela = candles[inicio:idx_atual]

    if not janela:
        return 0.0, 0.0

    media_vol = sum(c.volume for c in janela) / len(janela)
    media_corpo = sum(abs(c.close - c.open) for c in janela) / len(janela)
    return media_vol, media_corpo


def classificar_candle(
    candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG
) -> str:
    """
    Retorna:
    - "FORTE":  volume E corpo acima do limiar (expansão real)
    - "FRACO":  volume OU corpo acima do limiar (expansão parcial)
    - "NENHUM": sem expansão
    """
    corpo = abs(candle.close - candle.open)

    if media_vol <= 0 and media_corpo <= 0:
        return "NENHUM"

    vol_ok = media_vol > 0 and candle.volume >= media_vol * config.vol_factor_min
    corpo_ok = media_corpo > 0 and corpo >= media_corpo * config.expansion_factor_min

    if vol_ok and corpo_ok:
        return "FORTE"
    if vol_ok or corpo_ok:
        return "FRACO"
    return "NENHUM"


def e_candle_expansao(
    candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG
) -> bool:
    """Compatibilidade: aceita FRACO ou FORTE."""
    return classificar_candle(candle, media_vol, media_corpo, config) in ("FORTE", "FRACO")


# ============================================================
# POC / VWAP (dia anterior)
# ============================================================
def calcular_poc_vwap(candles: List[Candle], ativo: str, config: ConfigSMC = CONFIG) -> Dict[str, float]:
    """
    Calcula VWAP e POC do dia anterior.
    POC usa distribuição de volume entre High-Low (Volume Profile correto).
    Tick size vem do ConfigSMC, não é mais hardcoded.
    """
    if len(candles) < 20:
        return {"poc": 0.0, "vwap": 0.0}

    df = pd.DataFrame([c.__dict__ for c in candles])
    try:
        df["time_dt"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(BRT)
    except Exception:
        df["time_dt"] = pd.to_datetime(df["time"], errors="coerce")

    df["date"] = df["time_dt"].dt.date

    datas_unicas = sorted([d for d in df["date"].unique() if pd.notna(d)])
    hoje = datetime.now(BRT).date()

    datas_passadas = [d for d in datas_unicas if d < hoje]

    if datas_passadas:
        data_alvo = datas_passadas[-1]
    elif datas_unicas:
        data_alvo = datas_unicas[-1]
    else:
        return {"poc": 0.0, "vwap": 0.0}

    df_ontem = df[df["date"] == data_alvo].copy()
    if df_ontem.empty:
        df_ontem = df

    # 1. VWAP
    df_ontem["preco_tipico"] = (df_ontem["high"] + df_ontem["low"] + df_ontem["close"]) / 3
    df_ontem["vol_financeiro"] = df_ontem["preco_tipico"] * df_ontem["volume"]

    vol_total = df_ontem["volume"].sum()
    vwap = df_ontem["vol_financeiro"].sum() / vol_total if vol_total > 0 else 0.0

    # 2. POC (Volume Profile distribuído)
    tick_size = _tick_size_para(ativo, config)
    profile_dict: Dict[float, float] = {}

    for _, row in df_ontem.iterrows():
        h = row["high"]
        l = row["low"]
        v = row["volume"]

        if h <= 0 or l <= 0 or v <= 0:
            continue
        if h < l:
            h, l = l, h

        bins_candle = np.arange(
            np.floor(l / tick_size) * tick_size,
            np.ceil(h / tick_size) * tick_size + tick_size,
            tick_size,
        )

        if len(bins_candle) > 0:
            vol_por_bin = v / len(bins_candle)
            for b in bins_candle:
                b_rounded = round(float(b), 4)
                profile_dict[b_rounded] = profile_dict.get(b_rounded, 0.0) + vol_por_bin

    poc = max(profile_dict, key=profile_dict.get) if profile_dict else 0.0

    return {"poc": float(poc), "vwap": round(float(vwap), 1)}


# ============================================================
# SWINGS
# ============================================================
def detectar_swings(
    candles: List[Candle],
    left: int = CONFIG.swing_left,
    right: int = CONFIG.swing_right,
) -> List[Swing]:
    swings: List[Swing] = []
    n = len(candles)
    if n < left + right + 1:
        return swings

    for i in range(left, n - right):
        window = candles[i - left : i + right + 1]
        highs = [c.high for c in window]
        lows = [c.low for c in window]
        mid = candles[i]

        # HIGH — aceita equal highs
        if mid.high >= max(highs):
            tipo = "HIGH_EQ" if highs.count(mid.high) > 1 else "HIGH"
            swings.append(Swing(idx=i, preco=mid.high, tipo=tipo, time=mid.time))

        # LOW — aceita equal lows
        if mid.low <= min(lows):
            tipo = "LOW_EQ" if lows.count(mid.low) > 1 else "LOW"
            swings.append(Swing(idx=i, preco=mid.low, tipo=tipo, time=mid.time))

    return swings


def _so_highs(swings: List[Swing]) -> List[Swing]:
    return [s for s in swings if s.tipo.startswith("HIGH")]


def _so_lows(swings: List[Swing]) -> List[Swing]:
    return [s for s in swings if s.tipo.startswith("LOW")]


# ============================================================
# BOS / CHOCH
# ============================================================
def detectar_bos_choch(
    candles: List[Candle], swings: List[Swing]
) -> Tuple[List[EventoEstrutura], str]:
    eventos: List[EventoEstrutura] = []
    if len(swings) < 4 or len(candles) < 5:
        return eventos, "LATERAL"

    highs = _so_highs(swings)
    lows = _so_lows(swings)

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
        if s.tipo.startswith("HIGH"):
            if last_high:
                for c in candles[s.idx:]:
                    if c.close > last_high.preco:
                        tipo_ev = "BOS" if tendencia_atual == "ALTA" else "CHOCH"
                        eventos.append(
                            EventoEstrutura(
                                tipo=tipo_ev,
                                direcao="ALTA",
                                preco=last_high.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "ALTA"
                        break
            last_high = s

        if s.tipo.startswith("LOW"):
            if last_low:
                for c in candles[s.idx:]:
                    if c.close < last_low.preco:
                        tipo_ev = "BOS" if tendencia_atual == "BAIXA" else "CHOCH"
                        eventos.append(
                            EventoEstrutura(
                                tipo=tipo_ev,
                                direcao="BAIXA",
                                preco=last_low.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "BAIXA"
                        break
            last_low = s

    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias


# ============================================================
# FVG
# ============================================================
def detectar_fvg(candles: List[Candle], config: ConfigSMC = CONFIG) -> List[FVG]:
    fvgs: List[FVG] = []
    n = len(candles)
    if n < 3:
        return fvgs

    for i in range(2, n):
        c0, c1, c2 = candles[i - 2], candles[i - 1], candles[i]
        media_vol, media_corpo = calcular_metricas_medias(candles, i - 1, config.vol_ma_period)
        # Exige expansão FORTE para validar FVG
        if classificar_candle(c1, media_vol, media_corpo, config) != "FORTE":
            continue

        if c2.low > c0.high and (c2.low - c0.high) >= config.fvg_min_pontos:
            fvgs.append(
                FVG(tipo="COMPRA", superior=c2.low, inferior=c0.high, idx=i, time=c2.time)
            )

        if c2.high < c0.low and (c0.low - c2.high) >= config.fvg_min_pontos:
            fvgs.append(
                FVG(tipo="VENDA", superior=c0.low, inferior=c2.high, idx=i, time=c2.time)
            )

    # Marca FVGs preenchidos
    for fvg in fvgs:
        for c in candles[fvg.idx + 1:]:
            if fvg.tipo == "COMPRA" and c.low <= fvg.inferior:
                fvg.preenchido = True
                break
            if fvg.tipo == "VENDA" and c.high >= fvg.superior:
                fvg.preenchido = True
                break

    return fvgs


# ============================================================
# ORDER BLOCKS (com validação BOS/CHoCH + fallback + min range)
# ============================================================
def detectar_order_blocks(
    candles: List[Candle],
    swings: List[Swing],
    eventos_estrutura: List[EventoEstrutura],
    ativo: str = "WIN",
    config: ConfigSMC = CONFIG,
) -> List[OrderBlock]:
    obs_brutos: List[OrderBlock] = []
    n = len(candles)
    if n < 5 or len(swings) < 2:
        return obs_brutos

    for s in swings[-10:]:
        i = s.idx
        if i < 1 or i >= n - 1:
            continue

        cand = candles[i]
        prev = candles[i - 1]

        # OB é a última candle contrária
        if s.tipo.startswith("LOW"):
            ob_cand = prev if prev.close < prev.open else cand
        else:
            ob_cand = prev if prev.close > prev.open else cand

        # FILTRO: OB muito pequeno é ruído
        range_ob = ob_cand.high - ob_cand.low
        if range_ob < config.ob_min_range:
            continue

        media_vol, media_corpo = calcular_metricas_medias(candles, i, config.vol_ma_period)
        candle_saida = candles[i + 1] if (i + 1) < n else cand

        if not e_candle_expansao(candle_saida, media_vol, media_corpo, config):
            continue

        if s.tipo.startswith("LOW"):
            if any(c.close > cand.high for c in candles[i + 1 : min(i + 4, n)]):
                obs_brutos.append(
                    OrderBlock(
                        tipo="COMPRA",
                        high=ob_cand.high,
                        low=ob_cand.low,
                        preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1),
                        idx=ob_cand.idx,
                        time=ob_cand.time,
                    )
                )

        if s.tipo.startswith("HIGH"):
            if any(c.close < cand.low for c in candles[i + 1 : min(i + 4, n)]):
                obs_brutos.append(
                    OrderBlock(
                        tipo="VENDA",
                        high=ob_cand.high,
                        low=ob_cand.low,
                        preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1),
                        idx=ob_cand.idx,
                        time=ob_cand.time,
                    )
                )

    # ---- Validação: OB só é válido se houver BOS/CHoCH posterior
    obs_validados: List[OrderBlock] = []
    for ob in obs_brutos:
        direcao_alvo = "ALTA" if ob.tipo == "COMPRA" else "BAIXA"
        for e in eventos_estrutura:
            if (
                e.idx > ob.idx
                and e.idx <= ob.idx + config.ob_validacao_janela
                and e.direcao == direcao_alvo
            ):
                ob.validado_por = e.tipo
                obs_validados.append(ob)
                break

    # ---- LOG diagnóstico
    logger.info(
        f"OBs brutos: {len(obs_brutos)} | OBs validados por BOS/CHoCH: {len(obs_validados)}"
    )

    # ---- FALLBACK: se nenhum passou, usa os brutos
    if not obs_validados and obs_brutos and config.ob_fallback_brutos:
        logger.warning("Nenhum OB validado por BOS/CHoCH — usando brutos como fallback")
        for ob in obs_brutos:
            ob.validado_por = "FALLBACK"
        obs_validados = obs_brutos

    # ---- Deduplicação (threshold por ativo)
    dist_dedup = _dedup_dist_para(ativo, config)
    unicos: List[OrderBlock] = []
    for ob in obs_validados:
        if not any(
            abs(ob.preco_ref - u.preco_ref) < dist_dedup and ob.tipo == u.tipo
            for u in unicos
        ):
            unicos.append(ob)

    # Log diagnostico (ajuda a ver quantos OBs foram consolidados)
    if len(unicos) < len(obs_validados):
        logger.info(
            f"Dedup OB [{ativo}] (thr {dist_dedup:.0f} pts): "
            f"{len(obs_validados)} -> {len(unicos)}"
        )

    return unicos


# ============================================================
# LIQUIDEZ
# ============================================================
def detectar_liquidez(swings: List[Swing], tol: float = CONFIG.eq_tol_pontos) -> Dict[str, List[float]]:
    bsl: List[float] = []
    ssl: List[float] = []

    highs = _so_highs(swings)
    lows = _so_lows(swings)

    # Equal highs (BSL)
    for i in range(len(highs)):
        for j in range(i + 1, len(highs)):
            if abs(highs[i].preco - highs[j].preco) <= tol:
                nivel = round((highs[i].preco + highs[j].preco) / 2, 1)
                if not any(abs(nivel - x) <= tol for x in bsl):
                    bsl.append(nivel)

    # Equal lows (SSL)
    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            if abs(lows[i].preco - lows[j].preco) <= tol:
                nivel = round((lows[i].preco + lows[j].preco) / 2, 1)
                if not any(abs(nivel - x) <= tol for x in ssl):
                    ssl.append(nivel)

    # Swings marcados como *_EQ
    for s in highs:
        if s.tipo == "HIGH_EQ":
            nivel = round(s.preco, 1)
            if not any(abs(nivel - x) <= tol for x in bsl):
                bsl.append(nivel)

    for s in lows:
        if s.tipo == "LOW_EQ":
            nivel = round(s.preco, 1)
            if not any(abs(nivel - x) <= tol for x in ssl):
                ssl.append(nivel)

    bsl.sort(reverse=True)
    ssl.sort()
    return {"bsl": bsl[:6], "ssl": ssl[:6]}


# ============================================================
# ATR
# ============================================================
def _calcular_atr(candles: List[Candle], periodo: int = 20) -> float:
    """ATR aproximado (True Range médio)."""
    if len(candles) < 2:
        return 0.0
    n = min(periodo, len(candles) - 1)
    janela = candles[-n:]
    trs = []
    for i in range(1, len(janela)):
        c_atual = janela[i]
        c_ant = janela[i - 1]
        tr = max(
            c_atual.high - c_atual.low,
            abs(c_atual.high - c_ant.close),
            abs(c_atual.low - c_ant.close),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


# ============================================================
# CASCATA DE ENTRADA / STOP / ALVOS (com filtro de lado + ATR)
# ============================================================
def calcular_entrada_stop_alvos(
    bias: str,
    obs: List[OrderBlock],
    fvgs_abertos: List[FVG],
    liq: Dict[str, List[float]],
    preco_atual: float,
    candles: Optional[List[Candle]] = None,
    config: ConfigSMC = CONFIG,
) -> Tuple[Optional[float], Optional[float], List[float]]:
    """
    Cascata: OB → FVG → Preço atual.
    Alvos: liquidez BSL/SSL FILTRADA pelo lado correto + projeções measured move.
    Stop: aplica piso mínimo por ATR para evitar stops apertados em M5.
    """
    entrada: Optional[float] = None
    stop: Optional[float] = None
    alvos: List[float] = []

    # --- 1. ENTRADA (cascata OB → FVG → preço) ---
    if bias == "ALTA":
        ob = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        if ob:
            entrada = round(ob.high, 0)
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
            if fvg:
                entrada = round(fvg.superior, 0)
            else:
                entrada = round(preco_atual, 0)

    elif bias == "BAIXA":
        ob = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        if ob:
            entrada = round(ob.low, 0)
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
            if fvg:
                entrada = round(fvg.inferior, 0)
            else:
                entrada = round(preco_atual, 0)

    if entrada is None:
        return None, None, []

    # --- 2. STOP com piso por ATR ---
    atr = _calcular_atr(candles, config.stop_atr_period) if candles else 0.0
    stop_min = max(config.stop_min_dist, atr * config.stop_atr_mult)

    if bias == "ALTA":
        ob = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        if ob:
            stop_candidato = ob.low - 50
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
            stop_candidato = (fvg.inferior - 50) if fvg else (preco_atual - 100)

        if entrada - stop_candidato < stop_min:
            stop = round(entrada - stop_min, 0)
            logger.info(
                f"Stop ajustado por ATR: {stop_candidato:.0f} → {stop:.0f} "
                f"(ATR={atr:.0f}, min={stop_min:.0f})"
            )
        else:
            stop = round(stop_candidato, 0)

    elif bias == "BAIXA":
        ob = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        if ob:
            stop_candidato = ob.high + 50
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
            stop_candidato = (fvg.superior + 50) if fvg else (preco_atual + 100)

        if stop_candidato - entrada < stop_min:
            stop = round(entrada + stop_min, 0)
            logger.info(
                f"Stop ajustado por ATR: {stop_candidato:.0f} → {stop:.0f} "
                f"(ATR={atr:.0f}, min={stop_min:.0f})"
            )
        else:
            stop = round(stop_candidato, 0)

    # --- 3. ALVOS filtrados pelo lado correto ---
    if bias == "ALTA":
        if liq["bsl"]:
            alvos.extend([round(x, 0) for x in liq["bsl"][:3] if x > entrada])
    elif bias == "BAIXA":
        if liq["ssl"]:
            alvos.extend([round(x, 0) for x in liq["ssl"][:3] if x < entrada])

    # Projeções measured move
    dist = abs(entrada - stop)
    if dist > 0:
        if bias == "ALTA":
            alvos.append(round(entrada + dist, 0))
            alvos.append(round(entrada + dist * 1.618, 0))
        elif bias == "BAIXA":
            alvos.append(round(entrada - dist, 0))
            alvos.append(round(entrada - dist * 1.618, 0))

    # Deduplicação e ordenação
    alvos = sorted(set(alvos), key=lambda x: abs(x - entrada))

    # Sanity check final
    if bias == "ALTA":
        alvos = [a for a in alvos if a > entrada]
    elif bias == "BAIXA":
        alvos = [a for a in alvos if a < entrada]

    return entrada, stop, alvos[:4]


# ============================================================
# CONFIANÇA PONDERADA
# ============================================================
def calcular_confianca(
    bias: str,
    bos: bool,
    choch: bool,
    fvgs_abertos: List[FVG],
    obs: List[OrderBlock],
    ob_confluente: bool,
) -> int:
    pesos = {
        "bias": 25,
        "bos": 20,
        "choch": 10,
        "fvg": 15,
        "ob": 15,
        "ob_confluente": 15,
    }
    total_possivel = sum(pesos.values())

    score = 0
    if bias in ("ALTA", "BAIXA"):
        score += pesos["bias"]
    if bos:
        score += pesos["bos"]
    if choch:
        score += pesos["choch"]
    if fvgs_abertos:
        score += pesos["fvg"]
    if obs:
        score += pesos["ob"]
    if ob_confluente:
        score += pesos["ob_confluente"]

    return min(100, round((score / total_possivel) * 100))


# ============================================================
# ALERTA DE DIVERGÊNCIA MACRO × SMC
# ============================================================
def _checar_divergencia_macro(bias: str) -> Optional[str]:
    """Lê Metricas_Calculadas.json e retorna alerta se Macro × SMC brigarem."""
    try:
        if not METRICAS_FILE.exists():
            return None
        with open(METRICAS_FILE, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        ind_ext = metrics.get("indicadores_compostos", {}).get("indicador_mercado_externo")
        if ind_ext is None:
            return None

        if ind_ext < -2 and bias == "ALTA":
            return (
                f"⚠️ DIVERGÊNCIA: Macro em FORTE VENDA ({ind_ext:+.2f}%) "
                f"vs SMC em ALTA — possível armadilha de abertura"
            )
        if ind_ext > 2 and bias == "BAIXA":
            return (
                f"⚠️ DIVERGÊNCIA: Macro em FORTE COMPRA ({ind_ext:+.2f}%) "
                f"vs SMC em BAIXA — possível armadilha de abertura"
            )
    except Exception:
        return None
    return None


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================
def analisar_smc(
    dados_candles: Any,
    ativo: str = "WIN",
    timeframe: str = "5m",
    config: ConfigSMC = CONFIG,
) -> Dict[str, Any]:
    candles = normalizar_candles(dados_candles)

    # 1. Níveis institucionais
    inst_niveis = calcular_poc_vwap(candles, ativo, config)
    poc = inst_niveis["poc"]
    vwap = inst_niveis["vwap"]

    # 2. Lookback
    candles = aplicar_lookback(candles, config.lookback)

    if len(candles) < 10:
        logger.warning(f"Candles insuficientes ({len(candles)}), abortando análise")
        return {
            "timestamp": datetime.now(BRT).isoformat(),
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

    # 3. Detecções
    swings = detectar_swings(candles, config.swing_left, config.swing_right)
    eventos, bias = detectar_bos_choch(candles, swings)
    fvgs = detectar_fvg(candles, config)
    obs = detectar_order_blocks(candles, swings, eventos, ativo, config)
    liq = detectar_liquidez(swings, config.eq_tol_pontos)

    bos = any(e.tipo == "BOS" for e in eventos[-3:])
    choch = any(e.tipo == "CHOCH" for e in eventos[-3:])

    fvgs_abertos = [f for f in fvgs if not f.preenchido][-config.max_fvgs :]
    obs = obs[-config.max_obs :]

    preco_atual = candles[-1].close

    logger.info(
        f"[{ativo}] {len(candles)} candles | {len(swings)} swings | "
        f"{len(obs)} OBs | {len(fvgs_abertos)} FVGs abertos | bias={bias}"
    )

    # 4. Confluência OB ↔ POC
    ob_confluente = False
    if obs:
        ob_recente = obs[-1]
        distancia_poc = abs(ob_recente.preco_ref - poc)
        lim = config.ob_poc_dist_win if "WIN" in ativo.upper() else config.ob_poc_dist_wdo
        if distancia_poc <= lim:
            ob_confluente = True

    # 5. Estruturas textuais
    estruturas: List[str] = []
    for s in swings[-config.max_niveis :]:
        label = {
            "HIGH": "Swing High",
            "LOW": "Swing Low",
            "HIGH_EQ": "Equal High (BSL)",
            "LOW_EQ": "Equal Low (SSL)",
        }.get(s.tipo, "Swing")
        estruturas.append(f"{s.preco:.0f}: {label}")

    for ob in obs:
        estruturas.append(
            f"{ob.preco_ref:.0f}: OB {ob.tipo} ({ob.low:.0f}-{ob.high:.0f}) [{ob.validado_por}]"
        )

    for fvg in fvgs_abertos:
        estruturas.append(
            f"{(fvg.superior + fvg.inferior) / 2:.0f}: FVG {fvg.tipo} ({fvg.inferior:.0f}-{fvg.superior:.0f})"
        )

    # 6. Liquidez textual
    liquidez_txt: List[str] = [
        f"POC Institucional (Ontem): {poc:.0f}",
        f"VWAP (Ontem): {vwap:.0f}",
    ]
    for p in liq["bsl"]:
        liquidez_txt.append(f"BSL: {p:.0f} (equal highs / liquidez acima)")
    for p in liq["ssl"]:
        liquidez_txt.append(f"SSL: {p:.0f} (equal lows / liquidez abaixo)")

    # 7. Cenários
    cenarios: List[str] = []
    if bias == "BAIXA":
        res = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        fvg_v = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
        zona = res.preco_ref if res else (fvg_v.superior if fvg_v else preco_atual)
        alvo = liq["ssl"][0] if liq["ssl"] else preco_atual * 0.99
        cenarios.append(
            f"Cenário Vendedor: rejeição em {zona:.0f} (OB/FVG validado por volume) visando {alvo:.0f}."
        )
    elif bias == "ALTA":
        dem = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        fvg_c = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
        zona = dem.preco_ref if dem else (fvg_c.inferior if fvg_c else preco_atual)
        alvo = liq["bsl"][0] if liq["bsl"] else preco_atual * 1.01
        cenarios.append(
            f"Cenário Comprador: defesa em {zona:.0f} (OB/FVG validado por volume) visando {alvo:.0f}."
        )
    else:
        cenarios.append("Cenário Lateral: aguardar BOS com fechamento fora da faixa recente.")

    # 8. Alerta de divergência Macro × SMC
    alerta = _checar_divergencia_macro(bias)
    if alerta:
        logger.warning(alerta)
        cenarios.append(alerta)

    # 9. Confiança
    conf = calcular_confianca(bias, bos, choch, fvgs_abertos, obs, ob_confluente)

    # 10. Entrada / Stop / Alvos
    entrada, stop, alvos = calcular_entrada_stop_alvos(
        bias, obs, fvgs_abertos, liq, preco_atual, candles=candles, config=config
    )

    return {
        "timestamp": datetime.now(BRT).isoformat(),
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
            "ob_alinhado_com_poc": ob_confluente,
        },
        "order_blocks": [
            {
                "tipo": o.tipo,
                "preco": o.preco_ref,
                "high": o.high,
                "low": o.low,
                "validado_por": o.validado_por,
            }
            for o in obs
        ],
        "fair_value_gaps": [
            {
                "tipo": f.tipo,
                "superior": f.superior,
                "inferior": f.inferior,
                "preenchido": f.preenchido,
            }
            for f in fvgs_abertos
        ],
        "liquidez": liq,
        "eventos_estrutura": [
            {"tipo": e.tipo, "direcao": e.direcao, "preco": e.preco, "time": e.time}
            for e in eventos[-6:]
        ],
        "swings_recentes": [
            {"tipo": s.tipo, "preco": s.preco, "time": s.time} for s in swings[-10:]
        ],
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
            "versao_motor": "2.1",
            "config": asdict(config),
        },
    }


# ============================================================
# SALVAMENTO (com histórico opcional)
# ============================================================
def salvar_resultado(
    resultado: Dict[str, Any], caminho: Optional[Path] = None, guardar_historico: bool = False
) -> Path:
    caminho = caminho or ARQUIVO_SAIDA
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    if guardar_historico:
        try:
            HISTORICO_SMC_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(BRT).strftime("%Y%m%d_%H%M%S")
            hist = HISTORICO_SMC_DIR / f"SMC_{ts}.json"
            with open(hist, "w", encoding="utf-8") as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
            logger.info(f"Histórico salvo em {hist}")
        except Exception as e:
            logger.warning(f"Falha ao salvar histórico: {e}")

    return caminho


# ============================================================
# MT5 — CARREGAMENTO
# ============================================================
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


def carregar_mt5(
    symbol: str = "WIN$",
    timeframe_min: int = 5,
    qtd: int = 300,
    validar_pregao: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise RuntimeError("MetaTrader5 não instalado.") from e

    if validar_pregao:
        try:
            from config import esta_no_pregao

            if not esta_no_pregao():
                logger.warning("Fora do pregão — coleta pode trazer dados parciais")
        except ImportError:
            pass

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
            logger.info(f"Símbolo MT5 selecionado: {sym}")
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

        # MT5 retorna UTC — converte para BRT
        dt_brt = datetime.fromtimestamp(r["time"], tz=timezone.utc).astimezone(BRT)

        out.append(
            {
                "time": dt_brt.isoformat(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": v_real,
            }
        )

    mt5.shutdown()
    return out, simbolo_ok


# ============================================================
# CLI — execução isolada
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Motor SMC/ICT — análise de candles")
    parser.add_argument("--ativo", default="WIN$", help="Símbolo MT5 (ex: WIN$, WDO$)")
    parser.add_argument("--tf", type=int, default=5, help="Timeframe em minutos (1, 5, 15)")
    parser.add_argument("--qtd", type=int, default=300, help="Quantidade de candles")
    parser.add_argument("--historico", action="store_true", help="Salva cópia em Historico_SMC/")
    parser.add_argument("--validar-pregao", action="store_true", help="Só roda se estiver no pregão")
    args = parser.parse_args()

    logger.info(f"Iniciando análise SMC — ativo={args.ativo} tf={args.tf}m qtd={args.qtd}")

    try:
        candles, simbolo_ok = carregar_mt5(args.ativo, args.tf, args.qtd, args.validar_pregao)
    except Exception as e:
        logger.error(f"Falha na coleta MT5: {e}")
        sys.exit(1)

    resultado = analisar_smc(candles, ativo=simbolo_ok or args.ativo, timeframe=f"{args.tf}m")
    caminho = salvar_resultado(resultado, guardar_historico=args.historico)

    logger.info(f"✅ Resultado salvo em {caminho}")
    print(f"\n📊 Resultado:")
    print(f"   Bias:      {resultado['bias_direcional']}")
    print(f"   Confiança: {resultado['confianca_visual']}%")
    print(f"   Preço:     {resultado['preco_atual']:.0f}")
    print(f"   POC ontem: {resultado['niveis_institucionais']['poc_ontem']:.0f}")
    print(f"   VWAP onte: {resultado['niveis_institucionais']['vwap_ontem']:.0f}")
    if resultado.get("entrada_sugerida"):
        print(f"   Entrada:   {resultado['entrada_sugerida']:.0f}")
        print(f"   Stop:      {resultado['stop_sugerido']:.0f}")
        print(f"   Alvos:     {resultado['alvos']}")


if __name__ == "__main__":
    main()