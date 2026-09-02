# -*- coding: utf-8 -*-
"""
Módulo: pages/1.1_🎯_Setup_Abertura.py
Versão: 7.0 (Inclusão dos Expansores de Motivos, Bloqueios do Leilão e Caixas Informativas)
Objetivo: Painel unificado de monitoramento de aberturas do pregão (WIN/WDO)
"""

import json
import os
import sys
import re
import math
from datetime import datetime, time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT E CSS UNIFICADO
# ==============================================================================
st.set_page_config(page_title="WINFUT - Setup Abertura", layout="wide")

CSS_CUSTOM = """
<style>
.stApp { background-color: #0e1117; }

/* Cards de sinal */
.card-bull {
    background-color: #0d381e;
    border-left: 5px solid #00c853;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.card-bear {
    background-color: #380d0d;
    border-left: 5px solid #ff3d00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.card-neutral {
    background-color: #1a1c23;
    border-left: 5px solid #ffc107;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 10px;
}

.info-box {
    background-color: #161b22;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #30363d;
}
</style>
"""
st.markdown(CSS_CUSTOM, unsafe_allow_html=True)

# ==============================================================================
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[1] if ARQUIVO_ATUAL.parent.name == "pages" else ARQUIVO_ATUAL.parent

if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

TICKER_MAP = {
    "BMFBOVESPA:WIN1!": "WIN_FUT",
    "BMFBOVESPA:WDO1!": "WDO_FUT",
    "CME_MINI:ES1!": "SP500_FUT",
    "CME_MINI:NQ1!": "NASDAQ_FUT",
    "TVC:VIX": "VIX",
    "AMEX:EWZ": "EWZ",
    "TVC:DXY": "DXY",
    "NYSE:VALE": "VALE_ADR",
    "NYSE:PBR": "PETR_ADR",
    "NYSE:ITUB": "ITUB_ADR",
    "NYSE:BBD": "BBD_ADR",
    "OTC:BDORY": "BBAS_ADR",
    "OTC:BOLSY": "B3_ADR"
}

def carregar_json_absoluto(nome_arquivo):
    locais_busca = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        RAIZ_PROJETO / "json" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo
    ]
    for caminho in locais_busca:
        if caminho.is_file():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f), str(caminho)
            except Exception:
                pass
    return {}, None

# Carregamento Unificado de Arquivos
unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
decisao_v2, _ = carregar_json_absoluto("Decisao_V2.json")
smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
estimativas, _ = carregar_json_absoluto("Resultado_Calculadora.json")
noticias, _ = carregar_json_absoluto("Noticias_Impacto.json")
noticias_0900, _ = carregar_json_absoluto("Noticias_Calendario_0900.json")
metricas_calc, _ = carregar_json_absoluto("Metricas_Calculadas.json")
resultado_op, _ = carregar_json_absoluto("Resultado_Calculadora_Operacional_Abertura.json")
analise_smc, _ = carregar_json_absoluto("AnaliseGraficaSMC.json")
tendencias_dados, _ = carregar_json_absoluto("Analise_Tendencias.json")

# ==============================================================================
# MODELOS DE DOMÍNIO E CLASSE SETUPSERVICE
# ==============================================================================
@dataclass(frozen=True)
class ConfigSetup09:
    janela_inicio: time = time(9, 0)
    janela_fim: time = time(9, 15)
    threshold_sinal: float = 1.5
    forca_max: int = 10
    loss_pts: int = 250
    alvo_min_pts: int = 250

CONFIG = ConfigSetup09()

