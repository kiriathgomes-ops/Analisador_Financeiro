# -*- coding: utf-8 -*-
"""
Módulo: pages/7.2.1_🐶_IA_SpikeImagem_Expert.py
Versão: 5.2 (Expert) - Validação Matemática de R:R no Python e Foco SMC
Objetivo: Análise visual cirúrgica com bloqueio de trades de assimetria ruim.
"""

import os
import streamlit as st
import json
import re
import base64
import io
import requests
from datetime import datetime, timezone, timedelta
from PIL import Image

from utils.KeyManager import key_manager
from Limpar_Imagens_TradingView import limpar_e_processar_imagens
from config import COLETAS_DIR

IMG_15M = COLETAS_DIR / "WIN_15min.png"
IMG_5M = COLETAS_DIR / "WIN_5min.png"
ARQUIVO_IA = COLETAS_DIR / "AnaliseSpike_IA_Expert.json"
BRT = timezone(timedelta(hours=-3))

st.set_page_config(page_title="Quant Terminal - IA Spike Vision Expert", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🐶 IA Spike Vision Expert — Análise SMC Master</h2>", unsafe_allow_html=True)
st.caption("Foco 100% em SMC + Validação de Risco (R:R >= 1:2) feita pelo Python.")

status_chaves = key_manager.verificar_presenca_credenciais()
if not status_chaves.get("GROQ_API_KEY"):
    st.error("⚠️ Chave `GROQ_API_KEY` não encontrada no arquivo `.env`.")
    st.stop()

chave_mascarada = key_manager.obter_chave_mascarada("GROQ_API_KEY")
st.success(f"🔒 **Conexão Segura (KeyManager):** Groq API {chave_mascarada}")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def preparar_imagem(caminho_img):
    img = Image.open(caminho_img)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.thumbnail((1920, 1920)) 
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=100)
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"

def render_card(titulo, texto, cor_borda):
    st.markdown(f"#### {titulo}")
    texto_formatado = str(texto).replace("\n", "<br>")
    st.markdown(
        f"<div style='background-color: #161b24; padding: 20px; border-radius: 8px; "
        f"border-left: 5px solid {cor_borda}; color: #e6edf3; "
        f"line-height: 1.6; font-size: 1.05rem; font-family: sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.3); "
        f"white-space: pre-wrap; margin-bottom: 20px;'>"
        f"{texto_formatado}"
        f"</div>",
        unsafe_allow_html=True
    )

