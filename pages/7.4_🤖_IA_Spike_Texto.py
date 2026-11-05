# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Spike_Texto.py
Versão: 3.6.0 — Premium (SMC Multi-TF + Coleta Dupla Diário/Ext + Regras Operacionais)
Objetivo: Chat interativo com visão 360º do mercado.
"""

import streamlit as st

# 1. O SET_PAGE_CONFIG TEM QUE SER O PRIMEIRO COMANDO STREAMLIT DO ARQUIVO
st.set_page_config(page_title="Quant Terminal - Spike Premium", layout="wide")

# 2. IMPORTAÇÕES BLINDADAS (Se der erro, avisa na tela)
try:
    import logging
    import os
    import time
    import json
    import requests
    from pathlib import Path
    from datetime import datetime as _dt
    from config import COLETAS_DIR
    from utils.KeyManager import key_manager
    
    st.markdown("<h2 style='color:#00d4ff;'>💎 IA Spike PREMIUM — Visão 360º</h2>", unsafe_allow_html=True)
    st.caption("SMC Multi-Timeframe, Fluxo Diário/Extendido, Notícias e Operacionais Mastigados.")
    
    status_chaves = key_manager.verificar_presenca_credenciais()
    if not status_chaves.get("GROQ_API_KEY"):
        st.error("⚠️ Chave `GROQ_API_KEY` não encontrada no `.env`.")
        st.stop()
        
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

except Exception as e:
    st.error(f"❌ Erro na inicialização (Config/KeyManager): {e}")
    st.stop()

logger = logging.getLogger(__name__)
_CACHE_VERSION_CTX = "v3.6.0_PREMIUM"

@st.cache_data(ttl=30)
def compilar_contexto(_ver: str = _CACHE_VERSION_CTX) -> str:
    contexto = []

    # 1. Candles
    contexto.append("### ÚLTIMOS 5 CANDLES M5 (MT5)")
    vela_10h = None
    try:
        from cache_candles import obter_candles
        candles, _ = obter_candles("WIN$", 5, 20)
        for c in candles[-5:]:
            contexto.append(f"{c['time'][11:16]} | O:{c['open']:.0f} H:{c['high']:.0f} L:{c['low']:.0f} C:{c['close']:.0f}")
        for c in candles:
            if "10:00" in c['time']:
                vela_10h = c
                break
    except Exception as e:
        contexto.append(f"Erro ao ler candles: {e}")
    contexto.append("")

    # 2. Fluxo de 5 Janelas + Duplo (Diário / Ext)
    contexto.append("### FLUXO DE MERCADO (Janelas Intraday + Diário)")
    mapa_ativos = {
        "WIN": ["WIN_FUT", "BMFBOVESPA:WIN1!", "WIN_LAST_TICK"],
        "WDO": ["WDO_FUT", "BMFBOVESPA:WDO1!", "WDO_LAST_TICK"],
        "DI1 2027": ["DI1_2027", "BMFBOVESPA:DI1F2027"],
        "VIX": ["VIX", "TVC:VIX"],
        "DXY": ["DXY", "TVC:DXY"],
        "S&P500": ["SP500_FUT", "CME_MINI:ES1!"],
        "EWZ": ["EWZ", "AMEX:EWZ"],
        "VALE_ADR": ["VALE_ADR", "NYSE:VALE"],
        "PETR_ADR": ["PETR_ADR", "NYSE:PBR"],
        "ITUB_ADR": ["ITUB_ADR", "NYSE:ITUB"],
        "BBAS_ADR": ["BBAS_ADR", "OTC:BDORY"],
        "BBD_ADR": ["BBD_ADR", "NYSE:BBD"],
        "B3_ADR": ["B3_ADR", "OTC:BOLSY"],
        "VALE3": ["VALE3"], "PETR4": ["PETR4"], "ITUB4": ["ITUB4"],
        "BBAS3": ["BBAS3"], "BBDC4": ["BBDC4"], "B3SA3": ["B3SA3"]
    }
    janelas = [20, 15, 10, 5, 0]
    coletas = {tf: {} for tf in janelas}
    diarios = {} # Armazena o change_daily da janela 0 (Agora)
    
    for tf in janelas:
        path = COLETAS_DIR / f"Coleta_rom-{tf}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for item in json.load(f).get("coletas", []):
                    dados = item.get("dados_reais") or {}
                    var = dados.get("change_percent")
                    var_d = dados.get("change_daily")
                    
                    for nome, aliases in mapa_ativos.items():
                        if item.get("ativo") in aliases and var is not None:
                            if nome not in coletas[tf]: 
                                coletas[tf][nome] = var
                                if tf == 0 and var_d is not None:
                                    diarios[nome] = var_d
                            break

    grupos_fluxo = [
        ("Macro", ["WIN", "WDO", "DI1 2027", "VIX", "DXY", "S&P500"]),
        ("ADRs", ["EWZ", "VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"]),
        ("B3", ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"])
    ]
    for nome_grupo, chaves in grupos_fluxo:
        contexto.append(f"\n[{nome_grupo}]")
        contexto.append("Ativo    | 20m    | 15m    | 10m    | 5m     | Agora(Ext) | Diário")
        for k in chaves:
            if k in coletas[0]:
                inv = "⟲ " if k in ["WDO", "DI1 2027", "VIX", "DXY"] else "  "
                linha = [f"{inv}{k.ljust(6)}"]
                for tf in [20, 15, 10, 5]:
                    val = coletas[tf].get(k, 0)
                    linha.append(f"{val:+.2f}%")
                
                linha.append(f"{coletas[0].get(k, 0):+.2f}%")
                
                v_d = diarios.get(k)
                linha.append(f"{v_d:+.2f}%" if v_d is not None else "—")
                
                contexto.append(" | ".join(linha))
    contexto.append("")

    # 3. Pivôs e Institucional
    contexto.append("### PIVÔS E NÍVEIS INSTITUCIONAIS")
    est_path = COLETAS_DIR / "EstimativaAbertura.json"
    if est_path.exists():
        with open(est_path, "r", encoding="utf-8") as f:
            est = json.load(f)
            pivots = est.get("pivot_points", {}).get("WIN_FUT", {})
            if pivots:
                contexto.append(f"Pivôs: R2={pivots.get('R2')} | R1={pivots.get('R1')} | PP={pivots.get('PP')} | S1={pivots.get('S1')} | S2={pivots.get('S2')}")
            inst = est.get("pivots_institucionais", {})
            if inst.get("poc_ontem"):
                contexto.append(f"Institucional: POC={inst.get('poc_ontem')} | VWAP={inst.get('vwap_ontem')}")
    contexto.append("")

    # 4. SMC MULTI-TIMEFRAME (M15, M5, M1 + MTF)
    contexto.append("### SMC MULTI-TIMEFRAME (Zonas e Alvos)")
    
    def extrair_smc(arquivo, label):
        path = COLETAS_DIR / arquivo
        if not path.exists(): return
        with open(path, "r", encoding="utf-8") as f:
            smc = json.load(f)
        is_stale = smc.get('stale', False)
        contexto.append(f"[{label}] Bias: {smc.get('bias_direcional')} (Conf: {smc.get('confianca_visual')}%) | Stale: {is_stale}")
        
        obs = smc.get("order_blocks", [])
        if obs:
            obs_txt = [f"{ob.get('tipo')} em {ob.get('preco')}" for ob in obs[:2]]
            contexto.append(f"  - OBs: {' | '.join(obs_txt)}")
            
        fvgs = smc.get("fair_value_gaps", [])
        if fvgs:
            fvg_txt = [f"{fvg.get('tipo')} {fvg.get('inferior')}-{fvg.get('superior')}" for fvg in fvgs[:2]]
            contexto.append(f"  - FVGs: {' | '.join(fvg_txt)}")

    extrair_smc("AnaliseGraficaSMC_Regras_M15.json", "M15 (Macro)")
    extrair_smc("AnaliseGraficaSMC_Regras.json", "M5 (Médio)")
    extrair_smc("AnaliseGraficaSMC_Regras_M1.json", "M1 (Micro)")

    mtf_path = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"
    if mtf_path.exists():
        with open(mtf_path, "r", encoding="utf-8") as f:
            mtf = json.load(f).get("confluencia", {})
            contexto.append(f"[MTF] Veredito: {mtf.get('veredito_mtf')} | Direção: {mtf.get('direcao_dominante')}")
    contexto.append("")

    # 5. OPERACIONAIS
    contexto.append("### OPERACIONAIS DE ABERTURA E SMC")
    op_path = COLETAS_DIR / "Resultado_Calculadora_Operacional_Abertura.json"
    if op_path.exists():
        with open(op_path, "r", encoding="utf-8") as f:
            op_data = json.load(f)
            ops = op_data.get("decisao_core", {}).get("win", {}).get("operacionais", {})
            for op_nome, op_info in ops.items():
                contexto.append(f"{op_nome.upper()}: {op_info.get('status', 'DESCONHECIDO')}")
                detalhes = op_info.get("detalhes", {})
                if detalhes:
                    contexto.append(f"  Detalhes: {detalhes}")
                escoras = op_info.get("escoras", [])
                if escoras:
                    contexto.append(f"  Escoras (Stop): {', '.join(escoras[:2])}")
                barreiras = op_info.get("barreiras", [])
                if barreiras:
                    contexto.append(f"  Barreiras (Alvo): {', '.join(barreiras[:2])}")
    contexto.append("")

    # 6. NOTÍCIAS
    contexto.append("### NOTÍCIAS DO DIA (Calendário)")
    not_cal_path = COLETAS_DIR / "Noticias_Calendario.json"
    not_imp_path = COLETAS_DIR / "Noticias_Impacto_Dia.json"
    if not_imp_path.exists():
        with open(not_imp_path, "r", encoding="utf-8") as f:
            imp = json.load(f).get("resumo", {})
            contexto.append(f"Impacto Geral: {imp.get('classificacao', '?')}")
    if not_cal_path.exists():
        with open(not_cal_path, "r", encoding="utf-8") as f:
            eventos = json.load(f).get("calendario_eventos", {}).get("eventos", [])
            for ev in eventos:
                estrelas = "★" * ev.get("importancia", 0)
                contexto.append(f"- {ev.get('hora')} | {ev.get('pais')} | {ev.get('evento')} | Imp: {estrelas} | Atual: {ev.get('atual')} | Prev: {ev.get('previsao')}")
    contexto.append("")

    # 7. V2
    contexto.append("### V2")
    dec_path = COLETAS_DIR / "Decisao_V2.json"
    if dec_path.exists():
        with open(dec_path, "r", encoding="utf-8") as f:
            dec = json.load(f)
            d = dec.get("decisao", {})
            contexto.append(f"V2 Viés: {d.get('vies_final')} | Motivo: {d.get('motivo_saida')}")
    contexto.append("")

    return "\n".join(contexto)

# Interface padrão
if "messages_premium" not in st.session_state:
    st.session_state.messages_premium = [{"role": "assistant", "content": "Spike Premium aqui. Visão 360º ativada. Qual a boa?"}]
if "modo_direto_premium" not in st.session_state:
    st.session_state["modo_direto_premium"] = False

st.markdown("### 💬 Mesa de Operações (Premium)")
col_esq, col_dir = st.columns([4, 1])
with col_dir:
    st.toggle("⚡ Resposta direta", key="modo_direto_premium")

for msg in st.session_state.messages_premium:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Pergunte algo...", key="chat_premium"):
    st.session_state.messages_premium.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Cruzando os 360 graus do mercado..."):
            try:
                dados_contexto = compilar_contexto()
                bloco_modo = "Responda em no máximo 3 linhas." if st.session_state.get("modo_direto_premium") else "Responda de forma direta e focada em ação."
                
                system_prompt = f"""
                Você é o Spike Premium. Foco em trade de 1 minuto.
                Use os dados mastigados para dar respostas precisas de timing e gatilhos.

                REGRAS CRÍTICAS DOS OPERACIONAIS:
                1. **Op 1 (Retorno ao Ajuste):** Gap NÃO bloqueia. O que bloqueia são as "Barreiras" (OBs/Pivôs) no caminho ou contra-fluxo macro.
                2. **Op 2 (Explosão):** Gap NÃO importa. Foco na força/direção do Driver. Alvo1=250, Alvo2=400, Stop=250.
                3. **Op 3 (ORB):** Leia os cenários exatos (Gatilho, Stop, Alvo) do JSON. Não invente valores.
                4. **Op 4 (SMC Puro):** Se estiver STALE, ignore. Se preço > 500 pts da entrada, expirou.

                REGRAS DE LEITURA DE MERCADO:
                5. **Coleta Dupla (Diário vs Ext):** A tabela de fluxo tem duas colunas: "Agora(Ext)" e "Diário". O Diário é o fechamento oficial. O Agora(Ext) é o pré/pós-market. SEMPRE compare os dois. Se o Diário for -2% e o Agora for +1%, o ativo caiu ontem mas tenta recuperar agora. Avise o usuário sobre essa divergência.
                6. **SMC Multi-TF:** O M15 é o Macro (manda mais). Se o M15 for BAIXA e o M5 for ALTA, é uma armadilha.
                7. **Inversos:** WDO, DI1, VIX e DXY (⟲). Se subirem, é ruim para o WIN.

                {bloco_modo}
                
                DADOS:
                {dados_contexto}
                """
                
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "openai/gpt-oss-120b",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2048 
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=40)
                if response.status_code == 200:
                    resposta = response.json()['choices'][0]['message']['content']
                    st.markdown(resposta)
                    st.session_state.messages_premium.append({"role": "assistant", "content": resposta})
                else:
                    st.error(f"Erro na API: {response.status_code}")
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

with st.sidebar:
    st.markdown("### 🔍 Contexto Premium")
    if st.button("🔄 Recarregar contexto"):
        compilar_contexto.clear()
        st.rerun()
    with st.expander("Ver Dados Enviados"):
        try:
            st.text(compilar_contexto())
        except Exception as e:
            st.error(f"Erro ao compilar: {e}")