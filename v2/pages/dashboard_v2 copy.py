# v2/pages/dashboard_v2.py
import streamlit as st
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.services.vision_service import VisionService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine

st.set_page_config(page_title="Dashboard V2 - Análise Detalhada", layout="wide")

# ============================================================
# CSS PERSONALIZADO
# ============================================================
st.markdown("""
<style>
    .card-bull {
        border-left: 6px solid #00c853;
        background: #0d381e;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .card-bear {
        border-left: 6px solid #ff3d00;
        background: #380d0d;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .card-neutral {
        border-left: 6px solid #ffc107;
        background: #1a1c23;
        padding: 12px 20px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .badge-bull {
        background: #00c853;
        color: #fff;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-bear {
        background: #ff3d00;
        color: #fff;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-neutral {
        background: #ffc107;
        color: #000;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .progress-bar-bull {
        background: linear-gradient(90deg, #00c853, #00ff88);
        height: 12px;
        border-radius: 6px;
        transition: width 0.6s ease;
    }
    .progress-bar-bear {
        background: linear-gradient(90deg, #ff3d00, #ff6d00);
        height: 12px;
        border-radius: 6px;
        transition: width 0.6s ease;
    }
    .progress-bar-neutral {
        background: #ffc107;
        height: 12px;
        border-radius: 6px;
        transition: width 0.6s ease;
    }
    .fator-item {
        padding: 6px 0;
        border-bottom: 1px solid #2a2d4a;
    }
    .fator-item:last-child {
        border-bottom: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Dashboard V2 - Analisador Financeiro")
st.caption("Decisão com análise de contribuição dos fatores")

# Carregar dados
market = MarketService().build()
prediction = PredictionService().get_prediction()
news = NewsService().get_news()
vision = VisionService(market_context=market).get_vision()

if not market:
    st.error("❌ MarketContext não disponível.")
    st.stop()

# Executar Motores
engine = ConfluenceEngine()
resultado = engine.processar(market, prediction, news, vision)
decisao = DecisionEngine().gerar_decisao(resultado, market)

# ============================================================
# 1. PAINEL SUPERIOR (Cotações)
# ============================================================
st.subheader("📊 Cotações em Tempo Real")
col1, col2, col3, col4 = st.columns(4)
with col1:
    var = market.win_fut.variacao_pct
    delta_color = "normal" if var > 0 else "inverse"
    st.metric("**WIN**", f"{market.win_fut.preco:.0f}", f"{var:+.2f}%", delta_color=delta_color)
with col2:
    var = market.wdo_fut.variacao_pct
    delta_color = "normal" if var > 0 else "inverse"
    st.metric("**WDO**", f"{market.wdo_fut.preco:.2f}", f"{var:+.2f}%", delta_color=delta_color)
with col3:
    var = market.vix.variacao_pct
    st.metric("**VIX**", f"{market.vix.preco:.2f}", f"{var:+.2f}%", delta_color="inverse")
with col4:
    st.metric("**Tendência**", market.tendencia_win_padrao or "N/A")

st.divider()

# ============================================================
# 2. DECISÃO E VIÉS COM CORES
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Decisão Final")
    vies = resultado["vies"]
    conf = resultado["confianca"]

    # Define classe CSS e badge
    if vies == "COMPRA":
        card_class = "card-bull"
        badge_class = "badge-bull"
        emoji = "🟢"
    elif vies == "VENDA":
        card_class = "card-bear"
        badge_class = "badge-bear"
        emoji = "🔴"
    else:
        card_class = "card-neutral"
        badge_class = "badge-neutral"
        emoji = "🟡"

    # Barra de progresso da confiança
    if vies == "COMPRA":
        bar_class = "progress-bar-bull"
    elif vies == "VENDA":
        bar_class = "progress-bar-bear"
    else:
        bar_class = "progress-bar-neutral"

    st.markdown(f"""
    <div class="{card_class}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem; font-weight:700;">{emoji} {vies}</span>
            <span class="{badge_class}">{conf}% confiança</span>
        </div>
        <div style="margin-top:8px;">
            <div style="width:100%; background:#2a2d4a; border-radius:6px; overflow:hidden;">
                <div class="{bar_class}" style="width:{conf}%;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.subheader("📋 Status Operacional")
    if decisao.entrada:
        st.success(f"✅ **Entrada em {decisao.entrada:.0f}**")
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Stop", f"{decisao.stop_loss:.0f}", delta="Loss", delta_color="inverse")
        with m2: st.metric("Alvo 1", f"{decisao.alvo_1:.0f}", delta="Alvo")
        with m3: st.metric("Alvo 2", f"{decisao.alvo_2:.0f}", delta="Alvo")
    else:
        st.warning(f"⏳ {decisao.invalidacao}")

st.divider()

# ============================================================
# 3. ANÁLISE DE CONTRIBUIÇÃO DOS FATORES
# ============================================================
st.subheader("🧮 Análise de Contribuição dos Fatores")

# Gráfico de barras com cores personalizadas
votos = resultado["votos"]
df_votos = pd.DataFrame({
    "Direção": ["COMPRA", "VENDA"],
    "Pontuação": [votos["COMPRA"], votos["VENDA"]]
})

# Use st.bar_chart com color_map (mas não suporta cores diretas)
# Então usamos st.altair_chart para ter mais controle
import altair as alt

chart = alt.Chart(df_votos).mark_bar().encode(
    x=alt.X("Direção", axis=alt.Axis(labelAngle=0)),
    y=alt.Y("Pontuação", title="Pontuação"),
    color=alt.Color("Direção", scale=alt.Scale(domain=["COMPRA", "VENDA"], range=["#00c853", "#ff3d00"])),
    tooltip=["Direção", "Pontuação"]
).properties(
    height=250,
    width="container"
)
st.altair_chart(chart, use_container_width=True)

# Diagnóstico textual
st.markdown("### 📝 Diagnóstico da Decisão")

motivos = resultado["motivos"]
fatores_compra = [m for m in motivos if "COMPRA" in m]
fatores_venda = [m for m in motivos if "VENDA" in m]
fatores_neutros = [m for m in motivos if "NEUTRO" in m or "neutro" in m.lower()]

diagnostico = []

if fatores_compra and fatores_venda:
    diagnostico.append("⚖️ **Disputa de forças:**")
    if votos["COMPRA"] > votos["VENDA"]:
        diagnostico.append(f"   - 🟢 A **COMPRA** está predominando com **{votos['COMPRA']:.2f}** votos.")
        diagnostico.append(f"   - 📈 Fatores de COMPRA: {', '.join(fatores_compra)}")
        diagnostico.append(f"   - 📉 Fatores de VENDA (com {votos['VENDA']:.2f} votos): {', '.join(fatores_venda)}")
    else:
        diagnostico.append(f"   - 🔴 A **VENDA** está predominando com **{votos['VENDA']:.2f}** votos.")
        diagnostico.append(f"   - 📉 Fatores de VENDA: {', '.join(fatores_venda)}")
        diagnostico.append(f"   - 📈 Fatores de COMPRA (com {votos['COMPRA']:.2f} votos): {', '.join(fatores_compra)}")

if fatores_neutros:
    diagnostico.append(f"🟡 **Fatores Neutros:** {', '.join(fatores_neutros)}")

if resultado["vies"] == "COMPRA":
    diagnostico.append(f"✅ **Veredito:** A **COMPRA** venceu com **{resultado['confianca']}%** de confiança.")
elif resultado["vies"] == "VENDA":
    diagnostico.append(f"✅ **Veredito:** A **VENDA** venceu com **{resultado['confianca']}%** de confiança.")
else:
    diagnostico.append(f"🟡 **Veredito:** **NEUTRO** com **{resultado['confianca']}%** de confiança. Aguardando definição.")

for linha in diagnostico:
    st.markdown(linha)

st.caption("💡 A pontuação é calculada com base nos pesos de cada fator (Mercado, ADRs, Tendência, Predição, Visão SMC).")

st.divider()

# ============================================================
# 4. DETALHES DOS MOTIVOS E RISCOS
# ============================================================
with st.expander("📋 Ver lista completa de Motivos e Riscos"):
    st.write("**Motivos:**")
    for m in resultado["motivos"]:
        st.write(f"- {m}")
    st.write("**Riscos:**")
    for r in resultado["riscos"]:
        st.write(f"- {r}")

# ============================================================
# 5. NÍVEIS DE PREÇO (PIVOTS)
# ============================================================
if "pivots" in decisao.metadados:
    st.subheader("📍 Níveis de Preço (Pivots)")
    p = decisao.metadados["pivots"]
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("R2", f"{p.get('r2', 0):.0f}")
    with col2: st.metric("R1", f"{p.get('r1', 0):.0f}")
    with col3: st.metric("PP", f"{p.get('pp', 0):.0f}")
    with col4: st.metric("S1", f"{p.get('s1', 0):.0f}")
    with col5: st.metric("S2", f"{p.get('s2', 0):.0f}")

st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")