# ============================================================
# ARQUIVO: pages/21_📈_Historico_Macro.py
# OBJETIVO: Dashboard histórico de ativos macro (VIX, ADRs, Minério, Petróleo)
# VERSÃO: 2.4 com separação entre ADRs e Mercado Externo
# ============================================================

from __future__ import annotations

import json
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

# ------------------------------------------------------------
# CSS PERSONALIZADO (tema escuro)
# ------------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }
    .card {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2a2d4a;
        margin-bottom: 16px;
    }
    .card h3 {
        color: #58a6ff;
        margin-top: 0;
    }
    .metric-green { color: #00c853; }
    .metric-red { color: #ff3d00; }
    .metric-neutral { color: #ffc107; }
    .separator {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, #2a2d4a, transparent);
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# CAMINHOS
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"

# Mapeamento dos tickers originais (como aparecem nos ROMs) para os rótulos amigáveis
TICKER_ORIGINAL_TO_LABEL = {
    # ADRs Brasileiras
    "NYSE:VALE": "VALE",
    "NYSE:PBR": "PETR",
    "NYSE:ITUB": "ITUB",
    "NYSE:BBD": "BBD",
    "OTC:BDORY": "BBAS",
    "OTC:BOLSY": "B3",
    # Mercado Externo
    "TVC:VIX": "VIX",
    "SGX:FEF2!": "Minério (2M)",
    "NYMEX:CL1!": "Petróleo",
}

# Separação em grupos
GRUPO_ADRS = ["VALE", "PETR", "ITUB", "BBD", "BBAS", "B3"]
GRUPO_EXTERNO = ["VIX", "Minério (2M)", "Petróleo"]

# Cores para os gráficos
CORES = {
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
# FUNÇÃO: CARREGAR HISTÓRICO DOS ARQUIVOS ROM
# ------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def carregar_historico_rom() -> pd.DataFrame:
    registros = []

    nomes_rom = ["0", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"]
    arquivos = [COLETAS_DIR / f"Coleta_rom-{nome}.json" for nome in nomes_rom]
    arquivos_existentes = [a for a in arquivos if a.exists()]

    st.sidebar.write("**Arquivos ROM encontrados:**", len(arquivos_existentes))
    if arquivos_existentes:
        st.sidebar.write("Último:", arquivos_existentes[-1].name)

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
        mapa = {item["ativo"]: item for item in coletas}

        for ticker_original, label in TICKER_ORIGINAL_TO_LABEL.items():
            item = mapa.get(ticker_original)
            if not item:
                continue
            dados_reais = item.get("dados_reais")
            if not dados_reais:
                continue
            preco = dados_reais.get("close")
            if preco is None:
                continue
            variacao = dados_reais.get("change_percent", 0.0) or 0.0
            registros.append({
                "timestamp": ts,
                "ativo": label,
                "preco": float(preco),
                "variacao_pct": float(variacao),
            })

    if not registros:
        st.sidebar.warning("Nenhum dos tickers mapeados foi encontrado nos ROMs.")
        return carregar_atual_unificado()

    df = pd.DataFrame(registros)
    df = df.drop_duplicates(subset=["timestamp", "ativo"], keep="first")
    df = df.sort_values(["timestamp", "ativo"]).reset_index(drop=True)

    st.sidebar.write("**Ativos extraídos dos ROMs:**", df["ativo"].unique().tolist())
    return df

# ------------------------------------------------------------
# FUNÇÃO FALLBACK: CARREGAR DADOS ATUAIS DO UNIFICADO
# ------------------------------------------------------------
def carregar_atual_unificado() -> pd.DataFrame:
    arquivo = COLETAS_DIR / "DadosAtivosUnificados.json"
    if not arquivo.exists():
        st.sidebar.error("DadosAtivosUnificados.json não encontrado.")
        return pd.DataFrame()

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as e:
        st.sidebar.error(f"Erro ao ler DadosAtivosUnificados.json: {e}")
        return pd.DataFrame()

    ativos = dados.get("ativos", {})
    if not ativos:
        st.sidebar.warning("DadosAtivosUnificados.json não contém 'ativos'.")
        return pd.DataFrame()

    unificado_to_label = {
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
        variacao = item.get("variacao_pct", 0.0) or 0.0
        registros.append({
            "timestamp": ts,
            "ativo": label,
            "preco": float(preco),
            "variacao_pct": float(variacao),
        })

    if not registros:
        st.sidebar.warning("Nenhum ativo encontrado no DadosAtivosUnificados.json.")
        return pd.DataFrame()

    st.sidebar.write("**Ativos extraídos (fallback):**", [r["ativo"] for r in registros])
    return pd.DataFrame(registros)

# ------------------------------------------------------------
# FUNÇÃO: CALCULAR CORRELAÇÃO ENTRE ATIVOS
# ------------------------------------------------------------
def calcular_correlacao(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    ativos_validos = df.groupby("ativo").filter(lambda g: len(g) >= 3)["ativo"].unique()
    if len(ativos_validos) < 2:
        return pd.DataFrame()
    df_filtrado = df[df["ativo"].isin(ativos_validos)]
    pivot = df_filtrado.pivot(index="timestamp", columns="ativo", values="preco")
    if pivot.empty or len(pivot.columns) < 2:
        return pd.DataFrame()
    corr = pivot.pct_change().corr()
    return corr

# ------------------------------------------------------------
# FUNÇÃO AUXILIAR: EXIBIR GRÁFICO NORMALIZADO POR GRUPO
# ------------------------------------------------------------
def exibir_grafico_normalizado(df: pd.DataFrame, ativos_grupo: list, titulo: str):
    df_filtrado = df[df["ativo"].isin(ativos_grupo)]
    if df_filtrado.empty:
        st.info(f"Nenhum dado disponível para {titulo}.")
        return

    df_norm = df_filtrado.copy()
    df_norm["preco_norm"] = df_norm.groupby("ativo")["preco"].transform(
        lambda x: x / x.iloc[0] * 100 if len(x) > 0 else x
    )

    fig = px.line(
        df_norm,
        x="timestamp",
        y="preco_norm",
        color="ativo",
        color_discrete_map=CORES,
        title=f"Evolução normalizada (início = 100) – {titulo}",
        labels={"preco_norm": "Índice (base 100)", "timestamp": "Horário"},
    )
    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#e6edf3",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350,
    )
    fig.update_xaxes(gridcolor="#2a2d4a")
    fig.update_yaxes(gridcolor="#2a2d4a")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# FUNÇÃO AUXILIAR: EXIBIR GRÁFICOS INDIVIDUAIS POR GRUPO
# ------------------------------------------------------------
def exibir_graficos_individuais(df: pd.DataFrame, ativos_grupo: list):
    df_filtrado = df[df["ativo"].isin(ativos_grupo)]
    if df_filtrado.empty:
        return

    # Calcula variação percentual
    df_var = df_filtrado.copy()
    df_var["var_pct"] = df_var.groupby("ativo")["preco"].pct_change() * 100

    ativos_ordenados = sorted(ativos_grupo, key=lambda x: ativos_grupo.index(x))
    cols = st.columns(2)

    for i, ativo in enumerate(ativos_ordenados):
        with cols[i % 2]:
            df_plot = df_var[df_var["ativo"] == ativo]
            if df_plot.empty:
                continue
            fig = px.line(
                df_plot,
                x="timestamp",
                y="preco",
                title=f"{ativo}",
                labels={"preco": "Preço", "timestamp": ""},
                color_discrete_sequence=[CORES.get(ativo, "#ffffff")],
            )
            fig.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="#e6edf3",
                height=200,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False,
            )
            fig.update_xaxes(gridcolor="#2a2d4a")
            fig.update_yaxes(gridcolor="#2a2d4a")
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# INTERFACE STREAMLIT
# ------------------------------------------------------------
st.title("📈 Histórico Macro")
st.caption("Evolução de VIX, ADRs, Minério e Petróleo a partir dos arquivos de coleta")

st.sidebar.title("⚙️ Configurações")
max_pontos = st.sidebar.slider(
    "Número máximo de pontos (coletas)",
    min_value=5,
    max_value=120,
    value=60,
    step=5,
)

df = carregar_historico_rom()

if df.empty:
    st.error("❌ Nenhum dado disponível. Verifique os diagnósticos no sidebar.")
    st.stop()

df = df.sort_values("timestamp").tail(max_pontos)

st.sidebar.markdown("### Resumo")
st.sidebar.metric("Total de registros", len(df))
st.sidebar.metric("Ativos disponíveis", len(df["ativo"].unique()))
if not df.empty:
    st.sidebar.metric("Período", f"{df['timestamp'].min().strftime('%H:%M')} → {df['timestamp'].max().strftime('%H:%M')}")

# ------------------------------------------------------------
# SEÇÃO 1: ADRs Brasileiras
# ------------------------------------------------------------
st.markdown("### 🇧🇷 ADRs Brasileiras")
exibir_grafico_normalizado(df, GRUPO_ADRS, "ADRs")
exibir_graficos_individuais(df, GRUPO_ADRS)

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# SEÇÃO 2: Mercado Externo
# ------------------------------------------------------------
st.markdown("### 🌍 Mercado Externo (VIX, Minério, Petróleo)")
exibir_grafico_normalizado(df, GRUPO_EXTERNO, "Mercado Externo")
exibir_graficos_individuais(df, GRUPO_EXTERNO)

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ------------------------------------------------------------
# HEATMAP DE CORRELAÇÃO (GERAL)
# ------------------------------------------------------------
st.markdown("### 🔗 Correlação entre Ativos (Retornos)")

corr_matrix = calcular_correlacao(df)

if not corr_matrix.empty:
    fig_heat = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale="RdBu",
            zmid=0,
            text=corr_matrix.round(2).values,
            texttemplate="%{text}",
            textfont={"color": "#e6edf3", "size": 10},
        )
    )
    fig_heat.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#e6edf3",
        height=500,
        xaxis=dict(title="", tickangle=45),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("#### ⚡ Correlações mais altas")
    corr_abs = corr_matrix.abs().unstack()
    corr_abs = corr_abs[corr_abs.index.get_level_values(0) != corr_abs.index.get_level_values(1)]
    if not corr_abs.empty:
        top = corr_abs.sort_values(ascending=False).head(5)
        for (a, b), val in top.items():
            st.caption(f"**{a} × {b}**: {val:.2f}")
else:
    st.info("Dados insuficientes para calcular correlação.")

# ------------------------------------------------------------
# ÚLTIMOS VALORES E VARIAÇÕES (todos os ativos)
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
    if not df_anterior.empty:
        prev = df_anterior[df_anterior["ativo"] == ativo]
        var_real = (preco / prev.iloc[0]["preco"] - 1) * 100 if not prev.empty else None
    else:
        var_real = None
    delta = f"{var_real:+.2f}%" if var_real is not None else None
    cor = "normal" if var_real is not None and var_real > 0 else "inverse" if var_real is not None and var_real < 0 else "off"
    with cols[i]:
        st.metric(
            label=ativo,
            value=f"{preco:.2f}",
            delta=delta,
            delta_color=cor,
        )

# ------------------------------------------------------------
# RODAPÉ
# ------------------------------------------------------------
st.markdown("---")
if not df.empty:
    st.caption(f"Histórico baseado em {len(df)} registros de coleta • Última atualização: {ultimo_ts.strftime('%d/%m/%Y %H:%M:%S') if ultimo_ts else 'N/A'}")
else:
    st.caption("Sem dados históricos disponíveis.")