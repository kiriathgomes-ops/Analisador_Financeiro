# ============================================================
# ARQUIVO: pages/5_⚙️_Core_Engine.py
#
# MOTIVO:
# Visualização do Core Engine
# Decisão Quantitativa Final
#
# VERSÃO MELHORADA - Com decisão WIN/WDO separada
#
# ============================================================

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

import streamlit as st

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Core Engine - Quant Terminal",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS VISUAL MELHORADO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
    }

    .buy-box {
        background-color: #063b22;
        border: 2px solid #00ff88;
        padding: 25px;
        border-radius: 12px;
        text-align: center;
    }

    .sell-box {
        background-color: #420d12;
        border: 2px solid #ff4b4b;
        padding: 25px;
        border-radius: 12px;
        text-align: center;
    }

    .neutral-box {
        background-color: #1a1c23;
        border: 2px solid #ffc107;
        padding: 25px;
        border-radius: 12px;
        text-align: center;
    }

    .card-fator {
        background-color: #161b22;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 3px solid #7c5cfc;
        margin-bottom: 8px;
    }

    .card-fator .fator-tag {
        background: rgba(124, 92, 252, 0.15);
        color: #a78bfa;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        display: inline-block;
    }

    .info-box {
        background-color: #1a1c2a;
        border: 1px solid #2a2d3a;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.85rem;
        color: #cccccc;
        margin-top: 8px;
    }

    .score-high {
        color: #00c853;
        font-weight: bold;
    }
    .score-mid {
        color: #ffc107;
        font-weight: bold;
    }
    .score-low {
        color: #ff3d00;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

ARQUIVOS = {
    "decisao": os.path.join(COLETAS_DIR, "Decisao_Core.json"),
    "validacao": os.path.join(COLETAS_DIR, "Dados_Validados.json"),
    "noticias": os.path.join(COLETAS_DIR, "Noticias_Impacto_Dia.json"),
    "metricas": os.path.join(COLETAS_DIR, "Metricas_Calculadas.json"),
    "tendencias": os.path.join(COLETAS_DIR, "Analise_Tendencias.json"),
    "estimativa": os.path.join(COLETAS_DIR, "EstimativaAbertura.json"),
}

# ============================================================
# LEITOR JSON
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

decisao = carregar_json(ARQUIVOS["decisao"])
validacao = carregar_json(ARQUIVOS["validacao"])
noticias = carregar_json(ARQUIVOS["noticias"])
metricas = carregar_json(ARQUIVOS["metricas"])
tendencias = carregar_json(ARQUIVOS["tendencias"])
estimativa = carregar_json(ARQUIVOS["estimativa"])

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Core Engine")
st.sidebar.caption("Decisão Quantitativa Final")
st.sidebar.divider()

# Status dos dados
st.sidebar.markdown("### Status dos Dados")
for nome, caminho in ARQUIVOS.items():
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome.capitalize()}")

st.sidebar.divider()

