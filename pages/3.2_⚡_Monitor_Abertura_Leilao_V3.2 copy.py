# ============================================================
# ARQUIVO: pages/22_⚡_Monitor_Abertura_Leilao_V3.2.py
# VERSÃO: 4.1
# - Futuros globais integrados (ES, NQ, DXY, VIX, CL, Minério, Ouro, EWZ)
# - Projeção gap/abertura com pipeline + tilt global
# - Operacionais: Leilão + Ajuste (500/100) + Explosão
# ============================================================

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

try:
    import MetaTrader5 as mt5
    MT5_DISPONIVEL = True
except ImportError:
    MT5_DISPONIVEL = False

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Monitor de Abertura & Leilão",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%); }
    .card-bull {
        background-color: #0d381e; border-left: 5px solid #00c853;
        padding: 14px 16px; border-radius: 8px; margin-bottom: 10px;
    }
    .card-bear {
        background-color: #380d0d; border-left: 5px solid #ff3d00;
        padding: 14px 16px; border-radius: 8px; margin-bottom: 10px;
    }
    .card-neutral {
        background-color: #1a1c23; border-left: 5px solid #ffc107;
        padding: 14px 16px; border-radius: 8px; margin-bottom: 10px;
    }
    .separator {
        border: none; height: 2px;
        background: linear-gradient(90deg, #2a2d4a, transparent);
        margin: 18px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"
COLETAS_DIR.mkdir(parents=True, exist_ok=True)
ARQUIVO_HISTORICO_LEILAO = COLETAS_DIR / "historico_leilao_win.csv"

MAPEAMENTO_ADR = {
    "VALE3": "VALE",
    "PETR4": "PBR",
    "ITUB4": "ITUB",
    "BBDC4": "BBD",
    "BBAS3": "BDORY",
}

# Pesos alinhados ao pipeline + reforço de futuros globais
PESOS_ABERTURA = {
    "ewz": 0.25,
    "adrs": 0.30,          # cesta VALE/PETR/ITUB/BBD
    "sp500": 0.18,         # ES
    "nasdaq": 0.07,        # NQ
    "commodities": 0.12,   # minério + petróleo
    "dxy": 0.08,           # dólar índice (inverso no WIN)
}
PESOS_ADRS = {"VALE": 0.30, "PBR": 0.25, "ITUB": 0.25, "BBD": 0.20}
ALVO_AJUSTE_PTS = 500
LOSS_AJUSTE_PTS = 100


# ------------------------------------------------------------
# IO
# ------------------------------------------------------------
def carregar_json(nome: str) -> Dict[str, Any]:
    caminho = COLETAS_DIR / nome
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _preco_ativo(ativos: Dict, chave: str) -> float:
    item = ativos.get(chave) or {}
    if isinstance(item, dict):
        return _f(item.get("preco") or item.get("close") or item.get("valor"))
    return 0.0


def _var_ativo(ativos: Dict, chave: str) -> float:
    item = ativos.get(chave) or {}
    if isinstance(item, dict):
        return _f(item.get("variacao_pct") or item.get("change_percent"))
    return 0.0


# ------------------------------------------------------------
# MT5 helpers
# ------------------------------------------------------------
def obter_simbolo_win_ativo() -> str:
    if not MT5_DISPONIVEL:
        return "WIN$"
    candidatos = ["WIN$", "WINV26", "WINZ26", "WINQ26", "WINFUT"]
    # tenta achar o de maior volume entre prefixo WIN
    try:
        if not mt5.initialize():
            return "WIN$"
        simbolos = mt5.symbols_get()
        wins = []
        if simbolos:
            for s in simbolos:
                nome = s.name.upper()
                if nome.startswith("WIN") and len(nome) <= 6:
                    wins.append(s.name)
        for c in candidatos:
            if mt5.symbol_select(c, True):
                tick = mt5.symbol_info_tick(c)
                if tick and (tick.last > 0 or tick.bid > 0):
                    return c
        if wins:
            return wins[0]
    except Exception:
        pass
    return "WIN$"


def obter_refs_win_mt5() -> Dict[str, Any]:
    """Ajuste/session_close/last/teórico do contrato WIN no MT5."""
    out = {
        "simbolo": None,
        "last": None,
        "bid": None,
        "ask": None,
        "teorico": None,
        "session_close": None,
        "ajuste_settlement": None,
        "fonte": "MT5",
    }
    if not MT5_DISPONIVEL:
        out["fonte"] = "INDISPONIVEL"
        return out
    try:
        if not mt5.initialize():
            out["fonte"] = "FALHA_INIT"
            return out
        simbolo = obter_simbolo_win_ativo()
        mt5.symbol_select(simbolo, True)
        info = mt5.symbol_info(simbolo)
        tick = mt5.symbol_info_tick(simbolo)
        out["simbolo"] = simbolo
        if info:
            out["session_close"] = _f(getattr(info, "session_close", 0) or 0) or None
            teorico = getattr(info, "price_theoretical", None)
            if teorico and _f(teorico) > 0:
                out["teorico"] = _f(teorico)
            settlement = getattr(info, "session_price_settlement", None)
            if settlement and _f(settlement) > 0:
                out["ajuste_settlement"] = _f(settlement)
        if tick:
            out["last"] = _f(tick.last) if tick.last and tick.last > 0 else None
            out["bid"] = _f(tick.bid) if tick.bid and tick.bid > 0 else None
            out["ask"] = _f(tick.ask) if tick.ask and tick.ask > 0 else None
            if out["last"] is None:
                out["last"] = out["bid"] or out["ask"]
    except Exception as e:
        out["fonte"] = f"ERRO:{e}"
    return out


def obter_quote_finnhub(ticker: str) -> Optional[Dict[str, float]]:
    if not FINNHUB_KEY:
        return None
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
        res = requests.get(url, timeout=5).json()
        if "c" in res and res.get("c"):
            return {
                "preco": _f(res.get("c")),
                "var_pct": _f(res.get("dp")),
                "pc": _f(res.get("pc")),
            }
    except Exception:
        pass
    return None


# ------------------------------------------------------------
# PROJEÇÃO MELHORADA (pipeline + live)
# ------------------------------------------------------------
def montar_projecao() -> Dict[str, Any]:
    """
    Combina:
      1) Dados do pipeline (DadosAtivosUnificados, Metricas, Estimativa, Decisao_V2)
      2) MT5 live (last/teórico/session_close)
      3) Fórmula de abertura alinhada ao CalculadoraEstimativaAbertura
    """
    unificados = carregar_json("DadosAtivosUnificados.json")
    metricas = carregar_json("Metricas_Calculadas.json")
    estimativa = carregar_json("EstimativaAbertura.json")
    decisao_v2 = carregar_json("Decisao_V2.json")
    noticias_0900 = carregar_json("Noticias_Calendario_0900.json")

    ativos = unificados.get("ativos") or {}
    mt5_refs = obter_refs_win_mt5()

    # --- Ajuste / fechamento / last ---
    ajuste = (
        mt5_refs.get("ajuste_settlement")
        or _preco_ativo(ativos, "WIN_AJUSTE")
        or _preco_ativo(ativos, "WIN_FUT")
    )
    fechamento = (
        mt5_refs.get("session_close")
        or _preco_ativo(ativos, "WIN_PREV_CLOSE")
        or ajuste
    )
    last = (
        mt5_refs.get("teorico")
        or mt5_refs.get("last")
        or _preco_ativo(ativos, "WIN_LAST_TICK")
        or _preco_ativo(ativos, "WIN_FUT")
    )

    # V2 session override se existir
    sess = (decisao_v2.get("win_session") or {})
    precos_v2 = sess.get("precos") or {}
    if precos_v2.get("ajuste"):
        ajuste = _f(precos_v2["ajuste"], ajuste)
    if precos_v2.get("last_mt5"):
        last = _f(precos_v2["last_mt5"], last)
    if precos_v2.get("pre_abertura"):
        last = _f(precos_v2["pre_abertura"], last)

    # --- Variações para modelo ---
    ewz = _var_ativo(ativos, "EWZ")
    sp500 = _var_ativo(ativos, "SP500_FUT")
    nasdaq = _var_ativo(ativos, "NASDAQ_FUT")
    dxy = _var_ativo(ativos, "DXY")
    gold = _var_ativo(ativos, "GOLD")
    vale = _var_ativo(ativos, "VALE_ADR")
    petr = _var_ativo(ativos, "PETR_ADR")
    itub = _var_ativo(ativos, "ITUB_ADR")
    bbd = _var_ativo(ativos, "BBD_ADR")
    iron = _var_ativo(ativos, "IRON_ORE") or _var_ativo(ativos, "IRON_ORE_2M")
    oil = _var_ativo(ativos, "CRUDE_OIL")
    vix = _var_ativo(ativos, "VIX")

    # Preços dos futuros globais (para painel)
    px_sp500 = _preco_ativo(ativos, "SP500_FUT")
    px_nasdaq = _preco_ativo(ativos, "NASDAQ_FUT")
    px_dxy = _preco_ativo(ativos, "DXY")
    px_vix = _preco_ativo(ativos, "VIX")
    px_oil = _preco_ativo(ativos, "CRUDE_OIL")
    px_iron = _preco_ativo(ativos, "IRON_ORE") or _preco_ativo(ativos, "IRON_ORE_2M")
    px_gold = _preco_ativo(ativos, "GOLD")

    # Preferir métricas do pipeline quando existirem
    compostos = (metricas.get("indicadores_compostos") or {})
    macro = (metricas.get("indicadores_macro") or {})
    if macro.get("vix_change_pct") is not None:
        vix = _f(macro.get("vix_change_pct"), vix)
    if macro.get("crude_oil_change_pct") is not None:
        oil = _f(macro.get("crude_oil_change_pct"), oil)
    iron_obj = macro.get("iron_ore_fef2") or {}
    if isinstance(iron_obj, dict) and iron_obj.get("change_percent") is not None:
        iron = _f(iron_obj.get("change_percent"), iron)

    cesta_adrs = (
        vale * PESOS_ADRS["VALE"]
        + petr * PESOS_ADRS["PBR"]
        + itub * PESOS_ADRS["ITUB"]
        + bbd * PESOS_ADRS["BBD"]
    )
    cesta_comm = (iron * 0.50) + (oil * 0.50)

    # DXY alto pressiona emergentes/WIN → contribuição invertida
    var_modelo = (
        ewz * PESOS_ABERTURA["ewz"]
        + cesta_adrs * PESOS_ABERTURA["adrs"]
        + sp500 * PESOS_ABERTURA["sp500"]
        + nasdaq * PESOS_ABERTURA["nasdaq"]
        + cesta_comm * PESOS_ABERTURA["commodities"]
        + (-dxy) * PESOS_ABERTURA["dxy"]
    )

    # Estimativa do pipeline (se existir) — mistura 50/50 com modelo live
    est_win = ((estimativa.get("estimativas_abertura") or {}).get("WIN_INDICE") or {})
    var_pipeline = est_win.get("variacao_teorica_pct")
    abertura_pipeline = est_win.get("abertura_teorica_pontos")

    if var_pipeline is not None:
        var_teorica = 0.50 * _f(var_pipeline) + 0.50 * var_modelo
    else:
        var_teorica = var_modelo

    base_ref = ajuste or fechamento or 0.0
    if abertura_pipeline and base_ref:
        abertura_modelo = base_ref * (1 + var_teorica / 100.0)
        abertura_proj = round(0.50 * _f(abertura_pipeline) + 0.50 * abertura_modelo)
    elif base_ref:
        abertura_proj = round(base_ref * (1 + var_teorica / 100.0))
    else:
        abertura_proj = round(last) if last else 0

    gap_vs_ajuste = round(abertura_proj - ajuste, 0) if ajuste else None
    gap_vs_fech = round(abertura_proj - fechamento, 0) if fechamento else None
    gap_leilao_vs_ajuste = round(last - ajuste, 0) if (last and ajuste) else None

    # Indicadores compostos
    ind_adrs = compostos.get("indicador_adrs_brasileiras")
    if ind_adrs is None:
        ind_adrs = round(vale + petr + itub + bbd, 4)
    ind_ext = compostos.get("indicador_mercado_externo")
    if ind_ext is None:
        ind_ext = round((-vix) + oil + iron, 4)

    # Score explosão: ADRs + macro externo + tilt de futuros globais (ES/NQ)
    # ind_ext já traz -VIX + oil + iron (Calculadora)
    tilt_globais = (sp500 * 0.65 + nasdaq * 0.35)  # %
    score_explosao = round(
        _f(ind_adrs) * 0.45
        + _f(ind_ext) * 0.35
        + tilt_globais * 0.20,
        3,
    )

    # Notícia 3★
    alerta = (noticias_0900.get("alerta_noticia_0900") or {})
    tem_3est = bool(alerta.get("tem_evento_3_estrelas"))

    return {
        "timestamp": datetime.now().isoformat(),
        "simbolo_mt5": mt5_refs.get("simbolo"),
        "ajuste": ajuste or None,
        "fechamento_anterior": fechamento or None,
        "last_teorico": last or None,
        "abertura_projetada": abertura_proj or None,
        "var_teorica_pct": round(var_teorica, 4),
        "var_modelo_pct": round(var_modelo, 4),
        "var_pipeline_pct": round(_f(var_pipeline), 4) if var_pipeline is not None else None,
        "gap_projetado_vs_ajuste": gap_vs_ajuste,
        "gap_projetado_vs_fechamento": gap_vs_fech,
        "gap_leilao_vs_ajuste": gap_leilao_vs_ajuste,
        "detalhes": {
            "ewz": ewz, "sp500": sp500, "nasdaq": nasdaq, "dxy": dxy,
            "vale": vale, "petr": petr, "itub": itub, "bbd": bbd,
            "iron": iron, "oil": oil, "vix": vix, "gold": gold,
            "cesta_adrs": round(cesta_adrs, 4),
            "cesta_comm": round(cesta_comm, 4),
        },
        "futuros_globais": {
            "SP500_FUT": {"preco": px_sp500 or None, "var_pct": round(sp500, 3)},
            "NASDAQ_FUT": {"preco": px_nasdaq or None, "var_pct": round(nasdaq, 3)},
            "DXY": {"preco": px_dxy or None, "var_pct": round(dxy, 3)},
            "VIX": {"preco": px_vix or None, "var_pct": round(vix, 3)},
            "CRUDE_OIL": {"preco": px_oil or None, "var_pct": round(oil, 3)},
            "IRON_ORE": {"preco": px_iron or None, "var_pct": round(iron, 3)},
            "GOLD": {"preco": px_gold or None, "var_pct": round(gold, 3)},
            "EWZ": {"preco": _preco_ativo(ativos, "EWZ") or None, "var_pct": round(ewz, 3)},
        },
        "ind_adrs": round(_f(ind_adrs), 3),
        "ind_externo": round(_f(ind_ext), 3),
        "score_explosao": score_explosao,
        "tem_noticia_3est": tem_3est,
        "fonte_mt5": mt5_refs.get("fonte"),
        "decisao_v2": (decisao_v2.get("decisao") or {}),
        "opening_scenario_v2": (decisao_v2.get("opening_scenario") or {}),
    }


# ------------------------------------------------------------
# OPERACIONAIS (mesma lógica da página 1)
# ------------------------------------------------------------
def classificar_explosao(score: float) -> Dict[str, str]:
    if score >= 1.2:
        return {"direcao": "COMPRA", "forca": "ALTA", "status": "EXPLOSAO"}
    if score >= 0.45:
        return {"direcao": "COMPRA", "forca": "MODERADA", "status": "VIÉS_MODERADO"}
    if score <= -1.2:
        return {"direcao": "VENDA", "forca": "ALTA", "status": "EXPLOSAO"}
    if score <= -0.45:
        return {"direcao": "VENDA", "forca": "MODERADA", "status": "VIÉS_MODERADO"}
    return {"direcao": "NEUTRO", "forca": "FRACA", "status": "SEM_EXPLOSAO"}


def operacional_leilao(proj: Dict[str, Any]) -> Dict[str, Any]:
    dist = proj.get("gap_leilao_vs_ajuste")
    if dist is None:
        dist = proj.get("gap_projetado_vs_ajuste")

    if dist is None:
        gap_classe, direcao_gap = "INDEFINIDO", "NEUTRO"
    elif abs(dist) < 80:
        gap_classe, direcao_gap = "MORNO", "NEUTRO"
    elif abs(dist) < 150:
        gap_classe = "MODERADO"
        direcao_gap = "ALTA" if dist > 0 else "BAIXA"
    elif abs(dist) < 400:
        gap_classe = "RELEVANTE"
        direcao_gap = "ALTA" if dist > 0 else "BAIXA"
    else:
        gap_classe = "EXTREMO"
        direcao_gap = "ALTA" if dist > 0 else "BAIXA"

    exp = classificar_explosao(_f(proj.get("score_explosao")))
    alinhado = (
        (direcao_gap == "ALTA" and exp["direcao"] == "COMPRA" and exp["forca"] in ("ALTA", "MODERADA"))
        or (direcao_gap == "BAIXA" and exp["direcao"] == "VENDA" and exp["forca"] in ("ALTA", "MODERADA"))
    )
    divergente = (
        (direcao_gap == "ALTA" and exp["direcao"] == "VENDA" and exp["forca"] in ("ALTA", "MODERADA"))
        or (direcao_gap == "BAIXA" and exp["direcao"] == "COMPRA" and exp["forca"] in ("ALTA", "MODERADA"))
    )

    bloqueios: List[str] = []
    if proj.get("tem_noticia_3est"):
        bloqueios.append("Notícia ⭐⭐⭐ Brasil 09:00 — leilão pode ser sujo")
    if gap_classe in ("MORNO", "INDEFINIDO"):
        bloqueios.append("Gap de leilão pequeno ou indefinido")

    if bloqueios and (proj.get("tem_noticia_3est") or gap_classe in ("MORNO", "INDEFINIDO")):
        rec, lado, motivo = "AGUARDAR", "NEUTRO", bloqueios[0]
    elif alinhado and gap_classe in ("MODERADO", "RELEVANTE", "EXTREMO"):
        rec = "PREPARAR_EXPLOSAO"
        lado = "COMPRA" if direcao_gap == "ALTA" else "VENDA"
        motivo = f"Leilão {direcao_gap} alinhado com drivers ({exp['forca']}) — não fade"
    elif divergente or (direcao_gap != "NEUTRO" and exp["forca"] == "FRACA"):
        rec = "PREPARAR_AJUSTE"
        lado = "VENDA" if direcao_gap == "ALTA" else "COMPRA"
        motivo = f"Candidato a retorno ao ajuste (gap {direcao_gap}, drivers {exp['direcao']}/{exp['forca']})"
    else:
        rec, lado, motivo = "AGUARDAR", "NEUTRO", "Sem confluência clara no leilão"

    return {
        "recomendacao": rec,
        "lado_preparar": lado,
        "motivo": motivo,
        "gap_classe": gap_classe,
        "direcao_gap": direcao_gap,
        "dist_pts": dist,
        "alinhado": alinhado,
        "divergente": divergente,
        "explosao": exp,
        "bloqueios": bloqueios,
    }


def operacional_ajuste(proj: Dict[str, Any], lei: Dict[str, Any]) -> Dict[str, Any]:
    dist = proj.get("gap_leilao_vs_ajuste")
    if dist is None:
        dist = proj.get("gap_projetado_vs_ajuste")
    ajuste = proj.get("ajuste")

    if dist is not None and dist > 20:
        lado, pos = "VENDA", "ACIMA"
    elif dist is not None and dist < -20:
        lado, pos = "COMPRA", "ABAIXO"
    else:
        lado, pos = "NEUTRO", "NO_AJUSTE"

    entrada = ajuste
    if lado == "VENDA" and entrada:
        stop = entrada + LOSS_AJUSTE_PTS
        alvo = entrada - ALVO_AJUSTE_PTS
    elif lado == "COMPRA" and entrada:
        stop = entrada - LOSS_AJUSTE_PTS
        alvo = entrada + ALVO_AJUSTE_PTS
    else:
        stop = alvo = None

    bloqueios: List[str] = []
    if dist is not None and abs(dist) < 100:
        bloqueios.append(f"Distância pequena ({dist:+.0f} pts) — R:R do alvo 500 piora")
    if proj.get("tem_noticia_3est"):
        bloqueios.append("Notícia ⭐⭐⭐ — aguardar reação")
    exp = lei.get("explosao") or {}
    if lado == "VENDA" and exp.get("direcao") == "COMPRA" and exp.get("forca") in ("ALTA", "MODERADA"):
        bloqueios.append("Explosão de COMPRA — não fade o gap")
    if lado == "COMPRA" and exp.get("direcao") == "VENDA" and exp.get("forca") in ("ALTA", "MODERADA"):
        bloqueios.append("Explosão de VENDA — não fade o gap")

    # V2
    d2 = proj.get("decisao_v2") or {}
    vies_v2 = str(d2.get("vies_final") or "").upper()
    conf_v2 = int(d2.get("confianca") or 0)
    if conf_v2 >= 60:
        if lado == "VENDA" and vies_v2 in ("COMPRA", "ALTA", "BULL"):
            bloqueios.append(f"V2 COMPRA ({conf_v2}%) contra a venda no ajuste")
        if lado == "COMPRA" and vies_v2 in ("VENDA", "BAIXA", "BEAR"):
            bloqueios.append(f"V2 VENDA ({conf_v2}%) contra a compra no ajuste")

    if lado == "NEUTRO":
        status, motivo = "AGUARDAR", "Sem gap relevante vs ajuste"
    elif bloqueios:
        status, motivo = "BLOQUEADO", bloqueios[0]
    elif dist is not None and abs(dist) < 150:
        status, motivo = "ATENÇÃO", f"Distância moderada ({dist:+.0f} pts)"
    else:
        status, motivo = "LIBERADO", f"{lado} no ajuste com contexto favorável"

    return {
        "lado": lado,
        "posicao": pos,
        "status": status,
        "motivo": motivo,
        "bloqueios": bloqueios,
        "entrada": entrada,
        "stop": stop,
        "alvo": alvo,
        "dist_pts": dist,
        "alvo_pts": ALVO_AJUSTE_PTS,
        "loss_pts": LOSS_AJUSTE_PTS,
    }


def preferencia_operacional(lei: Dict, aj: Dict, exp: Dict) -> Dict[str, Any]:
    if aj.get("status") == "LIBERADO" and exp.get("status") == "EXPLOSAO":
        return {
            "preferencia": "EXPLOSAO",
            "conflito": True,
            "texto": "Explosão forte — priorizar continuação, não fade no ajuste",
        }
    if aj.get("status") == "LIBERADO":
        return {
            "preferencia": "AJUSTE",
            "conflito": False,
            "texto": f"Setup de {aj['lado']} no ajuste liberado",
        }
    if lei.get("recomendacao") == "PREPARAR_EXPLOSAO":
        return {
            "preferencia": "EXPLOSAO",
            "conflito": False,
            "texto": lei.get("motivo") or "Preparar explosão",
        }
    if lei.get("recomendacao") == "PREPARAR_AJUSTE" or aj.get("status") == "ATENÇÃO":
        return {
            "preferencia": "AJUSTE_ATENCAO",
            "conflito": False,
            "texto": aj.get("motivo") or lei.get("motivo") or "Ajuste com atenção",
        }
    return {
        "preferencia": "AGUARDAR",
        "conflito": False,
        "texto": lei.get("motivo") or aj.get("motivo") or "Aguardar",
    }


# ------------------------------------------------------------
# ARBITRAGEM ADR x B3 (mantida)
# ------------------------------------------------------------
def analisar_descasamento_leilao(limiar_spread: float = 0.5) -> pd.DataFrame:
    rows = []
    mt5_ok = MT5_DISPONIVEL and mt5.initialize()
    for ticker_b3, ticker_adr in MAPEAMENTO_ADR.items():
        q = obter_quote_finnhub(ticker_adr)
        var_adr = q["var_pct"] if q else 0.0
        preco_leilao = 0.0
        var_b3 = 0.0
        if mt5_ok:
            try:
                mt5.symbol_select(ticker_b3, True)
                tick = mt5.symbol_info_tick(ticker_b3)
                info = mt5.symbol_info(ticker_b3)
                if tick and info and getattr(info, "session_close", 0) > 0:
                    teorico = getattr(info, "price_theoretical", 0.0)
                    preco_leilao = _f(teorico) if teorico and _f(teorico) > 0 else _f(tick.last)
                    if preco_leilao > 0:
                        var_b3 = round(((preco_leilao / info.session_close) - 1) * 100, 2)
            except Exception:
                pass
        spread = round(var_adr - var_b3, 2)
        if spread >= limiar_spread:
            sinal = "COMPRA B3 (atrás da ADR)"
        elif spread <= -limiar_spread:
            sinal = "VENDA B3 (esticada vs ADR)"
        else:
            sinal = "NEUTRO"
        rows.append({
            "Ação B3": ticker_b3,
            "ADR": ticker_adr,
            "Preço Leilão B3": preco_leilao if preco_leilao > 0 else None,
            "Var B3 %": var_b3,
            "Var ADR %": var_adr,
            "Spread %": spread,
            "Sinal": sinal,
        })
    return pd.DataFrame(rows)


def obter_snapshot_leilao_win() -> Optional[Dict[str, Any]]:
    refs = obter_refs_win_mt5()
    if not refs.get("last") and not refs.get("teorico"):
        return None
    snap = {
        "Data_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Simbolo": refs.get("simbolo"),
        "Ultimo_Preco_Leilao": refs.get("teorico") or refs.get("last"),
        "Bid": refs.get("bid"),
        "Ask": refs.get("ask"),
        "Preco_Ajuste_Referencia": refs.get("ajuste_settlement") or refs.get("session_close"),
        "Fechamento_Anterior": refs.get("session_close"),
    }
    df = pd.DataFrame([snap])
    if ARQUIVO_HISTORICO_LEILAO.exists():
        df.to_csv(ARQUIVO_HISTORICO_LEILAO, mode="a", header=False, index=False)
    else:
        df.to_csv(ARQUIVO_HISTORICO_LEILAO, index=False)
    return snap


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("⚡ Monitor de Abertura & Leilão")
st.caption(
    "Versão 4.0 · Projeção com pipeline (Coletor/Métricas/Estimativa/V2) · "
    "Operacionais: Leilão · Ajuste 500/100 · Explosão ADRs/Macro"
)

with st.sidebar:
    st.header("Controles")
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    limiar_spread = st.slider("Limiar spread ADR×B3 (%)", 0.2, 2.0, 0.5, 0.1)
    st.markdown("---")
    st.caption("Arquivos do pipeline lidos da pasta Coletas/")
    for nome in [
        "DadosAtivosUnificados.json",
        "Metricas_Calculadas.json",
        "EstimativaAbertura.json",
        "Decisao_V2.json",
        "Noticias_Calendario_0900.json",
    ]:
        ok = (COLETAS_DIR / nome).exists()
        st.write(f"{'✅' if ok else '❌'} {nome}")

# Dados centrais
proj = montar_projecao()
lei = operacional_leilao(proj)
aj = operacional_ajuste(proj, lei)
exp_info = classificar_explosao(_f(proj.get("score_explosao")))
pref = preferencia_operacional(lei, aj, exp_info)

# ===== PREFERÊNCIA =====
st.markdown("### 🎯 Preferência operacional agora")
pref_key = pref["preferencia"]
if pref_key == "AJUSTE":
    classe = "card-bull" if aj["lado"] == "COMPRA" else "card-bear"
    titulo = f"✅ PREFERÊNCIA: {aj['lado']} NO AJUSTE"
elif pref_key == "EXPLOSAO":
    classe = "card-bull" if exp_info["direcao"] == "COMPRA" else "card-bear"
    if exp_info["direcao"] == "NEUTRO":
        classe = "card-neutral"
    titulo = f"🚀 PREFERÊNCIA: EXPLOSÃO {exp_info['direcao']}"
elif pref_key == "AJUSTE_ATENCAO":
    classe, titulo = "card-neutral", "⚠️ AJUSTE COM ATENÇÃO"
else:
    classe, titulo = "card-neutral", "🟡 AGUARDAR"

st.markdown(
    f"""
    <div class="{classe}">
        <h3 style="margin:0 0 6px;">{titulo}</h3>
        <div>{pref.get("texto") or ""}</div>
        {"<div style='margin-top:6px;'>⚠️ Conflito entre fade do ajuste e explosão</div>" if pref.get("conflito") else ""}
    </div>
    """,
    unsafe_allow_html=True,
)

# ===== PROJEÇÃO =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 📐 Projeção de gap e abertura (pipeline + MT5)")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Ajuste", f"{proj['ajuste']:,.0f}" if proj.get("ajuste") else "—")
with c2:
    st.metric("Last / Teórico", f"{proj['last_teorico']:,.0f}" if proj.get("last_teorico") else "—")
with c3:
    st.metric(
        "Abertura projetada",
        f"{proj['abertura_projetada']:,.0f}" if proj.get("abertura_projetada") else "—",
    )
with c4:
    g = proj.get("gap_leilao_vs_ajuste")
    if g is None:
        g = proj.get("gap_projetado_vs_ajuste")
    st.metric("Gap vs ajuste", f"{g:+.0f} pts" if g is not None else "—")
with c5:
    st.metric("Var. teórica", f"{proj['var_teorica_pct']:+.3f}%")

d1, d2, d3, d4 = st.columns(4)
with d1:
    st.caption(f"Modelo live: {proj['var_modelo_pct']:+.3f}%")
with d2:
    vp = proj.get("var_pipeline_pct")
    st.caption(f"Pipeline estimativa: {vp:+.3f}%" if vp is not None else "Pipeline estimativa: —")
with d3:
    st.caption(f"Contrato MT5: {proj.get('simbolo_mt5') or '—'} ({proj.get('fonte_mt5')})")
with d4:
    st.caption("Notícia 3★ 09:00: " + ("🚨 SIM" if proj.get("tem_noticia_3est") else "✅ NÃO"))

# ===== FUTUROS GLOBAIS =====
st.markdown("#### 🌍 Futuros globais (drivers externos)")
fg = proj.get("futuros_globais") or {}
g1, g2, g3, g4 = st.columns(4)
with g1:
    es = fg.get("SP500_FUT") or {}
    st.metric("ES (S&P Fut)", f"{es['preco']:,.2f}" if es.get("preco") else "—",
              delta=f"{es.get('var_pct', 0):+.2f}%")
with g2:
    nq = fg.get("NASDAQ_FUT") or {}
    st.metric("NQ (Nasdaq Fut)", f"{nq['preco']:,.2f}" if nq.get("preco") else "—",
              delta=f"{nq.get('var_pct', 0):+.2f}%")
with g3:
    dx = fg.get("DXY") or {}
    st.metric("DXY", f"{dx['preco']:,.2f}" if dx.get("preco") else "—",
              delta=f"{dx.get('var_pct', 0):+.2f}%")
with g4:
    vx = fg.get("VIX") or {}
    st.metric("VIX", f"{vx['preco']:,.2f}" if vx.get("preco") else "—",
              delta=f"{vx.get('var_pct', 0):+.2f}%")

g5, g6, g7, g8 = st.columns(4)
with g5:
    cl = fg.get("CRUDE_OIL") or {}
    st.metric("Petróleo (CL)", f"{cl['preco']:,.2f}" if cl.get("preco") else "—",
              delta=f"{cl.get('var_pct', 0):+.2f}%")
with g6:
    fe = fg.get("IRON_ORE") or {}
    st.metric("Minério", f"{fe['preco']:,.2f}" if fe.get("preco") else "—",
              delta=f"{fe.get('var_pct', 0):+.2f}%")
with g7:
    au = fg.get("GOLD") or {}
    st.metric("Ouro", f"{au['preco']:,.2f}" if au.get("preco") else "—",
              delta=f"{au.get('var_pct', 0):+.2f}%")
with g8:
    ez = fg.get("EWZ") or {}
    st.metric("EWZ", f"{ez['preco']:,.2f}" if ez.get("preco") else "—",
              delta=f"{ez.get('var_pct', 0):+.2f}%")

# Viés rápido dos globais
es_v = (fg.get("SP500_FUT") or {}).get("var_pct") or 0.0
nq_v = (fg.get("NASDAQ_FUT") or {}).get("var_pct") or 0.0
dx_v = (fg.get("DXY") or {}).get("var_pct") or 0.0
vx_v = (fg.get("VIX") or {}).get("var_pct") or 0.0
tilt = es_v * 0.65 + nq_v * 0.35 - dx_v * 0.4 - max(vx_v, 0) * 0.3
if tilt >= 0.35:
    st.caption(f"🌍 Tilt global: **COMPRA** ({tilt:+.2f}) — futuros favorecem gap de alta no WIN")
elif tilt <= -0.35:
    st.caption(f"🌍 Tilt global: **VENDA** ({tilt:+.2f}) — futuros favorecem gap de baixa no WIN")
else:
    st.caption(f"🌍 Tilt global: **NEUTRO** ({tilt:+.2f})")

with st.expander("Detalhes dos drivers da projeção", expanded=False):
    det = proj.get("detalhes") or {}
    st.write(
        pd.DataFrame(
            [
                {"Driver": "EWZ", "Var %": det.get("ewz")},
                {"Driver": "S&P Fut (ES)", "Var %": det.get("sp500")},
                {"Driver": "Nasdaq Fut (NQ)", "Var %": det.get("nasdaq")},
                {"Driver": "DXY", "Var %": det.get("dxy")},
                {"Driver": "VALE ADR", "Var %": det.get("vale")},
                {"Driver": "PETR ADR", "Var %": det.get("petr")},
                {"Driver": "ITUB ADR", "Var %": det.get("itub")},
                {"Driver": "BBD ADR", "Var %": det.get("bbd")},
                {"Driver": "Minério", "Var %": det.get("iron")},
                {"Driver": "Petróleo", "Var %": det.get("oil")},
                {"Driver": "VIX", "Var %": det.get("vix")},
                {"Driver": "Ouro", "Var %": det.get("gold")},
                {"Driver": "Cesta ADRs", "Var %": det.get("cesta_adrs")},
                {"Driver": "Cesta Comm", "Var %": det.get("cesta_comm")},
            ]
        )
    )

# ===== LEILÃO =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 🔔 Operacional de Leilão")

rec = lei["recomendacao"]
if rec == "PREPARAR_EXPLOSAO":
    classe = "card-bull" if lei["lado_preparar"] == "COMPRA" else "card-bear"
    titulo = f"🚀 PREPARAR EXPLOSÃO — {lei['lado_preparar']}"
elif rec == "PREPARAR_AJUSTE":
    classe = "card-bull" if lei["lado_preparar"] == "COMPRA" else "card-bear"
    titulo = f"🎯 PREPARAR AJUSTE — {lei['lado_preparar']} NO AJUSTE"
else:
    classe, titulo = "card-neutral", "🟡 AGUARDAR — SEM EDGE NO LEILÃO"

st.markdown(
    f"""
    <div class="{classe}">
        <h3 style="margin:0 0 6px;">{titulo}</h3>
        <div>{lei.get("motivo") or ""}</div>
        <div style="margin-top:6px;opacity:.9;">
            Gap leilão: <b>{lei.get("direcao_gap")}</b> ({lei.get("gap_classe")})
            &nbsp;|&nbsp; Drivers: <b>{exp_info.get("direcao")}</b> ({exp_info.get("forca")})
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ===== OPERACIONAIS ABERTURA =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### 🎯 Operacionais de Abertura")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### 1️⃣ Retorno ao Ajuste")
    st.caption("Acima → VENDA no ajuste · Abaixo → COMPRA no ajuste · Alvo 500 / Loss 100")
    st.markdown(
        f"**Status:** "
        + (
            "🟢 LIBERADO"
            if aj["status"] == "LIBERADO"
            else "🟡 ATENÇÃO"
            if aj["status"] == "ATENÇÃO"
            else "🔴 BLOQUEADO"
            if aj["status"] == "BLOQUEADO"
            else "⚪ AGUARDAR"
        )
    )
    st.markdown(f"**Lado:** `{aj['lado']}`")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Dist. ajuste", f"{aj['dist_pts']:+.0f}" if aj.get("dist_pts") is not None else "—")
    with m2:
        st.metric("Entrada", f"{aj['entrada']:,.0f}" if aj.get("entrada") else "—")
    with m3:
        st.metric("Alvo/Stop", f"{aj['alvo_pts']}/{aj['loss_pts']}")
    if aj.get("entrada") and aj.get("stop") and aj.get("alvo"):
        st.caption(f"Stop {aj['stop']:,.0f} · Alvo {aj['alvo']:,.0f}")
    st.caption(aj.get("motivo") or "")
    if aj.get("bloqueios"):
        with st.expander("Bloqueios"):
            for b in aj["bloqueios"]:
                st.write(f"• {b}")

with col_b:
    st.markdown("#### 2️⃣ Explosão Pós-Abertura")
    st.caption("Score = 55% Σ ADRs + 45% (−VIX + Minério + Petróleo)")
    st.markdown(
        f"**Status:** "
        + (
            "🚀 EXPLOSÃO"
            if exp_info["status"] == "EXPLOSAO"
            else "🟡 VIÉS MODERADO"
            if exp_info["status"] == "VIÉS_MODERADO"
            else "⚪ SEM EXPLOSÃO"
        )
    )
    st.markdown(f"**Direção:** `{exp_info['direcao']}` · **Força:** `{exp_info['forca']}`")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.metric("Score", f"{proj['score_explosao']:+.2f}")
    with e2:
        st.metric("Σ ADRs", f"{proj['ind_adrs']:+.2f}%")
    with e3:
        st.metric("Σ Macro", f"{proj['ind_externo']:+.2f}%")
    st.info(
        "Drivers a favor do gap → não fade. Drivers neutros/contra → retorno ao ajuste ganha prioridade."
    )

# ===== V2 resumo =====
d2 = proj.get("decisao_v2") or {}
if d2:
    st.markdown('<hr class="separator">', unsafe_allow_html=True)
    st.markdown("### 🚀 Decisão V2 (referência)")
    v1, v2, v3, v4 = st.columns(4)
    with v1:
        st.metric("Viés V2", str(d2.get("vies_final") or "—"))
    with v2:
        st.metric("Confiança", f"{d2.get('confianca') or 0}%")
    with v3:
        st.metric("Entrada", f"{d2['entrada']:,.0f}" if d2.get("entrada") else "—")
    with v4:
        st.metric("Stop", f"{d2['stop_loss']:,.0f}" if d2.get("stop_loss") else "—")

# ===== ARBITRAGEM =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### ⚖️ Arbitragem Ações B3 vs ADRs (leilão)")
df_desc = analisar_descasamento_leilao(limiar_spread=limiar_spread)
if not df_desc.empty:
    st.dataframe(df_desc, use_container_width=True, hide_index=True)
else:
    st.warning("Sem dados de descasamento (MT5/Finnhub).")

# ===== SNAPSHOT / HISTÓRICO =====
st.markdown('<hr class="separator">', unsafe_allow_html=True)
st.markdown("### ⏱️ Leilão em tempo real (MT5)")
col_l, col_r = st.columns([1, 2])
with col_l:
    if st.button("📸 Gravar snapshot do leilão"):
        snap = obter_snapshot_leilao_win()
        if snap:
            st.success("Snapshot gravado.")
            st.json(snap)
        else:
            st.error("Falha ao capturar snapshot MT5.")
with col_r:
    if ARQUIVO_HISTORICO_LEILAO.exists():
        try:
            df_hist = pd.read_csv(ARQUIVO_HISTORICO_LEILAO)
            if not df_hist.empty:
                st.dataframe(df_hist.tail(8), use_container_width=True, hide_index=True)
                cols_plot = [c for c in ["Ultimo_Preco_Leilao", "Preco_Ajuste_Referencia", "Fechamento_Anterior"] if c in df_hist.columns]
                if len(df_hist) >= 2 and cols_plot:
                    fig = px.line(
                        df_hist,
                        x="Data_Hora" if "Data_Hora" in df_hist.columns else df_hist.index,
                        y=cols_plot,
                        title="Formação do leilão vs referências",
                    )
                    fig.update_layout(
                        plot_bgcolor="#0e1117",
                        paper_bgcolor="#0e1117",
                        font_color="#e6edf3",
                        height=300,
                        margin=dict(l=10, r=10, t=30, b=10),
                    )
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao ler histórico: {e}")
    else:
        st.info("Nenhum histórico de leilão gravado ainda.")

st.caption(f"Última execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if auto_refresh:
    time.sleep(5)
    st.rerun()
