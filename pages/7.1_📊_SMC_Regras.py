# -*- coding: utf-8 -*-
"""
Módulo: pages/7.1_📊_SMC_Regras.py
Versão: 4.2 - Candlestick + Zonas SMC (POC/VWAP/OB/FVG/BSL/SSL)
                  + Zoom inicial nas últimas pernadas
                  + Auto-refresh de 5 min (sincronizado com o Agendador)
Objetivo: Renderizar estruturas SMC/ICT em gráfico de candles reais (MT5)
         com todas as zonas institucionais sobrepostas.
         Exibe por padrão apenas os últimos N candles (pernadas recentes).
"""

import streamlit as st
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from config import FILE_SMC_REGRAS

# 🔄 Auto-refresh (instalar: pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_DISPONIVEL = True
except ImportError:
    AUTOREFRESH_DISPONIVEL = False


# ==============================================================================
# CONFIGURAÇÕES DE VISUALIZAÇÃO (AJUSTE AQUI O PADRÃO)
# ==============================================================================
QTD_CANDLES_PADRAO = 30              # Padrão: 30 candles M5 (~2.5 horas de pregão)
OPCOES_CANDLES = [30, 60, 100, 150, 200]

# Intervalo do auto-refresh em minutos (alinhado com Agendador.py)
INTERVALO_REFRESH_MIN = 5


# ==============================================================================
# CARREGAMENTO DEFENSIVO
# ==============================================================================
def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)  # Reduzido para 60s (sincronizado com autorefresh)
def carregar_candles_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 200):
    """Busca candles do MT5. Cache de 60s para alinhar com o autorefresh."""
    try:
        from Motor_SMC_Regras import carregar_mt5
        candles, simbolo_ok = carregar_mt5(symbol, timeframe_min, qtd, validar_pregao=False)
        return candles, simbolo_ok
    except Exception as e:
        return [], str(e)


# ==============================================================================
# CONFIG
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - SMC por Regras", layout="wide")


# ==============================================================================
# AUTO-REFRESH + CONTROLES NA SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Controles SMC")
    auto_refresh = st.checkbox(
        f"🔄 Auto-atualizar ({INTERVALO_REFRESH_MIN} min)",
        value=True,
        help="Atualiza a página automaticamente para buscar novos dados do pipeline.",
        key="smc_auto_refresh_toggle",
    )

    if auto_refresh and AUTOREFRESH_DISPONIVEL:
        st_autorefresh(
            interval=INTERVALO_REFRESH_MIN * 60 * 1000,
            key="smc_autorefresh_key",
        )
        st.caption(f"✅ Ativo — refresh a cada {INTERVALO_REFRESH_MIN} min")
    elif auto_refresh and not AUTOREFRESH_DISPONIVEL:
        st.warning("⚠️ Instale: `pip install streamlit-autorefresh`")
    else:
        st.caption("⏸️ Auto-refresh pausado")


dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)

# --- CABEÇALHO ---
st.markdown("<h2 style='color:#00d4ff;'>🧠 Smart Money Concepts (SMC) & ICT</h2>", unsafe_allow_html=True)

# Mostra o timestamp do JSON + horário da última leitura
ts_dados = dados_smc.get('timestamp', 'N/A')
ts_pagina = datetime.now().strftime("%H:%M:%S")
st.caption(f"Análise algorítmica pura (Sem IA) · Dados: **{ts_dados}** · Página lida às **{ts_pagina}**")

if not dados_smc or "erro" in dados_smc:
    st.error(f"⚠️ Erro ao carregar dados do Motor SMC: {dados_smc.get('erro', 'Arquivo não gerado ou sem candles suficientes')}")
    st.stop()


# ==============================================================================
# CONTROLE DE CANDLES VISÍVEIS (SELETOR)
# ==============================================================================
col_ctrl1, col_ctrl2 = st.columns([1, 3])

with col_ctrl1:
    qtd_visivel = st.selectbox(
        "🕯️ Candles visíveis:",
        options=OPCOES_CANDLES,
        index=OPCOES_CANDLES.index(QTD_CANDLES_PADRAO) if QTD_CANDLES_PADRAO in OPCOES_CANDLES else 0,
        help="Quantidade de candles M5 exibidos inicialmente. Para visão mais ampla, use o Profit.",
        key="smc_qtd_candles",
    )

