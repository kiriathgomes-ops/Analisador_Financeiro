# ============================================================
# PÁGINA: Previsão de Abertura WINFUT
# FASE 7 — Dashboard operacional V2 + Plotly
#
# Visualizações:
#   - Barras de comportamentos (Plotly)
#   - Gauge distância / posição vs ajuste
#   - Níveis (ajuste, last, pivots)
#   - Contexto externo (barras de variação)
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Garante import da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.core.services.win_session_builder import build_win_session
from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura
from v2.core.services.session_history import SessionHistoryService, salvar_sessao_hoje

st.set_page_config(
    page_title="Previsão Abertura WINFUT",
    page_icon="📈",
    layout="wide",
)

# Tema escuro dos gráficos
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e6edf3", size=13),
    margin=dict(l=40, r=20, t=40, b=40),
)

st.title("📈 Previsão de Abertura — WINFUT")
st.caption("Cenários em relação ao ajuste · Não é ordem de compra/venda")

# ------------------------------------------------------------
# Carregar dados
# ------------------------------------------------------------
@st.cache_data(ttl=60)
def carregar():
    session = build_win_session()
    cenario = gerar_cenario_abertura(session)
    session.cenario = cenario
    return session, cenario


try:
    session, cenario = carregar()
except Exception as e:
    st.error(f"Falha ao montar WinSession: {e}")
    st.stop()

# ------------------------------------------------------------
# Ações
# ------------------------------------------------------------
col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_b:
    if st.button("💾 Gravar no histórico", use_container_width=True):
        path = salvar_sessao_hoje(session, cenario, tag="ui")
        st.success(f"Salvo: {path.name}")

# ------------------------------------------------------------
# 1. Referências de preço
# ------------------------------------------------------------
st.subheader("Referências")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Contrato", session.metadata.contrato_principal or "—")
with c2:
    st.metric("Ajuste", f"{session.precos.ajuste:,.0f}" if session.precos.ajuste else "—")
with c3:
    st.metric("Last MT5", f"{session.precos.last_mt5:,.0f}" if session.precos.last_mt5 else "—")
with c4:
    dist = session.distancias.last_vs_ajuste_pts
    st.metric(
        "Distância",
        f"{dist:+,.0f} pts" if dist is not None else "—",
        delta=f"{session.distancias.last_vs_ajuste_pct:+.3f}%" if session.distancias.last_vs_ajuste_pct else None,
    )
with c5:
    pos = cenario.relacao_com_ajuste.posicao or "—"
    cor = {"ACIMA": "🟢", "ABAIXO": "🔴", "NO_AJUSTE": "🟡"}.get(pos, "⚪")
    st.metric("Posição", f"{cor} {pos}")

st.divider()

# ------------------------------------------------------------
# 2. Cenário + Gauge de distância
# ------------------------------------------------------------
st.subheader("Cenário principal")

dir_ = cenario.direcao_provavel or "NEUTRO"
prob = cenario.probabilidade_direcao
conf = cenario.confianca_geral
badge = {"ALTA": "🟢 ALTA", "BAIXA": "🔴 BAIXA", "NEUTRO": "🟡 NEUTRO"}.get(dir_, dir_)

col1, col2 = st.columns([1.4, 1])

with col1:
    st.markdown(f"### {badge}")
    st.write(cenario.relacao_com_ajuste.cenario_principal or "—")
    if cenario.cenario_alternativo:
        st.info(f"**Alternativo:** {cenario.cenario_alternativo}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Prob. direção", f"{prob:.0f}%" if prob else "—")
    m2.metric("Confiança", f"{conf:.0f}%" if conf else "—")
    m3.metric(
        "Prob. cenário",
        f"{cenario.relacao_com_ajuste.probabilidade_cenario:.0f}%"
        if cenario.relacao_com_ajuste.probabilidade_cenario
        else "—",
    )

