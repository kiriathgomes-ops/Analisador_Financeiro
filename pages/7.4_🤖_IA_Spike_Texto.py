# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Spike_Texto.py
Versão: 2.6.8 — Consciência de Gap Extremo, Entrada SMC Expirada e Soma de ADRs.

Mudanças vs. 2.6.7:
  - Nova regra: "SMC EXPIRADO" (se o preço atual estiver > 500 pts da entrada, não operar).
  - Nova regra: "GAP EXTREMO" (se gap > 1000 pts, Novo Motor tem prioridade sobre SMC).
  - Nova regra: "SOMA DE ADRs" (entender que o indicador pode ser < -100% pois é soma bruta).
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

# --- VERIFICAÇÃO DE SEGURANÇA ---
status_chaves = key_manager.verificar_presenca_credenciais()
if not status_chaves.get("GROQ_API_KEY"):
    st.error("⚠️ Chave `GROQ_API_KEY` não encontrada no `.env`.")
    st.stop()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ==============================================================================
# COMPILADOR DE DADOS — v2.6.8
# ==============================================================================
_CACHE_VERSION_CTX = "v2.6.8"


@st.cache_data(ttl=30)
def compilar_contexto(_ver: str = _CACHE_VERSION_CTX) -> str:
    contexto = []

    # 0. CANDLES
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

    # 1. OCR
    csv_ocr = COLETAS_DIR / "preco_teorico_win_fluxo.csv"
    if csv_ocr.exists():
        contexto.append("### PREÇO TEÓRICO DO LEILÃO (OCR)")
        try:
            with open(csv_ocr, "r", encoding="utf-8-sig") as f:
                linhas = f.readlines()
            if linhas:
                ultima = linhas[-1].strip().split(",")
                if len(ultima) >= 2:
                    dt_ocr = ultima[0].strip()
                    preco_ocr = float(ultima[1])
                    contexto.append(f"Última leitura OCR: {preco_ocr:,.0f} pts (às {dt_ocr})")

                    dt_parsed = None
                    formato_usado = None
                    formatos = (
                        "%Y-%m-%d %H:%M:%S.%f", "%d/%m/%Y %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                        "%H:%M:%S.%f", "%H:%M:%S", "%H:%M",
                    )
                    for fmt in formatos:
                        try:
                            dt_parsed = _dt.strptime(dt_ocr, fmt)
                            formato_usado = fmt
                            break
                        except ValueError:
                            continue

                    if dt_parsed is not None:
                        if formato_usado in ("%H:%M:%S.%f", "%H:%M:%S", "%H:%M"):
                            hoje = _dt.now()
                            dt_parsed = dt_parsed.replace(year=hoje.year, month=hoje.month, day=hoje.day)
                        idade_min = (_dt.now() - dt_parsed).total_seconds() / 60.0
                        if idade_min < 0:
                            contexto.append(f"⚠️ Timestamp do OCR ({dt_ocr}) está no futuro")
                        elif idade_min > 30:
                            contexto.append(f"⚠️ ATENÇÃO: leitura OCR tem {idade_min:.0f} min — DESATUALIZADA")
                        else:
                            contexto.append(f"✅ Leitura recente ({idade_min:.0f} min)")
                    else:
                        contexto.append(f"⚠️ Timestamp do OCR não parseável ({dt_ocr})")
                else:
                    contexto.append("CSV do OCR encontrado, mas sem dados válidos na última linha.")
            else:
                contexto.append("CSV do OCR encontrado, mas está vazio.")
        except Exception as e:
            contexto.append(f"Erro ao ler o CSV do OCR: {e}")
    else:
        contexto.append("### PREÇO TEÓRICO DO LEILÃO (OCR)\n(Ainda sem leituras)")
    contexto.append("")

    # 2. NOTÍCIAS
    contexto.append("### NOTÍCIAS E CALENDÁRIO")
    noticias_0900 = {}
    path_0900 = COLETAS_DIR / "Noticias_Calendario_0900.json"
    if path_0900.exists():
        try:
            with open(path_0900, "r", encoding="utf-8") as f:
                noticias_0900 = json.load(f)
        except Exception:
            pass

    alerta = noticias_0900.get("alerta_noticia_0900", {}) or {}
    if alerta.get("tem_evento_3_estrelas"):
        eventos = ", ".join([e.get("evento", "?") for e in alerta.get("eventos", [])])
        contexto.append(f"🚨 ALERTA 3 ESTRELAS às 09:00: {eventos}")
    else:
        contexto.append("✅ Sem notícias críticas (3 estrelas) para as 09:00.")

    path_impacto = COLETAS_DIR / "Noticias_Impacto_Dia.json"
    if path_impacto.exists():
        try:
            with open(path_impacto, "r", encoding="utf-8") as f:
                impacto = json.load(f)
            resumo = impacto.get("resumo", {}) or {}
            if resumo:
                contexto.append(f"Resumo do dia: impacto total {resumo.get('impacto_total', '?')} → {resumo.get('classificacao', '?')}")
            alertas = impacto.get("alertas", {}) or {}
            if alertas.get("risco_abertura_WIN"):
                contexto.append("🚨 RISCO DE ABERTURA WIN ATIVO")
        except Exception:
            pass
    contexto.append("")

    # 3. INDICADORES
    contexto.append("### INDICADORES OPERACIONAIS")
    metricas = {}
    path_metricas = COLETAS_DIR / "Metricas_Calculadas.json"
    if path_metricas.exists():
        try:
            with open(path_metricas, "r", encoding="utf-8") as f:
                metricas = json.load(f)
        except Exception:
            pass

    ativos = {}
    path_ativos = COLETAS_DIR / "DadosAtivosUnificados.json"
    if path_ativos.exists():
        try:
            with open(path_ativos, "r", encoding="utf-8") as f:
                ativos = json.load(f).get("ativos", {})
        except Exception:
            pass

    ind_comp = metricas.get("indicadores_compostos", {}) or {}
    if ind_comp.get("indicador_mercado_externo") is not None:
        contexto.append(f"Indicador de Mercado Externo: {ind_comp['indicador_mercado_externo']:+.2f}%")
    if ind_comp.get("indicador_adrs_brasileiras") is not None:
        contexto.append(f"Indicador de ADRs Brasileiras (SOMA bruta): {ind_comp['indicador_adrs_brasileiras']:+.2f}")

    win_ajuste = (ativos.get("WIN_AJUSTE", {}) or {}).get("preco")
    win_last = ((ativos.get("WIN_LAST_TICK", {}) or {}).get("preco") or (ativos.get("WIN_FUT", {}) or {}).get("preco"))
    if win_ajuste and win_last:
        gap = win_last - win_ajuste
        contexto.append(f"Gap do Last vs Ajuste B3: {gap:+.0f} pts ({(gap/win_ajuste)*100:+.3f}%)")
    contexto.append("")

    # 4. ATIVOS (12 janelas)
    contexto.append("### DADOS DE MERCADO (Ativos Principais - 12 janelas)")
    contexto.append("⚠️ Ativos com ⟲ são INVERSOS ao WIN: WDO, DI1, VIX, DXY, OURO")
    ativos_foco = {
        "WIN": ["WIN_FUT", "B3_AJUSTE_WIN", "B3_FECHAMENTO_WIN", "BMFBOVESPA:WIN1!"],
        "WDO": ["WDO_FUT", "B3_AJUSTE_WDO", "B3_FECHAMENTO_WDO", "BMFBOVESPA:WDO1!"],
        "DI1 2027": ["DI1_2027", "BMFBOVESPA:DI1F2027"],
        "DI1 2029": ["DI1_2029", "BMFBOVESPA:DI1F2029"],
        "S&P500": ["SP500_FUT", "CME_MINI:ES1!"],
        "NASDAQ": ["NASDAQ_FUT", "CME_MINI:NQ1!"],
        "VIX": ["VIX", "TVC:VIX"],
        "DXY": ["DXY", "TVC:DXY"],
        "EWZ": ["EWZ", "AMEX:EWZ"],
        "MINERIO": ["IRON_ORE", "SGX:FEF1!"],
        "PETROLEO": ["CRUDE_OIL", "NYMEX:CL1!"],
        "OURO": ["TVC:GOLD", "GOLD"],
        "VALE ADR": ["NYSE:VALE", "VALE_ADR"],
        "PETR ADR": ["NYSE:PBR", "PETR_ADR"],
        "ITUB ADR": ["NYSE:ITUB", "ITUB_ADR"],
        "BBAS ADR": ["OTC:BDORY", "BBAS_ADR"],
        "BBD ADR": ["NYSE:BBD", "BBD_ADR"],
        "B3 ADR": ["OTC:BOLSY", "B3_ADR"],
        "VALE3": ["VALE3"],
        "PETR4": ["PETR4"],
        "ITUB4": ["ITUB4"],
        "BBAS3": ["BBAS3"],
        "BBDC4": ["BBDC4"],
        "B3SA3": ["B3SA3"],
    }
    inversos_win = {"WDO", "DI1 2027", "DI1 2029", "VIX", "DXY", "OURO"}
    janelas = [55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5, 0]
    coletas = {tf: {} for tf in janelas}
    for tf in janelas:
        caminho = COLETAS_DIR / f"Coleta_rom-{tf}.json"
        if caminho.exists():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    for item in json.load(f).get("coletas", []):
                        ativo_json = item.get("ativo")
                        var = (item.get("dados_reais") or {}).get("change_percent")
                        if var is None: continue
                        for nome_foco, chaves in ativos_foco.items():
                            if ativo_json in chaves:
                                if nome_foco not in coletas[tf]:
                                    coletas[tf][nome_foco] = var
                                break
            except Exception:
                pass

    header_cols = ["Ativo", "⟲"] + [("Agora" if tf == 0 else f"{tf}m") for tf in janelas]
    contexto.append(" | ".join(header_cols))
    for nome_foco in ativos_foco.keys():
        if nome_foco in coletas[0]:
            inv = "⟲" if nome_foco in inversos_win else " "
            linha = [nome_foco, inv] + [f"{coletas[tf].get(nome_foco, 0):+.2f}%" for tf in janelas]
            contexto.append(" | ".join(linha))
    contexto.append("")

    # 5. SMC
    contexto.append("### ANÁLISE SMC (Motor Python)")
    for tf_nome, arquivo in [("M15", "AnaliseGraficaSMC_Regras_M15.json"), ("M5", "AnaliseGraficaSMC_Regras.json")]:
        caminho = COLETAS_DIR / arquivo
        if not caminho.exists(): continue
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                smc = json.load(f)
            contexto.append(f"\n--- SMC {tf_nome} ---")
            if smc.get("stale"):
                contexto.append(f"🚨 STALE: candle de {smc.get('candle_idade_min', '?')} min atrás")
            contexto.append(f"Viés: {smc.get('bias_direcional')} (Conf: {smc.get('confianca_visual')}%) | Preço Atual no Momento do Cálculo: {smc.get('preco_atual')}")
            contexto.append(f"BOS: {smc.get('bos')} | CHOCH: {smc.get('choch')}")
            entrada = smc.get("entrada_sugerida")
            stop = smc.get("stop_sugerido")
            alvos = smc.get("alvos", []) or []
            if entrada is not None and stop is not None:
                risco = abs(entrada - stop)
                contexto.append(f"Entrada Sugerida: {entrada:.0f} | Stop: {stop:.0f} | Risco: {risco:.0f} pts")
                if alvos:
                    contexto.append(f"Alvos: {', '.join([f'{a:.0f}' for a in alvos])} (R:R 1º = 1:{abs(alvos[0]-entrada)/risco:.2f})")
            
            ni = smc.get("niveis_institucionais", {}) or {}
            contexto.append(f"POC Ontem: {ni.get('poc_ontem')} | VWAP Ontem: {ni.get('vwap_ontem')}")
            liq = smc.get("liquidez", {}) or {}
            contexto.append(f"BSL: {liq.get('bsl', [])} | SSL: {liq.get('ssl', [])}")
        except Exception:
            pass

    # 6. SNAPSHOT DO OPERACIONAL 3
    contexto.append("\n### SNAPSHOT DO OPERACIONAL 3 (Rompimento 10h)")
    snapshot_path = COLETAS_DIR / "snapshot_rompimento_10h.txt"
    if snapshot_path.exists():
        try:
            texto_snap = snapshot_path.read_text(encoding="utf-8")
            if "DADOS REAIS — SNAPSHOT DO PIPELINE" in texto_snap:
                bloco_dados = texto_snap.split("DADOS REAIS — SNAPSHOT DO PIPELINE")[1]
                contexto.append(bloco_dados[:3000])
            else:
                contexto.append("(Formato do snapshot não reconhecido)")
        except Exception as e:
            contexto.append(f"(Erro ao ler snapshot: {e})")
    else:
        contexto.append("(Snapshot do Op 3 não gerado ainda)")

    # 7. DECISÃO V2 (Novo Motor)
    contexto.append("\n### DECISÃO V2 (NOVO MOTOR / ORCHESTRATOR)")
    dec_path = COLETAS_DIR / "Decisao_V2.json"
    if dec_path.exists():
        try:
            with open(dec_path, "r", encoding="utf-8") as f:
                dec = json.load(f)
            nm = dec.get("decisao", {}).get("metadados", {}).get("novo_motor", {})
            if nm:
                contexto.append(f"Novo Motor Direção: {nm.get('direcao')}")
                contexto.append(f"Novo Motor Gap: {nm.get('gap_pontos')} pts")
                contexto.append(f"Novo Motor Score: {nm.get('score_magnitude')} (Força: {nm.get('score_forca')})")
        except Exception:
            pass

    return "\n".join(contexto)


