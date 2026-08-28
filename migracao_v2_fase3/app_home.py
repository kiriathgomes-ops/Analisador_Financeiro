# ============================================================
# ARQUIVO: app_home.py
# MOTIVO: Home / Landing Page + Roteador Central (st.navigation)
# VERSÃO: 2.1 — menu agrupado Decisão V2 / Operacional / Legado
# DATA: 27/08/2026 (migração V1 → V2)
# ============================================================


import os
import sys
import warnings
from pathlib import Path
from datetime import datetime

import streamlit as st

# ------------------------------------------------------------
# TRATAMENTO DE AVISOS
# ------------------------------------------------------------
if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="asyncio")

# ------------------------------------------------------------
# CAMINHOS BASE
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PASTA_PAGES = BASE_DIR / "pages"
PASTA_V2 = BASE_DIR / "v2/pages"  # Mapeamento da pasta externa v2
PASTA_IMAGENS = BASE_DIR / "Imagens"
COLETAS_DIR = BASE_DIR / "Coletas"

# Garantir que as pastas existam no caminho de busca do Python
for path_dir in [PASTA_PAGES, PASTA_V2]:
    if path_dir.exists() and str(path_dir) not in sys.path:
        sys.path.append(str(path_dir))

# ------------------------------------------------------------
# VERIFICAÇÃO DE IMAGEM DA HOME
# ------------------------------------------------------------
CAMINHO_IMAGEM = None
for ext in [".jpg", ".png"]:
    caminho = PASTA_IMAGENS / f"SpikeIAGrande{ext}"
    if caminho.exists():
        CAMINHO_IMAGEM = caminho
        break

# ------------------------------------------------------------
# RENDERIZADOR DA PÁGINA HOME
# ------------------------------------------------------------