if st.button("🚀 Acordar o Spike Expert (SMC Master)", type="primary", use_container_width=True):
    
    with st.spinner("🧹 Buscando os prints mais recentes na sua pasta Downloads..."):
        limpar_e_processar_imagens()
    
    if not (IMG_15M.exists() and IMG_5M.exists()):
        st.error("❌ O Spike não encontrou as imagens. Tire os prints do TradingView.")
        st.stop()

    with st.spinner("🐶 Spike Expert mapeando a estrutura do mercado... (aguarde ~10s)"):
        try:
            img15_b64 = preparar_imagem(IMG_15M)
            img5_b64 = preparar_imagem(IMG_5M)

            # ✅ PROMPT SMC FOCADO
            prompt = """
            Você é o "Spike Expert", um Trader Institucional Sênior especialista absoluto em SMC (Smart Money Concepts) e Price Action.
            Analise as duas imagens (M15 Macro e M5 Médio) do WINFUT.

            ⚠️ DIRETRIZES CRÍTICAS (ANTI-ALUCINAÇÃO):
            1. LEITURA DE ESCALA: Use o Eixo Y para ancorar os preços. Não invente valores.
            2. FOCO EM SMC: Ignore cunhas, bandeiras ou triângulos geométricos complexos. Foque em: Estrutura de Mercado (BOS/CHOCH), Order Blocks (OBs), Fair Value Gaps (FVGs) e Liquidez (BSL/SSL).
            3. PRICE ACTION BÁSICO: Identifique rejeições fortes (pavios longos), candles de engolfo (marubozu) ou exaustão de movimento.
            4. RANGES: O preço está consolidando? Onde estão o topo e o fundo do range?
            5. REGRAS DE OURO: Se for ALTA, entrada em demanda. Se for BAIXA, em oferta. O R:R MÍNIMO é 1:2.

            Seu raciocínio deve preencher os seguintes campos:
            - "analise_estrutura": Descreva a tendência (M15 e M5), se houve BOS ou CHOCH recente.
            - "analise_liquidez": Onde estão as liquidezes (topos/fundos iguais) e qual o alvo provável?
            - "analise_zonas": Descreva os Order Blocks e FVGs mais relevantes que você encontrou.

            Depois do raciocínio, preencha o JSON com os níveis para o Profit:
            {
                "analise_estrutura": "Texto detalhado sobre BOS, CHOCH e a tendência macro/micro...",
                "analise_liquidez": "Texto sobre onde a liquidez está acumulada (BSL/SSL)...",
                "analise_zonas": "Texto sobre as zonas de OB e FVG...",
                "bias_macro": "ALTA" | "BAIXA" | "LATERAL",
                "bias_medio": "ALTA" | "BAIXA" | "LATERAL",
                "niveis_ob": [
                    {"tipo": "COMPRA", "preco": 177000, "texto": "OB Compra M15"},
                    {"tipo": "VENDA", "preco": 178200, "texto": "OB Venda M5"}
                ],
                "niveis_fvg": [
                    {"tipo": "COMPRA", "preco": 177600, "texto": "FVG Compra M5"}
                ],
                "bsl": [178500],
                "ssl": [176000],
                "plano_de_trade": {
                    "cenario_principal": "Texto curto explicando a entrada.",
                    "entrada": 177550,
                    "stop": 177400,
                    "alvo": 178200,
                    "risco_retorno": "1:3"
                }
            }
            """

            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "qwen/qwen3.8-27b", 
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": img15_b64}},
                            {"type": "image_url", "image_url": {"url": img5_b64}}
                        ]
                    }
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "max_tokens": 4000
            }

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                dados_api = response.json()
                texto_resposta = dados_api['choices'][0]['message']['content']
                texto_limpo = re.sub(r'```json|```', '', texto_resposta).strip()
                dados = json.loads(texto_limpo)

                uso_tokens = dados_api.get("usage") or {}
                prompt_tokens = uso_tokens.get("prompt_tokens", 0)
                completion_tokens = uso_tokens.get("completion_tokens", 0)
                total_tokens = uso_tokens.get("total_tokens", 0)

                # --- GERANDO CÓDIGO NTSL ---
                linhas_ntsl = []
                for ob in dados.get("niveis_ob", []):
                    cor = "clVerde" if ob["tipo"] == "COMPRA" else "clVermelho"
                    linhas_ntsl.append(f'HorizontalLineCustom({ob["preco"]}, {cor}, 2, 0, "{ob["texto"]}", 10, tpTopLeft, 0, 0, 0, 0, 0);')
                for fvg in dados.get("niveis_fvg", []):
                    linhas_ntsl.append(f'HorizontalLineCustom({fvg["preco"]}, clAmarelo, 1, 1, "{fvg["texto"]}", 10, tpTopLeft, 0, 0, 0, 0, 0);')
                for bsl in dados.get("bsl", []):
                    linhas_ntsl.append(f'HorizontalLineCustom({bsl}, clAzul, 1, 1, "BSL", 10, tpTopLeft, 0, 0, 0, 0, 0);')
                for ssl in dados.get("ssl", []):
                    linhas_ntsl.append(f'HorizontalLineCustom({ssl}, clFucsia, 1, 1, "SSL", 10, tpTopLeft, 0, 0, 0, 0, 0);')
                
                plano = dados.get("plano_de_trade") or {}
                if plano.get("entrada"):
                    linhas_ntsl.append(f'HorizontalLineCustom({plano["entrada"]}, clBranco, 2, 0, "ENTRADA", 10, tpTopLeft, 0, 0, 0, 0, 0);')
                if plano.get("stop"):
                    linhas_ntsl.append(f'HorizontalLineCustom({plano["stop"]}, clVermelho, 1, 1, "STOP", 10, tpTopLeft, 0, 0, 0, 0, 0);')
                if plano.get("alvo"):
                    linhas_ntsl.append(f'HorizontalLineCustom({plano["alvo"]}, clVerde, 1, 1, "ALVO", 10, tpTopLeft, 0, 0, 0, 0, 0);')

                script_ntsl = "Inicio\n    " + "\n    ".join(linhas_ntsl) + "\nFim;"

                payload_salvar = {
                    "timestamp": datetime.now(BRT).isoformat(),
                    "fonte": "Spike_IA_Groq_Expert_SMC",
                    "consumo_tokens": uso_tokens,
                    "dados_analise": dados,
                    "codigo_ntsl_gerado": script_ntsl
                }
                ARQUIVO_IA.parent.mkdir(exist_ok=True)
                with open(ARQUIVO_IA, "w", encoding="utf-8") as f:
                    json.dump(payload_salvar, f, indent=2, ensure_ascii=False)

                st.success(f"✅ Análise SMC Master concluída! Salvo em `{ARQUIVO_IA.name}`")
                
                st.markdown("### ⚡ Consumo de Tokens")
                c_tok1, c_tok2, c_tok3 = st.columns(3)
                c_tok1.metric("Tokens de Entrada", f"{prompt_tokens:,}")
                c_tok2.metric("Tokens de Saída", f"{completion_tokens:,}")
                c_tok3.metric("Total de Tokens", f"{total_tokens:,}")

                st.markdown("### 📸 Prints Analisados")
                c_img1, c_img2 = st.columns(2)
                c_img1.image(str(IMG_15M), caption="M15 (Macro)", use_container_width=True)
                c_img2.image(str(IMG_5M), caption="M5 (Médio)", use_container_width=True)

                st.markdown("---")
                
                cor_macro = "#00ff88" if dados["bias_macro"] == "ALTA" else "#ff6b6b" if dados["bias_macro"] == "BAIXA" else "#ffa500"
                cor_medio = "#00ff88" if dados["bias_medio"] == "ALTA" else "#ff6b6b" if dados["bias_medio"] == "BAIXA" else "#ffa500"

                c1, c2 = st.columns(2)
                c1.markdown(f"<div style='background:#161b24; padding:15px; border-radius:8px; text-align:center; border-left:5px solid {cor_macro};'><h3 style='margin:0;'>M15 (Macro): <span style='color:{cor_macro};'>{dados['bias_macro']}</span></h3></div>", unsafe_allow_html=True)
                c2.markdown(f"<div style='background:#161b24; padding:15px; border-radius:8px; text-align:center; border-left:5px solid {cor_medio};'><h3 style='margin:0;'>M5 (Médio): <span style='color:{cor_medio};'>{dados['bias_medio']}</span></h3></div>", unsafe_allow_html=True)

                st.markdown("---")
                
                # ✅ RENDERIZAÇÃO DOS CARDS SMC
                render_card("🏗️ Estrutura de Mercado (BOS / CHOCH)", dados.get("analise_estrutura", "Não disponível."), "#00d4ff")
                
                col_liq, col_zonas = st.columns(2)
                with col_liq:
                    render_card("💧 Mapa de Liquidez (BSL / SSL)", dados.get("analise_liquidez", "Não disponível."), "#3b82f6")
                with col_zonas:
                    render_card("📦 Zonas SMC (OBs / FVGs)", dados.get("analise_zonas", "Não disponível."), "#a855f7")

                # 🎯 PLANO DE TRADE TÁTICO COM VALIDAÇÃO MATEMÁTICA
                st.markdown("### 🎯 Plano de Trade Tático")
                if plano:
                    entrada = float(plano.get('entrada') or 0)
                    stop = float(plano.get('stop') or 0)
                    alvo = float(plano.get('alvo') or 0)
                    
                    # ✅ O PYTHON CALCULA O R:R REAL
                    rr_valido = False
                    rr_real = 0.0
                    if entrada > 0 and stop > 0 and alvo > 0:
                        risco = abs(entrada - stop)
                        retorno = abs(alvo - entrada)
                        if risco > 0:
                            rr_real = retorno / risco
                            rr_valido = (rr_real >= 2.0)
                    
                    cor_cenario = "#ffa500" if rr_valido else "#ef4444"
                    emoji_alerta = "✅" if rr_valido else "🚨"
                    texto_alerta = "R:R APROVADO (>= 1:2)" if rr_valido else "CUIDADO: R:R ABAIXO DO MÍNIMO (1:2) - NÃO OPERAR"
                    
                    st.markdown(
                        f"<div style='background-color: #161b24; padding: 15px; border-radius: 8px; "
                        f"border-left: 5px solid {cor_cenario}; color: #e6edf3; margin-bottom: 15px; "
                        f"white-space: pre-wrap;'>"
                        f"<b>Cenário Principal:</b> {plano.get('cenario_principal', '—')}<br><br>"
                        f"<b>{emoji_alerta} Validação de Risco:</b> {texto_alerta}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("Entrada", f"{entrada:,.0f}" if entrada else "—")
                    p2.metric("Stop Loss", f"{stop:,.0f}" if stop else "—", delta_color="inverse")
                    p3.metric("Alvo", f"{alvo:,.0f}" if alvo else "—")
                    p4.metric("R:R Calculado", f"1:{rr_real:.1f}", help=f"A IA havia sugerido {plano.get('risco_retorno', '—')}")
                else:
                    st.warning("Spike Expert achou melhor não sugerir um trade neste momento.")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📥 Código NTSL (Pronto para o Profit)")
                st.code(script_ntsl, language="pascal")

            else:
                st.error(f"❌ Erro na API da Groq: {response.status_code}")
                st.text(response.text)

        except requests.exceptions.Timeout:
            st.error("❌ O Spike Expert demorou muito para responder. Tente novamente.")
        except Exception as e:
            st.error(f"❌ O Spike Expert se distraiu: {e}")