with col2:
    # Gauge: distância last vs ajuste
    dist_val = float(dist) if dist is not None else 0.0
    # Escala simétrica em torno de 0
    limite = max(400, abs(dist_val) * 1.5, 200)

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=dist_val,
            delta={"reference": 0, "relative": False, "valueformat": "+.0f"},
            number={"suffix": " pts", "font": {"size": 28}},
            title={"text": "Last × Ajuste", "font": {"size": 16}},
            gauge={
                "axis": {"range": [-limite, limite], "tickwidth": 1},
                "bar": {"color": "#00c853" if dist_val >= 0 else "#ff3d00"},
                "bgcolor": "#1a1c23",
                "borderwidth": 0,
                "steps": [
                    {"range": [-limite, -150], "color": "#3d1515"},
                    {"range": [-150, -50], "color": "#2a2210"},
                    {"range": [-50, 50], "color": "#1a2a1a"},
                    {"range": [50, 150], "color": "#1a2a1a"},
                    {"range": [150, limite], "color": "#153d15"},
                ],
                "threshold": {
                    "line": {"color": "#ffc107", "width": 3},
                    "thickness": 0.8,
                    "value": 0,
                },
            },
        )
    )
    fig_gauge.update_layout(
        **PLOTLY_LAYOUT,
        height=260,
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

st.divider()

# ------------------------------------------------------------
# 3. Comportamentos (barras Plotly)
# ------------------------------------------------------------
st.subheader("Comportamentos possíveis")

cb = cenario.comportamentos
labels = [
    "Romper e continuar",
    "Testar e rejeitar",
    "Testar e recuperar",
    "Retornar ao ajuste",
    "Falso rompimento",
]
valores = [
    cb.romper_e_continuar or 0,
    cb.testar_e_rejeitar or 0,
    cb.testar_e_recuperar or 0,
    cb.retornar_ao_ajuste or 0,
    cb.falso_rompimento or 0,
]
cores = ["#00c853", "#ff9800", "#42a5f5", "#ab47bc", "#ff3d00"]

fig_comp = go.Figure(
    go.Bar(
        x=valores,
        y=labels,
        orientation="h",
        marker_color=cores,
        text=[f"{v:.0f}%" for v in valores],
        textposition="outside",
        cliponaxis=False,
    )
)
fig_comp.update_layout(
    **PLOTLY_LAYOUT,
    height=280,
    xaxis=dict(title="Probabilidade (%)", range=[0, max(valores + [40]) * 1.25], gridcolor="#2a2d4a"),
    yaxis=dict(autorange="reversed"),
    showlegend=False,
)
st.plotly_chart(fig_comp, use_container_width=True)
st.caption("Heurística inicial — será refinada com histórico estatístico.")

st.divider()

# ------------------------------------------------------------
# 4. Níveis + Contexto (dois gráficos)
# ------------------------------------------------------------
col_n, col_x = st.columns(2)

with col_n:
    st.subheader("Níveis de preço")
    n = session.niveis
    nomes = []
    precos = []
    cores_n = []

    mapa_niveis = [
        ("R2", n.r2, "#ef5350"),
        ("R1", n.r1, "#ff8a65"),
        ("Last", session.precos.last_mt5, "#00e676"),
        ("Ajuste", session.precos.ajuste, "#ffc107"),
        ("PP", n.pivot_pp, "#90caf9"),
        ("S1", n.s1, "#81c784"),
        ("S2", n.s2, "#66bb6a"),
    ]
    for nome, val, cor in mapa_niveis:
        if val is not None:
            nomes.append(nome)
            precos.append(val)
            cores_n.append(cor)

    if precos:
        fig_niv = go.Figure(
            go.Bar(
                x=nomes,
                y=precos,
                marker_color=cores_n,
                text=[f"{p:,.0f}" for p in precos],
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig_niv.update_layout(
            **PLOTLY_LAYOUT,
            height=320,
            yaxis=dict(title="Pontos", gridcolor="#2a2d4a"),
            showlegend=False,
        )
        st.plotly_chart(fig_niv, use_container_width=True)
    else:
        st.write("Níveis indisponíveis.")

with col_x:
    st.subheader("Contexto externo (variação %)")
    ctx = session.contexto
    ctx_labels = []
    ctx_vals = []

    pares = [
        ("VIX", ctx.vix.variacao_pct),
        ("ES", ctx.sp500_fut.variacao_pct),
        ("NQ", ctx.nasdaq_fut.variacao_pct),
        ("DXY", ctx.dxy.variacao_pct),
        ("USD/BRL", ctx.usd_brl.variacao_pct),
        ("ADRs", ctx.indicador_adrs),
        ("Minério", ctx.iron_ore.variacao_pct),
        ("Petróleo", ctx.crude_oil.variacao_pct),
    ]
    for nome, val in pares:
        if val is not None:
            ctx_labels.append(nome)
            ctx_vals.append(val)

    if ctx_vals:
        cores_ctx = ["#00c853" if v >= 0 else "#ff3d00" for v in ctx_vals]
        fig_ctx = go.Figure(
            go.Bar(
                x=ctx_labels,
                y=ctx_vals,
                marker_color=cores_ctx,
                text=[f"{v:+.2f}%" for v in ctx_vals],
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig_ctx.update_layout(
            **PLOTLY_LAYOUT,
            height=320,
            yaxis=dict(title="Variação %", gridcolor="#2a2d4a", zeroline=True, zerolinecolor="#ffc107"),
            showlegend=False,
        )
        st.plotly_chart(fig_ctx, use_container_width=True)
    else:
        st.write("Contexto indisponível.")

    # Texto resumido
    if cenario.contexto_resumo:
        with st.expander("Detalhe textual"):
            for linha in cenario.contexto_resumo:
                st.write(f"• {linha}")

st.divider()

# ------------------------------------------------------------
# 5. Histórico recente (timeline simples)
# ------------------------------------------------------------
st.subheader("Histórico recente")

try:
    svc = SessionHistoryService()
    recentes = svc.resumo_recente(10)
    if not recentes:
        st.write("Nenhum histórico ainda. Use **Gravar no histórico**.")
    else:
        datas = [r.get("data") for r in recentes]
        dists = [r.get("distancia_pts") or 0 for r in recentes]
        cores_h = ["#00c853" if d >= 0 else "#ff3d00" for d in dists]

        fig_hist = go.Figure()
        fig_hist.add_trace(
            go.Scatter(
                x=datas,
                y=dists,
                mode="lines+markers",
                line=dict(color="#90caf9", width=2),
                marker=dict(size=10, color=cores_h),
                text=[
                    f"{r.get('posicao')} · {r.get('direcao')}<br>{r.get('cenario_principal', '')[:80]}"
                    for r in recentes
                ],
                hoverinfo="text+y",
            )
        )
        fig_hist.add_hline(y=0, line_dash="dot", line_color="#ffc107")
        fig_hist.update_layout(
            **PLOTLY_LAYOUT,
            height=280,
            yaxis=dict(title="Distância last × ajuste (pts)", gridcolor="#2a2d4a"),
            xaxis=dict(title="Data"),
            showlegend=False,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        with st.expander("Lista"):
            for r in reversed(recentes):
                st.write(
                    f"**{r.get('data')}** · {r.get('contrato')} · "
                    f"Ajuste {r.get('ajuste')} · Last {r.get('last_mt5')} · "
                    f"{r.get('distancia_pts'):+.0f} pts · {r.get('posicao')} · {r.get('direcao')}"
                )
except Exception as e:
    st.write(f"Histórico indisponível: {e}")

st.caption(
    f"Fonte last: {session.metadata.fonte_last or '—'} · "
    f"Coleta: {session.metadata.timestamp_coleta or '—'} · "
    "Assistente de cenário — não é recomendação de trade."
)
