# -*- coding: utf-8 -*-
"""
Módulo: pages/5.3_⚙️_Core_Engine.py
Versão: 3.2 - Central de Auditoria V2 (com SMC, Volume Profile e Cost of Carry)
Objetivo: Interface de controle, monitoramento e auditoria da tomada de decisão do Orquestrador V2.
"""

import json
from datetime import datetime
import pandas as pd
import streamlit as st

# Importação de caminhos centralizados do config.py da V2
from config import FILE_DECISAO_V2, FILE_DECISAO_CORE


def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Core Engine V2", layout="wide")

# --- CARGA DOS PAYLOADS DE DECISÃO ---
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
dados_v1_legado = carregar_json_defensivo(FILE_DECISAO_CORE)

st.markdown("<h2 style='color:#00d4ff;'>⚙️ Core Decision Engine — Central de Orquestração</h2>", unsafe_allow_html=True)
st.caption(f"**Fonte oficial: Decisao_V2.json** | Snapshot: {dados_v2.get('metadata', {}).get('timestamp', 'N/A')}")

# ============================================================
# VERIFICAÇÃO DE DEFASAGEM DOS DADOS
# ============================================================
timestamp_str = dados_v2.get('metadata', {}).get('timestamp', '')
if timestamp_str:
    try:
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

if not dados_v2:
    st.error("⚠️ Erro Crítico: Arquivo Decisao_V2.json não encontrado. O pipeline operacional V2 precisa ser executado.")
    st.stop()

# --- SEÇÃO 1: AUDITORIA DOS 5 CONTEXTOS DO ORQUESTRADOR V2 ---
st.markdown("### 📡 Saúde e Integridade dos Motores Contextuais (V2)")
st.caption("Verificação em tempo real de execução e resposta de cada braço analítico do pipeline")

ctx = dados_v2.get("contextos", {})

def obter_badge_status(flag_ok):
    return "🟢 OK" if flag_ok else "🔴 Falhou"

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
    p_col1, p_col2, p_col3 = st.columns(3)
    p_col1.metric("Ordem Gatilho (Stop Entry)", f"{decisao_data.get('entrada', 0):,.0f} pts" if decisao_data.get('entrada') else "—")
    p_col2.metric("Stop Loss Proteção", f"{decisao_data.get('stop_loss', 0):,.0f} pts" if decisao_data.get('stop_loss') else "—")
    p_col3.metric("Alvo Principal (Take 1)", f"{decisao_data.get('alvo_1', 0):,.0f} pts" if decisao_data.get('alvo_1') else "—")
    
    st.markdown(f"🚨 **Nível de Invalidação do Setup:** `{decisao_data.get('invalidacao', 'Não Mapeado')}`")

# --- SEÇÃO 3: NÍVEIS DE TESOURARIA & COST OF CARRY (NOVO PAINEL V2.6) ---
st.markdown("---")
st.markdown("### 🏦 Métricas Institucionais (Volume Profile & Cost of Carry)")

meta_info = decisao_data.get("metadados", {})
smc_info = meta_info.get("smc", {})
teorica_info = meta_info.get("precificacao_teorica", {})
pivots_info = meta_info.get("pivots", {})

col_smc_poc, col_smc_vwap, col_teorico, col_carregado = st.columns(4)

poc_val = smc_info.get("poc_ontem", 0.0)
vwap_val = smc_info.get("vwap_ontem", 0.0)
teorico_val = teorica_info.get("abertura_teorica", 0.0)
carregado_val = teorica_info.get("preco_carregado_di", 0.0)
ob_alinhado = smc_info.get("ob_alinhado_com_poc", False)

col_smc_poc.metric(
    "POC Ontem (Volume)", 
    f"{poc_val:,.0f} pts" if poc_val > 0 else "—",
    delta="OB Alinhado 🟢" if ob_alinhado else "Sem OB Direto",
    delta_color="normal" if ob_alinhado else "off"
)

col_smc_vwap.metric(
    "VWAP Ontem", 
    f"{vwap_val:,.1f} pts" if vwap_val > 0 else "—"
)

col_teorico.metric(
    "Abertura Teórica WIN", 
    f"{teorico_val:,.0f} pts" if teorico_val > 0 else "—"
)

col_carregado.metric(
    "Preço Carregado (DI/252)", 
    f"{carregado_val:,.0f} pts" if carregado_val > 0 else "—"
)

# --- SEÇÃO 4: AUDITORIA DE CRITÉRIOS (MOTIVOS E RISCOS) ---
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

# --- SEÇÃO 5: PIVÔS DE VAREJO (FLOOR PIVOTS) ---
st.markdown("---")
with st.expander("📍 Pivôs Clássicos de Varejo (Floor Pivots)"):
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Resistência 2 (R2)", f"{pivots_info.get('r2', 0):,.0f}")
    p2.metric("Resistência 1 (R1)", f"{pivots_info.get('r1', 0):,.0f}")
    p3.metric("Ponto de Pivô (PP)", f"{pivots_info.get('pp', 0):,.0f}")
    p4.metric("Suporte 1 (S1)", f"{pivots_info.get('s1', 0):,.0f}")
    p5.metric("Suporte 2 (S2)", f"{pivots_info.get('s2', 0):,.0f}")

# --- SEÇÃO 6: HISTÓRICO / AUDITORIA DA V1 CONTRA A V2 ---
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