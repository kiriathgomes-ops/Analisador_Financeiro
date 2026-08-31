# -*- coding: utf-8 -*-
"""
Módulo: v2/pages/1.3_analise_detalhada.py
Versão: 2.0 - Oficial de Produção V2
Objetivo: Detalhar exaustivamente os contextos, pesos e indicadores que geraram a decisão V2.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# Importação centralizada do caminho de produção V2
from config import FILE_DECISAO_V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Análise Detalhada", layout="wide")

# --- CARGA DOS DADOS V2 ---
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)

st.markdown("<h2 style='color:#00d4ff;'>🔬 Diagnóstico e Análise Detalhada da Decisão</h2>", unsafe_allow_html=True)
st.caption(f"Detalhamento completo de pesos e scores contextuais | Snapshot V2: {dados_v2.get('metadata', {}).get('timestamp', 'N/A')}")

if not dados_v2:
    st.error("❌ Erro: Arquivo Decisao_V2.json ausente no disco. Execute o pipeline para gerar as métricas detalhadas.")
    st.stop()

win_session = dados_v2.get("win_session", {})
contexto = win_session.get("contexto", {})

# ============================================================
# SEÇÃO 1: RESUMO DO CENÁRIO DE ABERTURA
# ============================================================
st.markdown("### 🗺️ Cenário Macroeconômico e Estrutural")
cenario_resumo = win_session.get("cenario", {})

c1, c2, c3 = st.columns(3)
c1.metric("Direção Provável (Gap)", cenario_resumo.get("direcao_provavel", "NEUTRO"))
c2.metric("Confiança do Cenário", f"{cenario_resumo.get('confianca_geral', 0.0):.1f}%")
c3.metric("Relação com Ajuste B3", cenario_resumo.get("relacao_com_ajuste", {}).get("posicao", "N/A"))

st.markdown(f"📋 **Comportamento Mapeado:** *{cenario_resumo.get('relacao_com_ajuste', {}).get('cenario_principal', 'Aguardando dados...')}*")

st.markdown("---")

# ============================================================
# SEÇÃO 2: DETALHAMENTO DOS COMPONENTES (TABs)
# ============================================================
st.markdown("### 🧩 Componentes do Cálculo Ponderado V2")

tab_global, tab_juros, tab_adrs = st.columns(3)

# ---- Bloco Mercado Global ----
with tab_global:
    st.markdown("#### 🌐 Drivers Globais & Commodities")
    sp500 = contexto.get("sp500_fut", {})
    nasdaq = contexto.get("nasdaq_fut", {})
    oil = contexto.get("crude_oil", {})
    iron = contexto.get("iron_ore", {})
    vix = contexto.get("vix", {})
    
    linhas_global = [
        {"Indicador": "S&P 500 Futuro", "Preço/Taxa": f"{sp500.get('preco', 0.0):,.2f}", "Variação": f"{sp500.get('variacao_pct', 0.0):+.2f}%"},
        {"Indicador": "Nasdaq Futuro", "Preço/Taxa": f"{nasdaq.get('preco', 0.0):,.2f}", "Variação": f"{nasdaq.get('variacao_pct', 0.0):+.2f}%"},
        {"Indicador": "Petróleo Crude Oil", "Preço/Taxa": f"US$ {oil.get('preco', 0.0):,.2f}", "Variação": f"{oil.get('variacao_pct', 0.0):+.2f}%"},
        {"Indicador": "Minério de Ferro", "Preço/Taxa": f"US$ {iron.get('preco', 0.0):,.2f}", "Variação": f"{iron.get('variacao_pct', 0.0):+.2f}%"},
        {"Indicador": "VIX (Volatilidade)", "Preço/Taxa": f"{vix.get('preco', 0.0):,.2f}", "Variação": f"{vix.get('variacao_pct', 0.0):+.2f}%"},
    ]
    st.table(pd.DataFrame(linhas_global).set_index("Indicador"))

# ---- Bloco Taxa de Juros ----
with tab_juros:
    st.markdown("#### 📉 Curva de Juros e Câmbio")
    dxy = contexto.get("dxy", {})
    usd_brl = contexto.get("usd_brl", {})
    
    linhas_juros = [
        {"Indicador": "Índice DXY (Dólar Global)", "Preço/Taxa": f"{dxy.get('preco', 0.0):,.3f}", "Variação": f"{dxy.get('variacao_pct', 0.0):+.2f}%"},
        {"Indicador": "USD/BRL Spot (TV)", "Preço/Taxa": f"R$ {usd_brl.get('preco', 0.0):,.4f}", "Variação": f"{usd_brl.get('variacao_pct', 0.0):+.2f}%"},
        {"Indicador": "USD PTAX Oficial", "Preço/Taxa": f"R$ {contexto.get('usd_ptax', 0.0):,.4f}", "Variação": "—"},
        {"Indicador": "DI1 Futuro 2027", "Preço/Taxa": f"{contexto.get('di1_2027', 0.0):,.2f}%", "Variação": "—"},
        {"Indicador": "DI1 Futuro 2029", "Preço/Taxa": f"{contexto.get('di1_2029', 0.0):,.2f}%", "Variação": "—"},
        {"Indicador": "Inclinação da Curva", "Preço/Taxa": f"{contexto.get('inclinacao_bps', 0.0):+.1f} bps", "Variação": "—"}
    ]
    st.table(pd.DataFrame(linhas_juros).set_index("Indicador"))

# ---- Bloco Cesta de ADRs ----
with tab_adrs:
    st.markdown("#### 🏢 Performance de ADRs em NY")
    vale = contexto.get("vale", {})
    petr = contexto.get("petr", {})
    itub = contexto.get("itub", {})
    bbd = contexto.get("bbd", {})
    bbas = contexto.get("bbas", {})
    
    linhas_adrs = [
        {"ADR de Referência": "VALE (Vale)", "Cotação": f"US$ {vale.get('preco', 0.0):,.2f}", "Variação": f"{vale.get('variacao_pct', 0.0):+.2f}%"},
        {"ADR de Referência": "PBR (Petrobras)", "Cotação": f"US$ {petr.get('preco', 0.0):,.2f}", "Variação": f"{petr.get('variacao_pct', 0.0):+.2f}%"},
        {"ADR de Referência": "ITUB (Itaú Unibanco)", "Cotação": f"US$ {itub.get('preco', 0.0):,.2f}", "Variação": f"{itub.get('variacao_pct', 0.0):+.2f}%"},
        {"ADR de Referência": "BBD (Bradesco)", "Cotação": f"US$ {bbd.get('preco', 0.0):,.2f}", "Variação": f"{bbd.get('change_percent', bbd.get('variacao_pct', 0.0)):+.2f}%"},
        {"ADR de Referência": "BDORY (Banco do Brasil)", "Cotação": f"US$ {bbas.get('preco', 0.0):,.2f}", "Variação": f"{bbas.get('variacao_pct', 0.0):+.2f}%"},
    ]
    st.table(pd.DataFrame(linhas_adrs).set_index("ADR de Referência"))

st.markdown("---")

# ============================================================
# SEÇÃO 3: AUDITORIA DO MOTOR DE CONFLUÊNCIA DE SINAIS
# ============================================================
st.markdown("### 🗳️ Matriz de Confluência e Votos do Orquestrador")
confluence = dados_v2.get("confluence", {})
votos = confluence.get("votos", {})

cv1, cv2 = st.columns(2)

with cv1:
    st.markdown("**Distribuição de Peso dos Modelos (Votos Brutos):**")
    for k, v in votos.items():
        st.markdown(f"• **Força Institucional de {k}:** `{v:.2f}` pontos de confluência.")

with cv2:
    st.markdown("**Comportamentos Probabilísticos de Abertura:**")
    comportamentos = cenario_resumo.get("comportamentos", {})
    if comportamentos:
        for k, v in comportamentos.items():
            nome_comportamento = k.replace("_", " ").title()
            st.markdown(f"• {nome_comportamento} : `{v:.1f}%` de probabilidade estatística.")
