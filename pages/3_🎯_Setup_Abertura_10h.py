# ============================================================
# ARQUIVO: pages/4_🎯_Setup_Abertura_10h.py
#
# MOTIVO:
# Dashboard Institucional de Confluência
# Setup Rompimento das 10:00 (Mercado à Vista)
#
# VERSÃO CORRIGIDA - Sem GAP (à vista não tem gap)
#
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
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Setup Abertura 10:00 - Quant Terminal",
    page_icon="🎯",
    layout="wide",
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

    .card-bull {
        background-color: #0d381e;
        border-left: 5px solid #00c853;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .card-bear {
        background-color: #380d0d;
        border-left: 5px solid #ff3d00;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .card-neutral {
        background-color: #1a1c23;
        border-left: 5px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
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

    .sensibilidade-baixa {
        color: #00c853;
        font-weight: bold;
    }
    .sensibilidade-media {
        color: #ffc107;
        font-weight: bold;
    }
    .sensibilidade-alta {
        color: #ff3d00;
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
    unsafe_allow_html=True
)

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

ARQUIVO_ATIVOS = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")
ARQUIVO_DECISAO = os.path.join(COLETAS_DIR, "Decisao_Core.json")
ARQUIVO_TENDENCIAS = os.path.join(COLETAS_DIR, "Analise_Tendencias.json")
ARQUIVO_METRICAS = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")
ARQUIVO_ESTIMATIVA = os.path.join(COLETAS_DIR, "EstimativaAbertura.json")

# ============================================================
# LEITURA JSON
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def carregar_json(caminho: str) -> Dict[str, Any]:
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

dados_ativos = carregar_json(ARQUIVO_ATIVOS)
dados_decisao = carregar_json(ARQUIVO_DECISAO)
dados_tendencias = carregar_json(ARQUIVO_TENDENCIAS)
dados_metricas = carregar_json(ARQUIVO_METRICAS)
dados_estimativa = carregar_json(ARQUIVO_ESTIMATIVA)

ativos = dados_ativos.get("ativos", dados_ativos)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🎯 Setup 10:00")
st.sidebar.caption("Rompimento da primeira vela (Mercado à Vista)")
st.sidebar.markdown("---")

st.sidebar.markdown("### Status dos Dados")
arquivos_status = {
    "Ativos": ARQUIVO_ATIVOS,
    "Decisão": ARQUIVO_DECISAO,
    "Tendências": ARQUIVO_TENDENCIAS,
    "Métricas": ARQUIVO_METRICAS,
    "Estimativa": ARQUIVO_ESTIMATIVA,
}
for nome, caminho in arquivos_status.items():
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome}")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Limpar Histórico IA 10h", width="stretch"):
    if "historico_ia_10h" in st.session_state:
        st.session_state.historico_ia_10h = []
    st.rerun()

# ============================================================
# CABEÇALHO
# ============================================================

st.title("🎯 Setup Rompimento das 10:00")
st.caption("Análise de confluência para rompimento da primeira vela do mercado à vista")

st.markdown("---")

if not ativos:
    st.error("⚠️ Dados de ativos não encontrados.\nExecute: python main_pipeline.py")
    st.stop()

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def obter_preco(nome):
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("preco", ativo.get("valor", 0.0))
    return 0.0

def obter_variacao(nome):
    ativo = ativos.get(nome, {})
    if isinstance(ativo, dict):
        return ativo.get("variacao_pct", ativo.get("var_pct", 0.0))
    return 0.0

def extrair_tendencia_win():
    if not dados_tendencias:
        return None
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
# ANÁLISE DE SENSIBILIDADE DO MERCADO (SEM GAP)
# ============================================================

st.subheader("📊 Análise de Sensibilidade do Mercado")

# 1. Volatilidade (VIX)
vix = ativos.get("VIX", {})
vix_valor = vix.get("preco", 0)
vix_var = vix.get("variacao_pct", 0)

# 2. Tendência do WIN (referência para o à vista)
tendencia = extrair_tendencia_win()