with col_ctrl2:
    st.caption(
        f"Exibindo os **últimos {qtd_visivel} candles** (~{qtd_visivel * 5 // 60}h de pregão). "
        "Aumente no seletor ao lado ou abra o Profit para uma visão mais ampla."
    )


# ==============================================================================
# KPIs SUPERIORES
# ==============================================================================
vies = dados_smc.get("bias_direcional", "LATERAL")
confianca = dados_smc.get("confianca_visual", 0)
preco_atual = dados_smc.get("preco_atual", 0.0)

c1, c2, c3 = st.columns(3)

if vies == "ALTA":
    c1.markdown(
        f"<div style='background-color:rgba(0, 255, 136, 0.1); padding:10px; border-radius:8px; border-left:5px solid #00ff88;'>"
        f"📊 <b>Viés Estrutural HTF:</b><br>"
        f"<span style='font-size:1.5rem; color:#00ff88; font-weight:bold;'>🐂 BULLISH / ALTA</span></div>",
        unsafe_allow_html=True,
    )
elif vies == "BAIXA":
    c1.markdown(
        f"<div style='background-color:rgba(255, 107, 107, 0.1); padding:10px; border-radius:8px; border-left:5px solid #ff6b6b;'>"
        f"📊 <b>Viés Estrutural HTF:</b><br>"
        f"<span style='font-size:1.5rem; color:#ff6b6b; font-weight:bold;'>🐻 BEARISH / BAIXA</span></div>",
        unsafe_allow_html=True,
    )
else:
    c1.markdown(
        f"<div style='background-color:rgba(255, 255, 255, 0.05); padding:10px; border-radius:8px; border-left:5px solid #888;'>"
        f"📊 <b>Viés Estrutural HTF:</b><br>"
        f"<span style='font-size:1.5rem; color:#ccc; font-weight:bold;'>⚖️ LATERAL / RANGE</span></div>",
        unsafe_allow_html=True,
    )

c2.metric(
    "Confiança do Setup",
    f"{confianca}%",
    delta="Sinal Forte" if confianca >= 70 else "Aguardar Confluência",
    delta_color="normal" if confianca >= 70 else "off",
)
c3.metric("Último Preço (B3)", f"{preco_atual:,.0f} pts")

st.markdown("---")


