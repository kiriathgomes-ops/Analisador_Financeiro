#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor_SMC_Regras.py
===================
Motor de regras SMC/ICT SEM IA.

Detecta:
- Swing High / Swing Low
- BOS (Break of Structure) e CHoCH (Change of Character)
- Fair Value Gaps (FVG)
- Order Blocks (OB) simplificados
- Liquidez (equal highs / equal lows aproximados)

Entrada: lista/DataFrame de candles OHLCV
Saída: JSON estruturado compatível com o pipeline
      (Coletas/AnaliseGraficaSMC_Regras.json)

Uso:
    from Motor_SMC_Regras import analisar_smc, salvar_resultado

    resultado = analisar_smc(candles, ativo="WIN", timeframe="5m")
    salvar_resultado(resultado)

Ou via CLI (com CSV):
    python Motor_SMC_Regras.py --csv caminho.csv --ativo WIN --tf 5m

CSV esperado (colunas): time, open, high, low, close [, volume]
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
COLETAS_DIR = BASE_DIR / "Coletas"
if not COLETAS_DIR.exists():
    # quando o script está em pages/ ou raiz do app
    alt = BASE_DIR.parent / "Coletas"
    if alt.exists():
        COLETAS_DIR = alt

ARQUIVO_SAIDA = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"


@dataclass
class ConfigSMC:
    # Swing: quantas velas de cada lado para confirmar pivô
    swing_left: int = 2
    swing_right: int = 2
    # FVG mínimo em pontos (WIN ~ pontos; WDO use valor menor)
    fvg_min_pontos: float = 20.0
    # Equal high/low: tolerância em pontos
    eq_tol_pontos: float = 15.0
    # Quantos níveis listar no resumo
    max_niveis: int = 12
    max_fvgs: int = 8
    max_obs: int = 6
    # Lookback de candles (0 = todos)
    lookback: int = 120


CONFIG = ConfigSMC()


# ============================================================
# ESTRUTURAS
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
    preco_ref: float  # meio do bloco
    idx: int
    time: str = ""


@dataclass
class EventoEstrutura:
    tipo: str  # "BOS" | "CHOCH"
    direcao: str  # "ALTA" | "BAIXA"
    preco: float
    idx: int
    time: str = ""


# ============================================================
# NORMALIZAÇÃO DE CANDLES
# ============================================================

def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def normalizar_candles(
    dados: Union[Sequence[Dict[str, Any]], Sequence[Sequence[Any]], Any],
) -> List[Candle]:
    """
    Aceita:
    - list[dict] com chaves open/high/low/close/time/volume
    - list[list] no formato [time, open, high, low, close, volume?]
    - pandas DataFrame (duck typing)
    """
    rows: List[Any] = []

    # DataFrame?
    if hasattr(dados, "to_dict") and hasattr(dados, "columns"):
        try:
            rows = dados.to_dict(orient="records")
        except Exception:
            rows = list(dados)
    else:
        rows = list(dados)

    candles: List[Candle] = []
    for i, row in enumerate(rows):
        if isinstance(row, dict):
            # aliases comuns
            o = row.get("open", row.get("Open", row.get("o")))
            h = row.get("high", row.get("High", row.get("h")))
            l = row.get("low", row.get("Low", row.get("l")))
            c = row.get("close", row.get("Close", row.get("c")))
            t = row.get("time", row.get("Time", row.get("datetime", row.get("date", ""))))
            vol = row.get("volume", row.get("Volume", row.get("tick_volume", 0)))
        elif isinstance(row, (list, tuple)) and len(row) >= 5:
            # [time, open, high, low, close, volume?]
            if isinstance(row[0], (int, float)) and len(row) >= 5 and not isinstance(row[1], str):
                # possível [open, high, low, close, volume] sem time
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
        # reindex
        for i, c in enumerate(slice_c):
            c.idx = i
        return slice_c
    return candles


# ============================================================
# SWINGS
# ============================================================

def detectar_swings(
    candles: List[Candle],
    left: int = CONFIG.swing_left,
    right: int = CONFIG.swing_right,
) -> List[Swing]:
    """Pivôs clássicos: high/low maior/menor que 'left' e 'right' vizinhos."""
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


