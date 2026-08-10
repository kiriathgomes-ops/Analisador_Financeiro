#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spike - Chat + Visão com SMC/ICT
================================
Interface Streamlit com suporte a Ctrl+V e análise de gráficos via Groq Vision AI.
Com acesso completo aos dados do pipeline.
"""

import os
import json
import base64
import io
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from PIL import Image

load_dotenv()

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Spike - Chat + Visão SMC",
    page_icon="🐶",
    layout="wide"
)

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_DIR = os.path.join(BASE_DIR, "PromptIA")
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
AVATAR_PATH = os.path.join(BASE_DIR, "Imagens", "SpikeIA.png")
AVATAR_IA = AVATAR_PATH if os.path.exists(AVATAR_PATH) else "🐶"

os.makedirs(PROMPT_DIR, exist_ok=True)

# Caminho do arquivo de configuração
CONFIG_PATH = os.path.join(PROMPT_DIR, "vision_prompt_config.json")

# ============================================================
# CSS PERSONALIZADO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }

    .chat-container {
        background: linear-gradient(145deg, #12141c 0%, #1a1c2a 100%);
        border-radius: 14px;
        padding: 0;
        border: 1px solid #2a2d4a;
        box-shadow: 0 12px 32px rgba(0,0,0,0.4);
        overflow: hidden;
    }

    .chat-header {
        background: #161b22;
        padding: 16px 24px;
        border-bottom: 1px solid #2a2d4a;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .chat-header .titulo {
        font-weight: 700;
        font-size: 1.05rem;
        color: #e6edf3;
    }

    .chat-header .badge {
        font-size: 0.75rem;
        color: #3fb950;
        background: #162419;
        padding: 4px 12px;
        border-radius: 12px;
        border: 1px solid #238636;
    }

    .chat-messages {
        height: 520px;
        overflow-y: auto;
        padding: 20px 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        scroll-behavior: smooth;
        background: #0d1117;
    }

    .chat-messages::-webkit-scrollbar {
        width: 6px;
    }
    .chat-messages::-webkit-scrollbar-track {
        background: #161b22;
    }
    .chat-messages::-webkit-scrollbar-thumb {
        background: #2a3a4a;
        border-radius: 3px;
    }

    .chat-bubble {
        max-width: 92%;
        padding: 16px 20px;
        border-radius: 12px;
        font-size: 0.95rem;
        line-height: 1.6;
        word-break: break-word;
        animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .chat-bubble.user {
        align-self: flex-end;
        background: linear-gradient(135deg, #0969da, #1a7f3a);
        color: white;
        border-bottom-right-radius: 2px;
        max-width: 80%;
    }

    .chat-bubble.ai {
        align-self: flex-start;
        background: #161c24;
        border: 1px solid #2d333b;
        border-bottom-left-radius: 2px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        width: 100%;
        max-width: 95%;
    }

    .ai-report h3 {
        color: #79c0ff;
        font-size: 1.1rem;
        margin: 14px 0 8px 0;
        border-bottom: 1px solid #2a2d4a;
        padding-bottom: 6px;
    }
    .ai-report h3:first-child { margin-top: 0; }
    .ai-report h4 {
        color: #d2a8ff;
        font-size: 1rem;
        margin: 10px 0 4px 0;
    }
    .ai-report p {
        margin-bottom: 8px;
        color: #c9d1d9;
    }
    .ai-report strong {
        color: #ffffff;
    }
    .ai-report ul {
        margin: 6px 0 12px 20px;
    }
    .ai-report li {
        margin-bottom: 4px;
        color: #c9d1d9;
    }
    .ai-report blockquote {
        border-left: 4px solid #58a6ff;
        padding: 8px 16px;
        margin: 10px 0;
        color: #8b949e;
        background: #11151c;
        border-radius: 0 8px 8px 0;
        font-style: italic;
    }

    .smc-tag {
        background: rgba(124, 92, 252, 0.15);
        color: #a78bfa;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        display: inline-block;
        margin: 2px 4px 2px 0;
    }

    .sidebar-info {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2a2d4a;
        margin-bottom: 12px;
    }
    .sidebar-info .label {
        color: #8b949e;
        font-size: 0.75rem;
    }
    .sidebar-info .value {
        color: #e6edf3;
        font-size: 0.95rem;
        font-weight: 600;
    }

    .chat-input-area {
        display: flex;
        gap: 10px;
        padding: 14px 20px;
        background: #161b22;
        border-top: 1px solid #2a2d4a;
        align-items: center;
        flex-wrap: wrap;
    }

    .btn-upload {
        background: #1c2128;
        border: 1px solid #30363d;
        color: #58a6ff;
        padding: 10px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 1rem;
        transition: 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
    }
    .btn-upload:hover {
        border-color: #58a6ff;
        background: #262c36;
    }

    .chat-input {
        flex: 1;
        padding: 12px 18px;
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        color: #e6edf3;
        outline: none;
        font-size: 0.95rem;
        min-width: 150px;
    }
    .chat-input:focus {
        border-color: #58a6ff;
        box-shadow: 0 0 0 3px rgba(88,166,255,0.1);
    }

    .chat-send {
        padding: 12px 22px;
        background: linear-gradient(135deg, #238636, #2ea043);
        border: none;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: 0.2s;
        display: flex;
        align-items: center;
        gap: 8px;
        white-space: nowrap;
    }
    .chat-send:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 16px rgba(35,134,54,0.3);
    }
    .chat-send:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# JAVASCRIPT PARA CTRL+V
# ============================================================

st.markdown(
    """
    <script>
    document.addEventListener('paste', function(e) {
        const items = e.clipboardData.items;
        for (let item of items) {
            if (item.type.startsWith('image/')) {
                const file = item.getAsFile();
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(evt) {
                        const base64 = evt.target.result;
                        const uploader = document.querySelector('input[type="file"]');
                        if (uploader) {
                            const dt = new DataTransfer();
                            dt.items.add(file);
                            uploader.files = dt.files;
                            uploader.dispatchEvent(new Event('change'));
                        }
                    };
                    reader.readAsDataURL(file);
                }
                break;
            }
        }
    });
    </script>
    """,
    unsafe_allow_html=True
)

# ============================================================
# FUNÇÕES DE CARREGAMENTO DE CONFIGURAÇÃO
# ============================================================

def carregar_instrucoes_vision():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Falha ao ler 'vision_prompt_config.json': {e}")

    return {
        "diretrizes_gerais": [
            "Analise o gráfico de Price Action com precisão utilizando conceitos SMC/ICT.",
            "Responda SEMPRE em português do Brasil.",
            "Seja direto, técnico e objetivo."
        ],
        "itens_para_analisar": [
            "Estrutura de Mercado (alta/baixa/lateral)",
            "Order Blocks (OB)",
            "Fair Value Gaps (FVG)",
            "Zonas de Liquidez",
            "Entrada e Saída"
        ],
        "estrutura_resposta_markdown": [
            "### 📊 1. Leitura de Price Action & Tendência",
            "Descreva a tendência geral (alta/baixa/lateral) e o contexto atual.",
            "",
            "### 🎯 2. Níveis Chave (Suportes e Resistências)",
            "Liste os níveis importantes baseados no gráfico.",
            "",
            "### 🔷 3. Order Blocks (OB) e Fair Value Gaps (FVG)",
            "Identifique OB de compra e venda, e FVGs relevantes.",
            "",
            "### 💧 4. Zonas de Liquidez",
            "Onde está a liquidez (acima/abaixo)?",
            "",
            "### 📈 5. Entrada e Saída (Setup SMC)",
            "- **ENTRADA:** Condição ideal para entrada (preço, gatilho)",
            "- **STOP:** Onde colocar o stop",
            "- **ALVO 1:** Primeiro alvo",
            "- **ALVO 2:** Segundo alvo",
            "",
            "### 🚦 6. Recomendação Final",
            "COMPRA/VENDA/AGUARDAR + justificativa",
            "",
            "### 📊 7. Confiança",
            "[1-10] + motivo"
        ]
    }

def construir_system_prompt():
    config = carregar_instrucoes_vision()
    diretrizes = "\n".join([f"- {d}" for d in config.get("diretrizes_gerais", [])])
    itens = "\n".join([f"- {i}" for i in config.get("itens_para_analisar", [])])
    estrutura = "\n".join(config.get("estrutura_resposta_markdown", []))

    return f"""INSTRUÇÕES PARA A IA:
{diretrizes}