def render_home_page():
    """Função responsável por renderizar a Landing Page principal."""
    
    # CSS PERSONALIZADO - VERSÃO PROFISSIONAL
    st.markdown(
        """
    <style>
    /* FUNDO E TEMA */
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
        border-right: 1px solid #1e2a3a !important;
    }

    /* TÍTULO PRINCIPAL */
    .main-title {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        background: linear-gradient(135deg, #00d4ff 0%, #7b61ff 50%, #ff6b6b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem !important;
        letter-spacing: -1px;
    }

    .main-subtitle {
        font-size: 1.2rem !important;
        color: #8b949e !important;
        font-weight: 300 !important;
        letter-spacing: 2px;
        margin-top: 0 !important;
    }

    /* HERO CARD */
    .hero-card {
        background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(30,34,45,0.95) 100%);
        border: 1px solid #2a3a4a;
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        backdrop-filter: blur(10px);
    }

    /* CARDS DE RECURSOS */
    .feature-card {
        background: linear-gradient(145deg, #161b24 0%, #1c2230 100%);
        border-radius: 12px;
        padding: 24px 20px;
        border: 1px solid #2a3a4a;
        height: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }

    .feature-card:hover {
        transform: translateY(-4px);
        border-color: #00d4ff;
        box-shadow: 0 8px 32px rgba(0,212,255,0.15);
    }

    .feature-card .icon { font-size: 2.2rem; margin-bottom: 12px; }
    .feature-card h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 8px; }
    .feature-card p { font-size: 0.9rem; color: #8b949e; line-height: 1.5; }

    /* TECH PILLS */
    .tech-pill {
        background: rgba(0,212,255,0.1);
        color: #00d4ff;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
        display: inline-block;
        margin: 4px 6px 4px 0;
        border: 1px solid rgba(0,212,255,0.15);
    }

    .divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #2a3a4a, transparent);
        margin: 32px 0;
    }

    .diferencial-item {
        display: inline-block;
        background: rgba(0,212,255,0.05);
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: #c9d1d9;
        margin: 4px 8px 4px 0;
        border: 1px solid rgba(255,255,255,0.05);
    }

    .footer { text-align: center; padding: 24px 0; border-top: 1px solid #1e2a3a; margin-top: 32px; }
    .footer .version { color: #8b949e; font-size: 0.8rem; letter-spacing: 1px; }
    .footer .version span { color: #00d4ff; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ------------------ SIDEBAR CUSTOMIZADA ------------------
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/bullish.png", width=60)
        st.title("⚡ Quant Terminal")
        st.caption("Analisador Financeiro v2.0")
        st.markdown("---")
        
        st.markdown("### 🟢 Status do Sistema")
        dados_recentes = False
        ultima_atualizacao = "N/A"
        
        if COLETAS_DIR.exists():
            arquivos = list(COLETAS_DIR.glob("*.json"))
            if arquivos:
                mais_recente = max(arquivos, key=lambda x: x.stat().st_mtime)
                ultima_atualizacao = datetime.fromtimestamp(
                    mais_recente.stat().st_mtime
                ).strftime("%H:%M:%S")
                dados_recentes = True
        
        st.markdown(f"**Status:** {'🟢 Online' if dados_recentes else '🟡 Aguardando'}")
        st.markdown(f"**Última:** {ultima_atualizacao}")
        st.markdown("---")

    # ------------------ HERO SECTION ------------------
    col_text, col_img = st.columns([1.2, 1], gap="large")
    
    with col_text:
        st.markdown(
            """
            <div class="main-title">ANALISADOR FINANCEIRO</div>
            <p class="main-subtitle">• PLATAFORMA QUANTITATIVA INSTITUCIONAL •</p>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown(
            """
            <div class="hero-card">
            <p style="color:#c9d1d9; font-size:1.05rem; line-height:1.7;">
            Transformamos <b style="color:#00d4ff;">dados macroeconômicos</b>, 
            <b style="color:#7b61ff;">fluxo institucional</b> e 
            <b style="color:#ff6b6b;">estruturas de preço</b> em um 
            <b style="color:#00ff88;">viés operacional claro</b> para 
            os contratos de <b>Mini-Índice (WIN)</b> e <b>Mini-Dólar (WDO)</b>.
            </p>
            <p style="color:#8b949e; font-size:0.95rem; margin-top:12px;">
            Integrando <b>Inteligência Artificial</b>, <b>Smart Money Concepts (SMC)</b>, 
            <b>ICT</b> e algoritmos quantitativos em tempo real.
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown(
            """
            <div style="margin-top:8px;">
            <span class="tech-pill">🧠 Smart Money Concepts</span>
            <span class="tech-pill">📈 ICT</span>
            <span class="tech-pill">🔷 Order Blocks</span>
            <span class="tech-pill">🔶 Fair Value Gaps</span>
            <span class="tech-pill">🏦 Fluxo Institucional</span>
            <span class="tech-pill">🤖 IA</span>
            <span class="tech-pill">⚡ Tempo Real</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col_img:
        if CAMINHO_IMAGEM:
            st.image(str(CAMINHO_IMAGEM), width="stretch")
        else:
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #1a2230, #0d1520); border-radius: 16px; padding: 60px 20px; text-align: center; border: 1px solid #2a3a4a;">
                    <div style="font-size: 4rem; margin-bottom: 12px;">📊</div>
                    <p style="color: #8b949e;">Analisador Financeiro<br>Quant Terminal</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ------------------ PILARES DO SISTEMA ------------------
    st.markdown("### 🧩 Arquitetura Analítica")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon">📊</div>
                <h3 style="color:#00d4ff;">Operacional</h3>
                <p>Monitoramento dos mercados globais, índices futuros, ADRs brasileiras, commodities, dólar e juros.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon">🎯</div>
                <h3 style="color:#00ff88;">Calculadora Operacional</h3>
                <p>Estimativa de abertura, Gap, Preço Justo, Pivôs, VWAP, Alvos, Stops e níveis institucionais.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="icon">⚙️</div>
                <h3 style="color:#ffaa00;">Core Engine</h3>
                <p>Motor principal que consolida informações e gera viés institucional usando SMC, ICT e modelos quantitativos.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ------------------ DIFERENCIAIS ------------------
    st.markdown("### ⭐ Diferenciais")
    diferenciais = [
        "✅ Coleta automática", "✅ Atualização contínua",
        "✅ Inteligência Artificial", "✅ Análise Institucional",
        "✅ SMC & ICT", "✅ Dashboard Operacional",
        "✅ Estimativa da Abertura", "✅ Preço Justo",
        "✅ Monitoramento Realtime", "✅ Suporte a Pastas v2"
    ]

    cols = st.columns(5)
    for i, item in enumerate(diferenciais):
        with cols[i % 5]:
            st.markdown(f'<span class="diferencial-item">{item}</span>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(
        """
        <div class="footer">
            <div class="version">
                ⚡ <b>ANALISADOR FINANCEIRO</b> • Versão <span>2.0</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# CONFIGURAÇÃO DAS PÁGINAS E NAVEGAÇÃO (st.navigation)
# ------------------------------------------------------------

# 1. Página Principal (Home) declarada como função
page_home = st.Page(
    render_home_page,
    title="Home / Dashboard",
    icon="🏠",
    default=True,
)

# ------------------------------------------------------------
# Páginas legadas de DECISÃO (mostrar com aviso no menu)
# ------------------------------------------------------------
LEGADO_DECISAO = {
    "1.2_🔮_Previsao_Inteligente_Abertura.py",
    "1.3_🔮_Previsao_Inteligente_Abertura_Comparador.py",
    "2.0_📈_Previsao_Abertura_WINFUT.py",
}

# 2. Core Engine (já migrado para V2 — destaque)
core_engine = None
core_path = PASTA_PAGES / "5.3_⚙️_Core_Engine.py"
if core_path.exists():
    core_engine = st.Page(
        core_path.relative_to(BASE_DIR).as_posix(),
        title="Core Engine (V2)",
        icon="⚙️",
    )

# 3. Pasta pages/ — separar operacional vs legado de decisão
paginas_operacional = []
paginas_legado = []
if PASTA_PAGES.exists():
    for arq in sorted(PASTA_PAGES.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        # Core Engine já tratado acima
        if arq.name == "5.3_⚙️_Core_Engine.py":
            continue

        rel_path = arq.relative_to(BASE_DIR).as_posix()
        nome_limpo = arq.stem
        for prefixo in [
            "10_", "4_", "5_", "6_", "7_", "8_", "21_",
            "🎯_", "🔢_", "⚙️_", "🔬_", "📡_", "📊_", "📅_",
            "🤖_", "📥_", "🗺️_", "🔑_", "⚡_", "📈_", "🔮_",
        ]:
            nome_limpo = nome_limpo.replace(prefixo, "")

        titulo = nome_limpo.replace("_", " ").strip()

        if arq.name in LEGADO_DECISAO:
            paginas_legado.append(
                st.Page(rel_path, title=f"[LEGADO] {titulo}", icon="⚠️")
            )
        else:
            paginas_operacional.append(
                st.Page(rel_path, title=titulo, icon="📌")
            )

# 4. Pasta v2/pages/ — decisão oficial
paginas_v2 = []
if PASTA_V2.exists():
    for arq in sorted(PASTA_V2.glob("*.py")):
        if arq.name.startswith("__"):
            continue
        rel_path = arq.relative_to(BASE_DIR).as_posix()
        mapa_titulo = {
            "1.1_dashboard_v2": "Dashboard V2",
            "1.2_comparador": "Comparador V1 × V2",
            "1.3_analise_detalhada": "Análise Detalhada",
        }
        chave = arq.stem
        titulo = mapa_titulo.get(chave, chave.replace("_", " ").title())
        paginas_v2.append(
            st.Page(rel_path, title=titulo, icon="🚀")
        )

# ------------------------------------------------------------
# Estrutura do Menu (ordem de exibição)
# ------------------------------------------------------------
estrutura_menu = {
    "Navegação Principal": [page_home],
}

# Decisão oficial em destaque
bloco_decisao = []
if core_engine is not None:
    bloco_decisao.append(core_engine)
bloco_decisao.extend(paginas_v2)
if bloco_decisao:
    estrutura_menu["🎯 Decisão V2 (oficial)"] = bloco_decisao

# Demais módulos operacionais
if paginas_operacional:
    estrutura_menu["Operacional"] = paginas_operacional

# Legado por último
if paginas_legado:
    estrutura_menu["⚠️ Legado (somente referência)"] = paginas_legado


# Configurações globais do Streamlit
st.set_page_config(
    page_title="Analisador Financeiro - Quant Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializa o roteador do Streamlit
pg = st.navigation(estrutura_menu)

# Executa a página ativa selecionada
pg.run()