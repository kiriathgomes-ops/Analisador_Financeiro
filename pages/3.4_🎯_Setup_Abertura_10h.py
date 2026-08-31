# -*- coding: utf-8 -*-
"""
Página Streamlit: 3.4 — Setup Abertura 10:00h (Ecossistema V2)
Objetivo: Monitorar a estratégia quantitativa/SMC de rompimento do range das 10h.
Consome: DadosAtivosUnificados.json, Decisao_V2.json, AnaliseGraficaSMC_Regras.json
"""

import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# Importações de caminhos centrais da sua aplicação
from config import COLETAS_DIR, FILE_UNIFICADO, FILE_DECISAO_V2, FILE_SMC_REGRAS

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Setup 10h", layout="wide")

def carregar_json_defensivo(caminho_path):
    """Carrega um arquivo JSON protegendo a UI contra falhas de I/O."""
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erro ao ler {caminho_path.name}: {e}")
        return {}

# --- CABEÇALHO DA INTERFACE ---
st.markdown("<h2 style='color:#00d4ff;'>🎯 Estratégia de Abertura das 10:00h</h2>", unsafe_allow_html=True)
st.caption("Foco exclusivo: Mini Índice (WINFUT) integrado ao Orquestrador V2 e Filtros SMC")

# --- LEITURA DE DADOS DO ECOSSISTEMA V2 ---
dados_unificados = carregar_json_defensivo(FILE_UNIFICADO)
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)

# Extração de variáveis de mercado em tempo real
ativos = dados_unificados.get("ativos", {})
win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 0.0)
win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)

# Simulação/Extração do range de 09:55-10:00 (substituir por integração real via API se disponível)
# Como exemplo quantitativo padrão, o sistema usará as métricas do último candle D1/M5 salvo
candle_high_10h = ativos.get("WIN_FUT", {}).get("high", win_last + 150)
candle_low_10h = ativos.get("WIN_FUT", {}).get("low", win_last - 150)
amplitude_range = candle_high_10h - candle_low_10h

# --- PAINEL LATERAL (SIDEBAR) CONTRA V1 ---
with st.sidebar:
    st.markdown("### 🚀 Confluência V2")
    vies_final = dados_v2.get("decisao", {}).get("vies_final", "NEUTRO")
    confianca = dados_v2.get("decisao", {}).get("confianca", 0)
    
    if "COMPRA" in vies_final.upper() or vies_final.upper() == "ALTA":
        st.success(f"Viés V2: COMPRA ({confianca}%)")
    elif "VENDA" in vies_final.upper() or vies_final.upper() == "BAIXA":
        st.error(f"Viés V2: VENDA ({confianca}%)")
    else:
        st.warning(f"Viés V2: NEUTRO ({confianca}%)")
        
    st.info(f"Preço Atual (MT5): {win_last:,.0f} pts")
    st.metric("Distância do Ajuste", f"{win_last - win_ajuste:+.0f} pts")

# --- CENTRAL OPERACIONAL (MÓDULO DE SINAL) ---
col_sinal, col_metricas = st.columns([1.5, 1])