O QUE VOCÊ DEVE ANALISAR NA IMAGEM:
{itens}

FORMATO OBRIGATÓRIO DE RESPOSTA (Siga estritamente esta estrutura Markdown em Português):
{estrutura}

⚠️ IMPORTANTE: Responda 100% em português do Brasil. NUNCA use inglês."""

# ============================================================
# FUNÇÕES DE DADOS DO PIPELINE
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados_pipeline() -> Dict[str, Any]:
    """Carrega todos os dados do pipeline para contexto da IA."""
    dados = {}
    
    # 1. Decisão Core
    caminho = os.path.join(COLETAS_DIR, "Decisao_Core.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                decisao = json.load(f)
                dados["decisao"] = decisao
                win_core = decisao.get("analise_operacional", {}).get("WIN_INDICE", {})
                dados["win_vies"] = win_core.get("vies_final", "N/A")
                dados["win_score"] = win_core.get("score_numeric", 0)
                wdo_core = decisao.get("analise_operacional", {}).get("WDO_DOLAR", {})
                dados["wdo_vies"] = wdo_core.get("vies_final", "N/A")
                dados["wdo_score"] = wdo_core.get("score_numeric", 0)
        except:
            pass
    
    # 2. Estimativa de Abertura
    caminho = os.path.join(COLETAS_DIR, "EstimativaAbertura.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                estimativa = json.load(f)
                win_est = estimativa.get("estimativas_abertura", {}).get("WIN_INDICE", {})
                dados["abertura_teorica"] = win_est.get("abertura_teorica_pontos", 0)
                dados["variacao_teorica"] = win_est.get("variacao_teorica_pct", 0)
                dados["gap"] = win_est.get("abertura_teorica_pontos", 0) - win_est.get("pontos_ajuste_base", 0)
                dados["pontos_ajuste"] = win_est.get("pontos_ajuste_base", 0)
        except:
            pass
    
    # 3. Ativos (preço atual)
    caminho = os.path.join(COLETAS_DIR, "DadosAtivosUnificados.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                ativos_data = json.load(f)
                ativos = ativos_data.get("ativos", {})
                win = ativos.get("WIN_FUT", {})
                dados["preco_win"] = win.get("preco", 0)
                dados["var_win"] = win.get("variacao_pct", 0)
                vix = ativos.get("VIX", {})
                dados["vix"] = vix.get("preco", 0)
                dados["vix_var"] = vix.get("variacao_pct", 0)
                sp500 = ativos.get("SP500_FUT", {})
                dados["sp500"] = sp500.get("preco", 0)
                dados["sp500_var"] = sp500.get("variacao_pct", 0)
        except:
            pass
    
    # 4. Métricas (indicadores compostos)
    caminho = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                metricas = json.load(f)
                indicadores = metricas.get("indicadores_compostos", {})
                dados["mercado_externo"] = indicadores.get("indicador_mercado_externo", 0)
                dados["adrs_brasil"] = indicadores.get("indicador_adrs_brasileiras", 0)
        except:
            pass
    
    # 5. Tendências
    caminho = os.path.join(COLETAS_DIR, "Analise_Tendencias.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                tendencias = json.load(f)
                win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
                if win_tend:
                    dados["tendencia_padrao"] = win_tend.get("padrao_comportamento", "N/A")
                    dados["tendencia_var"] = win_tend.get("intervalo_5_para_0", {}).get("variacao_pct", 0)
                    dados["tendencia_dir"] = win_tend.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
        except:
            pass
    
    return dados

def montar_contexto_pipeline(dados: Dict[str, Any]) -> str:
    """Monta o contexto do pipeline para enviar à IA."""
    if not dados:
        return ""
    
    contexto = """
