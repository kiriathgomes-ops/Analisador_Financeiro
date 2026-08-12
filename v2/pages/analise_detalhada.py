import streamlit as st
import sys
import plotly.graph_objects as go
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.services.vision_service import VisionService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine

st.set_page_config(page_title="Análise Detalhada", layout="wide")
st.title("📊 Análise Detalhada da Decisão")

# Carrega dados
market = MarketService().build()
prediction = PredictionService().get_prediction()
news = NewsService().get_news()
vision = VisionService(market_context=market).get_vision()

if not market:
    st.error("❌ MarketContext não disponível.")
    st.stop()

engine = ConfluenceEngine()
resultado = engine.processar(market, prediction, news, vision)
decisao = DecisionEngine().gerar_decisao(resultado, market)

col1, col2, col3 = st.columns(3)
with col1: st.metric("Viés Consolidado", resultado["vies"], f"Confiança: {resultado['confianca']}%")
with col2: st.metric("Decisão", decisao.vies_final, f"Confiança: {decisao.confianca}%")
with col3: st.metric("Entrada", f"{decisao.entrada:.0f}" if decisao.entrada else "Aguardar")

# Gráfico de votos
votos = resultado["votos"]
fig = go.Figure()
fig.add_trace(go.Bar(x=["COMPRA", "VENDA"], y=[votos["COMPRA"], votos["VENDA"]],
                     marker_color=["#00c853", "#ff3d00"]))
fig.update_layout(title="Votos por Direção", plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                  font_color="#e6edf3", height=300)
st.plotly_chart(fig, width="stretch")

# Motivos e riscos
col1, col2 = st.columns(2)
with col1:
    st.subheader("✅ Motivos")
    for m in resultado["motivos"]:
        st.write(f"- {m}")
with col2:
    st.subheader("⚠️ Riscos")
    for r in resultado["riscos"]:
        st.write(f"- {r}")

# Níveis (pivôs)
st.subheader("📍 Níveis de Preço")
pivots = decisao.metadados.get("pivots", {})
if pivots:
    cols = st.columns(5)
    with cols[0]: st.metric("R2", f"{pivots.get('r2', 0):.0f}")
    with cols[1]: st.metric("R1", f"{pivots.get('r1', 0):.0f}")
    with cols[2]: st.metric("PP", f"{pivots.get('pp', 0):.0f}")
    with cols[3]: st.metric("S1", f"{pivots.get('s1', 0):.0f}")
    with cols[4]: st.metric("S2", f"{pivots.get('s2', 0):.0f}")

# Tabela de contribuição dos fatores (simulada)
st.subheader("🧮 Contribuição dos Fatores")
fatores = [
    {"Fator": "Mercado Externo", "Contribuição": market.indicador_mercado_externo or 0},
    {"Fator": "ADRs", "Contribuição": market.indicador_adrs_brasileiras or 0},
    {"Fator": "Tendência", "Contribuição": 1 if market.tendencia_win == "SUBIU" else -1 if market.tendencia_win == "DESCEU" else 0},
    {"Fator": "Predição", "Contribuição": 1 if prediction and prediction.direcao_prevista == "COMPRA" else -1 if prediction and prediction.direcao_prevista == "VENDA" else 0},
    {"Fator": "Visão SMC", "Contribuição": 1 if vision and vision.direcao_estrutura == "COMPRA" else -1 if vision and vision.direcao_estrutura == "VENDA" else 0},
]
st.dataframe(fatores, hide_index=True)

st.caption("Análise gerada pelo motor V2")