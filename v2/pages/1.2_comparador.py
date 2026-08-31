# -*- coding: utf-8 -*-
"""
Módulo: v2/pages/1.2_comparador.py
Versão: 2.0 - Oficial de Auditoria (V2)
Objetivo: Comparar a tomada de decisão entre a V1 (Legada) e a V2 (Produção Oficial).
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# Importação centralizada de caminhos do config.py
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
st.set_page_config(page_title="Quant Terminal - Comparador V1 x V2", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>⚖️ Comparador Analítico: Core V1 × Confluência V2</h2>", unsafe_allow_html=True)
st.caption("Mapeamento de performance e auditoria de transição de motores analíticos")

# --- BANNER DE GOVERNANÇA (DECISOES.MD) ---
st.warning(
    "⚠️ **AVISO DE DESCONTINUAÇÃO:** O motor de viés V1 foi oficialmente desligado do pipeline de produção "
    "e sua etapa no orquestrador foi comentada. Use esta tela exclusivamente para auditoria e rastreabilidade histórica."
)

# --- CARGA DOS PAYLOADS ---
dados_v1 = carregar_json_defensivo(FILE_DECISAO_CORE)
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)

if not dados_v2:
    st.error("❌ Erro: Arquivo Decisao_V2.json ausente no disco. Execute o pipeline para gerar os dados oficiais.")
    st.stop()

# --- EXTRAÇÃO DE VARIÁVEIS V1 (LEGADO) ---
vies_v1_raw = dados_v1.get("analise_operacional", {}).get("WIN_INDICE", {})
vies_v1 = vies_v1_raw.get("vies_final", "DESATIVADO (NO-OP)")
score_v1 = vies_v1_raw.get("score_numeric", 0.0)

# --- EXTRAÇÃO DE VARIÁVEIS V2 (OFICIAL) ---
decisao_v2 = dados_v2.get("decisao", {})
vies_v2 = decisao_v2.get("vies_final", "NEUTRO")
confianca_v2 = decisao_v2.get("confianca", 0)

# ============================================================
# SEÇÃO 1: COMPARATIVO LADO A LADO (VISUAL CARDS)
# ============================================================
col_v1, col_v2 = st.columns(2, gap="large")

with col_v1:
    st.markdown("#### 🔴 Motor Antigo (Legado V1)")
    st.markdown(
        f"<div style='background-color:rgba(255,255,255,0.02); padding:20px; border-radius:8px; border:1px dashed #555; text-align:center;'>"
        f"<span style='font-size:0.9rem; color:#8b949e;'>VIÉS V1 HISTÓRICO</span><br>"
        f"<span style='font-size:1.8rem; font-weight:bold; color:#aaa;'>{vies_v1.replace('_', ' ')}</span><br>"
        f"<span style='font-size:1.1rem; color:#888;'>Score: {score_v1:+.2f}</span>"
        f"</div>", 
        unsafe_allow_html=True
    )

with col_v2:
    st.markdown("#### 🚀 Novo Motor (Oficial V2)")
    
    # Renderização dinâmica de cores baseada no sinal real ativo
    if "COMPRA" in vies_v2.upper() or vies_v2.upper() == "ALTA":
        cor_borda = "#00ff88"
        bg_card = "rgba(0, 255, 136, 0.1)"
    elif "VENDA" in vies_v2.upper() or vies_v2.upper() == "BAIXA":
        cor_borda = "#ff6b6b"
        bg_card = "rgba(255, 107, 107, 0.1)"
    else:
        cor_borda = "#00d4ff"
        bg_card = "rgba(0, 212, 255, 0.05)"
        
    st.markdown(
        f"<div style='background-color:{bg_card}; padding:20px; border-radius:8px; border:1px solid {cor_borda}; text-align:center;'>"
        f"<span style='font-size:0.9rem; color:#c9d1d9;'>VIÉS OPERACIONAL ATIVO</span><br>"
        f"<span style='font-size:1.8rem; font-weight:bold; color:{cor_borda};'>{vies_v2}</span><br>"
        f"<span style='font-size:1.1rem; color:#fff;'>Confiança: {confianca_v2}%</span>"
        f"</div>", 
        unsafe_allow_html=True
    )

st.markdown("---")

# ============================================================
# SEÇÃO 2: MATRIZ DE DIVERGÊNCIA E CONVERGÊNCIA
# ============================================================
st.markdown("### 🔍 Auditoria de Alinhamento Direcional")

# Checagem estatística simples de convergência
sinal_v1_comprador = any(x in vies_v1.upper() for x in ["COMPRA", "ALTA"])
sinal_v1_vendedor = any(x in vies_v1.upper() for x in ["VENDA", "BAIXA"])

sinal_v2_comprador = any(x in vies_v2.upper() for x in ["COMPRA", "ALTA"])
sinal_v2_vendedor = any(x in vies_v2.upper() for x in ["VENDA", "BAIXA"])

convergentes = (sinal_v1_comprador and sinal_v2_comprador) or (sinal_v1_vendedor and sinal_v2_vendedor)
ambos_neutros = "NEUTRO" in vies_v1.upper() and "NEUTRO" in vies_v2.upper()

if ambos_neutros:
    st.info("⚖️ **Alinhamento Neutro:** Ambos os motores concordam em não operar a abertura atual (Mercado em Equilíbrio).")
elif convergentes:
    st.success("✅ **Sinais Convergentes:** V1 e V2 apontam para a mesma direção de mercado. Alta confluência estatística.")
else:
    st.markdown(
        "<div style='background-color:rgba(255,170,0,0.12); padding:15px; border-radius:6px; border-left:5px solid #ffaa00; font-size:0.95rem;'>"
        "⚠️ <b>DIVERGÊNCIA DETECTADA:</b> Os motores apontam direções opostas ou conflito de liquidez. "
        "A <b>V2 prevalece isoladamente</b> como ordem de envio por possuir filtros institucionais de volume e SMC.</div>", 
        unsafe_allow_html=True
    )

# --- MATRIZ DE CAMPOS COMPILADA (PANDAS) ---
st.markdown("<br>", unsafe_allow_html=True)
matriz_comparativa = [
    {
        "Métrica Operacional": "Viés Direcional Final",
        "Configuração V1 (Legada)": vies_v1,
        "Orquestração V2 (Oficial)": vies_v2,
        "Ação do Sistema": "Executar sinal V2"
    },
    {
        "Métrica Operacional": "Força / Métrica de Confiança",
        "Configuração V1 (Legada)": f"{score_v1:+.2f} (Score)",
        "Orquestração V2 (Oficial)": f"{confianca_v2}% (Ponderado)",
        "Ação do Sistema": "Dimensionar lote via V2"
    },
    {
        "Métrica Operacional": "Ordem Gatilho (WIN)",
        "Configuração V1 (Legada)": "Não Mapeado (Apenas Direcional)",
        "Orquestração V2 (Oficial)": f"{decisao_v2.get('entrada', 0):,.0f} pts" if decisao_v2.get('entrada') else "Aguardando",
        "Ação do Sistema": "Enviar Stop Order MT5"
    },
    {
        "Métrica Operacional": "Fatores / Motivos",
        "Configuração V1 (Legada)": f"Mapeados: {len(vies_v1_raw.get('fatores_relevantes', []))}",
        "Orquestração V2 (Oficial)": f"Mapeados: {len(decisao_v2.get('motivos', []))}",
        "Apx Técnica": "Filtrar por Volume SMC"
    }
]

st.table(pd.DataFrame(matriz_comparativa).set_index("Métrica Operacional"))
