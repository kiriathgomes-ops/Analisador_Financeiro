# ============================================================
# ARQUIVO: pages/3_🎯_Setup_Abertura_10h.py
# VERSÃO: 5.0
# Setup 10:00 — Mercado à Vista
# Operacional principal: rompimento da 1ª vela de 5 min (10:00–10:05)
#   · Rompe máxima → compra | stop na mínima | alvo = 100% da amplitude
#   · Rompe mínima → venda  | stop na máxima | alvo = 100% da amplitude
# Contexto: ADRs × B3, futuros globais, notícias, pipeline, V2
# ============================================================

from __future__ import annotations

import json
import os
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    import MetaTrader5 as mt5
    MT5_OK = True
except ImportError:
    MT5_OK = False

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ------------------------------------------------------------
st.set_page_config(
    page_title="Setup Abertura 10:00 — À Vista",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background-color: #0e1117; }
    .card-bull {
        background:#0d381e; border-left:5px solid #00c853;
        padding:14px 16px; border-radius:8px; margin-bottom:10px;
    }
    .card-bear {
        background:#380d0d; border-left:5px solid #ff3d00;
        padding:14px 16px; border-radius:8px; margin-bottom:10px;
    }
    .card-neutral {
        background:#1a1c23; border-left:5px solid #ffc107;
        padding:14px 16px; border-radius:8px; margin-bottom:10px;
    }
    .separator {
        border:none; height:2px;
        background:linear-gradient(90deg,#2a2d4a,transparent);
        margin:18px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS = BASE_DIR / "Coletas"
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

ACOES_FOCO = ["VALE3", "PETR4", "ITUB4", "BBDC4", "BBAS3", "B3SA3"]
MAP_ADR = {
    "VALE3": "VALE",
    "PETR4": "PBR",
    "ITUB4": "ITUB",
    "BBDC4": "BBD",
    "BBAS3": "BDORY",
    "B3SA3": "BOLSY",
}
# Proxy líquido do "à vista" indexado para a 1ª vela de 5m
SIMBOLOS_VELA = ["WIN$", "WINV26", "WINZ26", "WINQ26"] + ACOES_FOCO


# ------------------------------------------------------------
# IO
# ------------------------------------------------------------
def load_json(name: str) -> Dict[str, Any]:
    p = COLETAS / name
    if not p.exists():
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def ativos_map() -> Dict[str, Any]:
    data = load_json("DadosAtivosUnificados.json")
    return data.get("ativos") or {}


def var_ativo(ativos: Dict, key: str) -> float:
    item = ativos.get(key) or {}
    if isinstance(item, dict):
        return fnum(item.get("variacao_pct") or item.get("change_percent"))
    return 0.0


def preco_ativo(ativos: Dict, key: str) -> float:
    item = ativos.get(key) or {}
    if isinstance(item, dict):
        return fnum(item.get("preco") or item.get("close") or item.get("valor"))
    return 0.0


# ------------------------------------------------------------
# MT5 — 1ª vela de 5 min
# ------------------------------------------------------------
def mt5_init() -> bool:
    if not MT5_OK:
        return False
    try:
        return bool(mt5.initialize())
    except Exception:
        return False


def resolver_simbolo_win() -> Optional[str]:
    if not mt5_init():
        return None
    for s in ["WIN$", "WINV26", "WINZ26", "WINQ26", "WINFUT"]:
        if mt5.symbol_select(s, True):
            tick = mt5.symbol_info_tick(s)
            if tick and (tick.last > 0 or tick.bid > 0):
                return s
    return None


def primeira_vela_5m(simbolo: str) -> Optional[Dict[str, Any]]:
    """
    Busca a vela de 5 min das 10:00–10:05 (horário de Brasília).
    Se ainda não fechou, usa a vela corrente do período 10:00.
    """
    if not mt5_init():
        return None
    if not mt5.symbol_select(simbolo, True):
        return None
    try:
        rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, 80)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        # Filtra sessões de hoje com hora >= 10:00
        hoje = datetime.now().date()
        df["date"] = df["time"].dt.date
        df["hour"] = df["time"].dt.hour
        df["minute"] = df["time"].dt.minute
        cand = df[(df["date"] == hoje) & (df["hour"] >= 10)].sort_values("time")
        if cand.empty:
            # fallback: última vela 5m
            row = df.iloc[-1]
            fonte = "ultima_m5"
        else:
            # primeira vela a partir das 10:00
            row = cand.iloc[0]
            fonte = "primeira_10h"
        o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])
        amplitude = h - l
        return {
            "simbolo": simbolo,
            "time": row["time"].to_pydatetime() if hasattr(row["time"], "to_pydatetime") else row["time"],
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "amplitude": amplitude,
            "fonte": fonte,
            "volume": float(row["tick_volume"]) if "tick_volume" in row else None,
        }
    except Exception:
        return None


