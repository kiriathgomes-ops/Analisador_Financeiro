import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.services.vision_service import VisionService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine

st.set_page_config(page_title="Comparador V1 × V2", layout="wide")
st.title("⚖️ Comparador de Decisões – V1 (Legado) vs V2")

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

vies_v1, score_v1 = "N/A", 0
try:
    with open(BASE_DIR / "Coletas" / "Decisao_Core.json", "r") as f:
        raw = json.load(f)
        win = raw.get("analise_operacional", {}).get("WIN_INDICE", {})
        vies_v1 = win.get("vies_final", "N/A")
        score_v1 = win.get("score_numeric", 0)
except: pass

col1, col2 = st.columns(2)
with col1:
    st.subheader("📟 V1 (Legado)")
    st.metric("Viés", vies_v1); st.metric("Score", f"{score_v1:.2f}")
with col2:
    st.subheader("🚀 V2")
    st.metric("Viés", decisao.vies_final)
    st.metric("Confiança", f"{decisao.confianca}%")
    if decisao.entrada:
        st.metric("Entrada", f"{decisao.entrada:.0f}")
        st.metric("Stop", f"{decisao.stop_loss:.0f}")

df = pd.DataFrame({
    "Critério": ["Viés", "Score/Confiança", "Entrada", "Stop"],
    "V1": [vies_v1, f"{score_v1:.2f}", "—", "—"],
    "V2": [decisao.vies_final, f"{decisao.confianca}%", f"{decisao.entrada:.0f}" if decisao.entrada else "—", f"{decisao.stop_loss:.0f}" if decisao.stop_loss else "—"]
})
st.dataframe(df, hide_index=True)

with st.expander("📋 Motivos e Riscos (V2)"):
    st.write("**Motivos:**"); [st.write(f"- {m}") for m in resultado["motivos"]]
    st.write("**Riscos:**"); [st.write(f"- {r}") for r in resultado["riscos"]]