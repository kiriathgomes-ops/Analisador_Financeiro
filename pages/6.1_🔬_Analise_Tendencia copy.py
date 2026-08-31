# ============================================================
# DASHBOARD ANALISE DE TENDÊNCIA
#
# Fonte:
# Coletas/Analise_Tendencias.json
#
# VERSÃO MELHORADA - Com atalhos e melhor visualização
#
# ============================================================

import streamlit as st
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"

ARQUIVO = COLETAS_DIR / "Analise_Tendencias.json"

# ============================================================
# CONFIG STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Análise Tendência",
    page_icon="📈",
    layout="wide"
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

    .card-tendencia {
        background: linear-gradient(145deg, #161b24 0%, #1c2230 100%);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2a3a4a;
        margin-bottom: 10px;
    }

    .card-tendencia .label {
        color: #8b949e;
        font-size: 0.75rem;
    }

    .card-tendencia .valor {
        font-size: 1.1rem;
        font-weight: 600;
    }

    .tendencia-up {
        color: #00c853;
    }
    .tendencia-down {
        color: #ff3d00;
    }
    .tendencia-neutral {
        color: #ffc107;
    }

    .card-atalho {
        background-color: #161b22;
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 3px solid #00d4ff;
        margin-bottom: 8px;
        cursor: pointer;
    }
    .card-atalho:hover {
        background-color: #1e2a3a;
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
# FUNÇÕES
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados():
    if not ARQUIVO.exists():
        return {}
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def classificar_padrao(padrao):
    """Classifica o padrão de comportamento."""
    if padrao == "SUBIU_E_SUBIU":
        return "🟢 Compra Forte", "tendencia-up"
    elif padrao == "SUBIU_E_ESTAVEL":
        return "🟡 Compra Perdendo Força", "tendencia-neutral"
    elif padrao == "DESCEU_E_SUBIU":
        return "🔵 Reversão Compra", "tendencia-up"
    elif padrao == "DESCEU_E_DESCEU":
        return "🔴 Venda Forte", "tendencia-down"
    elif padrao == "SUBIU_E_DESCEU":
        return "🟠 Reversão Venda", "tendencia-down"
    else:
        return "⚪ Neutro", "tendencia-neutral"

# ============================================================
# CARREGAR DADOS
# ============================================================

dados = carregar_dados()

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📈 Análise Tendência")
st.sidebar.caption("Fluxo das últimas 3 coletas")
st.sidebar.markdown("---")

# Status dos dados
st.sidebar.markdown("### Status")
if ARQUIVO.exists():
    timestamp = datetime.fromtimestamp(ARQUIVO.stat().st_mtime).strftime("%H:%M:%S")
    st.sidebar.success(f"✅ Dados carregados\nÚltima: {timestamp}")
else:
    st.sidebar.error("❌ Arquivo não encontrado")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados", width="stretch"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# TITULO
# ============================================================

st.title("📈 Análise Institucional de Tendência")
st.caption("Comparativo das últimas 3 coletas: 10 minutos → 5 minutos → Atual")

if not dados:
    st.warning("Arquivo Analise_Tendencias.json não encontrado.")
    st.info("Execute `rodar_pipeline_3x.bat` para gerar os dados.")
    st.stop()

# ============================================================
# ATALHOS PARA ATIVOS PRINCIPAIS
# ============================================================

st.subheader("🎯 Ativos Principais")

# Mapeamento de ativos principais
ativos_principais = {
    "WIN_FUT": "📊 WIN",
    "WDO_FUT": "💵 WDO",
    "SP500_FUT": "🇺🇸 S&P500",
    "NASDAQ_FUT": "💻 Nasdaq",
    "VIX": "⚠️ VIX",
    "EWZ": "🇧🇷 EWZ",
}

col_atalhos = st.columns(min(6, len(ativos_principais)))

for i, (chave, nome) in enumerate(ativos_principais.items()):
    # Tenta encontrar o ativo no dados (pode estar como BMFBOVESPA:WIN1!)
    info = None
    for key in [chave, f"BMFBOVESPA:{chave.split('_')[0]}1!"]:
        if key in dados:
            info = dados[key]
            break
    
    with col_atalhos[i % len(col_atalhos)]:
        if info:
            padrao = info.get("padrao_comportamento", "N/A")
            var = info.get("intervalo_5_para_0", {}).get("variacao_pct", 0)
            emoji = "🟢" if var > 0 else "🔴" if var < 0 else "🟡"
            st.metric(
                nome,
                f"{emoji} {padrao}",
                f"{var:+.2f}%"
            )
        else:
            st.metric(nome, "N/A")

st.markdown("---")

# ============================================================
# TRANSFORMA EM DATAFRAME
# ============================================================

lista = []
for ativo, info in dados.items():
    padrao = info.get("padrao_comportamento", "N/A")
    classificacao, css_class = classificar_padrao(padrao)
    
    precos = info.get("precos", {})
    intervalo_10_5 = info.get("intervalo_10_para_5", {})
    intervalo_5_0 = info.get("intervalo_5_para_0", {})
    
    lista.append({
        "Ativo": ativo,
        "10 Min": precos.get("10m", 0),
        "5 Min": precos.get("5m", 0),
        "Atual": precos.get("0m", 0),
        "10→5": intervalo_10_5.get("tendencia", "N/A"),
        "5→0": intervalo_5_0.get("tendencia", "N/A"),
        "Var Último Movimento %": intervalo_5_0.get("variacao_pct", 0),
        "Padrão": padrao,
        "Classificação": classificacao,
    })

df = pd.DataFrame(lista)

# ============================================================
# FILTROS
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    filtro_classificacao = st.multiselect(
        "Classificação",
        df["Classificação"].unique(),
        default=df["Classificação"].unique()
    )

with col2:
    filtro_tendencia = st.multiselect(
        "Tendência (5→0)",
        df["5→0"].unique(),
        default=df["5→0"].unique()
    )

with col3:
    busca = st.text_input("🔍 Buscar ativo", placeholder="Ex: WIN, VIX, PETR...")

df_view = df[
    (df["Classificação"].isin(filtro_classificacao)) &
    (df["5→0"].isin(filtro_tendencia))
]

if busca:
    df_view = df_view[df_view["Ativo"].str.contains(busca.upper(), na=False)]

# ============================================================
# INDICADORES
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("📊 Total Ativos", len(df))

with c2:
    compra_forte = len(df[df["Classificação"] == "🟢 Compra Forte"])
    st.metric("🟢 Compra Forte", compra_forte)

with c3:
    venda_forte = len(df[df["Classificação"] == "🔴 Venda Forte"])
    st.metric("🔴 Venda Forte", venda_forte)

with c4:
    reversao = len(df[df["Classificação"].str.contains("Reversão", na=False)])
    st.metric("🔄 Reversões", reversao)

with c5:
    neutro = len(df[df["Classificação"] == "⚪ Neutro"])
    st.metric("⚪ Neutro", neutro)

st.markdown("---")

# ============================================================
# TABELA PRINCIPAL
# ============================================================

st.subheader("📊 Fluxo das últimas coletas")

# Formatação da tabela
def color_var(val):
    if val > 0.5:
        return 'color: #00c853; font-weight: bold'
    elif val < -0.5:
        return 'color: #ff3d00; font-weight: bold'
    return 'color: #ffc107'

st.dataframe(
    df_view.sort_values("Var Último Movimento %", ascending=False),
    width="stretch",
    height=500,
    column_config={
        "Ativo": st.column_config.TextColumn("Ativo", width="medium"),
        "10 Min": st.column_config.NumberColumn("10 Min", format="%.2f"),
        "5 Min": st.column_config.NumberColumn("5 Min", format="%.2f"),
        "Atual": st.column_config.NumberColumn("Atual", format="%.2f"),
        "10→5": st.column_config.TextColumn("10→5", width="small"),
        "5→0": st.column_config.TextColumn("5→0", width="small"),
        "Var Último Movimento %": st.column_config.NumberColumn(
            "Var %",
            format="%+.2f%%"
        ),
        "Padrão": st.column_config.TextColumn("Padrão", width="medium"),
        "Classificação": st.column_config.TextColumn("Classificação", width="medium"),
    }
)

# ============================================================
# RANKING OPERACIONAL
# ============================================================

st.divider()
st.subheader("🔥 Ranking Operacional")

colA, colB = st.columns(2)

with colA:
    st.markdown("### 🟢 Maiores Forças Compradoras")
    compra = df[df["Classificação"] == "🟢 Compra Forte"]
    if not compra.empty:
        st.dataframe(
            compra.sort_values("Var Último Movimento %", ascending=False),
            width="stretch",
            column_config={
                "Ativo": "Ativo",
                "Var Último Movimento %": st.column_config.NumberColumn(
                    "Var %",
                    format="%+.2f%%"
                ),
                "Padrão": "Padrão",
            }
        )
    else:
        st.info("Nenhum ativo com compra forte")

with colB:
    st.markdown("### 🔴 Maiores Forças Vendedoras")
    venda = df[df["Classificação"] == "🔴 Venda Forte"]
    if not venda.empty:
        st.dataframe(
            venda.sort_values("Var Último Movimento %", ascending=True),
            width="stretch",
            column_config={
                "Ativo": "Ativo",
                "Var Último Movimento %": st.column_config.NumberColumn(
                    "Var %",
                    format="%+.2f%%"
                ),
                "Padrão": "Padrão",
            }
        )
    else:
        st.info("Nenhum ativo com venda forte")

# ============================================================
# RESUMO DOS ATIVOS PRINCIPAIS
# ============================================================

st.divider()
st.subheader("📋 Resumo dos Ativos Principais")

# Filtra apenas os ativos principais
principais_df = df[df["Ativo"].str.contains("WIN|WDO|VIX|EWZ|SP500|NASDAQ", case=False, na=False)]

if not principais_df.empty:
    st.dataframe(
        principais_df[["Ativo", "Padrão", "Var Último Movimento %", "Classificação"]],
        width="stretch",
        hide_index=True,
        column_config={
            "Ativo": "Ativo",
            "Padrão": "Padrão",
            "Var Último Movimento %": st.column_config.NumberColumn(
                "Var %",
                format="%+.2f%%"
            ),
            "Classificação": "Classificação",
        }
    )

# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.caption("Análise de Tendência - Analisador Financeiro Quant v2.0")