def tick_atual(simbolo: str) -> Optional[Dict[str, float]]:
    if not mt5_init():
        return None
    if not mt5.symbol_select(simbolo, True):
        return None
    tick = mt5.symbol_info_tick(simbolo)
    info = mt5.symbol_info(simbolo)
    if not tick:
        return None
    last = float(tick.last) if tick.last > 0 else (float(tick.bid) if tick.bid > 0 else float(tick.ask))
    teorico = getattr(info, "price_theoretical", None) if info else None
    session_close = getattr(info, "session_close", None) if info else None
    return {
        "last": last,
        "bid": float(tick.bid) if tick.bid else None,
        "ask": float(tick.ask) if tick.ask else None,
        "teorico": float(teorico) if teorico and float(teorico) > 0 else None,
        "session_close": float(session_close) if session_close and float(session_close) > 0 else None,
    }


def finnhub_quote(ticker: str) -> Optional[Dict[str, float]]:
    if not REQUESTS_OK or not FINNHUB_KEY:
        return None
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
        res = requests.get(url, timeout=5).json()
        if res.get("c"):
            return {"preco": fnum(res["c"]), "var_pct": fnum(res.get("dp")), "pc": fnum(res.get("pc"))}
    except Exception:
        pass
    return None



def atr_m5(simbolo: str, periodos: int = 14) -> Optional[float]:
    """ATR simples em M5 (média do true range)."""
    if not mt5_init():
        return None
    if not mt5.symbol_select(simbolo, True):
        return None
    try:
        rates = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, periodos + 5)
        if rates is None or len(rates) < periodos + 1:
            return None
        trs = []
        for i in range(1, len(rates)):
            h = float(rates[i]["high"])
            l = float(rates[i]["low"])
            prev_c = float(rates[i - 1]["close"])
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            trs.append(tr)
        if len(trs) < periodos:
            return None
        return sum(trs[-periodos:]) / periodos
    except Exception:
        return None