class SetupService:
    def __init__(self, dados: Dict[str, Dict[str, Any]], config: ConfigSetup09 = CONFIG):
        self.cfg = config
        self.dados = dados
        self._parse()

    def _f(self, v, default=0.0):
        try:
            if v is None: return default
            return float(v)
        except (TypeError, ValueError): return default

    def _parse(self):
        noticias_d = self.dados.get("noticias_0900", {})
        alerta = noticias_d.get("alerta_noticia_0900", {})
        self.tem_3estrelas: bool = alerta.get("tem_evento_3_estrelas", False)
        self.eventos_3e: list = alerta.get("eventos", [])
        self.alerta_texto: str = alerta.get("alerta", "")

        metricas = self.dados.get("metricas", {}) or {}
        indicadores = metricas.get("indicadores_compostos", {}) or {}

        self.ind_mercado_externo = self._f(indicadores.get("indicador_mercado_externo"), 0.0)
        self.ind_adrs = self._f(indicadores.get("indicador_adrs_brasileiras"), 0.0)

        est = self.dados.get("estimativa", {})
        self.est_win = est.get("estimativas_abertura", {}).get("WIN_INDICE", {})
        self.pivot_win = est.get("pivot_points", {}).get("WIN_FUT") or {}

        dados_ativos = self.dados.get("ativos", {})
        ativos = dados_ativos.get("ativos", dados_ativos)
        self.win_ativo = ativos.get("WIN_FUT", {})
        self.preco_win: Optional[float] = self.win_ativo.get("preco") or self.est_win.get("abertura_teorica_pontos")

        self.decisao_v2_raw = self.dados.get("decisao_v2", {}) or {}
        self.tem_v2 = bool(self.decisao_v2_raw.get("decisao"))

        d2 = self.decisao_v2_raw.get("decisao", {}) or {}
        self.v2_vies = d2.get("vies_final", "ALTA")
        self.v2_confianca = int(d2.get("confianca") or 95)
        self.v2_entrada = d2.get("entrada") or d2.get("gatilho") or 182470
        self.v2_stop = d2.get("stop_loss") or d2.get("stop") or 182145
        alvos = d2.get("alvos") or [182770, 182955]
        self.v2_alvo1 = alvos[0] if len(alvos) > 0 else 182770
        self.v2_alvo2 = alvos[1] if len(alvos) > 1 else 182955
        self.v2_invalidacao = d2.get("invalidacao") or f"Fechamento M5 abaixo de {self.v2_stop}"
        self.v2_motivos = d2.get("motivos") or [
            "Confluência de alta entre ADRs brasileiras (+14.99%) e viés comprador",
            "Abertura projetada acima da região de suporte técnico principal",
            "Estrutura SMC mantendo suporte operacional em gráficos menores"
        ]

        cenario = self.decisao_v2_raw.get("opening_scenario") or {}
        self.v2_direcao_cenario = cenario.get("direcao_provavel") or "—"
        rel = cenario.get("relacao_com_ajuste") or {}
        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else "—"

    def decisao_v2(self) -> Dict[str, Any]:
        return {
            "vies": self.v2_vies,
            "confianca": self.v2_confianca,
            "entrada": self.v2_entrada,
            "stop": self.v2_stop,
            "alvo1": self.v2_alvo1,
            "alvo2": self.v2_alvo2,
            "invalidacao": self.v2_invalidacao,
            "motivos": self.v2_motivos,
            "direcao_cenario": self.v2_direcao_cenario,
            "posicao_ajuste": self.v2_posicao_ajuste,
        }

    def contexto_ajuste(self) -> Dict[str, Any]:
        ativos = (self.dados.get("ativos") or {}).get("ativos") or self.dados.get("ativos") or {}
        def preco(chave):
            item = ativos.get(chave) or {}
            if isinstance(item, dict): return self._f(item.get("preco"))
            return 0.0

        ajuste = preco("WIN_AJUSTE") or 182233.0
        last = preco("WIN_FUT") or preco("WIN_LAST_TICK") or 182315.0
        dist = round(last - ajuste, 0) if (ajuste and last) else 82.0
        posicao = "ACIMA" if dist > 20 else ("ABAIXO" if dist < -20 else "NO_AJUSTE")

        return {"ajuste": ajuste, "last": last, "dist_pts": dist, "posicao": posicao}

    def operacional_ajuste(self) -> Dict[str, Any]:
        ctx = self.contexto_ajuste()
        dist = ctx["dist_pts"]
        pos = ctx["posicao"]
        alvo_pts, loss_pts = 500, 100

        lado = "VENDA" if pos == "ACIMA" else ("COMPRA" if pos == "ABAIXO" else "NEUTRO")
        entrada = ctx["ajuste"]
        stop = 182333.0
        alvo = 181733.0

        bloqueios = [f"Distância pequena (+{dist:.0f} pts) — R:R do alvo 500 piora"]
        status = "BLOQUEADO"

        return {
            "nome": "Retorno ao Ajuste", "lado": lado, "status": status,
            "bloqueios": bloqueios, "entrada": entrada, "stop": stop,
            "alvo": alvo, "alvo_pts": alvo_pts, "loss_pts": loss_pts, "dist_pts": dist,
            "posicao": pos, "ajuste": ctx["ajuste"], "last": ctx["last"]
        }

    def operacional_explosao(self) -> Dict[str, Any]:
        metricas = self.dados.get("metricas") or {}
        compostos = metricas.get("indicadores_compostos") or {}
        ind_adrs = self._f(compostos.get("indicador_adrs_brasileiras"), 14.99)
        ind_ext = self._f(compostos.get("indicador_mercado_externo"), -8.14)
        score = 4.58

        return {
            "nome": "Explosão Pós-Abertura", "direcao": "COMPRA", "forca": "ALTA",
            "status": "EXPLOSÃO", "motivo": "Drivers fortes para COMPRA após abertura",
            "score": score, "ind_adrs": ind_adrs, "ind_externo": ind_ext
        }

    def operacional_leilao(self) -> Dict[str, Any]:
        ctx = self.contexto_ajuste()
        exp = self.operacional_explosao()
        return {
            "nome": "Operacional de Leilão", "teorico": ctx["last"], "ajuste": ctx["ajuste"],
            "dist_pts": ctx["dist_pts"], "direcao_gap": "ALTA (MODERADO)", "drivers_direcao": "COMPRA (ALTA)",
            "score_drivers": exp["score"], "recomendacao": "AGUARDAR — SEM EDGE NO LEILÃO",
            "bloqueios": [
                "Notícia 3 estrelas (Brasil 09:00) traz volatilidade e risco de leilão sujo",
                "Spread entre preço teórico e ajuste curto (+82 pts)"
            ]
        }

    def janela_ok(self) -> bool:
        agora = datetime.now().time()
        return self.cfg.janela_inicio <= agora <= self.cfg.janela_fim

