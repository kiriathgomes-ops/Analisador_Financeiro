# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Spike_Texto.py
Versão: 2.6.4 — Spike lendo as 12 janelas de momentum

Mudança vs. 2.6.3:
  - janelas expandido de [0, 5, 10, 15, 30, 55] para as 12 coletas completas.
  - Ordem da tabela alterada para cronológica (55m -> Agora), permitindo que a IA
    leia a aceleração do momentum suavemente.

Mantido da v2.6.3:
  - Anti-alucinação (OCR vs Ajuste B3, Hierarquia Macro, Consistência)
  - Toggle "Resposta direta" (5 proteções)
  - Parser OCR com .%f
  - Noticias, SMC stale/R:R, 24 ativos.
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
# COMPILADOR DE DADOS — v2.6.4 (12 janelas)
# ==============================================================================
_CACHE_VERSION_CTX = "v2.6.4"


@st.cache_data(ttl=30)
def compilar_contexto(_ver: str = _CACHE_VERSION_CTX) -> str:
    """Lê os JSONs, o OCR e transforma em texto compacto para a IA."""
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
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%d/%m/%Y %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%d/%m/%Y %H:%M:%S",
                        "%d/%m/%Y %H:%M",
                        "%H:%M:%S.%f",
                        "%H:%M:%S",
                        "%H:%M",
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
                            contexto.append(f"⚠️ Timestamp do OCR ({dt_ocr}) está no futuro — verificar relógio")
                        elif idade_min > 30:
                            contexto.append(f"⚠️ ATENÇÃO: leitura OCR tem {idade_min:.0f} min — pode estar DESATUALIZADA")
                        else:
                            contexto.append(f"✅ Leitura recente ({idade_min:.0f} min)")
                    else:
                        contexto.append(f"⚠️ Timestamp do OCR não parseável ({dt_ocr}) — não foi possível validar idade")
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
                total = resumo.get("impacto_total", "?")
                clas = resumo.get("classificacao", "?")
                contexto.append(f"Resumo do dia: impacto total {total} → {clas}")

            alertas = impacto.get("alertas", {}) or {}
            linhas_alerta = []
            if alertas.get("risco_abertura_WIN"):
                linhas_alerta.append("🚨 RISCO DE ABERTURA WIN ATIVO")
            if alertas.get("tem_3_estrelas_outros_horarios"):
                nots = alertas.get("noticias_3_estrelas_outros_horarios", [])
                linhas_alerta.append(f"🚨 3★ fora das 09:00: {', '.join(nots) if nots else '(ver horários)'}")
            if alertas.get("tem_multiplas_2_estrelas_mesmo_horario"):
                hors = alertas.get("horarios_multiplas_2_estrelas", [])
                linhas_alerta.append(f"⚠️ Múltiplas 2★ no mesmo horário: {', '.join(hors) if hors else '(ver horários)'}")
            if linhas_alerta:
                contexto.append("Alertas de risco:")
                for l in linhas_alerta:
                    contexto.append(f"   • {l}")
            else:
                contexto.append("Alertas de risco: ✅ nenhum ativo")

            horarios = impacto.get("horarios", []) or []
            if horarios:
                contexto.append(f"Eventos agendados ({len(horarios)} horários):")
                for h in horarios:
                    hora = h.get("hora", "?")
                    clas = h.get("classificacao", "?")
                    for ev in (h.get("eventos") or []):
                        nome = ev.get("nome", "?")
                        pais = ev.get("pais", "?")
                        moeda = ev.get("moeda", "?")
                        estrelas = ev.get("estrelas", "?")
                        contexto.append(f"   • {hora} [{estrelas}★] {pais} {moeda} — {nome} ({clas})")
        except Exception:
            pass

    path_cal = COLETAS_DIR / "Noticias_Calendario.json"
    if path_cal.exists():
        try:
            with open(path_cal, "r", encoding="utf-8") as f:
                cal = json.load(f)
            eventos_cal = ((cal.get("calendario_eventos", {}) or {}).get("eventos", []) or [])
            if eventos_cal:
                linhas_real = []
                for ev in eventos_cal:
                    atual = (ev.get("atual") or "").strip()
                    if not atual:
                        continue
                    nome = ev.get("evento", "?")
                    hora = ev.get("hora", "?")
                    pais = ev.get("pais", "?")
                    previsao = (ev.get("previsao") or "").strip()
                    anterior = (ev.get("anterior") or "").strip()
                    importancia = ev.get("importancia", "?")

                    sufixo = ""
                    try:
                        a = float(atual)
                        p = float(previsao) if previsao else None
                        ant = float(anterior) if anterior else None
                        if p is not None:
                            if a > p:
                                sufixo = " — acima do esperado"
                            elif a < p:
                                sufixo = " — abaixo do esperado"
                            else:
                                sufixo = " — em linha com o esperado"
                        if ant is not None:
                            if a > ant:
                                sufixo += " (subiu vs anterior)"
                            elif a < ant:
                                sufixo += " (caiu vs anterior)"
                    except (TypeError, ValueError):
                        pass

                    prev_txt = f"esperado {previsao}" if previsao else "sem previsão"
                    linhas_real.append(
                        f"   • {hora} [{importancia}★] {pais} — {nome}: atual {atual} ({prev_txt}){sufixo}"
                    )
                if linhas_real:
                    contexto.append("Dados realizados (atual vs esperado):")
                    contexto.extend(linhas_real)
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
    ind_ext = ind_comp.get("indicador_mercado_externo")
    ind_adrs = ind_comp.get("indicador_adrs_brasileiras")
    if ind_ext is not None:
        contexto.append(f"Indicador de Mercado Externo: {ind_ext:+.2f}%")
    if ind_adrs is not None:
        contexto.append(f"Indicador de ADRs Brasileiras: {ind_adrs:+.2f}%")

    try:
        rom0_path = COLETAS_DIR / "Coleta_rom-0.json"
        if rom0_path.exists():
            with open(rom0_path, "r", encoding="utf-8") as f:
                rom0 = json.load(f)
            comp_map = {}
            for item in rom0.get("coletas", []):
                ativo_nome = item.get("ativo")
                var = (item.get("dados_reais") or {}).get("change_percent")
                if ativo_nome and var is not None:
                    comp_map[ativo_nome] = var
            comp_linhas = []
            for nome, chaves, inv in [
                ("VIX", ["TVC:VIX", "VIX"], True),
                ("Petróleo", ["NYMEX:CL1!", "CRUDE_OIL"], False),
                ("Minério", ["SGX:FEF1!", "IRON_ORE"], False),
                ("EWZ", ["AMEX:EWZ", "EWZ"], False),
                ("DXY", ["TVC:DXY", "DXY"], True),
            ]:
                for ch in chaves:
                    if ch in comp_map:
                        suf = " ⟲ inverso" if inv else ""
                        comp_linhas.append(f"   • {nome}: {comp_map[ch]:+.2f}%{suf}")
                        break
            if comp_linhas:
                contexto.append("Componentes do Mercado Externo:")
                contexto.extend(comp_linhas)
    except Exception:
        pass

    win_ajuste = (ativos.get("WIN_AJUSTE", {}) or {}).get("preco")
    win_last = ((ativos.get("WIN_LAST_TICK", {}) or {}).get("preco")
                or (ativos.get("WIN_FUT", {}) or {}).get("preco"))
    if win_ajuste and win_last:
        gap = win_last - win_ajuste
        pct = (gap / win_ajuste) * 100
        contexto.append(f"Gap do Last vs Ajuste B3: {gap:+.0f} pts ({pct:+.3f}%)")

    path_estim = COLETAS_DIR / "EstimativaAbertura.json"
    if path_estim.exists():
        try:
            with open(path_estim, "r", encoding="utf-8") as f:
                estim = json.load(f)
            pivots = estim.get("pivot_points", {}).get("WIN_FUT", {}) or {}
            if pivots:
                contexto.append(
                    f"Pivots WIN: PP={float(pivots.get('PP', 0) or 0):.0f} | "
                    f"R1={float(pivots.get('R1', 0) or 0):.0f} | R2={float(pivots.get('R2', 0) or 0):.0f} | "
                    f"S1={float(pivots.get('S1', 0) or 0):.0f} | S2={float(pivots.get('S2', 0) or 0):.0f}"
                )
        except Exception:
            pass

    path_dec = COLETAS_DIR / "Decisao_V2.json"
    if path_dec.exists():
        try:
            with open(path_dec, "r", encoding="utf-8") as f:
                dec = json.load(f)
            cenario = ((dec.get("decisao", {}) or {}).get("metadados", {}) or {}).get("opening_scenario", {}) or {}
            direcao = cenario.get("direcao_provavel")
            prob = cenario.get("probabilidade_direcao")
            conf_geral = cenario.get("confianca_geral")
            if direcao:
                contexto.append(f"Cenário de abertura: {direcao} (prob {prob}% / conf {conf_geral}%)")
        except Exception:
            pass

    contexto.append("")

    # 4. ATIVOS (12 janelas)
    contexto.append("### DADOS DE MERCADO (Ativos Principais - 12 janelas)")
    contexto.append("⚠️ Ativos com ⟲ são INVERSOS ao WIN (sobem = ruim para o WIN): WDO, DI1, VIX, DXY, OURO")
    contexto.append("")

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

    # v2.6.4 — 12 janelas em ordem cronológica
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
                        if var is None:
                            continue
                        for nome_foco, chaves in ativos_foco.items():
                            if ativo_json in chaves:
                                if nome_foco not in coletas[tf]:
                                    coletas[tf][nome_foco] = var
                                break
            except Exception:
                pass

    # Header dinâmico: Ativo | ⟲ | 55m | 50m | ... | Agora
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
    for tf_nome, arquivo in [("M15 (Macro)", "AnaliseGraficaSMC_Regras_M15.json"),
                              ("M5 (Médio)", "AnaliseGraficaSMC_Regras.json")]:
        caminho = COLETAS_DIR / arquivo
        if not caminho.exists():
            continue
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                smc = json.load(f)
            contexto.append(f"\n--- SMC {tf_nome} ---")

            stale = smc.get("stale", False)
            if stale:
                idade = smc.get("candle_idade_min")
                motivo = smc.get("stale_motivo")
                idade_str = f"{idade:.1f} min" if isinstance(idade, (int, float)) else "?"
                contexto.append(f"🚨 STALE: candle de {idade_str} atrás (motivo: {motivo})")
                contexto.append("   ⚠️ NÃO recomendar operação sem confirmar dados atuais.")

            contexto.append(f"Viés: {smc.get('bias_direcional')} (Conf: {smc.get('confianca_visual')}%) | Preço Atual: {smc.get('preco_atual')}")
            contexto.append(f"BOS: {smc.get('bos', False)} | CHOCH: {smc.get('choch', False)}")

            entrada = smc.get("entrada_sugerida")
            stop = smc.get("stop_sugerido")
            alvos = smc.get("alvos", []) or []
            if entrada is not None and stop is not None:
                risco = abs(entrada - stop)
                contexto.append(f"Entrada sugerida: {entrada:.0f} | Stop: {stop:.0f} | Risco: {risco:.0f} pts")
                if alvos:
                    alvos_str = ", ".join([f"{a:.0f}" for a in alvos])
                    contexto.append(f"Alvos: {alvos_str}")
                    if risco > 0:
                        rr1 = abs(alvos[0] - entrada) / risco
                        contexto.append(f"R:R do alvo 1: 1:{rr1:.2f}")

            obs = smc.get("order_blocks", []) or []
            if obs:
                obs_str = ", ".join([f"{o.get('tipo')} em {o.get('abertura')}" for o in obs[:3]])
                contexto.append(f"OBs: {obs_str}")

            fvgs = smc.get("fair_value_gaps", []) or []
            if fvgs:
                fvg_str = ", ".join([f"{f.get('tipo')} ({f.get('inferior')}-{f.get('superior')})" for f in fvgs[:3]])
                contexto.append(f"FVGs: {fvg_str}")

            ni = smc.get("niveis_institucionais", {}) or {}
            contexto.append(f"POC Ontem: {ni.get('poc_ontem')} | VWAP Ontem: {ni.get('vwap_ontem')}")
            if ni.get("ob_alinhado_com_poc"):
                contexto.append("⭐ OB alinhado com POC (confluência institucional)")

            liq = smc.get("liquidez", {}) or {}
            contexto.append(f"BSL (Topos): {liq.get('bsl', [])} | SSL (Fundos): {liq.get('ssl', [])}")

            eventos = smc.get("eventos_estrutura", []) or []
            if eventos:
                ev_str = ", ".join([f"{e.get('tipo')} {e.get('direcao')} em {e.get('preco')}" for e in eventos[:3]])
                contexto.append(f"Eventos recentes: {ev_str}")
        except Exception as e:
            contexto.append(f"--- SMC {tf_nome} ---\nErro ao ler: {e}")

    return "\n".join(contexto)


