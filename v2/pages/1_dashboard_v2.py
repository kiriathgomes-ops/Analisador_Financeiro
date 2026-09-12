# -*- coding: utf-8 -*-
"""
Módulo: v2/pages/1.1_dashboard_v2.py
Versão: 2.5 - Produção Oficial V2
Objetivo: Painel principal (Dashboard Master) para exibição do Viés Confluente V2 e Gatilhos.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# Ingestão de caminhos centralizados e estáveis do config.py
from config import FILE_DECISAO_V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit (Layout Wide para painéis de monitoramento)
st.set_page_config(page_title="Quant Terminal - Dashboard V2", layout="wide")

# --- CARGA DA FONTE DA VERDADE (V2) ---
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)

# --- CABEÇALHO PRINCIPAL ---
st.markdown("<h2 style='color:#00d4ff;'>🚀 Quant Terminal — Dashboard de Decisão Master V2</h2>", unsafe_allow_html=True)
st.caption(f"Pipeline Sincronizado | Horário do Snapshot: {dados_v2.get('metadata', {}).get('timestamp', 'N/A')}")

#############
# ============================================================
# VERIFICAÇÃO DE DEFASAGEM DOS DADOS
# ============================================================
timestamp_str = dados_v2.get('metadata', {}).get('timestamp', '')
if timestamp_str:
    try:
        # Tenta parsear timestamp ISO (com ou sem microssegundos)
        if 'Z' in timestamp_str:
            ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            ts = datetime.fromisoformat(timestamp_str)
    except ValueError:
        try:
            ts = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            ts = None
    
    if ts:
        agora = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        diff_minutos = (agora - ts).total_seconds() / 60
        
        if diff_minutos > 30:
            st.error(f"⛔ **Dados críticos desatualizados!** Última atualização há **{diff_minutos:.0f} minutos**. Execute o pipeline imediatamente.")
        elif diff_minutos > 5:
            st.warning(f"⚠️ **Dados defasados!** Última atualização há **{diff_minutos:.0f} minutos**. Considere rodar o pipeline novamente.")
        else:
            st.success(f"✅ Dados atualizados há **{diff_minutos:.1f} minutos**.")
else:
    st.info("ℹ️ Timestamp da decisão não disponível para verificação de atualização.")

#########




if not dados_v2:
    st.error("⚠️ Erro Crítico: O arquivo 'Decisao_V2.json' não foi encontrado. Execute o main_pipeline.py para consolidar a tomada de decisão.")
    st.stop()

decisao_data = dados_v2.get("decisao", {})
vies_final = decisao_data.get("vies_final", "NEUTRO")
confianca = decisao_data.get("confianca", 0)

# ============================================================
# SEÇÃO 1: PAINEL MASTER DE SINAL (KPIs DE FLUXO)
# ============================================================
col_sinal, col_alvos = st.columns([1, 2], gap="large")

with col_sinal:
    st.markdown("### 📡 Viés Direcional Consolidado")
    
    # Renderização de Bloco Estilizado com base no viés institucional do Orquestrador
    if "COMPRA" in vies_final.upper() or vies_final.upper() in ["ALTA", "BULL"]:
        st.markdown(
            f"<div style='background-color:rgba(0, 255, 136, 0.1); padding:24px; border-radius:12px; border:2px solid #00ff88; text-align:center;'>"
            f"<span style='font-size:1.1rem; color:#8b949e; letter-spacing:1px;'>DIREÇÃO DE PREVISTA</span><br>"
            f"<span style='font-size:2.8rem; font-weight:bold; color:#00ff88; letter-spacing:-1px;'>COMPRA</span><br>"
            f"<span style='font-size:1.6rem; font-weight:bold; color:#fff;'>{confianca}% Confluência</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
    elif "VENDA" in vies_final.upper() or vies_final.upper() in ["BAIXA", "BEAR"]:
        st.markdown(
            f"<div style='background-color:rgba(255, 107, 107, 0.1); padding:24px; border-radius:12px; border:2px solid #ff6b6b; text-align:center;'>"
            f"<span style='font-size:1.1rem; color:#8b949e; letter-spacing:1px;'>DIREÇÃO PREVISTA</span><br>"
            f"<span style='font-size:2.8rem; font-weight:bold; color:#ff6b6b; letter-spacing:-1px;'>VENDA</span><br>"
            f"<span style='font-size:1.6rem; font-weight:bold; color:#fff;'>{confianca}% Confluência</span>"
            f"</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='background-color:rgba(255, 255, 255, 0.05); padding:24px; border-radius:12px; border:2px solid #888; text-align:center;'>"
            f"<span style='font-size:1.1rem; color:#8b949e; letter-spacing:1px;'>DIREÇÃO PREVISTA</span><br>"
            f"<span style='font-size:2.8rem; font-weight:bold; color:#ccc; letter-spacing:-1px;'>NEUTRO</span><br>"
            f"<span style='font-size:1.6rem; font-weight:bold; color:#fff;'>{confianca}% Equilíbrio</span>"
            f"</div>", 
            unsafe_allow_html=True
        )

with col_alvos:
    st.markdown("### 🎯 Gatilhos e Limites Operacionais do Robô")
    
    # Cards de métricas com os preços de disparo injetados dinamicamente
    k1, k2, k3 = st.columns(3)
    k1.metric("Gatilho Entry (Stop Order)", f"{decisao_data.get('entrada', 0):,.0f} pts" if decisao_data.get('entrada') else "—")
    k2.metric("Stop Loss Técnico", f"{decisao_data.get('stop_loss', 0):,.0f} pts" if decisao_data.get('stop_loss') else "—", delta_color="inverse")
    k3.metric("Alvo Projeção (Take 1)", f"{decisao_data.get('alvo_1', 0):,.0f} pts" if decisao_data.get('alvo_1') else "—")
    
    st.markdown(f"⚠️ **Regra de Invalidação / Desmonte de Posição:** `{decisao_data.get('invalidacao', 'Aguardando Rompimento')}`")

st.markdown("---")

# ============================================================
# SEÇÃO 2: AUDITORIA DE ARGUMENTOS E FATORES DE RISCO
# ============================================================
col_argumentos, col_travas = st.columns(2)

with col_argumentos:
    st.markdown("### 📝 Argumentos e Confluência de Submotores")
    motivos = decisao_data.get("motivos", [])
    if motivos:
        for m in motivos:
            st.markdown(f"• {m}")
    else:
        st.caption("Mesa neutra. Sem vetores de força confluentes mapeados nas últimas barras.")

with col_travas:
    st.markdown("### 🛡️ Trava de Volatilidade e Alertas de Risco")
    riscos = decisao_data.get("riscos", [])
    if riscos:
        for r in riscos:
            st.markdown(f"❌ **ALERTA DE RISCO:** {r}")
    else:
        st.success("🟢 Alinhamento de risco limpo. Sem anomalias de spread ou volatilidade excessiva no robô.")

st.markdown("---")

# ============================================================
# SEÇÃO 3: VERIFICAÇÃO DE SAÚDE DOS CONTEXTOS V2
# ============================================================
st.markdown("### ⚙️ Painel de Auditoria de Contextos Operacionais")
ctx = dados_v2.get("contextos", {})

def formatar_status_ctx(flag_ok):
    return "🟢 INTEGRAL" if flag_ok else "🔴 INDISPONÍVEL / OFFLINE"

cx1, cx2, cx3, cx4, cx5 = st.columns(5)
cx1.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:6px; text-align:center;'>📊 <b>Market Context</b><br><span style='font-size:0.85rem; font-weight:bold;'>{formatar_status_ctx(ctx.get('market_ok'))}</span></div>", unsafe_allow_html=True)
cx2.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:6px; text-align:center;'>🔮 <b>Prediction Context</b><br><span style='font-size:0.85rem; font-weight:bold;'>{formatar_status_ctx(ctx.get('prediction_ok'))}</span></div>", unsafe_allow_html=True)
cx3.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:6px; text-align:center;'>📰 <b>News Context</b><br><span style='font-size:0.85rem; font-weight:bold;'>{formatar_status_ctx(ctx.get('news_ok'))}</span></div>", unsafe_allow_html=True)
cx4.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:6px; text-align:center;'>👁️ <b>Vision AI Context</b><br><span style='font-size:0.85rem; font-weight:bold;'>{formatar_status_ctx(ctx.get('vision_ok'))}</span></div>", unsafe_allow_html=True)
cx5.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:6px; text-align:center;'>🏦 <b>Session History</b><br><span style='font-size:0.85rem; font-weight:bold;'>{formatar_status_ctx(ctx.get('session_ok'))}</span></div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("🔒 Terminal de Produção V2 sincronizado — Dados processados de forma síncrona com os motores matemáticos de back-end.")
