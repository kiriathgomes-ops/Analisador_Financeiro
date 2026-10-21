# -*- coding: utf-8 -*-
"""
Módulo: pages/7.2_🤖_IA_SpikeImagem.py
Versão: 3.5 - Vision AI (Spike) Autônomo: Limpa imagens, analisa e salva JSON com UI refinada
Objetivo: Usar Groq Vision para ler gráficos M5 e M15, gerar relatório SMC e código Profit.
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

# Importa o gerenciador de chaves e o limpador de imagens
from utils.KeyManager import key_manager
from Limpar_Imagens_TradingView import limpar_e_processar_imagens
from config import COLETAS_DIR

# Caminhos
IMG_15M = COLETAS_DIR / "WIN_15min.png"
IMG_5M = COLETAS_DIR / "WIN_5min.png"
ARQUIVO_IA = COLETAS_DIR / "AnaliseSpike_IA.json"
BRT = timezone(timedelta(hours=-3))

st.set_page_config(page_title="Quant Terminal - IA Spike Vision", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🐶 IA Spike Vision — Análise SMC por Imagem</h2>", unsafe_allow_html=True)
st.caption("O Spike busca os prints novos na pasta Downloads, lê os gráficos e cospe o código NTSL.")

# --- VERIFICAÇÃO DE SEGURANÇA ---
status_chaves = key_manager.verificar_presenca_credenciais()
if not status_chaves.get("GROQ_API_KEY"):
    st.error("⚠️ Chave `GROQ_API_KEY` não encontrada no arquivo `.env`. O Spike não pode caçar sem a coleira.")
    st.stop()

chave_mascarada = key_manager.obter_chave_mascarada("GROQ_API_KEY")
st.success(f"🔒 **Conexão Segura (KeyManager):** Groq API {chave_mascarada}")

# Recupera a string pura para usar no requests
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def preparar_imagem(caminho_img):
    img = Image.open(caminho_img)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    img.thumbnail((1000, 1000)) 
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"

# --- EXECUÇÃO DA ANÁLISE ---
if st.button("🚀 Acordar o Spike (Limpar + Analisar + Salvar)", type="primary", use_container_width=True):
    
    with st.spinner("🧹 Buscando os prints mais recentes na sua pasta Downloads..."):
        limpar_e_processar_imagens()
    
    if not (IMG_15M.exists() and IMG_5M.exists()):
        st.error("❌ O Spike não encontrou as imagens. Verifique se você tirou os prints do TradingView.")
        st.stop()

    with st.spinner("🐶 Spike está farejando os gráficos... (aguarde ~3 segundos)"):
        try:
            img15_b64 = preparar_imagem(IMG_15M)
            img5_b64 = preparar_imagem(IMG_5M)

            prompt = """
            Você é o "Spike", um trader especialista em Smart Money Concepts (SMC) e ICT.
            Analise as duas imagens: a primeira é o gráfico de 15 minutos (Macro) e a segunda é de 5 minutos (Médio) do WINFUT.

            Sua missão:
            1. Identificar o Viés Macro (M15) e Médio (M5).
            2. Encontrar Order Blocks (OB) e Fair Value Gaps (FVG) que estão abertos.
            3. Identificar Liquidez (BSL / SSL).
            4. Escrever um relatório rápido (máximo 3 parágrafos).
            5. Extrair os PREÇOS EXATOS.

            IMPORTANTE: Responda APENAS um JSON válido, no seguinte formato:
            {
                "bias_macro": "ALTA" | "BAIXA" | "LATERAL",
                "bias_medio": "ALTA" | "BAIXA" | "LATERAL",
                "relatorio": "Seu texto aqui...",
                "niveis_ob": [
                    {"tipo": "COMPRA", "preco": 210500, "texto": "OB C-15"},
                    {"tipo": "VENDA", "preco": 212000, "texto": "OB V-5"}
                ],
                "niveis_fvg": [
                    {"tipo": "COMPRA", "preco": 210200, "texto": "FVG C-5"}
                ],
                "bsl": [213000],
                "ssl": [208000]
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
                "response_format": {"type": "json_object"}
            }

            response = requests.post(url, headers=headers, json=payload, timeout=25)
            
            if response.status_code == 200:
                dados_api = response.json()
                texto_resposta = dados_api['choices'][0]['message']['content']
                texto_limpo = re.sub(r'```json|```', '', texto_resposta).strip()
                dados = json.loads(texto_limpo)

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

                script_ntsl = "Inicio\n    " + "\n    ".join(linhas_ntsl) + "\nFim;"

                # --- SALVANDO O JSON ---
                payload_salvar = {
                    "timestamp": datetime.now(BRT).isoformat(),
                    "fonte": "Spike_IA_Groq",
                    "dados_analise": dados,
                    "codigo_ntsl_gerado": script_ntsl
                }
                ARQUIVO_IA.parent.mkdir(exist_ok=True)
                with open(ARQUIVO_IA, "w", encoding="utf-8") as f:
                    json.dump(payload_salvar, f, indent=2, ensure_ascii=False)

                # --- RENDERIZANDO RESULTADOS NA TELA ---
                st.success(f"✅ Spike terminou a análise! Relatório salvo em `{ARQUIVO_IA.name}`")
                
                st.markdown("### 📸 Prints Analisados")
                c_img1, c_img2 = st.columns(2)
                c_img1.image(str(IMG_15M), caption="M15 (Macro)", use_container_width=True)
                c_img2.image(str(IMG_5M), caption="M5 (Médio)", use_container_width=True)

                st.markdown("---")
                
                # Cores baseadas no viés
                cor_macro = "#00ff88" if dados["bias_macro"] == "ALTA" else "#ff6b6b" if dados["bias_macro"] == "BAIXA" else "#ffa500"
                cor_medio = "#00ff88" if dados["bias_medio"] == "ALTA" else "#ff6b6b" if dados["bias_medio"] == "BAIXA" else "#ffa500"
                
                # Bordas para o relatório (pega a cor do M15 como base)
                borda_relatorio = cor_macro

                c1, c2 = st.columns(2)
                c1.markdown(f"<div style='background:#161b24; padding:15px; border-radius:8px; text-align:center; border-left:5px solid {cor_macro};'><h3 style='margin:0;'>M15 (Macro): <span style='color:{cor_macro};'>{dados['bias_macro']}</span></h3></div>", unsafe_allow_html=True)
                c2.markdown(f"<div style='background:#161b24; padding:15px; border-radius:8px; text-align:center; border-left:5px solid {cor_medio};'><h3 style='margin:0;'>M5 (Médio): <span style='color:{cor_medio};'>{dados['bias_medio']}</span></h3></div>", unsafe_allow_html=True)

                # 🔥 CARD CUSTOMIZADO DO RELATÓRIO (Substituindo o st.info)
                st.markdown("### 📝 Relatório do Spike")
                st.markdown(
                    f"<div style='background-color: #161b24; padding: 20px; border-radius: 8px; "
                    f"border-left: 5px solid {borda_relatorio}; color: #e6edf3; "
                    f"line-height: 1.6; font-size: 1.05rem; font-family: sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>"
                    f"{dados['relatorio']}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📥 Código NTSL (Pronto para o Profit)")
                st.code(script_ntsl, language="pascal")
                st.caption("💡 Copie o código acima e cole no seu indicador no Profit Pro.")

            else:
                st.error(f"❌ Erro na API da Groq: {response.status_code}")
                st.text(response.text)

        except requests.exceptions.Timeout:
            st.error("❌ O Spike demorou muito para responder. Tente novamente.")
        except Exception as e:
            st.error(f"❌ O Spike se distraiu com um esquilo e deu erro: {e}")