# -*- coding: utf-8 -*-
"""
Módulo: pages/6.1_🔬_Analise_Tendencia.py
Versão: 2.10 - Limpeza Definitiva (Sem colunas auxiliares, lógica baseada na própria UI)
Objetivo: Renderizar a análise de tendência sequencial (10m ➔ 5m ➔ 0m) categorizada e estilizada.
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

drivers_win = ["WIN_FUT", "CME_MINI:ES1!", "AMEX:EWZ", "VALE3", "PETR4", "BMFBOVESPA:DI1F2029"]

cols = st.columns(len(drivers_win))

for idx, ativo in enumerate(drivers_win):
    with cols[idx]:
        if ativo in dados_tendencias:
            info = dados_tendencias[ativo]
            padrao = info.get("padrao_comportamento", "Estavel_E_Estavel")
            var_atual = info.get("intervalo_5_para_0", {}).get("variacao_pct", 0.0)
            
            nome_exibicao = ativo.replace("CME_MINI:", "").replace("AMEX:", "").replace("BMFBOVESPA:", "")
            
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

# --- SEÇÃO 2: GRADE GERAL SEPARADA POR TIPO DE ATIVO ---
st.markdown("### 📋 Grade Geral de Rotação de Memória Temporal (Por Categoria)")
st.caption("Histórico milimétrico categorizado com cores calibradas pelo impacto direto ou inverso no WINFUT")

TICKERS_EXCLUIDOS = ["WDO_LAST_TICK", "WIN_LAST_TICK"]

def categorizar_ativo(nome_ativo):
    n = nome_ativo.upper()
    if any(k in n for k in ["WIN", "WDO", "DI1", "PTAX"]):
        return "1. Futuros & Taxas B3"
    elif any(k in n for k in ["SP500", "NASDAQ", "VIX", "DXY", "ES1", "NQ1"]):
        return "2. Índices Globais & Câmbio"
    elif any(k in n for k in ["IRON", "CRUDE", "GOLD", "FEF", "CL1"]):
        return "3. Commodities & Metais"
    else:
        return "4. Ações & ADRs Brasileiras"

# Ativos de correlação inversa com o WIN
ATIVOS_INVERSOS = ["DXY", "VIX", "WDO", "USDBRL"]

categorias_dict = {}

for ativo, info in dados_tendencias.items():
    if ativo in TICKERS_EXCLUIDOS:
        continue
        
    cat = categorizar_ativo(ativo)
    if cat not in categorias_dict:
        categorias_dict[cat] = []
        
    precos = info.get("precos", {})
    int_10_5 = info.get("intervalo_10_para_5", {})
    int_5_0 = info.get("intervalo_5_para_0", {})
    
    nome_limpo = ativo.split(":")[-1] if ":" in ativo else ativo
    padrao = info.get("padrao_comportamento", "Estavel_E_Estavel")
    
    if "Alta_E_Alta" in padrao:
        padrao_formatado = "🚀 Alta Contínua"
    elif "Baixa_E_Baixa" in padrao:
        padrao_formatado = "📉 Queda Contínua"
    elif "Baixa" in padrao.split("_E_")[0] and "Alta" in padrao.split("_E_")[1]:
        padrao_formatado = "🔄 Reversão p/ Alta"
    elif "Alta" in padrao.split("_E_")[0] and "Baixa" in padrao.split("_E_")[1]:
        padrao_formatado = "⚠️ Perda de Momento"
    else:
        padrao_formatado = f"⚖️ {padrao.replace('_E_', ' ➔ ')}"
    
    # Adicionamos direto o DataFrame limpo sem colunas ocultas
    categorias_dict[cat].append({
        "Ativo": nome_limpo,
        "Preço 10m": precos.get('10m', 0.0) if precos.get('10m') else 0.0,
        "Preço 5m": precos.get('5m', 0.0) if precos.get('5m') else 0.0,
        "Preço Atual (0m)": precos.get('0m', 0.0) if precos.get('0m') else 0.0,
        "Var. 10m ➔ 5m (%)": int_10_5.get('variacao_pct', 0.0),
        "Var. 5m ➔ Atual (%)": int_5_0.get('variacao_pct', 0.0),
        "Padrão Dinâmico": padrao_formatado
    })

# Renderização organizada de todas as tabelas na página
for categoria in sorted(categorias_dict.keys()):
    st.markdown(f"#### **{categoria}**")
    linhas = categorias_dict[categoria]
    df_cat = pd.DataFrame(linhas)
    
    def colorir_impacto_win(row):
        estilos = [''] * len(row)
        nome_ativo = row["Ativo"].upper()
        padrao_txt = row["Padrão Dinâmico"]
        is_inverso = any(inv in nome_ativo for inv in ATIVOS_INVERSOS)
        
        for idx, col_name in enumerate(row.index):
            # Colunas de Variação
            if "Var." in col_name:
                val = row[col_name]
                if isinstance(val, (int, float)):
                    if val > 0:
                        cor = '#ff6b6b' if is_inverso else '#00ff88'
                        estilos[idx] = f'color: {cor}; font-weight: bold;'
                    elif val < 0:
                        cor = '#00ff88' if is_inverso else '#ff6b6b'
                        estilos[idx] = f'color: {cor}; font-weight: bold;'
            
            # Coluna de Padrão Dinâmico (pintada com base no texto exibido)
            elif col_name == "Padrão Dinâmico":
                if "Alta Contínua" in padrao_txt or "Reversão p/ Alta" in padrao_txt:
                    cor = '#ff6b6b' if is_inverso else '#00ff88'
                    estilos[idx] = f'color: {cor}; font-weight: bold;'
                elif "Queda Contínua" in padrao_txt:
                    cor = '#00ff88' if is_inverso else '#ff6b6b'
                    estilos[idx] = f'color: {cor}; font-weight: bold;'
                    
        return estilos

    # Aplica o estilo diretamente sobre o dataframe final limpo
    df_estilizado = df_cat.style.apply(colorir_impacto_win, axis=1).format({
        "Preço 10m": "{:,.3f}",
        "Preço 5m": "{:,.3f}",
        "Preço Atual (0m)": "{:,.3f}",
        "Var. 10m ➔ 5m (%)": "{:+.3f}%",
        "Var. 5m ➔ Atual (%)": "{:+.3f}%"
    })
    
    st.dataframe(
        df_estilizado, 
        use_container_width=True, 
        hide_index=True
    )
    st.markdown("")