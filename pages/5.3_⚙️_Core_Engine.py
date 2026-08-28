# ============================================================
# ARQUIVO: pages/5.3_⚙️_Core_Engine.py
#
# MOTIVO:
# Visualização do Core Engine V2 (decisão oficial)
# Decisão Quantitativa Final – consumindo Decisao_V2.json
#
# VERSÃO: 2.0 (migração V1 → V2)
# DATA: 27/08/2026
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
    page_title="Core Engine V2 - Quant Terminal",
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

    .legado-banner {
        background: #3d2a10;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 10px 16px;
        color: #ffc107;
        font-size: 0.85rem;
        margin-bottom: 16px;
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
    "decisao_v2": os.path.join(COLETAS_DIR, "Decisao_V2.json"),      # <-- PRIORIDADE
    "decisao_v1": os.path.join(COLETAS_DIR, "Decisao_Core.json"),    # <-- apenas para referência
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

# ============================================================
# CARREGAR DADOS
# ============================================================

decisao_v2 = carregar_json(ARQUIVOS["decisao_v2"])
decisao_v1 = carregar_json(ARQUIVOS["decisao_v1"])  # apenas para referência
validacao = carregar_json(ARQUIVOS["validacao"])
noticias = carregar_json(ARQUIVOS["noticias"])
metricas = carregar_json(ARQUIVOS["metricas"])
tendencias = carregar_json(ARQUIVOS["tendencias"])
estimativa = carregar_json(ARQUIVOS["estimativa"])

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Core Engine V2")
st.sidebar.caption("Decisão Quantitativa Final (V2)")
st.sidebar.divider()

# Status dos dados
st.sidebar.markdown("### Status dos Dados")
for nome, caminho in ARQUIVOS.items():
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome.capitalize()}")

st.sidebar.divider()