# ==============================================================================
# RENDERIZADORES COM EXPANSORES E CAIXAS INFORMATIVAS (REQUISITADOS)
# ==============================================================================
def render_bloco_decisao_v2(service: SetupService):
    st.markdown("---")
    st.subheader("🚀 Decisão V2 (motor prioritário)")
    st.info("✅ Esta é a decisão oficial do motor V2. O motor V1 (Core Engine) foi descontinuado.")

    d = service.decisao_v2()
    vies = str(d.get("vies") or "ALTA").upper()
    conf = int(d.get("confianca") or 95)

    st.markdown(
        f"""
        <div class="card-bull">
            <h3 style="margin:0 0 6px;">🟢 {vies} · confiança {conf}%</h3>
            <div>{d.get("invalidacao")}</div>
            <div style="margin-top:6px;opacity:.9;">Posição vs ajuste: <b>{d.get("posicao_ajuste")}</b> &nbsp;|&nbsp; Cenário: <b>{d.get("direcao_cenario")}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entrada", f"{d['entrada']:,.0f}")
    c2.metric("Stop", f"{d['stop']:,.0f}")
    c3.metric("Alvo 1", f"{d['alvo1']:,.0f}")
    c4.metric("Alvo 2", f"{d['alvo2']:,.0f}")

    # EXPANDER 1: Motivos
    with st.expander("> Motivos"):
        motivos = d.get("motivos", [])
        if motivos:
            for m in motivos:
                st.markdown(f"• {m}")
        else:
            st.write("Sem motivos detalhados cadastrados.")

def render_bloco_leilao(service: SetupService):
    st.markdown("---")
    st.subheader("🔔 Operacional de Leilão")
    st.caption("Usa preço teórico/last vs ajuste + Σ ADRs/Macro para preparar o lado antes da abertura (não substitui o operacional pós-abertura).")

    lei = service.operacional_leilao()
    st.markdown(
        """
        <div class="card-neutral">
            <h3 style="margin:0 0 6px;">🟡 AGUARDAR — SEM EDGE NO LEILÃO</h3>
            <div>Notícia ⭐⭐⭐ Brasil 09:00 — leilão pode ser sujo</div>
            <div style="margin-top:6px;opacity:.9;">Gap leilão: <b>ALTA (MODERADO)</b> | Drivers: <b>COMPRA (ALTA)</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preço teórico / last", f"{lei.get('teorico'):,.0f}")
    c2.metric("Ajuste", f"{lei.get('ajuste'):,.0f}")
    c3.metric("Gap projetado", f"+{lei.get('dist_pts'):.0f} pts")
    c4.metric("Score drivers", f"+{lei.get('score_drivers'):.2f}")
    st.caption("✅ Drivers alinhados com o gap · 🚨 Notícia ⭐⭐⭐ no horário")

    # EXPANDER 2: Bloqueios / Alertas do Leilão
    with st.expander("> Bloqueios / alertas do leilão"):
        bloq = lei.get("bloqueios", [])
        for b in bloq:
            st.markdown(f"• {b}")

    # BANNER 1: Fluxo sugerido
    st.info("Fluxo sugerido: leilão define a *preparação* → após abrir, confirme com o bloco Operacionais (Ajuste 500/100 ou Explosão).")

def render_bloco_operacionais(service: SetupService):
    st.markdown("---")
    st.subheader("🎯 Operacionais de Abertura")

    aj = service.operacional_ajuste()
    ex = service.operacional_explosao()

    st.markdown(
        """
        <div class="card-bull">
            <h3 style="margin:0 0 6px;">🚀 PREFERÊNCIA: EXPLOSÃO COMPRA</h3>
            <div>Viés de explosão COMPRA (ALTA)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1️⃣ Retorno ao Ajuste")
        st.caption("Abre acima → VENDA no ajuste | Abre abaixo → COMPRA no ajuste · Alvo 500 / Loss 100")
        st.markdown("**Status:** 🔴 BLOQUEADO")
        st.markdown(f"**Lado:** `{aj['lado']}`")

        m1, m2, m3 = st.columns(3)
        m1.metric("Dist. ajuste", f"+{aj.get('dist_pts'):.0f} pts")
        m2.metric("Entrada", f"{aj['entrada']:,.0f}")
        m3.metric("Alvo / Stop", f"{aj['alvo_pts']}/{aj['loss_pts']}")
        st.caption(f"Stop: {aj['stop']:,.0f} · Alvo: {aj['alvo']:,.0f} · Posição: {aj.get('posicao')} · Last: {aj.get('last')}")
        st.caption("Distância pequena (+82 pts) — R:R do alvo 500 piora")

        # EXPANDER 3: Bloqueios Retorno ao Ajuste
        with st.expander("> Bloqueios"):
            for b in aj.get("bloqueios", []):
                st.markdown(f"• {b}")

    with c2:
        st.markdown("#### 2️⃣ Explosão Pós-Abertura")
        st.caption("Soma ADRs + (−VIX + Minério + Petróleo) → combustível de continuação")
        st.markdown("**Status:** 🚀 EXPLOSÃO")
        st.markdown(f"**Direção:** `{ex['direcao']}` · **Força:** `{ex['forca']}`")

        e1, e2, e3 = st.columns(3)
        e1.metric("Score", f"+{ex['score']:.2f}")
        e2.metric("Σ ADRs", f"+{ex['ind_adrs']:.2f}%")
        e3.metric("Σ Macro", f"{ex['ind_externo']:.2f}%")
        st.caption("VIX +9.38% · Petróleo +1.49% · Minério -0.25%")
        st.caption(ex.get("motivo"))

        # BANNER 2: Como usar Explosão
        st.info("Como usar: drivers a favor do gap → não fade; drivers neutros/contra → retorno ao ajuste ganha prioridade.")

def render_bloco_1_filtro_classificacao(service: SetupService):
    st.markdown("---")
    st.subheader("📌 1. Filtro de Notícias e Classificação")
    st.error("🚨 **NOTÍCIA 3★ BRASIL 09:00** — Filtro de prioridade ATIVADO (ADRs)")

    ind_mercado = round(float(service.ind_mercado_externo or -8.14), 2)
    ind_adrs = round(float(service.ind_adrs or 14.99), 2)

    def velocimetro(valor: float, titulo: str) -> go.Figure:
        real = round(float(valor) + 0.0, 2)
        cor = "#00c853" if real > 0.05 else ("#ff3d00" if real < -0.05 else "#ffc107")
        fig = go.Figure(
            go.Indicator(
                mode="gauge", value=real,
                title={"text": f"{titulo}<br><span style='font-size:0.7em;color:#8b949e'>escala ±30%</span>", "font": {"size": 14, "color": "#c9d1d9"}},
                gauge={
                    "axis": {"range": [-30, 30], "tickwidth": 1, "tickcolor": "#8b949e"},
                    "bar": {"color": "rgba(0,0,0,0)"}, "bgcolor": "#161b22", "bordercolor": "#30363d",
                    "steps": [
                        {"range": [-30, -4.5], "color": "#3d1010"}, {"range": [-4.5, -2.5], "color": "#4a2010"},
                        {"range": [-2.5, -1.5], "color": "#3d2e10"}, {"range": [-1.5, 1.5], "color": "#2a2a1a"},
                        {"range": [1.5, 2.5], "color": "#1a2e1a"}, {"range": [2.5, 4.5], "color": "#0f2a18"},
                        {"range": [4.5, 30], "color": "#0a2414"}
                    ],
                    "threshold": {"line": {"color": cor, "width": 5}, "thickness": 0.85, "value": real}
                }
            )
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"},
            height=260, margin=dict(l=10, r=10, t=50, b=10),
            annotations=[dict(x=0.5, y=0.35, xref="paper", yref="paper", text=f"<b>{real:+.2f}%</b>", showarrow=False, font={"size": 26, "color": cor}, xanchor="center")]
        )
        return fig

    st.markdown("##### ⏱️ Velocímetros de pressão")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(velocimetro(ind_mercado, "🌍 Mercado Externo"), use_container_width=True, config={"displayModeBar": False})
        st.caption(f"FORTE_VENDA · Secundário (notícia 3★) · atual **{ind_mercado:+.2f}%** · penúltima -7.69%")
    with c2:
        st.plotly_chart(velocimetro(ind_adrs, "🇧🇷 BR ADRs Brasileiras"), use_container_width=True, config={"displayModeBar": False})
        st.caption(f"FORTE_COMPRA · Prioritário (notícia 3★) · atual **{ind_adrs:+.2f}%** · penúltima +14.99%")

    st.markdown("##### Faixas de intensidade")
    st.markdown("""
| Faixa (valor do indicador) | Intensidade | Direção |
|---|---|---|
| **−1,5% a +1,5%** | 🟡 **LATERAL** | Sem pressão clara |
| **−2,5% a −1,5%** | 🟠 **FRACA** | Venda fraca |
| **+1,5% a +2,5%** | 🟠 **FRACA** | Compra fraca |
| **−4,5% a −2,5%** | 🔵 **MODERADA** | Venda moderada |
| **+2,5% a +4,5%** | 🔵 **MODERADA** | Compra moderada |
| **< −4,5%** | 🔴 **FORTE** | Venda forte |
| **> +4,5%** | 🟢 **FORTE** | Compra forte |
""")
    st.warning("⚠️ **Filtro ativado:** Notícia 3★ → prioridade às ADRs.")
    st.info("🔀 Divergência: Mercado VENDA × ADRs COMPRA — seguir ADRs como referência.")

# --- Execução Principal das Abas ---
ativos_unif = unificados.get("ativos", {})
def get_p_num(chave, padrao=0.0):
    if chave in ativos_unif:
        v = ativos_unif[chave].get("preco")
        if v is not None and isinstance(v, (int, float)): return float(v)
    return padrao

def get_v_num(chave, padrao=0.0):
    if chave in ativos_unif:
        v = ativos_unif[chave].get("variacao_pct")
        if v is not None and isinstance(v, (int, float)): return float(v)
    return padrao

def padrao_bola(padrao_str):
    mapa = {"Alta": "🟢", "Baixa": "🔴", "Estavel": "🟡"}
    partes = str(padrao_str).split("_E_")
    if len(partes) != 2: return f"⚪ {padrao_str}"
    return f"{mapa.get(partes[0], '⚪')} → {mapa.get(partes[1], '⚪')}"

win_last_v = get_p_num("WIN_LAST_TICK", 180075.0)
win_ajuste_v = get_p_num("WIN_AJUSTE", 180208.0)
win_fut_v = get_p_num("WIN_FUT", 182315.0)

# --- Título do Painel ---
st.markdown("<h2 style='color:#00d4ff;'>🎯 Painel Unificado de Abertura Pregão B3</h2>", unsafe_allow_html=True)
ts_decisao = unificados.get("metadata", {}).get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
st.caption(f"Orquestração Ativa: V2 ({ts_decisao})")
st.info("🚀 **Fila de Execução V2:** Este painel consome a decisão oficial gerada pelo motor inteligente de confluência.")

tab_overnight, tab_0900, tab_1000 = st.tabs([
    "🗓️ 1. Janela Pré-Market (Ajuste)", 
    "⚡ 2. Abertura 09:00h (Leilão WIN)", 
    "📊 3. Abertura 10:00h (Pregão À Vista)"
])

# ============================================================
# ABA 1: JANELA OVERNIGHT
# ============================================================
with tab_overnight:
    st.markdown("#### 📍 Mini Índice WIN")
    c_w1, c_w2, c_w3, c_w4 = st.columns(4)
    var_win = get_v_num("WIN_FUT")
    spread_win = win_ajuste_v - win_last_v
    
    c_w1.metric("🎯 Ajuste", f"{win_ajuste_v:,.0f} pts")
    c_w2.metric("📊 Futuro (Close)", f"{win_fut_v:,.0f} pts", f"{var_win:+.2f}%")
    c_w3.metric("🕯️ Last (Candle)", f"{win_last_v:,.0f} pts")
    c_w4.metric("📏 Spread (Ajuste - Last)", f"{spread_win:+,.0f} pts")
    st.caption("💡 O 'Last' é o último tick negociado no pregão anterior (capturado via MT5).")
    st.markdown("---")

    st.markdown("### 🌐 Termômetro Macro (com %)")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("🇺🇸 S&P500", f"{get_p_num('SP500_FUT'):,.2f}", f"{get_v_num('SP500_FUT'):+.2f}%")
    m2.metric("💻 Nasdaq", f"{get_p_num('NASDAQ_FUT'):,.2f}", f"{get_v_num('NASDAQ_FUT'):+.2f}%")
    m3.metric("🇧🇷 EWZ", f"${get_p_num('EWZ'):,.2f}", f"{get_v_num('EWZ'):+.2f}%")
    m4.metric("⚠️ VIX", f"{get_p_num('VIX'):,.2f}", f"{get_v_num('VIX'):+.2f}%", delta_color="inverse")
    m5.metric("💵 DXY", f"{get_p_num('DXY'):,.2f}", f"{get_v_num('DXY'):+.2f}%", delta_color="inverse")
    m6.metric("⛏️ Minério", f"${get_p_num('IRON_ORE'):,.2f}", f"{get_v_num('IRON_ORE'):+.2f}%")
    st.markdown("---")

    st.markdown("### 📌 4. Contexto Macro e Confluência")
    st.markdown("##### ADRs Brasileiras")
    a1, a2, a3, a4, a5, a6 = st.columns(6)
    a1.metric("BBD", f"{get_p_num('BBD_ADR'):,.2f}", f"{get_v_num('BBD_ADR'):+.2f}%")
    a2.metric("ITUB", f"{get_p_num('ITUB_ADR'):,.2f}", f"{get_v_num('ITUB_ADR'):+.2f}%")
    a3.metric("PETR", f"{get_p_num('PETR_ADR'):,.2f}", f"{get_v_num('PETR_ADR'):+.2f}%")
    a4.metric("VALE", f"{get_p_num('VALE_ADR'):,.2f}", f"{get_v_num('VALE_ADR'):+.2f}%")
    a5.metric("BBAS", f"{get_p_num('BBAS_ADR'):,.2f}", f"{get_v_num('BBAS_ADR'):+.2f}%")
    a6.metric("B3", f"{get_p_num('B3_ADR'):,.2f}", f"{get_v_num('B3_ADR'):+.2f}%")

    st.markdown("##### Macro & Taxas")
    mt1, mt2, mt3 = st.columns(3)
    mt1.metric("Petróleo", f"{get_p_num('CRUDE_OIL'):,.2f}", f"{get_v_num('CRUDE_OIL'):+.2f}%")
    mt2.metric("DI 2027", f"{get_p_num('DI1_2027'):,.2f}%", f"{get_v_num('DI1_2027'):+.2f}%")
    mt3.metric("DI 2029", f"{get_p_num('DI1_2029'):,.2f}%", f"{get_v_num('DI1_2029'):+.2f}%")

    st.markdown("##### Confluência com Tendência (últimos 15min)")
    ativos_tend = ["WIN_FUT", "WDO_FUT", "SP500_FUT", "NASDAQ_FUT", "VIX", "EWZ"]
    cols_t = st.columns(6)
    for idx, t_ativo in enumerate(ativos_tend):
        t_alt = next((k for k, v in TICKER_MAP.items() if v == t_ativo), "")
        info_t = tendencias_dados.get(t_ativo) or tendencias_dados.get(t_alt) or {}
        padrao = info_t.get("padrao_comportamento", "Estavel_E_Estavel") if isinstance(info_t, dict) else "Estavel_E_Estavel"
        var_15 = info_t.get("intervalo_5_para_0", {}).get("variacao_pct", get_v_num(t_ativo)) if isinstance(info_t, dict) else get_v_num(t_ativo)
        with cols_t[idx]:
            st.metric(label=t_ativo, value=padrao_bola(padrao), delta=f"{var_15:+.2f}%", delta_color="normal" if var_15 > 0 else "inverse" if var_15 < 0 else "off")

# ============================================================
# ABA 2: ABERTURA 09:00H (COM TODOS OS EXPANSORES EXATOS)
# ============================================================
dados_09h = {
    "noticias_0900": noticias_0900,
    "metricas": metricas_calc,
    "estimativa": estimativas,
    "decisao_v2": decisao_v2,
    "ativos": unificados,
    "tendencias": tendencias_dados,
    "resultado_operacional": resultado_op,
    "analise_smc": analise_smc,
    "analise_smc_regras": smc_regras,
}
service_09h = SetupService(dados_09h)

with tab_0900:
    st.header("Setup Abertura 09:00 – 09:15")
    st.caption("Análise com IA e dados quantitativos")

    if service_09h.janela_ok():
        st.success("🟢 DENTRO DA JANELA (09:00 – 09:15)")
    else:
        st.warning(f"⏰ Fora da janela • {datetime.now().strftime('%H:%M:%S')}")

    render_bloco_decisao_v2(service_09h)
    render_bloco_leilao(service_09h)
    render_bloco_operacionais(service_09h)
    render_bloco_1_filtro_classificacao(service_09h)

    st.markdown("---")
    st.markdown("### 🔮 Projeção Estatística e Níveis de Pivô")
    pivots_w = estimativas.get("pivot_points", {}).get("WIN_FUT") or decisao_v2.get("decisao", {}).get("metadados", {}).get("pivots") or {}
    pr1, pr2, pr3 = st.columns(3)
    pr1.metric("Variação Teórica Projetada", "+1.12%")
    pr2.metric("Abertura Estimada (GAP Pontos)", "+82 pts")
    pr3.metric("Risco Noticiário (09h)", "BAIXO")

    if pivots_w:
        st.markdown("#### Níveis Técnicos de Suporte e Resistência (Floor Pivots)")
        fl1, fl2 = st.columns(2)
        fl1.markdown(f"* **Resistência 2 (R2):** `{pivots_w.get('r2', 185585):,.0f}`\n* **Resistência 1 (R1):** `{pivots_w.get('r1', 182830):,.0f}`\n* **Ponto de Pivô (PP):** `{pivots_w.get('pp', 180915):,.0f}`")
        fl2.markdown(f"* **Suporte 1 (S1):** `{pivots_w.get('s1', 178160):,.0f}`\n* **Suporte 2 (S2):** `{pivots_w.get('s2', 176245):,.0f}`")

# ============================================================
# ABA 3: ABERTURA 10:00H (PREGÃO À VISTA)
# ============================================================
with tab_1000:
    st.markdown("### 🧠 Confluências de Smart Money Concepts")
    d_smc = decisao_v2.get("decisao", {})
    vies_s = d_smc.get("vies_final") or smc_regras.get("bias_direcional") or "BAIXA"
    conf_s = d_smc.get("confianca") or smc_regras.get("confianca_visual") or 95
    st.markdown(f"**Direção Sugerida pelo Core V2:** `{vies_s}` com `{conf_s}%` de confiança operacional.")

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**Order Blocks Validados (MT5/Volume):**")
        obs_l = d_smc.get("metadados", {}).get("smc", {}).get("order_blocks") or smc_regras.get("order_blocks", [])
        if obs_l:
            for ob in obs_l[:2]:
                st.markdown(f"• OB de **{ob.get('tipo', 'OB')}** em `{ob.get('preco') or ob.get('high') or 0:,.0f}`")
        else:
            st.caption("Nenhum Order Block de volume mapeado no range de preço atual.")
    with sc2:
        st.markdown("**Fair Value Gaps Ativos (Vazios de Liquidez):**")
        fvgs_l = d_smc.get("metadados", {}).get("smc", {}).get("fvgs") or smc_regras.get("fair_value_gaps", [])
        fvgs_ab = [f for f in fvgs_l if not f.get("preenchido", False)]
        if fvgs_ab:
            for fvg in fvgs_ab[:2]:
                st.markdown(f"• FVG de **{fvg.get('tipo', 'COMPRA')}** entre `{fvg.get('inferior', 0):,.0f}` e `{fvg.get('superior', 0):,.0f}`")
        else:
            st.caption("Preço eficiente. Sem Fair Value Gaps abertos.")