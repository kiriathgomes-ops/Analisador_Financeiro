# -*- coding: utf-8 -*-
"""
Módulo: pages/3.3_📊_Acoes_e_ADRs.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Dashboard de correlação e performance relativa entre Ações B3 e ADRs em Nova York
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# Importações de caminhos padronizados do config.py da V2
from config import FILE_UNIFICADO, FILE_METRICAS, MAPEAMENTO_ADR_B3

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Ações e ADRs", layout="wide")

# --- CARGA DE DADOS DO BACKEND V2 ---
dados_unificados = carregar_json_defensivo(FILE_UNIFICADO)
dados_metricas = carregar_json_defensivo(FILE_METRICAS)

st.markdown("<h2 style='color:#00d4ff;'>📊 Correlação de Performance: B3 vs ADRs NY</h2>", unsafe_allow_html=True)
st.caption(f"Dados atualizados via pipeline quantitativo em: {dados_unificados.get('metadata', {}).get('timestamp', 'N/A')}")

# --- SEÇÃO 1: METRICAS COMPOSTAS E FLUXO GERAL ---
st.markdown("### 🏦 Termômetro Estatístico de Fluxo Estrangeiro")
ind_compostos = dados_metricas.get("indicadores_compostos", {})
ind_adrs = ind_compostos.get("indicador_adrs_brasileiras")
ind_externo = ind_compostos.get("indicador_mercado_externo")

c1, c2, c3 = st.columns(3)

# Indicador de ADRs (Soma/Média das variações das ADRs Brasileiras)
if ind_adrs is not None:
    c1.metric(
        label="Indicador Composto ADRs BR", 
        value=f"{ind_adrs:+.2f}%",
        delta="Fluxo Comprador" if ind_adrs > 0.5 else ("Fluxo Vendedor" if ind_adrs < -0.5 else "Estável"),
        delta_color="normal" if abs(ind_adrs) > 0.5 else "off"
    )
else:
    c1.metric(label="Indicador Composto ADRs BR", value="Aguardando dados...")

# Indicador de Mercado Externo (VIX, Petróleo, Minério combinados)
if ind_externo is not None:
    c2.metric(
        label="Indicador de Mercado Externo", 
        value=f"{ind_externo:+.2f}%",
        delta="Favorável ao Risco" if ind_externo > 0 else "Aversão ao Risco",
        delta_color="normal"
    )
else:
    c2.metric(label="Indicador de Mercado Externo", value="Aguardando dados...")

# ETF EWZ (Fundo de índice do Brasil negociado em NY)
ewz_pct = dados_metricas.get("performance_relativa", {}).get("ewz_change_pct", 0.0)
if ewz_pct is not None:
    c3.metric(
        label="EWZ (ETF Brasil em NY)", 
        value=f"{ewz_pct:+.2f}%",
        delta_color="off"
    )

st.markdown("---")

# --- SEÇÃO 2: TABELA DE COMPARAÇÃO PARALELA INDIVIDUAIZADA ---
st.markdown("### 🔍 Desempenho Setorial Lado a Lado")
st.caption("Cruzamento analítico entre a variação do papel local na B3 (via MT5) vs sua ADR correspondente (via Finnhub)")

ativos_unificados = dados_unificados.get("ativos", {})
perf_relativa = dados_metricas.get("performance_relativa", {})
adrs_brasileiras = perf_relativa.get("adrs_brasileiras", {})

# Mapeamento local inverso para construir a tabela de forma organizada
# Chave: Ticker B3 | Valor: ID da ADR no dicionário de métricas
MAPEAMENTO_TABELA = {
    "VALE3": "VALE_ADR",
    "PETR4": "PETR_ADR",
    "ITUB4": "ITUB_ADR",
    "BBAS3": "BBAS_ADR",
    "BBDC4": "BBD_ADR",
}

linhas_tabela = []

for ticker_b3, id_adr in MAPEAMENTO_TABELA.items():
    if ticker_b3 in ativos_unificados and id_adr in adrs_brasileiras:
        info_b3 = ativos_unificados[ticker_b3]
        info_adr = adrs_brasileiras[id_adr]
        
        var_b3 = info_b3.get("variacao_pct", 0.0)
        var_adr = info_adr.get("change_percent", 0.0)
        preco_adr = info_adr.get("close", 0.0)
        preco_b3 = info_b3.get("preco", 0.0)
        
        # Descolamento Relativo = Performance NY - Performance Local
        descolamento = var_adr - var_b3
        
        if descolamento > 0.4:
            status = "🔺 ADR puxando (Viés de Alta na abertura local)"
        elif descolamento < -0.4:
            status = "🔻 B3 esticada (Viés de Baixa / Realização local)"
        else:
            status = "⚖️ Arbitragem em Equilíbrio"
            
        linhas_tabela.append({
            "Ativo B3": ticker_b3,
            "Cotação B3": f"R$ {preco_b3:,.2f}",
            "Var B3": f"{var_b3:+.2f}%",
            "ADR NY": id_adr.replace("_ADR", ""),
            "Cotação ADR": f"US$ {preco_adr:,.2f}",
            "Var ADR": f"{var_adr:+.2f}%",
            "Descolamento": f"{descolamento:+.2f}%",
            "Diagnóstico": status
        })

if linhas_tabela:
    df_setorial = pd.DataFrame(linhas_tabela)
    st.dataframe(df_setorial.set_index("Ativo B3"), use_container_width=True)
else:
    st.warning("⚠️ Suporte de ativos incompleto nos arquivos do pipeline para montar a matriz setorial.")

st.markdown("---")
st.markdown("💡 **Nota de Trading:** Grandes descolamentos (maiores que ±0.50%) em papéis de alta liquidez como VALE3 e PETR4 costumam ser fechados rapidamente por robôs de arbitragem institucionais de alta frequência nas primeiras horas do pregão à vista brasileiro.")
