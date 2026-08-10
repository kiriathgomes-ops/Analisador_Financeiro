#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spike Híbrido - Chat + Visão SMC (VERSÃO PT-BR FORÇADO)
========================================================
Combina:
- Contexto rico do pipeline (todos os dados)
- Tradução forçada para português
- Prompt ultra-restritivo
- Modelo Llama 3.2 (melhor PT-BR)
- Interface interativa do Spike Chat
- 🔥 ROTAÇÃO AUTOMÁTICA DE CHAVES API
"""

import sys
import os
import json
import base64
import io
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from PIL import Image

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()

# ============================================================
# ADICIONA A RAIZ AO PATH PARA IMPORTAR O KEYMANAGER
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.KeyManager import get_groq_client, key_manager

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Spike Híbrido - Chat + Visão PT-BR",
    page_icon="🐶",
    layout="wide"
)

# ============================================================
# CAMINHOS
# ============================================================

PROMPT_DIR = BASE_DIR / "PromptIA"
COLETAS_DIR = BASE_DIR / "Coletas"
AVATAR_PATH = BASE_DIR / "Imagens" / "SpikeIA.png"
AVATAR_IA = str(AVATAR_PATH) if os.path.exists(AVATAR_PATH) else "🐶"

os.makedirs(PROMPT_DIR, exist_ok=True)

# ============================================================
# CSS PERSONALIZADO (MESMO DO SPIKE CHAT)
# ============================================================

st.markdown("""
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

.smc-tag {
    background: rgba(124, 92, 252, 0.15);
    color: #a78bfa;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.7rem;
    display: inline-block;
    margin: 2px 4px 2px 0;
}