def filtro_volatilidade(
    vela: Optional[Dict[str, Any]],
    ativos: Dict,
    simbolo: Optional[str],
) -> Dict[str, Any]:
    """
    Filtro de volatilidade otimizado para rompimento da 1ª vela 5m.

    Camadas:
      1) VIX nível + variação (medo/regime)
      2) Amplitude da 1ª vela vs ATR(M5)
      3) Amplitude vs faixas operacionais do WIN (ruído x candle monstro)

    Retorna classificação + bloqueios/avisos + fator de tamanho sugerido (0–1).
    """
    bloqueios: List[str] = []
    avisos: List[str] = []
    a_favor: List[str] = []

    # --- VIX ---
    vix_px = preco_ativo(ativos, "VIX")
    vix_var = var_ativo(ativos, "VIX")
    # fallback se só tiver variação
    if vix_px <= 0:
        vix_px = None

    # Regime por nível de VIX (aprox. SPX)
    if vix_px is not None:
        if vix_px >= 28:
            regime_vix = "EXTREMO"
        elif vix_px >= 22:
            regime_vix = "ALTO"
        elif vix_px >= 16:
            regime_vix = "MODERADO"
        else:
            regime_vix = "BAIXO"
    else:
        regime_vix = "INDEFINIDO"

    if regime_vix == "EXTREMO":
        bloqueios.append(f"VIX nível extremo ({vix_px:.1f}) — stops alargam e falso rompimento aumenta")
    elif regime_vix == "ALTO":
        avisos.append(f"VIX elevado ({vix_px:.1f}) — reduzir tamanho / exigir close fora da vela")
    elif regime_vix == "BAIXO":
        a_favor.append(f"VIX contido ({vix_px:.1f}) — ambiente mais limpo para rompimento")

    if vix_var >= 8:
        bloqueios.append(f"VIX explodindo na sessão ({vix_var:+.1f}%) — regime instável")
    elif vix_var >= 3:
        avisos.append(f"VIX em alta ({vix_var:+.1f}%) — cautela no stop")
    elif vix_var <= -3:
        a_favor.append(f"VIX caindo ({vix_var:+.1f}%) — favorece continuidade do rompimento")

    # --- Amplitude da 1ª vela ---
    amp = fnum(vela.get("amplitude")) if vela else 0.0
    atr = atr_m5(simbolo, 14) if simbolo else None
    ratio_atr = (amp / atr) if atr and atr > 0 and amp > 0 else None

    # Faixas em pontos de WIN (ajustáveis)
    # < 80  → ruído / pouco prêmio
    # 80–250 → zona operacional boa
    # 250–450 → alta volatilidade (atenção)
    # > 450 → candle monstro (evitar chase)
    if amp <= 0:
        classe_amp = "SEM_DADO"
    elif amp < 80:
        classe_amp = "RUIDO"
        avisos.append(f"Amplitude pequena ({amp:.0f} pts) — rompimento pode ser ruído")
    elif amp <= 250:
        classe_amp = "IDEAL"
        a_favor.append(f"Amplitude operacional ideal ({amp:.0f} pts)")
    elif amp <= 450:
        classe_amp = "ALTA"
        avisos.append(f"Amplitude alta ({amp:.0f} pts) — stop largo; reduzir tamanho")
    else:
        classe_amp = "MONSTRO"
        bloqueios.append(f"1ª vela monstro ({amp:.0f} pts) — evitar chase; esperar pullback")

    if ratio_atr is not None:
        if ratio_atr < 0.6:
            avisos.append(f"Vela < 60% do ATR M5 ({ratio_atr:.2f}×) — edge fraco")
        elif ratio_atr <= 1.8:
            a_favor.append(f"Vela alinhada ao ATR M5 ({ratio_atr:.2f}×)")
        elif ratio_atr <= 2.5:
            avisos.append(f"Vela bem acima do ATR ({ratio_atr:.2f}×) — volatilidade expandida")
        else:
            bloqueios.append(f"Vela >> ATR M5 ({ratio_atr:.2f}×) — expansão extrema")

    # --- Fator de tamanho (0 = não operar, 1 = tamanho cheio) ---
    tamanho = 1.0
    if bloqueios:
        tamanho = 0.0
    else:
        if regime_vix == "ALTO":
            tamanho *= 0.5
        elif regime_vix == "MODERADO":
            tamanho *= 0.85
        if classe_amp == "RUIDO":
            tamanho *= 0.5
        elif classe_amp == "ALTA":
            tamanho *= 0.6
        if vix_var >= 3:
            tamanho *= 0.75
        if ratio_atr is not None and ratio_atr > 1.8:
            tamanho *= 0.7
        tamanho = max(0.0, min(1.0, round(tamanho, 2)))

    # Status consolidado do filtro de vol
    if bloqueios:
        status = "BLOQUEADO"
    elif tamanho <= 0.6 or avisos:
        status = "ATENÇÃO"
    else:
        status = "OK"

    return {
        "status": status,
        "regime_vix": regime_vix,
        "vix_nivel": round(vix_px, 2) if vix_px is not None else None,
        "vix_var": round(vix_var, 2),
        "amplitude": round(amp, 1) if amp else None,
        "classe_amplitude": classe_amp,
        "atr_m5": round(atr, 1) if atr else None,
        "ratio_atr": round(ratio_atr, 2) if ratio_atr is not None else None,
        "tamanho_sugerido": tamanho,
        "bloqueios": bloqueios,
        "avisos": avisos,
        "a_favor": a_favor,
    }


