#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor_SMC_Regras.py
===================
Motor de regras SMC/ICT SEM IA — Versão 3.3 (Stale Detection)

Mudanças v3.3:
  - analisar_smc: adiciona metadados.stale / stale_motivo / candle_idade_min.
    stale=True quando o último candle tem idade > 15 min (fora do pregão,
    fim de semana, ou MT5 travado). O V2 usa esse flag para vetar a operação
    mesmo que o pipeline rode fora de hora (scheduler externo dispara a
    cada ~5 min ininterruptamente).

Mudanças v3.2 (mantidas):
  - calcular_entrada_stop_alvos: R:R mínimo forçado em 1:1.5.

Mudanças v3.1 (mantidas):
  - Mitigação de OBs por fechamento (Low/High), BSL/SSL por sweep.
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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MotorSMC")

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

BRT = timezone(timedelta(hours=-3))

# v3.3: idade máxima do último candle antes de marcar stale
STALE_IDADE_MAX_MIN = 15.0


@dataclass
class ConfigSMC:
    swing_left: int = 2
    swing_right: int = 2
    fvg_min_pontos: float = 20.0
    eq_tol_pontos: float = 15.0

    max_niveis: int = 20
    max_fvgs: int = 15
    max_obs: int = 15
    lookback: int = 500

    lookback_map: Dict[str, int] = field(
        default_factory=lambda: {
            "1m": 1000,
            "5m": 1500,
            "15m": 500,
        }
    )

    vol_ma_period: int = 20
    vol_factor_min: float = 1.2
    expansion_factor_min: float = 1.3

    tick_size_default: float = 5.0
    tick_size_map: Dict[str, float] = field(
        default_factory=lambda: {
            "WIN": 5.0, "WDO": 0.5, "VALE3": 0.01, "PETR4": 0.01,
            "ITUB4": 0.01, "BBAS3": 0.01, "BBDC4": 0.01, "B3SA3": 0.01,
            "ES": 0.25, "NQ": 0.25,
        }
    )

    ob_validacao_janela: int = 40
    ob_min_range: float = 30.0
    ob_fallback_brutos: bool = True

    dedup_ob_dist: Dict[str, float] = field(
        default_factory=lambda: {"WIN": 50.0, "WDO": 5.0}
    )
    dedup_ob_dist_default: float = 10.0

    ob_poc_dist_win: float = 300.0
    ob_poc_dist_wdo: float = 30.0
    stop_min_dist: float = 150.0
    stop_atr_mult: float = 0.8
    stop_atr_period: int = 20

    # v3.2 — R:R mínimo
    rr_minimo: float = 1.5

    # v3.3 — stale detection
    stale_idade_max_min: float = 15.0


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
    tipo: str
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
    abertura: float
    idx: int
    time: str = ""
    validado_por: str = ""


@dataclass
class EventoEstrutura:
    tipo: str
    direcao: str
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


def _tick_size_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    ativo_up = (ativo or "").upper()
    for chave, tick in config.tick_size_map.items():
        if chave in ativo_up:
            return tick
    return config.tick_size_default


def _dedup_dist_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    ativo_up = (ativo or "").upper()
    for chave, dist in config.dedup_ob_dist.items():
        if chave in ativo_up:
            return dist
    return config.dedup_ob_dist_default


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
            o, h, l, c = row.get("open", 0), row.get("high", 0), row.get("low", 0), row.get("close", 0)
            t = row.get("time", "")
            vol = row.get("real_volume", row.get("volume", row.get("tick_volume", 0)))
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

        candles.append(Candle(time=str(t) if t is not None else "", open=o, high=h, low=l, close=c, volume=_to_float(vol), idx=len(candles)))

    return candles


def aplicar_lookback(candles: List[Candle], lookback: int) -> List[Candle]:
    if lookback and lookback > 0 and len(candles) > lookback:
        slice_c = candles[-lookback:]
        for i, c in enumerate(slice_c):
            c.idx = i
        return slice_c
    return candles


