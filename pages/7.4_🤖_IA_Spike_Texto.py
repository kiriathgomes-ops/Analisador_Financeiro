# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Spike_Texto.py
Versão: 2.7.3 — Fix do max_tokens no Modo Direto (evita resposta vazia)
Objetivo: Chat interativo que adapta a resposta ao tipo de pergunta, sem estourar a cota.
"""

import os
import time
import streamlit as st
import json
import requests
from pathlib import Path
from datetime import datetime as _dt
from config import COLETAS_DIR
from utils.KeyManager import key_manager

st.set_page_config(page_title="Quant Terminal - Spike Desk", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🐶 IA Spike Desk — Seu Operador de Mesa Virtual</h2>", unsafe_allow_html=True)
st.caption("Converse com o Spike. Ele avalia as 4 estratégias, lê o OCR e te diz o melhor setup.")

status_chaves = key_manager.verificar_presenca_credenciais()
if not status_chaves.get("GROQ_API_KEY"):
    st.error("⚠️ Chave `GROQ_API_KEY` não encontrada no `.env`.")
    st.stop()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ==============================================================================
# COMPILADOR DE DADOS — v2.7.3 (OTIMIZADO)
# ==============================================================================
_CACHE_VERSION_CTX = "v2.7.3"


@st.cache_data(ttl=30)
def compilar_contexto(_ver: str = _CACHE_VERSION_CTX) -> str:
    contexto = []

    # 0. CANDLES (Reduzido para 5)
    contexto.append("### ÚLTIMOS 5 CANDLES M5 (MT5) - Horário BRT")
    try:
        from cache_candles import obter_candles
        candles, _ = obter_candles("WIN$", 5, 5)
        for c in candles:
            hora = c['time'][11:16]
            contexto.append(f"{hora} | O:{c['open']:.0f} H:{c['high']:.0f} L:{c['low']:.0f} C:{c['close']:.0f}")
    except Exception as e:
        contexto.append(f"Erro ao ler candles: {e}")
    contexto.append("")

    # 1. OCR (Resumido)
    csv_ocr = COLETAS_DIR / "preco_teorico_win_fluxo.csv"
    if csv_ocr.exists():
        try:
            with open(csv_ocr, "r", encoding="utf-8-sig") as f:
                linhas = f.readlines()
            if linhas:
                ultima = linhas[-1].strip().split(",")
                if len(ultima) >= 2:
                    dt_ocr = ultima[0].strip()
                    preco_ocr = float(ultima[1])
                    contexto.append(f"### OCR: {preco_ocr:,.0f} pts (às {dt_ocr})")
                    dt_parsed = None
                    formatos = ("%Y-%m-%d %H:%M:%S.%f", "%d/%m/%Y %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%H:%M:%S", "%H:%M")
                    for fmt in formatos:
                        try:
                            dt_parsed = _dt.strptime(dt_ocr, fmt)
                            break
                        except ValueError: continue
                    if dt_parsed:
                        if ":" in dt_ocr and "-" not in dt_ocr and "/" not in dt_ocr:
                            hoje = _dt.now()
                            dt_parsed = dt_parsed.replace(year=hoje.year, month=hoje.month, day=hoje.day)
                        idade_min = (_dt.now() - dt_parsed).total_seconds() / 60.0
                        if idade_min > 30:
                            contexto.append(f"⚠️ OCR velho ({idade_min:.0f} min)")
                        else:
                            contexto.append(f"✅ OCR recente ({idade_min:.0f} min)")
        except Exception: pass
    contexto.append("")

    # 2. NOTÍCIAS E INDICADORES (Unificados)
    contexto.append("### CONTEXTO MACRO")
    metricas = {}
    if (COLETAS_DIR / "Metricas_Calculadas.json").exists():
        with open(COLETAS_DIR / "Metricas_Calculadas.json", "r", encoding="utf-8") as f:
            metricas = json.load(f)
    ind_comp = metricas.get("indicadores_compostos", {}) or {}
    if ind_comp.get("indicador_mercado_externo") is not None:
        contexto.append(f"Merc. Externo: {ind_comp['indicador_mercado_externo']:+.2f}%")
    if ind_comp.get("indicador_adrs_brasileiras") is not None:
        contexto.append(f"ADRs (Soma): {ind_comp['indicador_adrs_brasileiras']:+.2f}")

    ativos = {}
    if (COLETAS_DIR / "DadosAtivosUnificados.json").exists():
        with open(COLETAS_DIR / "DadosAtivosUnificados.json", "r", encoding="utf-8") as f:
            ativos = json.load(f).get("ativos", {})
    win_ajuste = (ativos.get("WIN_AJUSTE", {}) or {}).get("preco")
    win_last = ((ativos.get("WIN_LAST_TICK", {}) or {}).get("preco") or (ativos.get("WIN_FUT", {}) or {}).get("preco"))
    if win_ajuste and win_last:
        gap = win_last - win_ajuste
        contexto.append(f"Gap vs Ajuste: {gap:+.0f} pts")

    if (COLETAS_DIR / "Noticias_Impacto_Dia.json").exists():
        with open(COLETAS_DIR / "Noticias_Impacto_Dia.json", "r", encoding="utf-8") as f:
            impacto = json.load(f)
        resumo = impacto.get("resumo", {})
        if resumo: contexto.append(f"Impacto Notícias: {resumo.get('classificacao', '?')}")
        if impacto.get("alertas", {}).get("risco_abertura_WIN"):
            contexto.append("🚨 Risco de Abertura WIN ATIVO")
    contexto.append("")

    # 3. ATIVOS (Tabela reduzida para 5 janelas)
    contexto.append("### MERCADO (5 janelas)")
    contexto.append("Ativo | ⟲ | 55m | 30m | 15m | 5m | Agora")
    ativos_foco = {
        "WIN": ["WIN_FUT", "B3_AJUSTE_WIN", "B3_FECHAMENTO_WIN"],
        "WDO": ["WDO_FUT", "B3_AJUSTE_WDO"],
        "DI1 2027": ["DI1_2027", "BMFBOVESPA:DI1F2027"],
        "VIX": ["VIX", "TVC:VIX"],
        "DXY": ["DXY", "TVC:DXY"],
        "EWZ": ["EWZ", "AMEX:EWZ"],
        "S&P500": ["SP500_FUT", "CME_MINI:ES1!"],
    }
    inversos_win = {"WDO", "DI1 2027", "VIX", "DXY"}
    janelas = [55, 30, 15, 5, 0]
    coletas = {tf: {} for tf in janelas}
    for tf in janelas:
        if (COLETAS_DIR / f"Coleta_rom-{tf}.json").exists():
            with open(COLETAS_DIR / f"Coleta_rom-{tf}.json", "r", encoding="utf-8") as f:
                for item in json.load(f).get("coletas", []):
                    var = (item.get("dados_reais") or {}).get("change_percent")
                    for nome, chaves in ativos_foco.items():
                        if item.get("ativo") in chaves and var is not None:
                            if nome not in coletas[tf]: coletas[tf][nome] = var
                            break
    
    for nome in ativos_foco.keys():
        if nome in coletas[0]:
            inv = "⟲" if nome in inversos_win else " "
            linha = [nome, inv] + [f"{coletas[tf].get(nome, 0):+.2f}%" for tf in janelas]
            contexto.append(" | ".join(linha))
    contexto.append("")

    # 4. SMC (Resumido)
    contexto.append("### SMC")
    for tf_nome, arquivo in [("M15", "AnaliseGraficaSMC_Regras_M15.json"), ("M5", "AnaliseGraficaSMC_Regras.json")]:
        if (COLETAS_DIR / arquivo).exists():
            with open(COLETAS_DIR / arquivo, "r", encoding="utf-8") as f:
                smc = json.load(f)
            stale = "🚨 STALE" if smc.get("stale") else "OK"
            contexto.append(f"SMC {tf_nome}: {smc.get('bias_direcional')} (Conf: {smc.get('confianca_visual')}%) | {stale}")
    contexto.append("")

    # 5. SNAPSHOT OP 3
    contexto.append("### SNAPSHOT OP 3")
    snapshot_path = COLETAS_DIR / "snapshot_rompimento_10h.txt"
    if snapshot_path.exists():
        texto_snap = snapshot_path.read_text(encoding="utf-8")
        if "--- BLOCO E:" in texto_snap:
            bloco_e = texto_snap.split("--- BLOCO E:")[1].split("--- BLOCO F:")[0]
            contexto.append(bloco_e[:1000].strip())
    else:
        contexto.append("Não gerado")
    contexto.append("")

    # 6. DECISÃO V2
    contexto.append("### DECISÃO V2")
    if (COLETAS_DIR / "Decisao_V2.json").exists():
        with open(COLETAS_DIR / "Decisao_V2.json", "r", encoding="utf-8") as f:
            dec = json.load(f)
        nm = dec.get("decisao", {}).get("metadados", {}).get("novo_motor", {})
        if nm:
            contexto.append(f"Novo Motor: {nm.get('direcao')} (Score {nm.get('score_magnitude')}) | Gap {nm.get('gap_pontos')} pts")

    return "\n".join(contexto)


# ==============================================================================
# INTERFACE — v2.7.3
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Fala, trader! Sou o Spike. Já cruzei seus dados e estou pronto."}]
if "modo_resposta_direta" not in st.session_state:
    st.session_state["modo_resposta_direta"] = False

st.markdown("### 💬 Mesa de Operações")
col_esq, col_dir = st.columns([4, 1])
with col_dir:
    st.toggle("⚡ Resposta direta", key="modo_resposta_direta", help="Marcado: veredito em até 3 linhas.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ex: Qual o melhor setup agora?", key="spike_chat_input"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    modo_direto = bool(st.session_state.get("modo_resposta_direta", False))
    modo_label = "direto ⚡" if modo_direto else "completo"

    with st.chat_message("assistant"):
        with st.spinner(f"Spike está avaliando [{modo_label}]..."):
            try:
                dados_contexto = compilar_contexto()

                if modo_direto:
                    bloco_modo = """
                    🛑 MODO DIRETO ATIVADO — SUA RESPOSTA DEVE SER APENAS O FORMATO ABAIXO, SEM TEXTO NARRATIVO.
                    Mesmo que o usuário peça "resuma em 3 linhas" ou "explique o cenário", você DEVE ignorar o formato de texto e responder EXATAMENTE neste padrão:

                    🎯 Veredito: [Operacional N — COMPRA / VENDA / NEUTRO / SEM DADO]
                    💡 Motivo: [1 frase, máx 20 palavras]
                    ⚠️ Alertas: [stale / OCR velho / risco / "nenhum"]

                    FIM. A resposta termina na linha "⚠️ Alertas:". Nada mais.
                    """
                else:
                    bloco_modo = """
                    MODO COMPLETO INTELIGENTE — Sua resposta deve se adaptar ao tipo de pergunta do usuário:
                    
                    1. SE A PERGUNTA FOR ESPECÍFICA (ex: "Qual o Op 3?", "Como está o SMC?", "O que diz o OCR?"):
                       - Comece a resposta respondendo DIRETAMENTE à pergunta.
                       - Depois, adicione um parágrafo curto de "Contexto Macro Relevante" APENAS se houver algo crítico (ex: gap extremo, inversos em alta, SMC stale) que impacte a resposta.
                       - NÃO liste os outros operacionais e NÃO faça o "Veredito Master" a menos que o usuário peça.

                    2. SE A PERGUNTA FOR GERAL (ex: "Qual o melhor setup?", "Analise o mercado", "O que fazer agora?"):
                       - Siga a estrutura detalhada obrigatória:
                       - **Análise Macro:** Comente os ativos (⟲ inversos), o Merc. Externo e notícias.
                       - **Leilão/OCR:** Compare OCR com ajuste. Avise se velho.
                       - **Avaliação dos 4 Operacionais:** Status de cada um (Op 1, Op 2, Op 3, Op 4).
                         - **ATENÇÃO ESPECIAL AO OP 3:** Se amplitude > 700 ou Regra 10 ativa, NÃO OPERAR.
                       - **Veredito Master:** Melhor oportunidade.
                       - **Regra de Ouro:** Não invente dados.
                       - ⚠️ FINALIZAÇÃO OBRIGATÓRIA: Termine com: 🎯 VIES FINAL: [COMPRA / VENDA / AGUARDAR]
                    """

                system_prompt = f"""
                Você é o "Spike", operador profissional de day trade da B3.
                Avalie os 4 Operacionais do usuário ou responda dúvidas.

                REGRAS DE COMPORTAMENTO:
                - **Perguntas Educacionais:** Atue como professor. NÃO emita VIES FINAL.
                - **Perguntas de Cálculo:** Faça a matemática. NÃO emita VIES FINAL.
                - **Perguntas de Mercado:** Aplique os 4 operacionais ou responda o que foi perguntado.

                OPERACIONAIS:
                1. Ajuste (Gap positivo→venda, negativo→compra).
                2. Drivers (Notícia 3★→ADRs, senão Merc. Externo. Positivo→compra, Negativo→venda).
                3. Rompimento 10h (ORB).
                4. SMC Puro (OB/FVG).

                REGRAS CRÍTICAS:
                - **Inversos:** WDO, DI1, VIX, DXY, OURO (⟲). Sobem = ruim para WIN.
                - **Stale:** Se 🚨 STALE no SMC, avise e não recomende SMC Puro.
                - **OCR velho:** Se ⚠️ ATENÇÃO (>30min), avise.
                - **Op 3 (ORB):** Se a vela estiver ausente OU amplitude > 700 OU Regra 10 ativa, o Op 3 está BLOQUEADO.
                - **Hierarquia Macro:** Merc. Externo negativo anula Op 1.
                - **ADRs (SOMA):** Pode passar de -100%, é normal.
                - **SMC EXPIRADO:** Se preço atual > 500 pts da entrada SMC, a entrada expirou.
                - **GAP EXTREMO:** Se Gap > 1000 pts, SMC perde prioridade.

                {bloco_modo}

                DADOS:
                {dados_contexto}
                """

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "openai/gpt-oss-120b",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "temperature": 0.1 if modo_direto else 0.2,
                    # ✅ FIX: Aumentado para 1024 para dar espaço ao modelo raciocinar antes de imprimir as 3 linhas
                    "max_tokens": 1024 if modo_direto else 4096 
                }

                max_retries = 3
                response = None
                for tentativa in range(max_retries):
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    if response.status_code == 200: break
                    elif response.status_code == 429:
                        st.warning(f"⚠️ Limite da Groq atingido. Aguardando 3s...")
                        time.sleep(3)
                    else: break

                if response is not None and response.status_code == 200:
                    dados_api = response.json()
                    resposta_ia = dados_api['choices'][0]['message']['content']
                    if modo_direto: resposta_ia = "⚡ " + resposta_ia
                    st.markdown(resposta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_ia})
                else:
                    code = response.status_code if response is not None else "?"
                    st.error(f"❌ Erro na Groq: {code}")
                    if response is not None: st.text(response.text)

            except Exception as e:
                st.error(f"❌ Erro ao processar: {e}")

with st.sidebar:
    st.markdown("### 🔍 O que o Spike está lendo")
    modo_atual = st.session_state.get("modo_resposta_direta", False)
    st.markdown(f"**Modo atual:** {'⚡ DIRETO' if modo_atual else '📄 COMPLETO'}")
    if st.button("🔄 Recarregar contexto"):
        compilar_contexto.clear()
        st.rerun()
    with st.expander("Ver Dados Enviados para a IA"):
        st.text(compilar_contexto())