# ==============================================================================
# INTERFACE — v2.6.8
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
                    🛑 MODO DIRETO ATIVADO — RESPOSTA OBRIGATORIAMENTE EM 3 LINHAS (Se for pergunta de mercado).
                    FORMATO EXATO:
                    🎯 Veredito: [Operacional N — COMPRA / VENDA / NEUTRO / SEM DADO]
                    💡 Motivo: [1 frase, máx 20 palavras]
                    ⚠️ Alertas: [stale / OCR velho / risco / "nenhum"]
                    """
                else:
                    bloco_modo = """
                    MODO COMPLETO — estrutura detalhada (Se for pergunta de mercado):
                    1. **Análise Macro:** Comente os ativos (⟲ inversos), o Merc. Externo e notícias.
                    2. **Leilão/OCR:** Compare OCR com ajuste. Avise se velho.
                    3. **Avaliação dos 4 Operacionais:** Status de cada um (Op 1, Op 2, Op 3, Op 4).
                       - **ATENÇÃO ESPECIAL AO OP 3:** Se o snapshot do Op 3 estiver no contexto, leia a "Amplitude" e a "Regra 10". Se amplitude > 700 ou Regra 10 ativa, NÃO OPERAR.
                    4. **Veredito Master:** Melhor oportunidade.
                    5. **Regra de Ouro:** Não invente dados.
                    
                    ⚠️ FINALIZAÇÃO OBRIGATÓRIA (Apenas para perguntas de mercado): Termine com:
                    🎯 VIES FINAL: [COMPRA / VENDA / AGUARDAR]
                    """

                system_prompt = f"""
                Você é o "Spike", operador profissional de day trade da B3 e um mentor quantitativo.
                Avalie os 4 Operacionais do usuário OU responda dúvidas teóricas/práticas.

                REGRAS DE COMPORTAMENTO:
                - **Perguntas Educacionais/Teóricas:** Se o usuário perguntar "O que é...", "Como funciona...", atue como professor. NÃO emita VIES FINAL.
                - **Perguntas de Cálculo:** Se pedir cálculo de lote, risco, etc., faça a matemática. NÃO emita VIES FINAL.
                - **Perguntas de Mercado:** Aplique os 4 operacionais e finalize com o VIES FINAL.

                OPERACIONAIS:
                1. Ajuste (Gap positivo→venda, negativo→compra).
                2. Drivers (Notícia 3★→ADRs, senão Merc. Externo. Positivo→compra, Negativo→venda).
                3. Rompimento 10h (ORB - Máxima e Mínima da vela 10h).
                4. SMC Puro (OB/FVG).

                REGRAS CRÍTICAS DE MERCADO:
                - **Inversos:** WDO, DI1, VIX, DXY, OURO (⟲). Sobem = ruim para WIN.
                - **Stale:** Se 🚨 STALE no SMC, avise e não recomende SMC Puro.
                - **OCR velho:** Se ⚠️ ATENÇÃO (>30min), avise.
                - **Op 3 (ORB):** Se o snapshot do Op 3 estiver no contexto, analise a vela de 10h. Se a vela estiver ausente OU se a amplitude for > 700 OU se a "Regra 10" estiver ativa (gap > 500), diga que o Op 3 está BLOQUEADO.
                - **Hierarquia Macro:** Merc. Externo negativo anula Op 1, mesmo com gap negativo.
                - **INDICADOR DE ADRs (SOMA):** O "Indicador de ADRs Brasileiras" no contexto é uma SOMA bruta de 6 ADRs. Portanto, é NORMAL que ele passe de -100%. Não trate como uma variação percentual simples, mas como um índice de pressão extrema.
                - **SMC EXPIRADO:** Se o SMC sugerir entrada (ex: Compra 175.215) mas o preço atual (ex: 177.135) já estiver > 500 pts distante, avise que a entrada EXPIRou e o R:R se perdeu.
                - **GAP EXTREMO:** Se o Gap vs Ajuste B3 for > 1000 pts (para cima ou baixo), o SMC perde prioridade. O mercado está anômalo. Priorize o Novo Motor (VENDA no gap de -31k) ou AGUARDE.

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
                    "max_tokens": 512 if modo_direto else 4096
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
                    if modo_direto and "VIES FINAL" in resposta_ia: 
                        resposta_ia = "⚡ " + resposta_ia
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