[📊 DADOS DO PIPELINE - Use como referência na análise]:

"""
    # Core Engine
    if dados.get("win_vies"):
        contexto += f"**Core Engine WIN:** {dados['win_vies']} (Score: {dados.get('win_score', 0):.2f})\n"
    if dados.get("wdo_vies"):
        contexto += f"**Core Engine WDO:** {dados['wdo_vies']} (Score: {dados.get('wdo_score', 0):.2f})\n"
    
    # Abertura
    if dados.get("abertura_teorica"):
        contexto += f"**Abertura Teórica WIN:** {dados['abertura_teorica']:,.0f} pts (var: {dados.get('variacao_teorica', 0):+.2f}%, gap: {dados.get('gap', 0):+.0f})\n"
    if dados.get("pontos_ajuste"):
        contexto += f"**Ajuste Base:** {dados['pontos_ajuste']:,.0f} pts\n"
    
    # Preço atual
    if dados.get("preco_win"):
        contexto += f"**Preço Atual WIN:** {dados['preco_win']:,.0f} pts ({dados.get('var_win', 0):+.2f}%)\n"
    if dados.get("vix"):
        contexto += f"**VIX:** {dados['vix']:.2f} ({dados.get('vix_var', 0):+.2f}%)\n"
    if dados.get("sp500"):
        contexto += f"**S&P500:** {dados['sp500']:.2f} ({dados.get('sp500_var', 0):+.2f}%)\n"
    
    # Indicadores
    if dados.get("mercado_externo") is not None:
        contexto += f"**Mercado Externo:** {dados['mercado_externo']:+.2f}%\n"
    if dados.get("adrs_brasil") is not None:
        contexto += f"**ADRs Brasileiras:** {dados['adrs_brasil']:+.2f}%\n"
    
    # Tendências
    if dados.get("tendencia_padrao"):
        contexto += f"**Tendência WIN (últimos 15min):** {dados['tendencia_padrao']} ({dados.get('tendencia_var', 0):+.2f}%)\n"
    
    return contexto

# ============================================================
# FUNÇÕES DE LIMPEZA
# ============================================================

def limpar_pensamento_ia(texto):
    if not texto:
        return ""
    texto_limpo = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL | re.IGNORECASE)
    texto_limpo = re.sub(r'<thought>.*?</thought>', '', texto_limpo, flags=re.DOTALL | re.IGNORECASE)
    if '<think>' in texto_limpo.lower():
        texto_limpo = re.sub(r'.*?</think>', '', texto_limpo, flags=re.DOTALL | re.IGNORECASE)
    posicao_primeiro_titulo = texto_limpo.find("###")
    if posicao_primeiro_titulo != -1:
        texto_limpo = texto_limpo[posicao_primeiro_titulo:]
    return texto_limpo.strip()

# ============================================================
# FUNÇÕES DE IMAGEM
# ============================================================

def imagem_para_base64(uploaded_file, max_size=1200):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), "image/jpeg"

# ============================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE (COM DADOS DO PIPELINE)
# ============================================================

def analisar_grafico(imagem_base64: str, pergunta_trader: str = "", dados_pipeline: Dict = None) -> str:
    """
    Envia a imagem para a API Groq Vision com lista de modelos ativos.
    Inclui dados do pipeline no contexto.
    """
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "❌ **Erro de Configuração:** A chave `GROQ_API_KEY` não foi encontrada."

        client = Groq(api_key=api_key)

        MODELOS_VISUAIS = [
            "qwen/qwen3.6-27b",
            "llama-3.2-11b-vision-preview",
            "meta-llama/llama-4-maverick-17b-128e-instruct"
        ]

        system_prompt = construir_system_prompt()

        # Monta contexto do pipeline
        contexto_pipeline = montar_contexto_pipeline(dados_pipeline) if dados_pipeline else ""

        pergunta = pergunta_trader.strip() if pergunta_trader else "Faça uma análise completa do gráfico anexado."
        
        user_content_text = f"""
{contexto_pipeline}