# ==============================================================================
# GRÁFICO DE CANDLESTICK COM ZONAS SMC
# ==============================================================================
def render_grafico_candles(dados: dict, qtd_visivel: int = QTD_CANDLES_PADRAO) -> go.Figure:
    """
    Gráfico de candlestick do WIN M5 com sobreposição:
    - POC / VWAP de ontem
    - Order Blocks (bandas horizontais)
    - Fair Value Gaps abertos (zonas)
    - BSL / SSL (linhas de liquidez)
    - Entrada / Stop / Alvos
    - Swing Highs / Lows (marcadores)
    - BOS / CHoCH (anotações)

    Parâmetros:
        qtd_visivel: número de candles M5 exibidos (foco nas últimas pernadas).
    """
    # ---------- Coleta de dados do SMC ----------
    niveis = dados.get("niveis_institucionais", {}) or {}
    poc = niveis.get("poc_ontem", 0.0)
    vwap = niveis.get("vwap_ontem", 0.0)

    obs = dados.get("order_blocks", []) or []
    fvgs = dados.get("fair_value_gaps", []) or []
    liq = dados.get("liquidez", {}) or {}
    bsl = liq.get("bsl", []) or []
    ssl = liq.get("ssl", []) or []

    entrada = dados.get("entrada_sugerida")
    stop = dados.get("stop_sugerido")
    alvos = dados.get("alvos", []) or []

    swings = list(dados.get("swings_recentes", []) or [])
    eventos = list(dados.get("eventos_estrutura", []) or [])

    # ---------- Busca candles do MT5 ----------
    # Sempre puxamos 200 para ter contexto, mas exibimos apenas os últimos N
    candles, simbolo_ok = carregar_candles_mt5("WIN$", 5, 200)

    # ---------- FATIA APENAS AS ÚLTIMAS PERNADAS ----------
    if candles and qtd_visivel and qtd_visivel < len(candles):
        candles = candles[-qtd_visivel:]

        # Janela temporal visível (para filtrar swings e eventos fora do range)
        t_min = candles[0]["time"]
        t_max = candles[-1]["time"]

        # Filtra swings que caem dentro da janela visível
        swings = [s for s in swings if t_min <= str(s.get("time", "")) <= t_max]

        # Filtra eventos (BOS/CHoCH) que caem dentro da janela visível
        eventos = [e for e in eventos if t_min <= str(e.get("time", "")) <= t_max]

    fig = go.Figure()

    # ---------- 1. Zonas horizontais (shapes) — por baixo dos candles ----------

    # Order Blocks
    for ob in obs:
        tipo = ob.get("tipo", "")
        low = ob.get("low")
        high = ob.get("high")
        if low is None or high is None:
            continue
        cor_fill = "rgba(0, 255, 136, 0.14)" if tipo == "COMPRA" else "rgba(255, 107, 107, 0.14)"
        cor_borda = "#00ff88" if tipo == "COMPRA" else "#ff6b6b"
        validado = ob.get("validado_por", "")
        label = f"OB {tipo} [{validado}]" if validado else f"OB {tipo}"

        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=low, y1=high,
            fillcolor=cor_fill,
            line=dict(color=cor_borda, width=1, dash="dot"),
            layer="below",
        )
        fig.add_annotation(
            xref="paper", x=0.005,
            yref="y", y=(low + high) / 2,
            text=label,
            showarrow=False,
            font=dict(color=cor_borda, size=10),
            xanchor="left",
        )

    # FVGs abertos
    for fvg in fvgs:
        if fvg.get("preenchido"):
            continue
        tipo = fvg.get("tipo", "")
        sup = fvg.get("superior")
        inf = fvg.get("inferior")
        if sup is None or inf is None:
            continue
        cor = "rgba(0, 212, 255, 0.10)" if tipo == "COMPRA" else "rgba(255, 165, 0, 0.10)"
        cor_borda = "#00d4ff" if tipo == "COMPRA" else "#ffa500"

        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=inf, y1=sup,
            fillcolor=cor,
            line=dict(color=cor_borda, width=1, dash="dashdot"),
            layer="below",
        )
        fig.add_annotation(
            xref="paper", x=0.995,
            yref="y", y=(inf + sup) / 2,
            text=f"FVG {tipo}",
            showarrow=False,
            font=dict(color=cor_borda, size=9),
            xanchor="right",
        )

    # ---------- 2. Candles ----------
    if candles:
        x_vals = [c["time"] for c in candles]
        fig.add_trace(go.Candlestick(
            x=x_vals,
            open=[c["open"] for c in candles],
            high=[c["high"] for c in candles],
            low=[c["low"] for c in candles],
            close=[c["close"] for c in candles],
            name="WIN M5",
            increasing=dict(line=dict(color="#00ff88", width=1), fillcolor="#00ff88"),
            decreasing=dict(line=dict(color="#ff6b6b", width=1), fillcolor="#ff6b6b"),
            hovertext=[
                f"O: {c['open']:,.0f}<br>H: {c['high']:,.0f}<br>L: {c['low']:,.0f}<br>C: {c['close']:,.0f}<br>V: {c['volume']:,.0f}"
                for c in candles
            ],
            hoverinfo="x+text",
        ))
        x_min = x_vals[0]
        x_max = x_vals[-1]
    else:
        # Fallback: sem candles do MT5 — usa range fictício
        st.warning(f"⚠️ Não foi possível buscar candles do MT5 ({simbolo_ok}). Exibindo apenas níveis.")
        x_min, x_max = 0, 1

    # ---------- 3. Níveis horizontais ----------

    if candles:
        x_line = [x_min, x_max]
    else:
        x_line = [0, 1]

    # POC
    if poc and poc > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[poc, poc],
            mode="lines",
            name=f"POC Ontem ({poc:,.0f})",
            line=dict(color="#a855f7", width=2, dash="dot"),
            hovertemplate=f"<b>POC Ontem</b><br>{poc:,.0f} pts<extra></extra>",
        ))

    # VWAP
    if vwap and vwap > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[vwap, vwap],
            mode="lines",
            name=f"VWAP Ontem ({vwap:,.1f})",
            line=dict(color="#9ca3af", width=2, dash="dot"),
            hovertemplate=f"<b>VWAP Ontem</b><br>{vwap:,.1f} pts<extra></extra>",
        ))

    # Entrada
    if entrada and entrada > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[entrada, entrada],
            mode="lines",
            name=f"Entrada ({entrada:,.0f})",
            line=dict(color="#00d4ff", width=2, dash="dash"),
            hovertemplate=f"<b>Entrada</b><br>{entrada:,.0f}<extra></extra>",
        ))

    # Stop
    if stop and stop > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[stop, stop],
            mode="lines",
            name=f"Stop ({stop:,.0f})",
            line=dict(color="#ff3d00", width=2, dash="dash"),
            hovertemplate=f"<b>Stop</b><br>{stop:,.0f}<extra></extra>",
        ))

    # Alvos
    for i, alvo in enumerate(alvos[:2]):
        if alvo and alvo > 0:
            fig.add_trace(go.Scatter(
                x=x_line, y=[alvo, alvo],
                mode="lines",
                name=f"Alvo {i+1} ({alvo:,.0f})",
                line=dict(color="#00ff88", width=1.5, dash="longdash"),
                hovertemplate=f"<b>Alvo {i+1}</b><br>{alvo:,.0f}<extra></extra>",
            ))

    # BSL
    for i, nivel in enumerate(bsl[:3]):
        fig.add_trace(go.Scatter(
            x=x_line, y=[nivel, nivel],
            mode="lines",
            name=f"BSL #{i+1} ({nivel:,.0f})",
            line=dict(color="#00bfff", width=1, dash="dot"),
            opacity=0.6,
            hovertemplate=f"<b>BSL</b><br>{nivel:,.0f}<extra></extra>",
        ))

    # SSL
    for i, nivel in enumerate(ssl[:3]):
        fig.add_trace(go.Scatter(
            x=x_line, y=[nivel, nivel],
            mode="lines",
            name=f"SSL #{i+1} ({nivel:,.0f})",
            line=dict(color="#ff6b6b", width=1, dash="dot"),
            opacity=0.6,
            hovertemplate=f"<b>SSL</b><br>{nivel:,.0f}<extra></extra>",
        ))

    # ---------- 4. Swing Highs / Lows (marcadores) ----------
    if candles and swings:
        swings_high = [s for s in swings if str(s.get("tipo", "")).startswith("HIGH")]
        swings_low = [s for s in swings if str(s.get("tipo", "")).startswith("LOW")]

        if swings_high:
            fig.add_trace(go.Scatter(
                x=[s["time"] for s in swings_high],
                y=[s["preco"] for s in swings_high],
                mode="markers",
                name="Swing High",
                marker=dict(color="#ff6b6b", size=8, symbol="triangle-down", line=dict(color="#ffffff", width=1)),
                hovertemplate="<b>Swing High</b><br>%{y:,.0f}<extra></extra>",
            ))

        if swings_low:
            fig.add_trace(go.Scatter(
                x=[s["time"] for s in swings_low],
                y=[s["preco"] for s in swings_low],
                mode="markers",
                name="Swing Low",
                marker=dict(color="#00ff88", size=8, symbol="triangle-up", line=dict(color="#ffffff", width=1)),
                hovertemplate="<b>Swing Low</b><br>%{y:,.0f}<extra></extra>",
            ))

    # ---------- 5. BOS / CHoCH (anotações) ----------
    if candles and eventos:
        for e in eventos[-4:]:
            tipo_ev = e.get("tipo", "")
            direcao = e.get("direcao", "")
            preco_ev = e.get("preco")
            time_ev = e.get("time")
            if preco_ev is None or time_ev is None:
                continue

            cor = "#00d4ff" if direcao == "ALTA" else "#ff6b6b"
            simbolo_seta = "↑" if direcao == "ALTA" else "↓"
            label = f"{tipo_ev} {simbolo_seta}"

            fig.add_annotation(
                x=time_ev, y=preco_ev,
                text=label,
                showarrow=True,
                arrowhead=2,
                arrowsize=1.2,
                arrowcolor=cor,
                ax=0,
                ay=-30 if direcao == "ALTA" else 30,
                font=dict(color=cor, size=10, family="Arial Black"),
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor=cor,
                borderwidth=1,
                borderpad=2,
            )

    # ---------- 6. Preço atual (linha) ----------
    if preco_atual and preco_atual > 0:
        fig.add_hline(
            y=preco_atual,
            line=dict(color="white", width=1.5, dash="dot"),
            annotation_text=f"  Atual: {preco_atual:,.0f}",
            annotation_position="right",
            annotation_font=dict(color="white", size=11),
        )

    # ---------- Layout ----------
    fig.update_layout(
        title=dict(
            text=f"<b>WIN M5 — Zonas Institucionais SMC</b> · "
                 f"Viés: <span style='color:{'#00ff88' if vies == 'ALTA' else '#ff6b6b' if vies == 'BAIXA' else '#ccc'}'>{vies}</span> · "
                 f"Confiança: {confianca}% · "
                 f"<span style='font-size:0.85em; color:#8b949e;'>últimos {len(candles) if candles else 0} candles</span>",
            font=dict(size=15),
        ),
        height=680,
        margin=dict(l=40, r=120, t=60, b=40),
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#1f2937",
            rangeslider=dict(visible=False),
            type="date" if candles else "-",
        ),
        yaxis=dict(
            title="Pontos (WIN)",
            showgrid=True,
            gridcolor="#1f2937",
            zeroline=False,
            autorange=True,
            side="right",
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(22, 27, 34, 0.85)",
            bordercolor="#30363d",
            borderwidth=1,
            font=dict(size=10),
        ),
        hovermode="x unified",
    )

    # Remove rangeslider nativo
    fig.update_xaxes(rangeslider_visible=False)

    return fig


