# -*- coding: utf-8 -*-
"""
Módulo: pages/7.1_📊_SMC_Regras.py
Versão: 5.0 - Cockpit Master (Dashboard MTF, Tabs, Gráficos Filtrados e UI/UX Refinada)
Objetivo: Renderizar estruturas SMC/ICT em gráfico de candles reais (MT5).
"""

import streamlit as st
import json
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

from config import COLETAS_DIR

# ==============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
ARQUIVOS_TF = {
    1:  COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json",
    5:  COLETAS_DIR / "AnaliseGraficaSMC_Regras.json",
    15: COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json",
}
ARQUIVO_MTF = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"

QTD_CANDLES_PADRAO = {1: 60, 5: 30, 15: 20}
OPCOES_CANDLES = {1: [30, 60, 120, 240], 5: [30, 60, 100, 200], 15: [10, 20, 40, 60]}
REFRESH_SEG_POR_TF = {1: 60, 5: 300, 15: 300}
REFRESH_SEG_DADOS = 300

RANGEBREAKS_B3 = [
    dict(bounds=["sat", "mon"]),
    dict(bounds=[18.5, 9], pattern="hour"),
]

# ==============================================================================
# HELPERS
# ==============================================================================
def _parse_dt(s):
    if isinstance(s, datetime): return s.replace(tzinfo=None)
    try: return datetime.fromisoformat(str(s)).replace(tzinfo=None)
    except Exception: return s

@st.cache_data(ttl=5, show_spinner=False)
def carregar_json_defensivo(caminho_str: str):
    caminho = Path(caminho_str)
    if not caminho.exists(): return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

@st.cache_data(ttl=30, show_spinner=False)
def carregar_candles_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 200):
    try:
        from cache_candles import obter_candles
        candles, contrato = obter_candles(symbol, timeframe_min, qtd)
        return candles, contrato
    except Exception as e:
        return [], str(e)

