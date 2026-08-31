# -*- coding: utf-8 -*-
"""
Módulo: pages/5.3_⚙️_Core_Engine.py
Versão: 3.0 - Central de Auditoria V2
Objetivo: Interface de controle, monitoramento e auditoria da tomada de decisão do Orquestrador V2.
"""

import streamlit as st
import json
from datetime import datetime
import pandas as pd

# Importação de caminhos centralizados do config.py da V2
from config import FILE_DECISAO_V2, FILE_DECISAO_CORE

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Core Engine V2", layout="wide")

# --- CARGA DOS PAYLOADS DE DECISÃO ---
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
dados_v1_legado = carregar_json_defensivo(FILE_DECISAO_CORE)

st.markdown("<h2 style='color:#00d4ff;'>⚙️ Core Decision Engine — Central de Orquestração</h2>", unsafe_allow_html=True)
st.caption(f"Status da Matriz de Decisão V2 | Snapshot: {dados_v2.get('metadata', {}).get('timestamp', 'N/A')}")

if not dados_v2:
    st.error("⚠️ Erro Crítico: Arquivo Decisao_V2.json não encontrado. O pipeline operacional V2 precisa ser executado.")
    st.stop()

# --- SEÇÃO 1: AUDITORIA DOS 5 CONTEXTOS DO ORQUESTRADOR V2 ---
st.markdown("### 📡 Saúde e Integridade dos Motores Contextuais (V2)")
st.caption("Verificação em tempo real de execução e resposta de cada braço analítico do pipeline")

ctx = dados_v2.get("contextos", {})

# Ícones dinâmicos de status
def obter_badge_status(flag_ok):
    return "🟢 Concluído / Integridade OK" if flag_ok else "🔴 Falhou / Offline (Usando Fallback/Cache)"

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:8px; text-align:center; border-top:3px solid #00ff88;'>📊 <b>Market Context</b><br><span style='font-size:0.85rem;'>{obter_badge_status(ctx.get('market_ok'))}</span></div>", unsafe_allow_html=True)
c2.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:8px; text-align:center; border-top:3px solid #00ff88;'>🔮 <b>Prediction Context</b><br><span style='font-size:0.85rem;'>{obter_badge_status(ctx.get('prediction_ok'))}</span></div>", unsafe_allow_html=True)
c3.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:8px; text-align:center; border-top:3px solid #00ff88;'>📰 <b>News Context</b><br><span style='font-size:0.85rem;'>{obter_badge_status(ctx.get('news_ok'))}</span></div>", unsafe_allow_html=True)
c4.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:8px; text-align:center; border-top:3px solid #00ff88;'>👁️ <b>Vision AI Context</b><br><span style='font-size:0.85rem;'>{obter_badge_status(ctx.get('vision_ok'))}</span></div>", unsafe_allow_html=True)
c5.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:8px; text-align:center; border-top:3px solid #00ff88;'>🏦 <b>Session History</b><br><span style='font-size:0.85rem;'>{obter_badge_status(ctx.get('session_ok'))}</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- SEÇÃO 2: RESULTADO CONSOLIDADO DA VERDADE (V2) ---
st.markdown("### 🎯 Parâmetros Finais de Tomada de Decisão (Gatilhos)")

decisao_data = dados_v2.get("decisao", {})
vies_final = decisao_data.get("vies_final", "NEUTRO")
confianca = decisao_data.get("confianca", 0)

col_vies, col_parametros = st.columns([1, 2])

