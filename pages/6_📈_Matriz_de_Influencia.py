# -*- coding: utf-8 -*-
"""
Módulo: pages/1.2_📈_Matriz_de_Influencia.py
Versão: 1.0
Objetivo: Guia rápido e visual de correlação/influência dos ativos internacionais e taxas no WIN/WDO
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="WINFUT - Matriz de Influência", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; }
.card-impact-high {
    background-color: #0d381e;
    border-left: 5px solid #00c853;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.card-impact-bear {
    background-color: #380d0d;
    border-left: 5px solid #ff3d00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.card-impact-warn {
    background-color: #382b0d;
    border-left: 5px solid #ffab00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CABEÇALHO TÉCNICO
# ==============================================================================
st.markdown("<h2 style='color:#00d4ff;'>📈 Matriz de Influência e Confluência de Ativos</h2>", unsafe_allow_html=True)
st.caption("Guia de consulta rápida para tomada de decisão no leilão e pré-market da B3")

# ==============================================================================
# 1. PESO E IMPACTO DIRETO DOS ATIVOS NO WIN/WDO
# ==============================================================================
st.markdown("---")
st.subheader("⚖️ Pesos e Vetores de Influência Directa")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 🟢 Drivers Principais do Mini Índice (WIN)")
    df_win_peso = pd.DataFrame([
        {"Ativo": "ADRs Brasileiras (VALE, PETR, Bancos)", "Peso Proporcional": 55, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "Índices US (S&P500 / Nasdaq)", "Peso Proporcional": 25, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "Commodities (Petróleo / Minério)", "Peso Proporcional": 10, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "VIX (Índice do Medo)", "Peso Proporcional": -5, "Impacto Directo": "Inverso (+ / -)"},
        {"Ativo": "Curva de Juros DI (DI1 2027/2029)", "Peso Proporcional": -5, "Impacto Directo": "Inverso (+ / -)"}
    ])
    
    fig_win = px.bar(
        df_win_peso, x="Peso Proporcional", y="Ativo", orientation='h',
        color="Peso Proporcional",
        color_continuous_scale=["#ff3d00", "#ffab00", "#00c853"],
        title="Força Explicativa no Pregão de Abertura do WIN"
    )
    fig_win.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"}, coloraxis_showscale=False)
    st.plotly_chart(fig_win, use_container_width=True)

with col_right:
    st.markdown("#### 🔴 Drivers Principais do Mini Dólar (WDO)")
    df_wdo_peso = pd.DataFrame([
        {"Ativo": "DXY (Índice Dólar Global)", "Peso Proporcional": 45, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "Curva de Juros DI (DI1 2027/2029)", "Peso Proporcional": 25, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "EWZ (ETF Brasil no Exterior)", "Peso Proporcional": -20, "Impacto Directo": "Inverso (+ / -)"},
        {"Ativo": "VIX (Aversão Global a Risco)", "Peso Proporcional": 10, "Impacto Directo": "Direto (+ / +)"}
    ])
    
    fig_wdo = px.bar(
        df_wdo_peso, x="Peso Proporcional", y="Ativo", orientation='h',
        color="Peso Proporcional",
        color_continuous_scale=["#00c853", "#ffab00", "#ff3d00"],
        title="Força Explicativa no Pregão de Abertura do WDO"
    )
    fig_wdo.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"}, coloraxis_showscale=False)
    st.plotly_chart(fig_wdo, use_container_width=True)

# ==============================================================================
# 2. TABELA INTERATIVA DE CENÁRIOS E DIVERGÊNCIAS (CONSULTA RÁPIDA)
# ==============================================================================
st.markdown("---")
st.subheader("🧩 Cenários de Confluência e Divergência na Prática")

cenarios_data = [
    {
        "Cenário": "🔥 Super Confluência de Alta",
        "ADRs BR": "🟢 Forte Alta (+2.0%)",
        "S&P / Nasdaq": "🟢 Positivos",
        "VIX / DI": "🔴 Queda / Estável",
        "Comportamento Projetado (WIN)": "🚀 GAP de Alta Forte + Explosão",
        "Estratégia": "Não fazer FADE/Venda contra o gap. Foco em compra no retração ou rompimento pós-abertura."
    },
    {
        "Cenário": "⚡ Divergência: ADRs vs EUA (Seu Exemplo)",
        "ADRs BR": "🟢 Forte Alta (+1.5%)",
        "S&P / Nasdaq": "🔴 Baixa (-0.8%)",
        "VIX / DI": "🟡 Neutro",
        "Comportamento Projetado (WIN)": "⚖️ Abertura Autônoma / Rali do Ibovespa",
        "Estratégia": "Prioridade total às ADRs (VALE/PETR/Bancos). O peso local supera o exterior se commodities/commodities financeiras estiverem compradas."
    },
    {
        "Cenário": "⚠️ Aversão Global a Risco (Risk-Off)",
        "ADRs BR": "🔴 Em Queda",
        "S&P / Nasdaq": "🔴 Em Queda Forte",
        "VIX / DI": "🟢 VIX Dispara / DI Sobe",
        "Comportamento Projetado (WIN)": "📉 GAP de Baixa Agressivo",
        "Estratégia": "Aguardar teste no ajuste. Se perder o ajuste no leilão, preferência por continuação da venda (Explosão Venda)."
    },
    {
        "Cenário": "🛑 Divergência Interna de Commodities",
        "ADRs BR": "🟡 Mistas (PETR subindo, VALE caindo)",
        "S&P / Nasdaq": "🟢 Leve Alta",
        "VIX / DI": "🟡 Estável",
        "Comportamento Projetado (WIN)": "🔄 Mercado Travado / Leilão Sujo",
        "Estratégia": "Operacional de Leilão fica BLOQUEADO. Operar preferencialmente 'Retorno ao Ajuste (500/100)' após 09:15h."
    }
]

for c in cenarios_data:
    if "Super Confluência" in c["Cenário"]:
        css = "card-impact-high"
    elif "Divergência" in c["Cenário"]:
        css = "card-impact-warn"
    else:
        css = "card-impact-bear"
        
    st.markdown(f"""
    <div class="{css}">
        <h4 style="margin:0 0 8px;">{c['Cenário']}</h4>
        <p><b>• ADRs BR:</b> {c['ADRs BR']} | <b>• EUA:</b> {c['S&P / Nasdaq']} | <b>• VIX/DI:</b> {c['VIX / DI']}</p>
        <p><b>📉 Expectativa no Índice:</b> <code style="color:#00d4ff;">{c['Comportamento Projetado (WIN)']}</code></p>
        <p style="margin-bottom:0;">💡 <b>Estratégia Operacional:</b> {c['Estratégia']}</p>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. MAPA DE CALOR DE MATRIZ DE CORRELAÇÃO ESTÁTICA/HISTÓRICA
