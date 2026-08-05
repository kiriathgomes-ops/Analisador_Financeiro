# ============================================================
# ARQUIVO: pages/2_🎯_Calculadora.py
#
# MOTIVO:
# Terminal Quant - Abertura, Pivot Points e Macro
#
# VERSÃO MELHORADA - Com % e mais indicadores
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
    page_title="Calculadora Quant - Terminal",
    page_icon="🎯",
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

    .card {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }

    .card-destaque {
        background: linear-gradient(145deg, #1a2230 0%, #0d1520 100%);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2a3a4a;
    }

    .metric-positive {
        color: #00c853 !important;
    }
    .metric-negative {
        color: #ff3d00 !important;
    }
    .metric-neutral {
        color: #ffc107 !important;
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
    "estimativa": os.path.join(COLETAS_DIR, "EstimativaAbertura.json"),
    "operacional": os.path.join(COLETAS_DIR, "Resultado_Calculadora_Operacional_Abertura.json"),
    "metricas": os.path.join(COLETAS_DIR, "Metricas_Calculadas.json"),
    "ativos": os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json"),
    "tendencias": os.path.join(COLETAS_DIR, "Analise_Tendencias.json"),
}

# ============================================================
# LEITURA JSON
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

estimativa = carregar_json(ARQUIVOS["estimativa"])
operacional = carregar_json(ARQUIVOS["operacional"])
metricas = carregar_json(ARQUIVOS["metricas"])
ativos_data = carregar_json(ARQUIVOS["ativos"])
tendencias = carregar_json(ARQUIVOS["tendencias"])

# Extrai ativos
ativos = ativos_data.get("ativos", ativos_data)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🎯 Calculadora Quant")
st.sidebar.caption("Abertura | Pivots | Macro")
st.sidebar.divider()

# Status dos dados
st.sidebar.markdown("### Status dos Dados")
for nome, caminho in ARQUIVOS.items():
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome.capitalize()}")

st.sidebar.divider()

if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_preco(nome):
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("preco", ativo.get("valor", 0.0))
    return 0.0

def obter_variacao(nome):
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("variacao_pct", ativo.get("var_pct", 0.0))
    return 0.0

def get_macro_valor(chave, sub_chave=None):
    """Busca valor de indicador macro em múltiplas fontes."""
    # Tenta do resumo_macro da estimativa
    resumo = estimativa.get("resumo_macro", {})
    if sub_chave:
        item = resumo.get(chave, {})
        if isinstance(item, dict):
            return item.get(sub_chave)
        return resumo.get(chave, 0)
    return resumo.get(chave, 0)

# ============================================================
# CABEÇALHO
# ============================================================

st.title("🎯 Terminal Quant - Abertura, Pivots e Macro")
st.caption("Estimativa institucional de abertura do mercado")

timestamp = operacional.get("metadata", {}).get("timestamp", "N/A")
st.info(f"⏱ Última atualização: {timestamp}")

# ============================================================
# 1 - ABERTURA TEÓRICA
# ============================================================

st.divider()
st.subheader("📊 Projeção Teórica de Abertura")

col1, col2 = st.columns(2)

win = estimativa.get("estimativas_abertura", {}).get("WIN_INDICE", {})
wdo = estimativa.get("estimativas_abertura", {}).get("WDO_DOLAR", {})

with col1:
    st.markdown("### 🟩 Mini Índice WIN")
    st.metric(
        "Abertura Teórica",
        f"{win.get('abertura_teorica_pontos', 0):,.0f}",
        f"{win.get('variacao_teorica_pct', 0):+.2f}%"
    )
    st.write("Ajuste base:", f"{win.get('pontos_ajuste_base', 0):,.0f} pts")

with col2:
    st.markdown("### 💵 Mini Dólar WDO")
    st.metric(
        "Abertura Teórica",
        f"{wdo.get('abertura_teorica_pontos', 0):,.2f}",
        f"{wdo.get('variacao_teorica_pct', 0):+.2f}%"
    )
    st.write("Ajuste base:", f"{wdo.get('pontos_ajuste_base', 0):,.2f} pts")

# ============================================================
# 2 - PIVOT POINTS
# ============================================================

st.divider()
st.subheader("📍 Mapa de Pivot Points")

pivots = estimativa.get("pivot_points", {})

if pivots:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### WIN_FUT")
        dados_pivot = pivots.get("WIN_FUT", {})
        if dados_pivot:
            st.metric("PP", f"{dados_pivot.get('PP', 0):,.0f}")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("R2", f"{dados_pivot.get('R2', 0):,.0f}")
            with c2:
                st.metric("R1", f"{dados_pivot.get('R1', 0):,.0f}")
            with c3:
                st.metric("S1", f"{dados_pivot.get('S1', 0):,.0f}")
            with c4:
                st.metric("S2", f"{dados_pivot.get('S2', 0):,.0f}")
        else:
            st.warning("Pivot Points não encontrados")
    
    with col2:
        st.markdown("### WDO_FUT")
        dados_pivot = pivots.get("WDO_FUT", {})
        if dados_pivot:
            st.metric("PP", f"{dados_pivot.get('PP', 0):,.2f}")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("R2", f"{dados_pivot.get('R2', 0):,.2f}")
            with c2:
                st.metric("R1", f"{dados_pivot.get('R1', 0):,.2f}")
            with c3:
                st.metric("S1", f"{dados_pivot.get('S1', 0):,.2f}")
            with c4:
                st.metric("S2", f"{dados_pivot.get('S2', 0):,.2f}")
        else:
            st.warning("Pivot Points não encontrados")