# 3. Mercado Externo
sp500 = ativos.get("SP500_FUT", {})
sp500_var = sp500.get("variacao_pct", 0)

# 4. EWZ (ETF Brasil)
ewz = ativos.get("EWZ", {})
ewz_var = ewz.get("variacao_pct", 0)

col_sens1, col_sens2, col_sens3, col_sens4 = st.columns(4)

with col_sens1:
    cor_vix = "🟢" if vix_valor < 18 else "🟡" if vix_valor < 25 else "🔴"
    st.metric(
        "⚠️ VIX",
        f"{vix_valor:.2f}",
        f"{vix_var:+.2f}% {cor_vix}",
        delta_color="inverse"
    )

with col_sens2:
    if tendencia:
        emoji = "🟢" if tendencia["variacao"] > 0 else "🔴" if tendencia["variacao"] < 0 else "🟡"
        st.metric(
            "📈 Tendência WIN (referência)",
            f"{emoji} {tendencia['padrao']}",
            f"{tendencia['variacao']:+.2f}%"
        )
    else:
        st.metric("📈 Tendência WIN", "N/A")

with col_sens3:
    cor_sp = "🟢" if sp500_var > 0 else "🔴" if sp500_var < 0 else "🟡"
    st.metric(
        "🇺🇸 S&P500",
        f"{sp500_var:+.2f}%",
        f"{cor_sp} {'Positivo' if sp500_var > 0 else 'Negativo' if sp500_var < 0 else 'Neutro'}"
    )

with col_sens4:
    cor_ewz = "🟢" if ewz_var > 0 else "🔴" if ewz_var < 0 else "🟡"
    st.metric(
        "🇧🇷 EWZ (Brasil)",
        f"{ewz_var:+.2f}%",
        f"{cor_ewz} {'Positivo' if ewz_var > 0 else 'Negativo' if ewz_var < 0 else 'Neutro'}"
    )

# Interpretação da Sensibilidade
st.markdown("---")
st.markdown("**Interpretação da Sensibilidade:**")

sensibilidade_pontos = 0
if vix_valor > 22:
    sensibilidade_pontos += 2
if tendencia and tendencia["tendencia"] == "SUBIU":
    sensibilidade_pontos += 1
elif tendencia and tendencia["tendencia"] == "DESCEU":
    sensibilidade_pontos -= 1
if abs(sp500_var) > 1.0:
    sensibilidade_pontos += 1

if sensibilidade_pontos >= 3:
    st.warning("🔴 MERCADO SENSÍVEL - Alta volatilidade. Reduza lote e aguarde confirmação.")
elif sensibilidade_pontos >= 1:
    st.info("🟡 MERCADO MODERADO - Atenção na abertura. Confirme com volume.")
else:
    st.success("🟢 MERCADO CALMO - Ambiente favorável para o setup.")

st.markdown("---")

# ============================================================
# BLOCO 1 - ATIVO OPERACIONAL (Preço de Ajuste)
# ============================================================

st.subheader("📌 Preço de Ajuste - Referência para Abertura")

# O preço de ajuste do WIN é a referência para o à vista
win_ajuste = obter_preco("WIN_AJUSTE")
win_atual = obter_preco("WIN_FUT")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📊 Preço de Ajuste WIN",
        f"{win_ajuste:,.0f} pts"
    )

with col2:
    st.metric(
        "📈 WIN Futuro (referência)",
        f"{win_atual:,.0f} pts",
        f"{obter_variacao('WIN_FUT'):+.2f}%"
    )

with col3:
    # Distância do ajuste
    dist_ajuste = win_atual - win_ajuste
    st.metric(
        "📏 Distância do Ajuste",
        f"{dist_ajuste:+.0f} pts",
        f"{'Acima' if dist_ajuste > 0 else 'Abaixo' if dist_ajuste < 0 else 'Neutro'}"
    )

with col4:
    # VWAP aproximado (usando PP)
    pp = dados_estimativa.get("pivot_points", {}).get("WIN_FUT", {}).get("PP", 0)
    st.metric(
        "📍 PP (VWAP Ref)",
        f"{pp:,.0f} pts"
    )

