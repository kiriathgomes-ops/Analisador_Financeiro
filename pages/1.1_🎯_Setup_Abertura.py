# -*- coding: utf-8 -*-
"""
Módulo: pages/1.1_🎯_Setup_Abertura.py
Versão: 2.1 (Migrado para Produção V2)
Objetivo: Painel unificado de monitoramento de aberturas do pregão (WIN/WDO)
"""

import streamlit as st
import json
import plotly.graph_objects as go
from datetime import datetime

# Importações de caminhos padronizados do seu arquivo central config.py
from config import (
    FILE_UNIFICADO, 
    FILE_DECISAO_V2, 
    FILE_SMC_REGRAS, 
    FILE_ESTIMATIVA_ABERTURA,
    FILE_NOTICIAS_IMPACTO
)

def carregar_json(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# --- Inicialização e Carga de Dados Ativos V2 ---
unificados = carregar_json(FILE_UNIFICADO)
decisao_v2 = carregar_json(FILE_DECISAO_V2)
smc_regras = carregar_json(FILE_SMC_REGRAS)
estimativas = carregar_json(FILE_ESTIMATIVA_ABERTURA)
noticias = carregar_json(FILE_NOTICIAS_IMPACTO)

ativos = unificados.get("ativos", {})
win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 0.0)
win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)

# --- Cabeçalho Técnico ---
st.markdown("<h2 style='color:#00d4ff;'>🎯 Painel Unificado de Abertura Pregão B3</h2>", unsafe_allow_html=True)
st.caption(f"Orquestração Ativa: V2 ({decisao_v2.get('metadata', {}).get('timestamp', 'N/A')})")

# --- Banner de Alinhamento de Produção ---
st.info("🚀 **Fila de Execução V2:** Este painel consome a decisão oficial gerada pelo motor inteligente de confluência.")

# --- Divisão Estratégica por Sub-Abas Operacionais ---
tab_overnight, tab_0900, tab_1000 = st.tabs([
    "🗓️ 1. Janela Pré-Market (Ajuste)", 
    "⚡ 2. Abertura 09:00h (Leilão WIN)", 
    "📊 3. Abertura 10:00h (Pregão À Vista)"
])

# ============================================================
# ABA 1: JANELA OVERNIGHT / ANÁLISE DE AJUSTE
# ============================================================
with tab_overnight:
    st.markdown("### 🌐 Cenário Macro e Arbitragem")
    
    col_macro, col_spread = st.columns([2, 1])
    
    with col_macro:
        resumo_macro = estimativas.get("resumo_macro", {})
        st.markdown(f"""
        * **Ambiente Global de Risco (VIX):** `{resumo_macro.get('vix', 'N/A')}`
        * **Petróleo Brent/WTI:** `US$ {resumo_macro.get('crude_oil', 'N/A')}`
        * **Minério de Ferro (SGX):** `US$ {resumo_macro.get('iron_ore', 'N/A')}`
        * **Curva DI Curta (2027):** `{resumo_macro.get('di1_2027', 'N/A')}%` | **DI Longa (2029):** `{resumo_macro.get('di1_2029', 'N/A')}%`
        """)
        
    with col_spread:
        distancia_pts = win_last - win_ajuste
        st.metric(
            label="Preço vs Ajuste Anterior",
            value=f"{win_last:,.0f} pts",
            delta=f"{distancia_pts:+.0f} pts",
            delta_color="normal" if abs(distancia_pts) > 100 else "off"
        )
        st.caption(f"Ajuste Base de Referência: {win_ajuste:,.0f}")

# ============================================================
# ABA 2: ABERTURA 09:00H (GAP E PIVOTS)
# ============================================================
with tab_0900:
    st.markdown("### 🔮 Projeção Estatística e Níveis de Pivô")
    
    win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE", {})
    pivots_win = estimativas.get("pivot_points", {}).get("WIN_FUT", {})
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Variação Teórica Projetada", f"{win_est.get('variacao_teorica_pct', 0.0):+.2f}%")
    c2.metric("Abertura Estimada (Pontos)", f"{win_est.get('abertura_teorica_pontos', 0.0):,.0f} pts")
    c3.metric("Risco Noticiário (09h)", noticias.get("resumo", {}).get("classificacao", "BAIXO"))
    
    if pivots_win:
        st.markdown("#### Níveis Técnicos de Suporte e Resistência (Floor Pivots)")
        p_col1, p_col2 = st.columns(2)
        p_col1.markdown(f"""
        * **Resistência 2 (R2):** `{pivots_win.get('R2', 0):,.0f}`
        * **Resistência 1 (R1):** `{pivots_win.get('R1', 0):,.0f}`
        * **Ponto de Pivô (PP):** `{pivots_win.get('PP', 0):,.0f}`
        """)
        p_col2.markdown(f"""
        * **Suporte 1 (S1):** `{pivots_win.get('S1', 0):,.0f}`
        * **Suporte 2 (S2):** `{pivots_win.get('S2', 0):,.0f}`
        """)

# ============================================================
# ABA 3: ABERTURA 10:00H (SMC E FILTROS INSTITUCIONAIS)
# ============================================================
with tab_1000:
    st.markdown("### 🧠 Confluências de Smart Money Concepts")
    
    vies_final = decisao_v2.get("decisao", {}).get("vies_final", "NEUTRO")
    confianca = decisao_v2.get("decisao", {}).get("confianca", 0)
    
    st.markdown(f"**Direção Sugerida pelo Core V2:** `{vies_final}` com `{confianca}%` de confiança operacional.")
    
    s_col1, s_col2 = st.columns(2)
    
    with s_col1:
        st.markdown("**Order Blocks Validados (MT5/Volume):**")
        obs = smc_regras.get("order_blocks", [])
        if obs:
            for ob in obs[:2]:
                st.markdown(f"• OB de **{ob['tipo']}** em `{ob['preco']:.0f}`")
        else:
            st.caption("Nenhum Order Block de volume mapeado no range de preço atual.")
            
    with s_col2:
        st.markdown("**Fair Value Gaps Ativos (Vazios de Liquidez):**")
        fvgs = smc_regras.get("fair_value_gaps", [])
        fvgs_abertos = [f for f in fvgs if not f.get("preenchido", False)]
        if fvgs_abertos:
            for fvg in fvgs_abertos[:2]:
                st.markdown(f"• FVG de **{fvg['tipo']}** entre `{fvg['inferior']:.0f}` e `{fvg['superior']:.0f}`")
        else:
            st.caption("Preço eficiente. Sem Fair Value Gaps abertos.")