if st.sidebar.button("🔄 Atualizar", width="stretch"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# CABEÇALHO
# ============================================================

st.title("⚙️ Core Engine — Decisão Quantitativa V2")
st.caption("Fonte oficial: Decisao_V2.json (motor V2)")

# Verifica se a V2 está disponível
if not decisao_v2:
    st.error("❌ Decisao_V2.json não encontrado. Execute o pipeline V2 primeiro.")
    st.info("💡 Rode: `python v2_rodar_decisao_completa.py`")
    st.stop()

timestamp = decisao_v2.get("metadata", {}).get("timestamp", "N/A")
st.info(f"⏱ Última decisão V2: {timestamp}")

# ============================================================
# BANNER DE DESCONTINUAÇÃO DA V1 (se disponível)
# ============================================================
if decisao_v1:
    st.markdown(
        """
        <div class="legado-banner">
            ⚠️ <b>Motor V1 (Core Engine) está descontinuado</b> – esta página exibe apenas a decisão V2.
            A V1 é mantida apenas para referência histórica.
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# DECISÃO V2 – DADOS PRINCIPAIS
# ============================================================

st.divider()
st.subheader("🎯 Decisão do Core Engine V2")

# Estrutura do V2: decisao_v2["decisao"] contém os campos principais
decisao_data = decisao_v2.get("decisao", {}) if isinstance(decisao_v2, dict) else {}

vies = decisao_data.get("vies_final", "NEUTRO")
confianca = decisao_data.get("confianca", 0)
entrada = decisao_data.get("entrada")
stop = decisao_data.get("stop_loss")
alvo1 = decisao_data.get("alvo_1")
alvo2 = decisao_data.get("alvo_2")
invalidacao = decisao_data.get("invalidacao", "N/A")
motivos = decisao_data.get("motivos", [])
riscos = decisao_data.get("riscos", [])

# Define cor e classe
if "COMPRA" in vies.upper() or vies.upper() in ("ALTA", "BULL"):
    box_class = "buy-box"
    emoji = "🟢"
elif "VENDA" in vies.upper() or vies.upper() in ("BAIXA", "BEAR"):
    box_class = "sell-box"
    emoji = "🔴"
else:
    box_class = "neutral-box"
    emoji = "🟡"

# Força da decisão (baseado na confiança)
if confianca >= 80:
    forca_texto = "FORTE"
    forca_cor = "score-high"
elif confianca >= 60:
    forca_texto = "MODERADA"
    forca_cor = "score-mid"
else:
    forca_texto = "FRACA"
    forca_cor = "score-low"

st.markdown(f"""
<div class="{box_class}">
    <h2>{emoji} {vies}</h2>
    <h4>Confiança: <span class="{forca_cor}">{confianca}%</span></h4>
    <p>Força: {forca_texto}</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# NÍVEIS OPERACIONAIS (entrada, stop, alvos)
# ============================================================

st.markdown("### 📊 Níveis Operacionais")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🎯 Entrada", f"{entrada:,.0f}" if entrada is not None else "—")

with col2:
    st.metric("🛑 Stop Loss", f"{stop:,.0f}" if stop is not None else "—")

with col3:
    st.metric("🎯 Alvo 1", f"{alvo1:,.0f}" if alvo1 is not None else "—")

with col4:
    st.metric("🎯 Alvo 2", f"{alvo2:,.0f}" if alvo2 is not None else "—")

if invalidacao:
    st.info(f"⚠️ **Invalidação:** {invalidacao}")

# ============================================================
# FATORES RELEVANTES E RISCOS (V2)
# ============================================================

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### ✅ Fatores que motivaram a decisão")
    if motivos:
        for m in motivos:
            st.markdown(f"""
            <div class="card-fator">
                <span class="fator-tag">Fator</span>
                {m}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Nenhum fator listado.")

with col2:
    st.markdown("#### ⚠️ Riscos identificados")
    if riscos:
        for r in riscos:
            st.markdown(f"""
            <div class="card-fator" style="border-left-color: #ff3d00;">
                <span class="fator-tag" style="background:rgba(255,61,0,0.15);color:#ff3d00;">Risco</span>
                {r}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Nenhum risco listado.")

# ============================================================
# MÉTRICAS E CONTEXTOS AUXILIARES (oriundos de outros JSONs)
# ============================================================

st.divider()
st.subheader("📈 Contexto e Métricas Auxiliares")

# Abertura teórica (da estimativa)
win_est = estimativa.get("estimativa_abertura", {}).get("WIN_INDICE", {})
wdo_est = estimativa.get("estimativa_abertura", {}).get("WDO_DOLAR", {})

col1, col2 = st.columns(2)
with col1:
    if win_est:
        st.metric(
            "WIN Abertura Teórica",
            f"{win_est.get('abertura_teorica_pontos', 0):,.0f} pts",
            f"{win_est.get('variacao_teorica_pct', 0):+.2f}%"
        )
with col2:
    if wdo_est:
        st.metric(
            "WDO Abertura Teórica",
            f"{wdo_est.get('abertura_teorica_pontos', 0):,.2f} pts",
            f"{wdo_est.get('variacao_teorica_pct', 0):+.2f}%"
        )

# Métricas macro (da Calculadora)
if metricas:
    indicadores = metricas.get("indicadores_compostos", {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "🌍 Mercado Externo",
            f"{indicadores.get('indicador_mercado_externo', 0):+.2f}%",
            "Compra" if indicadores.get('indicador_mercado_externo', 0) > 0 else "Venda" if indicadores.get('indicador_mercado_externo', 0) < 0 else "Neutro"
        )
    with col2:
        st.metric(
            "🇧🇷 ADRs Brasileiras",
            f"{indicadores.get('indicador_adrs_brasileiras', 0):+.2f}%",
            "Compra" if indicadores.get('indicador_adrs_brasileiras', 0) > 0 else "Venda" if indicadores.get('indicador_adrs_brasileiras', 0) < 0 else "Neutro"
        )

# Tendência (se disponível)
if tendencias:
    win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
    if win_tend:
        padrao = win_tend.get("padrao_comportamento", "N/A")
        var = win_tend.get("intervalo_5_para_0", {}).get("variacao_pct", 0)
        emoji_tend = "🟢" if var > 0 else "🔴" if var < 0 else "🟡"
        st.markdown(f"""
        <div class="info-box">
            <b>📈 Tendência WIN (15min):</b> {emoji_tend} {padrao} ({var:+.2f}%)
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# AUDITORIA – contexto de disponibilidade dos serviços V2
# ============================================================

st.divider()
st.subheader("🔍 Auditoria V2")

contextos = decisao_v2.get("contextos", {})
if contextos:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Market", "✅" if contextos.get("market_ok") else "❌")
    with col2:
        st.metric("Prediction", "✅" if contextos.get("prediction_ok") else "❌")
    with col3:
        st.metric("News", "✅" if contextos.get("news_ok") else "❌")
    with col4:
        st.metric("Vision", "✅" if contextos.get("vision_ok") else "❌")
    with col5:
        st.metric("Session", "✅" if contextos.get("session_ok") else "❌")
else:
    st.caption("Contextos não disponíveis no JSON V2.")

# ============================================================
# JSON COMPLETO (para debug)
# ============================================================

st.divider()
with st.expander("📄 Visualizar JSON Completo do V2"):
    st.json(decisao_v2)

# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.caption("Analisador Financeiro - Core Engine V2 • Decisão oficial • v2.0")