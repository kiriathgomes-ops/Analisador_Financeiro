# ============================================================
# PÁGINA: Análise Ações B3 × ADRs
# Dashboard de comparação entre ações locais e ADRs americanos
# ============================================================

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Garante import da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Ações B3 × ADRs",
    page_icon="📊",
    layout="wide",
)

# Tema escuro dos gráficos
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e6edf3", size=13),
    margin=dict(l=40, r=20, t=40, b=40),
)

st.title("📊 Ações B3 × ADRs")
st.caption("Comparativo de preços, variação e prêmio/desconto entre ações locais e seus ADRs")

# ------------------------------------------------------------
# Pares oficiais de comparação
# ------------------------------------------------------------
PARES = [
    {"acao": "VALE3",  "adr": "VALE_ADR",  "nome": "Vale"},
    {"acao": "PETR4",  "adr": "PETR_ADR",  "nome": "Petrobras"},
    {"acao": "ITUB4",  "adr": "ITUB_ADR",  "nome": "Itaú"},
    {"acao": "BBAS3",  "adr": "BBAS_ADR",  "nome": "Banco do Brasil"},
    {"acao": "BBDC4",  "adr": "BBD_ADR",   "nome": "Bradesco"},
    {"acao": "B3SA3",  "adr": "B3_ADR",    "nome": "B3"},
]

# ------------------------------------------------------------
# Carregar dados
# ------------------------------------------------------------
@st.cache_data(ttl=30)
def carregar_unificado():
    path = ROOT / "Coletas" / "DadosAtivosUnificados.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


dados = carregar_unificado()

if dados is None:
    st.error("Arquivo `Coletas/DadosAtivosUnificados.json` não encontrado. Execute o Coletor.py primeiro.")
    st.stop()

ativos = dados.get("ativos", {})
meta = dados.get("metadata", {})
timestamp = meta.get("timestamp", "—")

col_btn, col_info = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.caption(f"Última coleta: **{timestamp}** · Total de ativos: {meta.get('total_ativos', '—')}")

# ------------------------------------------------------------
# Montar DataFrame de comparação
# ------------------------------------------------------------
linhas = []
for p in PARES:
    acao = ativos.get(p["acao"], {})
    adr  = ativos.get(p["adr"], {})

    preco_acao = acao.get("preco")
    preco_adr  = adr.get("preco")
    var_acao   = acao.get("variacao_pct")
    var_adr    = adr.get("variacao_pct")
    status_acao = acao.get("status", "—")
    status_adr  = adr.get("status", "—")

    # Diferença de variação (ADR - Ação)
    delta_var = None
    if var_acao is not None and var_adr is not None:
        delta_var = round(var_adr - var_acao, 2)

    linhas.append({
        "Empresa": p["nome"],
        "Ação B3": p["acao"],
        "Preço Ação": preco_acao,
        "Var% Ação": var_acao,
        "ADR": p["adr"],
        "Preço ADR": preco_adr,
        "Var% ADR": var_adr,
        "Δ Var% (ADR − Ação)": delta_var,
        "Status Ação": status_acao,
        "Status ADR": status_adr,
    })

df = pd.DataFrame(linhas)

# ------------------------------------------------------------
# 1. Tabela principal
# ------------------------------------------------------------
st.subheader("Comparativo Ação × ADR")

def color_delta(val):
    if val is None or pd.isna(val):
        return ""
    if val > 0.15:
        return "background-color: rgba(0,180,0,0.25)"
    if val < -0.15:
        return "background-color: rgba(220,50,50,0.25)"
    return ""

styled = (
    df.style
    .format({
        "Preço Ação": "{:.2f}",
        "Preço ADR": "{:.2f}",
        "Var% Ação": "{:+.2f}%",
        "Var% ADR": "{:+.2f}%",
        "Δ Var% (ADR − Ação)": "{:+.2f}",
    }, na_rep="—")
    .map(color_delta, subset=["Δ Var% (ADR − Ação)"])
)

st.dataframe(styled, use_container_width=True, hide_index=True)

st.caption(
    "Δ Var% positivo = ADR subindo mais (ou caindo menos) que a ação local. "
    "Valores em destaque forte indicam divergência > 0,15 p.p."
)

# ------------------------------------------------------------
# 2. Gráfico de barras – Variação lado a lado
# ------------------------------------------------------------
st.subheader("Variação do dia (%)")

df_plot = df.dropna(subset=["Var% Ação", "Var% ADR"]).copy()
if not df_plot.empty:
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Ação B3",
        x=df_plot["Empresa"],
        y=df_plot["Var% Ação"],
        marker_color="#58a6ff",
        text=[f"{v:+.2f}%" for v in df_plot["Var% Ação"]],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="ADR",
        x=df_plot["Empresa"],
        y=df_plot["Var% ADR"],
        marker_color="#3fb950",
        text=[f"{v:+.2f}%" for v in df_plot["Var% ADR"]],
        textposition="outside",
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="group",
        yaxis_title="Variação %",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados de variação disponíveis para o gráfico.")

# ------------------------------------------------------------
# 3. Cards individuais por empresa
# ------------------------------------------------------------
st.subheader("Detalhe por empresa")

cols = st.columns(3)
for i, p in enumerate(PARES):
    with cols[i % 3]:
        acao = ativos.get(p["acao"], {})
        adr  = ativos.get(p["adr"], {})

        preco_acao = acao.get("preco")
        preco_adr  = adr.get("preco")
        var_acao   = acao.get("variacao_pct")
        var_adr    = adr.get("variacao_pct")

        with st.container(border=True):
            st.markdown(f"**{p['nome']}**")
            c1, c2 = st.columns(2)
            with c1:
                st.metric(
                    p["acao"],
                    f"{preco_acao:.2f}" if preco_acao is not None else "—",
                    delta=f"{var_acao:+.2f}%" if var_acao is not None else None,
                )
            with c2:
                st.metric(
                    p["adr"].replace("_ADR", ""),
                    f"{preco_adr:.2f}" if preco_adr is not None else "—",
                    delta=f"{var_adr:+.2f}%" if var_adr is not None else None,
                )

            if var_acao is not None and var_adr is not None:
                delta = var_adr - var_acao
                if abs(delta) < 0.15:
                    st.caption(f"Δ {delta:+.2f} p.p. · alinhados")
                elif delta > 0:
                    st.caption(f"Δ {delta:+.2f} p.p. · ADR mais forte")
                else:
                    st.caption(f"Δ {delta:+.2f} p.p. · Ação mais forte")

# ------------------------------------------------------------
# 4. EWZ (contexto Brasil)
# ------------------------------------------------------------
st.subheader("Contexto — EWZ (ETF Brasil)")

ewz = ativos.get("EWZ", {})
if ewz:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Preço EWZ", f"{ewz.get('preco', 0):.2f}")
    with c2:
        var = ewz.get("variacao_pct")
        st.metric("Variação", f"{var:+.2f}%" if var is not None else "—")
    with c3:
        st.metric("Status", ewz.get("status", "—"))
else:
    st.info("EWZ não encontrado na coleta.")

st.divider()
st.caption(
    "Fonte: DadosAtivosUnificados.json · Ações via MetaTrader 5 · ADRs/EWZ via Finnhub · "
    "Página gerada automaticamente a partir do Coletor."
)