# ==============================================================================
# CSS GLOBAL
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - SMC Regras", layout="wide")
st.markdown("""
<style>
  .main h1, .main h2, .main h3 { font-weight: 700 !important; }
  .main h2 { font-size: 1.8rem !important; }
  .main h3 { font-size: 1.35rem !important; margin-top: 0.5rem; }
  .main h4 { font-size: 1.1rem !important; }
  .main .stCaption, .main [data-testid="stCaptionContainer"] { font-size: 0.95rem !important; color: #a0a9b8 !important; }
  .metric-box { background-color:#161b24; padding:15px; border-radius:8px; text-align:center; height: 100%; border: 1px solid #30363d; }
  .metric-title { font-size: 0.9rem; color: #8b949e; margin-bottom: 5px; }
  .metric-value { font-size: 1.5rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Controles SMC")
    st.caption("🔄 **Refresh automático:**")
    st.markdown("- **Dados (Cenários/Parâmetros):** 5 min\n- **Gráfico M1:** 1 min\n- **Gráficos M5/M15:** 5 min")
    st.markdown("---")
    st.markdown("### 🧭 Fluxo de Análise")
    st.markdown(
        "1. **Painel Master** — Vieses e Veredito\n"
        "2. **Cenários** — O que o motor diz\n"
        "3. **Parâmetros** — Entrada e Stop\n"
        "4. **Gráficos** — Confirmação visual\n"
        "5. **Estruturas** — Detalhe de OB/FVG/Liq"
    )

# ==============================================================================
# CABEÇALHO E PAINEL MASTER (DASHBOARD)
# ==============================================================================
dados_m1 = carregar_json_defensivo(str(ARQUIVOS_TF[1]))
dados_m5 = carregar_json_defensivo(str(ARQUIVOS_TF[5]))
dados_m15 = carregar_json_defensivo(str(ARQUIVOS_TF[15]))
dados_mtf = carregar_json_defensivo(str(ARQUIVO_MTF))

st.markdown("<h2 style='color:#00d4ff;'>🧠 Smart Money Concepts (SMC) & ICT</h2>", unsafe_allow_html=True)
_ts_dados = dados_m5.get('timestamp', 'N/A')
st.caption(f"Análise algorítmica pura · Snapshot MT5: **{_ts_dados}** · Página lida às **{datetime.now().strftime('%H:%M:%S')}**")

# Função auxiliar para renderizar o card de viés
def _render_bias_card(col, tf_nome, dados):
    bias = dados.get("bias_direcional", "LATERAL")
    conf = dados.get("confianca_visual", 0)
    cor = "#00ff88" if bias == "ALTA" else ("#ff6b6b" if bias == "BAIXA" else "#ffa500")
    
    with col:
        st.markdown(
            f"<div class='metric-box' style='border-left: 5px solid {cor};'>"
            f"<div class='metric-title'>{tf_nome} (Bias)</div>"
            f"<div class='metric-value' style='color:{cor};'>{bias}</div>"
            f"<div style='font-size:0.8rem; color:#c9d1d9; margin-top:5px;'>Conf: {conf}%</div>"
            f"</div>", 
            unsafe_allow_html=True
        )

st.markdown("### 🎯 Painel Master de Confluência")
col_m15, col_m5, col_m1, col_veredito = st.columns([1, 1, 1, 2])

_render_bias_card(col_m15, "M15 (Macro)", dados_m15)
_render_bias_card(col_m5, "M5 (Médio)", dados_m5)
_render_bias_card(col_m1, "M1 (Micro)", dados_m1)

with col_veredito:
    conf_meta = dados_mtf.get("confluencia", {})
    veredito = conf_meta.get("veredito_mtf", "AGUARDANDO")
    direcao = conf_meta.get("direcao_dominante", "—")
    racional = conf_meta.get("racional", "Sem confluência mapeada.")
    
    cor_v = "#00ff88" if "ALINHADO" in veredito else ("#ff6b6b" if "DIVERGENTE" in veredito or "CONFLITO" in veredito else "#ffa500")
    
    st.markdown(
        f"<div class='metric-box' style='border-left: 5px solid {cor_v}; text-align:left; padding: 15px;'>"
        f"<div style='font-size: 0.9rem; color:#8b949e;'>Veredito MTF:</div>"
        f"<div style='font-size: 1.3rem; font-weight: bold; color:{cor_v}; margin-bottom: 5px;'>{veredito} <span style='font-size:1rem; color:#c9d1d9;'>({direcao})</span></div>"
        f"<div style='font-size: 0.85rem; color:#c9d1d9; line-height: 1.2;'>{racional}</div>"
        f"</div>", 
        unsafe_allow_html=True
    )

st.markdown("---")

# ==============================================================================
# 2. CENÁRIOS OPERACIONAIS (FRAGMENT)
# ==============================================================================
@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_cenarios():
    dados_smc = carregar_json_defensivo(str(ARQUIVOS_TF[5])) # Base M5
    st.markdown("### 🗺️ Cenários Operacionais Mapeados")
    cenarios = dados_smc.get("zonas_de_interesse_e_cenarios", [])
    
    if cenarios:
        for cenario in cenarios:
            if "DIVERGÊNCIA" in cenario or "armadilha" in cenario.lower():
                st.error(f"🚨 {cenario}")
            elif "Vendedor" in cenario or "BAIXA" in cenario:
                st.warning(f"🔻 {cenario}")
            elif "Comprador" in cenario or "ALTA" in cenario:
                st.success(f"🟢 {cenario}")
            else:
                st.info(f"ℹ️ {cenario}")
    else:
        st.caption("Aguardando consolidação do range.")

_bloco_cenarios()
st.markdown("---")

# ==============================================================================
# 3. PARÂMETROS DE EXECUÇÃO (FRAGMENT)
# ==============================================================================
@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_parametros():
    st.markdown("### 🎯 Parâmetros de Execução do Motor")
    
    # Seletor de TF de referência
    tf_ref = st.radio("Referência para Setup:", ["M1", "M5", "M15"], horizontal=True, index=1)
    dados_ref = carregar_json_defensivo(str(ARQUIVOS_TF[1 if tf_ref=="M1" else 5 if tf_ref=="M5" else 15]))

    col_trade, col_status_filtro = st.columns([2.5, 1])

    with col_trade:
        entrada = dados_ref.get("entrada_sugerida")
        stop = dados_ref.get("stop_sugerido")
        alvos = dados_ref.get("alvos", [])

        if entrada and stop:
            t_col1, t_col2, t_col3 = st.columns(3)
            t_col1.markdown(
                f"<div class='metric-box'><div class='metric-title'>🟢 ORDEM (STOP)</div>"
                f"<div class='metric-value' style='color:#00d4ff;'>{entrada:,.0f}</div></div>", unsafe_allow_html=True
            )
            t_col2.markdown(
                f"<div class='metric-box'><div class='metric-title'>🛑 STOP LOSS</div>"
                f"<div class='metric-value' style='color:#ff6b6b;'>{stop:,.0f}</div></div>", unsafe_allow_html=True
            )
            alvos_txt = " / ".join([f"{x:,.0f}" for x in alvos]) if alvos else "—"
            t_col3.markdown(
                f"<div class='metric-box'><div class='metric-title'>🏁 ALVOS (MITIGAÇÃO)</div>"
                f"<div class='metric-value' style='color:#00ff88; font-size:1.1rem;'>{alvos_txt}</div></div>", unsafe_allow_html=True
            )
        else:
            st.info(f"⚖️ **Modo de Observação ({tf_ref}):** O preço não mitigou nenhum Order Block relevante com confirmação.")

    with col_status_filtro:
        meta = dados_ref.get("metadados", {})
        vol_filtro = meta.get("filtro_volume_real_aplicado", False)
        st.markdown("**Status das Validações:**")
        st.markdown(f"• Filtro de Volume: {'✅ **ATIVO**' if vol_filtro else '❌ Inativo'}")
        st.markdown(f"• Candles (Lookback): `{meta.get('n_candles', 0)}` bars")
        st.markdown(f"• Motor: `v{meta.get('versao_motor', 'N/A')}`")

_bloco_parametros()
st.markdown("---")

# ==============================================================================
# 4. GRÁFICOS (TABS + FRAGMENTS)
# ==============================================================================
st.markdown("## 📊 Visão Gráfica Multi-Timeframe")
st.caption("Gráficos separados por abas para facilitar a leitura. Os níveis (OBs/FVGs) são limitados aos 4 mais recentes para não poluir o preço.")

def render_grafico_candles(dados, qtd_visivel, timeframe_min, tf_label, limitar_niveis=True):
    vies = dados.get("bias_direcional", "LATERAL")
    confianca = dados.get("confianca_visual", 0)
    preco_atual = dados.get("preco_atual", 0.0)
    
    _qtd_fetch = max(200, qtd_visivel + 20)
    candles, simbolo_ok = carregar_candles_mt5("WIN$", timeframe_min, _qtd_fetch)
    
    if not candles:
        st.warning(f"⚠️ Sem candles do MT5 ({simbolo_ok}).")
        return go.Figure()

    for c in candles: c["_dt"] = _parse_dt(c.get("time"))
    if qtd_visivel < len(candles):
        candles = candles[-qtd_visivel:]
        
    x_min = candles[0]["_dt"]
    x_max = candles[-1]["_dt"]

    fig = go.Figure()

    # 1. ORDER BLOCKS (Filtrados)
    obs = dados.get("order_blocks", [])
    if limitar_niveis:
        obs = sorted(obs, key=lambda x: x.get("time", ""), reverse=True)[:4] # Pega os 4 mais recentes
        
    for ob in obs:
        low, high = ob.get("low"), ob.get("high")
        if low is None or high is None: continue
        tipo = ob.get("tipo")
        cor_fill = "rgba(0, 255, 136, 0.10)" if tipo == "COMPRA" else "rgba(255, 107, 107, 0.10)"
        cor_borda = "#00ff88" if tipo == "COMPRA" else "#ff6b6b"
        
        # Plotar como bloco a partir da data de criação
        dt_ob = _parse_dt(ob.get("time"))
        x0_ob = dt_ob if dt_ob > x_min else x_min
        
        fig.add_shape(type="rect", x0=x0_ob, x1=x_max, y0=low, y1=high,
                      fillcolor=cor_fill, line=dict(color=cor_borda, width=1, dash="dot"), layer="below")
        fig.add_annotation(x=x0_ob, y=high, text=f"OB {tipo}", showarrow=False, 
                           font=dict(color=cor_borda, size=10), xanchor="left", yanchor="bottom")

    # 2. FVGs (Filtrados)
    fvgs = dados.get("fair_value_gaps", [])
    fvgs_abertos = [f for f in fvgs if not f.get("preenchido")]
    if limitar_niveis:
        fvgs_abertos = sorted(fvgs_abertos, key=lambda x: x.get("time", ""), reverse=True)[:4]
        
    for fvg in fvgs_abertos:
        sup, inf = fvg.get("superior"), fvg.get("inferior")
        if sup is None or inf is None: continue
        tipo = fvg.get("tipo")
        cor = "rgba(0, 212, 255, 0.10)" if tipo == "COMPRA" else "rgba(255, 165, 0, 0.10)"
        cor_borda = "#00d4ff" if tipo == "COMPRA" else "#ffa500"
        
        dt_fvg = _parse_dt(fvg.get("time"))
        x0_fvg = dt_fvg if dt_fvg > x_min else x_min
        
        fig.add_shape(type="rect", x0=x0_fvg, x1=x_max, y0=inf, y1=sup,
                      fillcolor=cor, line=dict(color=cor_borda, width=1, dash="dashdot"), layer="below")
        fig.add_annotation(x=x0_fvg, y=sup, text=f"FVG", showarrow=False, 
                           font=dict(color=cor_borda, size=9), xanchor="left", yanchor="bottom")

    # 3. CANDLES
    x_vals = [c["_dt"] for c in candles]
    fig.add_trace(go.Candlestick(
        x=x_vals, open=[c["open"] for c in candles], high=[c["high"] for c in candles],
        low=[c["low"] for c in candles], close=[c["close"] for c in candles], name=f"WIN {tf_label}",
        increasing=dict(line=dict(color="#00ff88", width=1), fillcolor="#00ff88"),
        decreasing=dict(line=dict(color="#ff6b6b", width=1), fillcolor="#ff6b6b"),
    ))

    # 4. NÍVEIS INSTITUCIONAIS E LIQUIDEZ (Linhas)
    ni = dados.get("niveis_institucionais", {})
    if ni.get("poc_ontem"): fig.add_hline(y=ni["poc_ontem"], line=dict(color="#a855f7", width=1.5, dash="dot"), annotation_text="POC")
    if ni.get("vwap_ontem"): fig.add_hline(y=ni["vwap_ontem"], line=dict(color="#9ca3af", width=1.5, dash="dot"), annotation_text="VWAP")
    
    liq = dados.get("liquidez", {})
    for p in liq.get("bsl", [])[:2]: fig.add_hline(y=p, line=dict(color="#00bfff", width=1, dash="dot"), opacity=0.7, annotation_text="BSL", annotation_position="top left")
    for p in liq.get("ssl", [])[:2]: fig.add_hline(y=p, line=dict(color="#ff6b6b", width=1, dash="dot"), opacity=0.7, annotation_text="SSL", annotation_position="bottom left")

    if preco_atual > 0: fig.add_hline(y=preco_atual, line=dict(color="white", width=1), annotation_text=f"Atual")

    fig.update_layout(
        title=dict(text=f"<b>WIN {tf_label}</b> · Viés: <span style='color:{'#00ff88' if vies == 'ALTA' else '#ff6b6b' if vies == 'BAIXA' else '#ccc'}'>{vies}</span>", font=dict(size=14)),
        height=550, template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        xaxis=dict(showgrid=True, gridcolor="#1f2937", rangeslider=dict(visible=False), type="date"),
        yaxis=dict(title="Pontos (WIN)", showgrid=True, gridcolor="#1f2937", autorange=True, side="right"),
        margin=dict(l=20, r=80, t=40, b=20), hovermode="x unified", showlegend=False
    )
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=RANGEBREAKS_B3)
    return fig

# --- Definição das Abas e Fragmentos ---
@st.fragment(run_every=REFRESH_SEG_POR_TF[1])
def _grafico_m1():
    q = st.selectbox("Candles M1:", OPCOES_CANDLES[1], index=1, key="q_m1")
    fig = render_grafico_candles(carregar_json_defensivo(str(ARQUIVOS_TF[1])), q, 1, "M1")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

@st.fragment(run_every=REFRESH_SEG_POR_TF[5])
def _grafico_m5():
    q = st.selectbox("Candles M5:", OPCOES_CANDLES[5], index=1, key="q_m5")
    fig = render_grafico_candles(carregar_json_defensivo(str(ARQUIVOS_TF[5])), q, 5, "M5")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

@st.fragment(run_every=REFRESH_SEG_POR_TF[15])
def _grafico_m15():
    q = st.selectbox("Candles M15:", OPCOES_CANDLES[15], index=1, key="q_m15")
    fig = render_grafico_candles(carregar_json_defensivo(str(ARQUIVOS_TF[15])), q, 15, "M15")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# Renderiza as Abas
aba_m1, aba_m5, aba_m15 = st.tabs(["🕯️ Gráfico M1 (Micro)", "📊 Gráfico M5 (Médio)", "📈 Gráfico M15 (Macro)"])

with aba_m1: _grafico_m1()
with aba_m5: _grafico_m5()
with aba_m15: _grafico_m15()

st.markdown("---")

# ==============================================================================
# 5. ESTRUTURAS DETALHADAS (FRAGMENT)
# ==============================================================================
@st.fragment(run_every=REFRESH_SEG_DADOS)
def _bloco_estruturas():
    st.markdown("### 🏢 Detalhamento de Estruturas (Base M5)")
    dados_smc = carregar_json_defensivo(str(ARQUIVOS_TF[5]))
    col_ob, col_fvg, col_liq = st.columns(3)

    with col_ob:
        st.markdown("#### 🟢 Order Blocks")
        obs = dados_smc.get("order_blocks", [])
        if obs:
            for ob in obs:
                cor = "#00ff88" if ob["tipo"] == "COMPRA" else "#ff6b6b"
                validado = ob.get("validado_por", "")
                badge = f" <span style='color:#00d4ff; font-size:0.8em;'>[{validado}]</span>" if validado else ""
                st.markdown(f"""
                <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                    <b>OB de {ob['tipo']}</b>{badge}<br>
                    • Ref: <b>{ob['preco']:,.0f}</b><br>
                    • Range: {ob['low']:,.0f} - {ob['high']:,.0f}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Nenhum Order Block ativo.")

    with col_fvg:
        st.markdown("#### 🕳️ Fair Value Gaps")
        fvgs = dados_smc.get("fair_value_gaps", [])
        if fvgs:
            for fvg in fvgs:
                cor = "#00ff88" if fvg["tipo"] == "COMPRA" else "#ff6b6b"
                st.markdown(f"""
                <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                    <b>FVG {fvg['tipo']}</b><br>
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

        st.markdown("**🌐 BSL (Alvos Acima)**")
        if bsl:
            for p in bsl: st.markdown(f"• `{p:,.0f}` — *Equal Highs*")
        else: st.caption("Sem BSL mapeado.")

        st.markdown("**🩸 SSL (Alvos Abaixo)**")
        if ssl:
            for p in ssl: st.markdown(f"• `{p:,.0f}` — *Equal Lows*")
        else: st.caption("Sem SSL mapeado.")

_bloco_estruturas()