def calcular_metricas_medias(candles: List[Candle], idx_atual: int, config: ConfigSMC = CONFIG) -> Tuple[float, float]:
    periodo = config.vol_ma_period
    inicio = max(0, idx_atual - periodo)
    janela = candles[inicio:idx_atual]
    if not janela:
        return 0.0, 0.0
    media_vol = sum(c.volume for c in janela) / len(janela)
    media_corpo = sum(abs(c.close - c.open) for c in janela) / len(janela)
    return media_vol, media_corpo


def classificar_candle(candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG) -> str:
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


def e_candle_expansao(candle: Candle, media_vol: float, media_corpo: float, config: ConfigSMC = CONFIG) -> bool:
    return classificar_candle(candle, media_vol, media_corpo, config) in ("FORTE", "FRACO")


def calcular_poc_vwap(candles: List[Candle], ativo: str, config: ConfigSMC = CONFIG) -> Dict[str, float]:
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

    df_ontem["preco_tipico"] = (df_ontem["high"] + df_ontem["low"] + df_ontem["close"]) / 3
    df_ontem["vol_financeiro"] = df_ontem["preco_tipico"] * df_ontem["volume"]

    vol_total = df_ontem["volume"].sum()
    vwap = df_ontem["vol_financeiro"].sum() / vol_total if vol_total > 0 else 0.0

    tick_size = _tick_size_para(ativo, config)
    profile_dict: Dict[float, float] = {}

    for _, row in df_ontem.iterrows():
        h, l, v = row["high"], row["low"], row["volume"]
        if h <= 0 or l <= 0 or v <= 0:
            continue
        if h < l:
            h, l = l, h
        bins_candle = np.arange(np.floor(l / tick_size) * tick_size, np.ceil(h / tick_size) * tick_size + tick_size, tick_size)
        if len(bins_candle) > 0:
            vol_por_bin = v / len(bins_candle)
            for b in bins_candle:
                b_rounded = round(float(b), 4)
                profile_dict[b_rounded] = profile_dict.get(b_rounded, 0.0) + vol_por_bin

    poc = max(profile_dict, key=profile_dict.get) if profile_dict else 0.0
    return {"poc": float(poc), "vwap": round(float(vwap), 1)}


def detectar_swings(candles: List[Candle], config: ConfigSMC = CONFIG) -> List[Swing]:
    left, right = config.swing_left, config.swing_right
    swings: List[Swing] = []
    n = len(candles)
    if n < left + right + 1:
        return swings

    for i in range(left, n - right):
        window = candles[i - left: i + right + 1]
        highs = [c.high for c in window]
        lows = [c.low for c in window]
        mid = candles[i]

        if mid.high >= max(highs):
            tipo = "HIGH_EQ" if highs.count(mid.high) > 1 else "HIGH"
            swings.append(Swing(idx=i, preco=mid.high, tipo=tipo, time=mid.time))

        if mid.low <= min(lows):
            tipo = "LOW_EQ" if lows.count(mid.low) > 1 else "LOW"
            swings.append(Swing(idx=i, preco=mid.low, tipo=tipo, time=mid.time))

    return swings


def _so_highs(swings: List[Swing]) -> List[Swing]:
    return [s for s in swings if s.tipo.startswith("HIGH")]


def _so_lows(swings: List[Swing]) -> List[Swing]:
    return [s for s in swings if s.tipo.startswith("LOW")]


