# -*- coding: utf-8 -*-
"""
Módulo: pages/6.1_🔬_Analise_Tendencia.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar a análise de tendência sequencial (10m ➔ 5m ➔ 0m) dos ativos do ecossistema.
"""

import streamlit as st
import json
import pandas as pd
from config import FILE_TENDENCIAS  # Importação centralizada do config V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Análise de Tendência", layout="wide")

# --- CARGA DOS DADOS V2 ---
dados_tendencias = carregar_json_defensivo(FILE_TENDENCIAS)

st.markdown("<h2 style='color:#00d4ff;'>🔬 Análise Cíclica de Tendência (Janela Móvel)</h2>", unsafe_allow_html=True)
st.caption("Mapeamento sequencial de variação de preços a cada 5 minutos (10m ➔ 5m ➔ Atual)")

if not dados_tendencias:
    st.warning("⚠️ Arquivo de tendências não encontrado ou vazio. Certifique-se de que o pipeline rodou a rotação temporal (rodar_pipeline_3x.bat).")
    st.stop()

# --- SEÇÃO 1: OS MAIORES DRIVERS DO MINI ÍNDICE (WIN) ---
st.markdown("### 🎯 Direcionadores Críticos do WIN")
st.caption("Acompanhamento imediato dos ativos com maior peso de correlação com o Mini Índice")

# Lista ordenada de prioridade para o trade de índice
drivers_win = ["WIN_LAST_TICK", "CME_MINI:ES1!", "AMEX:EWZ", "VALE3", "PETR4", "BMFBOVESPA:DI1F2029"]

cols = st.columns(len(drivers_win))

for idx, ativo in enumerate(drivers_win):
    with cols[idx]:
        if ativo in dados_tendencias:
            info = dados_tendencias[ativo]
            padrao = info.get("padrao_comportamento", "Estavel_E_Estavel")
            var_atual = info.get("intervalo_5_para_0", {}).get("variacao_pct", 0.0)
            
            # Formatação visual amigável do nome para exibição na UI
            nome_exibicao = ativo.replace("CME_MINI:", "").replace("AMEX:", "").replace("BMFBOVESPA:", "")
            
            # Lógica de cor baseada no padrão de comportamento recente
            if "Alta_E_Alta" in padrao:
                cor_box = "rgba(0, 255, 136, 0.15)"
                border_color = "#00ff88"
                txt_status = "🚀 Forte Alta"
            elif "Baixa_E_Baixa" in padrao:
                cor_box = "rgba(255, 107, 107, 0.15)"
                border_color = "#ff6b6b"
                txt_status = "📉 Forte Baixa"
            elif "Alta" in padrao.split("_E_")[-1]:
                cor_box = "rgba(0, 212, 255, 0.1)"
                border_color = "#00d4ff"
                txt_status = "🔺 Recompondo"
            elif "Baixa" in padrao.split("_E_")[-1]:
                cor_box = "rgba(255, 170, 0, 0.1)"
                border_color = "#ffaa00"
                txt_status = "🔻 Corrigindo"
            else:
                cor_box = "rgba(255, 255, 255, 0.05)"
                border_color = "#888"
                txt_status = "⚖️ Estável"
                
            st.markdown(
                f"<div style='background-color:{cor_box}; padding:12px; border-radius:8px; border:1px solid {border_color}; text-align:center; height:100%;'>"
                f"<b style='font-size:1.1rem; color:#fff;'>{nome_exibicao}</b><br>"
                f"<span style='font-size:1.3rem; font-weight:bold;'>{var_atual:+.3f}%</span><br>"
                f"<span style='font-size:0.85rem; color:#ccc;'>{txt_status}</span>"
                f"</div>", 
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='text-align:center; padding:15px; color:#555;'>Falta Snapshot</div>", unsafe_allow_html=True)

st.markdown("---")

# --- SEÇÃO 2: MATRIZ COMPLETA DE DADOS EM TABELA (PANDAS) ---
st.markdown("### 📋 Grade Geral de Rotação de Memória Temporal")
st.caption("Histórico milimétrico de variação de preços coletados pelo pipeline")

linhas_tabela = []

for ativo, info in dados_tendencias.items():
    precos = info.get("precos", {})
    int_10_5 = info.get("intervalo_10_para_5", {})
    int_5_0 = info.get("intervalo_5_para_0", {})
    
    # Limpeza de nomes longos para a tabela ficar scannable
    nome_limpo = ativo.split(":")[-1] if ":" in ativo else ativo
    
    linhas_tabela.append({
        "Ativo": nome_limpo,
        "Preço 10m atrás": f"{precos.get('10m', 0.0):,.3f}" if precos.get('10m') else "—",
        "Preço 5m atrás": f"{precos.get('5m', 0.0):,.3f}" if precos.get('5m') else "—",
        "Preço Atual (0m)": f"{precos.get('0m', 0.0):,.3f}" if precos.get('0m') else "—",
        "Var. 10m ➔ 5m": f"{int_10_5.get('variacao_pct', 0.0):+.3f}%",
        "Var. 5m ➔ Atual": f"{int_5_0.get('variacao_pct', 0.0):+.3f}%",
        "Padrão Dinâmico": info.get("padrao_comportamento", "Estavel_E_Estavel").replace("_E_", " ➔ ")
    })

if linhas_tabela:
    df_tendencias = pd.DataFrame(linhas_tabela)
    # Exibe como dataframe Streamlit nativo ocupando a largura total
    st.dataframe(df_tendencias.set_index("Ativo"), use_container_width=True)
else:
    st.caption("Aguardando novas coletas do orquestrador para preencher a grade geral.")