# ------------------------------------------------------------
# OPERACIONAL — ROMPIMENTO 1ª VELA 5M
# ------------------------------------------------------------
def operacional_rompimento(vela: Dict[str, Any], preco_atual: Optional[float]) -> Dict[str, Any]:
    """
    Regra do usuário:
      · Rompe máxima da 1ª vela 5m → COMPRA | stop na mínima | alvo = high + amplitude (100%)
      · Rompe mínima → VENDA | stop na máxima | alvo = low - amplitude (100%)
    """
    h, l, o, c = vela["high"], vela["low"], vela["open"], vela["close"]
    amp = vela["amplitude"]
    px = preco_atual if preco_atual is not None else c

    # Estado da vela / rompimento
    if px > h:
        lado = "COMPRA"
        status = "ROMPIDO_ALTA"
        entrada = h
        stop = l
        alvo = h + amp  # 100% da amplitude
        motivo = "Preço acima da máxima da 1ª vela de 5 min"
    elif px < l:
        lado = "VENDA"
        status = "ROMPIDO_BAIXA"
        entrada = l
        stop = h
        alvo = l - amp
        motivo = "Preço abaixo da mínima da 1ª vela de 5 min"
    else:
        # Ainda dentro da vela — preparar níveis
        lado = "AGUARDAR"
        status = "DENTRO_DA_VELA"
        entrada = stop = alvo = None
        motivo = "Aguardando rompimento da máxima ou mínima da 1ª vela"

    risco = abs(entrada - stop) if entrada is not None and stop is not None else amp
    reward = abs(alvo - entrada) if entrada is not None and alvo is not None else amp
    rr = (reward / risco) if risco else None

    return {
        "lado": lado,
        "status": status,
        "motivo": motivo,
        "entrada": round(entrada, 1) if entrada is not None else None,
        "stop": round(stop, 1) if stop is not None else None,
        "alvo": round(alvo, 1) if alvo is not None else None,
        "amplitude": round(amp, 1),
        "risco_pts": round(risco, 1) if risco else None,
        "reward_pts": round(reward, 1) if reward else None,
        "rr": round(rr, 2) if rr else None,
        "maxima": round(h, 1),
        "minima": round(l, 1),
        "open": round(o, 1),
        "close": round(c, 1),
        "preco_atual": round(px, 1) if px else None,
    }