def detectar_bos_choch(candles: List[Candle], swings: List[Swing], config: ConfigSMC = CONFIG) -> Tuple[List[EventoEstrutura], str]:
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

    last_high, last_low = None, None
    tendencia_atual = bias if bias != "LATERAL" else "LATERAL"

    for s in swings:
        if s.tipo.startswith("HIGH"):
            if last_high:
                for c in candles[s.idx:]:
                    if c.close > last_high.preco:
                        tipo_ev = "BOS" if tendencia_atual == "ALTA" else "CHOCH"
                        eventos.append(EventoEstrutura(tipo=tipo_ev, direcao="ALTA", preco=last_high.preco, idx=c.idx, time=c.time))
                        tendencia_atual = "ALTA"
                        break
            last_high = s

        if s.tipo.startswith("LOW"):
            if last_low:
                for c in candles[s.idx:]:
                    if c.close < last_low.preco:
                        tipo_ev = "BOS" if tendencia_atual == "BAIXA" else "CHOCH"
                        eventos.append(EventoEstrutura(tipo=tipo_ev, direcao="BAIXA", preco=last_low.preco, idx=c.idx, time=c.time))
                        tendencia_atual = "BAIXA"
                        break
            last_low = s

    if eventos:
        vistos, unicos = set(), []
        for e in eventos:
            chave = (e.idx, e.tipo, e.direcao)
            if chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(e)
        eventos = unicos
        eventos.sort(key=lambda e: e.idx)

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
        media_vol, media_corpo = calcular_metricas_medias(candles, i - 1, config)
        if classificar_candle(c1, media_vol, media_corpo, config) != "FORTE":
            continue

        if c2.low > c0.high and (c2.low - c0.high) >= config.fvg_min_pontos:
            fvgs.append(FVG(tipo="COMPRA", superior=c2.low, inferior=c0.high, idx=i, time=c2.time))
        if c2.high < c0.low and (c0.low - c2.high) >= config.fvg_min_pontos:
            fvgs.append(FVG(tipo="VENDA", superior=c0.low, inferior=c2.high, idx=i, time=c2.time))

    for fvg in fvgs:
        for c in candles[fvg.idx + 1:]:
            if fvg.tipo == "COMPRA" and c.low <= fvg.inferior:
                fvg.preenchido = True
                break
            if fvg.tipo == "VENDA" and c.high >= fvg.superior:
                fvg.preenchido = True
                break

    return fvgs


def detectar_order_blocks(candles: List[Candle], swings: List[Swing], eventos_estrutura: List[EventoEstrutura], ativo: str = "WIN", config: ConfigSMC = CONFIG) -> List[OrderBlock]:
    obs_brutos: List[OrderBlock] = []
    n = len(candles)
    if n < 5 or len(swings) < 2:
        return obs_brutos

    for s in swings[-60:]:
        i = s.idx
        if i < 1 or i >= n - 1:
            continue
        cand, prev = candles[i], candles[i - 1]

        if s.tipo.startswith("LOW"):
            ob_cand = prev if prev.close < prev.open else cand
        else:
            ob_cand = prev if prev.close > prev.open else cand

        range_ob = ob_cand.high - ob_cand.low
        if range_ob < config.ob_min_range:
            continue

        media_vol, media_corpo = calcular_metricas_medias(candles, i, config)
        candle_saida = candles[i + 1] if (i + 1) < n else cand

        if not e_candle_expansao(candle_saida, media_vol, media_corpo, config):
            continue

        if s.tipo.startswith("LOW"):
            if any(c.close > ob_cand.high for c in candles[i + 1: min(i + 11, n)]):
                obs_brutos.append(OrderBlock(
                    tipo="COMPRA", high=ob_cand.high, low=ob_cand.low,
                    preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1),
                    abertura=ob_cand.open,
                    idx=ob_cand.idx, time=ob_cand.time
                ))

        if s.tipo.startswith("HIGH"):
            if any(c.close < ob_cand.low for c in candles[i + 1: min(i + 11, n)]):
                obs_brutos.append(OrderBlock(
                    tipo="VENDA", high=ob_cand.high, low=ob_cand.low,
                    preco_ref=round((ob_cand.high + ob_cand.low) / 2, 1),
                    abertura=ob_cand.open,
                    idx=ob_cand.idx, time=ob_cand.time
                ))

    obs_validados: List[OrderBlock] = []
    for ob in obs_brutos:
        direcao_alvo = "ALTA" if ob.tipo == "COMPRA" else "BAIXA"
        for e in eventos_estrutura:
            if (e.idx > ob.idx and e.idx <= ob.idx + config.ob_validacao_janela and e.direcao == direcao_alvo):
                ob.validado_por = e.tipo
                obs_validados.append(ob)
                break

    if not obs_validados and obs_brutos and config.ob_fallback_brutos:
        for ob in obs_brutos:
            ob.validado_por = "FALLBACK"
        obs_validados = obs_brutos

    obs_nao_mitigados: List[OrderBlock] = []
    for ob in obs_validados:
        mitigado = False
        for c in candles[ob.idx + 1:]:
            if ob.tipo == "COMPRA" and c.close < ob.low:
                mitigado = True
                break
            if ob.tipo == "VENDA" and c.close > ob.high:
                mitigado = True
                break
        if not mitigado:
            obs_nao_mitigados.append(ob)

    dist_dedup = _dedup_dist_para(ativo, config)
    unicos: List[OrderBlock] = []
    for ob in obs_nao_mitigados:
        if not any(abs(ob.preco_ref - u.preco_ref) < dist_dedup and ob.tipo == u.tipo for u in unicos):
            unicos.append(ob)

    return unicos


