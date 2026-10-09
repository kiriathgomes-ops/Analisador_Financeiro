# -*- coding: utf-8 -*-
"""
Módulo: pages/7.1_📊_SMC_Regras.py
Versão: 4.8 - Refresh independente por seção (dados + gráficos)
Objetivo: Renderizar estruturas SMC/ICT em gráfico de candles reais (MT5).

fix86/89/90/91/92: rangebreaks emendam overnight + fim de semana.
fix93: refresh por TF nos gráficos (M1=60s, M5/M15=300s).
fix94: legenda afastada + fonte maior.
fix95: legenda ordenada por valor decrescente.
fix96: seções reordenadas por fluxo de decisão + sidebar com lembrete.
fix97: CSS titulos maiores + cenarios sem numeracao.
fix98: fragments por seção de dados (300s) — dados atualizam sem F5.
"""

import streamlit as st
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from config import FILE_SMC_REGRAS


# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
QTD_CANDLES_PADRAO = 30
OPCOES_CANDLES = [30, 60, 100, 150, 200]

QTD_CANDLES_POR_TF = {
    1:  60,
    5:  30,
    15: 20,
}
OPCOES_CANDLES_POR_TF = {
    1:  [30, 60, 120, 240, 480, 960],
    5:  [30, 60, 100, 150, 200],
    15: [10, 20, 40, 60, 80],
}

# fix93: refresh dos graficos (segundos)
REFRESH_SEG_POR_TF = {
    1:  60,
    5:  300,
    15: 300,
}

# fix98: refresh das secoes de dados (alinhado com motor SMC — 5 min)
REFRESH_SEG_DADOS = 300


# ==============================================================================
# RANGEBREAKS
# ==============================================================================
RANGEBREAKS_B3 = [
    dict(bounds=["sat", "mon"]),
    dict(bounds=[18.5, 9], pattern="hour"),
]


# ==============================================================================
# HELPERS
# ==============================================================================
def _parse_dt(s):
    """fix90: converte string ISO -> datetime NAIVE."""
    if isinstance(s, datetime):
        return s.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(s)).replace(tzinfo=None)
    except Exception:
        return s


def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@st.cache_data(ttl=30, show_spinner=False)
def carregar_candles_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 200):
    """fix41: usa cache_candles.obter_candles(). fix93: TTL 30s."""
    try:
        from cache_candles import obter_candles
        candles, contrato = obter_candles(symbol, timeframe_min, qtd)
        return candles, contrato
    except Exception as e:
        return [], str(e)


# ==============================================================================
# CONFIG + CSS
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - SMC por Regras", layout="wide")

