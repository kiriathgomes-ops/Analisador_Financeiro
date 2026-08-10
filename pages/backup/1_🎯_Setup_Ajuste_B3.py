# ============================================================
# ARQUIVO: pages/1_🎯_Setup_Ajuste_B3.py
#
# MOTIVO:
# Dashboard quantitativo do Setup Ajuste B3
# VERSÃO MELHORADA - Com IA e Tendências
#
# Data alteração:
# 2026-08-04
# ============================================================

import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Setup Ajuste B3 - Quant Terminal",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS VISUAL MELHORADO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
    }

    .card-buy {
        background-color: #0d381e;
        border-left: 5px solid #00c853;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }

    .card-sell {
        background-color: #380d0d;
        border-left: 5px solid #ff3d00;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }

    .card-neutral {
        background-color: #1a1c23;
        border-left: 5px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }

    .card-ai {
        background: linear-gradient(145deg, #12141c 0%, #1a1c2a 100%);
        border-left: 5px solid #7c5cfc;
        padding: 20px;
        border-radius: 8px;
        margin-top: 12px;
        border: 1px solid #2a2d4a;
    }
    .card-ai h4 {
        color: #7c5cfc;
        margin-top: 0;
    }
    .card-ai .analysis-content {
        color: #c9d1d9;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .card-ai .smc-tag {
        background: rgba(124, 92, 252, 0.15);
        color: #a78bfa;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        display: inline-block;
        margin: 2px 4px 2px 0;
    }

    .info-box {
        background-color: #161b22;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #30363d;
    }

    .tendencia-up {
        color: #00c853;
        font-weight: bold;
    }
    .tendencia-down {
        color: #ff3d00;
        font-weight: bold;
    }
    .tendencia-neutral {
        color: #ffc107;
        font-weight: bold;
    }

    .explicacao {
        background-color: #1a1c2a;
        border: 1px solid #2a2d3a;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.85rem;
        color: #cccccc;
        margin-top: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

# Arquivos de dados
ARQUIVOS_DADOS = [
    "DadosAtivosUnificados.json",
    "Dados_Validados.json",
    "Resultado_Calculadora_Operacional_Abertura.json",
]

ARQUIVO_TENDENCIAS = os.path.join(COLETAS_DIR, "Analise_Tendencias.json")
ARQUIVO_DECISAO = os.path.join(COLETAS_DIR, "Decisao_Core.json")
ARQUIVO_METRICAS = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")

# ============================================================
# CARREGAMENTO DOS DADOS
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    """Lê JSON com cache; retorna dict vazio em caso de erro."""
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}

def carregar_dados():
    """Carrega dados com fallback entre arquivos."""
    for arquivo in ARQUIVOS_DADOS:
        caminho = os.path.join(COLETAS_DIR, arquivo)
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    return dados, arquivo
            except Exception:
                continue
    return None, None

dados, fonte_dados = carregar_dados()

# Carrega tendências e métricas
dados_tendencias = carregar_json(ARQUIVO_TENDENCIAS)
dados_decisao = carregar_json(ARQUIVO_DECISAO)
dados_metricas = carregar_json(ARQUIVO_METRICAS)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🎯 Setup Ajuste B3")
st.sidebar.caption("Operação em regiões de Ajuste Oficial")
st.sidebar.markdown("---")

if fonte_dados:
    st.sidebar.success(f"✅ Fonte: {fonte_dados}")
else:
    st.sidebar.error("❌ Sem dados")

st.sidebar.markdown("---")
st.sidebar.markdown("### Status dos Dados")

arquivos_status = {
    "Ativos": os.path.join(COLETAS_DIR, ARQUIVOS_DADOS[0]),
    "Tendências": ARQUIVO_TENDENCIAS,
    "Decisão": ARQUIVO_DECISAO,
    "Métricas": ARQUIVO_METRICAS,
}
for nome, caminho in arquivos_status.items():
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome}")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Limpar Histórico IA", width="stretch"):
    if "historico_ia_ajuste" in st.session_state:
        st.session_state.historico_ia_ajuste = []
    st.rerun()

# ============================================================
# CABEÇALHO
# ============================================================

st.title("🎯 Operacional do Ajuste B3 — Leitura Quantitativa")
st.caption("Estratégia baseada em: Ajuste Oficial + Fluxo Global + Confluência Macro + IA")

if dados:
    timestamp = dados.get("metadata", {}).get(
        "timestamp",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    st.info(f"⏱ Última atualização: **{timestamp}** | 📂 Fonte: **{fonte_dados}**")
else:
    st.error("""
    ⚠️ Nenhum arquivo de dados encontrado.
    Execute: `python main_pipeline.py` para gerar as coletas.
    """)
    st.stop()

# ============================================================
# EXTRAÇÃO BASE DOS ATIVOS
# ============================================================

ativos = dados.get("ativos", {})
if not ativos:
    st.warning("Arquivo encontrado, porém sem bloco de ativos.")
    st.stop()

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_preco(nome):
    """Obtém o preço de um ativo."""
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("preco", ativo.get("valor", 0.0))
    return 0.0

def obter_variacao(nome):
    """Obtém a variação percentual de um ativo."""
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("variacao_pct", ativo.get("var_pct", 0.0))
    return 0.0

def variacao(ativo):
    """Obtém a variação de um ativo já carregado."""
    if isinstance(ativo, dict):
        return ativo.get("variacao_pct", ativo.get("var_pct", 0))
    return 0

def calcular_distancia(preco, ajuste):
    """Calcula distância entre preço e ajuste."""
    if not preco or not ajuste:
        return 0, 0
    pontos = preco - ajuste
    percentual = (pontos / ajuste) * 100 if ajuste != 0 else 0
    return pontos, percentual

def extrair_tendencia_win():
    """Extrai tendência do WIN do arquivo de tendências."""
    if not dados_tendencias:
        return None
    
    # Tenta encontrar WIN_FUT ou BMFBOVESPA:WIN1!
    for chave in ["WIN_FUT", "BMFBOVESPA:WIN1!"]:
        if chave in dados_tendencias:
            info = dados_tendencias[chave]
            return {
                "padrao": info.get("padrao_comportamento", "N/A"),
                "variacao": info.get("intervalo_5_para_0", {}).get("variacao_pct", 0),
                "tendencia": info.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
            }
    return None

# ============================================================
# BLOCO 1: NÍVEIS DE AJUSTE OFICIAL
# ============================================================

st.markdown("---")
st.subheader("📌 1. Ajuste Oficial x Preço Atual")

win_ajuste = obter_preco("WIN_AJUSTE")
win_atual = obter_preco("WIN_FUT")
wdo_ajuste = obter_preco("WDO_AJUSTE")
wdo_atual = obter_preco("WDO_FUT")
ptax = obter_preco("USD_PTAX")

dist_win_pts, dist_win_pct = calcular_distancia(win_atual, win_ajuste)
dist_wdo_pts, dist_wdo_pct = calcular_distancia(wdo_atual, wdo_ajuste)

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "🎯 Ajuste WIN",
        f"{win_ajuste:,.0f} pts",
        f"Atual {win_atual:,.0f}"
    )
    st.write(f"""
    Distância:
    **{dist_win_pts:+,.0f} pts**
    **{dist_win_pct:+.2f}%**
    """)

with c2:
    st.metric(
        "🎯 Ajuste WDO",
        f"{wdo_ajuste:,.2f}",
        f"Atual {wdo_atual:,.2f}"
    )
    st.write(f"""
    Distância:
    **{dist_wdo_pts:+,.2f} pts**
    **{dist_wdo_pct:+.2f}%**
    """)

with c3:
    st.metric("💵 PTAX BACEN", f"R$ {ptax:,.4f}" if ptax else "N/A")

# ============================================================
# BLOCO 2: TERMÔMETRO MACRO (COM %)
# ============================================================

st.markdown("---")
st.subheader("🌐 2. Termômetro Macro (com % )")

sp500 = ativos.get("SP500_FUT", {})
nasdaq = ativos.get("NASDAQ_FUT", {})
ewz = ativos.get("EWZ", {})
vix = ativos.get("VIX", {})
dxy = ativos.get("DXY", {})
iron = ativos.get("IRON_ORE", {})
petr = ativos.get("PETR_ADR", {})

m1, m2, m3, m4, m5, m6 = st.columns(6)

with m1:
    st.metric(
        "🇺🇸 S&P500",
        f"{sp500.get('preco', 0):,.2f}",
        f"{variacao(sp500):+.2f}%"
    )

with m2:
    st.metric(
        "💻 Nasdaq",
        f"{nasdaq.get('preco', 0):,.2f}",
        f"{variacao(nasdaq):+.2f}%"
    )

with m3:
    st.metric(
        "🇧🇷 EWZ",
        f"${ewz.get('preco', 0):,.2f}",
        f"{variacao(ewz):+.2f}%"
    )

with m4:
    st.metric(
        "⚠️ VIX",
        f"{vix.get('preco', 0):,.2f}",
        f"{variacao(vix):+.2f}%",
        delta_color="inverse"
    )

with m5:
    st.metric(
        "💵 DXY",
        f"{dxy.get('preco', 0):,.2f}",
        f"{variacao(dxy):+.2f}%",
        delta_color="inverse"
    )

with m6:
    st.metric(
        "⛏️ Minério",
        f"${iron.get('preco', 0):,.2f}",
        f"{variacao(iron):+.2f}%"
    )

# ============================================================
# BLOCO 3: CONFLUÊNCIA COM TENDÊNCIA
# ============================================================

st.markdown("---")
st.subheader("📈 3. Confluência com Tendência")

tendencia_win = extrair_tendencia_win()

if tendencia_win:
    emoji = "🟢" if tendencia_win["variacao"] > 0 else "🔴" if tendencia_win["variacao"] < 0 else "🟡"
    st.metric(
        "WIN - Tendência",
        f"{emoji} {tendencia_win['padrao']}",
        f"{tendencia_win['variacao']:+.2f}%"
    )
    
    # Interpretação
    if dist_win_pts > 300 and tendencia_win["tendencia"] == "SUBIU":
        st.success("✅ WIN distante do ajuste e tendência de alta - Viés Comprador")
    elif dist_win_pts < -300 and tendencia_win["tendencia"] == "DESCEU":
        st.error("🔴 WIN distante do ajuste e tendência de baixa - Viés Vendedor")
    elif abs(dist_win_pts) > 300:
        st.warning(f"⚠️ WIN distante do ajuste ({dist_win_pts:+.0f} pts) - Aguardar confirmação")
    else:
        st.info("ℹ️ WIN próximo do ajuste - Aguardar definição")
else:
    st.info("📊 Dados de tendência não disponíveis. Execute `MapearTendencia15Min.py`")

# ============================================================
# BLOCO 4: SCORE QUANTITATIVO WIN
# ============================================================

st.markdown("---")
st.subheader("📊 4. Score Quantitativo WIN")

score_win = 0
criterios_win = []

if variacao(sp500) > 0:
    score_win += 1
    criterios_win.append("✅ S&P500 positivo")
else:
    criterios_win.append("❌ S&P500 negativo")

if variacao(iron) > 0:
    score_win += 1
    criterios_win.append("✅ Minério positivo")
else:
    criterios_win.append("❌ Minério negativo")

if variacao(ewz) > 0:
    score_win += 1
    criterios_win.append("✅ EWZ positivo")
else:
    criterios_win.append("❌ EWZ negativo")

if variacao(vix) < 0:
    score_win += 1
    criterios_win.append("✅ VIX reduzindo risco")
else:
    criterios_win.append("❌ VIX pressionando")

if variacao(nasdaq) > 0:
    score_win += 1
    criterios_win.append("✅ Nasdaq positivo")
else:
    criterios_win.append("❌ Nasdaq negativo")

# Bônus: tendência confirma
if tendencia_win and tendencia_win["tendencia"] == "SUBIU" and dist_win_pts > 300:
    score_win += 1
    criterios_win.append("✅ Tendência confirma ajuste")

col_score, col_lista = st.columns(2)

with col_score:
    st.metric("Score WIN", f"{score_win}/6")
    if score_win >= 5:
        st.success("🟢 VIÉS COMPRADOR FORTE")
    elif score_win >= 3:
        st.warning("🟡 VIÉS NEUTRO/MODERADO")
    else:
        st.error("🔴 VIÉS VENDEDOR")

with col_lista:
    for item in criterios_win:
        st.write(item)

# ============================================================
# BLOCO 5: SCORE QUANTITATIVO WDO
# ============================================================

st.markdown("---")
st.subheader("💵 5. Score Quantitativo WDO")

usd_mxn = ativos.get("USD_MXN", {})
score_wdo = 0
criterios_wdo = []

if variacao(dxy) > 0:
    score_wdo += 1
    criterios_wdo.append("✅ DXY fortalecendo dólar")
else:
    criterios_wdo.append("❌ DXY enfraquecendo dólar")

if variacao(usd_mxn) > 0:
    score_wdo += 1
    criterios_wdo.append("✅ USD/MXN favorece dólar")
else:
    criterios_wdo.append("❌ USD/MXN favorece moedas emergentes")

if variacao(vix) > 0:
    score_wdo += 1
    criterios_wdo.append("✅ VIX em alta (proteção)")
else:
    criterios_wdo.append("❌ VIX em queda")

c_score, c_lista = st.columns(2)

with c_score:
    st.metric("Score WDO", f"{score_wdo}/3")
    if score_wdo >= 2:
        st.success("🟢 VIÉS COMPRADOR DÓLAR")
    elif score_wdo == 0:
        st.error("🔴 VIÉS VENDEDOR DÓLAR")
    else:
        st.warning("🟡 DÓLAR NEUTRO")

with c_lista:
    for item in criterios_wdo:
        st.write(item)

# ============================================================
# BLOCO 6: CHECKLIST OPERACIONAL
# ============================================================

st.markdown("---")
st.subheader("📋 6. Checklist de Execução")

col_check1, col_check2 = st.columns(2)

with col_check1:
    st.markdown("### 📈 WIN Ajuste")
    check_win_dist = st.checkbox("WIN distante do ajuste (>300 pontos)")
    check_win_fluxo = st.checkbox("Fluxo confirmou defesa/rejeição no ajuste")
    check_win_noticia = st.checkbox("Sem notícia de alto impacto próxima")

with col_check2:
    st.markdown("### 💵 WDO Ajuste")
    check_wdo_dist = st.checkbox("WDO distante do ajuste (>10 pontos)")
    check_wdo_fluxo = st.checkbox("Tape Reading confirmou absorção")
    check_wdo_noticia = st.checkbox("Sem evento macro imediato")

check_win_total = sum([check_win_dist, check_win_fluxo, check_win_noticia])
check_wdo_total = sum([check_wdo_dist, check_wdo_fluxo, check_wdo_noticia])

# ============================================================
# BLOCO 7: DECISÃO FINAL DO SETUP
# ============================================================

st.markdown("---")
st.subheader("🚦 7. Semáforo Operacional")

def gerar_status(score, checklist):
    pontos = score + checklist
    if pontos >= 7:
        return "🟢", "SETUP LIBERADO", "Alta confluência"
    elif pontos >= 4:
        return "🟡", "AGUARDAR CONFIRMAÇÃO", "Confluência parcial"
    else:
        return "🔴", "NÃO OPERAR", "Risco elevado"

status_win = gerar_status(score_win, check_win_total)
status_wdo = gerar_status(score_wdo, check_wdo_total)

cwin, cwdo = st.columns(2)

with cwin:
    st.markdown(f"""
    <div class="info-box">
        <h3>📈 SETUP WIN</h3>
        <h2>{status_win[0]} {status_win[1]}</h2>
        <p>Score: {score_win}/6<br>Checklist: {check_win_total}/3<br>{status_win[2]}</p>
    </div>
    """, unsafe_allow_html=True)

with cwdo:
    st.markdown(f"""
    <div class="info-box">
        <h3>💵 SETUP WDO</h3>
        <h2>{status_wdo[0]} {status_wdo[1]}</h2>
        <p>Score: {score_wdo}/3<br>Checklist: {check_wdo_total}/3<br>{status_wdo[2]}</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# BLOCO 8: ANÁLISE IA - AJUSTE B3 (SOMENTE TEXTO)
# ============================================================

st.markdown("---")
st.subheader("🧠 8. Análise IA - Ajuste B3")

# Configuração da IA
groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BASE_DIR, ".env"))
        groq_key = os.getenv("GROQ_API_KEY", "")
    except Exception:
        pass

with st.expander("⚙️ Configurações da IA", expanded=not bool(groq_key)):
    groq_key_input = st.text_input(
        "Groq API Key",
        type="password",
        value=groq_key,
        help="Obtenha em https://console.groq.com",
        key="groq_key_ajuste"
    )
    modelo_texto = st.selectbox(
        "Modelo (texto)",
        ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
        index=0,
        key="modelo_ajuste"
    )
    st.caption("💡 Modelos de texto são mais rápidos e baratos")

if st.button("📊 Analisar Ajuste B3 (IA)", type="primary", key="btn_ajuste"):
    key_final = groq_key_input or groq_key
    
    if not key_final:
        st.error("⚠️ Informe a Groq API Key")
    else:
        with st.spinner("🧠 Analisando setup de ajuste..."):
            try:
                # Prepara dados para IA
                dados_ia = {
                    "win_ajuste": f"{win_ajuste:,.0f}",
                    "win_atual": f"{win_atual:,.0f}",
                    "dist_win": f"{dist_win_pts:+,.0f}",
                    "wdo_ajuste": f"{wdo_ajuste:,.2f}",
                    "wdo_atual": f"{wdo_atual:,.2f}",
                    "dist_wdo": f"{dist_wdo_pts:+,.2f}",
                    "ptax": f"{ptax:,.4f}" if ptax else "N/A",
                    "score_win": f"{score_win}/6",
                    "score_wdo": f"{score_wdo}/3",
                    "status_win": status_win[1],
                    "status_wdo": status_wdo[1],
                    "tendencia_win": tendencia_win["padrao"] if tendencia_win else "N/A",
                    "sp500": f"{variacao(sp500):+.2f}%",
                    "nasdaq": f"{variacao(nasdaq):+.2f}%",
                    "vix": f"{variacao(vix):+.2f}%",
                    "dxy": f"{variacao(dxy):+.2f}%",
                    "iron": f"{variacao(iron):+.2f}%",
                }
                
                prompt = f"""⚠️ RESPONDA EM PORTUGUÊS DO BRASIL. SEJA DIRETO.

VOCÊ É UM ESPECIALISTA EM AJUSTE B3.

DADOS DO SETUP:

WIN: Ajuste {dados_ia['win_ajuste']} | Atual {dados_ia['win_atual']} | Distância {dados_ia['dist_win']}
WDO: Ajuste {dados_ia['wdo_ajuste']} | Atual {dados_ia['wdo_atual']} | Distância {dados_ia['dist_wdo']}
PTAX: {dados_ia['ptax']}
Score WIN: {dados_ia['score_win']} | Status: {dados_ia['status_win']}
Score WDO: {dados_ia['score_wdo']} | Status: {dados_ia['status_wdo']}
Tendência WIN: {dados_ia['tendencia_win']}
S&P500: {dados_ia['sp500']} | Nasdaq: {dados_ia['nasdaq']}
VIX: {dados_ia['vix']} | DXY: {dados_ia['dxy']} | Minério: {dados_ia['iron']}

---

RESPONDA EM PORTUGUÊS:

1. ANÁLISE DO AJUSTE WIN: O ajuste está distante ou próximo? O que esperar?
2. ANÁLISE DO AJUSTE WDO: O ajuste está distante ou próximo? O que esperar?
3. CONFLUÊNCIA MACRO: O cenário macro favorece ou atrapalha o ajuste?
4. OPORTUNIDADE: Vale a pena operar o ajuste? (SIM/NÃO/PARCIAIS)
5. RECOMENDAÇÃO: Qual ativo (WIN/WDO) tem melhor setup?
6. CONFIANÇA: De 1 a 10

SEJA DIRETO. PORTUGUÊS APENAS."""

                client = Groq(api_key=key_final)
                completion = client.chat.completions.create(
                    model=modelo_texto,
                    messages=[
                        {"role": "system", "content": "Você é um especialista em ajuste B3. Responda em português."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                )
                
                resposta = completion.choices[0].message.content
                resposta_limpa = re.sub(r'<think>.*?</think>', '', resposta, flags=re.DOTALL)
                resposta_limpa = resposta_limpa.strip()
                
                st.markdown(f"""
                <div class="card-ai">
                    <h4>🤖 Análise IA - Ajuste B3</h4>
                    <div style="color:#a78bfa; font-size:0.85rem; margin-bottom:8px;">
                        ⚡ Análise baseada nos dados do pipeline
                        <span style="margin-left:12px; background:rgba(124,92,252,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">{modelo_texto}</span>
                    </div>
                    <div class="analysis-content">
                        {resposta_limpa.replace(chr(10), '<br>')}
                    </div>
                    <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
                        <span class="smc-tag">🎯 Ajuste B3</span>
                        <span class="smc-tag">📊 WIN/WDO</span>
                        <span class="smc-tag">🏦 Fluxo</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if "historico_ia_ajuste" not in st.session_state:
                    st.session_state.historico_ia_ajuste = []
                st.session_state.historico_ia_ajuste.append({
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "resposta": resposta_limpa,
                })
                
            except Exception as e:
                st.error(f"❌ Erro ao chamar IA: {e}")

# Histórico IA
if st.session_state.get("historico_ia_ajuste"):
    with st.expander("📜 Histórico de análises IA"):
        for i, h in enumerate(reversed(st.session_state.historico_ia_ajuste), 1):
            st.markdown(f"**#{i} • {h['hora']}**")
            st.markdown(h["resposta"])
            st.markdown("---")

# ============================================================
# BLOCO 9: SAÍDA PARA CORE ENGINE
# ============================================================

st.markdown("---")
st.subheader("🤖 9. Dados Preparados para Core Engine")

decisao_setup = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "ativo_principal": "WIN/WDO",
    "win": {
        "score": score_win,
        "checklist": check_win_total,
        "status": status_win[1]
    },
    "wdo": {
        "score": score_wdo,
        "checklist": check_wdo_total,
        "status": status_wdo[1]
    },
    "fonte": fonte_dados,
    "tendencia_win": tendencia_win["padrao"] if tendencia_win else "N/A",
}

with st.expander("📄 Visualizar JSON de decisão"):
    st.json(decisao_setup)

st.caption("Setup Ajuste B3 - módulo quantitativo do Analisador Financeiro")