if st.sidebar.button("🔄 Atualizar", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# CABEÇALHO
# ============================================================

st.title("⚙️ Core Engine — Decisão Quantitativa")
st.caption("Resultado final gerado pelo Engine_Vies.py")

if not decisao:
    st.error("Decisao_Core.json não encontrado.")
    st.info("Execute primeiro: python main_pipeline.py")
    st.stop()

timestamp = decisao.get("metadata", {}).get("timestamp", "N/A")
st.info(f"⏱ Última decisão: {timestamp}")

# ============================================================
# ANÁLISE OPERACIONAL - WIN E WDO
# ============================================================

st.divider()
st.subheader("🎯 Decisão do Core Engine")

analise_op = decisao.get("analise_operacional", {})
win_core = analise_op.get("WIN_INDICE", {})
wdo_core = analise_op.get("WDO_DOLAR", {})

col1, col2 = st.columns(2)

# ============================================================
# WIN
# ============================================================
with col1:
    st.markdown("### 📈 Mini Índice (WIN)")
    
    win_vies = win_core.get("vies_final", "NEUTRO")
    win_score = win_core.get("score_numeric", 0)
    win_fatores = win_core.get("fatores_relevantes", [])
    
    # Define cor e classe
    if "COMPRA" in win_vies.upper():
        box_class = "buy-box"
        emoji = "🟢"
    elif "VENDA" in win_vies.upper():
        box_class = "sell-box"
        emoji = "🔴"
    else:
        box_class = "neutral-box"
        emoji = "🟡"
    
    # Força da decisão
    if abs(win_score) >= 4:
        forca_texto = "FORTE"
        forca_cor = "score-high"
    elif abs(win_score) >= 1.5:
        forca_texto = "MODERADA"
        forca_cor = "score-mid"
    else:
        forca_texto = "FRACA"
        forca_cor = "score-low"
    
    st.markdown(f"""
    <div class="{box_class}">
        <h2>{emoji} {win_vies}</h2>
        <h4>Score: <span class="{forca_cor}">{win_score:.2f}</span></h4>
        <p>Força: {forca_texto}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fatores
    if win_fatores:
        with st.expander("📋 Fatores relevantes"):
            for f in win_fatores:
                st.markdown(f"""
                <div class="card-fator">
                    <span class="fator-tag">Fator</span>
                    {f}
                </div>
                """, unsafe_allow_html=True)

# ============================================================
# WDO
# ============================================================
with col2:
    st.markdown("### 💵 Mini Dólar (WDO)")
    
    wdo_vies = wdo_core.get("vies_final", "NEUTRO")
    wdo_score = wdo_core.get("score_numeric", 0)
    wdo_fatores = wdo_core.get("fatores_relevantes", [])
    
    if "COMPRA" in wdo_vies.upper():
        box_class = "buy-box"
        emoji = "🟢"
    elif "VENDA" in wdo_vies.upper():
        box_class = "sell-box"
        emoji = "🔴"
    else:
        box_class = "neutral-box"
        emoji = "🟡"
    
    if abs(wdo_score) >= 4:
        forca_texto = "FORTE"
        forca_cor = "score-high"
    elif abs(wdo_score) >= 1.5:
        forca_texto = "MODERADA"
        forca_cor = "score-mid"
    else:
        forca_texto = "FRACA"
        forca_cor = "score-low"
    
    st.markdown(f"""
    <div class="{box_class}">
        <h2>{emoji} {wdo_vies}</h2>
        <h4>Score: <span class="{forca_cor}">{wdo_score:.2f}</span></h4>
        <p>Força: {forca_texto}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if wdo_fatores:
        with st.expander("📋 Fatores relevantes"):
            for f in wdo_fatores:
                st.markdown(f"""
                <div class="card-fator">
                    <span class="fator-tag">Fator</span>
                    {f}
                </div>
                """, unsafe_allow_html=True)

# ============================================================
# RESUMO DA DECISÃO
# ============================================================

st.divider()
st.subheader("📊 Resumo da Decisão")

# Tabela resumo
resumo_data = {
    "Ativo": ["WIN", "WDO"],
    "Viés": [win_vies, wdo_vies],
    "Score": [f"{win_score:.2f}", f"{wdo_score:.2f}"],
    "Força": [forca_texto, forca_texto],
}

st.dataframe(
    resumo_data,
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# TENDÊNCIA (se disponível)
# ============================================================

if tendencias:
    st.divider()
    st.subheader("📈 Análise de Tendência (Últimos 15min)")
    
    # Busca WIN_FUT
    win_tend = None
    for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
        if chave in tendencias:
            win_tend = tendencias[chave]
            break
    
    if win_tend:
        padrao = win_tend.get("padrao_comportamento", "N/A")
        var = win_tend.get("intervalo_5_para_0", {}).get("variacao_pct", 0)
        emoji = "🟢" if var > 0 else "🔴" if var < 0 else "🟡"
        
        st.markdown(f"""
        <div class="info-box">
            <b>WIN - Tendência:</b> {emoji} {padrao} ({var:+.2f}%)
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# ABERTURA TEÓRICA (referência)
# ============================================================

if estimativa:
    st.divider()
    st.subheader("📊 Referência de Abertura")
    
    win_est = estimativa.get("estimativas_abertura", {}).get("WIN_INDICE", {})
    wdo_est = estimativa.get("estimativas_abertura", {}).get("WDO_DOLAR", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "WIN Abertura Teórica",
            f"{win_est.get('abertura_teorica_pontos', 0):,.0f} pts",
            f"{win_est.get('variacao_teorica_pct', 0):+.2f}%"
        )
    
    with col2:
        st.metric(
            "WDO Abertura Teórica",
            f"{wdo_est.get('abertura_teorica_pontos', 0):,.2f} pts",
            f"{wdo_est.get('variacao_teorica_pct', 0):+.2f}%"
        )

# ============================================================
# MATRIZ DE DADOS (Auditoria)
# ============================================================

st.divider()
st.subheader("📊 Auditoria dos Dados")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Decisão",
        "✅" if decisao else "❌"
    )

with col2:
    st.metric(
        "Dados Validados",
        len(validacao.get("ativos_validados", []))
    )

with col3:
    st.metric(
        "Eventos Notícias",
        len(noticias.get("horarios", []))
    )

with col4:
    st.metric(
        "Métricas",
        len(metricas)
    )

# ============================================================
# JSON COMPLETO (para debug)
# ============================================================

st.divider()
with st.expander("📄 Visualizar JSON Completo do Core"):
    st.json(decisao)

# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.caption("Analisador Financeiro - Core Engine Quant v2.0")