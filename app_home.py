# ============================================================
# ARQUIVO: app_home.py
# MOTIVO: Home / Landing Page Institucional - Versão Profissional
# ============================================================

import os
import sys
import warnings
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------
# TRATAMENTO DE AVISOS
# ------------------------------------------------------------
if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="asyncio")

# ------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="Analisador Financeiro - Quant Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# IDIOMA
# ------------------------------------------------------------
components.html(
    """
<script>
document.documentElement.lang = "pt-BR";
</script>
""",
    height=0,
)

# ------------------------------------------------------------
# CAMINHOS
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PASTA_IMAGENS = BASE_DIR / "Imagens"
COLETAS_DIR = BASE_DIR / "Coletas"

CAMINHO_IMAGEM = None
for ext in [".jpg", ".png"]:
    caminho = PASTA_IMAGENS / f"SpikeIAGrande{ext}"
    if caminho.exists():
        CAMINHO_IMAGEM = caminho
        break

# ------------------------------------------------------------
# CSS PERSONALIZADO - VERSÃO PROFISSIONAL
# ------------------------------------------------------------
st.markdown(
    """
<style>
/* ============================================================
   FUNDO E TEMA
   ============================================================ */
.stApp {
    background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
}

/* ============================================================
   SIDEBAR - HOME DESTACADA
   ============================================================ */
[data-testid="stSidebarNav"] ul li:first-child a {
    font-size: 1.25rem !important;
    font-weight: 900 !important;
    color: #00d4ff !important;
    border-left: 3px solid #00d4ff;
    padding-left: 12px !important;
    margin-bottom: 10px !important;
    background: linear-gradient(90deg, rgba(0,212,255,0.1) 0%, transparent 100%) !important;
    border-radius: 0 4px 4px 0 !important;
}

/* ============================================================
   SIDEBAR
   ============================================================ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
    border-right: 1px solid #1e2a3a !important;
}

[data-testid="stSidebar"] .stMarkdown {
    color: #8b949e !important;
}

/* ============================================================
   TÍTULO PRINCIPAL
   ============================================================ */
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

/* ============================================================
   HERO CARD
   ============================================================ */
.hero-card {
    background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(30,34,45,0.95) 100%);
    border: 1px solid #2a3a4a;
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    backdrop-filter: blur(10px);
}

/* ============================================================
   CARDS DE RECURSOS
   ============================================================ */
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

.feature-card .icon {
    font-size: 2.2rem;
    margin-bottom: 12px;
}

.feature-card h3 {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 8px;
}

.feature-card p {
    font-size: 0.9rem;
    color: #8b949e;
    line-height: 1.5;
}

/* ============================================================
   BOTÕES DOS MÓDULOS
   ============================================================ */
.module-btn {
    width: 100%;
    padding: 16px !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: 1px solid #2a3a4a !important;
    background: linear-gradient(135deg, #1a2230 0%, #0d1520 100%) !important;
    color: #e6edf3 !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
    text-align: center !important;
}

.module-btn:hover {
    border-color: #00d4ff !important;
    box-shadow: 0 4px 20px rgba(0,212,255,0.2);
    transform: translateY(-2px);
}

.module-btn .emoji {
    font-size: 1.4rem;
    margin-right: 8px;
}

/* ============================================================
   STATS CARDS
   ============================================================ */
.stat-card {
    background: linear-gradient(145deg, #161b24 0%, #1c2230 100%);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    border: 1px solid #2a3a4a;
}

.stat-card .number {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #00d4ff, #7b61ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.stat-card .label {
    font-size: 0.8rem;
    color: #8b949e;
    margin-top: 4px;
}

/* ============================================================
   TECH PILLS
   ============================================================ */
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
    transition: all 0.2s ease;
}

.tech-pill:hover {
    background: rgba(0,212,255,0.2);
    border-color: rgba(0,212,255,0.3);
}

/* ============================================================
   DIVISOR
   ============================================================ */
.divider {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #2a3a4a, transparent);
    margin: 32px 0;
}

/* ============================================================
   DIFERENCIAIS
   ============================================================ */
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

/* ============================================================
   RODAPÉ
   ============================================================ */
.footer {
    text-align: center;
    padding: 24px 0;
    border-top: 1px solid #1e2a3a;
    margin-top: 32px;
}

.footer .version {
    color: #8b949e;
    font-size: 0.8rem;
    letter-spacing: 1px;
}

.footer .version span {
    color: #00d4ff;
}

/* ============================================================
   WARNING / INFO
   ============================================================ */
.custom-info {
    background: rgba(0,212,255,0.05) !important;
    border-left: 4px solid #00d4ff !important;
    border-radius: 8px !important;
    padding: 16px 20px !important;
    font-size: 0.9rem !important;
}

/* ============================================================
   RESPONSIVIDADE
   ============================================================ */
@media (max-width: 768px) {
    .main-title {
        font-size: 2.2rem !important;
    }
    .hero-card {
        padding: 20px !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR - VERSÃO PROFISSIONAL
# ============================================================

def render_sidebar():
    """Sidebar profissional com status do sistema."""
    
    st.sidebar.image(
        "https://img.icons8.com/fluency/96/bullish.png",
        width=60,
    )
    
    st.sidebar.title("⚡ Quant Terminal")
    st.sidebar.caption("Analisador Financeiro v2.0")
    
    st.sidebar.markdown("---")
    
    # Status em tempo real
    st.sidebar.markdown("### 🟢 Status do Sistema")
    
    # Verifica se os dados estão atualizados
    dados_recentes = False
    ultima_atualizacao = "N/A"
    
    if COLETAS_DIR.exists():
        arquivos = list(COLETAS_DIR.glob("*.json"))
        if arquivos:
            # Pega o mais recente
            mais_recente = max(arquivos, key=lambda x: x.stat().st_mtime)
            ultima_atualizacao = datetime.fromtimestamp(
                mais_recente.stat().st_mtime
            ).strftime("%H:%M:%S")
            dados_recentes = True
    
    col_status, col_hora = st.sidebar.columns(2)
    with col_status:
        st.sidebar.markdown(
            f"**Status:** {'🟢 Online' if dados_recentes else '🟡 Aguardando'}"
        )
    with col_hora:
        st.sidebar.markdown(f"**Última:** {ultima_atualizacao}")
    
    st.sidebar.markdown("---")
    
    # Arquitetura
    st.sidebar.markdown("### 🛠️ Arquitetura")
    st.sidebar.markdown(
        """
        <div style="font-size:0.85rem; color:#8b949e; line-height:1.8;">
        • Coleta em Tempo Real<br>
        • IA e Visão Computacional<br>
        • Smart Money Concepts (SMC)<br>
        • Core Engine Quantitativo
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.sidebar.markdown("---")
    
    # Pipeline status
    st.sidebar.markdown("### 📊 Pipeline")
    pipeline_files = {
        "Coleta": COLETAS_DIR / "Coleta_rom-0.json",
        "Validação": COLETAS_DIR / "Dados_Validados.json",
        "Métricas": COLETAS_DIR / "Metricas_Calculadas.json",
        "Decisão": COLETAS_DIR / "Decisao_Core.json",
    }
    
    for nome, caminho in pipeline_files.items():
        existe = "✅" if caminho.exists() else "⬜"
        st.sidebar.caption(f"{existe} {nome}")
    
    st.sidebar.markdown("---")
    
    st.sidebar.info(
        "💡 Navegue pelos módulos usando o menu lateral."
    )

render_sidebar()

# ============================================================
# HERO - VERSÃO PROFISSIONAL
# ============================================================

def render_hero():
    """Hero section com título e descrição."""
    
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
        
        # Tech Pills
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
            st.image(str(CAMINHO_IMAGEM), use_container_width=True)
        else:
            st.markdown(
                """
                <div style="
                    background: linear-gradient(135deg, #1a2230, #0d1520);
                    border-radius: 16px;
                    padding: 60px 20px;
                    text-align: center;
                    border: 1px solid #2a3a4a;
                ">
                    <div style="font-size: 4rem; margin-bottom: 12px;">📊</div>
                    <p style="color: #8b949e;">Analisador Financeiro<br>Quant Terminal</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

render_hero()

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ============================================================
# PILARES DO SISTEMA
# ============================================================

st.markdown("### 🧩 Arquitetura Analítica")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="feature-card">
            <div class="icon">📊</div>
            <h3 style="color:#00d4ff;">Operacional</h3>
            <p>Monitoramento dos mercados globais, índices futuros, ADRs brasileiras, commodities, dólar, juros e calendário econômico.</p>
            <div style="margin-top:12px;">
                <span style="color:#8b949e; font-size:0.8rem;">• Mercados Internacionais</span><br>
                <span style="color:#8b949e; font-size:0.8rem;">• Calendário Econômico</span><br>
                <span style="color:#8b949e; font-size:0.8rem;">• ADRs e Commodities</span>
            </div>
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
            <div style="margin-top:12px;">
                <span style="color:#8b949e; font-size:0.8rem;">• Gap Esperado</span><br>
                <span style="color:#8b949e; font-size:0.8rem;">• Preço Justo</span><br>
                <span style="color:#8b949e; font-size:0.8rem;">• Pivôs e VWAP</span>
            </div>
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
            <p>Motor principal que consolida todas as informações e gera um viés institucional utilizando SMC, ICT e modelos quantitativos.</p>
            <div style="margin-top:12px;">
                <span style="color:#8b949e; font-size:0.8rem;">• Order Blocks</span><br>
                <span style="color:#8b949e; font-size:0.8rem;">• Fair Value Gaps</span><br>
                <span style="color:#8b949e; font-size:0.8rem;">• Viés Institucional</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ============================================================
# MÓDULOS DO SISTEMA
# ============================================================

st.markdown("### 🚀 Módulos do Sistema")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📊 Operacional", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📊_Operacional.py")

with col2:
    if st.button("🎯 Calculadora", use_container_width=True, type="primary"):
        st.switch_page("pages/2_🎯_Calculadora.py")

with col3:
    if st.button("⚙️ Core Engine", use_container_width=True, type="primary"):
        st.switch_page("pages/3_⚙️_Core_Engine.py")

with col4:
    if st.button("📈 Tendências", use_container_width=True, type="primary"):
        st.switch_page("pages/6_Analise_Tendencia.py")

st.markdown("---")

# ============================================================
# O QUE O SISTEMA MONITORA
# ============================================================

st.markdown("### 📌 O que o sistema monitora")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(
        """
        <div style="background:#161b24; border-radius:12px; padding:20px; border:1px solid #2a3a4a;">
            <h4 style="color:#00d4ff; margin-top:0;">🌎 Mercado Externo</h4>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px;">
                <span style="color:#8b949e; font-size:0.9rem;">• Índices americanos</span>
                <span style="color:#8b949e; font-size:0.9rem;">• VIX</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Petróleo</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Minério de Ferro</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Ouro</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Dólar</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Treasury</span>
                <span style="color:#8b949e; font-size:0.9rem;">• ADRs</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_b:
    st.markdown(
        """
        <div style="background:#161b24; border-radius:12px; padding:20px; border:1px solid #2a3a4a;">
            <h4 style="color:#00ff88; margin-top:0;">📈 Mercado Brasileiro</h4>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px;">
                <span style="color:#8b949e; font-size:0.9rem;">• WIN</span>
                <span style="color:#8b949e; font-size:0.9rem;">• WDO</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Ibovespa</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Fluxo Institucional</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Smart Money Concepts</span>
                <span style="color:#8b949e; font-size:0.9rem;">• ICT</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Order Blocks</span>
                <span style="color:#8b949e; font-size:0.9rem;">• Fair Value Gaps</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ============================================================
# DIFERENCIAIS
# ============================================================

st.markdown("### ⭐ Diferenciais")

# Organiza em grid de 4 colunas
diferenciais = [
    "✅ Coleta automática de dados", "✅ Atualização contínua",
    "✅ Inteligência Artificial", "✅ Análise Institucional",
    "✅ Smart Money Concepts (SMC)", "✅ ICT",
    "✅ Dashboard Operacional", "✅ Estimativa da Abertura",
    "✅ Core de Decisão", "✅ Cálculo do Preço Justo",
    "✅ Monitoramento em Tempo Real", "✅ Arquitetura Modular"
]

cols = st.columns(4)
for i, item in enumerate(diferenciais):
    with cols[i % 4]:
        st.markdown(f'<span class="diferencial-item">{item}</span>', unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# STATS
# ============================================================

st.markdown("### 📊 Métricas do Sistema")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class="stat-card">
            <div class="number">24</div>
            <div class="label">Ativos Monitorados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="stat-card">
            <div class="number">7</div>
            <div class="label">Módulos do Sistema</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="stat-card">
            <div class="number">⚡</div>
            <div class="label">Atualização em Tempo Real</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <div class="stat-card">
            <div class="number">🧠</div>
            <div class="label">IA Integrada</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ============================================================
# AVISO
# ============================================================

st.markdown(
    """
    <div class="custom-info">
        <b>⚠️ Aviso Importante</b><br>
        As informações apresentadas possuem finalidade exclusivamente educacional e de apoio à tomada de decisão.
        O sistema não realiza operações automaticamente nem constitui recomendação de compra ou venda de ativos financeiros.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ============================================================
# TECNOLOGIAS
# ============================================================

st.markdown("### 📚 Tecnologias Utilizadas")

st.markdown(
    """
    <div style="
        background: linear-gradient(145deg, #161b24 0%, #1c2230 100%);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #2a3a4a;
    ">
        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:20px;">
            <div>
                <h4 style="color:#00d4ff; margin-top:0;">🔹 Inteligência Artificial</h4>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Visão Computacional</span>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Modelos de Linguagem (LLMs)</span>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Análise Contextual</span>
            </div>
            <div>
                <h4 style="color:#00ff88; margin-top:0;">🔹 Trading Quantitativo</h4>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Smart Money Concepts (SMC)</span>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• ICT</span>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Price Action</span>
            </div>
            <div>
                <h4 style="color:#ffaa00; margin-top:0;">🔹 Engenharia de Software</h4>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Python & Streamlit</span>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• APIs Financeiras</span>
                <span style="color:#8b949e; font-size:0.9rem; display:block;">• Arquitetura Modular</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ============================================================
# RODAPÉ
# ============================================================

st.markdown(
    """
    <div class="footer">
        <div class="version">
            ⚡ <b>ANALISADOR FINANCEIRO</b> • Versão <span>2.0</span>
            <br>
            <span style="font-size:0.75rem; color:#6e7681;">
            Plataforma institucional para análise quantitativa e apoio à decisão operacional
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
) 