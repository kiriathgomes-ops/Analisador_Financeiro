# -*- coding: utf-8 -*-
"""
Módulo: v2/pages/3_page_cockpit_pregao.py
Versão: 3.1 — Cockpit operacional WIN com fragments + drivers coloridos
Objetivo: Painel de decisão ao vivo (SMC + pivots + drivers globais) durante o pregão.
"""

import json
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Cockpit Operacional WIN - Pregão ao Vivo",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização CSS personalizada para alta visibilidade no pregão
st.markdown("""
<style>
    .buy-signal { background-color: #0e3a2f; border: 2px solid #00e676; border-radius: 10px; padding: 15px; text-align: center; }
    .sell-signal { background-color: #3a0e14; border: 2px solid #ff5252; border-radius: 10px; padding: 15px; text-align: center; }
    .neutral-signal { background-color: #2a2e39; border: 2px solid #ffb74d; border-radius: 10px; padding: 15px; text-align: center; }
    .zone-box { background-color: #131722; border: 1px solid #363c4e; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[2] if len(ARQUIVO_ATUAL.parents) >= 3 else ARQUIVO_ATUAL.parent


def _carregar_json_absoluto(nome_arquivo):
    """Procura os JSONs varrendo a árvore a partir da raiz absoluta do projeto."""
    locais_busca = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        RAIZ_PROJETO / "json" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo,
    ]

    for caminho in locais_busca:
        if caminho.is_file():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f), str(caminho)
            except Exception:
                pass
    return {}, None


@st.cache_data(ttl=5)
def _carregar_tudo() -> dict:
    """Carrega os 5 JSONs num único ponto (consistência entre fragments)."""
    dados_v2, path_v2 = _carregar_json_absoluto("Decisao_V2.json")
    dados_smc, path_smc = _carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
    dados_unificados, path_unificados = _carregar_json_absoluto("DadosAtivosUnificados.json")
    dados_mt5, path_mt5 = _carregar_json_absoluto("Dados_MT5_v2_2.json")
    dados_val, path_val = _carregar_json_absoluto("Dados_Validados.json")
    return {
        "v2": dados_v2, "v2_path": path_v2,
        "smc": dados_smc, "smc_path": path_smc,
        "unif": dados_unificados, "unif_path": path_unificados,
        "mt5": dados_mt5, "mt5_path": path_mt5,
        "val": dados_val, "val_path": path_val,
    }


# ==============================================================================
# EXTRAÇÃO DE VARIÁVEIS DOS DRIVERS GLOBAIS (PURO — não usa globais)
# ==============================================================================
def _extrair_valor_objeto(obj):
    """Extrai valor numérico de variação de diferentes tipos de objetos/dicionários."""
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        for k in ["var", "variacao", "change", "pct", "pct_change", "v", "value", "variacao_pct"]:
            if k in obj and isinstance(obj[k], (int, float)):
                return float(obj[k])
    return None


def _buscar_var_universal(fontes: list, chaves_busca: list) -> float:
    """Procura uma variação de ativo em todas as estruturas conhecidas dos JSONs."""
    for fonte in fontes:
        if not fonte:
            continue

        # 1. Lista de dicionários
        if isinstance(fonte, list):
            for item in fonte:
                if isinstance(item, dict):
                    nome = str(
                        item.get("ativo") or item.get("symbol") or item.get("nome") or item.get("ticker") or ""
                    ).upper()
                    if any(k.upper() in nome for k in chaves_busca):
                        res = _extrair_valor_objeto(item)
                        if res is not None:
                            return res

        # 2. Dicionário
        elif isinstance(fonte, dict):
            for k_fonte, v_fonte in fonte.items():
                if any(k.upper() in str(k_fonte).upper() for k in chaves_busca):
                    res = _extrair_valor_objeto(v_fonte)
                    if res is not None:
                        return res

            sub_dict = fonte.get("ativos") or fonte.get("cotacoes") or fonte.get("dados") or {}
            if isinstance(sub_dict, dict):
                for k_fonte, v_fonte in sub_dict.items():
                    if any(k.upper() in str(k_fonte).upper() for k in chaves_busca):
                        res = _extrair_valor_objeto(v_fonte)
                        if res is not None:
                            return res

    return 0.0


# ==============================================================================
# SIDEBAR DE STATUS E DIAGNÓSTICO (estática)
# ==============================================================================
def _render_sidebar():
    with st.sidebar:
        st.header("🔍 Status dos Dados")
        dados = _carregar_tudo()

        st.write("Decisao_V2.json:", "🟢 CARREGADO" if dados["v2_path"] else "🔴 AUSENTE")
        st.write("SMC Rules:", "🟢 CARREGADO" if dados["smc_path"] else "🔴 AUSENTE")
        st.write(
            "Dados Unificados:",
            f"🟢 CARREGADO (`{os.path.basename(dados['unif_path'])}`)" if dados["unif_path"] else "🔴 AUSENTE",
        )
        st.write(
            "Dados MT5:",
            f"🟢 CARREGADO (`{os.path.basename(dados['mt5_path'])}`)" if dados["mt5_path"] else "🔴 AUSENTE",
        )

        st.markdown("---")
        st.caption(f"📁 Pasta Raiz: `{RAIZ_PROJETO}`")


# ==============================================================================
# FRAGMENT 1 — HEADER + BANNER + KPIs + DRIVERS (refresh 60s)
# ==============================================================================
@st.fragment(run_every=60)
def _render_bloco_mercado():
    dados = _carregar_tudo()

    # ---- Parse V2 ----
    obj_decisao = dados["v2"].get("decisao", {})
    obj_meta = obj_decisao.get("metadados", {})

    vies_final = str(obj_decisao.get("vies_final", "NEUTRO")).upper()
    confianca = float(obj_decisao.get("confianca", 50))
    entrada_oficial = obj_decisao.get("entrada", 0)
    stop_official = obj_decisao.get("stop_loss", 0)
    alvo_1 = obj_decisao.get("alvo_1", 0)
    alvo_2 = obj_decisao.get("alvo_2", 0)

    gap_pts = float(obj_meta.get("gap_pts", 0.0))
    riscos = obj_decisao.get("riscos", [])
    trava_noticias = len(riscos) > 0

    # ---- Drivers globais ----
    fontes_drivers = [dados["unif"], dados["val"], dados["mt5"]]
    val_adrs = _buscar_var_universal(fontes_drivers, ["ADRS_BASKET", "ADR_BASKET", "ADRS", "cesta_adrs", "VALE3", "PETR4"])
    ewz_var = _buscar_var_universal(fontes_drivers, ["EWZ", "EWZ_ETF", "iShares MSCI Brazil"])
    sp_fut = _buscar_var_universal(fontes_drivers, ["SP500_FUT", "US500", "SP500", "S&P", "INX", "US500.F"])
    val_minerio = _buscar_var_universal(fontes_drivers, ["MINERIO", "IRON_ORE", "minerio_sgx", "TSI"])
    val_petroleo = _buscar_var_universal(fontes_drivers, ["PETROLEO", "BRENT", "WTI", "OIL", "CL1!"])
    di_inc = _buscar_var_universal(fontes_drivers, ["DI_INCLINACAO", "DI_SPREAD", "DI1F27", "DI1"])

    # ---- HEADER ----
    st.title("⚡ COCKPIT OPERACIONAL WIN - PREGÃO AO VIVO")

    col_banner, col_meter = st.columns([2, 1])

    with col_banner:
        if "ALTA" in vies_final or "COMPRA" in vies_final:
            st.markdown(f"""
            <div class="buy-signal">
                <h1 style="color: #00e676; margin:0;">🚀 VIÉS INSTITUCIONAL: COMPRA ({vies_final})</h1>
                <p style="font-size: 16px; margin:0; color: #a3e635;">Entrada Sugerida: <b>{entrada_oficial:,.0f}</b> | Stop Loss: <b>{stop_official:,.0f}</b></p>
                <p style="font-size: 14px; margin:0; color: #a3e635;">Alvo 1: <b>{alvo_1:,.0f}</b> | Alvo 2: <b>{alvo_2:,.0f}</b></p>
            </div>
            """, unsafe_allow_html=True)
        elif "BAIXA" in vies_final or "VENDA" in vies_final:
            st.markdown(f"""
            <div class="sell-signal">
                <h1 style="color: #ff5252; margin:0;">🔻 VIÉS INSTITUCIONAL: VENDA ({vies_final})</h1>
                <p style="font-size: 16px; margin:0; color: #fca5a5;">Entrada Sugerida: <b>{entrada_oficial:,.0f}</b> | Stop Loss: <b>{stop_official:,.0f}</b></p>
                <p style="font-size: 14px; margin:0; color: #fca5a5;">Alvo 1: <b>{alvo_1:,.0f}</b> | Alvo 2: <b>{alvo_2:,.0f}</b></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="neutral-signal">
                <h1 style="color: #ffb74d; margin:0;">⚠️ VIÉS NEUTRO / AGUARDAR</h1>
                <p style="font-size: 16px; margin:0; color: #fde047;">Mercado sem confluência suficiente para tomada de posição.</p>
            </div>
            """, unsafe_allow_html=True)

    with col_meter:
        st.markdown("### 📊 Confluência SMC")
        st.progress(min(max(int(confianca), 0), 100) / 100)
        st.markdown(f"**Confiança Institucional:** `{confianca:.0f}%`")
        if trava_noticias:
            st.error(f"🚫 **ALERTAS DE RISCO:** {', '.join(riscos)}")
        else:
            st.success("🟢 **OPERACIONAL LIBERADO**")

    st.markdown("---")

    # ---- PAINEL 1: KPIs ----
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("🎯 GAP Projeção Abertura", f"{gap_pts:+} pts")
    with k2:
        st.metric("📈 Curva DI (Inclinacao)", f"{di_inc:+.2f} bps")
    with k3:
        st.metric("🇺🇸 S&P 500 Futuro", f"{sp_fut:+.2f}%")
    with k4:
        st.metric("🇧🇷 EWZ (Gringo NY)", f"{ewz_var:+.2f}%")

    st.markdown("---")

    # ---- PAINEL 3: Drivers globais (bar chart colorido por sinal) ----
    st.markdown("## 📊 Impacto dos Drivers Globais")

    drivers_labels = ["ADRs Brasil", "EWZ ETF", "S&P 500", "Minério", "Petróleo"]
    drivers_valores = [val_adrs, ewz_var, sp_fut, val_minerio, val_petroleo]

    # Cor por barra: verde se >= 0, vermelho se < 0
    cores = ["#22c55e" if v >= 0 else "#ef4444" for v in drivers_valores]

    fig = go.Figure(data=[
        go.Bar(
            x=drivers_labels,
            y=drivers_valores,
            marker_color=cores,
            text=[f"{v:+.2f}%" for v in drivers_valores],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Variação: %{y:+.2f}%<extra></extra>",
        )
    ])
    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Driver",
        yaxis_title="Variação (%)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ==============================================================================
# FRAGMENT 2 — SMC + PIVOTS (refresh 300s)
# ==============================================================================
@st.fragment(run_every=300)
def _render_bloco_smc():
    dados = _carregar_tudo()

    obj_decisao = dados["v2"].get("decisao", {})
    obj_meta = obj_decisao.get("metadados", {})

    pivots = obj_meta.get("pivots", {})
    pp = pivots.get("pp", 0)
    r1 = pivots.get("r1", 0)
    r2 = pivots.get("r2", 0)
    s1 = pivots.get("s1", 0)
    s2 = pivots.get("s2", 0)

    smc_data = obj_meta.get("smc", {})
    order_blocks = smc_data.get("order_blocks") or dados["smc"].get("order_blocks") or []
    fvgs = smc_data.get("fvgs") or dados["smc"].get("fair_value_gaps") or []

    obs_compra = [ob for ob in order_blocks if ob.get("tipo") in ["COMPRA", "BULLISH"]]
    obs_venda = [ob for ob in order_blocks if ob.get("tipo") in ["VENDA", "BEARISH"]]

    st.markdown("## 🎯 Zonas de Confluência SMC & Níveis Técnicos")

    col_ob, col_fvg, col_pivots = st.columns(3)

    with col_ob:
        st.markdown("### 🟢 Order Blocks (Regiões de Absorção)")
        if obs_compra:
            for ob in obs_compra:
                st.markdown(f"""
                <div class="zone-box" style="border-left: 5px solid #00e676;">
                    <b style="color:#00e676;">OB COMPRA</b><br>
                    📍 <b>Gatilho Preço:</b> {ob.get('preco', 0):,.0f}<br>
                    📏 <b>Faixa (Low-High):</b> {ob.get('low', 0):,.0f} - {ob.get('high', 0):,.0f}
                </div>
                """, unsafe_allow_html=True)
        elif obs_venda:
            for ob in obs_venda:
                st.markdown(f"""
                <div class="zone-box" style="border-left: 5px solid #ff5252;">
                    <b style="color:#ff5252;">OB VENDA</b><br>
                    📍 <b>Gatilho Preço:</b> {ob.get('preco', 0):,.0f}<br>
                    📏 <b>Faixa (Low-High):</b> {ob.get('low', 0):,.0f} - {ob.get('high', 0):,.0f}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhum Order Block ativo mapeado.")

    with col_fvg:
        st.markdown("### 📦 Fair Value Gaps (Ineficiências)")
        if fvgs:
            for fvg in fvgs[:3]:
                st.markdown(f"""
                <div class="zone-box" style="border-left: 5px solid #2962ff;">
                    <b style="color:#2962ff;">FVG {fvg.get('tipo', 'COMPRA')}</b><br>
                    📍 <b>Zona:</b> {fvg.get('inferior', 0):,.0f} - {fvg.get('superior', 0):,.0f}<br>
                    Status: <b>{'Preenchido' if fvg.get('preenchido') else 'Aberto (Líquido)'}</b>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sem FVGs abertos no momento.")

    with col_pivots:
        st.markdown("### 📌 Níveis de Pivô Matemáticos")
        st.markdown(f"• **R2:** `{r2:,.0f}`")
        st.markdown(f"• **R1:** `{r1:,.0f}`")
        st.markdown(f"• **Pivot Point (PP):** `{pp:,.0f}`")
        st.markdown(f"• **S1:** `{s1:,.0f}`")
        st.markdown(f"• **S2:** `{s2:,.0f}`")

    st.markdown("---")


# ==============================================================================
# CORPO
# ==============================================================================
def render_body():
    _render_sidebar()
    _render_bloco_mercado()
    _render_bloco_smc()


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
render_body()