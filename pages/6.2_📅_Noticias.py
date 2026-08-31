# -*- coding: utf-8 -*-
"""
Módulo: pages/6.2_📅_Noticias.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar o calendário econômico do dia e os alertas de impacto/travas gerados pelo pipeline.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
from config import FILE_NOTICIAS_IMPACTO  # Caminho centralizado da V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Calendário Econômico", layout="wide")

# --- CARGA DOS DADOS DE IMPACTO V2 ---
dados_noticias = carregar_json_defensivo(FILE_NOTICIAS_IMPACTO)

st.markdown("<h2 style='color:#00d4ff;'>📅 Calendário Econômico e Impacto Macro</h2>", unsafe_allow_html=True)
st.caption(f"Análise quantitativa de risco gerada pelo pipeline | Auditoria: {dados_noticias.get('metadata', {}).get('timestamp', 'N/A')}")

if not dados_noticias:
    st.warning("⚠️ Arquivo de impacto de notícias não encontrado. Certifique-se de que o pipeline (Analise_Noticias.py) foi executado com sucesso.")
    st.stop()

resumo = dados_noticias.get("resumo", {})
alertas = dados_noticias.get("alertas", {})
impacto_total = resumo.get("impacto_total", 0)
classificacao = resumo.get("classificacao", "BAIXO")

# --- PAINEL DE METRICAS E ALERTAS OPERACIONAIS ---
c1, c2, c3 = st.columns(3)
c1.metric("Pontuação de Impacto Global", f"{impacto_total} pts", delta=f"Risco: {classificacao}")

# Alerta de Risco para a Abertura do Mini Índice (WIN)
risco_win = alertas.get("risco_abertura_WIN", False)
if risco_win or impacto_total >= 10:
    c2.markdown("<div style='background-color:rgba(255, 107, 107, 0.15); padding:10px; border-radius:8px; border:1px solid #ff6b6b; text-align:center; height:100%;'><span style='color:#ff6b6b; font-weight:bold; font-size:1.1rem;'>⚠️ ALERTA: RISCO ELEVADO</span><br><span style='font-size:0.85rem; color:#ccc;'>Janela de Abertura do WIN instável.</span></div>", unsafe_allow_html=True)
else:
    c2.markdown("<div style='background-color:rgba(0, 255, 136, 0.1); padding:10px; border-radius:8px; border:1px solid #00ff88; text-align:center; height:100%;'><span style='color:#00ff88; font-weight:bold; font-size:1.1rem;'>🟢 ABERTURA LIBERADA</span><br><span style='font-size:0.85rem; color:#ccc;'>Sem volatilidade abusiva nas notícias.</span></div>", unsafe_allow_html=True)

# Trava do leilão das 09:00h
trava_0900 = alertas.get("tem_3_estrelas_brasil_0900", False)
if trava_0900:
    c3.markdown("<div style='background-color:rgba(255, 170, 0, 0.15); padding:10px; border-radius:8px; border:1px solid #ffaa00; text-align:center; height:100%;'><span style='color:#ffaa00; font-weight:bold; font-size:1.1rem;'>🚨 TRAVA OPERACIONAL CRÍTICA</span><br><span style='font-size:0.85rem; color:#ccc;'>Notícia BRL 3 Estrelas às 09:00h.</span></div>", unsafe_allow_html=True)
else:
    c3.markdown("<div style='background-color:#161b24; padding:10px; border-radius:8px; border:1px solid #2a3a4a; text-align:center; height:100%;'><span style='color:#8b949e; font-weight:bold; font-size:1.1rem;'>🟢 SEM TRAVA 09:00H</span><br><span style='font-size:0.85rem; color:#ccc;'>Abertura livre de IPCA/PIB institucional.</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- EXIBIÇÃO DE ADVERTÊNCIAS ESPECÍFICAS ---
if alertas.get("tem_3_estrelas_outros_horarios", False):
    st.markdown("**🚨 Eventos de 3 Estrelas (Alto Impacto) Agendados para Hoje:**")
    for item in alertas.get("noticias_3_estrelas_outros_horarios", []):
        st.error(f"• **Horário: {item['hora']}** | [{item['moeda']}] {item['pais']} - *{item['evento']}*")
        
if alertas.get("tem_multiplas_2_estrelas_mesmo_horario", False):
    st.markdown("**⚠️ Concentração de Notícias de Médio Impacto (2 Estrelas):**")
    for item in alertas.get("horarios_multiplas_2_estrelas", []):
        st.warning(f"• **Horário: {item['hora']}** acumula `{item['quantidade_2_estrelas']}` eventos simultâneos de 2 estrelas. Potencial de volatilidade combinada.")

st.markdown("---")

# --- GRADE COMPLETA DO CRONOGRAMA ECONÔMICO ---
st.markdown("### 📋 Agenda Cronológica do Pregão")
horarios_data = dados_noticias.get("horarios", [])

linhas_tabela = []
for h_bloco in horarios_data:
    hora = h_bloco.get("hora", "N/A")
    pontos_hora = h_bloco.get("pontuacao", 0)
    risco_hora = h_bloco.get("classificacao", "BAIXO")
    
    for evento in h_bloco.get("eventos", []):
        linhas_tabela.append({
            "Horário (BR)": hora,
            "Moeda / País": f"[{evento.get('moeda')}] {evento.get('pais')}",
            "Evento Econômico": evento.get("nome"),
            "Peso Quant": evento.get("peso", 0),
            "Importância": "⭐" * evento.get("estrelas", 1),
            "Risco do Bloco Horário": f"{pontos_hora} pts ({risco_hora})"
        })

if linhas_tabela:
    df_noticias = pd.DataFrame(linhas_tabela)
    # Ordena cronologicamente pelo horário
    df_noticias = df_noticias.sort_values(by="Horário (BR)")
    st.dataframe(df_noticias.set_index("Horário (BR)"), use_container_width=True)
else:
    st.info("🟢 Nenhuma notícia de médio ou alto impacto agendada para o dia de hoje.")
