# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Spike_Texto.py
Versão: 2.3 - Spike Desk com Mapeamento de Ativos e Leitura do Preço Teórico OCR
"""

import os
import time
import streamlit as st
import json
import requests
from pathlib import Path
from config import COLETAS_DIR
from utils.KeyManager import key_manager

st.set_page_config(page_title="Quant Terminal - Spike Desk", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🐶 IA Spike Desk — Seu Operador de Mesa Virtual</h2>", unsafe_allow_html=True)
st.caption("Converse com o Spike. Ele avalia as 4 estratégias, lê o OCR e te diz o melhor setup.")

# --- VERIFICAÇÃO DE SEGURANÇA ---
status_chaves = key_manager.verificar_presenca_credenciais()
if not status_chaves.get("GROQ_API_KEY"):
    st.error("⚠️ Chave `GROQ_API_KEY` não encontrada no `.env`.")
    st.stop()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==============================================================================
# COMPILADOR DE DADOS (Otimizado)
# ==============================================================================
def compilar_contexto() -> str:
    """Lê os JSONs, o OCR e transforma em texto compacto para a IA."""
    contexto = []
    
    # 0. CANDLES RECENTES DO MT5
    contexto.append("### ÚLTIMOS 10 CANDLES M5 (MT5) - Horário BRT")
    try:
        from cache_candles import obter_candles
        candles, _ = obter_candles("WIN$", 5, 10)
        for c in candles:
            hora = c['time'][11:16]
            contexto.append(f"{hora} | O:{c['open']:.0f} H:{c['high']:.0f} L:{c['low']:.0f} C:{c['close']:.0f} V:{c['volume']}")
    except Exception as e:
        contexto.append(f"Erro ao ler candles: {e}")
    contexto.append("")

    # 1. PREÇO TEÓRICO OCR (LEILÃO)
    csv_ocr = COLETAS_DIR / "preco_teorico_win_fluxo.csv"
    if csv_ocr.exists():
        contexto.append("### PREÇO TEÓRICO DO LEILÃO (OCR)")
        try:
            with open(csv_ocr, "r", encoding="utf-8-sig") as f:
                linhas = f.readlines()
                if linhas:
                    ultima = linhas[-1].strip().split(",")
                    if len(ultima) >= 2:
                        dt_ocr = ultima[0]
                        preco_ocr = float(ultima[1])
                        contexto.append(f"Última leitura OCR: {preco_ocr:,.0f} pts (às {dt_ocr})")
                    else:
                        contexto.append("CSV do OCR encontrado, mas sem dados válidos na última linha.")
                else:
                    contexto.append("CSV do OCR encontrado, mas está vazio.")
        except Exception as e:
            contexto.append(f"Erro ao ler o CSV do OCR: {e}")
    else:
        contexto.append("### PREÇO TEÓRICO DO LEILÃO (OCR)\n(Ainda sem leituras de OCR registradas)")
    contexto.append("")

    # 2. NOTÍCIAS
    noticias_0900 = {}
    path_0900 = COLETAS_DIR / "Noticias_Calendario_0900.json"
    if path_0900.exists():
        with open(path_0900, "r", encoding="utf-8") as f: noticias_0900 = json.load(f)

    contexto.append("### NOTÍCIAS E CALENDÁRIO")
    alerta = noticias_0900.get("alerta_noticia_0900", {})
    if alerta.get("tem_evento_3_estrelas"):
        eventos = ", ".join([e.get("evento", "?") for e in alerta.get("eventos", [])])
        contexto.append(f"🚨 ALERTA 3 ESTRELAS às 09:00: {eventos}")
    else:
        contexto.append("✅ Sem notícias críticas (3 estrelas) para as 09:00.")
    contexto.append("")

    # 3. MÉTRICAS E GAP
    metricas = {}
    path_metricas = COLETAS_DIR / "Metricas_Calculadas.json"
    if path_metricas.exists():
        with open(path_metricas, "r", encoding="utf-8") as f: metricas = json.load(f)

    ativos = {}
    path_ativos = COLETAS_DIR / "DadosAtivosUnificados.json"
    if path_ativos.exists():
        with open(path_ativos, "r", encoding="utf-8") as f:
            ativos = json.load(f).get("ativos", {})

    ind_ext = metricas.get("indicadores_compostos", {}).get("indicador_mercado_externo")
    ind_adrs = metricas.get("indicadores_compostos", {}).get("indicador_adrs_brasileiras")
    win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco")
    win_last = ativos.get("WIN_LAST_TICK", {}).get("preco") or ativos.get("WIN_FUT", {}).get("preco")
    gap = (win_last - win_ajuste) if (win_ajuste and win_last) else None

    contexto.append("### INDICADORES OPERACIONAIS")
    if ind_ext is not None: contexto.append(f"Indicador de Mercado Externo: {ind_ext:+.2f}%")
    if ind_adrs is not None: contexto.append(f"Indicador de ADRs Brasileiras: {ind_adrs:+.2f}%")
    if gap is not None: contexto.append(f"Gap do Last vs Ajuste B3: {gap:+.0f} pts")
    contexto.append("")

    # 4. COLETAS (Mapeamento Correto)
    ativos_foco = {
        "WIN": ["WIN_FUT", "B3_AJUSTE_WIN", "B3_FECHAMENTO_WIN", "BMFBOVESPA:WIN1!"],
        "WDO": ["WDO_FUT", "B3_AJUSTE_WDO", "B3_FECHAMENTO_WDO", "BMFBOVESPA:WDO1!"],
        "S&P500": ["SP500_FUT", "CME_MINI:ES1!"],
        "NASDAQ": ["NASDAQ_FUT", "CME_MINI:NQ1!"],
        "VIX": ["VIX", "TVC:VIX"],
        "DXY": ["DXY", "TVC:DXY"],
        "EWZ": ["EWZ", "AMEX:EWZ"],
        "MINERIO": ["IRON_ORE", "SGX:FEF1!"],
        "PETROLEO": ["CRUDE_OIL", "NYMEX:CL1!"],
        "DI1 2027": ["DI1_2027", "BMFBOVESPA:DI1F2027"],
        "DI1 2029": ["DI1_2029", "BMFBOVESPA:DI1F2029"],
    }
    
    janelas = [0, 5, 10, 15, 30, 55]
    coletas = {tf: {} for tf in janelas}
    
    for tf in janelas:
        caminho = COLETAS_DIR / f"Coleta_rom-{tf}.json"
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                for item in json.load(f).get("coletas", []):
                    ativo_json = item.get("ativo")
                    var = (item.get("dados_reais") or {}).get("change_percent")
                    if var is None: continue
                    
                    for nome_foco, chaves in ativos_foco.items():
                        if ativo_json in chaves:
                            coletas[tf][nome_foco] = var
                            break
    
    contexto.append("### DADOS DE MERCADO (Ativos Principais)")
    contexto.append("Ativo | Agora | 5m | 10m | 15m | 30m | 55m")
    for nome_foco in ativos_foco.keys():
        if nome_foco in coletas[0]:
            linha = [nome_foco] + [f"{coletas[tf].get(nome_foco, 0):+.2f}%" for tf in janelas]
            contexto.append(" | ".join(linha))
    
    # 5. SMC
    contexto.append("\n### ANÁLISE SMC (Motor Python)")
    for tf_nome, arquivo in [("M15 (Macro)", "AnaliseGraficaSMC_Regras_M15.json"), ("M5 (Médio)", "AnaliseGraficaSMC_Regras.json")]:
        caminho = COLETAS_DIR / arquivo
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f: smc = json.load(f)
            contexto.append(f"\n--- SMC {tf_nome} ---")
            contexto.append(f"Viés: {smc.get('bias_direcional')} (Conf: {smc.get('confianca_visual')}%) | Preço Atual: {smc.get('preco_atual')}")
            obs = smc.get("order_blocks", [])
            if obs: contexto.append(f"OBs: {', '.join([f'{o['tipo']} em {o['abertura']}' for o in obs[:3]])}")
            fvgs = smc.get("fair_value_gaps", [])
            if fvgs: contexto.append(f"FVGs: {', '.join([f'{f['tipo']} ({f['inferior']}-{f['superior']})' for f in fvgs[:3]])}")
            ni = smc.get("niveis_institucionais", {})
            contexto.append(f"POC Ontem: {ni.get('poc_ontem')} | VWAP Ontem: {ni.get('vwap_ontem')}")
            liq = smc.get("liquidez", {})
            contexto.append(f"BSL (Topos): {liq.get('bsl', [])} | SSL (Fundos): {liq.get('ssl', [])}")

    return "\n".join(contexto)

# ==============================================================================
# INTERFACE DE CHAT
# ==============================================================================
st.markdown("### 💬 Mesa de Operações")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Fala, trader! Sou o Spike. Já cruzei seus dados, as notícias e o OCR do leilão. Quer que eu avalie qual dos 4 Operacionais está dando o melhor gatilho agora?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ex: Qual o melhor setup agora? Qual o preço do leilão no OCR?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Spike está avaliando os 4 operacionais..."):
            try:
                dados_contexto = compilar_contexto()
                
                system_prompt = f"""
                Você é o "Spike", um operador profissional de day trade da B3.
                Seu trabalho é avaliar os 4 Operacionais Oficiais do usuário e dizer qual deles tem o setup mais robusto no momento.

                OS 4 OPERACIONAIS DO USUÁRIO:
                1. **Operacional 1 (Ajuste):** Gap positivo → VENDER no ajuste. Gap negativo → COMPRAR no ajuste.
                2. **Operacional 2 (Drivers de Abertura):** Se houver notícia 3★, priorize ADRs. Se não, priorize Mercado Externo. Positivo = Compra. Negativo = Venda.
                3. **Operacional 3 (Rompimento 10h):** Entrada no rompimento da vela de 10:00. Alvo = Tamanho do candle. Stop = Extremidade oposta.
                4. **Operacional 4 (SMC Puro):** Entrada em OBs, FVGs ou Liquidez.

                SUA MISSÃO NA RESPOSTA:
                1. Ser direto e falar como um trader de mesa.
                2. **Análise Macro:** Comente sobre os ativos da tabela.
                3. **Análise de Leilão/OCR:** Se houver um "Preço Teórico do Leilão (OCR)" nos dados, compare-o com o Ajuste B3 para o Operacional 1 e com os OBs para o Operacional 4.
                4. **Avaliação dos 4 Operacionais:** Diga o status de CADA UM dos 4.
                5. **Veredito Master:** Diga qual dos 4 é a melhor oportunidade agora e justifique.
                6. **Regra de Ouro:** Se os dados não estiverem na tabela, NÃO INVENTE. Diga apenas que não recebeu esse dado.

                DADOS DO SISTEMA:
                {dados_contexto}
                """

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                
                payload = {
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048
                }

                max_retries = 3
                for tentativa in range(max_retries):
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    if response.status_code == 200: break
                    elif response.status_code == 429:
                        st.warning(f"⚠️ Limite da Groq atingido. Aguardando 3s (Tentativa {tentativa+1}/{max_retries})...")
                        time.sleep(3)
                    else: break
                
                if response.status_code == 200:
                    dados_api = response.json()
                    resposta_ia = dados_api['choices'][0]['message']['content']
                    st.markdown(resposta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_ia})
                else:
                    st.error(f"❌ Erro na Groq: {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"❌ Erro ao processar: {e}")

# --- PAINEL DE DEBUG ---
with st.sidebar:
    st.markdown("### 🔍 O que o Spike está lendo")
    with st.expander("Ver Dados Enviados para a IA"):
        st.text(compilar_contexto())