# ============================================================
# BOS / CHOCH
# ============================================================

def detectar_bos_choch(
    candles: List[Candle],
    swings: List[Swing],
) -> Tuple[List[EventoEstrutura], str]:
    """
    Estrutura simplificada:
    - Tendência de alta: Higher Highs + Higher Lows
    - Tendência de baixa: Lower Highs + Lower Lows
    - BOS: rompimento na direção da tendência
    - CHoCH: rompimento contra a tendência (possível reversão)
    """
    eventos: List[EventoEstrutura] = []
    if len(swings) < 4 or len(candles) < 5:
        return eventos, "LATERAL"

    # últimos swings relevantes
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

    # Percorre swings em ordem e detecta rompimentos pelo close posterior
    last_high: Optional[Swing] = None
    last_low: Optional[Swing] = None
    tendencia_atual = bias if bias != "LATERAL" else "LATERAL"

    for s in swings:
        if s.tipo == "HIGH":
            if last_high and tendencia_atual in ("ALTA", "LATERAL"):
                # BOS de alta: close acima do último high
                for c in candles[s.idx :]:
                    if c.close > last_high.preco:
                        eventos.append(
                            EventoEstrutura(
                                tipo="BOS" if tendencia_atual == "ALTA" else "CHOCH",
                                direcao="ALTA",
                                preco=last_high.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "ALTA"
                        break
            elif last_high and tendencia_atual == "BAIXA":
                for c in candles[s.idx :]:
                    if c.close > last_high.preco:
                        eventos.append(
                            EventoEstrutura(
                                tipo="CHOCH",
                                direcao="ALTA",
                                preco=last_high.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "ALTA"
                        break
            last_high = s

        if s.tipo == "LOW":
            if last_low and tendencia_atual in ("BAIXA", "LATERAL"):
                for c in candles[s.idx :]:
                    if c.close < last_low.preco:
                        eventos.append(
                            EventoEstrutura(
                                tipo="BOS" if tendencia_atual == "BAIXA" else "CHOCH",
                                direcao="BAIXA",
                                preco=last_low.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "BAIXA"
                        break
            elif last_low and tendencia_atual == "ALTA":
                for c in candles[s.idx :]:
                    if c.close < last_low.preco:
                        eventos.append(
                            EventoEstrutura(
                                tipo="CHOCH",
                                direcao="BAIXA",
                                preco=last_low.preco,
                                idx=c.idx,
                                time=c.time,
                            )
                        )
                        tendencia_atual = "BAIXA"
                        break
            last_low = s

    # bias final: último evento ou estrutura de swings
    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias


# ============================================================
# FVG
# ============================================================

def detectar_fvg(
    candles: List[Candle],
    min_pontos: float = CONFIG.fvg_min_pontos,
) -> List[FVG]:
    """
    FVG de 3 velas:
    - Bullish (COMPRA): low[i] > high[i-2]  → gap entre high[i-2] e low[i]
    - Bearish (VENDA):  high[i] < low[i-2] → gap entre high[i] e low[i-2]
    """
    fvgs: List[FVG] = []
    n = len(candles)
    if n < 3:
        return fvgs

    for i in range(2, n):
        c0, c1, c2 = candles[i - 2], candles[i - 1], candles[i]

        # Bullish FVG
        if c2.low > c0.high:
            gap = c2.low - c0.high
            if gap >= min_pontos:
                fvgs.append(
                    FVG(
                        tipo="COMPRA",
                        superior=c2.low,
                        inferior=c0.high,
                        idx=i,
                        time=c2.time,
                    )
                )

        # Bearish FVG
        if c2.high < c0.low:
            gap = c0.low - c2.high
            if gap >= min_pontos:
                fvgs.append(
                    FVG(
                        tipo="VENDA",
                        superior=c0.low,
                        inferior=c2.high,
                        idx=i,
                        time=c2.time,
                    )
                )

    # marca preenchimento parcial/total pelo preço posterior
    for fvg in fvgs:
        for c in candles[fvg.idx + 1 :]:
            if fvg.tipo == "COMPRA" and c.low <= fvg.inferior:
                fvg.preenchido = True
                break
            if fvg.tipo == "VENDA" and c.high >= fvg.superior:
                fvg.preenchido = True
                break

    return fvgs


# ============================================================
# ORDER BLOCKS
# ============================================================

def detectar_order_blocks(
    candles: List[Candle],
    swings: List[Swing],
) -> List[OrderBlock]:
    """
    OB simplificado:
    - Bullish OB: última vela de baixa antes de um impulso de alta que gera HH
    - Bearish OB: última vela de alta antes de um impulso de baixa que gera LL

    Heurística: vela oposta imediatamente anterior a um swing extremo +
    deslocamento forte nas 1-3 velas seguintes.
    """
    obs: List[OrderBlock] = []
    n = len(candles)
    if n < 5 or len(swings) < 2:
        return obs

    for s in swings[-8:]:  # últimos swings
        i = s.idx
        if i < 1 or i >= n - 1:
            continue

        if s.tipo == "LOW":
            # procura vela de baixa antes do bounce
            cand = candles[i]
            prev = candles[i - 1]
            # impulso: close futuro acima do high da vela do swing
            impulso = False
            for c in candles[i + 1 : min(i + 4, n)]:
                if c.close > cand.high:
                    impulso = True
                    break
            if impulso and prev.close < prev.open:
                obs.append(
                    OrderBlock(
                        tipo="COMPRA",
                        high=prev.high,
                        low=prev.low,
                        preco_ref=round((prev.high + prev.low) / 2, 1),
                        idx=prev.idx,
                        time=prev.time,
                    )
                )

        if s.tipo == "HIGH":
            cand = candles[i]
            prev = candles[i - 1]
            impulso = False
            for c in candles[i + 1 : min(i + 4, n)]:
                if c.close < cand.low:
                    impulso = True
                    break
            if impulso and prev.close > prev.open:
                obs.append(
                    OrderBlock(
                        tipo="VENDA",
                        high=prev.high,
                        low=prev.low,
                        preco_ref=round((prev.high + prev.low) / 2, 1),
                        idx=prev.idx,
                        time=prev.time,
                    )
                )

    # dedup por preço aproximado
    unicos: List[OrderBlock] = []
    for ob in obs:
        if not any(abs(ob.preco_ref - u.preco_ref) < 5 for u in unicos):
            unicos.append(ob)
    return unicos


# ============================================================
# LIQUIDEZ (equal highs / lows)
# ============================================================

def detectar_liquidez(
    swings: List[Swing],
    tol: float = CONFIG.eq_tol_pontos,
) -> Dict[str, List[float]]:
    bsl: List[float] = []  # buy-side liquidity (acima) = equal highs
    ssl: List[float] = []  # sell-side liquidity (abaixo) = equal lows

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


# ============================================================
# MOTOR PRINCIPAL
# ============================================================

def analisar_smc(
    dados_candles: Any,
    ativo: str = "WIN",
    timeframe: str = "5m",
    config: ConfigSMC = CONFIG,
) -> Dict[str, Any]:
    """
    Executa o motor completo e devolve dict pronto para JSON / pipeline.
    """
    candles = normalizar_candles(dados_candles)
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
    fvgs = detectar_fvg(candles, config.fvg_min_pontos)
    obs = detectar_order_blocks(candles, swings)
    liq = detectar_liquidez(swings, config.eq_tol_pontos)

    # eventos recentes
    bos = any(e.tipo == "BOS" for e in eventos[-3:])
    choch = any(e.tipo == "CHOCH" for e in eventos[-3:])

    # FVGs não preenchidos (mais relevantes)
    fvgs_abertos = [f for f in fvgs if not f.preenchido]
    fvgs_abertos = fvgs_abertos[-config.max_fvgs :]
    obs = obs[-config.max_obs :]

    preco_atual = candles[-1].close

    # níveis chave (texto estilo AnaliseGraficaSMC)
    estruturas: List[str] = []
    for s in swings[-config.max_niveis :]:
        label = "Swing High" if s.tipo == "HIGH" else "Swing Low"
        estruturas.append(f"{s.preco:.0f}: {label}")

    for ob in obs:
        estruturas.append(
            f"{ob.preco_ref:.0f}: OB {ob.tipo} ({ob.low:.0f}-{ob.high:.0f})"
        )

    for fvg in fvgs_abertos:
        estruturas.append(
            f"{(fvg.superior + fvg.inferior) / 2:.0f}: FVG {fvg.tipo} "
            f"({fvg.inferior:.0f}-{fvg.superior:.0f})"
        )

    liquidez_txt: List[str] = []
    for p in liq["bsl"]:
        liquidez_txt.append(f"BSL: {p:.0f} (equal highs / liquidez de compra acima)")
    for p in liq["ssl"]:
        liquidez_txt.append(f"SSL: {p:.0f} (equal lows / liquidez de venda abaixo)")

    # cenários operacionais simples
    cenarios: List[str] = []
    if bias == "BAIXA":
        res = next((o for o in reversed(obs) if o.tipo == "VENDA"), None)
        fvg_v = next((f for f in reversed(fvgs_abertos) if f.tipo == "VENDA"), None)
        zona = res.preco_ref if res else (fvg_v.superior if fvg_v else preco_atual)
        alvo = liq["ssl"][0] if liq["ssl"] else preco_atual * 0.99
        cenarios.append(
            f"Cenário Vendedor: rejeição na região {zona:.0f} "
            f"(OB/FVG de venda) visando {alvo:.0f}."
        )
        cenarios.append(
            "Cenário alternativo: varredura de liquidez acima antes da continuação de baixa."
        )
    elif bias == "ALTA":
        dem = next((o for o in reversed(obs) if o.tipo == "COMPRA"), None)
        fvg_c = next((f for f in reversed(fvgs_abertos) if f.tipo == "COMPRA"), None)
        zona = dem.preco_ref if dem else (fvg_c.inferior if fvg_c else preco_atual)
        alvo = liq["bsl"][0] if liq["bsl"] else preco_atual * 1.01
        cenarios.append(
            f"Cenário Comprador: defesa na região {zona:.0f} "
            f"(OB/FVG de compra) visando {alvo:.0f}."
        )
        cenarios.append(
            "Cenário alternativo: varredura de liquidez abaixo antes da continuação de alta."
        )
    else:
        cenarios.append(
            "Cenário Lateral: aguardar BOS com fechamento fora da faixa recente."
        )

    # confiança heurística
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
    conf = min(95, conf)

    # entrada / stop sugeridos (regras)
    entrada = None
    stop = None
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

    resultado: Dict[str, Any] = {
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
        "order_blocks": [
            {
                "tipo": o.tipo,
                "preco": o.preco_ref,
                "high": o.high,
                "low": o.low,
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
            {
                "tipo": e.tipo,
                "direcao": e.direcao,
                "preco": e.preco,
                "time": e.time,
            }
            for e in eventos[-6:]
        ],
        "swings_recentes": [
            {"tipo": s.tipo, "preco": s.preco, "time": s.time}
            for s in swings[-10:]
        ],
        # Campos compatíveis com AnaliseGraficaSMC (Gemini) / Setup Abertura
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
            "config": asdict(config),
        },
    }
    return resultado


def salvar_resultado(
    resultado: Dict[str, Any],
    caminho: Optional[Path] = None,
) -> Path:
    caminho = caminho or ARQUIVO_SAIDA
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    return caminho


# ============================================================
# HELPERS: CSV / MT5
# ============================================================

def carregar_csv(caminho: str) -> List[Dict[str, Any]]:
    import csv

    with open(caminho, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _candidatos_simbolo(symbol: str) -> List[str]:
    """Gera lista de possíveis nomes de contrato WIN/WDO no MT5."""
    s = (symbol or "").strip().upper()
    candidatos: List[str] = []

    def add(x: str):
        if x and x not in candidatos:
            candidatos.append(x)

    add(symbol)
    add(s)

    # Contínuos / genéricos comuns em corretoras BR
    if s.startswith("WIN") or s in ("", "WIN", "WIN$"):
        for c in (
            "WIN$",
            "WIN$N",
            "WIN@N",
            "WIN",
            "WINc",
            "WIN$",  # duplicata ok (add ignora)
        ):
            add(c)
        # Meses B3: F G H J K M N Q U V X Z + ano (ex.: WINQ26)
        meses = "FGHJKMNQUVXZ"
        from datetime import datetime as _dt

        agora = _dt.now()
        ano = agora.year % 100
        for m in meses:
            add(f"WIN{m}{ano:02d}")
            add(f"WIN{m}{ano + 1:02d}")

    if s.startswith("WDO") or s in ("WDO", "WDO$"):
        for c in ("WDO$", "WDO$N", "WDO@N", "WDO", "WDOc"):
            add(c)
        meses = "FGHJKMNQUVXZ"
        from datetime import datetime as _dt

        agora = _dt.now()
        ano = agora.year % 100
        for m in meses:
            add(f"WDO{m}{ano:02d}")
            add(f"WDO{m}{ano + 1:02d}")

    # Contratos já usados no Coletor_MT5 / Dados_MT5.json
    dados_mt5 = COLETAS_DIR / "Dados_MT5.json"
    if dados_mt5.exists():
        try:
            with open(dados_mt5, "r", encoding="utf-8") as f:
                data = json.load(f)
            contratos = data.get("contratos", {})
            if isinstance(contratos, dict):
                for nome in contratos.keys():
                    add(str(nome))
            # alguns layouts usam lista
            if isinstance(contratos, list):
                for item in contratos:
                    if isinstance(item, dict) and "symbol" in item:
                        add(str(item["symbol"]))
                    elif isinstance(item, str):
                        add(item)
        except Exception:
            pass

    return candidatos


def listar_simbolos_mt5(filtro: str = "WIN") -> List[str]:
    """Lista símbolos do MT5 que contêm o filtro (para diagnóstico)."""
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise RuntimeError("MetaTrader5 não instalado.") from e

    if not mt5.initialize():
        raise RuntimeError(f"Falha ao inicializar MT5: {mt5.last_error()}")

    symbols = mt5.symbols_get()
    mt5.shutdown()
    if not symbols:
        return []

    filtro_u = (filtro or "").upper()
    nomes = []
    for s in symbols:
        name = s.name
        if not filtro_u or filtro_u in name.upper():
            nomes.append(name)
    return sorted(nomes)


def carregar_mt5(
    symbol: str = "WIN$",
    timeframe_min: int = 5,
    qtd: int = 120,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Tenta puxar candles do MetaTrader5.
    Retorna (candles, simbolo_usado).
    Testa vários nomes de contrato se o informado falhar.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise RuntimeError(
            "MetaTrader5 não instalado. Use --csv ou passe candles manualmente."
        ) from e

    if not mt5.initialize():
        raise RuntimeError(f"Falha ao inicializar MT5: {mt5.last_error()}")

    tf_map = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
    }
    tf = tf_map.get(timeframe_min, mt5.TIMEFRAME_M5)

    candidatos = _candidatos_simbolo(symbol)
    tentativas: List[str] = []
    rates = None
    simbolo_ok = None

    for sym in candidatos:
        # garante que o símbolo está no Market Watch
        info = mt5.symbol_info(sym)
        if info is None:
            tentativas.append(f"{sym}=não existe")
            continue
        if not info.visible:
            mt5.symbol_select(sym, True)

        r = mt5.copy_rates_from_pos(sym, tf, 0, qtd)
        if r is not None and len(r) > 0:
            rates = r
            simbolo_ok = sym
            break
        tentativas.append(f"{sym}=sem rates")

    if rates is None or simbolo_ok is None:
        # diagnóstico: mostra alguns símbolos WIN/WDO disponíveis
        disponiveis = []
        all_sym = mt5.symbols_get()
        if all_sym:
            for s in all_sym:
                nu = s.name.upper()
                if "WIN" in nu or "WDO" in nu or "IND" in nu or "DOL" in nu:
                    disponiveis.append(s.name)
        mt5.shutdown()
        msg = (
            f"Sem rates para '{symbol}'.\n"
            f"Tentados: {', '.join(tentativas[:15])}...\n"
        )
        if disponiveis:
            msg += "Símbolos parecidos no MT5:\n  - " + "\n  - ".join(disponiveis[:30])
            msg += "\n\nUse: python Motor_SMC_Regras.py --mt5 --symbol NOME_EXATO"
        else:
            msg += (
                "Nenhum símbolo WIN/WDO visível. "
                "Abra o Market Watch no MT5 e habilite o mini índice/dólar."
            )
        raise RuntimeError(msg)

    out: List[Dict[str, Any]] = []
    for r in rates:
        out.append(
            {
                "time": datetime.fromtimestamp(r["time"]).isoformat(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["tick_volume"]),
            }
        )

    mt5.shutdown()
    print(f"✅ MT5 OK — símbolo usado: {simbolo_ok} ({len(out)} candles)")
    return out, simbolo_ok


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Motor SMC por regras (sem IA)")
    parser.add_argument("--csv", type=str, help="CSV com time,open,high,low,close")
    parser.add_argument("--mt5", action="store_true", help="Buscar candles no MT5")
    parser.add_argument("--symbol", type=str, default="WIN$", help="Símbolo MT5 (ex: WINQ26)")
    parser.add_argument("--tf", type=int, default=5, help="Timeframe minutos (1/5/15)")
    parser.add_argument("--ativo", type=str, default="WIN")
    parser.add_argument("--qtd", type=int, default=120)
    parser.add_argument(
        "--list-symbols",
        type=str,
        nargs="?",
        const="WIN",
        help="Lista símbolos MT5 (filtro opcional, ex: --list-symbols WIN)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(ARQUIVO_SAIDA),
        help="Caminho do JSON de saída",
    )
    parser.add_argument(
        "--fvg-min",
        type=float,
        default=CONFIG.fvg_min_pontos,
        help="Gap mínimo do FVG em pontos",
    )
    args = parser.parse_args()

    if args.list_symbols is not None:
        try:
            nomes = listar_simbolos_mt5(args.list_symbols)
            print(f"Símbolos MT5 com '{args.list_symbols}' ({len(nomes)}):")
            for n in nomes:
                print(f"  {n}")
            if not nomes:
                print("Nenhum encontrado. Tente --list-symbols WDO ou --list-symbols \"\"")
        except Exception as e:
            print(f"Erro: {e}")
        return

    cfg = ConfigSMC(fvg_min_pontos=args.fvg_min, lookback=args.qtd)

    if args.csv:
        candles = carregar_csv(args.csv)
        tf_label = f"{args.tf}m"
        print(f"✅ CSV OK — {len(candles)} linhas")
    elif args.mt5:
        candles, simbolo_usado = carregar_mt5(args.symbol, args.tf, args.qtd)
        tf_label = f"{args.tf}m"
        if not args.ativo or args.ativo == "WIN":
            # infere WIN/WDO pelo símbolo
            if "WDO" in simbolo_usado.upper():
                args.ativo = "WDO"
            else:
                args.ativo = "WIN"
    else:
        print("Informe --csv arquivo.csv ou --mt5")
        print("Exemplos:")
        print("  python Motor_SMC_Regras.py --list-symbols WIN")
        print("  python Motor_SMC_Regras.py --mt5 --symbol WINQ26 --tf 5")
        print("  python Motor_SMC_Regras.py --mt5 --symbol WDO$ --tf 5")
        return

    resultado = analisar_smc(
        candles,
        ativo=args.ativo,
        timeframe=tf_label,
        config=cfg,
    )
    path = salvar_resultado(resultado, Path(args.out))

    print("=" * 60)
    print(" MOTOR SMC POR REGRAS ")
    print("=" * 60)
    print(f"Ativo:        {resultado.get('ativo')}")
    print(f"Timeframe:    {resultado.get('timeframe')}")
    print(f"Preço:        {resultado.get('preco_atual')}")
    print(f"Bias:         {resultado.get('bias_direcional')}")
    print(f"BOS:          {resultado.get('bos')} | CHoCH: {resultado.get('choch')}")
    print(f"Confiança:    {resultado.get('confianca_visual')}/100")
    print(f"OBs:          {len(resultado.get('order_blocks', []))}")
    print(f"FVGs abertos: {len(resultado.get('fair_value_gaps', []))}")
    print(f"Arquivo:      {path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