def detectar_liquidez(swings: List[Swing], candles: List[Candle], config: ConfigSMC = CONFIG) -> Dict[str, List[float]]:
    tol = config.eq_tol_pontos
    highs = _so_highs(swings)
    lows = _so_lows(swings)

    bsl_raw = []
    ssl_raw = []

    for i in range(len(highs)):
        for j in range(i + 1, len(highs)):
            if abs(highs[i].preco - highs[j].preco) <= tol:
                nivel = round((highs[i].preco + highs[j].preco) / 2, 1)
                idx_formacao = max(highs[i].idx, highs[j].idx)
                if not any(abs(nivel - x[0]) <= tol for x in bsl_raw):
                    bsl_raw.append((nivel, idx_formacao))

    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            if abs(lows[i].preco - lows[j].preco) <= tol:
                nivel = round((lows[i].preco + lows[j].preco) / 2, 1)
                idx_formacao = max(lows[i].idx, lows[j].idx)
                if not any(abs(nivel - x[0]) <= tol for x in ssl_raw):
                    ssl_raw.append((nivel, idx_formacao))

    for s in highs:
        if s.tipo == "HIGH_EQ":
            nivel = round(s.preco, 1)
            if not any(abs(nivel - x[0]) <= tol for x in bsl_raw):
                bsl_raw.append((nivel, s.idx))
    for s in lows:
        if s.tipo == "LOW_EQ":
            nivel = round(s.preco, 1)
            if not any(abs(nivel - x[0]) <= tol for x in ssl_raw):
                ssl_raw.append((nivel, s.idx))

    bsl_ativos = []
    for nivel, idx in bsl_raw:
        mitigado = False
        for c in candles[idx + 1:]:
            if c.close > nivel:
                mitigado = True
                break
        if not mitigado:
            bsl_ativos.append(nivel)

    ssl_ativos = []
    for nivel, idx in ssl_raw:
        mitigado = False
        for c in candles[idx + 1:]:
            if c.close < nivel:
                mitigado = True
                break
        if not mitigado:
            ssl_ativos.append(nivel)

    bsl_ativos.sort(reverse=True)
    ssl_ativos.sort()
    return {"bsl": bsl_ativos[:6], "ssl": ssl_ativos[:6]}


