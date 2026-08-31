# -*- coding: utf-8 -*-
"""
Módulo: pages/21_📈_Historico_Macro.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Dashboard analítico de série temporal e histórico macro/operacional do WIN.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go

# Importação da constante de diretório configurada no config.py da V2
from config import HISTORICO_ABERTURAS_DIR

def carregar_json_defensivo(caminho_path):
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Histórico Macro", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>📊 Série Temporal e Histórico Macro Operacional</h2>", unsafe_allow_html=True)
st.caption("Análise estatística retroativa dos fechamentos, ajustes e cenários gravados pelo ecossistema V2")

# --- CENTRAL DE INGESTÃO DO HISTÓRICO FÍSICO V2 ---
if not HISTORICO_ABERTURAS_DIR.exists():
    st.warning("⚠️ Diretório de histórico de aberturas V2 não encontrado no disco local. Aguardando primeiras gravações do pregão.")
    st.stop()

# Varre os arquivos JSON salvos na pasta de histórico
arquivos_historicos = sorted(list(HISTORICO_ABERTURAS_DIR.glob("*.json")))

if not arquivos_historicos:
    st.info("ℹ️ Nenhuma sessão diária imutável foi persistida na pasta Historico_Aberturas/ ainda.")
    st.stop()

# Processamento em lote dos arquivos para montar a série temporal (Dataframe)
linhas_Série = []

for caminho in arquivos_historicos:
    # O nome do arquivo é a data da sessão (ex: 2026-08-30.json)
    data_sessao = caminho.stem
    
    dados_dia = carregar_json_defensivo(caminho)
    atualizacoes = dados_dia.get("atualizacoes", [])
    
    if atualizacoes and isinstance(atualizacoes, list):
        # Captura o último snapshot consolidado do dia (mais atual)
        ultimo_snapshot = atualizacoes[-1]
        
        precos = ultimo_snapshot.get("precos", {})
        distancias = ultimo_snapshot.get("distancias", {})
        cenario = ultimo_snapshot.get("cenario", {})
        contexto = ultimo_snapshot.get("contexto", {})
        
        # Injeta na lista de tuplas para consolidação do Pandas
        linhas_Série.append({
            "Data Sessão": data_sessao,
            "Contrato Principal": ultimo_snapshot.get("metadata", {}).get("contrato_principal", "WIN"),
            "Preço Ajuste B3": precos.get("ajuste"),
            "Último MT5 (Last)": precos.get("last_mt5"),
            "Desvio Ajuste (Pts)": distancias.get("last_vs_ajuste_pts"),
            "VIX (Volatilidade)": contexto.get("vix", {}).get("preco"),
            "Direção Cenário": cenario.get("direcao_provavel", "NEUTRO"),
            "Confiança (%)": cenario.get("confianca_geral", 0.0)
        })

# Converte a lista em Dataframe estruturado do Pandas
df_historico = pd.DataFrame(linhas_Série).sort_values(by="Data Sessão", ascending=False)

# --- RENDERIZAÇÃO DA VISÃO GRÁFICA INTERATIVA (PLOTLY) ---
st.markdown("### 📉 Curva Comparativa: Preço Last vs Ajuste Oficial B3")
st.caption("Monitore o comportamento histórico e o fechamento de spreads institucionais ao longo das sessões")

# Garante que temos dados numéricos para plotar
df_grafico = df_historico.sort_values(by="Data Sessão", ascending=True)

if not df_grafico.empty and df_grafico["Preço Ajuste B3"].notna().any():
    fig = go.Figure()
    
    # Linha do Ajuste
    fig.add_trace(go.Scatter(
        x=df_grafico["Data Sessão"], 
        y=df_grafico["Preço Ajuste B3"],
        mode="lines+markers",
        name="Preço de Ajuste Oficial B3",
        line=dict(color="orange", width=2)
    ))
    
    # Linha do Último Preço do MT5
    fig.add_trace(go.Scatter(
        x=df_grafico["Data Sessão"], 
        y=df_grafico["Último MT5 (Last)"],
        mode="lines+markers",
        name="Último Tick MetaTrader 5 (Last)",
        line=dict(color="#00d4ff", width=2, dash="dash")
    ))
    
    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Aguardando mais pontos históricos para plotar as curvas de tendência.")

st.markdown("---")

# --- CENTRAL DE DADOS: GRADE HISTÓRICA COMPLETA ---
st.markdown("### 📋 Histórico Consolidado de Snapshots da Mesa")
st.caption("Grade analítica contendo todas as variáveis gravadas em background pelo pipeline")

# Formata exibição da tabela Streamlit
st.dataframe(df_historico.set_index("Data Sessão"), use_container_width=True)

st.markdown("---")
st.caption("🔒 Módulo de inteligência histórica ativo — Em conformidade com o ecossistema de armazenamento imutável V2.")