Pergunta/Instrução do Trader: {pergunta}

⚠️ IMPORTANTE: Use os dados do pipeline acima como referência. Combine a análise do gráfico com os dados quantitativos para uma análise mais completa.
"""

        if not imagem_base64.startswith("data:image"):
            imagem_base64 = f"data:image/png;base64,{imagem_base64}"

        ultimo_erro = None

        for modelo in MODELOS_VISUAIS:
            try:
                response = client.chat.completions.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_content_text},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": imagem_base64}
                                }
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2500,
                )

                resposta_bruta = response.choices[0].message.content
                return limpar_pensamento_ia(resposta_bruta)

            except Exception as e:
                ultimo_erro = e
                msg_erro = str(e).lower()
                if "model_not_found" in msg_erro or "decommissioned" in msg_erro or "404" in msg_erro:
                    continue
                raise e

        return f"❌ **Erro na Análise Vision:** Nenhum modelo disponível respondeu. Último detalhe: {str(ultimo_erro)}"

    except Exception as e:
        return f"❌ **Erro na Análise Vision:** {str(e)}"

# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("🐶 Spike - Chat + Visão SMC")
st.caption("Análise de gráficos com IA • Powered by Groq • Com dados do pipeline")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Configurações")
    
    st.markdown("""
    <div class="sidebar-info">
        <div class="label">Status</div>
        <div class="value">🟢 Online</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 Dados do Pipeline")
    
    # Carrega dados do pipeline para mostrar status
    dados_pipeline = carregar_dados_pipeline()
    if dados_pipeline:
        st.success("✅ Dados carregados")
        if dados_pipeline.get("win_vies"):
            st.caption(f"WIN: {dados_pipeline['win_vies']} (score: {dados_pipeline.get('win_score', 0):.2f})")
        if dados_pipeline.get("preco_win"):
            st.caption(f"WIN Preço: {dados_pipeline['preco_win']:,.0f}")
    else:
        st.warning("⚠️ Nenhum dado do pipeline disponível")
        st.info("💡 Execute `rodar_pipeline_3x.bat` para gerar dados")
    
    st.divider()
    
    if os.path.exists(CONFIG_PATH):
        st.success("✅ Configuração SMC carregada")
    else:
        st.warning("⚠️ Configuração padrão (crie vision_prompt_config.json)")
    
    st.divider()
    
    if st.button("🔄 Limpar conversa", width="stretch"):
        st.session_state.messages = []
        st.rerun()
    
    if st.button("🗑️ Resetar tudo", width="stretch"):
        st.session_state.clear()
        st.rerun()

