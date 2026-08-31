# ============================================================
# ARQUIVO: pages/14_🌐_Ativos_Monitorados.py
#
# MOTIVO:
# Monitor Exclusivo dos Ativos Mapeados do Coletor (JSON Dinâmico)
# VERSÃO MELHORADA - Cobertura de Ações Locais + Tratamento de Dados
# ============================================================

import json
import os
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Ativos Monitorados - Quant Terminal",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS PERSONALIZADO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }

    .card-ativo {
        background: #161b22;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #2a2d3a;
        transition: all 0.3s ease;
        height: 100%;
    }
    .card-ativo:hover {
        border-color: #58a6ff;
        box-shadow: 0 4px 20px rgba(88,166,255,0.1);
        transform: translateY(-2px);
    }

    .card-ativo .simbolo {
        font-size: 0.8rem;
        color: #8b949e;
    }
    .card-ativo .preco {
        font-size: 1.4rem;
        font-weight: 700;
        color: #e6edf3;
    }
    .card-ativo .variacao {
        font-size: 0.9rem;
        font-weight: 600;
    }
    .card-ativo .variacao.positiva {
        color: #00c853;
    }
    .card-ativo .variacao.negativa {
        color: #ff3d00;
    }
    .card-ativo .variacao.neutra {
        color: #ffc107;
    }

    .card-critico {
        background: linear-gradient(145deg, #1a2230 0%, #0d1520 100%);
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #2a3a4a;
        text-align: center;
    }
    .card-critico .simbolo {
        font-size: 0.7rem;
        color: #8b949e;
    }
    .card-critico .preco {
        font-size: 1.2rem;
        font-weight: 700;
        color: #e6edf3;
    }

    .stat-box {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2a2d3a;
    }
    .stat-box .number {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .stat-box .number.alta {
        color: #00c853;
    }
    .stat-box .number.baixa {
        color: #ff3d00;
    }
    .stat-box .number.neutra {
        color: #ffc107;
    }
    .stat-box .label {
        color: #8b949e;
        font-size: 0.8rem;
        margin-top: 4px;
    }

    .sidebar-info {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2a2d4a;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# CAMINHOS
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
ARQUIVO_ATIVOS = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")

# ============================================================
# GRUPOS VISUAIS COMPLETO (32 ATIVOS)
# ============================================================

GRUPOS_ATIVOS = {
    "🇧🇷 Mercado Local, Ajustes & Curva DI": [
        "USD_PTAX", "WIN_AJUSTE", "WDO_AJUSTE", "WIN_FUT", "WDO_FUT",
        "DI1_2027", "DI1_2029", "DI1_FUT"
    ],
    "🏢 Ações Locais (B3)": [
        "VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"
    ],
    "🇺🇸 ADRs Brasileiras (NYSE/OTC)": [
        "VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"
    ],
    "🌐 Índices Globais, Moedas & Risco": [
        "EWZ", "SP500_FUT", "NASDAQ_FUT", "VIX", "DXY", "USD_MXN"
    ],
    "⛏️ Commodities & Câmbio": [
        "IRON_ORE", "IRON_ORE_2M", "CRUDE_OIL", "GOLD", "USD_BRL"
    ],
    "📊 Métricas & Auxiliares": [
        "WIN_PREV_CLOSE", "WIN_LAST_TICK"
    ]
}

# ============================================================
# ATIVOS IMPORTANTES PARA ABERTURA
# ============================================================

ATIVOS_CRITICOS = [
    "WIN_FUT", "WDO_FUT", "NASDAQ_FUT", "SP500_FUT", "VIX",
    "VALE_ADR", "PETR_ADR", "IRON_ORE", "DXY", "USD_BRL"
]

# ============================================================
# LEITURA JSON
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados():
    if not os.path.exists(ARQUIVO_ATIVOS):
        return None
    try:
        with open(ARQUIVO_ATIVOS, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception as erro:
        st.error(f"Erro lendo dados: {erro}")
        return None

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🌐 Monitor Global")
st.sidebar.caption("Ativos do Coletor Quant")
st.sidebar.markdown("---")

# Status dos dados
st.sidebar.markdown("### Status")
if os.path.exists(ARQUIVO_ATIVOS):
    timestamp_arquivo = datetime.fromtimestamp(
        os.path.getmtime(ARQUIVO_ATIVOS)
    ).strftime("%H:%M:%S")
    st.sidebar.success(f"✅ Dados carregados\nÚltima: {timestamp_arquivo}")
else:
    st.sidebar.error("❌ Arquivo não encontrado")

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Filtros")
grupo_selecionado = st.sidebar.selectbox(
    "Grupo",
    ["Todos"] + list(GRUPOS_ATIVOS.keys())
)
ordenar_por = st.sidebar.selectbox(
    "Ordenar por",
    ["Nome", "Variação % (Maior → Menor)", "Variação % (Menor → Maior)"]
)

# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================

dados = carregar_dados()

st.title("🌐 Painel de Cotações — Monitor de Ativos")
st.caption("Fonte oficial: DadosAtivosUnificados.json")

if not dados:
    st.error("""
    ⚠️ Dados dos ativos não encontrados.
    Execute: `python main_pipeline.py` para gerar as coletas.
    """)
    st.stop()

# ============================================================
# TIMESTAMP & METADATA
# ============================================================

metadata = dados.get("metadata", {})
timestamp = metadata.get(
    "timestamp",
    datetime.now().strftime("%d/%m/%Y %H:%M:%S")
)
total_no_json = metadata.get("total_ativos", 0)

st.info(f"🕒 Última coleta: **{timestamp}** | Total no JSON: **{total_no_json} ativos**")

# ============================================================
# EXTRAIR DADOS PARA DATAFRAME (LEITURA DINÂMICA DA FONTE JSON)
# ============================================================

ativos_brutos = dados.get("ativos", {})
lista_ativos = []

for nome_limpo, info in ativos_brutos.items():
    if isinstance(info, dict):
        preco = info.get("preco", info.get("valor", 0.0))
        variacao = info.get("variacao_pct", info.get("var_pct", 0.0))
        ticker_orig = info.get("ticker_original", nome_limpo)
    else:
        preco = info if isinstance(info, (int, float)) else 0.0
        variacao = 0.0
        ticker_orig = nome_limpo
    
    # Determina grupo dinamicamente
    grupo = "Outros / Não Mapeados"
    for nome_grupo, lista in GRUPOS_ATIVOS.items():
        if nome_limpo in lista:
            grupo = nome_grupo
            break
    
    lista_ativos.append({
        "Ativo": nome_limpo,
        "Ticker": ticker_orig,
        "Preço": preco,
        "Variação %": variacao,
        "Grupo": grupo,
    })

df = pd.DataFrame(lista_ativos)

# ============================================================
# FILTROS E ORDENAÇÃO DO DATAFRAME
# ============================================================

if grupo_selecionado != "Todos":
    df_filtrado = df[df["Grupo"] == grupo_selecionado]
else:
    df_filtrado = df.copy()

if ordenar_por == "Nome":
    df_filtrado = df_filtrado.sort_values("Ativo")
elif ordenar_por == "Variação % (Maior → Menor)":
    df_filtrado = df_filtrado.sort_values("Variação %", ascending=False)
elif ordenar_por == "Variação % (Menor → Maior)":
    df_filtrado = df_filtrado.sort_values("Variação %", ascending=True)

# ============================================================
# STATS (MÉTRICAS GERAIS DO PAINEL)
# ============================================================

col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)

with col_stats1:
    st.markdown(f"""
    <div class="stat-box">
        <div class="number">{len(df)}</div>
        <div class="label">Total Exibidos</div>
    </div>
    """, unsafe_allow_html=True)

with col_stats2:
    alta = len(df[df["Variação %"] > 0.5])
    st.markdown(f"""
    <div class="stat-box">
        <div class="number alta">{alta}</div>
        <div class="label">🟢 Em Alta (> +0.5%)</div>
    </div>
    """, unsafe_allow_html=True)

with col_stats3:
    baixa = len(df[df["Variação %"] < -0.5])
    st.markdown(f"""
    <div class="stat-box">
        <div class="number baixa">{baixa}</div>
        <div class="label">🔴 Em Baixa (< -0.5%)</div>
    </div>
    """, unsafe_allow_html=True)

with col_stats4:
    neutra = len(df[(df["Variação %"] >= -0.5) & (df["Variação %"] <= 0.5)])
    st.markdown(f"""
    <div class="stat-box">
        <div class="number neutra">{neutra}</div>
        <div class="label">🟡 Neutro (-0.5% a +0.5%)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# GRÁFICO DE BARRAS - VARIAÇÕES
# ============================================================

st.subheader("📊 Variação dos Ativos")

if not df_filtrado.empty:
    fig = px.bar(
        df_filtrado,
        x="Ativo",
        y="Variação %",
        color="Variação %",
        color_continuous_scale=["#ff3d00", "#ffc107", "#00c853"],
        title="Variação Percentual por Ativo",
        labels={"Variação %": "Variação (%)", "Ativo": "Ativo"},
        height=400,
    )
    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#e6edf3",
        xaxis_tickangle=-45,
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ============================================================
# BLOCO CRÍTICO PARA ABERTURA
# ============================================================

st.subheader("🎯 Ativos Críticos para Abertura WIN/WDO")

cols = st.columns(5)
criticos_presentes = [a for a in ATIVOS_CRITICOS if a in ativos_brutos]

for i, ativo in enumerate(criticos_presentes):
    info = ativos_brutos[ativo]
    preco = info.get("preco", 0.0) if isinstance(info, dict) else info
    variacao = info.get("variacao_pct", 0.0) if isinstance(info, dict) else 0.0
    
    cor = "#00c853" if variacao > 0 else "#ff3d00" if variacao < 0 else "#ffc107"
    emoji = "🟢" if variacao > 0 else "🔴" if variacao < 0 else "🟡"
    
    with cols[i % 5]:
        st.markdown(f"""
        <div class="card-critico">
            <div class="simbolo">{ativo}</div>
            <div class="preco" style="color:{cor}">{preco:,.2f}</div>
            <div class="variacao" style="color:{cor}">{emoji} {variacao:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# TODOS OS ATIVOS POR GRUPO (CARDS)
# ============================================================

st.subheader("📋 Todos os Ativos por Categoria")

grupos_para_exibir = GRUPOS_ATIVOS.keys() if grupo_selecionado == "Todos" else [grupo_selecionado]

for grupo in grupos_para_exibir:
    if grupo not in GRUPOS_ATIVOS:
        continue
    
    lista = GRUPOS_ATIVOS[grupo]
    # Exibe apenas quem realmente existe no JSON para evitar cards vazios/falsos
    lista_presentes = [t for t in lista if t in ativos_brutos]
    
    if not lista_presentes:
        continue
        
    st.markdown(f"### {grupo}")
    colunas = st.columns(min(4, len(lista_presentes)))
    
    for i, ticker in enumerate(lista_presentes):
        info = ativos_brutos[ticker]
        if isinstance(info, dict):
            preco = info.get("preco", info.get("valor", 0.0))
            variacao = info.get("variacao_pct", info.get("var_pct", 0.0))
        else:
            preco = info if isinstance(info, (int, float)) else 0.0
            variacao = 0.0
        
        cor_classe = "positiva" if variacao > 0 else "negativa" if variacao < 0 else "neutra"
        emoji = "🟢" if variacao > 0 else "🔴" if variacao < 0 else "🟡"
        
        with colunas[i % len(colunas)]:
            st.markdown(f"""
            <div class="card-ativo">
                <div class="simbolo">{ticker}</div>
                <div class="preco">{preco:,.2f}</div>
                <div class="variacao {cor_classe}">{emoji} {variacao:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")

# ============================================================
# TABELA COMPLETA
# ============================================================

with st.expander("📊 Ver Tabela Completa"):
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ativo": "Ativo",
            "Ticker": "Ticker Original",
            "Preço": st.column_config.NumberColumn("Preço", format="%.4f"),
            "Variação %": st.column_config.NumberColumn("Variação %", format="%+.2f%%"),
            "Grupo": "Grupo",
        }
    )

# ============================================================
# RODAPÉ
# ============================================================

st.caption("Analisador Financeiro | Monitor de Ativos Quantitativo v2.1")