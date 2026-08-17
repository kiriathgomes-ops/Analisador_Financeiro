# ============================================================
# ARQUIVO: pages/21_📈_Historico_Macro.py
# VERSÃO: 4.0 - Fixa: WIN + ADRs + Mercado Externo
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
# MAPEAMENTO DOS TICKERS (ajuste conforme seus ROMs)
# ------------------------------------------------------------
TICKER_MAP = {
    "BMFBOVESPA:WIN1!": "WIN",
    "WIN1!": "WIN",
    "WIN$": "WIN",
    "TVC:VIX": "VIX",
    "NYSE:VALE": "VALE",
    "VALE": "VALE",
    "NYSE:PBR": "PETR",
    "PBR": "PETR",
    "NYSE:ITUB": "ITUB",
    "NYSE:BBD": "BBD",
    "OTC:BDORY": "BBAS",
    "OTC:BOLSY": "B3",
    "SGX:FEF2!": "Minério (2M)",
    "FEF2!": "Minério (2M)",
    "NYMEX:CL1!": "Petróleo",
    "CL1!": "Petróleo",
}

# Grupos fixos
GRUPO_WIN = ["WIN"]
GRUPO_ADRS = ["VALE", "PETR", "ITUB", "BBD", "BBAS", "B3"]
GRUPO_EXTERNO = ["VIX", "Minério (2M)", "Petróleo"]
TODOS_ATIVOS = GRUPO_WIN + GRUPO_ADRS + GRUPO_EXTERNO

# Cores
CORES = {
    "WIN": "#00d4ff",
    "VIX": "#ff6b6b",
    "VALE": "#4ecdc4",
    "PETR": "#ffe66d",
    "ITUB": "#4dabf7",
    "BBD": "#f783ac",
    "BBAS": "#9775fa",
    "B3": "#69db7c",
    "Minério (2M)": "#fcc419",
    "Petróleo": "#ff922b",
}

# ------------------------------------------------------------
# CARREGAR DADOS
# ------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados() -> pd.DataFrame:
    registros = []

    # Tenta carregar dos ROMs
    nomes_rom = ["0", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"]
    arquivos = [COLETAS_DIR / f"Coleta_rom-{nome}.json" for nome in nomes_rom]
    arquivos_existentes = [a for a in arquivos if a.exists()]

    if arquivos_existentes:
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
                # Verifica se o ticker está no mapa
                label = TICKER_MAP.get(ticker)
                if not label:
                    continue
                dados_reais = item.get("dados_reais")
                if not dados_reais:
                    continue
                preco = dados_reais.get("close")
                if preco is None:
                    continue
                registros.append({
                    "timestamp": ts,
                    "ativo": label,
                    "preco": float(preco),
                })

    # Se não encontrou nos ROMs, tenta fallback
    if not registros:
        arquivo = COLETAS_DIR / "DadosAtivosUnificados.json"
        if arquivo.exists():
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except Exception:
                return pd.DataFrame()
            ativos = dados.get("ativos", {})
            if ativos:
                unificado_map = {
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
                ts = datetime.now()
                for nome, label in unificado_map.items():
                    item = ativos.get(nome)
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

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    df = df.drop_duplicates(subset=["timestamp", "ativo"], keep="first")
    df = df.sort_values(["timestamp", "ativo"]).reset_index(drop=True)
    return df

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
        st.info(f"Nenhum dado para {titulo}.")
        return
    df_norm = df.copy()
    df_norm["preco_norm"] = df_norm.groupby("ativo")["preco"].transform(
        lambda x: x / x.iloc[0] * 100 if len(x) > 0 else x
    )
    fig = px.line(df_norm, x="timestamp", y="preco_norm", color="ativo",
                  color_discrete_map=CORES,
                  title=f"Evolução normalizada – {titulo}",
                  labels={"preco_norm": "Índice (base 100)", "timestamp": "Horário"})
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                      font_color="#e6edf3", height=350,
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
                          labels={"preco": "Preço", "timestamp": ""},
                          color_discrete_sequence=[CORES.get(ativo, "#ffffff")])
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
st.caption("WIN • ADRs • Mercado Externo")

st.sidebar.title("⚙️ Configurações")
max_pontos = st.sidebar.slider("Pontos (coletas)", 5, 120, 60, 5)

df_all = carregar_dados()

if df_all.empty:
    st.error("❌ Nenhum dado disponível. Execute o pipeline para gerar coletas.")
    st.stop()

# Filtra apenas os ativos dos grupos fixos
df = df_all[df_all["ativo"].isin(TODOS_ATIVOS)]
df = df.sort_values("timestamp").tail(max_pontos)

st.sidebar.markdown("### Resumo")
st.sidebar.metric("Registros", len(df))
st.sidebar.metric("Ativos carregados", len(df["ativo"].unique()))
if not df.empty:
    st.sidebar.metric("Período", f"{df['timestamp'].min().strftime('%H:%M')} → {df['timestamp'].max().strftime('%H:%M')}")

# ------------------------------------------------------------
# GRÁFICO UNIFICADO (todos os grupos)
# ------------------------------------------------------------
st.markdown("### 📊 Comparação Unificada")
if len(df["ativo"].unique()) >= 2:
    df_norm = df.copy()
    df_norm["preco_norm"] = df_norm.groupby("ativo")["preco"].transform(
        lambda x: x / x.iloc[0] * 100 if len(x) > 0 else x
    )
    fig = px.line(df_norm, x="timestamp", y="preco_norm", color="ativo",
                  color_discrete_map=CORES,
                  title="Evolução normalizada – WIN, ADRs e Mercado Externo",
                  labels={"preco_norm": "Índice (base 100)", "timestamp": "Horário"})
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                      font_color="#e6edf3", height=450,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_xaxes(gridcolor="#2a2d4a")
    fig.update_yaxes(gridcolor="#2a2d4a")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dados insuficientes para o gráfico unificado.")

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# WIN
# ------------------------------------------------------------
st.markdown("### 🎯 WIN")
win_df = df[df["ativo"].isin(GRUPO_WIN)]
exibir_grafico_normalizado(win_df, "WIN")
exibir_graficos_individuais(win_df)
st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# ADRs
# ------------------------------------------------------------
st.markdown("### 🇧🇷 ADRs Brasileiras")
adrs_df = df[df["ativo"].isin(GRUPO_ADRS)]
exibir_grafico_normalizado(adrs_df, "ADRs")
exibir_graficos_individuais(adrs_df)
st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# Mercado Externo
# ------------------------------------------------------------
st.markdown("### 🌍 Mercado Externo")
ext_df = df[df["ativo"].isin(GRUPO_EXTERNO)]
exibir_grafico_normalizado(ext_df, "Mercado Externo")
exibir_graficos_individuais(ext_df)
st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# CORRELAÇÃO
# ------------------------------------------------------------
st.markdown("### 🔗 Correlação entre ativos")
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