# ============================================================
# HISTÓRICO DA CONVERSA
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================================
# ÁREA DE CHAT
# ============================================================

st.markdown('<div class="chat-container">', unsafe_allow_html=True)

st.markdown("""
<div class="chat-header">
    <span class="titulo">🧠 Spike Vision Trader</span>
    <span class="badge">👁️ Groq Vision Ativo</span>
</div>
""", unsafe_allow_html=True)

messages_container = st.container()

with messages_container:
    if not st.session_state.messages:
        st.markdown("""
        <div class="chat-bubble ai ai-report">
            <h3><i class="fas fa-rocket"></i> Central de Análise de Gráficos</h3>
            <p>Envie um print do seu gráfico (clique em Anexar ou cole com <strong>Ctrl + V</strong> diretamente na tela) para obter uma leitura completa com conceitos <strong>SMC/ICT</strong>.</p>
            <p style="color: #8b949e; font-size: 0.9rem;">📊 A IA tem acesso aos dados do pipeline para uma análise mais completa.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-bubble user">
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                conteudo = msg["content"]
                conteudo_limpo = limpar_pensamento_ia(conteudo)
                st.markdown(f"""
                <div class="chat-bubble ai ai-report">
                    {conteudo_limpo.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)

# ============================================================
# UPLOAD + INPUT
# ============================================================

col1, col2, col3 = st.columns([1, 6, 1.5])

with col1:
    uploaded_file = st.file_uploader(
        "📎",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        label_visibility="collapsed",
        key="image_uploader"
    )

with col2:
    prompt_input = st.text_input(
        "Digite sua mensagem...",
        placeholder="Digite sua mensagem ou cole uma imagem com Ctrl+V...",
        label_visibility="collapsed",
        key="chat_input"
    )

with col3:
    enviar = st.button("📤 Enviar", width="stretch", type="primary")

# ============================================================
# PROCESSAMENTO
# ============================================================

if enviar and prompt_input:
    st.session_state.messages.append({"role": "user", "content": prompt_input})
    
    # Carrega dados do pipeline
    dados_pipeline = carregar_dados_pipeline()
    
    if uploaded_file:
        with st.spinner("🧠 Analisando gráfico com SMC/ICT + dados do pipeline..."):
            try:
                b64, mime = imagem_para_base64(uploaded_file)
                resposta = analisar_grafico(
                    imagem_base64=b64,
                    pergunta_trader=prompt_input,
                    dados_pipeline=dados_pipeline
                )
                st.session_state.messages.append({"role": "assistant", "content": resposta})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Erro: {e}"})
        st.rerun()
    else:
        with st.spinner("🧠 Pensando..."):
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    st.session_state.messages.append({"role": "assistant", "content": "❌ API Key não encontrada."})
                else:
                    client = Groq(api_key=api_key)
                    system_prompt = construir_system_prompt()
                    
                    contexto = montar_contexto_pipeline(dados_pipeline)
                    user_msg = f"{contexto}\n\nPergunta: {prompt_input}\n\nResponda em português."
                    
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg}
                        ],
                        temperature=0.2,
                        max_tokens=1000,
                    )
                    resposta = response.choices[0].message.content
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Erro: {e}"})
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# BOTÕES RÁPIDOS
# ============================================================

