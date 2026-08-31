# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Imagem.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar os insights de Smart Money gerados pela Visão Computacional (IA) sobre os gráficos do WIN.
"""

import streamlit as st
import json
from pathlib import Path

# Importação de caminhos centralizados do config.py da V2
from config import COLETAS_DIR, FILE_WIN_5MIN

# Definição do caminho do arquivo de resultado da Visão IA
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

st.markdown("<h2 style='color:#00d4ff;'>🤖 IA Spike Imagem — Visão Computacional SMC</h2>", unsafe_allow_html=True)
st.caption("Auditoria de insights e estruturas gráficas extraídas por modelos de visão em background")

st.info("💡 **Arquitetura V2:** Para mitigar latência na UI, o processamento de imagem é executado de forma assíncrona pelo backend. Esta tela exibe o último snapshot auditado.")

# --- CARGA DOS RESULTADOS DA VISÃO IA ---
dados_visao = carregar_json_defensivo(FILE_SMC_VISAO_IA)

# --- DIVISION DESIGN: IMAGEM VS TEXTO DA IA ---
col_grafico, col_insights = st.columns([1.2, 1], gap="large")

with col_grafico:
    st.markdown("### 📈 Gráfico Analisado (MT5 / TradingView)")
    
    # Exibe a imagem física que o backend enviou para a IA
    if FILE_WIN_5MIN.exists():
        st.image(str(FILE_WIN_5MIN), caption="WIN_5min.png — Captura utilizada na última janela analítica", use_container_width=True)
    else:
        st.warning("⚠️ Arquivo físico de imagem 'WIN_5min.png' não encontrado na pasta Coletas/. Execute o script de limpeza/captura.")
        # Fallback visual caso a imagem não exista
        st.markdown(
            "<div style='background-color:#161b24; padding:60px 20px; text-align:center; border-radius:8px; border:1px solid #2a3a4a; color:#8b949e;'>"
            "📊 Aguardando nova captura de tela do gráfico do Mini Índice."
            "</div>", 
            unsafe_allow_html=True
        )

with col_insights:
    st.markdown("### 🧠 Diagnóstico de Estruturas (Leitura da IA)")
    
    if not dados_visao:
        st.error("❌ Erro: O arquivo 'AnaliseGraficaSMC.json' não foi encontrado ou está corrompido. O motor contextual de visão precisa ser executado pelo Orquestrador V2.")
    else:
        # Exibição do Viés Computacional Interpretado pelo Modelo
        bias_ia = dados_visao.get("bias_direcional", "NEUTRO / LATERAL")
        tf_identificado = dados_visao.get("timeframes_identificados", "Não Mapeado")
        
        st.markdown(f"**Timeframe Detectado pela IA:** `{tf_identificado}`")
        
        if "COMPRA" in bias_ia.upper() or "BULL" in bias_ia.upper() or "ALTA" in bias_ia.upper():
            st.success(f"Viés da IA: {bias_ia}")
        elif "VENDA" in bias_ia.upper() or "BEAR" in bias_ia.upper() or "BAIXA" in bias_ia.upper():
            st.error(f"Viés da IA: {bias_ia}")
        else:
            st.warning(f"Viés da IA: {bias_ia}")
            
        st.markdown("---")
        
        # 1. Renderização das Estruturas Coletadas Textualmente
        st.markdown("**Níveis e Blocos de Preço Identificados no Gráfico:**")
        estruturas = dados_visao.get("estruturas_coletadas", [])
        if estruturas:
            for est in estruturas:
                st.markdown(f"• {est}")
        else:
            st.caption("Nenhum nível estrutural extraído textualmente neste snapshot.")
            
        st.markdown("---")
        
        # 2. Piscinas de Liquidez Mapeadas Visualmente
        st.markdown("**Mapeamento de Liquidez (Zonas de Caça):**")
        liquidez = dados_visao.get("liquidez_relevante", [])
        if liquidez:
            for liq in liquidez:
                st.markdown(f"🎯 {liq}")
        else:
            st.caption("Nenhuma piscina de liquidez expressiva apontada pelo modelo de visão.")
            
        st.markdown("---")
        
        # 3. Cenários Operacionais Sugeridos pela IA
        st.markdown("**Mapeamento de Cenários para o Pregão:**")
        cenarios = dados_visao.get("zonas_de_interesse_e_cenarios", [])
        if cenarios:
            for idx, cenario in enumerate(cenarios, start=1):
                st.markdown(f"**{idx}.** *{cenario}*")
        else:
            st.caption("Sem cenários preditivos gerados para esta janela de preço.")