st.caption("💡 O mercado à vista abre baseado no preço de ajuste. A distância do ajuste indica se o mercado está 'esticado' ou 'descontado'.")

st.markdown("---")

# ============================================================
# BLOCO 2 - CONTEXTO GLOBAL
# ============================================================

st.subheader("🌐 Contexto Global")

sp500 = ativos.get("SP500_FUT", {})
nasdaq = ativos.get("NASDAQ_FUT", {})
ewz = ativos.get("EWZ", {})
vix = ativos.get("VIX", {})
dxy = ativos.get("DXY", {})

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric(
        "🇺🇸 S&P500",
        f"{sp500.get('preco', 0):,.2f}",
        f"{sp500.get('variacao_pct', 0):+.2f}%"
    )

with c2:
    st.metric(
        "💻 Nasdaq",
        f"{nasdaq.get('preco', 0):,.2f}",
        f"{nasdaq.get('variacao_pct', 0):+.2f}%"
    )

with c3:
    st.metric(
        "🇧🇷 EWZ",
        f"{ewz.get('preco', 0):,.2f}",
        f"{ewz.get('variacao_pct', 0):+.2f}%"
    )

with c4:
    st.metric(
        "⚠️ VIX",
        f"{vix.get('preco', 0):,.2f}",
        f"{vix.get('variacao_pct', 0):+.2f}%",
        delta_color="inverse"
    )

with c5:
    st.metric(
        "💵 DXY",
        f"{dxy.get('preco', 0):,.2f}",
        f"{dxy.get('variacao_pct', 0):+.2f}%",
        delta_color="inverse"
    )

st.markdown("---")

# ============================================================
# BLOCO 3 - ADRS BRASILEIRAS
# ============================================================

st.subheader("📊 ADRs Brasileiras - Peso Ibovespa")

vale = ativos.get("VALE_ADR", {})
petr = ativos.get("PETR_ADR", {})
itub = ativos.get("ITUB_ADR", {})
bbd = ativos.get("BBD_ADR", {})

a1, a2, a3, a4 = st.columns(4)

with a1:
    st.metric(
        "⛏️ VALE",
        f"{vale.get('preco', 0):,.2f}",
        f"{vale.get('variacao_pct', 0):+.2f}%"
    )

with a2:
    st.metric(
        "🛢️ PETR",
        f"{petr.get('preco', 0):,.2f}",
        f"{petr.get('variacao_pct', 0):+.2f}%"
    )

with a3:
    st.metric(
        "🏦 ITUB",
        f"{itub.get('preco', 0):,.2f}",
        f"{itub.get('variacao_pct', 0):+.2f}%"
    )

with a4:
    st.metric(
        "🏦 BBD",
        f"{bbd.get('preco', 0):,.2f}",
        f"{bbd.get('variacao_pct', 0):+.2f}%"
    )

st.markdown("---")

# ============================================================
# BLOCO 4 - SCORE INSTITUCIONAL
# ============================================================

st.subheader("🧮 Score Quantitativo do Setup")

score = 0
score_max = 12

def variacao(ativo):
    return ativo.get("variacao_pct", 0)

# Fatores positivos
if variacao(nasdaq) > 0:
    score += 2
if variacao(sp500) > 0:
    score += 2
if variacao(vale) > 0:
    score += 2
if variacao(petr) > 0:
    score += 2
if variacao(ewz) > 0:
    score += 1

# Fatores de risco
if variacao(vix) < 0:
    score += 2
if variacao(dxy) < 0:
    score += 1

# Bônus: tendência confirma
if tendencia and tendencia["tendencia"] == "SUBIU":
    score += 1

col_score, col_texto = st.columns([1, 3])

with col_score:
    st.metric("Score", f"{score}/{score_max}")