st.markdown("""
<style>
  .main h1, .main h2, .main h3 { font-weight: 700 !important; }
  .main h2 { font-size: 1.8rem !important; }
  .main h3 { font-size: 1.35rem !important; margin-top: 0.5rem; }
  .main h4 { font-size: 1.1rem !important; }
  .main .stCaption, .main [data-testid="stCaptionContainer"] {
    font-size: 0.95rem !important;
    color: #a0a9b8 !important;
  }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Controles SMC")
    st.caption("🔄 **Refresh automático:**")
    st.markdown(
        "- **Dados (Cenários/Parâmetros):** 5 min\n"
        "- **Gráfico M1:** 1 min\n"
        "- **Gráficos M5/M15:** 5 min\n"
    )
    st.caption("_(fragmentos independentes — página não recarrega)_")

    st.markdown("---")

    st.markdown("### 🧭 Fluxo de Análise")
    st.markdown(
        "1. **O motor diz?** — Cenários\n"
        "2. **Por que?** — Racional\n"
        "3. **O que fazer?** — Parâmetros\n"
        "4. **Como confirmar?** — Gráficos MTF\n"
        "5. **Detalhe?** — Estruturas (OB/FVG/Liq)\n"
    )
    st.caption("_(ordem das seções segue este fluxo)_")


# ==============================================================================
# LOAD INICIAL (só pro header — os fragments recarregam)
# ==============================================================================
dados_smc_inicial = carregar_json_defensivo(FILE_SMC_REGRAS)


# ==============================================================================
# HEADER (fora de fragment — atualiza só no F5, junto com a página)
# ==============================================================================
st.markdown("<h2 style='color:#00d4ff;'>🧠 Smart Money Concepts (SMC) & ICT</h2>", unsafe_allow_html=True)

_ts_dados = dados_smc_inicial.get('timestamp', 'N/A')
_ts_pagina = datetime.now().strftime("%H:%M:%S")
st.caption(f"Análise algorítmica pura (Sem IA) · Dados: **{_ts_dados}** · Página lida às **{_ts_pagina}**")

if not dados_smc_inicial or "erro" in dados_smc_inicial:
    st.error(f"⚠️ Erro ao carregar dados do Motor SMC: {dados_smc_inicial.get('erro', 'Arquivo não gerado ou sem candles suficientes')}")
    st.stop()


# ==============================================================================
# FUNÇÕES DE GRÁFICO
# ==============================================================================
def render_grafico_candles(dados, qtd_visivel=QTD_CANDLES_PADRAO, timeframe_min=5, tf_label="M5"):
    vies = dados.get("bias_direcional", "LATERAL")
    confianca = dados.get("confianca_visual", 0)
    preco_atual = dados.get("preco_atual", 0.0)

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

    _qtd_fetch = max(200, qtd_visivel + 20)
    candles, simbolo_ok = carregar_candles_mt5("WIN$", timeframe_min, _qtd_fetch)

    for c in candles:
        c["_dt"] = _parse_dt(c.get("time"))
    for s in swings:
        s["_dt"] = _parse_dt(s.get("time"))
    for e in eventos:
        e["_dt"] = _parse_dt(e.get("time"))

    if candles and qtd_visivel and qtd_visivel < len(candles):
        candles = candles[-qtd_visivel:]
        t_min = candles[0]["_dt"]
        t_max = candles[-1]["_dt"]
        swings = [s for s in swings if t_min <= s.get("_dt") <= t_max]
        eventos = [e for e in eventos if t_min <= e.get("_dt") <= t_max]

    fig = go.Figure()

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

        fig.add_shape(type="rect", xref="paper", x0=0, x1=1, yref="y", y0=low, y1=high,
                      fillcolor=cor_fill, line=dict(color=cor_borda, width=1, dash="dot"), layer="below")
        fig.add_annotation(xref="paper", x=0.005, yref="y", y=(low + high) / 2,
                           text=label, showarrow=False, font=dict(color=cor_borda, size=10), xanchor="left")

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
        fig.add_shape(type="rect", xref="paper", x0=0, x1=1, yref="y", y0=inf, y1=sup,
                      fillcolor=cor, line=dict(color=cor_borda, width=1, dash="dashdot"), layer="below")
        fig.add_annotation(xref="paper", x=0.995, yref="y", y=(inf + sup) / 2,
                           text=f"FVG {tipo}", showarrow=False, font=dict(color=cor_borda, size=9), xanchor="right")

    if candles:
        x_vals = [c["_dt"] for c in candles]
        fig.add_trace(go.Candlestick(
            x=x_vals,
            open=[c["open"] for c in candles],
            high=[c["high"] for c in candles],
            low=[c["low"] for c in candles],
            close=[c["close"] for c in candles],
            name=f"WIN {tf_label}",
            increasing=dict(line=dict(color="#00ff88", width=1), fillcolor="#00ff88"),
            decreasing=dict(line=dict(color="#ff6b6b", width=1), fillcolor="#ff6b6b"),
            hovertext=[f"O: {c['open']:,.0f}<br>H: {c['high']:,.0f}<br>L: {c['low']:,.0f}<br>C: {c['close']:,.0f}<br>V: {c['volume']:,.0f}" for c in candles],
            hoverinfo="x+text",
        ))
        x_min, x_max = x_vals[0], x_vals[-1]
    else:
        st.warning(f"⚠️ Sem candles do MT5 ({simbolo_ok}). Exibindo apenas níveis.")
        x_min, x_max = 0, 1

    x_line = [x_min, x_max] if candles else [0, 1]

    _niveis = []
    if poc and poc > 0:
        _niveis.append((poc, f"POC Ontem ({poc:,.0f})", "#a855f7", "dot", 2, 1.0, "POC Ontem"))
    if vwap and vwap > 0:
        _niveis.append((vwap, f"VWAP Ontem ({vwap:,.1f})", "#9ca3af", "dot", 2, 1.0, "VWAP Ontem"))
    if entrada and entrada > 0:
        _niveis.append((entrada, f"Entrada ({entrada:,.0f})", "#00d4ff", "dash", 2, 1.0, "Entrada"))
    if stop and stop > 0:
        _niveis.append((stop, f"Stop ({stop:,.0f})", "#ff3d00", "dash", 2, 1.0, "Stop"))
    for i, alvo in enumerate(alvos[:2]):
        if alvo and alvo > 0:
            _niveis.append((alvo, f"Alvo {i+1} ({alvo:,.0f})", "#00ff88", "longdash", 1.5, 1.0, f"Alvo {i+1}"))
    for i, nivel in enumerate(bsl[:3]):
        _niveis.append((nivel, f"BSL #{i+1} ({nivel:,.0f})", "#00bfff", "dot", 1, 0.6, "BSL"))
    for i, nivel in enumerate(ssl[:3]):
        _niveis.append((nivel, f"SSL #{i+1} ({nivel:,.0f})", "#ff6b6b", "dot", 1, 0.6, "SSL"))

    _niveis.sort(key=lambda x: -float(x[0]))

    for valor, label, cor, dash, largura, opac, tipo in _niveis:
        fig.add_trace(go.Scatter(
            x=x_line, y=[valor, valor],
            mode="lines", name=label,
            line=dict(color=cor, width=largura, dash=dash),
            opacity=opac,
            hovertemplate=f"<b>{tipo}</b><br>{valor:,.0f}<extra></extra>",
        ))

    if candles and swings:
        swings_high = [s for s in swings if str(s.get("tipo", "")).startswith("HIGH")]
        swings_low = [s for s in swings if str(s.get("tipo", "")).startswith("LOW")]
        if swings_high:
            fig.add_trace(go.Scatter(
                x=[s["_dt"] for s in swings_high], y=[s["preco"] for s in swings_high],
                mode="markers", name="Swing High",
                marker=dict(color="#ff6b6b", size=8, symbol="triangle-down", line=dict(color="#ffffff", width=1)),
                hovertemplate="<b>Swing High</b><br>%{y:,.0f}<extra></extra>",
            ))
        if swings_low:
            fig.add_trace(go.Scatter(
                x=[s["_dt"] for s in swings_low], y=[s["preco"] for s in swings_low],
                mode="markers", name="Swing Low",
                marker=dict(color="#00ff88", size=8, symbol="triangle-up", line=dict(color="#ffffff", width=1)),
                hovertemplate="<b>Swing Low</b><br>%{y:,.0f}<extra></extra>",
            ))

    if candles and eventos:
        for e in eventos[-4:]:
            tipo_ev = e.get("tipo", "")
            direcao = e.get("direcao", "")
            preco_ev = e.get("preco")
            dt_ev = e.get("_dt")
            if preco_ev is None or dt_ev is None:
                continue
            cor = "#00d4ff" if direcao == "ALTA" else "#ff6b6b"
            fig.add_annotation(
                x=dt_ev, y=preco_ev, text=f"{tipo_ev} {'↑' if direcao == 'ALTA' else '↓'}",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor=cor,
                ax=0, ay=-30 if direcao == "ALTA" else 30,
                font=dict(color=cor, size=10, family="Arial Black"),
                bgcolor="rgba(0,0,0,0.5)", bordercolor=cor, borderwidth=1, borderpad=2,
            )

    if preco_atual and preco_atual > 0:
        fig.add_hline(y=preco_atual, line=dict(color="white", width=1.5, dash="dot"),
                      annotation_text=f"  Atual: {preco_atual:,.0f}",
                      annotation_position="right", annotation_font=dict(color="white", size=11))

    fig.update_layout(
        title=dict(text=f"<b>WIN {tf_label} — Zonas Institucionais SMC</b> · "
                       f"Viés: <span style='color:{'#00ff88' if vies == 'ALTA' else '#ff6b6b' if vies == 'BAIXA' else '#ccc'}'>{vies}</span> · "
                       f"Confiança: {confianca}% · "
                       f"<span style='font-size:0.85em; color:#8b949e;'>últimos {len(candles) if candles else 0} candles</span>",
                  font=dict(size=15)),
        height=680,
        margin=dict(l=40, r=180, t=60, b=40),
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        xaxis=dict(title="", showgrid=True, gridcolor="#1f2937", rangeslider=dict(visible=False), type="date"),
        yaxis=dict(title="Pontos (WIN)", showgrid=True, gridcolor="#1f2937", zeroline=False, autorange=True, side="right"),
        legend=dict(orientation="v", yanchor="top", y=1.0, xanchor="left", x=1.10,
                    bgcolor="rgba(22, 27, 34, 0.85)", bordercolor="#30363d", borderwidth=1, font=dict(size=12)),
        hovermode="x unified",
    )

    fig.update_xaxes(rangeslider_visible=False, rangebreaks=RANGEBREAKS_B3)
    return fig


def _carregar_dados_tf(tf_min):
    from config import COLETAS_DIR, FILE_SMC_REGRAS
    mapa = {
        1: COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json",
        5: FILE_SMC_REGRAS,
        15: COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json",
    }
    return carregar_json_defensivo(mapa.get(tf_min, FILE_SMC_REGRAS))


def _render_bloco_tf(tf_min, tf_label):
    dados_tf = _carregar_dados_tf(tf_min)
    st.markdown(f"### 🕯️ {tf_label} — Zonas SMC")
    if not dados_tf or "erro" in dados_tf:
        st.warning(f"⚠️ Arquivo SMC de {tf_label} não disponível.")
        return

    _bias_tf = dados_tf.get("bias_direcional", "LATERAL")
    _conf_tf = dados_tf.get("confianca_visual", 0)
    _cor = "#00ff88" if _bias_tf == "ALTA" else ("#ff6b6b" if _bias_tf == "BAIXA" else "#ccc")
    st.markdown(
        f"<div style='padding:6px 12px; border-left:4px solid {_cor}; "
        f"background:rgba(255,255,255,0.03); border-radius:6px;'>"
        f"Viés {tf_label}: <b style='color:{_cor};'>{_bias_tf}</b> · "
        f"Confiança: <b>{_conf_tf}%</b></div>", unsafe_allow_html=True,
    )

    _opcoes = OPCOES_CANDLES_POR_TF.get(tf_min, [30, 60, 100])
    _default = QTD_CANDLES_POR_TF.get(tf_min, 30)
    _qtd = st.selectbox(
        f"Candles visíveis ({tf_label}):",
        options=_opcoes,
        index=_opcoes.index(_default) if _default in _opcoes else 0,
        key=f"smc_qtd_tf_{tf_min}",
    )

    fig_tf = render_grafico_candles(dados_tf, qtd_visivel=_qtd, timeframe_min=tf_min, tf_label=tf_label)
    st.plotly_chart(fig_tf, use_container_width=True, config={"displayModeBar": False}, key=f"plot_tf_{tf_min}")


# ==============================================================================
# FIX98: FRAGMENTS DAS SEÇÕES DE DADOS
# ==============================================================================

@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_cenarios():
    dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)
    st.markdown("### 🗺️ Cenários Operacionais Mapeados")
    cenarios = dados_smc.get("zonas_de_interesse_e_cenarios", [])
    if cenarios:
        for cenario in cenarios:
            if "DIVERGÊNCIA" in cenario:
                st.warning(cenario)
            else:
                st.markdown(cenario)
    else:
        st.caption("Aguardando consolidação do range.")


@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_parametros():
    dados_smc = carregar_json_definitivo = carregar_json_defensivo(FILE_SMC_REGRAS)
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


@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_niveis_distancias():
    dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)
    preco_atual = dados_smc.get("preco_atual", 0.0)

    # --- NIVEIS ---
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

    st.markdown("---")

    # --- DISTANCIAS ---
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


@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_estruturas():
    dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)
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


# ==============================================================================
# FIX93: FRAGMENTS DOS GRÁFICOS
# ==============================================================================

@st.fragment(run_every=REFRESH_SEG_POR_TF[1])
def _bloco_m1():
    _render_bloco_tf(1, "M1")


@st.fragment(run_every=REFRESH_SEG_POR_TF[5])
def _bloco_m5():
    _render_bloco_tf(5, "M5")


@st.fragment(run_every=REFRESH_SEG_POR_TF[15])
def _bloco_m15():
    _render_bloco_tf(15, "M15")


# ==============================================================================
# RENDER PRINCIPAL — ordem por fluxo de decisão
# ==============================================================================

# 1. Cenários
_bloco_cenarios()
st.markdown("---")

# 2. Parâmetros
_bloco_parametros()
st.markdown("---")

# 3. Níveis + 4. Distâncias
_bloco_niveis_distancias()
st.markdown("---")

# 5. Visão Multi-Timeframe
st.markdown("## 📊 Visão Multi-Timeframe (M1 · M5 · M15)")
st.caption(
    "Sequência **micro → médio → macro**. Cada gráfico mostra as zonas SMC "
    "do timeframe correspondente. **M1 atualiza a cada 1 min; M5/M15 a cada 5 min.**"
)

_bloco_m1()
st.markdown("<br>", unsafe_allow_html=True)
_bloco_m5()
st.markdown("<br>", unsafe_allow_html=True)
_bloco_m15()
st.markdown("---")

# 6. Estruturas
_bloco_estruturas()