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
st.title("🚀 Dashboard V2 - Analisador Financeiro")
st.caption("Decisão com análise de contribuição dos fatores")

# CSS personalizado para cores e cards
st.markdown("""
<style>
    .card-compra {
        background: linear-gradient(135deg, #0d381e, #1a5a2e);
        border-left: 5px solid #00c853;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .card-venda {
        background: linear-gradient(135deg, #3d0d0d, #5a1a1a);
        border-left: 5px solid #ff3d00;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .card-neutro {
        background: linear-gradient(135deg, #1a1c23, #2a2d3a);
        border-left: 5px solid #ffc107;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
    }
    .badge-compra {
        background: #00c853;
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-venda {
        background: #ff3d00;
        color: #fff;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .badge-neutro {
        background: #ffc107;
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .progress-bar {
        height: 10px;
        border-radius: 10px;
        background: #2a2d4a;
        margin: 6px 0;
    }
    .progress-bar .fill-compra {
        background: linear-gradient(90deg, #00c853, #00ff88);
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    .progress-bar .fill-venda {
        background: linear-gradient(90deg, #ff3d00, #ff6d00);
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    .progress-bar .fill-neutro {
        background: linear-gradient(90deg, #ffc107, #ffdd57);
        height: 100%;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

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
    cor_win = "green" if market.win_fut.variacao_pct > 0 else "red"
    st.metric("WIN", f"{market.win_fut.preco:.0f}", f"{market.win_fut.variacao_pct:+.2f}%", delta_color="normal")
with col2:
    cor_wdo = "green" if market.wdo_fut.variacao_pct > 0 else "red"
    st.metric("WDO", f"{market.wdo_fut.preco:.2f}", f"{market.wdo_fut.variacao_pct:+.2f}%", delta_color="normal")
with col3:
    st.metric("VIX", f"{market.vix.preco:.2f}", f"{market.vix.variacao_pct:+.2f}%", delta_color="inverse")
with col4:
    st.metric("Tendência", market.tendencia_win_padrao or "N/A")

st.divider()

# ============================================================
# 2. DECISÃO E VIÉS (com cards coloridos)
# ============================================================
st.subheader("🎯 Decisão Final")

col1, col2 = st.columns([1, 1])

with col1:
    vies = resultado["vies"]
    if vies == "COMPRA":
        card_class = "card-compra"
        badge = '<span class="badge-compra">🟢 COMPRA</span>'
    elif vies == "VENDA":
        card_class = "card-venda"
        badge = '<span class="badge-venda">🔴 VENDA</span>'
    else:
        card_class = "card-neutro"
        badge = '<span class="badge-neutro">🟡 NEUTRO</span>'

    st.markdown(f"""
    <div class="{card_class}">
        <h3 style="margin:0;">Viés Consolidado</h3>
        <div style="font-size:2rem; font-weight:700;">{badge}</div>
        <div style="font-size:1.2rem;">Confiança: {resultado['confianca']}%</div>
        <div class="progress-bar">
            <div class="fill-{vies.lower() if vies in ['COMPRA','VENDA'] else 'neutro'}" style="width:{resultado['confianca']}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    if decisao.entrada:
        st.success(f"✅ **Entrada autorizada** em {decisao.entrada:.0f}")
        st.metric("Stop Loss", f"{decisao.stop_loss:.0f}", delta="Loss")
        st.metric("Alvo 1", f"{decisao.alvo_1:.0f}", delta="Alvo")
        st.metric("Alvo 2", f"{decisao.alvo_2:.0f}", delta="Alvo")
    else:
        st.warning(f"⏳ {decisao.invalidacao}")

st.divider()

# ============================================================
# 3. ANÁLISE DE CONTRIBUIÇÃO DOS FATORES
# ============================================================
st.subheader("🧮 Análise de Contribuição dos Fatores")

col1, col2 = st.columns([2, 1])

with col1:
    # Gráfico de barras com cores
    votos = resultado["votos"]
    df_votos = pd.DataFrame({
        "Direção": ["COMPRA", "VENDA"],
        "Pontuação": [votos["COMPRA"], votos["VENDA"]]
    })
    # Usar cores condicionais
    import plotly.express as px
    fig = px.bar(df_votos, x="Direção", y="Pontuação", 
                 color="Direção",
                 color_discrete_map={"COMPRA": "#00c853", "VENDA": "#ff3d00"},
                 title="Votos por Direção",
                 text_auto=True)
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#e6edf3")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 📊 Resumo dos Votos")
    st.metric("COMPRA", f"{votos['COMPRA']:.2f}", delta="Votos")
    st.metric("VENDA", f"{votos['VENDA']:.2f}", delta="Votos")
    st.caption(f"Diferença: {votos['COMPRA'] - votos['VENDA']:+.2f}")

# Diagnóstico textual dinâmico
st.markdown("### 📝 Diagnóstico da Decisão")

motivos = resultado["motivos"]
fatores_compra = [m for m in motivos if "COMPRA" in m]
fatores_venda = [m for m in motivos if "VENDA" in m]
fatores_neutros = [m for m in motivos if "NEUTRO" in m or "neutro" in m.lower()]

diagnostico = []

if fatores_compra and fatores_venda:
    diagnostico.append("⚖️ **Disputa de forças:**")
    if votos["COMPRA"] > votos["VENDA"]:
        diagnostico.append(f"   - A **COMPRA** está predominando com **{votos['COMPRA']:.2f}** votos.")
        diagnostico.append(f"   - Principais fatores de COMPRA: {', '.join(fatores_compra)}")
        diagnostico.append(f"   - Fatores de VENDA (com **{votos['VENDA']:.2f}** votos) estão perdendo: {', '.join(fatores_venda)}")
    else:
        diagnostico.append(f"   - A **VENDA** está predominando com **{votos['VENDA']:.2f}** votos.")
        diagnostico.append(f"   - Principais fatores de VENDA: {', '.join(fatores_venda)}")
        diagnostico.append(f"   - Fatores de COMPRA (com **{votos['COMPRA']:.2f}** votos) estão perdendo: {', '.join(fatores_compra)}")

if fatores_neutros:
    diagnostico.append(f"🟡 **Fatores Neutros/Divergentes:** {', '.join(fatores_neutros)}")

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