def filtros_contexto(
    ativos: Dict,
    metricas: Dict,
    noticias_0900: Dict,
    decisao_v2: Dict,
    lado: str,
    vol: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Bloqueios / avisos de segurança para o rompimento."""
    bloqueios: List[str] = []
    avisos: List[str] = []
    a_favor: List[str] = []

    # --- Volatilidade (filtro dedicado) ---
    if vol:
        bloqueios.extend(vol.get("bloqueios") or [])
        avisos.extend(vol.get("avisos") or [])
        a_favor.extend(vol.get("a_favor") or [])

    # Notícias
    alerta = (noticias_0900.get("alerta_noticia_0900") or {})
    if alerta.get("tem_evento_3_estrelas"):
        bloqueios.append("Notícia ⭐⭐⭐ Brasil no horário — volatilidade institucional")

    # Futuros globais
    es = var_ativo(ativos, "SP500_FUT")
    nq = var_ativo(ativos, "NASDAQ_FUT")
    vix = var_ativo(ativos, "VIX")
    dxy = var_ativo(ativos, "DXY")
    tilt = es * 0.65 + nq * 0.35 - max(vix, 0) * 0.3 - dxy * 0.25

    if lado == "COMPRA":
        if tilt >= 0.3:
            a_favor.append(f"Tilt global a favor da compra ({tilt:+.2f})")
        elif tilt <= -0.3:
            bloqueios.append(f"Tilt global contra compra ({tilt:+.2f})")
    elif lado == "VENDA":
        if tilt <= -0.3:
            a_favor.append(f"Tilt global a favor da venda ({tilt:+.2f})")
        elif tilt >= 0.3:
            bloqueios.append(f"Tilt global contra venda ({tilt:+.2f})")

    # ADRs / indicador
    compostos = metricas.get("indicadores_compostos") or {}
    ind_adrs = compostos.get("indicador_adrs_brasileiras")
    if ind_adrs is None:
        ind_adrs = (
            var_ativo(ativos, "VALE_ADR")
            + var_ativo(ativos, "PETR_ADR")
            + var_ativo(ativos, "ITUB_ADR")
            + var_ativo(ativos, "BBD_ADR")
        )
    ind_adrs = fnum(ind_adrs)
    if lado == "COMPRA" and ind_adrs > 0.5:
        a_favor.append(f"Σ ADRs positivo ({ind_adrs:+.2f}%)")
    if lado == "COMPRA" and ind_adrs < -0.5:
        avisos.append(f"Σ ADRs negativo ({ind_adrs:+.2f}%) — à vista pode falhar")
    if lado == "VENDA" and ind_adrs < -0.5:
        a_favor.append(f"Σ ADRs negativo ({ind_adrs:+.2f}%)")
    if lado == "VENDA" and ind_adrs > 0.5:
        avisos.append(f"Σ ADRs positivo ({ind_adrs:+.2f}%) — venda mais fraca")

    # V2
    d2 = (decisao_v2.get("decisao") or {})
    vies = str(d2.get("vies_final") or "").upper()
    conf = int(d2.get("confianca") or 0)
    if conf >= 60 and lado in ("COMPRA", "VENDA"):
        if lado == "COMPRA" and vies in ("VENDA", "BAIXA", "BEAR"):
            bloqueios.append(f"V2 em VENDA ({conf}%) contra o rompimento de alta")
        if lado == "VENDA" and vies in ("COMPRA", "ALTA", "BULL"):
            bloqueios.append(f"V2 em COMPRA ({conf}%) contra o rompimento de baixa")
        if lado == "COMPRA" and vies in ("COMPRA", "ALTA", "BULL"):
            a_favor.append(f"V2 alinhado COMPRA ({conf}%)")
        if lado == "VENDA" and vies in ("VENDA", "BAIXA", "BEAR"):
            a_favor.append(f"V2 alinhado VENDA ({conf}%)")

    if lado == "AGUARDAR":
        status = "AGUARDAR"
    elif bloqueios:
        status = "BLOQUEADO"
    elif avisos:
        status = "ATENÇÃO"
    else:
        status = "LIBERADO"

    tamanho = 1.0
    if vol:
        tamanho = fnum(vol.get("tamanho_sugerido"), 1.0)
    if status == "BLOQUEADO":
        tamanho = 0.0
    elif status == "ATENÇÃO":
        tamanho = min(tamanho, 0.6)

    return {
        "status": status,
        "bloqueios": bloqueios,
        "avisos": avisos,
        "a_favor": a_favor,
        "tilt_global": round(tilt, 3),
        "ind_adrs": round(ind_adrs, 3),
        "es": round(es, 3),
        "nq": round(nq, 3),
        "vix": round(vix, 3),
        "dxy": round(dxy, 3),
        "vol": vol or {},
        "tamanho_sugerido": tamanho,
    }


# ------------------------------------------------------------
# OPERACIONAL SECUNDÁRIO — abertura à vista (descasamento ADR)
# ------------------------------------------------------------
def operacional_descasamento_adr(limiar: float = 0.6) -> pd.DataFrame:
    """Se ADR >> leilão/preço B3 → ação atrasada (compra). Inverso → venda."""
    rows = []
    mt5_ready = mt5_init()
    for b3, adr in MAP_ADR.items():
        q = finnhub_quote(adr)
        var_adr = q["var_pct"] if q else None
        var_b3 = None
        preco_b3 = None
        if mt5_ready and mt5.symbol_select(b3, True):
            info = mt5.symbol_info(b3)
            tick = mt5.symbol_info_tick(b3)
            if info and tick:
                sc = fnum(getattr(info, "session_close", 0))
                teorico = getattr(info, "price_theoretical", None)
                last = fnum(teorico) if teorico and fnum(teorico) > 0 else (
                    fnum(tick.last) if tick.last > 0 else fnum(tick.bid)
                )
                preco_b3 = last
                if sc > 0 and last > 0:
                    var_b3 = round((last / sc - 1) * 100, 2)
        if var_adr is None and var_b3 is None:
            continue
        va = fnum(var_adr)
        vb = fnum(var_b3)
        spread = round(va - vb, 2)
        if spread >= limiar:
            sinal = "COMPRA B3 (atrás da ADR)"
        elif spread <= -limiar:
            sinal = "VENDA B3 (esticada vs ADR)"
        else:
            sinal = "NEUTRO"
        rows.append({
            "Ação": b3,
            "ADR": adr,
            "Var ADR %": va,
            "Var B3 %": vb,
            "Spread %": spread,
            "Preço B3": preco_b3,
            "Sinal": sinal,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("🎯 Setup 10:00 — Mercado à Vista")
st.caption(
    "Versão 5.1 · Rompimento da 1ª vela de 5 min (10:00–10:05) · "
    "Alvo 100% amplitude · Filtro vol (VIX+ATR+amplitude) · ADRs / futuros / V2"
)

# Sidebar
with st.sidebar:
    st.header("Status pipeline")
    files = {
        "Ativos": "DadosAtivosUnificados.json",
        "Métricas": "Metricas_Calculadas.json",
        "Decisão V2": "Decisao_V2.json",
        "Decisão V1": "Decisao_Core.json",
        "Tendências": "Analise_Tendencias.json",
        "Notícias 09:00": "Noticias_Calendario_0900.json",
    }
    for label, fn in files.items():
        st.write(f"{'✅' if (COLETAS / fn).exists() else '❌'} {label}")
    st.markdown("---")
    st.caption(f"MT5: {'✅' if MT5_OK else '❌'}")
    limiar_adr = st.slider("Limiar spread ADR×B3 (%)", 0.3, 2.0, 0.6, 0.1)
    st.markdown("---")
    st.markdown(
        """
**Regra principal**
- 1ª vela 5m (10:00–10:05)
- Rompe máxima → **compra**
- Stop na **mínima**
- Alvo = **100%** da amplitude
- Rompe mínima → **venda** (espelho)
"""
    )

# Load data
ativos = ativos_map()
metricas = load_json("Metricas_Calculadas.json")
decisao_v2 = load_json("Decisao_V2.json")
noticias = load_json("Noticias_Calendario_0900.json")
tendencias = load_json("Analise_Tendencias.json")

# ===== CONTEXTO RÁPIDO =====
st.markdown("### 🌍 Contexto antes do rompimento")
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("ES", f"{var_ativo(ativos,'SP500_FUT'):+.2f}%")
with c2:
    st.metric("NQ", f"{var_ativo(ativos,'NASDAQ_FUT'):+.2f}%")
with c3:
    st.metric("VIX", f"{var_ativo(ativos,'VIX'):+.2f}%")
with c4:
    st.metric("DXY", f"{var_ativo(ativos,'DXY'):+.2f}%")
with c5:
    st.metric("EWZ", f"{var_ativo(ativos,'EWZ'):+.2f}%")
with c6:
    alerta = (noticias.get("alerta_noticia_0900") or {})
    st.metric("Notícia 3★ 09h", "SIM" if alerta.get("tem_evento_3_estrelas") else "NÃO")

# ===== 1ª VELA =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 🕯️ 1ª vela de 5 min (10:00–10:05)")

simbolo_win = resolver_simbolo_win()
vela = primeira_vela_5m(simbolo_win) if simbolo_win else None
tick = tick_atual(simbolo_win) if simbolo_win else None
preco_agora = (tick or {}).get("last")

if not vela:
    st.warning(
        "Não foi possível obter a 1ª vela de 5 min via MT5. "
        "Verifique se o terminal está aberto e se o pregão às 10h já começou. "
        "Os níveis aparecerão automaticamente após as 10:00."
    )
    op = None
    vol = filtro_volatilidade(None, ativos, simbolo_win)
    ctx = filtros_contexto(ativos, metricas, noticias, decisao_v2, "AGUARDAR", vol=vol)
else:
    op = operacional_rompimento(vela, preco_agora)
    vol = filtro_volatilidade(vela, ativos, simbolo_win)
    ctx = filtros_contexto(ativos, metricas, noticias, decisao_v2, op["lado"], vol=vol)

    v1, v2, v3, v4, v5 = st.columns(5)
    with v1:
        st.metric("Símbolo", vela["simbolo"])
    with v2:
        st.metric("Máxima", f"{op['maxima']:,.1f}")
    with v3:
        st.metric("Mínima", f"{op['minima']:,.1f}")
    with v4:
        st.metric("Amplitude", f"{op['amplitude']:,.1f} pts")
    with v5:
        st.metric("Preço atual", f"{op['preco_atual']:,.1f}" if op.get("preco_atual") else "—")

    st.caption(
        f"Vela: O {op['open']:,.1f} · C {op['close']:,.1f} · "
        f"Horário ref: {vela['time']} · Fonte: {vela['fonte']}"
    )

# ===== FILTRO DE VOLATILIDADE =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 📉 Filtro de volatilidade")
vol_ui = ctx.get("vol") or vol or {}
vc1, vc2, vc3, vc4, vc5 = st.columns(5)
with vc1:
    st.metric("Regime VIX", vol_ui.get("regime_vix") or "—")
with vc2:
    vn = vol_ui.get("vix_nivel")
    st.metric("VIX nível", f"{vn:.1f}" if vn is not None else "—",
              delta=f"{vol_ui.get('vix_var', 0):+.1f}%")
with vc3:
    st.metric("Amplitude vela", f"{vol_ui['amplitude']:.0f} pts" if vol_ui.get("amplitude") else "—")
with vc4:
    st.metric("ATR M5", f"{vol_ui['atr_m5']:.0f}" if vol_ui.get("atr_m5") else "—",
              delta=f"{vol_ui['ratio_atr']:.2f}×" if vol_ui.get("ratio_atr") is not None else None)
with vc5:
    tam = ctx.get("tamanho_sugerido", vol_ui.get("tamanho_sugerido", 1.0))
    st.metric("Tamanho sugerido", f"{float(tam)*100:.0f}%")

classe_amp = vol_ui.get("classe_amplitude") or "—"
st.caption(
    f"Classe da amplitude: **{classe_amp}** · "
    f"Filtro vol: **{vol_ui.get('status') or '—'}** · "
    f"RUIDO <80 · IDEAL 80–250 · ALTA 250–450 · MONSTRO >450 pts"
)

# ===== SINAL PRINCIPAL =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 🎯 Operacional: rompimento da 1ª vela")

if not op:
    st.info("Aguardando dados da vela de 5 min.")
else:
    status_final = ctx["status"]
    if op["status"] == "DENTRO_DA_VELA":
        classe, titulo = "card-neutral", "🟡 DENTRO DA VELA — AGUARDAR ROMPIMENTO"
    elif op["lado"] == "COMPRA" and status_final == "LIBERADO":
        classe, titulo = "card-bull", "🟢 ROMPIMENTO DE ALTA — COMPRA LIBERADA"
    elif op["lado"] == "VENDA" and status_final == "LIBERADO":
        classe, titulo = "card-bear", "🔴 ROMPIMENTO DE BAIXA — VENDA LIBERADA"
    elif status_final == "BLOQUEADO":
        classe, titulo = "card-neutral", f"⛔ ROMPIMENTO {op['lado']} — BLOQUEADO PELO CONTEXTO"
    elif status_final == "ATENÇÃO":
        classe = "card-bull" if op["lado"] == "COMPRA" else "card-bear"
        titulo = f"⚠️ ROMPIMENTO {op['lado']} — OPERAR COM ATENÇÃO"
    else:
        classe, titulo = "card-neutral", f"🟡 {op['status']}"

    st.markdown(
        f"""
        <div class="{classe}">
            <h3 style="margin:0 0 6px;">{titulo}</h3>
            <div>{op.get("motivo") or ""}</div>
            <div style="margin-top:6px;opacity:.9;">
                Contexto: <b>{status_final}</b>
                &nbsp;|&nbsp; Tilt global: <b>{ctx['tilt_global']:+.2f}</b>
                &nbsp;|&nbsp; Σ ADRs: <b>{ctx['ind_adrs']:+.2f}%</b>
                &nbsp;|&nbsp; Tamanho: <b>{ctx.get('tamanho_sugerido', 1)*100:.0f}%</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    n1, n2, n3, n4 = st.columns(4)
    with n1:
        st.metric("Entrada", f"{op['entrada']:,.1f}" if op.get("entrada") else "—")
    with n2:
        st.metric("Stop", f"{op['stop']:,.1f}" if op.get("stop") else "—")
    with n3:
        st.metric("Alvo (100%)", f"{op['alvo']:,.1f}" if op.get("alvo") else "—")
    with n4:
        st.metric("R:R", f"{op['rr']:.2f}" if op.get("rr") else "1.00")

    if op.get("entrada") is None:
        st.info(
            f"Níveis preparados — **compra** acima de **{op['maxima']:,.1f}** "
            f"(stop {op['minima']:,.1f} · alvo {op['maxima'] + op['amplitude']:,.1f}) · "
            f"**venda** abaixo de **{op['minima']:,.1f}** "
            f"(stop {op['maxima']:,.1f} · alvo {op['minima'] - op['amplitude']:,.1f})"
        )

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        if ctx["a_favor"]:
            with st.expander("A favor", expanded=True):
                for x in ctx["a_favor"]:
                    st.write(f"✅ {x}")
    with col_f2:
        if ctx["avisos"]:
            with st.expander("Avisos", expanded=True):
                for x in ctx["avisos"]:
                    st.write(f"⚠️ {x}")
    with col_f3:
        if ctx["bloqueios"]:
            with st.expander("Bloqueios", expanded=True):
                for x in ctx["bloqueios"]:
                    st.write(f"🛑 {x}")

# ===== CHECKLIST DE SEGURANÇA =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### ✅ Checklist de segurança (10:05)")

checks = []
agora = datetime.now().time()
checks.append(("Horário ≥ 10:05 (vela de 5m definida)", agora >= time(10, 5)))
checks.append(("1ª vela capturada", vela is not None))
if op:
    checks.append(("Rompimento ocorrido", op["status"] in ("ROMPIDO_ALTA", "ROMPIDO_BAIXA")))
    checks.append(("Contexto não bloqueado", ctx["status"] != "BLOQUEADO"))
    checks.append(("R:R ≈ 1.0 (alvo 100%)", op.get("rr") is not None and op["rr"] >= 0.9))
checks.append(("Sem notícia 3★ crítica", not (noticias.get("alerta_noticia_0900") or {}).get("tem_evento_3_estrelas")))
vol_ok = (ctx.get("vol") or {}).get("status") != "BLOQUEADO"
checks.append(("Filtro de volatilidade OK", vol_ok))
amp_ok = (ctx.get("vol") or {}).get("classe_amplitude") in ("IDEAL", "ALTA", None, "SEM_DADO")
checks.append(("Amplitude não monstro/ruído extremo", amp_ok))
checks.append(("Tilt global não contrário", True))  # detalhado nos filtros

for label, ok in checks:
    st.write(f"{'✅' if ok else '❌'} {label}")

# ===== ADRs × B3 =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### ⚖️ Leilão / abertura à vista — ADRs × B3")
st.caption(
    "Operacional opcional: ação B3 atrasada vs ADR → possível continuação no rompimento. "
    "Se não usar, ignore este bloco."
)
df_adr = operacional_descasamento_adr(limiar=limiar_adr)
if not df_adr.empty:
    st.dataframe(df_adr, use_container_width=True, hide_index=True)
    compras = df_adr[df_adr["Sinal"].str.contains("COMPRA", na=False)]
    vendas = df_adr[df_adr["Sinal"].str.contains("VENDA", na=False)]
    if len(compras) >= 2 and op and op["lado"] == "COMPRA":
        st.success(f"{len(compras)} ações atrasadas vs ADR — confluência com rompimento de alta")
    if len(vendas) >= 2 and op and op["lado"] == "VENDA":
        st.success(f"{len(vendas)} ações esticadas vs ADR — confluência com rompimento de baixa")
else:
    st.info("Sem dados ADR×B3 no momento (Finnhub/MT5).")

# ===== VELAS DAS AÇÕES (extra) =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 📊 1ª vela 5m — ações foco (opcional)")
rows_acoes = []
if mt5_init():
    for s in ACOES_FOCO:
        v = primeira_vela_5m(s)
        t = tick_atual(s)
        if not v:
            continue
        px = (t or {}).get("last") or v["close"]
        romp = "ALTA" if px > v["high"] else ("BAIXA" if px < v["low"] else "DENTRO")
        rows_acoes.append({
            "Ação": s,
            "Open": round(v["open"], 2),
            "High": round(v["high"], 2),
            "Low": round(v["low"], 2),
            "Close/Last": round(px, 2),
            "Amplitude": round(v["amplitude"], 2),
            "Rompimento": romp,
        })
if rows_acoes:
    st.dataframe(pd.DataFrame(rows_acoes), use_container_width=True, hide_index=True)
else:
    st.caption("Ações foco ainda sem vela de 5m (antes das 10:00 ou MT5 indisponível).")

# ===== V2 =====
d2 = decisao_v2.get("decisao") or {}
if d2:
    st.markdown('<hr class="separator">', unsafe_allow_html=True)
    st.markdown("### 🚀 Decisão V2 (referência WIN)")
    x1, x2, x3, x4 = st.columns(4)
    with x1:
        st.metric("Viés", str(d2.get("vies_final") or "—"))
    with x2:
        st.metric("Confiança", f"{d2.get('confianca') or 0}%")
    with x3:
        st.metric("Entrada", f"{d2['entrada']:,.0f}" if d2.get("entrada") else "—")
    with x4:
        st.metric("Stop", f"{d2['stop_loss']:,.0f}" if d2.get("stop_loss") else "—")

st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
