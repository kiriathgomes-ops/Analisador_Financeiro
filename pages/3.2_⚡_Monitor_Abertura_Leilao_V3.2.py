# -*- coding: utf-8 -*-
"""
Módulo: pages/3.2_⚡_Monitor_Abertura_Leilao_V3.2.py
Versão: 3.2 - Otimizado para Produção V2
Objetivo: Monitorar a formação de preço teórico e spreads no leilão da B3 (WIN/WDO/Ações)
"""

import streamlit as st
import json
import os
import pandas as pd 
from datetime import datetime
import plotly.graph_objects as go

# Importações de caminhos padronizados do config.py da V2
from config import FILE_MT5_V2, FILE_UNIFICADO, FILE_DECISAO_V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Monitor de Leilão", layout="wide")

# --- CARGA DE DADOS V2 ---
dados_mt5 = carregar_json_defensivo(FILE_MT5_V2)
dados_unificados = carregar_json_defensivo(FILE_UNIFICADO)
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)

st.markdown("<h2 style='color:#00d4ff;'>⚡ Monitor de Abertura e Leilão B3</h2>", unsafe_allow_html=True)
st.caption(f"Último snapshot capturado pelo pipeline: {dados_mt5.get('timestamp', 'N/A')}")

# --- SEÇÃO 1: STATUS DO MINI ÍNDICE (WIN) NO LEILÃO ---
st.markdown("### 📊 Status dos Contratos Vigentes")

ativos_mt5 = dados_mt5.get("ativos", {})
win_data = ativos_mt5.get("WIN", {})
wdo_data = ativos_mt5.get("WDO", {})

col_win, col_wdo = st.columns(2)

with col_win:
    st.markdown("#### 🔹 Mini Índice Future")
    if win_data.get("status") == "OK":
        contrato_win = win_data.get("contrato_principal", "N/A")
        preco_teorico = win_data.get("preco_teorico")
        last_price = win_data.get("last", 0.0)
        
        st.markdown(f"**Contrato Ativo:** `{contrato_win}` | **Vencimento:** `{win_data.get('vencimento', 'N/A')[:10]}`")
        
        # Validação do preço teórico (só aparece se estiver em leilão ativo)
        if preco_teorico and preco_teorico > 0:
            st.metric("Preço Teórico do Leilão", f"{preco_teorico:,.0f} pts", 
                      delta=f"{preco_teorico - last_price:+.0f} pts vs Último")
        else:
            st.metric("Último Preço (Mercado Aberto/Ajustado)", f"{last_price:,.0f} pts")
            st.caption("💡 Preço teórico indisponível fora do horário de leilão (08:50 - 09:00).")
    else:
        st.warning("⚠️ Dados do leilão do WIN indisponíveis no snapshot do MT5.")

with col_wdo:
    st.markdown("#### 💵 Mini Dólar Future")
    if wdo_data.get("status") == "OK":
        contrato_wdo = wdo_data.get("contrato_principal", "N/A")
        preco_teorico_wdo = wdo_data.get("preco_teorico")
        last_price_wdo = wdo_data.get("last", 0.0)
        
        st.markdown(f"**Contrato Ativo:** `{contrato_wdo}` | **Vencimento:** `{wdo_data.get('vencimento', 'N/A')[:10]}`")
        
        if preco_teorico_wdo and preco_teorico_wdo > 0:
            st.metric("Preço Teórico do Leilão", f"{preco_teorico_wdo:,.4f}", 
                      delta=f"{preco_teorico_wdo - last_price_wdo:+.4f} vs Último")
        else:
            st.metric("Último Preço (Mercado Aberto/Ajustado)", f"{last_price_wdo:,.2f}")
            st.caption("💡 Preço teórico indisponível fora do horário de leilão.")
    else:
        st.warning("⚠️ Dados do leilão do WDO indisponíveis no snapshot do MT5.")

st.markdown("---")

# --- SEÇÃO 2: MONITOR DE ARBITRAGEM DE AÇÕES (09:45 - 10:00) ---
st.markdown("### 🏦 Leilão do Mercado à Vista vs ADRs (Arbitragem)")
st.caption("Análise de descasamento e spread para abertura das ações às 10:00h")

# Lista de papéis peso-pesado mapeados na sua V2
acoes_foco = ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"]
ativos_unificados = dados_unificados.get("ativos", {})

linhas_tabela = []
for acao in acoes_foco:
    if acao in ativos_unificados:
        dados_acao = ativos_unificados[acao]
        ticker_adr = acao.replace("3", "").replace("4", "") + "_ADR"
        
        # Puxa variação da ADR correspondente vinda do Finnhub processado
        var_adr = ativos_unificados.get(ticker_adr, {}).get("variacao_pct", 0.0)
        var_b3 = dados_acao.get("variacao_pct", 0.0)
        
        spread = var_adr - var_b3
        
        sinal = "⚖️ Alinhado"
        if spread >= 0.5:
            sinal = "🟢 COMPRA B3 (Atrasada)"
        elif spread <= -0.5:
            sinal = "🔴 VENDA B3 (Esticada)"
            
        linhas_tabela.append({
            "Ativo B3": acao,
            "Preço Indicativo": f"R$ {dados_acao.get('preco', 0.0):,.2f}",
            "Var B3 (%)": f"{var_b3:+.2f}%",
            "Var ADR NY (%)": f"{var_adr:+.2f}%",
            "Spread (NY - B3)": f"{spread:+.2f}%",
            "Sinal Arbitragem": sinal
        })

if linhas_tabela:
    df_arbitragem = pd.DataFrame(linhas_tabela)
    st.table(df_arbitragem)
else:
    st.info("Aguardando atualização do arquivo de ativos unificados para calcular spreads de arbitragem.")

# --- SEÇÃO 3: TRAVA DE RISCO MACRO V2 ---
st.markdown("---")
st.markdown("### 🛡️ Alinhamento de Risco do Orquestrador V2")

decisao_data = dados_v2.get("decisao", {})
vies_macro = decisao_data.get("vies_final", "NEUTRO")
riscos_v2 = decisao_data.get("riscos", [])

if riscos_v2:
    st.markdown("**Alertas de Risco Ativos para a Abertura:**")
    for risco in riscos_v2:
        st.markdown(f"⚠️ {risco}")
else:
    st.success("🟢 Zero travas quantitativas ou riscos extremos reportados pelo Orquestrador V2.")