.aviso-pt {
    background: rgba(0, 212, 255, 0.1);
    border-left: 4px solid #00d4ff;
    padding: 8px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 0.8rem;
    color: #8b949e;
    margin-bottom: 12px;
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
""", unsafe_allow_html=True)

# ============================================================
# JAVASCRIPT PARA CTRL+V
# ============================================================

st.markdown("""
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
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÃO DE TRADUÇÃO FORÇADA (DO SETUP 09h)
# ============================================================

def forcar_portugues(resposta: str) -> str:
    """Converte qualquer resposta para português - FORÇA BRUTA."""
    
    traducao = {
        # Mercado e Tendência
        "Market": "Mercado", "Trend": "Tendência", "Uptrend": "Alta",
        "Downtrend": "Baixa", "Sideways": "Lateral", "Range": "Lateral",
        "Bullish": "Altista", "Bearish": "Baixista",
        
        # Ações
        "Buy": "Compra", "Sell": "Venda", "Entry": "Entrada",
        "Exit": "Saída", "Trade": "Operação", "Position": "Posição",
        
        # Análise Técnica
        "Price": "Preço", "Support": "Suporte", "Resistance": "Resistência",
        "Level": "Nível", "Target": "Alvo", "Stop": "Stop",
        "Loss": "Perda", "Analysis": "Análise", "Structure": "Estrutura",
        "Liquidity": "Liquidez", "Confirmation": "Confirmação",
        "Break": "Rompimento", "Retest": "Reteste",
        
        # Intensidade
        "Strong": "Forte", "Weak": "Fraco", "Moderate": "Moderado",
        "High": "Alto", "Low": "Baixo", "Very": "Muito",
        
        # Tempo
        "Open": "Abertura", "Close": "Fechamento", "Volume": "Volume",
        "Momentum": "Momentum", "Divergence": "Divergência",
        
        # Verbos
        "is": "está", "are": "estão", "was": "estava", "were": "estavam",
        "has": "tem", "have": "têm", "will": "vai", "would": "iria",
        "could": "poderia", "should": "deveria", "can": "pode",
        
        # Conjunções
        "and": "e", "or": "ou", "but": "mas", "because": "porque",
        "therefore": "portanto", "however": "no entanto",
        "although": "embora", "while": "enquanto",
        "when": "quando", "where": "onde", "than": "que",
        
        # Comparativos
        "more": "mais", "less": "menos", "above": "acima",
        "below": "abaixo", "near": "próximo", "far": "longe",
        "between": "entre", "among": "entre",
        
        # SMC/ICT (mantém em inglês mas adiciona explicação)
        "Order Block": "Order Block (OB)",
        "Fair Value Gap": "Fair Value Gap (FVG)",
        "FVG": "FVG",
        "OB": "OB",
        "SMC": "SMC",
        "ICT": "ICT",
    }
    
    palavras = resposta.split()
    palavras_traduzidas = []
    
    for palavra in palavras:
        palavra_limpa = palavra.strip(".,!?;:")
        traducao_palavra = traducao.get(palavra_limpa, palavra)
        
        # Mantém pontuação
        if palavra != palavra_limpa:
            pontuacao = palavra[-1] if palavra[-1] in ".,!?;:" else ""
            if pontuacao:
                traducao_palavra += pontuacao
        
        # Mantém maiúsculas/minúsculas
        if palavra_limpa.isupper():
            traducao_palavra = traducao_palavra.upper()
        elif palavra_limpa.istitle():
            traducao_palavra = traducao_palavra.title()
        
        palavras_traduzidas.append(traducao_palavra)
    
    return " ".join(palavras_traduzidas)

def garantir_portugues(resposta: str) -> str:
    """Versão final - combina detecção + tradução forçada."""
    
    # 1. Primeiro remove tags de pensamento
    resposta = re.sub(r'<think>.*?</think>', '', resposta, flags=re.DOTALL | re.IGNORECASE)
    resposta = re.sub(r'<thought>.*?</thought>', '', resposta, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Detecta se já está em português
    palavras_portugues = [
        "mercado", "tendência", "compra", "venda", "preço", "suporte", 
        "resistência", "análise", "estrutura", "liquidez", "entrada", 
        "alvo", "stop", "perda", "rompimento", "confirmação", "nível",
        "abertura", "fechamento", "volume", "divergência"
    ]
    
    tem_portugues = any(p in resposta.lower() for p in palavras_portugues)
    
    if tem_portugues:
        # Já está em PT-BR, apenas substitui alguns termos comuns
        traducao_simples = {
            "Market": "Mercado", "Trend": "Tendência", "Buy": "Compra",
            "Sell": "Venda", "Price": "Preço", "Support": "Suporte",
            "Resistance": "Resistência", "Entry": "Entrada", "Target": "Alvo",
            "Stop": "Stop", "Analysis": "Análise", "Structure": "Estrutura",
            "Liquidity": "Liquidez", "Break": "Rompimento",
            "Confirmation": "Confirmação", "Level": "Nível",
        }
        for en, pt in traducao_simples.items():
            resposta = resposta.replace(en, pt)
        return resposta
    
    # 3. Força tradução completa
    aviso = "⚠️ **RESPOSTA TRADUZIDA PARA PORTUGUÊS:**\n\n"
    return aviso + forcar_portugues(resposta)

# ============================================================
# FUNÇÕES DE DADOS DO PIPELINE (VERSÃO RICA)
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados_pipeline() -> Dict[str, Any]:
    """Carrega TODOS os dados do pipeline (versão rica)."""
    dados = {}
    
    # 1. Decisão Core
    caminho = COLETAS_DIR / "Decisao_Core.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                decisao = json.load(f)
                win_core = decisao.get("analise_operacional", {}).get("WIN_INDICE", {})
                dados["win_vies"] = win_core.get("vies_final", "N/A")
                dados["win_score"] = win_core.get("score_numeric", 0)
                dados["win_fatores"] = win_core.get("fatores_relevantes", [])
                
                wdo_core = decisao.get("analise_operacional", {}).get("WDO_DOLAR", {})
                dados["wdo_vies"] = wdo_core.get("vies_final", "N/A")
                dados["wdo_score"] = wdo_core.get("score_numeric", 0)
        except:
            pass
    
    # 2. Estimativa de Abertura
    caminho = COLETAS_DIR / "EstimativaAbertura.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                estimativa = json.load(f)
                win_est = estimativa.get("estimativas_abertura", {}).get("WIN_INDICE", {})
                dados["abertura_teorica"] = win_est.get("abertura_teorica_pontos", 0)
                dados["variacao_teorica"] = win_est.get("variacao_teorica_pct", 0)
                dados["pontos_ajuste"] = win_est.get("pontos_ajuste_base", 0)
                dados["gap"] = dados["abertura_teorica"] - dados["pontos_ajuste"] if dados["abertura_teorica"] else 0
                
                wdo_est = estimativa.get("estimativas_abertura", {}).get("WDO_DOLAR", {})
                dados["wdo_abertura"] = wdo_est.get("abertura_teorica_pontos", 0)
                dados["wdo_variacao"] = wdo_est.get("variacao_teorica_pct", 0)
                
                # Pivot Points
                pivots = estimativa.get("pivot_points", {})
                win_pivot = pivots.get("WIN_FUT", {})
                dados["win_r1"] = win_pivot.get("R1", 0)
                dados["win_r2"] = win_pivot.get("R2", 0)
                dados["win_pp"] = win_pivot.get("PP", 0)
                dados["win_s1"] = win_pivot.get("S1", 0)
                dados["win_s2"] = win_pivot.get("S2", 0)
        except:
            pass
    
    # 3. Ativos (preço atual de TODOS)
    caminho = COLETAS_DIR / "DadosAtivosUnificados.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                ativos_data = json.load(f)
                ativos = ativos_data.get("ativos", {})
                
                # WIN
                win = ativos.get("WIN_FUT", {})
                dados["preco_win"] = win.get("preco", 0)
                dados["var_win"] = win.get("variacao_pct", 0)
                
                # WDO
                wdo = ativos.get("WDO_FUT", {})
                dados["preco_wdo"] = wdo.get("preco", 0)
                dados["var_wdo"] = wdo.get("variacao_pct", 0)
                
                # VIX
                vix = ativos.get("VIX", {})
                dados["vix"] = vix.get("preco", 0)
                dados["vix_var"] = vix.get("variacao_pct", 0)
                
                # S&P500
                sp500 = ativos.get("SP500_FUT", {})
                dados["sp500"] = sp500.get("preco", 0)
                dados["sp500_var"] = sp500.get("variacao_pct", 0)
                
                # NASDAQ
                nasdaq = ativos.get("NASDAQ_FUT", {})
                dados["nasdaq"] = nasdaq.get("preco", 0)
                dados["nasdaq_var"] = nasdaq.get("variacao_pct", 0)
                
                # EWZ
                ewz = ativos.get("EWZ", {})
                dados["ewz"] = ewz.get("preco", 0)
                dados["ewz_var"] = ewz.get("variacao_pct", 0)
                
                # Commodities
                iron = ativos.get("IRON_ORE", {})
                dados["iron"] = iron.get("preco", 0)
                dados["iron_var"] = iron.get("variacao_pct", 0)
                
                crude = ativos.get("CRUDE_OIL", {})
                dados["crude"] = crude.get("preco", 0)
                dados["crude_var"] = crude.get("variacao_pct", 0)
                
                # ADRs
                vale = ativos.get("VALE_ADR", {})
                dados["vale"] = vale.get("preco", 0)
                dados["vale_var"] = vale.get("variacao_pct", 0)
                
                petr = ativos.get("PETR_ADR", {})
                dados["petr"] = petr.get("preco", 0)
                dados["petr_var"] = petr.get("variacao_pct", 0)
        except:
            pass
    
    # 4. Métricas (indicadores compostos)
    caminho = COLETAS_DIR / "Metricas_Calculadas.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                metricas = json.load(f)
                indicadores = metricas.get("indicadores_compostos", {})
                dados["mercado_externo"] = indicadores.get("indicador_mercado_externo", 0)
                dados["adrs_brasil"] = indicadores.get("indicador_adrs_brasileiras", 0)
                
                # Spread
                cambio = metricas.get("cambio_e_arbitragem", {})
                dados["spread_wdo_ptax"] = cambio.get("spread_wdo_ptax_pontos", 0)
                
                # Curva DI
                juros = metricas.get("curva_juros_b3", {})
                dados["inclinacao_di"] = juros.get("inclinacao_29_27_bps", 0)
        except:
            pass
    
    # 5. Tendências (últimos 15min)
    caminho = COLETAS_DIR / "Analise_Tendencias.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r") as f:
                tendencias = json.load(f)
                
                # WIN
                win_tend = tendencias.get("WIN_FUT") or tendencias.get("BMFBOVESPA:WIN1!")
                if win_tend:
                    dados["tendencia_padrao"] = win_tend.get("padrao_comportamento", "N/A")
                    dados["tendencia_var"] = win_tend.get("intervalo_5_para_0", {}).get("variacao_pct", 0)
                    dados["tendencia_dir"] = win_tend.get("intervalo_5_para_0", {}).get("tendencia", "N/A")
                
                # WDO
                wdo_tend = tendencias.get("WDO_FUT") or tendencias.get("BMFBOVESPA:WDO1!")
                if wdo_tend:
                    dados["wdo_tendencia"] = wdo_tend.get("padrao_comportamento", "N/A")
                    dados["wdo_tendencia_var"] = wdo_tend.get("intervalo_5_para_0", {}).get("variacao_pct", 0)
        except:
            pass
    
    return dados

# ============================================================
# FUNÇÃO DE MONTAR CONTEXTO (VERSÃO RICA + FORMATADA)
# ============================================================

def montar_contexto_pipeline(dados: Dict[str, Any]) -> str:
    """Monta contexto completo e formatado do pipeline."""
    if not dados:
        return ""
    
    contexto = """
📊 **DADOS DO PIPELINE - Use como referência na análise:**

"""
    
    # ==========================================================
    # 1. CORE ENGINE
    # ==========================================================
    contexto += "### 🎯 Core Engine\n"
    if dados.get("win_vies"):
        contexto += f"• **WIN:** {dados['win_vies']} (Score: {dados.get('win_score', 0):.2f})\n"
    if dados.get("wdo_vies"):
        contexto += f"• **WDO:** {dados['wdo_vies']} (Score: {dados.get('wdo_score', 0):.2f})\n"
    
    # Fatores do WIN (se disponíveis)
    if dados.get("win_fatores"):
        contexto += "• **Fatores WIN:**\n"
        for fator in dados["win_fatores"][:3]:
            contexto += f"  - {fator}\n"
    contexto += "\n"
    
    # ==========================================================
    # 2. ABERTURA TEÓRICA
    # ==========================================================
    contexto += "### 📈 Abertura Teórica\n"
    if dados.get("abertura_teorica"):
        contexto += f"• **WIN:** {dados['abertura_teorica']:,.0f} pts (var: {dados.get('variacao_teorica', 0):+.2f}%, gap: {dados.get('gap', 0):+.0f})\n"
    if dados.get("wdo_abertura"):
        contexto += f"• **WDO:** {dados['wdo_abertura']:.2f} pts (var: {dados.get('wdo_variacao', 0):+.2f}%)\n"
    if dados.get("pontos_ajuste"):
        contexto += f"• **Ajuste Base:** {dados['pontos_ajuste']:,.0f} pts\n"
    contexto += "\n"
    
    # ==========================================================
    # 3. PREÇOS ATUAIS (MAIS DETALHADO)
    # ==========================================================
    contexto += "### 💰 Preços e Variações\n"
    if dados.get("preco_win"):
        contexto += f"• **WIN:** {dados['preco_win']:,.0f} pts ({dados.get('var_win', 0):+.2f}%)\n"
    if dados.get("preco_wdo"):
        contexto += f"• **WDO:** {dados['preco_wdo']:.2f} pts ({dados.get('var_wdo', 0):+.2f}%)\n"
    if dados.get("vix"):
        contexto += f"• **VIX:** {dados['vix']:.2f} ({dados.get('vix_var', 0):+.2f}%)\n"
    if dados.get("sp500"):
        contexto += f"• **S&P500:** {dados['sp500']:.2f} ({dados.get('sp500_var', 0):+.2f}%)\n"
    if dados.get("nasdaq"):
        contexto += f"• **Nasdaq:** {dados['nasdaq']:.2f} ({dados.get('nasdaq_var', 0):+.2f}%)\n"
    if dados.get("ewz"):
        contexto += f"• **EWZ (Brasil):** ${dados['ewz']:.2f} ({dados.get('ewz_var', 0):+.2f}%)\n"
    contexto += "\n"
    
    # ==========================================================
    # 4. ESCORAS (PIVOT POINTS)
    # ==========================================================
    if any([dados.get("win_r1"), dados.get("win_pp")]):
        contexto += "### 📍 Escoras WIN\n"
        if dados.get("win_r2"):
            contexto += f"• **R2:** {dados['win_r2']:,.0f}\n"
        if dados.get("win_r1"):
            contexto += f"• **R1:** {dados['win_r1']:,.0f}\n"
        if dados.get("win_pp"):
            contexto += f"• **PP:** {dados['win_pp']:,.0f}\n"
        if dados.get("win_s1"):
            contexto += f"• **S1:** {dados['win_s1']:,.0f}\n"
        if dados.get("win_s2"):
            contexto += f"• **S2:** {dados['win_s2']:,.0f}\n"
        contexto += "\n"
    
    # ==========================================================
    # 5. COMMODITIES E MACRO
    # ==========================================================
    if dados.get("iron") or dados.get("crude"):
        contexto += "### ⛏️ Commodities\n"
        if dados.get("iron"):
            contexto += f"• **Minério:** ${dados['iron']:.2f} ({dados.get('iron_var', 0):+.2f}%)\n"
        if dados.get("crude"):
            contexto += f"• **Petróleo:** ${dados['crude']:.2f} ({dados.get('crude_var', 0):+.2f}%)\n"
        contexto += "\n"
    
    # ==========================================================
    # 6. ADRs BRASILEIRAS
    # ==========================================================
    if dados.get("vale") or dados.get("petr"):
        contexto += "### 🏢 ADRs Brasileiras\n"
        if dados.get("vale"):
            contexto += f"• **VALE:** ${dados['vale']:.2f} ({dados.get('vale_var', 0):+.2f}%)\n"
        if dados.get("petr"):
            contexto += f"• **PETR:** ${dados['petr']:.2f} ({dados.get('petr_var', 0):+.2f}%)\n"
        contexto += "\n"
    
    # ==========================================================
    # 7. INDICADORES COMPOSTOS
    # ==========================================================
    if dados.get("mercado_externo") is not None or dados.get("adrs_brasil") is not None:
        contexto += "### 🧮 Indicadores Compostos\n"
        if dados.get("mercado_externo") is not None:
            contexto += f"• **Mercado Externo:** {dados['mercado_externo']:+.2f}%\n"
        if dados.get("adrs_brasil") is not None:
            contexto += f"• **ADRs Brasileiras:** {dados['adrs_brasil']:+.2f}%\n"
        if dados.get("spread_wdo_ptax") is not None:
            contexto += f"• **Spread WDO x PTAX:** {dados['spread_wdo_ptax']:+.1f} pts\n"
        if dados.get("inclinacao_di") is not None:
            contexto += f"• **Inclinação DI (29-27):** {dados['inclinacao_di']:+.1f} bps\n"
        contexto += "\n"
    
    # ==========================================================
    # 8. TENDÊNCIAS (15min)
    # ==========================================================
    if dados.get("tendencia_padrao"):
        contexto += "### 📊 Tendências (últimos 15min)\n"
        contexto += f"• **WIN:** {dados['tendencia_padrao']} ({dados.get('tendencia_var', 0):+.2f}%) - {dados.get('tendencia_dir', 'N/A')}\n"
    if dados.get("wdo_tendencia"):
        contexto += f"• **WDO:** {dados['wdo_tendencia']} ({dados.get('wdo_tendencia_var', 0):+.2f}%)\n"
    contexto += "\n"
    
    return contexto

# ============================================================
# FUNÇÃO DE PROMPT ULTRA-RESTRITIVO
# ============================================================

def construir_prompt_ultra_restritivo() -> str:
    """Prompt ultra-restritivo para forçar PT-BR e análise SMC."""
    
    return """⚠️ **INSTRUÇÕES OBRIGATÓRIAS - LEIA COM ATENÇÃO:**

1. **IDIOMA OBRIGATÓRIO:** Você DEVE responder 100% em PORTUGUÊS DO BRASIL.
2. **NUNCA** use inglês, mesmo em termos técnicos.
3. **NÃO MOSTRE** seu raciocínio interno.
4. **SEJA DIRETO** e objetivo.

---

**ANÁLISE SMC/ICT - ESTRUTURA DE MERCADO:**

Analise o gráfico e os dados do pipeline e responda com a seguinte estrutura:

### 📊 1. Leitura de Price Action e Tendência
- Qual a tendência geral (Alta/Baixa/Lateral)?
- O contexto atual do mercado.

### 🎯 2. Níveis Chave (Suportes e Resistências)
- Liste os níveis mais importantes baseados no gráfico.
- Destaque os que estão próximos do preço atual.

### 🔷 3. Order Blocks (OB) e Fair Value Gaps (FVG)
- Identifique OBs de compra e venda.
- Identifique FVGs relevantes.

### 💧 4. Zonas de Liquidez
- Onde está a liquidez (acima e abaixo)?
- Possíveis sweep de topos ou fundos.

### 📈 5. Entrada e Saída (Setup SMC)
- **ENTRADA:** Condição ideal para entrada (preço, gatilho)
- **STOP:** Onde colocar o stop loss
- **ALVO 1:** Primeiro alvo (risco/recompensa mínimo 1:1)
- **ALVO 2:** Segundo alvo (risco/recompensa 1:2+)

### 🚦 6. Recomendação Final
- COMPRA / VENDA / AGUARDAR
- Justificativa resumida

### 📊 7. Confiança
- De 1 a 10
- Motivo da confiança

---

⚠️ **LEMBRE-SE:**
- Use os dados do pipeline como referência.
- Combine análise técnica com dados quantitativos.
- Seja prático e útil para o trader.

RESPONDA 100% EM PORTUGUÊS DO BRASIL.
"""

# ============================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE (HÍBRIDA) COM ROTAÇÃO DE CHAVES
# ============================================================

def analisar_grafico_hibrido(
    imagem_base64: str, 
    pergunta_trader: str = "", 
    dados_pipeline: Dict = None
) -> str:
    """
    Versão híbrida com rotação de chaves:
    - Contexto rico do pipeline
    - Tradução forçada
    - Prompt ultra-restritivo
    - Modelo Llama 3.2 (melhor PT-BR)
    """
    try:
        # 🔥 USA O GERENCIADOR DE CHAVES PARA ROTAÇÃO
        try:
            client, key_utilizada = get_groq_client()
            print(f"🔑 Usando chave: {key_utilizada[:20]}...")
        except Exception as e:
            return f"❌ **Erro ao obter chave API:** {str(e)}"

        MODELOS_VISUAIS = [
            "llama-3.2-11b-vision-preview",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "qwen/qwen3.6-27b"
        ]

        system_prompt = construir_prompt_ultra_restritivo()
        contexto_pipeline = montar_contexto_pipeline(dados_pipeline) if dados_pipeline else ""
        pergunta = pergunta_trader.strip() if pergunta_trader else "Faça uma análise completa do gráfico anexado."

        user_content = f"""
{contexto_pipeline}

---

**PERGUNTA/INSTRUÇÃO DO TRADER:**
{pergunta}

---

⚠️ **ATENÇÃO:**
- Use os dados do pipeline como referência.
- Combine a análise do gráfico com os dados quantitativos.
- Responda 100% em PORTUGUÊS do Brasil.
"""

        if not imagem_base64.startswith("data:image"):
            imagem_base64 = f"data:image/jpeg;base64,{imagem_base64}"

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
                                {"type": "text", "text": user_content},
                                {"type": "image_url", "image_url": {"url": imagem_base64}}
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=3000,
                )

                # Registra uso de tokens
                if hasattr(response, 'usage'):
                    tokens = response.usage.total_tokens
                    key_manager.registrar_uso(key_utilizada, tokens)
                    print(f"📊 Tokens usados: {tokens} (chave: {key_utilizada[:8]}...)")

                resposta_bruta = response.choices[0].message.content
                return garantir_portugues(resposta_bruta)

            except Exception as e:
                erro_msg = str(e).lower()
                ultimo_erro = e

                # Rate limit detectado
                if "429" in erro_msg or "rate_limit" in erro_msg:
                    print(f"⚠️ Rate limit detectado na chave {key_utilizada[:8]}...")
                    key_manager.marcar_rate_limit(key_utilizada)
                    
                    # Tenta com a próxima chave
                    try:
                        client, key_utilizada = get_groq_client()
                        print(f"🔑 Trocando para nova chave: {key_utilizada[:20]}...")
                        continue
                    except Exception as e2:
                        print(f"❌ Erro ao trocar chave: {e2}")
                        return "❌ Todas as chaves em rate limit. Tente novamente em algumas horas."

                # Modelo não encontrado, tenta próximo
                elif "model_not_found" in erro_msg or "decommissioned" in erro_msg or "404" in erro_msg:
                    print(f"⚠️ Modelo {modelo} não encontrado, tentando próximo...")
                    continue

                # Outros erros
                else:
                    raise e

        return f"❌ **Erro:** Todos os modelos falharam. Último erro: {str(ultimo_erro)}"

    except Exception as e:
        return f"❌ **Erro na Análise:** {str(e)}"

# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("🐶 Spike Híbrido - Chat + Visão PT-BR")
st.caption("Análise SMC/ICT • Tradução Forçada • Contexto Completo do Pipeline • 🔥 Rotação de Chaves")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Configurações")
    
    st.markdown("""
    <div class="sidebar-info">
        <div class="label">Status</div>
        <div class="value">🟢 Online - PT-BR Forçado</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 Dados do Pipeline")
    
    dados_pipeline = carregar_dados_pipeline()
    if dados_pipeline:
        st.success("✅ Dados carregados")
        if dados_pipeline.get("win_vies"):
            st.caption(f"WIN: {dados_pipeline['win_vies']} (score: {dados_pipeline.get('win_score', 0):.2f})")
        if dados_pipeline.get("preco_win"):
            st.caption(f"WIN Preço: {dados_pipeline['preco_win']:,.0f}")
        if dados_pipeline.get("vix"):
            st.caption(f"VIX: {dados_pipeline['vix']:.2f} ({dados_pipeline.get('vix_var', 0):+.2f}%)")
    else:
        st.warning("⚠️ Nenhum dado do pipeline disponível")
        st.info("💡 Execute `rodar_pipeline_3x.bat` para gerar dados")
    
    st.divider()
    
    # Status das chaves
    st.subheader("🔑 Status das Chaves")
    status = key_manager.get_status()
    if status:
        for nome, info in status.items():
            status_text = "🟢" if info["ativa"] else "🔴"
            if info["rate_limit_ate"]:
                status_text = "⏳"
            st.caption(f"{status_text} {nome}: {info['total_tokens']:,} tokens")
    else:
        st.warning("⚠️ Nenhuma chave configurada")
    
    st.divider()
    
    st.markdown("""
    <div class="aviso-pt">
        🇧🇷 <b>PORTUGUÊS OBRIGATÓRIO</b><br>
        Esta versão força a IA a responder 100% em português do Brasil.
    </div>
    """, unsafe_allow_html=True)
    
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
    <span class="titulo">🧠 Spike Híbrido - PT-BR Forçado</span>
    <span class="badge">🇧🇷 Português Obrigatório</span>
</div>
""", unsafe_allow_html=True)