# ==============================================================================
# RENDERIZAÇÃO
# ==============================================================================
st.markdown("### 📈 Gráfico de Candles com Zonas SMC sobrepostas")
st.caption(
    "Candles M5 do WIN (via MT5) com sobreposição de POC/VWAP, Order Blocks, "
    "Fair Value Gaps, liquidez (BSL/SSL), swings, BOS/CHoCH e setup operacional."
)

with st.expander("ℹ️ Como ler este gráfico", expanded=False):
    st.markdown("""
| Elemento | Significado |
|---|---|
| **🟢🔴 Candles** | WIN M5 (verde = alta, vermelho = baixa) |
| **🟪 POC Ontem** | Preço de maior volume do dia anterior — ímã de preço |
| **⬜ VWAP Ontem** | Preço médio ponderado por volume do dia anterior |
| **⬜ Linha pontilhada branca** | Preço atual em tempo real |
| **🟢 Banda verde** | Order Block de COMPRA (suporte institucional) |
| **🔴 Banda vermelha** | Order Block de VENDA (resistência institucional) |
| **🔵 Banda azul clara** | FVG de compra aberto (imbalance) |
| **🟠 Banda laranja** | FVG de venda aberto |
| **🔻 Triângulos vermelhos** | Swing Highs (topos) |
| **🔺 Triângulos verdes** | Swing Lows (fundos) |
| **🩵 BSL** | Liquidez acima (stop de compradores) |
| **🔴 SSL** | Liquidez abaixo (stop de vendedores) |
| **↑ BOS/CHoCH ALTA** | Rompimento de estrutura para cima |
| **↓ BOS/CHoCH BAIXA** | Rompimento de estrutura para baixo |
| **🔵 Entrada / 🔴 Stop / 🟢 Alvos** | Setup operacional gerado pelo motor |
""")

