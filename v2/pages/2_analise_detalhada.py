# -*- coding: utf-8 -*-
"""
Módulo: v2/pages/2_analise_detalhada.py
Versão: 3.0 - Refatorado para o schema V3.2-VisaoC do orquestrador
Objetivo: Detalhar contextos, pesos e indicadores que geraram a Decisão V2.

Mudanças da v2.0 → v3.0:
  - Lê DadosAtivosUnificados.json para dados brutos (S&P, VIX, ADRs)
  - Lê Metricas_Calculadas.json para indicadores compostos e curva DI
  - Lê EstimativaAbertura.json para var teórica e cost of carry
  - Consome novo schema do Decisao_V2.json (metadados.novo_motor)
  - Auto-refresh via @st.fragment(run_every=60)
  - Fallbacks defensivos para todos os campos
"""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from config import (
    COLETAS_DIR,
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_METRICAS,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_TENDENCIAS,
)


# ==============================================================================
# LOADERS DEFENSIVOS
# ==============================================================================
def carregar_json(caminho) -> dict:
    if not caminho or not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _f(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _snapshot(ativos: dict, chave: str) -> dict:
    item = ativos.get(chave) or {}
    if not isinstance(item, dict):
        return {"preco": 0.0, "var": 0.0}
    return {
        "preco": _f(item.get("preco")),
        "var": _f(item.get("variacao_pct")),
    }


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - Análise Detalhada", layout="wide")


# ==============================================================================
# CORPO (auto-refresh 60s)
# ==============================================================================
@st.fragment(run_every=60)
def render_body():
    # ---- Carga ----
    dados_v2 = carregar_json(FILE_DECISAO_V2)
    unificado = carregar_json(FILE_UNIFICADO)
    metricas = carregar_json(FILE_METRICAS)
    estimativa = carregar_json(FILE_ESTIMATIVA_ABERTURA)
    tendencias = carregar_json(FILE_TENDENCIAS)

    # ---- Cabeçalho ----
    st.markdown(
        "<h2 style='color:#00d4ff;'>🔬 Diagnóstico e Análise Detalhada da Decisão</h2>",
        unsafe_allow_html=True,
    )
    ts = dados_v2.get("metadata", {}).get("timestamp", "N/A")
    st.caption(
        f"Detalhamento completo de pesos e scores contextuais · "
        f"Snapshot V2: {ts} · 🔄 {datetime.now().strftime('%H:%M:%S')}"
    )

    if not dados_v2:
        st.error("❌ Arquivo `Decisao_V2.json` ausente. Rode o pipeline.")
        st.stop()

    decisao = dados_v2.get("decisao", {}) or {}
    meta = decisao.get("metadados", {}) or {}
    novo_motor = meta.get("novo_motor", {}) or {}
    ativos = (unificado.get("ativos", {}) or {}) if isinstance(unificado, dict) else {}

    # ====================================================================
    # SEÇÃO 1 — RESUMO DO CENÁRIO
    # ====================================================================
    st.markdown("### 🗺️ Cenário Macroeconômico e Estrutural")

    c1, c2, c3, c4 = st.columns(4)

    vies = decisao.get("vies_final") or "NEUTRO"
    conf = decisao.get("confianca") or 0

    direcao_gap = novo_motor.get("direcao") or "NEUTRO"
    gap_pts = _f(novo_motor.get("gap_pontos"))
    gap_pct = _f(novo_motor.get("gap_pct"))
    gap_intens = novo_motor.get("gap_intensidade") or "—"

    fonte_ab = novo_motor.get("fonte_abertura") or "—"

    c1.metric("Viés Final V2", vies, delta=f"{conf}% confiança")
    c2.metric("Direção do Gap", direcao_gap, delta=f"{gap_pts:+.0f} pts")
    c3.metric("Intensidade do Gap", gap_intens, delta=f"{gap_pct:+.4f}%")
    c4.metric("Fonte da Abertura", fonte_ab)

    # Comportamento / aviso
    div_flag = novo_motor.get("divergencia_direcao", False)
    div_msg = novo_motor.get("divergencia_detalhes", "")
    if div_flag:
        st.warning(f"⚠️ **Divergência interna do motor:** {div_msg}")
    else:
        cenario_nome = novo_motor.get("cenario_principal_nome") or "—"
        cenario_desc = novo_motor.get("cenario_desc") or "Aguardando dados..."
        st.info(f"📋 **Cenário principal:** `{cenario_nome}` — {cenario_desc}")

    st.markdown("---")

    # ====================================================================
    # SEÇÃO 2 — COMPONENTES DO CÁLCULO (3 colunas)
    # ====================================================================
    st.markdown("### 🧩 Componentes do Cálculo Ponderado V2")

    col_global, col_juros, col_adrs = st.columns(3)

    # ---- Bloco A: Drivers Globais ----
    with col_global:
        st.markdown("#### 🌐 Drivers Globais & Commodities")
        sp = _snapshot(ativos, "SP500_FUT")
        nq = _snapshot(ativos, "NASDAQ_FUT")
        oil = _snapshot(ativos, "CRUDE_OIL")
        iron = _snapshot(ativos, "IRON_ORE_2M") if _snapshot(ativos, "IRON_ORE_2M")["preco"] > 0 else _snapshot(ativos, "IRON_ORE")
        vix = _snapshot(ativos, "VIX")

        linhas = [
            {"Indicador": "S&P 500 Futuro", "Preço/Taxa": f"{sp['preco']:,.2f}", "Variação": f"{sp['var']:+.2f}%"},
            {"Indicador": "Nasdaq Futuro", "Preço/Taxa": f"{nq['preco']:,.2f}", "Variação": f"{nq['var']:+.2f}%"},
            {"Indicador": "Petróleo Crude Oil", "Preço/Taxa": f"US$ {oil['preco']:,.2f}", "Variação": f"{oil['var']:+.2f}%"},
            {"Indicador": "Minério de Ferro", "Preço/Taxa": f"US$ {iron['preco']:,.2f}", "Variação": f"{iron['var']:+.2f}%"},
            {"Indicador": "VIX (Volatilidade)", "Preço/Taxa": f"{vix['preco']:,.2f}", "Variação": f"{vix['var']:+.2f}%"},
        ]
        st.table(pd.DataFrame(linhas).set_index("Indicador"))

    # ---- Bloco B: Curva de Juros e Câmbio ----
    with col_juros:
        st.markdown("#### 📉 Curva de Juros e Câmbio")
        dxy = _snapshot(ativos, "DXY")
        usdbrl = _snapshot(ativos, "USD_BRL")
        ptax = _snapshot(ativos, "USD_PTAX")
        di27 = _snapshot(ativos, "DI1_2027")
        di29 = _snapshot(ativos, "DI1_2029")

        # Inclinação da curva (do metricas)
        inclin = metricas.get("curva_juros_b3", {}).get("inclinacao_29_27_bps") if metricas else None

        linhas = [
            {"Indicador": "Índice DXY (Dólar Global)", "Preço/Taxa": f"{dxy['preco']:,.3f}", "Variação": f"{dxy['var']:+.2f}%"},
            {"Indicador": "USD/BRL Spot (TV)", "Preço/Taxa": f"R$ {usdbrl['preco']:,.4f}", "Variação": f"{usdbrl['var']:+.2f}%"},
            {"Indicador": "USD PTAX Oficial", "Preço/Taxa": f"R$ {ptax['preco']:,.4f}", "Variação": "—"},
            {"Indicador": "DI1 Futuro 2027", "Preço/Taxa": f"{di27['preco']:,.2f}%", "Variação": f"{di27['var']:+.2f}%"},
            {"Indicador": "DI1 Futuro 2029", "Preço/Taxa": f"{di29['preco']:,.2f}%", "Variação": f"{di29['var']:+.2f}%"},
            {"Indicador": "Inclinação da Curva", "Preço/Taxa": f"{_f(inclin):+.1f} bps" if inclin is not None else "—", "Variação": "—"},
        ]
        st.table(pd.DataFrame(linhas).set_index("Indicador"))

    # ---- Bloco C: ADRs ----
    with col_adrs:
        st.markdown("#### 🏢 Performance de ADRs em NY")
        vale = _snapshot(ativos, "VALE_ADR")
        petr = _snapshot(ativos, "PETR_ADR")
        itub = _snapshot(ativos, "ITUB_ADR")
        bbd = _snapshot(ativos, "BBD_ADR")
        bbas = _snapshot(ativos, "BBAS_ADR")

        linhas = [
            {"ADR": "VALE", "Cotação": f"US$ {vale['preco']:,.2f}", "Variação": f"{vale['var']:+.2f}%"},
            {"ADR": "PBR (Petrobras)", "Cotação": f"US$ {petr['preco']:,.2f}", "Variação": f"{petr['var']:+.2f}%"},
            {"ADR": "ITUB (Itaú)", "Cotação": f"US$ {itub['preco']:,.2f}", "Variação": f"{itub['var']:+.2f}%"},
            {"ADR": "BBD (Bradesco)", "Cotação": f"US$ {bbd['preco']:,.2f}", "Variação": f"{bbd['var']:+.2f}%"},
            {"ADR": "BDORY (BB)", "Cotação": f"US$ {bbas['preco']:,.2f}", "Variação": f"{bbas['var']:+.2f}%"},
        ]
        st.table(pd.DataFrame(linhas).set_index("ADR"))

    st.markdown("---")

    # ====================================================================
    # SEÇÃO 3 — INDICADORES COMPOSTOS + VAR TEÓRICA
    # ====================================================================
    st.markdown("### 📊 Indicadores Compostos e Precificação")

    ind = metricas.get("indicadores_compostos", {}) if metricas else {}
    ind_ext = _f(ind.get("indicador_mercado_externo"))
    ind_adrs = _f(ind.get("indicador_adrs_brasileiras"))

    est_win = estimativa.get("estimativa_abertura", {}).get("WIN_INDICE", {}) if estimativa else {}
    var_teor = _f(est_win.get("variacao_teorica_pct"))
    abertura_teor = _f(est_win.get("abertura_teorica_pontos"))
    preco_carregado = _f((est_win.get("cost_of_carry") or {}).get("preco_teorico_carregado"))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Σ Mercado Externo", f"{ind_ext:+.2f}%")
    k2.metric("Σ ADRs Brasileiras", f"{ind_adrs:+.2f}%")
    k3.metric("Variação Teórica WIN", f"{var_teor:+.4f}%")
    k4.metric("Abertura Teórica WIN", f"{abertura_teor:,.0f} pts")

    with st.expander("🏦 Referências de Tesouraria (SMC + Cost of Carry)"):
        smc_meta = meta.get("smc", {}) or {}
        preco_carregado_meta = meta.get("precificacao_teorica", {}).get("preco_carregado_di") if meta.get("precificacao_teorica") else None

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("POC Ontem", f"{_f(smc_meta.get('poc_ontem')):,.0f} pts")
        t2.metric("VWAP Ontem", f"{_f(smc_meta.get('vwap_ontem')):,.1f} pts")
        t3.metric("Preço Carregado (DI/252)", f"{_f(preco_carregado_meta or preco_carregado):,.0f} pts")
        ob_alinhado = smc_meta.get("ob_alinhado_com_poc")
        t4.metric("OB Alinhado com POC", "🟢 SIM" if ob_alinhado else "⚪ NÃO")

        pivots = meta.get("pivots", {}) or {}
        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("R2", f"{_f(pivots.get('r2')):,.0f}")
        p2.metric("R1", f"{_f(pivots.get('r1')):,.0f}")
        p3.metric("PP", f"{_f(pivots.get('pp')):,.0f}")
        p4.metric("S1", f"{_f(pivots.get('s1')):,.0f}")
        p5.metric("S2", f"{_f(pivots.get('s2')):,.0f}")

    st.markdown("---")

    # ====================================================================
    # SEÇÃO 4 — CONFLUÊNCIA E ARGUMENTOS
    # ====================================================================
    st.markdown("### 🗳️ Matriz de Confluência e Argumentos do Orquestrador")

    col_mot, col_risc = st.columns(2)

    with col_mot:
        st.markdown("**Fatores de Confluência Encontrados (motivos):**")
        motivos = decisao.get("motivos", []) or []
        if motivos:
            for m in motivos:
                st.markdown(f"• {m}")
        else:
            st.caption("Sem motivos detalhados registrados neste ciclo.")

    with col_risc:
        st.markdown("**Trava de Risco (alertas ativos):**")
        riscos = decisao.get("riscos", []) or []
        if riscos:
            for r in riscos:
                st.markdown(f"❌ {r}")
        else:
            st.success("🟢 Nenhuma trava ativa neste ciclo.")

    # ---- Detalhes do NOVO_MOTOR ----
    with st.expander("🤖 Detalhes do NOVO_MOTOR (abertura + divergência + score)"):
        if novo_motor:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Score Magnitude", f"{_f(novo_motor.get('score_magnitude')):.1f}")
            m2.metric("Score Força", novo_motor.get("score_forca") or "—")
            m3.metric("Score Direção", novo_motor.get("score_direcao") or "—")
            m4.metric("Divergência", "⚠️ SIM" if novo_motor.get("divergencia_direcao") else "🟢 NÃO")

            n1, n2, n3, n4 = st.columns(4)
            n1.metric("Abertura Projetada", f"{_f(novo_motor.get('abertura_projetada')):,.0f}")
            n2.metric("Faixa Inferior", f"{_f(novo_motor.get('faixa_inf')):,.0f}")
            n3.metric("Faixa Superior", f"{_f(novo_motor.get('faixa_sup')):,.0f}")
            n4.metric("Abertura Leilão Real", f"{_f(novo_motor.get('abertura_leilao_real')):,.0f}" if novo_motor.get("abertura_leilao_real") else "—")

            if novo_motor.get("divergencia_detalhes"):
                st.warning(novo_motor["divergencia_detalhes"])

    # ---- Status dos contextos ----
    with st.expander("⚙️ Status dos 5 Contextos Operacionais"):
        ctx = dados_v2.get("contextos", {}) or {}
        c1, c2, c3, c4, c5 = st.columns(5)
        _status = lambda ok: "🟢 OK" if ok else "🔴 FALHOU"
        c1.metric("Market", _status(ctx.get("market_ok")))
        c2.metric("Prediction", _status(ctx.get("prediction_ok")))
        c3.metric("News", _status(ctx.get("news_ok")))
        c4.metric("Vision", _status(ctx.get("vision_ok")))
        c5.metric("Session", _status(ctx.get("session_ok")))

    # ---- Erros acumulados ----
    erros = dados_v2.get("erros", []) or []
    if erros:
        with st.expander(f"⚠️ Avisos do orquestrador ({len(erros)})"):
            for e in erros:
                st.markdown(f"• {e}")

    st.markdown("---")
    st.caption("🔒 Terminal de Produção V2 — dados consolidados de múltiplas fontes (DadosAtivosUnificados, Metricas_Calculadas, Decisao_V2, EstimativaAbertura).")


render_body()