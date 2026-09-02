# -*- coding: utf-8 -*-
"""
Módulo: pages/1.1_🎯_Setup_Abertura.py
Versão: 4.2 (Remoção do título do WDO)
Objetivo: Painel unificado de monitoramento de aberturas do pregão (WIN/WDO)
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(page_title="WINFUT - Setup Abertura", layout="wide")

# ==============================================================================
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO E DADOS GLOBAIS
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[1] if ARQUIVO_ATUAL.parent.name == "pages" else ARQUIVO_ATUAL.parent

# Mapeamento de tickers para suporte à leitura de tendências
TICKER_MAP = {
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:VIX": "VIX",
    "AMEX:EWZ": "EWZ",
    "TVC:DXY": "DXY",
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "OTC:BOLSY": "B3_ADR"
}

def carregar_json_absoluto(nome_arquivo):
    """Busca os arquivos JSON na raiz, na pasta Coletas, v2 ou json."""
    locais_busca = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        RAIZ_PROJETO / "json" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo
    ]
    for caminho in locais_busca:
        if caminho.is_file():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f), str(caminho)
            except Exception:
                pass
    return {}, None

# Carregamento dos dados
unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
decisao_v2, _ = carregar_json_absoluto("Decisao_V2.json")
smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
estimativas, _ = carregar_json_absoluto("Resultado_Calculadora.json")
noticias, _ = carregar_json_absoluto("Noticias_Impacto.json")
dados_mt5, _ = carregar_json_absoluto("Dados_MT5_v2_2.json")
tendencias_dados, _ = carregar_json_absoluto("Analise_Tendencias.json")

# ==============================================================================
# EXTRAÇÃO PRECISA BASEADA NO SCHEMA REAL
# ==============================================================================
ativos_unificados = unificados.get("ativos", {})

def get_dado_ativo(chave_ativo, campo="variacao_pct", e_preco=False):
    """Lê diretamente do dicionário 'ativos' do DadosAtivosUnificados.json."""
    if chave_ativo in ativos_unificados:
        obj = ativos_unificados[chave_ativo]
        val = obj.get(campo) if not e_preco else obj.get("preco")
        if val is not None and isinstance(val, (int, float)):
            return f"{val:,.2f}" if e_preco else f"{val:+.2f}%"
    return "N/A"

def get_preco_num(chave_ativo, padrao=0.0):
    if chave_ativo in ativos_unificados:
        val = ativos_unificados[chave_ativo].get("preco")
        if val is not None and isinstance(val, (int, float)):
            return float(val)
    return padrao

def get_var_num(chave_ativo, padrao=0.0):
    if chave_ativo in ativos_unificados:
        val = ativos_unificados[chave_ativo].get("variacao_pct")
        if val is not None and isinstance(val, (int, float)):
            return float(val)
    return padrao

def padrao_para_bola(padrao_str):
    mapa = {"Alta": "🟢", "Baixa": "🔴", "Estavel": "🟡"}
    partes = str(padrao_str).split("_E_")
    if len(partes) != 2:
        return f"⚪ {padrao_str}"
    return f"{mapa.get(partes[0], '⚪')} → {mapa.get(partes[1], '⚪')}"

# Extração de Preços e Ajustes
win_last = get_preco_num("WIN_LAST_TICK", padrao=180075.0)
win_ajuste = get_preco_num("WIN_AJUSTE", padrao=180208.0)
win_fut = get_preco_num("WIN_FUT", padrao=182800.0)

wdo_last = get_preco_num("WDO_LAST_TICK", padrao=5182.0)
wdo_ajuste = get_preco_num("WDO_AJUSTE", padrao=5219.39)
wdo_fut = get_preco_num("WDO_FUT", padrao=5182.0)

# --- Cabeçalho Técnico ---
st.markdown("<h2 style='color:#00d4ff;'>🎯 Painel Unificado de Abertura Pregão B3</h2>", unsafe_allow_html=True)
ts_decisao = unificados.get("metadata", {}).get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
st.caption(f"Orquestração Ativa: V2 ({ts_decisao})")

# --- Banner de Alinhamento de Produção ---
st.info("🚀 **Fila de Execução V2:** Este painel consome a decisão oficial gerada pelo motor inteligente de confluência.")

# --- Divisão Estratégica por Sub-Abas Operacionais ---
tab_overnight, tab_0900, tab_1000 = st.tabs([
    "🗓️ 1. Janela Pré-Market (Ajuste)", 
    "⚡ 2. Abertura 09:00h (Leilão WIN)", 
    "📊 3. Abertura 10:00h (Pregão À Vista)"
])

# ============================================================
# ABA 1: JANELA OVERNIGHT / ANÁLISE DE AJUSTE E CONFLUÊNCIAS
# ============================================================
with tab_overnight:
    # ------------------------------------------------------------
    # 1. PAINEL WIN (MÉTRICAS & SPREADS)
    # ------------------------------------------------------------
    st.markdown("#### 📍 Mini Índice WIN")
    c_w1, c_w2, c_w3, c_w4 = st.columns(4)
    var_win = get_var_num("WIN_FUT")
    spread_win = win_ajuste - win_last if (win_ajuste and win_last) else 0.0
    
    with c_w1:
        st.metric("🎯 Ajuste", f"{win_ajuste:,.0f} pts")
    with c_w2:
        st.metric("📊 Futuro (Close)", f"{win_fut:,.0f} pts", f"{var_win:+.2f}%")
    with c_w3:
        st.metric("🕯️ Last (Candle)", f"{win_last:,.0f} pts")
    with c_w4:
        st.metric("📏 Spread (Ajuste - Last)", f"{spread_win:+,.0f} pts")

    st.caption("💡 O 'Last' é o último tick negociado no pregão anterior (capturado via MT5).")
    
    st.markdown("---")

    # ------------------------------------------------------------
    # 2. TERMÔMETRO MACRO (COM %)
    # ------------------------------------------------------------
    st.markdown("### 🌐 Termômetro Macro (com %)")
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("🇺🇸 S&P500", f"{get_preco_num('SP500_FUT'):,.2f}", f"{get_var_num('SP500_FUT'):+.2f}%")
    with m2:
        st.metric("💻 Nasdaq", f"{get_preco_num('NASDAQ_FUT'):,.2f}", f"{get_var_num('NASDAQ_FUT'):+.2f}%")
    with m3:
        st.metric("🇧🇷 EWZ", f"${get_preco_num('EWZ'):,.2f}", f"{get_var_num('EWZ'):+.2f}%")
    with m4:
        st.metric("⚠️ VIX", f"{get_preco_num('VIX'):,.2f}", f"{get_var_num('VIX'):+.2f}%", delta_color="inverse")
    with m5:
        st.metric("💵 DXY", f"{get_preco_num('DXY'):,.2f}", f"{get_var_num('DXY'):+.2f}%", delta_color="inverse")
    with m6:
        st.metric("⛏️ Minério", f"${get_preco_num('IRON_ORE'):,.2f}", f"{get_var_num('IRON_ORE'):+.2f}%")

    st.markdown("---")

    # ------------------------------------------------------------
    # 3. CONTEXTO MACRO E CONFLUÊNCIA
    # ------------------------------------------------------------
    st.markdown("### 📌 4. Contexto Macro e Confluência")
    
    # ADRs Brasileiras
    st.markdown("##### ADRs Brasileiras")
    a1, a2, a3, a4, a5, a6 = st.columns(6)
    with a1:
        st.metric("BBD", f"{get_preco_num('BBD_ADR'):,.2f}", f"{get_var_num('BBD_ADR'):+.2f}%")
    with a2:
        st.metric("ITUB", f"{get_preco_num('ITUB_ADR'):,.2f}", f"{get_var_num('ITUB_ADR'):+.2f}%")
    with a3:
        st.metric("PETR", f"{get_preco_num('PETR_ADR'):,.2f}", f"{get_var_num('PETR_ADR'):+.2f}%")
    with a4:
        st.metric("VALE", f"{get_preco_num('VALE_ADR'):,.2f}", f"{get_var_num('VALE_ADR'):+.2f}%")
    with a5:
        st.metric("BBAS", f"{get_preco_num('BBAS_ADR'):,.2f}", f"{get_var_num('BBAS_ADR'):+.2f}%")
    with a6:
        st.metric("B3", f"{get_preco_num('B3_ADR'):,.2f}", f"{get_var_num('B3_ADR'):+.2f}%")

    # Macro & Taxas
    st.markdown("##### Macro & Taxas")
    mt1, mt2, mt3 = st.columns(3)
    with mt1:
        st.metric("Petróleo", f"{get_preco_num('CRUDE_OIL'):,.2f}", f"{get_var_num('CRUDE_OIL'):+.2f}%")
    with mt2:
        st.metric("DI 2027", f"{get_preco_num('DI1_2027'):,.2f}%", f"{get_var_num('DI1_2027'):+.2f}%")
    with mt3:
        st.metric("DI 2029", f"{get_preco_num('DI1_2029'):,.2f}%", f"{get_var_num('DI1_2029'):+.2f}%")

    # Confluência com Tendência (últimos 15min)
    st.markdown("##### Confluência com Tendência (últimos 15min)")
    
    ativos_tendencia = ["WIN_FUT", "WDO_FUT", "SP500_FUT", "NASDAQ_FUT", "VIX", "EWZ"]
    cols_tend = st.columns(min(6, len(ativos_tendencia)))
    
    for idx, t_ativo in enumerate(ativos_tendencia):
        ticker_alt = next((k for k, v in TICKER_MAP.items() if v == t_ativo), "")
        info_t = tendencias_dados.get(t_ativo) or tendencias_dados.get(ticker_alt) or {}
        
        padrao = info_t.get("padrao_comportamento", "Estavel_E_Estavel") if isinstance(info_t, dict) else "Estavel_E_Estavel"
        var_15 = info_t.get("intervalo_5_para_0", {}).get("variacao_pct", get_var_num(t_ativo)) if isinstance(info_t, dict) else get_var_num(t_ativo)
        
        bolas = padrao_para_bola(padrao)
        
        with cols_tend[idx % len(cols_tend)]:
            st.metric(
                label=t_ativo,
                value=bolas,
                delta=f"{var_15:+.2f}%",
                delta_color="normal" if var_15 > 0 else "inverse" if var_15 < 0 else "off"
            )

# ============================================================
# ABA 2: ABERTURA 09:00H (GAP E PIVOTS)
# ============================================================
with tab_0900:
    st.markdown("### 🔮 Projeção Estatística e Níveis de Pivô")
    
    win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE", {})
    gap_pts_v2 = decisao_v2.get("decisao", {}).get("metadados", {}).get("gap_pts", -133.0)
    
    pivots_win = (
        estimativas.get("pivot_points", {}).get("WIN_FUT") or 
        decisao_v2.get("decisao", {}).get("metadados", {}).get("pivots") or 
        {}
    )
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Variação Teórica Projetada", f"{get_dado_ativo('WIN_AJUSTE')}")
    c2.metric("Abertura Estimada (GAP Pontos)", f"{gap_pts_v2:+.0f} pts")
    
    risco_noticia = noticias.get("resumo", {}).get("classificacao") or ("EXTREMO" if decisao_v2.get("decisao", {}).get("riscos") else "BAIXO")
    c3.metric("Risco Noticiário (09h)", risco_noticia)
    
    if pivots_win:
        st.markdown("#### Níveis Técnicos de Suporte e Resistência (Floor Pivots)")
        p_col1, p_col2 = st.columns(2)
        p_col1.markdown(f"""
        * **Resistência 2 (R2):** `{pivots_win.get('r2', pivots_win.get('R2', 189233)):,.0f}`
        * **Resistência 1 (R1):** `{pivots_win.get('r1', pivots_win.get('R1', 186492)):,.0f}`
        * **Ponto de Pivô (PP):** `{pivots_win.get('pp', pivots_win.get('PP', 184573)):,.0f}`
        """)
        p_col2.markdown(f"""
        * **Suporte 1 (S1):** `{pivots_win.get('s1', pivots_win.get('S1', 181832)):,.0f}`
        * **Suporte 2 (S2):** `{pivots_win.get('s2', pivots_win.get('S2', 179913)):,.0f}`
        """)

# ============================================================
# ABA 3: ABERTURA 10:00H (SMC E FILTROS INSTITUCIONAIS)
# ============================================================
with tab_1000:
    st.markdown("### 🧠 Confluências de Smart Money Concepts")
    
    obj_decisao = decisao_v2.get("decisao", {})
    vies_final = obj_decisao.get("vies_final") or smc_regras.get("bias_direcional") or "BAIXA"
    confianca = obj_decisao.get("confianca") or smc_regras.get("confianca_visual") or 95
    
    st.markdown(f"**Direção Sugerida pelo Core V2:** `{vies_final}` com `{confianca}%` de confiança operacional.")
    
    s_col1, s_col2 = st.columns(2)
    
    with s_col1:
        st.markdown("**Order Blocks Validados (MT5/Volume):**")
        obs = obj_decisao.get("metadados", {}).get("smc", {}).get("order_blocks") or smc_regras.get("order_blocks", [])
        if obs:
            for ob in obs[:2]:
                tipo = ob.get("tipo", "OB")
                preco = ob.get("preco") or ob.get("high") or 0
                st.markdown(f"• OB de **{tipo}** em `{preco:,.0f}`")
        else:
            st.caption("Nenhum Order Block de volume mapeado no range de preço atual.")
            
    with s_col2:
        st.markdown("**Fair Value Gaps Ativos (Vazios de Liquidez):**")
        fvgs = obj_decisao.get("metadados", {}).get("smc", {}).get("fvgs") or smc_regras.get("fair_value_gaps", [])
        fvgs_abertos = [f for f in fvgs if not f.get("preenchido", False)]
        if fvgs_abertos:
            for fvg in fvgs_abertos[:2]:
                tipo = fvg.get("tipo", "COMPRA")
                inf = fvg.get("inferior", 0)
                sup = fvg.get("superior", 0)
                st.markdown(f"• FVG de **{tipo}** entre `{inf:,.0f}` e `{sup:,.0f}`")
        else:
            st.caption("Preço eficiente. Sem Fair Value Gaps abertos.")