with col_texto:
    if score >= 9:
        st.markdown(f"""
        <div class="card-bull">
            <h3>🟢 VIÉS COMPRADOR</h3>
            Score institucional: <b>{score}/{score_max}</b>
            <br><br>
            Ambiente favorável para rompimento da máxima da primeira barra.
        </div>
        """, unsafe_allow_html=True)
    elif score <= 4:
        st.markdown(f"""
        <div class="card-bear">
            <h3>🔴 VIÉS VENDEDOR</h3>
            Score institucional: <b>{score}/{score_max}</b>
            <br><br>
            Pressão externa negativa.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="card-neutral">
            <h3>🟡 MERCADO NEUTRO</h3>
            Score: <b>{score}/{score_max}</b>
            <br><br>
            Aguardar confirmação do preço.
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# BLOCO 5 - CONFLUÊNCIA COM CORE ENGINE
# ============================================================

st.subheader("⚙️ Confluência Core Engine + Setup 10h")

win_core = dados_decisao.get("analise_operacional", {}).get("WIN_INDICE", {})
win_vies = win_core.get("vies_final", "N/D")
win_score = win_core.get("score_numeric", 0)

col_core, col_setup = st.columns(2)

with col_core:
    st.info(f"""
    **Core Engine - WIN**
    Viés: `{win_vies}`
    Score: `{win_score}`
    """)

with col_setup:
    if score >= 9:
        setup = "COMPRA"
    elif score <= 4:
        setup = "VENDA"
    else:
        setup = "NEUTRO"
    
    st.info(f"""
    **Setup 10:00**
    Viés: `{setup}`
    Score Institucional: `{score}/{score_max}`
    """)

st.markdown("---")

# ============================================================
# BLOCO 6 - RESULTADO FINAL
# ============================================================

st.subheader("🎯 Decisão Operacional")

setup_compra = "COMPRA" in str(win_vies).upper()
setup_venda = "VENDA" in str(win_vies).upper()
score_compra = score >= 7
score_venda = score <= 5

if setup_compra and score_compra:
    st.success("""
    🟢 CONFLUÊNCIA COMPRADORA
    Rompimento da máxima da primeira barra autorizado após confirmação de volume.
    """)
elif setup_venda and score_venda:
    st.error("""
    🔴 CONFLUÊNCIA VENDEDORA
    Rompimento da mínima pode ser operado após confirmação.
    """)
else:
    st.warning("""
    🟡 SEM CONFLUÊNCIA
    Aguardar preço, volume e estrutura.
    """)

st.markdown("---")

# ============================================================
# BLOCO 7 - ANÁLISE IA - ROMPIMENTO 10h
# ============================================================

st.subheader("🧠 Análise IA - Rompimento 10h")

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
        key="groq_key_10h"
    )
    modelo_texto = st.selectbox(
        "Modelo (texto)",
        ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
        index=0,
        key="modelo_10h"
    )

if st.button("📊 Analisar Rompimento 10h (IA)", type="primary", key="btn_10h"):
    key_final = groq_key_input or groq_key
    
    if not key_final:
        st.error("⚠️ Informe a Groq API Key")
    else:
        with st.spinner("🧠 Analisando setup de rompimento 10h..."):
            try:
                dados_ia = {
                    "ajuste": f"{win_ajuste:,.0f}",
                    "win_atual": f"{win_atual:,.0f}",
                    "dist_ajuste": f"{dist_ajuste:+.0f}",
                    "vix": f"{vix.get('preco', 0):.2f}",
                    "vix_var": f"{vix.get('variacao_pct', 0):+.2f}%",
                    "sp500": f"{sp500.get('variacao_pct', 0):+.2f}%",
                    "ewz": f"{ewz.get('variacao_pct', 0):+.2f}%",
                    "score": f"{score}/{score_max}",
                    "setup": setup,
                    "win_vies": win_vies,
                    "tendencia": tendencia["padrao"] if tendencia else "N/A",
                    "sensibilidade": "Alta" if sensibilidade_pontos >= 3 else "Moderada" if sensibilidade_pontos >= 1 else "Baixa",
                }
                
                prompt = f"""⚠️ RESPONDA EM PORTUGUÊS DO BRASIL.

VOCÊ É UM ESPECIALISTA EM SETUP DE ROMPIMENTO DAS 10:00 (MERCADO À VISTA).

DADOS DO SETUP:

Preço de Ajuste: {dados_ia['ajuste']}
WIN Futuro: {dados_ia['win_atual']}
Distância do Ajuste: {dados_ia['dist_ajuste']}
VIX: {dados_ia['vix']} ({dados_ia['vix_var']})
S&P500: {dados_ia['sp500']}
EWZ (Brasil): {dados_ia['ewz']}
Score Institucional: {dados_ia['score']}
Viés Setup: {dados_ia['setup']}
Core Engine WIN: {dados_ia['win_vies']}
Tendência: {dados_ia['tendencia']}
Sensibilidade: {dados_ia['sensibilidade']}

---

RESPONDA EM PORTUGUÊS:

1. ROMPIMENTO ESPERADO: O mercado deve romper a máxima ou mínima da primeira vela?

2. VOLATILIDADE ESPERADA: O mercado deve ter movimento rápido ou lento na abertura?

3. NÍVEIS CHAVE: Onde colocar stop e alvo (considerando o setup)?

4. LIQUIDEZ: Abertura deve ter bom volume ou pode ser seca?

5. RECOMENDAÇÃO: Operar ou aguardar os primeiros minutos?

6. CONFIANÇA: De 1 a 10

SEJA DIRETO. PORTUGUÊS APENAS."""

                client = Groq(api_key=key_final)
                completion = client.chat.completions.create(
                    model=modelo_texto,
                    messages=[
                        {"role": "system", "content": "Você é um especialista em setup de rompimento do mercado à vista. Responda em português."},
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
                    <h4>🤖 Análise IA - Rompimento 10h (Mercado à Vista)</h4>
                    <div style="color:#a78bfa; font-size:0.85rem; margin-bottom:8px;">
                        ⚡ Análise baseada nos dados do pipeline
                        <span style="margin-left:12px; background:rgba(124,92,252,0.15); padding:2px 10px; border-radius:12px; font-size:0.7rem;">{modelo_texto}</span>
                    </div>
                    <div class="analysis-content">
                        {resposta_limpa.replace(chr(10), '<br>')}
                    </div>
                    <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
                        <span class="smc-tag">🎯 Rompimento 10h</span>
                        <span class="smc-tag">📊 Mercado à Vista</span>
                        <span class="smc-tag">🚀 Primeira Vela</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if "historico_ia_10h" not in st.session_state:
                    st.session_state.historico_ia_10h = []
                st.session_state.historico_ia_10h.append({
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "resposta": resposta_limpa,
                })
                
            except Exception as e:
                st.error(f"❌ Erro ao chamar IA: {e}")

if st.session_state.get("historico_ia_10h"):
    with st.expander("📜 Histórico de análises IA"):
        for i, h in enumerate(reversed(st.session_state.historico_ia_10h), 1):
            st.markdown(f"**#{i} • {h['hora']}**")
            st.markdown(h["resposta"])
            st.markdown("---")

# ============================================================
# BLOCO 8 - CHECKLIST OPERACIONAL
# ============================================================

st.markdown("---")
st.subheader("✅ Checklist Candle 10:00 - 10:05")

ck1 = st.checkbox("Volume acima da média (confirmação)", key="ck_10h_1")
ck2 = st.checkbox("Rompimento ocorreu com fechamento forte", key="ck_10h_2")
ck3 = st.checkbox("Direção alinhada com o viés (Setup + Core)", key="ck_10h_3")
ck4 = st.checkbox("Preço respeitou PP/VWAP", key="ck_10h_4")
ck5 = st.checkbox("Análise IA revisada e concordo com a direção", key="ck_10h_5")

if ck1 and ck2 and ck3 and ck4 and ck5:
    st.success("🚀 SETUP VALIDADO - Entrada permitida")
else:
    st.info("⏳ Aguardando todas as confirmações")

# ============================================================
# RODAPÉ
# ============================================================

st.markdown("---")
st.caption("Setup Abertura 10:00 - Mercado à Vista • Analisador Financeiro Quant v2.0")