with col_vies:
    if "COMPRA" in vies_final.upper() or vies_final.upper() == "ALTA":
        st.markdown(f"<div style='background-color:rgba(0, 255, 136, 0.1); padding:20px; border-radius:12px; border:1px solid #00ff88; text-align:center;'><span style='font-size:1rem; color:#8b949e;'>VIÉS CORE V2</span><br><span style='font-size:2rem; font-weight:bold; color:#00ff88;'>COMPRA</span><br><span style='font-size:1.5rem; font-weight:bold;'>{confianca}%</span> de Força</div>", unsafe_allow_html=True)
    elif "VENDA" in vies_final.upper() or vies_final.upper() == "BAIXA":
        st.markdown(f"<div style='background-color:rgba(255, 107, 107, 0.1); padding:20px; border-radius:12px; border:1px solid #ff6b6b; text-align:center;'><span style='font-size:1rem; color:#8b949e;'>VIÉS CORE V2</span><br><span style='font-size:2rem; font-weight:bold; color:#ff6b6b;'>VENDA</span><br><span style='font-size:1.5rem; font-weight:bold;'>{confianca}%</span> de Força</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background-color:rgba(255, 255, 255, 0.05); padding:20px; border-radius:12px; border:1px solid #888; text-align:center;'><span style='font-size:1rem; color:#8b949e;'>VIÉS CORE V2</span><br><span style='font-size:2rem; font-weight:bold; color:#ccc;'>NEUTRO</span><br><span style='font-size:1.5rem; font-weight:bold;'>{confianca}%</span> de Força</div>", unsafe_allow_html=True)

with col_parametros:
    # Mostra os gatilhos matemáticos de ordens gerados na V2
    p_col1, p_col2, p_col3 = st.columns(3)
    p_col1.metric("Ordem Gatilho (Stop Entry)", f"{decisao_data.get('entrada', 0):,.0f} pts" if decisao_data.get('entrada') else "—")
    p_col2.metric("Stop Loss Proteção", f"{decisao_data.get('stop_loss', 0):,.0f} pts" if decisao_data.get('stop_loss') else "—")
    p_col3.metric("Alvo Principal (Take 1)", f"{decisao_data.get('alvo_1', 0):,.0f} pts" if decisao_data.get('alvo_1') else "—")
    
    st.markdown(f"🚨 **Nível de Invalidação do Setup:** `{decisao_data.get('invalidacao', 'Não Mapeado')}`")

# --- SEÇÃO 3: AUDITORIA DE CRITÉRIOS (POR QUE TOMOU ESSA DECISÃO?) ---
st.markdown("---")
st.markdown("### 📝 Fatores Determinantes e Modelagem de Riscos")

col_motivos, col_riscos = st.columns(2)

with col_motivos:
    st.markdown("**Fatores de Confluência Encontrados (Motivos):**")
    motivos = decisao_data.get("motivos", [])
    if motivos:
        for m in motivos:
            st.markdown(f"• {m}")
    else:
        st.caption("Proporção neutra. Sem confluências expressivas registradas.")

with col_riscos:
    st.markdown("**Trava Geral de Risco (Alertas Ativos):**")
    riscos = decisao_data.get("riscos", [])
    if riscos:
        for r in riscos:
            st.markdown(f"❌ {r}")
    else:
        st.success("🟢 Alinhamento quantitativo limpo. Sem travas de volatilidade abusiva ou erros de cache.")

# --- SEÇÃO 4: HISTÓRICO / AUDITORIA DA V1 CONTRA A V2 ---
st.markdown("---")
with st.expander("📚 Histórico e Auditoria de Retrocompatibilidade (Módulo V1 Legado)"):
    st.warning("⚠️ **ATENÇÃO:** O motor de viés institucional V1 está DESATIVADO do pipeline operacional conforme as regras de governança do projeto. Os dados abaixo servem exclusivamente para auditoria ou rollback emergencial.")
    
    if dados_v1_legado:
        vies_v1 = dados_v1_legado.get("analise_operacional", {}).get("WIN_INDICE", {})
        st.markdown(f"""
        * **Último Viés V1 Registrado:** `{vies_v1.get('vies_final', 'NEUTRO')}`
        * **Último Score Numérico V1:** `{vies_v1.get('score_numeric', 0.0)}` de limite de banda (-10.0 a +10.0)
        * **Carimbado em:** `{dados_v1_legado.get('metadata', {}).get('timestamp', 'N/A')}`
        """)
    else:
        st.caption("Nenhum cache de dados históricos do Core V1 encontrado em Coletas/Decisao_Core.json.")
