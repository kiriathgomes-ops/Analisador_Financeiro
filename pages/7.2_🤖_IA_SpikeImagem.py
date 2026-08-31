# -*- coding: utf-8 -*-
"""
Módulo: pages/7.2_🤖_IA_SpikeImagem.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar a análise de anomalias visuais e Spikes institucionais no tempo gráfico de 1min.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Importação de caminhos centralizados do config.py da V2
from config import COLETAS_DIR, FILE_WIN_1MIN, FILE_SMC_REGRAS

# Definição do caminho do arquivo de resultado da Visão IA (Mapeado via ecossistema)
FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - IA Spike Imagem", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🤖 IA Spike Imagem — Detecção de Anomalias LTF</h2>", unsafe_allow_html=True)
st.caption("Monitoramento quantitativo de picos de volume e volatilidade no tempo gráfico de 1 Minuto (LTF)")

st.info("⚡ **Módulo de Volatilidade:** Esta tela monitora movimentos abruptos (Spikes) e desequilíbrios de curtíssimo prazo capturados em background pelo pipeline V2.")

# --- CARGA DOS DADOS DE SUPORTE V2 ---
dados_visao = carregar_json_defensivo(FILE_SMC_VISAO_IA)
dados_smc_regras = carregar_json_defensivo(FILE_SMC_REGRAS)

# --- DIVISION DESIGN: GRÁFICO DE 1MIN VS DIAGNÓSTICO DE SPIKE ---
col_grafico, col_insights = st.columns([1.2, 1], gap="large")

with col_grafico:
    st.markdown("### 📉 Gráfico de Execução Rápida (WIN 1 Minuto)")
    
    # Exibe a imagem do gráfico de 1 minuto para o trader auditar o Spike visualmente
    if FILE_WIN_1MIN.exists():
        st.image(str(FILE_WIN_1MIN), caption="WIN_1min.png — Captura de momentum e fluxo em tempo real", use_container_width=True)
    else:
        st.warning("⚠️ Imagem 'WIN_1min.png' não encontrada na pasta Coletas/. Executando carregamento defensivo.")
        st.markdown(
            "<div style='background-color:#161b24; padding:60px 20px; text-align:center; border-radius:8px; border:1px solid #2a3a4a; color:#8b949e;'>",
            unsafe_allow_html=True
        )
        st.markdown("Aguardando nova captura de anomalia visual pelo orquestrador.")
        st.markdown("</div>", unsafe_allow_html=True)

with col_insights:
    st.markdown("### 🚨 Diagnóstico de Momentum e Fluxo")
    
    # KPIs Rápidos do Motor de Regras LTF
    preco_atual = dados_smc_regras.get("preco_atual", 0.0)
    bias_ltf = dados_smc_regras.get("bias_direcional", "NEUTRO")
    confianca_ltf = dados_smc_regras.get("confianca_visual", 0)
    
    c1, c2 = st.columns(2)
    c1.metric("Preço de Tela (WIN)", f"{preco_atual:,.0f} pts")
    
    if bias_ltf == "ALTA":
        c2.markdown("<div style='background-color:rgba(0, 255, 136, 0.1); padding:8px; border-radius:6px; text-align:center; border:1px solid #00ff88;'><span style='font-size:0.85rem; color:#ccc;'>MOMENTUM LTF</span><br><b style='color:#00ff88; font-size:1.1rem;'>🐂 COMPRA ACELERADA</b></div>", unsafe_allow_html=True)
    elif bias_ltf == "BAIXA":
        c2.markdown("<div style='background-color:rgba(255, 107, 107, 0.1); padding:8px; border-radius:6px; text-align:center; border:1px solid #ff6b6b;'><span style='font-size:0.85rem; color:#ccc;'>MOMENTUM LTF</span><br><b style='color:#ff6b6b; font-size:1.1rem;'>Bearish / Venda Forte</b></div>", unsafe_allow_html=True)
    else:
        c2.markdown("<div style='background-color:rgba(255, 255, 255, 0.05); padding:8px; border-radius:6px; text-align:center; border:1px solid #888;'><span style='font-size:0.85rem; color:#ccc;'>MOMENTUM LTF</span><br><b style='color:#ccc; font-size:1.1rem;'>⚖️ Acumulação / Range</b></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Cruzamento com os metadados do motor para validar se houve Vela de Expansão (Inbalance Real)
    meta_regras = dados_smc_regras.get("metadados", {})
    filtro_vol = meta_regras.get("filtro_volume_aplicado", False)
    
    st.markdown("**Auditoria do Motor Contextual (Filtro Institucional):**")
    if filtro_vol:
        st.success("✅ **Filtro de Deslocamento de Volume Ativo:** O movimento atual foi validado acima da média móvel institucional (Vela de Expansão Realizada).")
    else:
        st.info("⚖️ **Volume Normal:** Oscilação dentro da média aritmética. Sem atuação de grandes lotes (ruído de varejo).")
        
    st.markdown("---")
    
    # Exibição dos Eventos de Estrutura de Curto Prazo (LTF) capturados
    st.markdown("**Últimos Eventos de Estrutura Registrados (LTF):**")
    eventos_est = dados_smc_regras.get("eventos_structure", [])
    
    if eventos_est:
        linhas_eventos = []
        for ev in eventos_est[-4:]:  # Exibe os 4 mais recentes para não poluir
            linhas_eventos.append({
                "Horário": ev.get("time", "N/A")[-8:],
                "Evento": f"⚠️ {ev.get('tipo')}" if ev.get('tipo') == "CHoCH" else f"🔷 {ev.get('tipo')}",
                "Direção": "🔼 ALTA" if ev.get("direcao") == "ALTA" else "🔽 BAIXA",
                "Preço": f"{ev.get('preco'):,.0f} pts"
            })
        df_ev = pd.DataFrame(linhas_eventos)
        st.table(df_ev.set_index("Horário"))
    else:
        st.caption("Sem quebras de estrutura (BOS/CHoCH) registradas no histórico recente de 1min.")
