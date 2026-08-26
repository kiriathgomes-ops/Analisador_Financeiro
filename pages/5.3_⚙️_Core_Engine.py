# ============================================================
# ARQUIVO: pages/5_⚙️_Core_Engine.py
#
# MOTIVO:
# Visualização do Core Engine
# Decisão Quantitativa Final - Foco Exclusivo WIN (Mini Índice)
#
# VERSÃO COM PIVOT POINTS DO WIN
# ============================================================

import json
import os
from typing import Dict, Any, Tuple

import streamlit as st

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Core Engine (WIN) - Quant Terminal",
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
# LEITOR JSON E HELPER DE FORÇA
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    """Lê arquivos JSON com validação de existência, tamanho e erros de sintaxe."""
    if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        st.warning(f"⚠️ Erro de sintaxe JSON em `{os.path.basename(caminho)}`: {e}")
        return {}
    except Exception as e:
        st.error(f"❌ Erro de leitura em `{os.path.basename(caminho)}`: {e}")
        return {}

def calcular_nivel_forca(score: float) -> Tuple[str, str]:
    """Calcula texto e classe de cor para o nível de força baseado no score."""
    if abs(score) >= 4.0:
        return "FORTE", "score-high"
    elif abs(score) >= 1.5:
        return "MODERADA", "score-mid"
    return "FRACA", "score-low"

# Carregamento dos dados via cache
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
st.sidebar.caption("Decisão Quantitativa (WIN)")
st.sidebar.divider()

# Status dos arquivos no disco
st.sidebar.markdown("### Status dos Dados")
for nome, caminho in ARQUIVOS.items():
    existe = os.path.exists(caminho) and os.path.getsize(caminho) > 0
    icone = "✅" if existe else "❌"
    st.sidebar.caption(f"{icone} {nome.capitalize()}")

st.sidebar.divider()

if st.sidebar.button("🔄 Atualizar", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# CABEÇALHO
# ============================================================

st.title("⚙️ Core Engine — Mini Índice (WIN)")
st.caption("Resultado final gerado pelo Engine_Vies.py")

if not decisao:
    st.error("Decisao_Core.json não encontrado ou inválido.")
    st.info("Execute primeiro: python main_pipeline.py")
    st.stop()

timestamp = decisao.get("metadata", {}).get("timestamp", "N/A")
st.info(f"⏱ Última decisão: {timestamp}")

# ============================================================
# ANÁLISE OPERACIONAL - WIN
# ============================================================

st.divider()
st.subheader("🎯 Decisão do Core Engine")

analise_op = decisao.get("analise_operacional", {})
win_core = analise_op.get("WIN_INDICE", {})

win_vies = win_core.get("vies_final", "NEUTRO")
win_score = float(win_core.get("score_numeric", 0))
win_fatores = win_core.get("fatores_relevantes", [])

if "COMPRA" in win_vies.upper():
    win_box_class = "buy-box"
    win_emoji = "🟢"
elif "VENDA" in win_vies.upper():
    win_box_class = "sell-box"
    win_emoji = "🔴"
else:
    win_box_class = "neutral-box"
    win_emoji = "🟡"

win_forca_texto, win_forca_cor = calcular_nivel_forca(win_score)

# Painel Centralizado da Decisão do WIN
st.markdown(f"""
<div class="{win_box_class}">
    <h2>{win_emoji} {win_vies}</h2>
    <h4>Score: <span class="{win_forca_cor}">{win_score:.2f}</span></h4>
    <p>Força: {win_forca_texto}</p>
</div>
""", unsafe_allow_html=True)

if win_fatores:
    st.write("")
    with st.expander("📋 Fatores relevantes do WIN", expanded=True):
        for f in win_fatores:
            st.markdown(f"""
            <div class="card-fator">
                <span class="fator-tag">Fator</span>
                {f}
            </div>
            """, unsafe_allow_html=True)

# ============================================================
# TENDÊNCIA E ABERTURA TEÓRICA
# ============================================================

st.divider()
col_tend, col_abert = st.columns(2)

with col_tend:
    st.subheader("📈 Tendência (15min)")
    if tendencias:
        win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
        if isinstance(win_tend, dict):
            padrao = win_tend.get("padrao_comportamento", "N/A")
            intervalo = win_tend.get("intervalo_5_para_0") or {}
            var = intervalo.get("variacao_pct", 0)
            emoji_tend = "🟢" if var > 0 else "🔴" if var < 0 else "🟡"
            
            st.markdown(f"""
            <div class="info-box">
                <b>Padrão:</b> {emoji_tend} {padrao}<br>
                <b>Variação:</b> {var:+.2f}%
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("Sem dados de tendência para WIN_FUT.")
    else:
        st.caption("Analise_Tendencias.json não carregado.")

with col_abert:
    st.subheader("📊 Abertura Teórica")
    if estimativa:
        est_abertura = estimativa.get("estimativa_abertura", {}) or estimativa.get("estimativas_abertura", {})
        win_est = est_abertura.get("WIN_INDICE", {})
        
        if win_est:
            pts = win_est.get("abertura_teorica_pontos", 0)
            var = win_est.get("variacao_teorica_pct", 0)
            
            st.metric(
                label="WIN Abertura Teórica",
                value=f"{pts:,.0f} pts",
                delta=f"{var:+.2f}%"
            )
        else:
            st.warning("Dados do WIN_INDICE não encontrados no JSON.")
    else:
        st.caption("EstimativaAbertura.json não carregado.")

# ============================================================
# PIVOT POINTS (WIN)
# ============================================================

if estimativa:
    pivots_data = estimativa.get("pivot_points", {})
    win_pivots = pivots_data.get("WIN_FUT") or pivots_data.get("WIN_INDICE", {})
    
    if win_pivots:
        st.divider()
        st.subheader("📌 Pivot Points (WIN)")
        
        r2 = win_pivots.get("R2", 0)
        r1 = win_pivots.get("R1", 0)
        pp = win_pivots.get("PP", 0)
        s1 = win_pivots.get("S1", 0)
        s2 = win_pivots.get("S2", 0)
        
        col_r2, col_r1, col_pp, col_s1, col_s2 = st.columns(5)
        
        col_r2.metric("Resistência 2 (R2)", f"{r2:,.2f}")
        col_r1.metric("Resistência 1 (R1)", f"{r1:,.2f}")
        col_pp.metric("Pivot Point (PP)", f"{pp:,.2f}")
        col_s1.metric("Suporte 1 (S1)", f"{s1:,.2f}")
        col_s2.metric("Suporte 2 (S2)", f"{s2:,.2f}")

# ============================================================
# MATRIZ DE DADOS (Auditoria)
# ============================================================

st.divider()
st.subheader("📊 Auditoria dos Dados")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Decisão", "✅" if decisao else "❌")

with col2:
    st.metric("Dados Validados", len(validacao.get("ativos_validados", [])))

with col3:
    st.metric("Eventos Notícias", len(noticias.get("horarios", [])))

with col4:
    st.metric("Métricas", len(metricas) if isinstance(metricas, dict) else 0)

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
st.caption("Analisador Financeiro - Core Engine Quant v2.0 (WIN Focus)")