def _calcular_atr(candles: List[Candle], periodo: int = 20) -> float:
    if len(candles) < 2:
        return 0.0
    n = min(periodo, len(candles) - 1)
    janela = candles[-n:]
    trs = []
    for i in range(1, len(janela)):
        c_atual, c_ant = janela[i], janela[i - 1]
        tr = max(c_atual.high - c_atual.low, abs(c_atual.high - c_ant.close), abs(c_atual.low - c_ant.close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def calcular_entrada_stop_alvos(
    bias: str,
    obs: List[OrderBlock],
    fvgs_abertos: List[FVG],
    liq: Dict[str, List[float]],
    preco_atual: float,
    candles: Optional[List[Candle]] = None,
    config: ConfigSMC = CONFIG,
) -> Tuple[Optional[float], Optional[float], List[float]]:
    entrada, stop, alvos = None, None, []
    if bias == "ALTA":
        ob = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        if ob:
            entrada = round(ob.abertura, 0)
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
            entrada = round(fvg.superior, 0) if fvg else round(preco_atual, 0)
    elif bias == "BAIXA":
        ob = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        if ob:
            entrada = round(ob.abertura, 0)
        else:
            fvg = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
            entrada = round(fvg.inferior, 0) if fvg else round(preco_atual, 0)

    if entrada is None:
        return None, None, []

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
        else:
            stop = round(stop_candidato, 0)

    if bias == "ALTA":
        if liq["bsl"]:
            alvos.extend([round(x, 0) for x in liq["bsl"][:3] if x > entrada])
    elif bias == "BAIXA":
        if liq["ssl"]:
            alvos.extend([round(x, 0) for x in liq["ssl"][:3] if x < entrada])

    # v3.2 — R:R mínimo 1:1.5
    dist = abs(entrada - stop)
    if dist > 0:
        dist_min_alvo = dist * config.rr_minimo
        dist_alvo_2 = dist * (config.rr_minimo + 1.0)

        if bias == "ALTA":
            alvos = [a for a in alvos if (a - entrada) >= dist_min_alvo]
            alvos.append(round(entrada + dist_min_alvo, 0))
            alvos.append(round(entrada + dist_alvo_2, 0))
        elif bias == "BAIXA":
            alvos = [a for a in alvos if (entrada - a) >= dist_min_alvo]
            alvos.append(round(entrada - dist_min_alvo, 0))
            alvos.append(round(entrada - dist_alvo_2, 0))
    else:
        logger.warning("calcular_entrada_stop_alvos: distância entrada↔stop = 0; R:R não aplicado.")

    alvos = sorted(set(alvos), key=lambda x: abs(x - entrada))
    if bias == "ALTA":
        alvos = [a for a in alvos if a > entrada]
    elif bias == "BAIXA":
        alvos = [a for a in alvos if a < entrada]

    return entrada, stop, alvos[:4]


def calcular_confianca(bias: str, bos: bool, choch: bool, fvgs_abertos: List[FVG], obs: List[OrderBlock], ob_confluente: bool) -> int:
    pesos = {"bias": 25, "bos": 20, "choch": 10, "fvg": 15, "ob": 15, "ob_confluente": 15}
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


def _checar_divergencia_macro(bias: str) -> Optional[str]:
    try:
        if not METRICAS_FILE.exists():
            return None
        with open(METRICAS_FILE, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        ind_ext = metrics.get("indicadores_compostos", {}).get("indicador_mercado_externo")
        if ind_ext is None:
            return None
        if ind_ext < -2 and bias == "ALTA":
            return f"⚠️ DIVERGÊNCIA: Macro FORTE VENDA ({ind_ext:+.2f}%) vs SMC ALTA"
        if ind_ext > 2 and bias == "BAIXA":
            return f"⚠️ DIVERGÊNCIA: Macro FORTE COMPRA ({ind_ext:+.2f}%) vs SMC BAIXA"
    except Exception:
        return None
    return None


def _calcular_stale(candles: List[Candle], config: ConfigSMC = CONFIG) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    v3.3 — Detecta se o SMC está rodando sobre candle velho.
    Retorna (stale, stale_motivo, candle_idade_min).
    stale_motivo ∈ {None, 'candle_antigo', 'sem_candles'}.
    """
    if not candles or not candles[-1].time:
        return True, "sem_candles", None
    try:
        ts_ultimo = pd.to_datetime(candles[-1].time, utc=True).tz_convert(BRT)
        agora = pd.Timestamp.now(tz=BRT)
        idade_min = float((agora - ts_ultimo).total_seconds() / 60.0)
        if idade_min > config.stale_idade_max_min:
            return True, "candle_antigo", round(idade_min, 1)
        return False, None, round(idade_min, 1)
    except Exception as e:
        logger.warning(f"_calcular_stale: falha ao ler timestamp do último candle: {e}")
        return False, None, None


def analisar_smc(dados_candles: Any, ativo: str = "WIN", timeframe: str = "5m", config: ConfigSMC = CONFIG) -> Dict[str, Any]:
    candles = normalizar_candles(dados_candles)
    inst_niveis = calcular_poc_vwap(candles, ativo, config)
    poc, vwap = inst_niveis["poc"], inst_niveis["vwap"]

    lookback_efetivo = config.lookback_map.get(timeframe, config.lookback)
    candles = aplicar_lookback(candles, lookback_efetivo)

    if len(candles) < 10:
        return {"timestamp": datetime.now(BRT).isoformat(), "ativo": ativo, "timeframe": timeframe, "erro": "Candles insuficientes", "bias_direcional": "LATERAL", "confianca_visual": 0}

    swings = detectar_swings(candles, config)
    eventos, bias = detectar_bos_choch(candles, swings, config)
    fvgs = detectar_fvg(candles, config)
    obs = detectar_order_blocks(candles, swings, eventos, ativo, config)
    liq = detectar_liquidez(swings, candles, config)

    if bias in ("ALTA", "BAIXA"):
        bos = any(e.tipo == "BOS" and e.direcao == bias for e in eventos[-3:])
        choch = any(e.tipo == "CHOCH" and e.direcao == bias for e in eventos[-3:])
    else:
        bos = any(e.tipo == "BOS" for e in eventos[-3:])
        choch = any(e.tipo == "CHOCH" for e in eventos[-3:])

    fvgs_abertos = [f for f in fvgs if not f.preenchido][-config.max_fvgs:]
    obs = obs[-config.max_obs:]

    preco_atual = candles[-1].close
    ob_confluente = False
    if obs:
        ob_recente = obs[-1]
        distancia_poc = abs(ob_recente.preco_ref - poc)
        lim = config.ob_poc_dist_win if "WIN" in ativo.upper() else config.ob_poc_dist_wdo
        if distancia_poc <= lim:
            ob_confluente = True

    estruturas: List[str] = []
    for s in swings[-config.max_niveis:]:
        label = {"HIGH": "Swing High", "LOW": "Swing Low", "HIGH_EQ": "Equal High (BSL)", "LOW_EQ": "Equal Low (SSL)"}.get(s.tipo, "Swing")
        estruturas.append(f"{s.preco:.0f}: {label}")

    for ob in obs:
        estruturas.append(f"{ob.abertura:.0f}: OB {ob.tipo} ({ob.low:.0f}-{ob.high:.0f}) [{ob.validado_por}]")

    for fvg in fvgs_abertos:
        estruturas.append(f"{(fvg.superior + fvg.inferior) / 2:.0f}: FVG {fvg.tipo} ({fvg.inferior:.0f}-{fvg.superior:.0f})")

    liquidez_txt: List[str] = [f"POC Institucional (Ontem): {poc:.0f}", f"VWAP (Ontem): {vwap:.0f}"]
    for p in liq["bsl"]:
        liquidez_txt.append(f"BSL: {p:.0f} (equal highs / liquidez acima)")
    for p in liq["ssl"]:
        liquidez_txt.append(f"SSL: {p:.0f} (equal lows / liquidez abaixo)")

    cenarios: List[str] = []
    if bias == "BAIXA":
        res = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        fvg_v = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
        zona = res.abertura if res else (fvg_v.superior if fvg_v else preco_atual)
        alvo = liq["ssl"][0] if liq["ssl"] else preco_atual * 0.99
        cenarios.append(f"Cenário Vendedor: rejeição em {zona:.0f} visando {alvo:.0f}.")
    elif bias == "ALTA":
        dem = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        fvg_c = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
        zona = dem.abertura if dem else (fvg_c.inferior if fvg_c else preco_atual)
        alvo = liq["bsl"][0] if liq["bsl"] else preco_atual * 1.01
        cenarios.append(f"Cenário Comprador: defesa em {zona:.0f} visando {alvo:.0f}.")
    else:
        cenarios.append("Cenário Lateral: aguardar BOS com fechamento fora da faixa recente.")

    alerta = _checar_divergencia_macro(bias)
    if alerta:
        cenarios.append(alerta)

    conf = calcular_confianca(bias, bos, choch, fvgs_abertos, obs, ob_confluente)
    entrada, stop, alvos = calcular_entrada_stop_alvos(bias, obs, fvgs_abertos, liq, preco_atual, candles=candles, config=config)

    # v3.3 — stale detection
    stale, stale_motivo, candle_idade_min = _calcular_stale(candles, config)

    return {
        "timestamp": datetime.now(BRT).isoformat(), "ativo": ativo, "timeframe": timeframe, "fonte": "regras_smc",
        "preco_atual": preco_atual, "timeframes_identificados": timeframe,
        "bias_direcional": bias, "direcao_estrutura": bias, "bos": bos, "choch": choch, "confianca_visual": conf,
        # v3.3 — stale (flat no root para facilitar inspeção)
        "stale": stale,
        "stale_motivo": stale_motivo,
        "candle_idade_min": candle_idade_min,
        "niveis_institucionais": {"poc_ontem": poc, "vwap_ontem": vwap, "ob_alinhado_com_poc": ob_confluente},
        "order_blocks": [{"tipo": o.tipo, "preco": o.preco_ref, "abertura": o.abertura, "high": o.high, "low": o.low, "validado_por": o.validado_por, "time": o.time} for o in obs],
        "fair_value_gaps": [{"tipo": f.tipo, "superior": f.superior, "inferior": f.inferior, "preenchido": f.preenchido, "time": f.time} for f in fvgs_abertos],
        "liquidez": liq,
        "eventos_estrutura": [{"tipo": e.tipo, "direcao": e.direcao, "preco": e.preco, "time": e.time} for e in eventos[-6:]],
        "swings_recentes": [{"tipo": s.tipo, "preco": s.preco, "time": s.time} for s in swings[-10:]],
        "estruturas_coletadas": estruturas[-config.max_niveis:],
        "liquidez_relevante": liquidez_txt,
        "zonas_de_interesse_e_cenarios": cenarios,
        "entrada_sugerida": entrada, "stop_sugerido": stop, "alvos": alvos,
        "metadados": {
            "n_candles": len(candles), "n_swings": len(swings), "n_fvgs_abertos": len(fvgs_abertos), "n_obs": len(obs),
            "filtro_volume_real_aplicado": True, "versao_motor": "3.3",
            "rr_minimo_aplicado": config.rr_minimo,
            "stale_idade_max_min": config.stale_idade_max_min,
            "stale": stale,
            "stale_motivo": stale_motivo,
            "candle_idade_min": candle_idade_min,
            "config": asdict(config),
            "_debug_confianca": {
                "bias_ativo": bias in ("ALTA", "BAIXA"), "bos_ativo": bos, "choch_ativo": choch,
                "fvg_ativo": bool(fvgs_abertos), "ob_ativo": bool(obs), "ob_confluente_ativo": ob_confluente,
                "total_eventos": len(eventos), "ultimos_3_eventos": [{"tipo": e.tipo, "direcao": e.direcao, "time": e.time} for e in eventos[-3:]],
            },
        },
    }


def salvar_resultado(resultado: Dict[str, Any], caminho: Optional[Path] = None, guardar_historico: bool = False) -> Path:
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
        except Exception:
            pass
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
    return candidatos


def carregar_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 2000, validar_pregao: bool = False) -> Tuple[List[Dict[str, Any]], str]:
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
            rates, simbolo_ok = r, sym
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
        dt_brt = datetime.fromtimestamp(r["time"], tz=timezone.utc).replace(tzinfo=BRT)
        out.append({"time": dt_brt.isoformat(), "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]), "volume": v_real})
    mt5.shutdown()
    return out, simbolo_ok


def main():
    parser = argparse.ArgumentParser(description="Motor SMC/ICT — análise de candles")
    parser.add_argument("--ativo", default="WIN$", help="Símbolo MT5 (ex: WIN$, WDO$)")
    parser.add_argument("--tf", type=int, default=5, help="Timeframe em minutos (1, 5, 15)")
    parser.add_argument("--qtd", type=int, default=2000, help="Quantidade de candles")
    parser.add_argument("--historico", action="store_true", help="Salva cópia em Historico_SMC/")
    parser.add_argument("--validar-pregao", action="store_true", help="Só roda se estiver no pregão (não implementado; stale é detectado automaticamente)")
    args = parser.parse_args()
    try:
        candles, simbolo_ok = carregar_mt5(args.ativo, args.tf, args.qtd, args.validar_pregao)
    except Exception as e:
        logger.error(f"Falha na coleta MT5: {e}")
        sys.exit(1)
    resultado = analisar_smc(candles, ativo=simbolo_ok or args.ativo, timeframe=f"{args.tf}m")
    caminho = salvar_resultado(resultado, guardar_historico=args.historico)
    stale_txt = "STALE" if resultado.get("stale") else "OK"
    print(f"✅ Resultado salvo em {caminho} [{stale_txt}, idade={resultado.get('candle_idade_min')}min]")


if __name__ == "__main__":
    main()