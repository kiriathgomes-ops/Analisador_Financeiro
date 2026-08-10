# NOVO_MOTOR_PREVISAO_ABERTURA/pages/🔮_Previsao_Inteligente_Abertura.py
import sys
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from NOVO_MOTOR_PREVISAO_ABERTURA.core.motor_previsao import executar_previsao

st.set_page_config(
    page_title="Previsão Inteligente de Abertura",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS (mesmo de antes, mantido)
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%); }
    .card-previsao { background: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #2a2d4a; margin-bottom: 16px; }
    .card-previsao h3 { color: #58a6ff; margin-top: 0; }
    .card-previsao .valor { font-size: 2rem; font-weight: 700; color: #e6edf3; }
    .card-previsao .rotulo { color: #8b949e; font-size: 0.85rem; }
    .card-cenario { background: #1a1c2a; border-radius: 10px; padding: 16px 20px; border-left: 4px solid #58a6ff; margin-bottom: 10px; }
    .card-cenario .titulo { font-weight: 700; font-size: 1.05rem; color: #e6edf3; }
    .card-cenario .descricao { color: #c9d1d9; font-size: 0.9rem; margin: 6px 0; }
    .card-cenario .detalhe { color: #8b949e; font-size: 0.8rem; }
    .badge-compra { background: #0d381e; color: #00c853; padding: 4px 12px; border-radius: 12px; font-weight: 600; border: 1px solid #00c853; }
    .badge-venda { background: #380d0d; color: #ff3d00; padding: 4px 12px; border-radius: 12px; font-weight: 600; border: 1px solid #ff3d00; }
    .badge-neutro { background: #1a1c23; color: #ffc107; padding: 4px 12px; border-radius: 12px; font-weight: 600; border: 1px solid #ffc107; }
    .badge-concordancia { background: #0d381e; color: #00c853; padding: 4px 12px; border-radius: 12px; font-weight: 600; border: 1px solid #00c853; }
    .badge-divergencia { background: #380d0d; color: #ff3d00; padding: 4px 12px; border-radius: 12px; font-weight: 600; border: 1px solid #ff3d00; }
    .score-bar { height: 12px; background: #2a2d4a; border-radius: 6px; overflow: hidden; margin-top: 6px; }
    .score-bar .fill { height: 100%; border-radius: 6px; transition: width 0.6s ease; }
    .score-bar .fill.forte { background: linear-gradient(90deg, #00c853, #00ff88); }
    .score-bar .fill.moderado { background: linear-gradient(90deg, #ffc107, #ffdd57); }
    .score-bar .fill.fraco { background: linear-gradient(90deg, #ff3d00, #ff6d00); }
    .footer { text-align: center; padding: 20px 0; border-top: 1px solid #1e2a3a; margin-top: 24px; color: #8b949e; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🔮 Previsão de Abertura")
st.sidebar.caption("Motor Inteligente v1.1")
st.sidebar.markdown("---")
st.sidebar.markdown("### Status")
status_container = st.sidebar.empty()
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Previsão", width="stretch"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("---")
st.sidebar.markdown("### Sobre")
st.sidebar.info(
    """
    **Motor de Previsão de Abertura v1.1**
    - GAP classificado (MICRO a EXTREMO)
    - Análise de posição em relação ao ajuste
    - Cenários condicionais
    - Score de confiança (0–100)
    - Comparação com sistema legado
    - Dados de pré-abertura (máx/mín)
    """
)

@st.cache_data(ttl=60, show_spinner=False)
def obter_previsao():
    return executar_previsao()

def get_badge(direcao):
    if direcao == "COMPRA":
        return '<span class="badge-compra">🟢 COMPRA</span>'
    elif direcao == "VENDA":
        return '<span class="badge-venda">🔴 VENDA</span>'
    else:
        return '<span class="badge-neutro">🟡 NEUTRO</span>'

def get_score_class(score):
    if score >= 60:
        return "forte"
    elif score >= 40:
        return "moderado"
    else:
        return "fraco"

dados = obter_previsao()
if not dados:
    st.error("⚠️ Não foi possível carregar a previsão.")
    st.stop()

st.title("🔮 Previsão Inteligente de Abertura")
st.caption("Baseado em dados do pipeline, gap, ajuste, cenários e comparativo com legado")

ts = dados.get("timestamp", "")
if ts:
    dt = datetime.fromisoformat(ts)
    st.info(f"⏱ Última atualização: {dt.strftime('%d/%m/%Y %H:%M:%S')}")

# === PAINEL PRINCIPAL ===
st.markdown("---")
st.subheader("📊 Resumo da Previsão")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🎯 Abertura Projetada", f"{dados['abertura_projetada']:,.0f} pts")
with col2:
    gap = dados['gap']
    st.metric("📉 GAP", f"{gap['pontos']:+,.0f} pts", delta=f"{gap['pontos']:+,.0f} pts", delta_color="inverse" if gap['pontos'] < 0 else "normal")
with col3:
    direcao = dados['direcao_prevista']
    st.markdown(f"""
    <div style="background:#161b22; padding:16px; border-radius:10px; border:1px solid #2a2d4a; text-align:center;">
        <div style="font-size:0.8rem; color:#8b949e;">DIREÇÃO PREVISTA</div>
        <div style="font-size:1.8rem; font-weight:700; margin-top:4px;">{get_badge(direcao)}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    score = dados['score']
    st.markdown(f"""
    <div style="background:#161b22; padding:16px; border-radius:10px; border:1px solid #2a2d4a; text-align:center;">
        <div style="font-size:0.8rem; color:#8b949e;">CONFIANÇA</div>
        <div style="font-size:1.8rem; font-weight:700; color:#e6edf3;">{score['valor']:.0f}%</div>
        <div style="font-size:0.9rem; color:{'#00c853' if score['classificacao'] in ['FORTE','MUITO FORTE'] else '#ffc107' if score['classificacao'] == 'MODERADO' else '#ff3d00'};">
            {score['classificacao']}
        </div>
        <div class="score-bar"><div class="fill {get_score_class(score['valor'])}" style="width:{score['valor']}%;"></div></div>
    </div>
    """, unsafe_allow_html=True)

# === DADOS DE PRÉ-ABERTURA ===
pre = dados.get('pre_abertura', {})
if pre.get('maxima') is not None or pre.get('minima') is not None:
    st.markdown("---")
    st.subheader("📡 Dados de Pré-Abertura (Tempo Real)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📈 Máxima Pré-Abertura", f"{pre.get('maxima', 0):,.0f}" if pre.get('maxima') else "N/A")
    with col2:
        st.metric("📉 Mínima Pré-Abertura", f"{pre.get('minima', 0):,.0f}" if pre.get('minima') else "N/A")
    with col3:
        st.metric("💰 Preço Atual", f"{pre.get('preco_atual', 0):,.0f}" if pre.get('preco_atual') else "N/A")
    if pre.get('maxima') and pre.get('minima'):
        faixa = dados['faixa_provavel']
        st.caption(f"📊 Faixa provável ajustada: {faixa[0]:,.0f} – {faixa[1]:,.0f} (baseada na pré-abertura)")

# === GRÁFICO AJUSTE vs ABERTURA ===
st.markdown("---")
st.subheader("📍 Posição em relação ao Ajuste")
abertura = dados['abertura_projetada']
ajuste = dados['metadados']['ajuste_utilizado']
faixa_inf, faixa_sup = dados['faixa_provavel']

fig = go.Figure()
fig.add_trace(go.Bar(x=["Ajuste B3"], y=[ajuste], name="Ajuste", marker_color="#2a3a4a", text=f"{ajuste:,.0f}", textposition="outside"))
fig.add_trace(go.Bar(x=["Abertura Projetada"], y=[abertura], name="Abertura Projetada", marker_color="#58a6ff" if abertura > ajuste else "#ff3d00", text=f"{abertura:,.0f}", textposition="outside"))
fig.add_hrect(y0=faixa_inf, y1=faixa_sup, fillcolor="rgba(88,166,255,0.15)", line_width=0, annotation_text=f"Faixa Provável: {faixa_inf:,.0f} – {faixa_sup:,.0f}", annotation_position="inside", annotation_font_color="#8b949e")
fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#e6edf3", height=300, margin=dict(l=40, r=40, t=40, b=40), xaxis_title="", yaxis_title="Pontos", yaxis_tickformat=",.0f")
st.plotly_chart(fig, width="stretch")

# === ANÁLISE DO AJUSTE ===
st.markdown("---")
st.subheader("📊 Análise do Ajuste")
col1, col2 = st.columns(2)
with col1:
    ajuste_analise = dados['analise_ajuste']
    st.markdown(f"""
    <div class="card-previsao">
        <h3>🎯 Posição</h3>
        <div style="font-size:2rem; font-weight:700;">{ajuste_analise['posicao']}</div>
        <div style="color:#8b949e;">Distância: {ajuste_analise['distancia_pontos']:+,.0f} pts ({ajuste_analise.get('distancia_percentual', 0):+.2f}%)</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    gap = dados['gap']
    st.markdown(f"""
    <div class="card-previsao">
        <h3>📉 Classificação do GAP</h3>
        <div style="font-size:2rem; font-weight:700; color:{'#ff3d00' if gap['pontos'] < 0 else '#00c853'};">{gap['intensidade']}</div>
        <div style="color:#8b949e;">{gap['classificacao']}<br>Percentual: {gap['percentual']:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

# === CENÁRIOS ===
st.markdown("---")
st.subheader("🎯 Cenários Operacionais")
col_princ, col_alt = st.columns(2)
with col_princ:
    cenario = dados['cenario_principal']
    cor_borda = "#00c853" if "COMPRA" in cenario['nome'] else "#ff3d00" if "VENDA" in cenario['nome'] else "#ffc107"
    st.markdown(f"""
    <div class="card-cenario" style="border-left-color: {cor_borda};">
        <div class="titulo">🎯 Principal: {cenario['nome']}</div>
        <div class="descricao">{cenario['descricao']}</div>
        <div class="detalhe">✅ Gatilho: {cenario['gatilho']}</div>
        <div class="detalhe">✅ Confirmação: {cenario['confirmacao']}</div>
        <div class="detalhe">❌ Invalidação: {cenario['invalidacao']}</div>
    </div>
    """, unsafe_allow_html=True)
with col_alt:
    cenario = dados['cenario_alternativo']
    cor_borda = "#ffc107"
    st.markdown(f"""
    <div class="card-cenario" style="border-left-color: {cor_borda};">
        <div class="titulo">🔄 Alternativo: {cenario['nome']}</div>
        <div class="descricao">{cenario['descricao']}</div>
    </div>
    """, unsafe_allow_html=True)

# === COMPARADOR COM SISTEMA LEGADO ===
legado = dados.get('legado')
if legado:
    st.markdown("---")
    st.subheader("⚖️ Comparador com Sistema Legado (Core Engine)")

    # Mapeamento de direções para comparação
    dir_novo = dados['direcao_prevista']
    dir_legado = legado.get('vies', 'NEUTRO')
    # Normaliza o viés do legado (pode vir como "FORTE_COMPRA", "MODERADO_VENDA", etc.)
    if "COMPRA" in dir_legado.upper():
        dir_legado_simples = "COMPRA"
    elif "VENDA" in dir_legado.upper():
        dir_legado_simples = "VENDA"
    else:
        dir_legado_simples = "NEUTRO"

    concordancia = dir_novo == dir_legado_simples
    badge_comp = '<span class="badge-concordancia">✅ CONCORDÂNCIA</span>' if concordancia else '<span class="badge-divergencia">⚠️ DIVERGÊNCIA</span>'

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div style="background:#161b22; padding:16px; border-radius:10px; border:1px solid #2a2d4a; text-align:center;">
            <div style="font-size:0.8rem; color:#8b949e;">NOVO MOTOR</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px;">{get_badge(dir_novo)}</div>
            <div style="color:#8b949e;">Score: {dados['score']['valor']:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background:#161b22; padding:16px; border-radius:10px; border:1px solid #2a2d4a; text-align:center;">
            <div style="font-size:0.8rem; color:#8b949e;">SISTEMA LEGADO</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px;">{get_badge(dir_legado_simples)}</div>
            <div style="color:#8b949e;">Score: {legado.get('score', 0):.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="background:#161b22; padding:16px; border-radius:10px; border:1px solid #2a2d4a; text-align:center;">
            <div style="font-size:0.8rem; color:#8b949e;">STATUS</div>
            <div style="font-size:1.5rem; font-weight:700; margin-top:4px;">{badge_comp}</div>
            <div style="color:#8b949e;">{'Ambos alinhados' if concordancia else 'Visões diferentes'}</div>
        </div>
        """, unsafe_allow_html=True)

    # Detalhes do legado (fatores, se disponíveis)
    if legado.get('fatores'):
        with st.expander("📋 Fatores considerados pelo legado"):
            for f in legado['fatores']:
                st.write(f"• {f}")

# === SCORE DETALHADO ===
st.markdown("---")
st.subheader("🧮 Score de Confiança – Detalhes")
score = dados['score']
detalhes = score['detalhes']
df_detalhes = pd.DataFrame(list(detalhes.items()), columns=["Fator", "Contribuição"])
df_detalhes["Contribuição"] = df_detalhes["Contribuição"].round(2)
df_detalhes = df_detalhes.iloc[df_detalhes["Contribuição"].abs().argsort()[::-1]]
col1, col2 = st.columns([2, 1])
with col1:
    st.dataframe(df_detalhes, width="stretch", hide_index=True, column_config={"Fator": "Fator", "Contribuição": st.column_config.NumberColumn("Contribuição", format="%+.2f")})
with col2:
    st.metric("Score Total", f"{score['valor']:.1f}%", f"{score['classificacao']}")

# === METADADOS ===
with st.expander("📄 Metadados e Versão"):
    st.json(dados.get("metadados", {}))

st.markdown("---")
st.markdown(
    """
    <div class="footer">
        🔮 Previsão Inteligente de Abertura • Motor v1.1.0 • Comparador com legado • Pré-abertura integrada
    </div>
    """,
    unsafe_allow_html=True
)