with col_sinal:
    st.markdown("### 📡 Status do Sinal Operacional")
    
    # Validação de travas quantitativas de volatilidade
    if amplitude_range > 450 or amplitude_range < 70:
        st.markdown(
            f"<div style='background-color:rgba(255,107,107,0.15); padding:15px; border-radius:8px; border:1px solid #ff6b6b;'>"
            f"⚠️ <b>SINAL OPERACIONAL BLOQUEADO:</b> A amplitude da vela mãe (09:55-10:00) está fora do padrão "
            f"operacional seguro ({amplitude_range:.0f} pontos). Alto risco de ruído ou volatilidade abusiva.</div>", 
            unsafe_allow_html=True
        )
    else:
        # Geração dinâmica de níveis de Fibonacci institucionais com base na direção do Viés V2
        if "COMPRA" in vies_final.upper() or vies_final.upper() == "ALTA":
            entrada = candle_high_10h + 5
            stop = candle_low_10h - 20
            alvo = entrada + amplitude_range
            
            st.markdown(
                f"<div style='background-color:rgba(0,212,255,0.1); padding:15px; border-radius:8px; border:1px solid #00d4ff;'>"
                f"🟢 <b>PREPARADO PARA COMPRA:</b> Preço trabalhando para romper a Máxima do range das 10h.<br>"
                f"• <b>Gatilho Buy Stop:</b> {entrada:,.0f} pts (Máxima + 1 tick)<br>"
                f"• <b>Stop Loss Técnico:</b> {stop:,.0f} pts (Mínima - margem)<br>"
                f"• <b>Alvo (Projeção 100%):</b> {alvo:,.0f} pts</div>", 
                unsafe_allow_html=True
            )
        elif "VENDA" in vies_final.upper() or vies_final.upper() == "BAIXA":
            entrada = candle_low_10h - 5
            stop = candle_high_10h + 20
            alvo = entrada - amplitude_range
            
            st.markdown(
                f"<div style='background-color:rgba(255,107,107,0.1); padding:15px; border-radius:8px; border:1px solid #ff6b6b;'>"
                f"🔴 <b>PREPARADO PARA VENDA:</b> Preço trabalhando para romper a Mínima do range das 10h.<br>"
                f"• <b>Gatilho Sell Stop:</b> {entrada:,.0f} pts (Mínima - 1 tick)<br>"
                f"• <b>Stop Loss Técnico:</b> {stop:,.0f} pts (Máxima + margem)<br>"
                f"• <b>Alvo (Projeção 100%):</b> {alvo:,.0f} pts</div>", 
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='background-color:#1e2230; padding:15px; border-radius:8px;'>⚖️ <b>AGUARDANDO:</b> Orquestrador V2 aponta neutralidade macro. Não operar a abertura.</div>", unsafe_allow_html=True)

with col_metricas:
    st.markdown("### 📊 Métricas do Range (09:55-10:00)")
    c1, c2 = st.columns(2)
    c1.metric("Máxima Mãe", f"{candle_high_10h:,.0f} pts")
    c1.metric("Mínima Mãe", f"{candle_low_10h:,.0f} pts")
    c2.metric("Amplitude", f"{amplitude_range:.0f} pts")
    c2.metric("Ajuste Diário", f"{win_ajuste:,.0f} pts")

st.markdown("---")

# --- CONFLUENCIAS SMART MONEY (SMC) DO SEU MOTOR POR REGRAS ---
st.markdown("### 🧠 Filtros e Estruturas de Liquidez Ativas (SMC V2)")
col_ob, col_fvg, col_liq = st.columns(3)

with col_ob:
    st.markdown("**Order Blocks Recentes (Volume Confirmed)**")
    obs = dados_smc.get("order_blocks", [])
    if obs:
        for ob in obs[:3]:
            cor = "#00ff88" if ob['tipo'] == "COMPRA" else "#ff6b6b"
            st.markdown(f"• <span style='color:{cor};'>OB de {ob['tipo']}</span> em `{ob['preco']:.0f}` (Níveis: {ob['low']:.0f}-{ob['high']:.0f})", unsafe_allow_html=True)
    else:
        st.caption("Nenhum Order Block validado por volume na região atual.")

with col_fvg:
    st.markdown("**Fair Value Gaps Abertos (Imbalance)**")
    fvgs = dados_smc.get("fair_value_gaps", [])
    if fvgs:
        for fvg in fvgs[:3]:
            cor = "#00ff88" if fvg['tipo'] == "COMPRA" else "#ff6b6b"
            st.markdown(f"• <span style='color:{cor};'>FVG {fvg['tipo']}</span> | Zona: `{fvg['inferior']:.0f}` - `{fvg['superior']:.0f}`", unsafe_allow_html=True)
    else:
        st.caption("Mercado eficiente. Sem desequilíbrios institucionais abertos.")

with col_liq:
    st.markdown("**Piscinas de Liquidez Pendentes**")
    liq = dados_smc.get("liquidez", {})
    bsl = liq.get("bsl", [])
    ssl = liq.get("ssl", [])
    
    if bsl:
        st.markdown(f"🔼 **BSL (Buy Side):** `{bsl[0]:.0f}` pts — Alvo de caça comprador.")
    if ssl:
        st.markdown(f"🔽 **SSL (Sell Side):** `{ssl[0]:.0f}` pts — Alvo de caça vendedor.")
    if not bsl and not ssl:
        st.caption("Sem topos ou fundos duplos (Equal Highs/Lows) mapeados.")

st.markdown("---")

# --- GRÁFICO INTERATIVO PLOTLY COM PARÂMETROS DO PROJETO ---
st.markdown("### 📉 Visão Gráfica e Monitoramento de Rompimento")

# Gerando dados simulados para plotar o range interativo no terminal
fig = go.Figure()

# Plot do Ajuste B3
fig.add_trace(go.Scatter(x=[0, 10], y=[win_ajuste, win_ajuste], mode="lines", name="Ajuste Oficial B3", line=dict(color="orange", dash="dash")))

# Plot das linhas do Range das 10h
fig.add_trace(go.Scatter(x=[2, 8], y=[candle_high_10h, candle_high_10h], mode="lines+text", name="Máxima Mãe (Resistência)", line=dict(color="#00d4ff", width=2), text=["Gatilho Compra"], textposition="top center"))
fig.add_trace(go.Scatter(x=[2, 8], y=[candle_low_10h, candle_low_10h], mode="lines+text", name="Mínima Mãe (Suporte)", line=dict(color="#ff6b6b", width=2), text=["Gatilho Venda"], textposition="bottom center"))

# Preço atual
fig.add_trace(go.Scatter(x=[5], y=[win_last], mode="markers+text", name="Preço Atual B3", marker=dict(color="white", size=12, symbol="diamond"), text=[f"WIN: {win_last:.0f}"], textposition="middle right"))

fig.update_layout(
    title="Níveis Críticos para a Janela de Rompimento Institucional",
    xaxis=dict(showgrid=False, showticklabels=False),
    yaxis=dict(title="Pontuação Mini Índice (WIN)"),
    template="plotly_dark",
    height=400,
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(fig, use_container_width=True)