fig_smc = render_grafico_candles(dados_smc, qtd_visivel=qtd_visivel)
st.plotly_chart(fig_smc, use_container_width=True, config={"displayModeBar": False})

# ---------- Sumário de distâncias ----------
st.markdown("##### 📌 Distâncias até o preço atual")
d1, d2, d3, d4 = st.columns(4)

poc = dados_smc.get("niveis_institucionais", {}).get("poc_ontem", 0.0)
vwap = dados_smc.get("niveis_institucionais", {}).get("vwap_ontem", 0.0)

if preco_atual and poc:
    d_poc = preco_atual - poc
    d1.metric("Δ até POC", f"{d_poc:+,.0f} pts", delta_color="normal" if d_poc > 0 else "inverse")
else:
    d1.metric("Δ até POC", "—")

if preco_atual and vwap:
    d_vwap = preco_atual - vwap
    d2.metric("Δ até VWAP", f"{d_vwap:+,.0f} pts", delta_color="normal" if d_vwap > 0 else "inverse")
else:
    d2.metric("Δ até VWAP", "—")

bsl_list = dados_smc.get("liquidez", {}).get("bsl", [])
bsl_acima = sorted([x for x in bsl_list if x > (preco_atual or 0)])
if bsl_acima and preco_atual:
    prox_bsl = bsl_acima[0]
    d3.metric("Próx. BSL (acima)", f"{prox_bsl:,.0f}", f"{prox_bsl - preco_atual:+,.0f} pts")