else:
    st.warning("⚠️ Pivot Points ainda não encontrados.")

# ============================================================
# 3 - INDICADORES MACRO (COM %)
# ============================================================

st.divider()
st.subheader("🌐 Indicadores Macro")

# Dados do DadosAtivosUnificados
vix_preco = obter_preco("VIX")
vix_var = obter_variacao("VIX")
crude_preco = obter_preco("CRUDE_OIL")
crude_var = obter_variacao("CRUDE_OIL")
iron_preco = obter_preco("IRON_ORE")
iron_var = obter_variacao("IRON_ORE")
dxy_preco = obter_preco("DXY")
dxy_var = obter_variacao("DXY")
gold_preco = obter_preco("GOLD")
gold_var = obter_variacao("GOLD")

# DI do resumo macro
di27 = get_macro_valor("di1_2027")
di29 = get_macro_valor("di1_2029")

# Se não tiver do resumo, tenta da estimativa
if not di27:
    di27 = estimativa.get("resumo_macro", {}).get("di1_2027", 0)
if not di29:
    di29 = estimativa.get("resumo_macro", {}).get("di1_2029", 0)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "⚠️ VIX",
        f"{vix_preco:.2f}" if vix_preco else "N/A",
        f"{vix_var:+.2f}%" if vix_var else None,
        delta_color="inverse"
    )

with col2:
    st.metric(
        "🛢️ Petróleo",
        f"${crude_preco:.2f}" if crude_preco else "N/A",
        f"{crude_var:+.2f}%" if crude_var else None
    )

with col3:
    st.metric(
        "⛏️ Minério",
        f"${iron_preco:.2f}" if iron_preco else "N/A",
        f"{iron_var:+.2f}%" if iron_var else None
    )

with col4:
    st.metric(
        "💵 DXY",
        f"{dxy_preco:.2f}" if dxy_preco else "N/A",
        f"{dxy_var:+.2f}%" if dxy_var else None,
        delta_color="inverse"
    )

with col5:
    st.metric(
        "📈 DI 2027",
        f"{di27:.2f}%" if di27 else "N/A"
    )

with col6:
    st.metric(
        "📈 DI 2029",
        f"{di29:.2f}%" if di29 else "N/A"
    )

# ============================================================
# 4 - ADRS BRASILEIRAS (COM %)
# ============================================================

st.divider()
st.subheader("📊 ADRs Brasileiras")

vale_preco = obter_preco("VALE_ADR")
vale_var = obter_variacao("VALE_ADR")
petr_preco = obter_preco("PETR_ADR")
petr_var = obter_variacao("PETR_ADR")
itub_preco = obter_preco("ITUB_ADR")
itub_var = obter_variacao("ITUB_ADR")
bbd_preco = obter_preco("BBD_ADR")
bbd_var = obter_variacao("BBD_ADR")
bbas_preco = obter_preco("BBAS_ADR")
bbas_var = obter_variacao("BBAS_ADR")
b3_preco = obter_preco("B3_ADR")
b3_var = obter_variacao("B3_ADR")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "⛏️ VALE",
        f"${vale_preco:.2f}" if vale_preco else "N/A",
        f"{vale_var:+.2f}%" if vale_var else None
    )

with col2:
    st.metric(
        "🛢️ PETR",
        f"${petr_preco:.2f}" if petr_preco else "N/A",
        f"{petr_var:+.2f}%" if petr_var else None
    )

with col3:
    st.metric(
        "🏦 ITUB",
        f"${itub_preco:.2f}" if itub_preco else "N/A",
        f"{itub_var:+.2f}%" if itub_var else None
    )

with col4:
    st.metric(
        "🏦 BBD",
        f"${bbd_preco:.2f}" if bbd_preco else "N/A",
        f"{bbd_var:+.2f}%" if bbd_var else None
    )

with col5:
    st.metric(
        "🏦 BBAS",
        f"${bbas_preco:.2f}" if bbas_preco else "N/A",
        f"{bbas_var:+.2f}%" if bbas_var else None
    )

with col6:
    st.metric(
        "🏦 B3",
        f"${b3_preco:.2f}" if b3_preco else "N/A",
        f"{b3_var:+.2f}%" if b3_var else None
    )

# ============================================================
# 5 - INDICADORES COMPOSTOS
# ============================================================

st.divider()
st.subheader("🧮 Indicadores Compostos")

indicadores = metricas.get("indicadores_compostos", {})
mercado_ext = indicadores.get("indicador_mercado_externo", 0)
adrs_brasil = indicadores.get("indicador_adrs_brasileiras", 0)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "🌍 Mercado Externo",
        f"{mercado_ext:+.2f}%",
        "Compra" if mercado_ext > 0 else "Venda" if mercado_ext < 0 else "Neutro"
    )

with col2:
    st.metric(
        "🇧🇷 ADRs Brasileiras",
        f"{adrs_brasil:+.2f}%",
        "Compra" if adrs_brasil > 0 else "Venda" if adrs_brasil < 0 else "Neutro"
    )

# ============================================================
# 6 - TENDÊNCIA (se disponível)
# ============================================================

if tendencias:
    st.divider()
    st.subheader("📈 Análise de Tendência (Últimos 15min)")
    
    # Busca WIN_FUT ou BMFBOVESPA:WIN1!
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
        <div class="card">
            <b>WIN - Tendência:</b> {emoji} {padrao} ({var:+.2f}%)
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.caption("Analisador Financeiro - Terminal Quant v2.0")