# ==============================================================================
# INTERFACE — v2.6.4
# ==============================================================================

# 1) Inicializa session_state (antes de QUALQUER widget)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Fala, trader! Sou o Spike. Já cruzei seus dados, as notícias e o OCR do leilão. Quer que eu avalie qual dos 4 Operacionais está dando o melhor gatilho agora?"}
    ]
if "modo_resposta_direta" not in st.session_state:
    st.session_state["modo_resposta_direta"] = False

# 2) Toggle PRIMEIRO (antes do histórico — posição estável entre reruns)
st.markdown("### 💬 Mesa de Operações")
col_esq, col_dir = st.columns([4, 1])
with col_dir:
    st.toggle(
        "⚡ Resposta direta",
        key="modo_resposta_direta",
        help="Marcado: veredito em até 3 linhas. Desmarcado: análise completa.",
    )

# 3) Histórico do chat (depois do toggle)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4) Chat input (com key explícita)
if prompt := st.chat_input("Ex: Qual o melhor setup agora? Qual o preço do leilão no OCR?", key="spike_chat_input"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 5) Lê o modo do session_state (fonte de verdade)
    modo_direto = bool(st.session_state.get("modo_resposta_direta", False))
    modo_label = "direto ⚡" if modo_direto else "completo"

    with st.chat_message("assistant"):
        with st.spinner(f"Spike está avaliando [{modo_label}]..."):
            try:
                dados_contexto = compilar_contexto()

                if modo_direto:
                    bloco_modo = """
                    🛑 MODO DIRETO ATIVADO — RESPOSTA OBRIGATORIAMENTE EM 3 LINHAS. NÃO ESCREVA MAIS QUE ISSO.

                    PROIBIDO nesta resposta:
                    - ❌ NÃO use "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"
                    - ❌ NÃO escreva os cabeçalhos "Análise Macro", "Leilão/OCR", "Avaliação dos 4 Operacionais", "Veredito Master", "Avisos finais"
                    - ❌ NÃO repita dados do contexto (VIX, DXY, gap, OCR, etc.)
                    - ❌ NÃO justifique com mais de uma frase
                    - ❌ NÃO escreva texto antes ou depois do formato abaixo

                    FORMATO EXATO (copie esta estrutura, 3 linhas):

                    🎯 Veredito: [Operacional N — COMPRA / VENDA / NEUTRO / SEM DADO]
                    💡 Motivo: [1 frase, máx 20 palavras]
                    ⚠️ Alertas: [stale / OCR velho / risco_abertura / "nenhum"]

                    FIM. A resposta termina na linha "⚠️ Alertas:". Nada mais.
                    """
                else:
                    bloco_modo = """
                    MODO COMPLETO — estrutura detalhada obrigatória:

                    SUA MISSÃO NA RESPOSTA:
                    1. Ser direto e falar como um trader de mesa.
                    2. **Análise Macro:** Comente os ativos da tabela (⟲ quando inverso), os componentes do merc. externo, e os dados realizados.
                    3. **Análise de Leilão/OCR:** Se houver OCR, compare com o Ajuste B3 (Op 1) e com os OBs (Op 4). Se estiver velho, avise.
                    4. **Avaliação dos 4 Operacionais:** Diga o status de CADA UM dos 4.
                    5. **Veredito Master:** Diga qual dos 4 é a melhor oportunidade agora e justifique.
                    6. **Regra de Ouro:** Se os dados não estiverem na tabela, NÃO INVENTE. Diga apenas que não recebeu esse dado.
                    """

                system_prompt = f"""
                Você é o "Spike", um operador profissional de day trade da B3.
                Seu trabalho é avaliar os 4 Operacionais Oficiais do usuário e dizer qual deles tem o setup mais robusto no momento.

                OS 4 OPERACIONAIS DO USUÁRIO:
                1. **Operacional 1 (Ajuste):** Gap positivo → VENDER no ajuste. Gap negativo → COMPRAR no ajuste.
                2. **Operacional 2 (Drivers de Abertura):** Se houver notícia 3★, priorize ADRs. Se não, priorize Mercado Externo. Positivo = Compra. Negativo = Venda.
                3. **Operacional 3 (Rompimento 10h):** Entrada no rompimento da vela de 10:00. Alvo = Tamanho do candle. Stop = Extremidade oposta.
                4. **Operacional 4 (SMC Puro):** Entrada em OBs, FVGs ou Liquidez.

                REGRAS CRÍTICAS DE INTERPRETAÇÃO:
                - **Ativos ⟲ INVERSOS ao WIN:** WDO, DI1 2027, DI1 2029, VIX, DXY, OURO. Quando esses SOBEM, é RUIM para o WIN. Nunca os trate como "drivers bullish".
                - **SMC STALE:** Se 🚨 STALE, avise. NÃO recomende SMC Puro sem dados frescos.
                - **R:R:** Se R:R do alvo 1 < 1.5, alerte.
                - **OCR desatualizado:** Se ⚠️ ATENÇÃO (idade > 30min), avise ANTES de usá-lo.
                - **Dados macro realizados:** USE-OS. Ex.: jobless claims 194 vs 200 = abaixo = risk-on = bullish WIN.
                - **Alertas de risco:** Se "risco_abertura_WIN" ativo, avise antes.

                REGRAS ANTI-ALUCINAÇÃO (v2.6.4):
                - **DIFERENÇA ENTRE OCR E AJUSTE B3:** O OCR (lido no leilão) NÃO É o preço de Ajuste B3. NUNCA diga que o ajuste B3 tem o mesmo valor do OCR. O Ajuste B3 é a referência oficial da B3. Se precisar estimá-lo, use: Last Tick + Gap. Se não souber o Last Tick, diga "Use o ajuste oficial". NUNCA invente o valor do ajuste.
                - **HIERARQUIA MACRO:** O viés macro é definido pelo Indicador de Mercado Externo. Se ele estiver fortemente negativo (ex: < -10%), o viés é BAIXA. Um único dado positivo (ex: Jobless Claims abaixo do esperado) NÃO inverte o viés macro. Se o Op 1 for compra contra o macro, alerte o conflito.
                - **CONSISTÊNCIA DE VEREDITO:** Se em perguntas anteriores você escolheu o Op 2 (Venda) por causa do macro bearish, não mude para Op 1 (Compra) na próxima resposta sem justificar explicitamente que os dados de mercado mudaram.

                {bloco_modo}

                DADOS DO SISTEMA:
                {dados_contexto}
                """

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

                max_tokens = 512 if modo_direto else 2048
                temperature = 0.1 if modo_direto else 0.2

                payload = {
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                max_retries = 3
                response = None
                for tentativa in range(max_retries):
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:
                        st.warning(f"⚠️ Limite da Groq atingido. Aguardando 3s (Tentativa {tentativa+1}/{max_retries})...")
                        time.sleep(3)
                    else:
                        break

                if response is not None and response.status_code == 200:
                    dados_api = response.json()
                    resposta_ia = dados_api['choices'][0]['message']['content']

                    if modo_direto:
                        resposta_ia = "⚡ " + resposta_ia

                    st.markdown(resposta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_ia})
                else:
                    code = response.status_code if response is not None else "?"
                    st.error(f"❌ Erro na Groq: {code}")
                    if response is not None:
                        st.text(response.text)

            except Exception as e:
                st.error(f"❌ Erro ao processar: {e}")


# --- PAINEL DE DEBUG ---
with st.sidebar:
    st.markdown("### 🔍 O que o Spike está lendo")

    modo_atual = st.session_state.get("modo_resposta_direta", False)
    st.markdown(f"**Modo atual:** {'⚡ DIRETO' if modo_atual else '📄 COMPLETO'}")
    st.caption(f"max_tokens: {512 if modo_atual else 2048} · temperature: {0.1 if modo_atual else 0.2}")

    if st.button("🔄 Recarregar contexto", help="Limpa o cache e relê todos os JSONs"):
        compilar_contexto.clear()
        st.rerun()
    with st.expander("Ver Dados Enviados para a IA"):
        st.text(compilar_contexto())
        