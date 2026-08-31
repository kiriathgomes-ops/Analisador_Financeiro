# -*- coding: utf-8 -*-
"""
Módulo: pages/8.2_🔢_Calculadora.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Calculadora operacional de risco, simulação de ordens e dimensionamento de lote para WIN.
"""

import streamlit as st
import json
from config import FILE_UNIFICADO  # Importação centralizada do config V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Calculadora Operacional", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🔢 Calculadora Operacional e Gestão de Risco</h2>", unsafe_allow_html=True)
st.caption("Simulador quantitativo para dimensionamento de posição e gerenciamento de capital (WIN)")

# --- CARGA DE PREÇOS V2 PARA PREENCHIMENTO PADRÃO ---
unificados = carregar_json_defensivo(FILE_UNIFICADO)
ativos = unificados.get("ativos", {})
win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 175000.0) # Fallback seguro se vazio

# --- INTERFACE DE ENTRADA DE DADOS ---
st.markdown("### 🛠️ Parâmetros da Operação (Simulação)")

col_params, col_fibo = st.columns(2, gap="large")

with col_params:
    st.markdown("**Dimensionamento de Lote e Capital:**")
    capital_total = st.number_input("Capital Total Alocado na Corretora (R$):", min_value=100.0, value=5000.0, step=500.0)
    numero_contratos = st.number_input("Quantidade de Contratos (Lote WIN):", min_value=1, value=5, step=1)
    
    st.markdown("<br>**Níveis de Preço do Trade (SMC/ICT):**", unsafe_allow_html=True)
    preco_entrada = st.number_input("Preço de Entrada (Gatilho Stop Entry):", min_value=1000.0, value=float(win_last), step=5.0)
    preco_stop = st.number_input("Preço de Invalidação (Stop Loss Técnico):", min_value=1000.0, value=float(win_last - 150), step=5.0)
    preco_alvo = st.number_input("Preço de Mitigação (Take Profit 1):", min_value=1000.0, value=float(win_last + 300), step=5.0)

# --- MOTORES DE CÁLCULO DE RISCO ---
# 1. Distâncias em pontos
pts_stop = abs(preco_entrada - preco_stop)
pts_alvo = abs(preco_alvo - preco_entrada)

# 2. Valores financeiros (WIN = R$ 0,20 por ponto por contrato)
financeiro_stop = pts_stop * 0.20 * numero_contratos
financeiro_alvo = pts_alvo * 0.20 * numero_contratos

# 3. Percentual de risco sobre o capital da conta
pct_risco_capital = (financeiro_stop / capital_total) * 100

# 4. Relação Risco vs Recompensa (R:R)
relacao_rr = pts_alvo / pts_stop if pts_stop > 0 else 0.0

# --- EXIBIÇÃO DO PAINEL DE RISCO (OUTPUT VISUAL) ---
with col_fibo:
    st.markdown("**🛡️ Diagnóstico de Risco e Alocação:**")
    
    # Caixa de status baseada no gerenciamento de risco profissional (máximo 2% por trade)
    if pct_risco_capital > 2.5:
        st.markdown(
            f"<div style='background-color:rgba(255,107,107,0.12); padding:15px; border-radius:8px; border:1px solid #ff6b6b; margin-bottom:15px;'>"
            f"❌ <b>ALERTA DE ALTA EXPOSIÇÃO:</b> Este trade arrisca <b>{pct_risco_capital:.2f}%</b> do seu capital. "
            f"Recomendado reduzir o lote ou o stop para ficar abaixo do limite institucional de 2.00%.</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='background-color:rgba(0,255,136,0.1); padding:15px; border-radius:8px; border:1px solid #00ff88; margin-bottom:15px;'> "
            f"🟢 <b>RISCO SOBRE CONTROLE:</b> Exposição de <b>{pct_risco_capital:.2f}%</b> do capital. "
            f"Parâmetros dentro do gerenciamento profissional seguro.</div>", 
            unsafe_allow_html=True
        )

    # Painel de KPIs Financeiros
    m1, m2 = st.columns(2)
    m1.metric("Stop Loss Estimado", f"R$ {financeiro_stop:,.2f}", f"{pts_stop:.0f} pts", delta_color="inverse")
    m2.metric("Take Profit Estimado", f"R$ {financeiro_alvo:,.2f}", f"{pts_alvo:.0f} pts")
    
    st.markdown("---")
    st.markdown(f"📐 **Relação Risco vs Recompensa (R:R):** `1 : {relacao_rr:.2f}`")
    
    if relacao_rr >= 2.0:
        st.caption("🎯 **Matemática Matemática Favorável:** Relação maior que 1:2. Setup estatisticamente lucrativo no longo prazo.")
    else:
        st.caption("⚠️ **Atenção:** Relação R:R menor que 1:2. O risco pode não compensar o ganho potencial para este tamanho de stop.")

st.markdown("---")
st.caption("🔒 Módulo matemático auxiliar — Focado estritamente na preservação de capital e proteção da conta de trading.")