messages_container = st.container()

with messages_container:
    if not st.session_state.messages:
        st.markdown("""
        <div class="chat-bubble ai ai-report">
            <h3>🇧🇷 Análise de Gráficos em Português</h3>
            <p>Envie um print do seu gráfico (clique em Anexar ou cole com <strong>Ctrl + V</strong>) para obter uma leitura completa com conceitos <strong>SMC/ICT</strong>.</p>
            <p style="color: #8b949e; font-size: 0.9rem;">
                📊 A IA tem acesso a <strong>TODOS os dados do pipeline</strong> e <strong>FORÇA</strong> a resposta em português.
            </p>
            <div style="margin-top:8px;">
                <span class="smc-tag">🇧🇷 PT-BR</span>
                <span class="smc-tag">📊 Pipeline Completo</span>
                <span class="smc-tag">🧠 SMC/ICT</span>
                <span class="smc-tag">🛡️ Tradução Forçada</span>
                <span class="smc-tag">🔥 Rotação de Chaves</span>
            </div>
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
                conteudo_limpo = re.sub(r'<think>.*?</think>', '', conteudo, flags=re.DOTALL)
                conteudo_limpo = re.sub(r'<thought>.*?</thought>', '', conteudo_limpo, flags=re.DOTALL)
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
        key="image_uploader_hibrido"
    )

with col2:
    prompt_input = st.text_input(
        "Digite sua mensagem em português...",
        placeholder="Digite sua pergunta em português ou cole uma imagem com Ctrl+V...",
        label_visibility="collapsed",
        key="chat_input_hibrido"
    )

with col3:
    enviar = st.button("📤 Enviar", width="stretch", type="primary")

# ============================================================
# PROCESSAMENTO
# ============================================================

if enviar and prompt_input:
    st.session_state.messages.append({"role": "user", "content": prompt_input})
    
    dados_pipeline = carregar_dados_pipeline()
    
    if uploaded_file:
        with st.spinner("🧠 Analisando gráfico com SMC/ICT + dados do pipeline (PT-BR FORÇADO)..."):
            try:
                uploaded_file.seek(0)
                img = Image.open(uploaded_file)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if max(img.size) > 1200:
                    img.thumbnail((1200, 1200))
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=80)
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                resposta = analisar_grafico_hibrido(
                    imagem_base64=b64,
                    pergunta_trader=prompt_input,
                    dados_pipeline=dados_pipeline
                )
                st.session_state.messages.append({"role": "assistant", "content": resposta})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Erro: {e}"})
        st.rerun()
    else:
        with st.spinner("🧠 Pensando em português..."):
            try:
                # 🔥 USA ROTAÇÃO DE CHAVES PARA TEXTO TAMBÉM
                client, key_utilizada = get_groq_client()
                system_prompt = construir_prompt_ultra_restritivo()
                contexto = montar_contexto_pipeline(dados_pipeline)
                
                user_msg = f"""
{contexto}

---

**PERGUNTA DO TRADER:**
{prompt_input}

---

⚠️ Responda 100% em PORTUGUÊS do Brasil.
"""
                
                response = client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.2,
                    max_tokens=1500,
                )
                
                if hasattr(response, 'usage'):
                    tokens = response.usage.total_tokens
                    key_manager.registrar_uso(key_utilizada, tokens)
                    print(f"📊 Tokens usados (texto): {tokens}")
                
                resposta_bruta = response.choices[0].message.content
                resposta_final = garantir_portugues(resposta_bruta)
                st.session_state.messages.append({"role": "assistant", "content": resposta_final})
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
            with st.spinner("🧠 Analisando..."):
                try:
                    uploaded_file.seek(0)
                    img = Image.open(uploaded_file)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    if max(img.size) > 1200:
                        img.thumbnail((1200, 1200))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=80)
                    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico_hibrido(
                        imagem_base64=b64,
                        pergunta_trader="Análise SMC/ICT completa do gráfico, considerando todos os dados do pipeline.",
                        dados_pipeline=dados_pipeline
                    )
                    st.session_state.messages.append({"role": "user", "content": "📊 Análise SMC Completa"})
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    with col2:
        if st.button("🎯 Entrada e Saída", width="stretch"):
            with st.spinner("🧠 Analisando..."):
                try:
                    uploaded_file.seek(0)
                    img = Image.open(uploaded_file)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    if max(img.size) > 1200:
                        img.thumbnail((1200, 1200))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=80)
                    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico_hibrido(
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
            with st.spinner("🧠 Identificando níveis..."):
                try:
                    uploaded_file.seek(0)
                    img = Image.open(uploaded_file)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    if max(img.size) > 1200:
                        img.thumbnail((1200, 1200))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=80)
                    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico_hibrido(
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
                    uploaded_file.seek(0)
                    img = Image.open(uploaded_file)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    if max(img.size) > 1200:
                        img.thumbnail((1200, 1200))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=80)
                    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    
                    dados_pipeline = carregar_dados_pipeline()
                    resposta = analisar_grafico_hibrido(
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
st.caption("🐶 Spike Híbrido - Analisador de Gráficos com IA • PT-BR Forçado • v4.1 • Com rotação de chaves")