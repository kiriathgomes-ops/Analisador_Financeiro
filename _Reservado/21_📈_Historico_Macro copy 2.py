# ============================================================
# ARQUIVO: pages/21_📈_Historico_Macro.py
# VERSÃO: 3.1 - Seleção manual de ativos via multiselect
# ============================================================

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="Histórico Macro - Analisador Financeiro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%); }
    .card { background: #161b22; border-radius: 10px; padding: 16px; border: 1px solid #2a2d4a; margin-bottom: 16px; }
    .card h3 { color: #58a6ff; margin-top: 0; }
    .metric-green { color: #00c853; }
    .metric-red { color: #ff3d00; }
    .metric-neutral { color: #ffc107; }
    .separator { border: none; height: 2px; background: linear-gradient(90deg, #2a2d4a, transparent); margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"

# ------------------------------------------------------------
# FUNÇÃO: INFERIR RÓTULO AMIGÁVEL
# ------------------------------------------------------------
def inferir_label(ticker: str) -> str:
    nome = ticker
    for prefixo in ["TVC:", "NYSE:", "OTC:", "SGX:", "NYMEX:", "FX_IDC:", "BMFBOVESPA:", "CME_MINI:"]:
        if nome.startswith(prefixo):
            nome = nome[len(prefixo):]
            break
    nome = re.sub(r"[!@#$%^&*()_+=\-]", "", nome)
    nome = re.sub(r"FUT|ADR|_2M|_", "", nome)
    mapping = {
        "CL1": "Petróleo",
        "FEF2": "Minério (2M)",
        "FEF1": "Minério (1M)",
        "ES1": "S&P500",
        "NQ1": "Nasdaq",
    }
    if nome in mapping:
        return mapping[nome]
    if len(nome) <= 5:
        return nome
    partes = nome.split(":")
    return partes[-1] if partes else nome

# ------------------------------------------------------------
# FUNÇÃO: CARREGAR TODOS OS ATIVOS DOS ROMs
# ------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def carregar_todos_ativos() -> pd.DataFrame:
    registros = []
    nomes_rom = ["0", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"]
    arquivos = [COLETAS_DIR / f"Coleta_rom-{nome}.json" for nome in nomes_rom]
    arquivos_existentes = [a for a in arquivos if a.exists()]

    if not arquivos_existentes:
        return carregar_atual_unificado()

    for arquivo in arquivos_existentes:
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception:
            continue

        ts_str = dados.get("metadata_coleta", {}).get("timestamp_coleta")
        if not ts_str:
            ts = datetime.fromtimestamp(arquivo.stat().st_mtime)
        else:
            try:
                ts = datetime.fromisoformat(ts_str)
            except ValueError:
                ts = datetime.fromtimestamp(arquivo.stat().st_mtime)

        coletas = dados.get("coletas", [])
        for item in coletas:
            ticker = item.get("ativo")
            if not ticker:
                continue
            dados_reais = item.get("dados_reais")
            if not dados_reais:
                continue
            preco = dados_reais.get("close")
            if preco is None:
                continue
            label = inferir_label(ticker)
            registros.append({
                "timestamp": ts,
                "ticker_original": ticker,
                "ativo": label,
                "preco": float(preco),
            })

    if not registros:
        return carregar_atual_unificado()

    df = pd.DataFrame(registros)
    df = df.drop_duplicates(subset=["timestamp", "ativo"], keep="first")
    df = df.sort_values(["timestamp", "ativo"]).reset_index(drop=True)
    return df

# ------------------------------------------------------------
# FALLBACK: DadosAtivosUnificados.json
# ------------------------------------------------------------
def carregar_atual_unificado() -> pd.DataFrame:
    arquivo = COLETAS_DIR / "DadosAtivosUnificados.json"
    if not arquivo.exists():
        return pd.DataFrame()

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return pd.DataFrame()

    ativos = dados.get("ativos", {})
    if not ativos:
        return pd.DataFrame()

    unificado_to_label = {
        "WIN_FUT": "WIN",
        "VIX": "VIX",
        "VALE_ADR": "VALE",
        "PETR_ADR": "PETR",
        "ITUB_ADR": "ITUB",
        "BBD_ADR": "BBD",
        "BBAS_ADR": "BBAS",
        "B3_ADR": "B3",
        "IRON_ORE_2M": "Minério (2M)",
        "CRUDE_OIL": "Petróleo",
    }

    registros = []
    ts = datetime.now()
    for nome_padrao, label in unificado_to_label.items():
        item = ativos.get(nome_padrao)
        if not item:
            continue
        preco = item.get("preco")
        if preco is None:
            continue
        registros.append({
            "timestamp": ts,
            "ativo": label,
            "preco": float(preco),
        })

    return pd.DataFrame(registros)

# ------------------------------------------------------------
# CORRELAÇÃO
# ------------------------------------------------------------
def calcular_correlacao(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    ativos_validos = []
    for ativo in df["ativo"].unique():
        if len(df[df["ativo"] == ativo]) >= 3:
            ativos_validos.append(ativo)
    if len(ativos_validos) < 2:
        return pd.DataFrame()
    df_filtrado = df[df["ativo"].isin(ativos_validos)]
    pivot = df_filtrado.pivot(index="timestamp", columns="ativo", values="preco")
    if pivot.empty or len(pivot.columns) < 2:
        return pd.DataFrame()
    return pivot.pct_change().corr()

# ------------------------------------------------------------
# EXIBIR GRÁFICOS
# ------------------------------------------------------------
def exibir_grafico_normalizado(df: pd.DataFrame, titulo: str):
    if df.empty:
        st.info("Nenhum dado para exibir.")
        return
    df_norm = df.copy()
    df_norm["preco_norm"] = df_norm.groupby("ativo")["preco"].transform(
        lambda x: x / x.iloc[0] * 100 if len(x) > 0 else x
    )
    fig = px.line(df_norm, x="timestamp", y="preco_norm", color="ativo",
                  title=f"Evolução normalizada – {titulo}",
                  labels={"preco_norm": "Índice (base 100)", "timestamp": "Horário"})
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                      font_color="#e6edf3", height=400,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(gridcolor="#2a2d4a")
    fig.update_yaxes(gridcolor="#2a2d4a")
    st.plotly_chart(fig, use_container_width=True)

def exibir_graficos_individuais(df: pd.DataFrame):
    if df.empty:
        return
    df_var = df.copy()
    df_var["var_pct"] = df_var.groupby("ativo")["preco"].pct_change() * 100
    ativos = sorted(df["ativo"].unique())
    cols = st.columns(2)
    for i, ativo in enumerate(ativos):
        with cols[i % 2]:
            df_plot = df_var[df_var["ativo"] == ativo]
            if df_plot.empty:
                continue
            fig = px.line(df_plot, x="timestamp", y="preco", title=ativo,
                          labels={"preco": "Preço", "timestamp": ""})
            fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                              font_color="#e6edf3", height=200, margin=dict(l=20, r=20, t=40, b=20),
                              showlegend=False)
            fig.update_xaxes(gridcolor="#2a2d4a")
            fig.update_yaxes(gridcolor="#2a2d4a")
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
st.title("📈 Histórico Macro")
st.caption("Selecione os ativos que deseja visualizar no sidebar")

st.sidebar.title("⚙️ Configurações")
max_pontos = st.sidebar.slider("Pontos (coletas)", 5, 120, 60, 5)

# Carrega todos os ativos disponíveis
df_all = carregar_todos_ativos()

if df_all.empty:
    st.error("❌ Nenhum dado disponível. Execute o pipeline para gerar coletas.")
    st.stop()

# Lista de ativos disponíveis
ativos_disponiveis = sorted(df_all["ativo"].unique())

# Multiselect para escolher quais ativos exibir
ativos_selecionados = st.sidebar.multiselect(
    "Selecione os ativos para exibir",
    options=ativos_disponiveis,
    default=ativos_disponiveis[:6] if len(ativos_disponiveis) > 6 else ativos_disponiveis,
    help="Escolha os ativos que deseja visualizar nos gráficos e cards."
)

if not ativos_selecionados:
    st.warning("Selecione pelo menos um ativo no sidebar.")
    st.stop()

# Filtra o DataFrame
df = df_all[df_all["ativo"].isin(ativos_selecionados)]
df = df.sort_values("timestamp").tail(max_pontos)

# Resumo no sidebar
st.sidebar.markdown("### Resumo")
st.sidebar.metric("Registros", len(df))
st.sidebar.metric("Ativos selecionados", len(ativos_selecionados))
if not df.empty:
    st.sidebar.metric("Período", f"{df['timestamp'].min().strftime('%H:%M')} → {df['timestamp'].max().strftime('%H:%M')}")

# Atalhos para seleções rápidas
st.sidebar.markdown("### Atalhos")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("📊 WIN + ADRs + Ext"):
        default_sel = [a for a in ativos_disponiveis if any(x in a.upper() for x in ["WIN", "VALE", "PETR", "ITUB", "BBD", "BBAS", "B3", "VIX", "MINÉRIO", "PETRÓLEO"])]
        if default_sel:
            st.session_state.ativos_selecionados = default_sel
            st.rerun()
with col2:
    if st.button("🎯 Apenas WIN"):
        win_sel = [a for a in ativos_disponiveis if "WIN" in a.upper()]
        if win_sel:
            st.session_state.ativos_selecionados = win_sel
            st.rerun()

# Salva seleção na sessão para persistência
if "ativos_selecionados" not in st.session_state:
    st.session_state.ativos_selecionados = ativos_selecionados
else:
    # Se a seleção mudou, atualiza o multiselect
    if st.session_state.ativos_selecionados != ativos_selecionados:
        # O multiselect já reflete o estado atual, mas podemos sincronizar
        pass

# ------------------------------------------------------------
# GRÁFICO UNIFICADO
# ------------------------------------------------------------
st.markdown("### 📊 Comparação Unificada")
if len(df["ativo"].unique()) >= 2:
    exibir_grafico_normalizado(df, "Todos os ativos selecionados")
else:
    st.info("Selecione pelo menos 2 ativos para o gráfico comparativo.")

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# GRÁFICOS INDIVIDUAIS
# ------------------------------------------------------------
st.markdown("### 📉 Gráficos individuais")
exibir_graficos_individuais(df)

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# CORRELAÇÃO
# ------------------------------------------------------------
st.markdown("### 🔗 Correlação entre ativos selecionados")
corr = calcular_correlacao(df)
if not corr.empty:
    fig = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.index,
                                    colorscale="RdBu", zmid=0,
                                    text=corr.round(2), texttemplate="%{text}",
                                    textfont={"color": "#e6edf3"}))
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                      font_color="#e6edf3", height=450,
                      xaxis=dict(tickangle=45))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dados insuficientes para correlação.")

# ------------------------------------------------------------
# ÚLTIMAS COTAÇÕES
# ------------------------------------------------------------
st.markdown("### 📌 Últimas cotações e variações")

ultimo_ts = df["timestamp"].max()
df_ultimo = df[df["timestamp"] == ultimo_ts]

if len(df["timestamp"].unique()) > 1:
    ts_anterior = sorted(df["timestamp"].unique())[-2]
    df_anterior = df[df["timestamp"] == ts_anterior]
else:
    df_anterior = pd.DataFrame()

cols = st.columns(min(len(df_ultimo), 6))
for i, (_, row) in enumerate(df_ultimo.iterrows()):
    if i >= len(cols):
        break
    ativo = row["ativo"]
    preco = row["preco"]
    var_real = None
    if not df_anterior.empty:
        prev = df_anterior[df_anterior["ativo"] == ativo]
        if not prev.empty:
            var_real = (preco / prev.iloc[0]["preco"] - 1) * 100
    delta = f"{var_real:+.2f}%" if var_real is not None else None
    cor = "normal" if var_real is not None and var_real > 0 else "inverse" if var_real is not None and var_real < 0 else "off"
    with cols[i]:
        st.metric(label=ativo, value=f"{preco:.2f}", delta=delta, delta_color=cor)

st.markdown("---")
st.caption(f"{len(df)} registros • Última: {ultimo_ts.strftime('%d/%m/%Y %H:%M:%S')}")