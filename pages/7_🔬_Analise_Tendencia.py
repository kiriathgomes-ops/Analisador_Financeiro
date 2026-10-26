# -*- coding: utf-8 -*-
"""
Módulo: pages/7_🔬_Analise_Tendencia.py
Versão: 3.8.1 — Histograma colorido por sinal + inversão visual p/ ativos inversos
Objetivo: Mapear velocidade e direção dos ativos via 12 coletas rolantes.

Mudança vs. 3.8:
  - "Ouro" adicionado ao ATIVOS_INVERSOS (safe haven, sobe com aversão a risco)
  - _mini_histograma_svg recebe flag `inverter`. Ativos inversos são plotados
    com sinal negado: DXY +0.5% → barra vermelha (ruim p/ WIN). Alinha o
    histograma com o Status e o Δ Agora, sem ambiguidade visual.
  - Tooltip mostra "+X.XXX% (inverso)" quando aplicável.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from config import COLETAS_DIR


st.set_page_config(page_title="Quant Terminal - Análise de Tendência", layout="wide")


# v3.8.1 — bump quando JANELAS, formato de dados ou cálculo mudar.
_CACHE_VERSION = "v3.8.1"


# ==============================================================================
# CATEGORIAS — chaves reais do Coleta_rom-X.json
# ==============================================================================
CATEGORIAS = {
    "🇧🇷 Futuros & Taxas B3": [
        ("WIN", ["WIN_FUT", "BMFBOVESPA:WIN1!", "B3_AJUSTE_WIN", "B3_FECHAMENTO_WIN"]),
        ("WDO", ["WDO_FUT", "BMFBOVESPA:WDO1!", "B3_AJUSTE_WDO", "B3_FECHAMENTO_WDO"]),
        ("DI1 2027", ["BMFBOVESPA:DI1F2027", "DI1_2027"]),
        ("DI1 2029", ["BMFBOVESPA:DI1F2029", "DI1_2029"]),
    ],
    "🌍 Drivers Globais & Risco": [
        ("S&P500", ["CME_MINI:ES1!", "SP500_FUT"]),
        ("Nasdaq", ["CME_MINI:NQ1!", "NASDAQ_FUT"]),
        ("VIX", ["TVC:VIX", "VIX"]),
        ("DXY", ["TVC:DXY", "DXY"]),
        ("EWZ", ["AMEX:EWZ", "EWZ"]),
    ],
    "🪵 Commodities Cíclicas": [
        ("Minério", ["SGX:FEF1!", "IRON_ORE"]),
        ("Petróleo", ["NYMEX:CL1!", "CRUDE_OIL"]),
        ("Ouro", ["TVC:GOLD", "GOLD"]),
    ],
    "📈 ADRs Brasileiras": [
        ("VALE ADR", ["NYSE:VALE", "VALE_ADR"]),
        ("PETR ADR", ["NYSE:PBR", "PETR_ADR"]),
        ("ITUB ADR", ["NYSE:ITUB", "ITUB_ADR"]),
        ("BBAS ADR", ["OTC:BDORY", "BBAS_ADR"]),
        ("BBD ADR", ["NYSE:BBD", "BBD_ADR"]),
        ("B3 ADR", ["OTC:BOLSY", "B3_ADR"]),
    ],
    "🏦 Mercado à Vista": [
        ("VALE3", ["VALE3"]),
        ("PETR4", ["PETR4"]),
        ("ITUB4", ["ITUB4"]),
        ("BBAS3", ["BBAS3"]),
        ("BBDC4", ["BBDC4"]),
        ("B3SA3", ["B3SA3"]),
    ],
}

# v3.8.1 — "Ouro" incluído (safe haven, sobe com aversão a risco → ruim p/ WIN)
ATIVOS_INVERSOS = {"DXY", "VIX", "WDO", "USDBRL", "DI1 2027", "DI1 2029", "Ouro"}

# 12 janelas, ordem "mais antigo → mais recente" (55m → Agora)
JANELAS = [55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0]


# ==============================================================================
# CHAVES DOS INDICADORES COMPOSTOS
# ==============================================================================
ADRS_COMPOSTO_KEYS = [
    ["NYSE:VALE", "VALE_ADR"],
    ["NYSE:PBR", "PETR_ADR"],
    ["NYSE:ITUB", "ITUB_ADR"],
    ["OTC:BDORY", "BBAS_ADR"],
    ["NYSE:BBD", "BBD_ADR"],
    ["OTC:BOLSY", "B3_ADR"],
]

VIX_KEYS = ["TVC:VIX", "VIX"]
CRUDE_KEYS = ["NYMEX:CL1!", "CRUDE_OIL"]
IRON_KEYS = ["SGX:FEF1!", "IRON_ORE"]


def _label_janela(j: int) -> str:
    return "Agora" if j == 0 else f"{j}m"


# ==============================================================================
# LOADERS
# ==============================================================================
@st.cache_data(ttl=30)
def carregar_coleta_rom(minutos: int, _ver: str = _CACHE_VERSION) -> dict:
    caminho = COLETAS_DIR / f"Coleta_rom-{minutos}.json"
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return {}

    resultado: dict = {}
    coletas = dados.get("coletas")
    if not isinstance(coletas, list):
        return resultado

    for item in coletas:
        if not isinstance(item, dict):
            continue
        ativo = item.get("ativo")
        if not ativo:
            continue
        cp = (item.get("dados_reais") or {}).get("change_percent")
        if cp is None:
            continue
        try:
            resultado[ativo] = float(cp)
        except (TypeError, ValueError):
            continue

    return resultado


@st.cache_data(ttl=30)
def carregar_todas_coletas(_ver: str = _CACHE_VERSION) -> dict:
    return {j: carregar_coleta_rom(j, _ver) for j in JANELAS}


# ==============================================================================
# LOOKUP / MOMENTUM / COMPOSTOS
# ==============================================================================
def _buscar_valor(coleta: dict, chaves: list) -> Optional[float]:
    for chave in chaves:
        if chave in coleta:
            return coleta[chave]
    return None


def _calc_momentum(coletas: dict) -> dict:
    resultado: dict = {}
    for nome_cat, ativos in CATEGORIAS.items():
        resultado[nome_cat] = {}
        for nome_ativo, chaves in ativos:
            valores = {
                j: _buscar_valor(coletas.get(j, {}) or {}, chaves)
                for j in JANELAS
            }
            resultado[nome_cat][nome_ativo] = valores
    return resultado


def _media_janela(momentum_cat: dict, janela: int, inverso_por_ativo: set) -> Optional[float]:
    vals = []
    for nome, valores in momentum_cat.items():
        v = valores.get(janela)
        if v is None:
            continue
        vals.append(-v if nome in inverso_por_ativo else v)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def _momentum_categoria(momentum_cat: dict, inverso_por_ativo: set) -> dict:
    return {j: _media_janela(momentum_cat, j, inverso_por_ativo) for j in JANELAS}


def _calc_adrs_br(coleta: dict) -> Optional[float]:
    vals = []
    for chaves in ADRS_COMPOSTO_KEYS:
        v = _buscar_valor(coleta, chaves)
        if v is not None and abs(v) <= 15.0:
            vals.append(v)
    if not vals:
        return None
    return round(sum(vals), 4)


def _calc_mercado_externo(coleta: dict) -> Optional[float]:
    vix = _buscar_valor(coleta, VIX_KEYS)
    crude = _buscar_valor(coleta, CRUDE_KEYS)
    iron = _buscar_valor(coleta, IRON_KEYS)
    if vix is None or crude is None or iron is None:
        return None
    return round(-vix + crude + iron, 4)


def _calc_compostos(coletas: dict) -> dict:
    adrs_por_janela = {}
    externo_por_janela = {}
    for j in JANELAS:
        coleta = coletas.get(j, {}) or {}
        adrs_por_janela[j] = _calc_adrs_br(coleta)
        externo_por_janela[j] = _calc_mercado_externo(coleta)
    return {
        "ADRs BR": adrs_por_janela,
        "Merc. Externo": externo_por_janela,
    }


# ==============================================================================
# STATUS / COR
# ==============================================================================
def _status_momentum(valores: dict, inverso: bool = False) -> str:
    v5 = valores.get(5)
    v30 = valores.get(30)
    v55 = valores.get(55)
    if v5 is None and v30 is None and v55 is None:
        return "⚪ sem dados"

    v5 = v5 if v5 is not None else 0.0
    v30 = v30 if v30 is not None else 0.0
    v55 = v55 if v55 is not None else 0.0

    if max(abs(v5), abs(v30), abs(v55)) < 0.10:
        return "⚖️ sem direção"

    dir_curta = 1 if v5 > 0 else (-1 if v5 < 0 else 0)
    dir_longa = 1 if v55 > 0 else (-1 if v55 < 0 else 0)

    if dir_curta == dir_longa and dir_curta != 0:
        if dir_curta > 0:
            if abs(v5) > abs(v30) > abs(v55):
                base = "🚀 Acelerando alta"
            elif abs(v5) < abs(v55):
                base = "📈 Alta perdendo força"
            else:
                base = "📈 Alta consistente"
        else:
            if abs(v5) > abs(v30) > abs(v55):
                base = "📉 Acelerando baixa"
            elif abs(v5) < abs(v55):
                base = "⚠️ Baixa desacelerando"
            else:
                base = "📉 Baixa consistente"
    elif dir_curta != 0 and dir_longa != 0 and dir_curta != dir_longa:
        base = "🔄 Revertendo p/ alta" if dir_curta > 0 else "🔄 Revertendo p/ baixa"
    else:
        base = "⚖️ Misto"

    if inverso:
        mapa_inverso = {
            "🚀 Acelerando alta":     "⚠️ Acelerando alta — ruim p/ WIN",
            "📈 Alta consistente":    "⚠️ Alta consistente — ruim p/ WIN",
            "📈 Alta perdendo força": "🟡 Alta perdendo força — aliviando",
            "📉 Acelerando baixa":    "✅ Acelerando baixa — bom p/ WIN",
            "📉 Baixa consistente":   "✅ Baixa consistente — bom p/ WIN",
            "⚠️ Baixa desacelerando": "🟡 Baixa desacelerando — atenção",
            "🔄 Revertendo p/ alta":  "⚠️ Revertendo p/ alta — ruim p/ WIN",
            "🔄 Revertendo p/ baixa": "✅ Revertendo p/ baixa — bom p/ WIN",
            "⚖️ Misto":               "⚖️ Misto",
        }
        return mapa_inverso.get(base, base)

    return base


def _cor_status(texto: str, inverso: bool = False) -> str:
    if "✅" in texto or "bom p/ WIN" in texto:
        return "#22c55e"
    if "⚠️" in texto or "ruim p/ WIN" in texto:
        return "#ef4444"
    if "🟡" in texto or "aliviando" in texto or "atenção" in texto:
        return "#fbbf24"
    if "🚀" in texto:
        return "#22c55e"
    if "📉" in texto:
        return "#ef4444"
    if "📈" in texto:
        return "#86efac"
    return "#8b949e"


def _cor_valor(v, inverso: bool = False) -> str:
    if v is None:
        return "#8b949e"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "#8b949e"
    if abs(f) < 0.005:
        return "#e6edf3"
    favoravel = (f > 0) != inverso
    return "#22c55e" if favoravel else "#ef4444"


# ==============================================================================
# HISTOGRAMA SVG INLINE (com inversão)
# ==============================================================================
def _mini_histograma_svg(
    valores_dict: dict,
    largura: int = 220,
    altura: int = 44,
    inverter: bool = False,
) -> str:
    """
    SVG de 12 barras, uma por janela. Zero-line no centro.

    Se `inverter=True` (ativos inversos ao WIN), o sinal é negado ANTES de
    plotar — assim DXY +0.5% vira barra vermelha (ruim p/ WIN).
    O tooltip mostra o valor BRUTO + "(inverso)" para não enganar.

    Escala vertical: normalizada ao maior |valor| da própria série (após
    inversão). None → barra cinza minúscula.
    """
    vals_brutos = [valores_dict.get(j) for j in JANELAS]
    # valores plotados: brutos, ou negados se inverso
    vals_plot = [(-v if (v is not None and inverter) else v) for v in vals_brutos]

    n = len(vals_plot)
    abs_vals = [abs(v) for v in vals_plot if v is not None]
    max_abs = max(abs_vals) if abs_vals else 1.0
    if max_abs == 0:
        max_abs = 1.0

    gap = 2
    bar_w = (largura - (n - 1) * gap) / n
    meio_y = altura / 2
    altura_bar = (altura / 2) - 3

    parts = []
    for i, v_plot in enumerate(vals_plot):
        x = i * (bar_w + gap)
        label = _label_janela(JANELAS[i])
        v_bruto = vals_brutos[i]

        if v_bruto is None or v_plot is None:
            parts.append(
                f'<rect x="{x:.1f}" y="{meio_y - 1:.1f}" width="{bar_w:.1f}" '
                f'height="2" fill="#4b5563"/>'
                f'<title>{label}: —</title>'
            )
            continue

        h = max(1.0, (abs(v_plot) / max_abs) * altura_bar)
        cor = "#22c55e" if v_plot >= 0 else "#ef4444"
        y = (meio_y - h) if v_plot >= 0 else meio_y

        sufixo = " (inverso)" if inverter else ""
        tooltip = f"{label}: {v_bruto:+.3f}%{sufixo}"

        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'fill="{cor}" rx="1"/>'
            f'<title>{tooltip}</title>'
        )

    parts.append(
        f'<line x1="0" y1="{meio_y}" x2="{largura}" y2="{meio_y}" '
        f'stroke="#4b5563" stroke-width="0.5"/>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}" style="display:block;">'
        f'{"".join(parts)}</svg>'
    )


# ==============================================================================
# RENDER DE TABELA (HTML puro)
# ==============================================================================
COL_SPARK = "Evolução"
COL_DELTA = "Δ Agora"
COL_STATUS = "Status"

_TABLE_STYLE = (
    "width:100%;border-collapse:collapse;font-family:Arial,sans-serif;"
    "font-size:13px;color:#e6edf3;"
)
_TH_STYLE = "text-align:left;padding:6px 8px;color:#8b949e;font-weight:600;border-bottom:1px solid #30363d;"
_TD_STYLE = "padding:4px 8px;border-bottom:1px solid #1a1a1a;vertical-align:middle;"


def _render_tabela_histograma(
    linhas: list,
    status_txts: list,
    inv_flags: list,
    col_nome: str,
    largura_svg: int = 220,
):
    if not linhas:
        st.info("Sem dados.")
        return

    rows = []
    rows.append(
        f'<tr>'
        f'<th style="{_TH_STYLE}">{col_nome}</th>'
        f'<th style="{_TH_STYLE}">Evolução (55m → Agora)</th>'
        f'<th style="{_TH_STYLE};text-align:right;">{COL_DELTA}</th>'
        f'<th style="{_TH_STYLE}">{COL_STATUS}</th>'
        f'</tr>'
    )

    for i, linha in enumerate(linhas):
        inv = inv_flags[i] if i < len(inv_flags) else False
        nome = linha[col_nome]
        serie = linha[COL_SPARK]
        valores_dict = {j: serie[idx] for idx, j in enumerate(JANELAS)}
        delta = linha[COL_DELTA]
        status = linha[COL_STATUS]

        svg = _mini_histograma_svg(valores_dict, largura=largura_svg, altura=44, inverter=inv)

        cor_delta = _cor_valor(delta, inv)
        delta_txt = f"{delta:+.3f}%" if delta is not None else "—"
        # marca visualmente o Δ quando é inverso
        if inv and delta is not None:
            delta_txt += " ⟲"

        cor_status = _cor_status(status, inv)

        rows.append(
            f'<tr>'
            f'<td style="{_TD_STYLE};font-weight:700;">{nome}</td>'
            f'<td style="{_TD_STYLE}">{svg}</td>'
            f'<td style="{_TD_STYLE};text-align:right;color:{cor_delta};font-weight:700;">{delta_txt}</td>'
            f'<td style="{_TD_STYLE};color:{cor_status};font-weight:700;">{status}</td>'
            f'</tr>'
        )

    html = f'<table style="{_TABLE_STYLE}">{"".join(rows)}</table>'
    st.markdown(html, unsafe_allow_html=True)


# ==============================================================================
# MINI VELOCÍMETRO (intacto)
# ==============================================================================
def mini_velocimetro(
    valor,
    label: str,
    preco_fmt: str = "",
    inverter: bool = False,
    range_max: float = 10.0,
):
    if valor is None:
        real_exibicao = 0.0
        cor = "#8b949e"
        texto_valor = "—"
    else:
        try:
            real_exibicao = max(-range_max, min(range_max, float(valor)))
        except (TypeError, ValueError):
            real_exibicao = 0.0
        real_cor = -real_exibicao if inverter else real_exibicao
        if real_cor > 0.05:
            cor = "#00cc44"
        elif real_cor < -0.05:
            cor = "#ff4b4b"
        else:
            cor = "#ffa500"
        texto_valor = f"{float(valor):+.2f}%"

    angulo = (real_exibicao / range_max) * 90.0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        html, body {{ margin:0; padding:0; background:transparent;
            font-family: Arial, sans-serif; color: #e6edf3; overflow: hidden; }}
        .mini-wrap {{ display:flex; flex-direction:column; align-items:center; padding:2px 0; }}
        .mini-label {{ font-size:11px; color:#c9d1d9; margin-bottom:1px;
            text-align:center; font-weight:700; white-space:nowrap; }}
        .mini-gauge {{ position:relative; width:120px; height:62px; }}
        .mini-arc {{ position:absolute; left:5px; top:3px; width:110px; height:55px;
            border-radius:110px 110px 0 0;
            background: conic-gradient(from 270deg at 50% 100%,
                #ff2020 0deg 30deg, #b02020 30deg 60deg, #602020 60deg 90deg,
                #206020 90deg 120deg, #00a030 120deg 150deg, #00cc44 150deg 180deg);
            -webkit-mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
                    mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px); }}
        .mini-needle {{ position:absolute; left:50%; bottom:3px; width:8px; height:52px;
            margin-left:-4px; transform-origin:50% 100%;
            transition: transform 0.6s cubic-bezier(0.4,0,0.2,1); z-index:3; }}
        .mini-pivot {{ position:absolute; left:50%; bottom:0px; width:12px; height:12px;
            margin-left:-6px; border-radius:50%; background:{cor}; z-index:4; }}
        .mini-value {{ font-size:14px; font-weight:900; color:{cor};
            text-align:center; margin-top:4px; line-height:1.1; }}
        .mini-sub {{ font-size:10px; color:#8b949e; text-align:center;
            margin-top:2px; line-height:1.1; }}
    </style>
    </head>
    <body>
        <div class="mini-wrap">
            <div class="mini-label">{label}</div>
            <div class="mini-gauge">
                <div class="mini-arc"></div>
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 52">
                    <path d="M 4 0 L 5.5 46 L 2.5 46 Z" fill="#ffffff"/>
                </svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-sub">{preco_fmt}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=145, scrolling=False)


# ==============================================================================
# CABEÇALHO
# ==============================================================================
st.markdown("<h2 style='color:#00d4ff;'>🔬 Análise de Tendência — Momentum Multi-Janela</h2>", unsafe_allow_html=True)
st.caption(
    "Histograma das 12 coletas rolantes (55m → 50m → … → Agora) · "
    "🟢 verde = favorável p/ WIN · 🔴 vermelho = desfavorável · "
    "ativos com ⟲ têm o sinal invertido (DXY/VIX/WDO/DI/Ouro) · "
    "hover mostra o valor bruto · atualiza a cada 60s"
)


# ==============================================================================
# FRAGMENT — DASHBOARD
# ==============================================================================
@st.fragment(run_every=60)
def _render_dashboard():
    coletas = carregar_todas_coletas()
    momentum = _calc_momentum(coletas)

    st.caption(f"🕒 Última leitura local: {datetime.now().strftime('%H:%M:%S')}")

    # 1) Termômetro por categoria
    st.markdown("### 🌡️ Termômetro de Momentum por Categoria")
    st.caption("Média das variações no 'Agora' (com sinal ajustado pros inversos) — impacto agregado no WIN")

    cols_cat = st.columns(5)
    for idx, nome_cat in enumerate(CATEGORIAS.keys()):
        media_agora = _media_janela(momentum[nome_cat], 0, ATIVOS_INVERSOS)
        nome_curto = nome_cat.split(" ", 1)[-1][:18]
        with cols_cat[idx]:
            mini_velocimetro(media_agora, nome_curto, "" if media_agora is None else f"{media_agora:+.3f}%")

    # 2) Tabela de evolução das categorias
    st.markdown("##### 📋 Evolução das Categorias (55m → Agora)")
    st.caption("Histograma = média das 12 coletas por categoria · Δ Agora = valor atual · cores = impacto no WIN")

    linhas_cat, status_txts_cat, inv_flags_cat = [], [], []
    for nome_cat in CATEGORIAS.keys():
        medias = _momentum_categoria(momentum[nome_cat], ATIVOS_INVERSOS)
        status_txt = _status_momentum(medias, inverso=False)
        nome_curto = nome_cat.split(" ", 1)[-1]
        linhas_cat.append({
            "Categoria": nome_curto,
            COL_SPARK: [medias.get(j) for j in JANELAS],
            COL_DELTA: medias.get(0),
            COL_STATUS: status_txt,
        })
        status_txts_cat.append(status_txt)
        inv_flags_cat.append(False)  # categorias já têm sinal ajustado na média

    _render_tabela_histograma(linhas_cat, status_txts_cat, inv_flags_cat, "Categoria")

    st.markdown("---")

    # 3) Abas por categoria
    st.markdown("### 📊 Detalhe por Categoria — evolução visual por ativo")
    st.caption("Histograma das 12 coletas por ativo · Δ Agora = último valor · ⟲ = ativo inverso (sinal plotado invertido)")

    abas = st.tabs(list(CATEGORIAS.keys()))

    for idx_aba, nome_cat in enumerate(CATEGORIAS.keys()):
        with abas[idx_aba]:
            linhas, status_txts, inv_flags = [], [], []

            for nome_ativo, valores in momentum[nome_cat].items():
                inverso = nome_ativo in ATIVOS_INVERSOS
                texto_status = _status_momentum(valores, inverso=inverso)
                linhas.append({
                    "Ativo": nome_ativo,
                    COL_SPARK: [valores.get(j) for j in JANELAS],
                    COL_DELTA: valores.get(0),
                    COL_STATUS: texto_status,
                })
                status_txts.append(texto_status)
                inv_flags.append(inverso)

            if not linhas:
                st.info("Sem dados dessa categoria nas coletas atuais.")
                continue

            _render_tabela_histograma(linhas, status_txts, inv_flags, "Ativo")

    st.markdown("---")

    # 4) Indicadores compostos
    st.markdown("### 🎯 Indicadores Compostos (Calculadora Fase 4)")
    st.caption(
        "ADRs Brasileiras = soma das 6 ADRs · Mercado Externo = −VIX + Petróleo + Minério · "
        "mesmas fórmulas da `Calculadora.py`"
    )

    composto = _calc_compostos(coletas)

    adrs_agora = composto["ADRs BR"].get(0)
    ext_agora = composto["Merc. Externo"].get(0)

    g1, g2 = st.columns(2)
    with g1:
        mini_velocimetro(adrs_agora, "🇧🇷 ADRs Brasileiras",
                         "" if adrs_agora is None else f"{adrs_agora:+.2f}%",
                         range_max=30.0)
    with g2:
        mini_velocimetro(ext_agora, "🌍 Mercado Externo",
                         "" if ext_agora is None else f"{ext_agora:+.2f}%",
                         range_max=15.0)

    st.markdown("##### 📋 Evolução dos Compostos (55m → Agora)")

    linhas_comp, status_txts_comp, inv_flags_comp = [], [], []
    for nome_comp in ("ADRs BR", "Merc. Externo"):
        valores = composto[nome_comp]
        status_txt = _status_momentum(valores, inverso=False)
        linhas_comp.append({
            "Composto": nome_comp,
            COL_SPARK: [valores.get(j) for j in JANELAS],
            COL_DELTA: valores.get(0),
            COL_STATUS: status_txt,
        })
        status_txts_comp.append(status_txt)
        inv_flags_comp.append(False)  # compostos já embutem o sinal correto na fórmula

    _render_tabela_histograma(linhas_comp, status_txts_comp, inv_flags_comp, "Composto")


def render_body():
    _render_dashboard()


render_body()