if uploaded_file:
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📊 Análise SMC Completa", width="stretch"):
            with st.spinner("🧠 Analisando gráfico SMC com dados do pipeline..."):
                try:
                    b64, mime = imagem_para_base64(uploaded_file)
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico(
                        imagem_base64=b64,
                        pergunta_trader="Análise SMC/ICT completa do gráfico, considerando os dados do pipeline.",
                        dados_pipeline=dados_pipeline
                    )
                    st.session_state.messages.append({"role": "user", "content": "📊 Análise SMC Completa"})
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    with col2:
        if st.button("🎯 Entrada e Saída", width="stretch"):
            with st.spinner("🧠 Analisando pontos de entrada/saída..."):
                try:
                    b64, mime = imagem_para_base64(uploaded_file)
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico(
                        imagem_base64=b64,
                        pergunta_trader="Identifique os melhores pontos de ENTRADA e SAÍDA baseado no SMC/ICT e nos dados do pipeline.",
                        dados_pipeline=dados_pipeline
                    )
                    st.session_state.messages.append({"role": "user", "content": "🎯 Entrada e Saída"})
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    with col3:
        if st.button("📈 Níveis Chave", width="stretch"):
            with st.spinner("🧠 Identificando níveis chave..."):
                try:
                    b64, mime = imagem_para_base64(uploaded_file)
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico(
                        imagem_base64=b64,
                        pergunta_trader="Liste todos os níveis chave: suportes, resistências, OB e FVG, considerando os dados do pipeline.",
                        dados_pipeline=dados_pipeline
                    )
                    st.session_state.messages.append({"role": "user", "content": "📈 Níveis Chave"})
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    with col4:
        if st.button("📝 Resumo Executivo", width="stretch"):
            with st.spinner("🧠 Resumindo..."):
                try:
                    b64, mime = imagem_para_base64(uploaded_file)
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico(
                        imagem_base64=b64,
                        pergunta_trader="Resuma em 5 frases a tendência, a recomendação e a confluência com os dados do pipeline.",
                        dados_pipeline=dados_pipeline
                    )
                    st.session_state.messages.append({"role": "user", "content": "📝 Resumo Executivo"})
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

# ============================================================
# RODAPÉ
# ============================================================

st.markdown("---")
st.caption("🐶 Spike - Analisador de Gráficos com IA • v3.1 • Com dados do pipeline")