else:
    d3.metric("Próx. BSL (acima)", "—")

ssl_list = dados_smc.get("liquidez", {}).get("ssl", [])
ssl_abaixo = sorted([x for x in ssl_list if x < (preco_atual or 0)], reverse=True)
if ssl_abaixo and preco_atual:
    prox_ssl = ssl_abaixo[0]
    d4.metric("Próx. SSL (abaixo)", f"{prox_ssl:,.0f}", f"{prox_ssl - preco_atual:+,.0f} pts")
else:
    d4.metric("Próx. SSL (abaixo)", "—")

st.markdown("---")


# ==============================================================================
# PARÂMETROS DE EXECUÇÃO
# ==============================================================================
st.markdown("### 🎯 Parâmetros de Execução Gerados pelo Motor")
col_trade, col_status_filtro = st.columns([2, 1])

with col_trade:
    entrada = dados_smc.get("entrada_sugerida")
    stop = dados_smc.get("stop_sugerido")
    alvos = dados_smc.get("alvos", [])

    if entrada and stop:
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.markdown(
            f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>"
            f"🟢 <b>ORDEM BUY/SELL STOP:</b><br>"
            f"<span style='font-size:1.4rem; font-weight:bold; color:#00d4ff;'>{entrada:,.0f}</span></div>",
            unsafe_allow_html=True,
        )
        t_col2.markdown(
            f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>"
            f"🛑 <b>STOP LOSS TÉCNICO:</b><br>"
            f"<span style='font-size:1.4rem; font-weight:bold; color:#ff6b6b;'>{stop:,.0f}</span></div>",
            unsafe_allow_html=True,
        )
        alvos_txt = " | ".join([f"{x:,.0f}" for x in alvos]) if alvos else "Aguardando Alvo por Liquidez"
        t_col3.markdown(
            f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>"
            f"🏁 <b>ALVOS DE MITIGAÇÃO:</b><br>"
            f"<span style='font-size:1.1rem; font-weight:bold; color:#00ff88;'>{alvos_txt}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("⚖️ **Modo de Observação Ativo:** O preço atual não mitigou nenhum Order Block relevante com confirmação de volume.")

with col_status_filtro:
    meta = dados_smc.get("metadados", {})
    vol_filtro = meta.get("filtro_volume_real_aplicado", False)

    st.markdown("**Status das Validações:**")
    st.markdown(f"• Filtro de Volume: {'✅ **ATIVO**' if vol_filtro else '❌ Inativo'}")
    st.markdown(f"• Candles (Lookback): `{meta.get('n_candles', 0)}` bars")
    st.markdown(f"• Swings Mapeados: `{meta.get('n_swings', 0)}`")
    st.markdown(f"• Motor: `v{meta.get('versao_motor', 'N/A')}`")

st.markdown("---")


# ==============================================================================
# ESTRUTURAS INSTITUCIONAIS
# ==============================================================================
col_ob, col_fvg, col_liq = st.columns(3)

with col_ob:
    st.markdown("#### 🏢 Order Blocks")
    obs = dados_smc.get("order_blocks", [])
    if obs:
        for ob in obs:
            cor = "#00ff88" if ob["tipo"] == "COMPRA" else "#ff6b6b"
            validado = ob.get("validado_por", "")
            badge = f" <span style='color:#00d4ff; font-size:0.8em;'>[{validado}]</span>" if validado else ""
            st.markdown(f"""
            <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                🔹 <b>OB de {ob['tipo']}</b>{badge}<br>
                • Ref: <b>{ob['preco']:,.0f}</b><br>
                • Range: {ob['low']:,.0f} - {ob['high']:,.0f}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Nenhum Order Block ativo detectado.")

with col_fvg:
    st.markdown("#### 🕳️ Fair Value Gaps")
    fvgs = dados_smc.get("fair_value_gaps", [])
    if fvgs:
        for fvg in fvgs:
            cor = "#00ff88" if fvg["tipo"] == "COMPRA" else "#ff6b6b"
            st.markdown(f"""
            <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                🔸 <b>FVG {fvg['tipo']}</b><br>
                • Faixa: {fvg['inferior']:,.0f} ➔ {fvg['superior']:,.0f}<br>
                • Status: {'⚠️ Preenchido' if fvg.get('preenchido') else '🟢 Aberto'}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Nenhum FVG em aberto.")

with col_liq:
    st.markdown("#### 🎯 Liquidez Institucional")
    liq = dados_smc.get("liquidez", {})
    bsl = liq.get("bsl", [])
    ssl = liq.get("ssl", [])

    st.markdown("**🌐 BSL (Topos)**")
    if bsl:
        for p in bsl:
            st.markdown(f"• `{p:,.0f}` — *Equal Highs*")
    else:
        st.caption("Sem BSL mapeado.")

    st.markdown("**🩸 SSL (Fundos)**")
    if ssl:
        for p in ssl:
            st.markdown(f"• `{p:,.0f}` — *Equal Lows*")
    else:
        st.caption("Sem SSL mapeado.")

st.markdown("---")


# ==============================================================================
# CENÁRIOS E NÍVEIS INSTITUCIONAIS
# ==============================================================================
st.markdown("### 🗺️ Cenários Operacionais Mapeados")
cenarios = dados_smc.get("zonas_de_interesse_e_cenarios", [])
if cenarios:
    for i, cenario in enumerate(cenarios, start=1):
        if "DIVERGÊNCIA" in cenario:
            st.warning(f"**{i}.** {cenario}")
        else:
            st.markdown(f"**{i}.** {cenario}")
else:
    st.caption("Aguardando consolidação do range.")

st.markdown("---")
st.markdown("### 🏦 Níveis Institucionais (Resumo)")

ni1, ni2, ni3, ni4 = st.columns(4)
niveis = dados_smc.get("niveis_institucionais", {})
poc_v = niveis.get("poc_ontem", 0.0)
vwap_v = niveis.get("vwap_ontem", 0.0)
ob_alin = niveis.get("ob_alinhado_com_poc", False)

ni1.metric("POC Ontem", f"{poc_v:,.0f} pts")
ni2.metric("VWAP Ontem", f"{vwap_v:,.1f} pts")
ni3.metric("Preço Atual", f"{preco_atual:,.0f} pts")
ni4.metric("OB Alinhado com POC", "🟢 SIM" if ob_alin else "⚪ NÃO")

if preco_atual and poc_v:
    dist_poc = preco_atual - poc_v
    if abs(dist_poc) <= 100:
        st.success(f"📌 Preço **sobre a POC** de ontem ({dist_poc:+.0f} pts) — equilíbrio institucional.")
    elif dist_poc > 0:
        st.info(f"📌 Preço **{dist_poc:+,.0f} pts acima** da POC — viés comprador vs. referência.")
    else:
        st.warning(f"📌 Preço **{dist_poc:+,.0f} pts abaixo** da POC — viés vendedor vs. referência.")