# ==============================================================================
st.markdown("---")
st.subheader("🔥 Matriz de Correlação Cruzada (Referência Pré-Market)")

matriz_corr = pd.DataFrame(
    [
        [1.00, 0.85, 0.72, -0.68, -0.62, -0.78],
        [0.85, 1.00, 0.65, -0.55, -0.50, -0.72],
        [0.72, 0.65, 1.00, -0.45, -0.40, -0.58],
        [-0.68, -0.55, -0.45, 1.00, 0.75, 0.62],
        [-0.62, -0.50, -0.40, 0.75, 1.00, 0.55],
        [-0.78, -0.72, -0.58, 0.62, 0.55, 1.00]
    ],
    columns=["WIN_FUT", "ADRs BR", "S&P500", "VIX", "DI1", "WDO_FUT"],
    index=["WIN_FUT", "ADRs BR", "S&P500", "VIX", "DI1", "WDO_FUT"]
)

fig_heatmap = px.imshow(
    matriz_corr,
    text_auto=".2f",
    color_continuous_scale="RdBu_r",
    title="Coeficiente de Correlação Típico do Leilão de Abertura"
)
fig_heatmap.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"})
st.plotly_chart(fig_heatmap, use_container_width=True)

# ==============================================================================
# 4. REGRAS DE OURO PARA CONSULTA RÁPIDA
# ==============================================================================
st.markdown("---")
st.markdown("### 📌 Regras de Ouro no Pré-Market")

col_r1, col_r2, col_r3 = st.columns(3)

with col_r1:
    st.markdown("""
    **1. Prioridade das ADRs**
    Quando há notícia Relevante de 3★ no Brasil às 09:00, as **ADRs Brasileiras** (VALE, PETR, ITUB) possuem **60%+ da prioridade** operacional sobre os índices S&P500/Nasdaq.
    """)

with col_r2:
    st.markdown("""
    **2. Trava do VIX**
    Se o **VIX** estiver subindo acima de **+5.00%**, qualquer alta do Mini Índice deve ser operada com desconfiança (alvo mais curto), pois o risco de pullback abrupto é elevado.
    """)

with col_r3:
    st.markdown("""
    **3. Regra dos DIs Curto vs Longo**
    Se a Curva de **DI (2027/2029)** estiver subindo forte, o Mini Índice tende a pressionar para baixo e o Mini Dólar atua na ponta compradora.
    """)