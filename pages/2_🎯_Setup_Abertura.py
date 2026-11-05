# -*- coding: utf-8 -*-
"""
Módulo: pages/2_🎯_Setup_Abertura.py
Versão: 9.6 (Coleta Dupla: Pré/Pós + Diário nos Filtros de Pressão)
Objetivo: Painel unificado de monitoramento de aberturas do pregão (WIN/WDO)
"""

import json
import logging
import os
import sys
import re
import math
from datetime import datetime, time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd
from config import MAPEAMENTO_TICKERS, MAPEAMENTO_TICKERS_INVERSO, ADRS_COMPOSTO

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT E CSS UNIFICADO
# ==============================================================================
st.set_page_config(page_title="WINFUT - Setup Abertura", layout="wide")

CSS_CUSTOM = """
<style>
.stApp { background-color: #0e1117; }
.card-bull { background-color: #0d381e; border-left: 5px solid #00c853; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
.card-bear { background-color: #380d0d; border-left: 5px solid #ff3d00; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
.card-neutral { background-color: #1a1c23; border-left: 5px solid #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
.info-box { background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
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

def carregar_json_absoluto(nome_arquivo):
    locais_busca = [
        RAIZ_PROJETO / nome_arquivo, RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo, RAIZ_PROJETO / "json" / nome_arquivo,
        Path.cwd() / nome_arquivo, Path.cwd() / "Coletas" / nome_arquivo,
    ]
    for caminho in locais_busca:
        if caminho.is_file():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f), str(caminho)
            except Exception as e:
                logger.warning("[SETUP_ABERTURA] Falha lendo JSON %s: %s", caminho, e)
    return {}, None

@st.cache_data(ttl=2)
def carregar_rom5() -> dict:
    for path in [RAIZ_PROJETO / "Coletas" / "Coleta_rom-5.json",
                 RAIZ_PROJETO / "Coleta_rom-5.json",
                 Path.cwd() / "Coletas" / "Coleta_rom-5.json"]:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f: return json.load(f)
            except Exception: return {}
    return {}

def _get_var_rom5(rom5: dict, chave_interna: str) -> Optional[float]:
    if not rom5: return None
    ticker = MAPEAMENTO_TICKERS_INVERSO.get(chave_interna, chave_interna)
    for item in rom5.get("coletas", []):
        if item.get("ativo") == ticker:
            val = (item.get("dados_reais") or {}).get("change_percent")
            if isinstance(val, (int, float)): return float(val)
    return None

def calcular_ind_adrs_rom5(rom5: dict) -> Optional[float]:
    vals = [_get_var_rom5(rom5, adr) for adr in ADRS_COMPOSTO]
    vals = [v for v in vals if v is not None]
    return round(sum(vals), 4) if vals else None

def calcular_ind_externo_rom5(rom5: dict) -> Optional[float]:
    vix = _get_var_rom5(rom5, "VIX")
    crude = _get_var_rom5(rom5, "CRUDE_OIL")
    iron = _get_var_rom5(rom5, "IRON_ORE")
    if vix is None or crude is None or iron is None: return None
    return round(-vix + crude + iron, 4)

# ==============================================================================
# MINI VELOCÍMETRO
# ==============================================================================
def mini_velocimetro(
    valor: Optional[float], label: str, preco_fmt: str = "", inverter: bool = False,
    valor_anterior: Optional[float] = None, escala: float = 1.0, range_max: float = 10.0,
    var_diaria: Optional[float] = None
) -> None:
    valor_real = None
    if valor is None:
        real_exibicao = 0.0; cor = "#8b949e"; texto_valor = "—"
    else:
        try: valor_real = float(valor)
        except (TypeError, ValueError): valor_real = None
        if valor_real is None:
            real_exibicao = 0.0; cor = "#8b949e"; texto_valor = "—"
        else:
            real_exibicao = max(-range_max, min(range_max, valor_real))
            real_cor = -real_exibicao if inverter else real_exibicao
            if real_cor > 0.05: cor = "#00cc44"
            elif real_cor < -0.05: cor = "#ff4b4b"
            else: cor = "#ffa500"
            texto_valor = f"{valor_real:+.2f}%"

    svg_anterior = ""; texto_delta = ""
    if valor_anterior is not None and valor_real is not None:
        try:
            real_ant = max(-range_max, min(range_max, float(valor_anterior)))
            angulo_ant = (real_ant / range_max) * 90.0
            svg_anterior = (
                f'<svg class="mini-needle-ant" style="transform: rotate({angulo_ant}deg);" viewBox="0 0 14 58">'
                f'<path d="M 7 0 L 9.5 46 L 4.5 46 Z" fill="rgba(220, 220, 255, 0.85)"/></svg>'
            )
            delta = valor_real - float(valor_anterior)
            texto_delta = "Δ 0.00%" if abs(delta) < 0.005 else f"Δ {delta:+.2f}%"
        except (TypeError, ValueError) as e:
            logger.warning("[SETUP_ABERTURA] Falha calculando delta '%s': %s", label, e)

    # Texto do Diário
    texto_diaria = ""
    if var_diaria is not None:
        texto_diaria = f'<div class="mini-daily">Diário: {var_diaria:+.2f}%</div>'

    angulo = (real_exibicao / range_max) * 90.0
    s = max(0.5, float(escala))
    gauge_w = 120*s; gauge_h = 62*s; arc_left = 5*s; arc_top = 3*s; arc_w = 110*s; arc_h = 55*s
    arc_mask_inner = 34*s; arc_mask_outer = 35*s; needle_w = 8*s; needle_h = 52*s; needle_margin = -4*s
    needle_ant_w = 14*s; needle_ant_h = 48*s; needle_ant_margin = -7*s
    pivot_w = 12*s; pivot_h = 12*s; pivot_margin = -6*s
    label_fs = 11*s; value_fs = 14*s; delta_fs = 10*s; sub_fs = 10*s
    value_mt = 4*s; delta_mt = 3*s; sub_mt = 2*s
    altura_widget = int(155*s) if s <= 1.5 else int(150*s + 30)
    
    if var_diaria is not None:
        altura_widget += 15

    html = f"""
    <!DOCTYPE html><html><head><style>
        html, body {{ margin: 0; padding: 0; background: transparent; font-family: Arial, sans-serif; color: #e6edf3; overflow: hidden; }}
        .mini-wrap {{ display: flex; flex-direction: column; align-items: center; padding: {2*s}px 0; }}
        .mini-label {{ font-size: {label_fs}px; color: #c9d1d9; margin-bottom: {1*s}px; text-align: center; font-weight: 700; white-space: nowrap; }}
        .mini-gauge {{ position: relative; width: {gauge_w}px; height: {gauge_h}px; }}
        .mini-arc {{ position: absolute; left: {arc_left}px; top: {arc_top}px; width: {arc_w}px; height: {arc_h}px; border-radius: {arc_w}px {arc_w}px 0 0; background: conic-gradient(from 270deg at 50% 100%, #ff2020 0deg 30deg, #b02020 30deg 60deg, #602020 60deg 90deg, #206020 90deg 120deg, #00a030 120deg 150deg, #00cc44 150deg 180deg); -webkit-mask: radial-gradient(circle at 50% 100%, transparent {arc_mask_inner}px, black {arc_mask_outer}px); mask: radial-gradient(circle at 50% 100%, transparent {arc_mask_inner}px, black {arc_mask_outer}px); }}
        .mini-needle {{ position: absolute; left: 50%; bottom: {3*s}px; width: {needle_w}px; height: {needle_h}px; margin-left: {needle_margin}px; transform-origin: 50% 100%; transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1); z-index: 3; }}
        .mini-needle-ant {{ position: absolute; left: 50%; bottom: {3*s}px; width: {needle_ant_w}px; height: {needle_ant_h}px; margin-left: {needle_ant_margin}px; transform-origin: 50% 100%; transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1); z-index: 2; }}
        .mini-pivot {{ position: absolute; left: 50%; bottom: 0px; width: {pivot_w}px; height: {pivot_h}px; margin-left: {pivot_margin}px; border-radius: 50%; background: {cor}; z-index: 4; transition: background 0.5s ease; }}
        .mini-value {{ font-size: {value_fs}px; font-weight: 900; color: {cor}; text-align: center; margin-top: {value_mt}px; transition: color 0.5s ease; letter-spacing: 0.3px; line-height: 1.1; }}
        .mini-sub {{ font-size: {sub_fs}px; color: #8b949e; text-align: center; margin-top: {sub_mt}px; line-height: 1.1; }}
        .mini-delta {{ font-size: {delta_fs}px; color: #c9d1d9; text-align: center; margin-top: {delta_mt}px; font-weight: 700; letter-spacing: 0.3px; line-height: 1.1; }}
        .mini-daily {{ font-size: {sub_fs}px; color: #8b949e; text-align: center; margin-top: 2px; font-weight: 600; }}
    </style></head><body>
        <div class="mini-wrap">
            <div class="mini-label">{label}</div>
            <div class="mini-gauge">
                <div class="mini-arc"></div>
                {svg_anterior}
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 52"><path d="M 4 0 L 5.5 46 L 2.5 46 Z" fill="#ffffff"/></svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-sub">{preco_fmt}</div>
            {f'<div class="mini-delta">{texto_delta}</div>' if texto_delta else ''}
            {texto_diaria}
        </div>
    </body></html>
    """
    components.html(html, height=altura_widget, scrolling=False)

# ==============================================================================
# MODELOS DE DOMÍNIO E CLASSE SETUPSERVICE
# ==============================================================================
@dataclass(frozen=True)
class ConfigSetup09:
    janela_inicio: time = time(9, 0); janela_fim: time = time(9, 15)
    threshold_sinal: float = 1.5; forca_max: int = 10; loss_pts: int = 250; alvo_min_pts: int = 250

CONFIG = ConfigSetup09()

class SetupService:
    def __init__(self, dados: Dict[str, Dict[str, Any]], config: ConfigSetup09 = CONFIG):
        self.cfg = config
        self.dados = dados
        self._parse()

    def _f(self, v):
        try: return float(v) if v is not None else None
        except (TypeError, ValueError): return None

    def _parse(self):
        noticias_d = self.dados.get("noticias_0900", {})
        alerta = noticias_d.get("alerta_noticia_0900", {})
        self.tem_3estrelas: bool = alerta.get("tem_evento_3_estrelas", False)
        self.eventos_3e: list = alerta.get("eventos", [])
        self.alerta_texto: str = alerta.get("alerta", "")

        metricas = self.dados.get("metricas", {}) or {}
        indicadores = metricas.get("indicadores_compostos", {}) or {}
        
        self.ind_mercado_externo = self._f(indicadores.get("indicador_mercado_externo"))
        self.ind_adrs = self._f(indicadores.get("indicador_adrs_brasileiras"))
        
        # NOVOS CAMPOS DIÁRIOS DA CALCULADORA
        self.ind_mercado_externo_diario = self._f(indicadores.get("indicador_mercado_externo_diario"))
        self.ind_adrs_diario = self._f(indicadores.get("indicador_adrs_brasileiras_diario"))

        anterior = metricas.get("anterior") or {}
        self.ind_mercado_externo_penultima = self._f(anterior.get("indicador_mercado_externo"))
        self.ind_adrs_penultima = self._f(anterior.get("indicador_adrs_brasileiras"))

        est = self.dados.get("estimativa", {})
        self.win_est = est.get("estimativa_abertura", {}).get("WIN_INDICE", {}) or est.get("estimativas_abertura", {}).get("WIN_INDICE", {})
        self.pivot_win = est.get("pivot_points", {}).get("WIN_FUT") or {}

        dados_ativos = self.dados.get("ativos", {})
        ativos = dados_ativos.get("ativos", dados_ativos)
        self.win_ativo = ativos.get("WIN_FUT", {})
        self.preco_win: Optional[float] = self.win_ativo.get("preco") or self.win_est.get("abertura_teorica_pontos")

        self.decisao_v2_raw = self.dados.get("decisao_v2", {}) or {}
        self.tem_v2 = bool(self.decisao_v2_raw.get("decisao"))

        d2 = self.decisao_v2_raw.get("decisao", {}) or {}
        meta_d2 = d2.get("metadados", {})
        smc_meta = meta_d2.get("smc", {})
        prec_meta = meta_d2.get("precificacao_teorica", {})

        self.v2_vies = d2.get("vies_final"); self.v2_confianca = d2.get("confianca")
        self.v2_entrada = d2.get("entrada"); self.v2_stop = d2.get("stop_loss")
        alvos = d2.get("alvos") or []
        self.v2_alvo1 = d2.get("alvo_1") or (alvos[0] if len(alvos) > 0 else None)
        self.v2_alvo2 = d2.get("alvo_2") or (alvos[1] if len(alvos) > 1 else None)
        self.v2_invalidacao = d2.get("invalidacao"); self.v2_motivos = d2.get("motivos") or []

        cenario = (self.decisao_v2_raw.get("decisao", {}).get("metadados", {}).get("opening_scenario") or self.decisao_v2_raw.get("opening_scenario") or {})
        if not cenario:
            try:
                from datetime import date as _date
                _hoje = _date.today().isoformat()
                _hist, _ = carregar_json_absoluto(f"Historico_Aberturas/{_hoje}.json")
                if _hist:
                    _atu = _hist.get("atualizacoes") or []
                    if _atu: cenario = (_atu[-1].get("cenario") or {})
            except Exception: cenario = {}
        
        self.v2_direcao_cenario = cenario.get("direcao_provavel")
        rel = cenario.get("relacao_com_ajuste") or {}
        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else None

        self.poc_ontem = smc_meta.get("poc_ontem") or self.dados.get("analise_smc_regras", {}).get("niveis_institucionais", {}).get("poc_ontem")
        self.vwap_ontem = smc_meta.get("vwap_ontem") or self.dados.get("analise_smc_regras", {}).get("niveis_institucionais", {}).get("vwap_ontem")
        self.ob_alinhado = smc_meta.get("ob_alinhado_com_poc")
        self.abertura_teorica = prec_meta.get("abertura_teorica") or self.win_est.get("abertura_teorica_pontos")
        self.preco_carregado = prec_meta.get("preco_carregado_di") or self.win_est.get("cost_of_carry", {}).get("preco_teorico_carregado")
        self.var_teorica_pct = self.win_est.get("variacao_teorica_pct")

        res_op = self.dados.get("resultado_operacional", {})
        self.ops_backend = res_op.get("decisao_core", {}).get("win", {}).get("operacionais", {})

    def decisao_v2(self) -> Dict[str, Any]:
        return {
            "vies": self.v2_vies, "confianca": self.v2_confianca, "entrada": self.v2_entrada, "stop": self.v2_stop,
            "alvo1": self.v2_alvo1, "alvo2": self.v2_alvo2, "invalidacao": self.v2_invalidacao, "motivos": self.v2_motivos,
            "direcao_cenario": self.v2_direcao_cenario, "posicao_ajuste": self.v2_posicao_ajuste,
            "poc_ontem": self.poc_ontem, "vwap_ontem": self.vwap_ontem, "ob_alinhado": self.ob_alinhado,
            "abertura_teorica": self.abertura_teorica, "preco_carregado": self.preco_carregado, "var_teorica_pct": self.var_teorica_pct,
        }

    def contexto_ajuste(self) -> Dict[str, Any]:
        ativos = (self.dados.get("ativos") or {}).get("ativos") or self.dados.get("ativos") or {}
        def preco(chave):
            item = ativos.get(chave) or {}
            return self._f(item.get("preco")) if isinstance(item, dict) else None
        ajuste = preco("WIN_AJUSTE"); last = preco("WIN_LAST_TICK") or preco("WIN_FUT")
        dist = round(last - ajuste, 0) if ajuste is not None and last is not None else None
        posicao = None
        if dist is not None: posicao = "ACIMA" if dist > 20 else ("ABAIXO" if dist < -20 else "NO_AJUSTE")
        return {"ajuste": ajuste, "last": last, "dist_pts": dist, "posicao": posicao}

    def operacional_ajuste(self) -> Dict[str, Any]:
        op1 = self.ops_backend.get("op1_retorno_ajuste", {})
        if not op1: return {"status": "INDISPONIVEL", "detalhes": {}, "escoras": [], "barreiras": []}
        return op1

    def operacional_explosao(self) -> Dict[str, Any]:
        op2 = self.ops_backend.get("op2_explosao", {})
        if not op2: return {"status": "INDISPONIVEL", "detalhes": {}, "escoras": [], "barreiras": []}
        return op2

    def operacional_orb(self) -> Dict[str, Any]:
        op3 = self.ops_backend.get("op3_orb", {})
        if not op3: return {"status": "INDISPONIVEL", "detalhes": {}, "escoras": [], "barreiras": []}
        return op3

    def janela_ok(self) -> bool:
        agora = datetime.now().time()
        return self.cfg.janela_inicio <= agora <= self.cfg.janela_fim

# ==============================================================================
# HELPERS DE APRESENTAÇÃO
# ==============================================================================
def _fmt(valor, casas=0, sufixo=""):
    if valor is None: return "—"
    try: return f"{float(valor):,.{casas}f}{sufixo}" if casas > 0 else f"{float(valor):,.0f}{sufixo}"
    except (TypeError, ValueError): return "—"

def padrao_bola(padrao_str):
    mapa = {"Alta": "🟢", "Baixa": "🔴", "Estavel": "🟡"}
    partes = str(padrao_str).split("_E_")
    if len(partes) != 2: return f"⚪ {padrao_str}"
    return f"{mapa.get(partes[0], '⚪')} → {mapa.get(partes[1], '⚪')}"

def _extrair_p(ativos_unif, chave):
    item = ativos_unif.get(chave) or {}
    v = item.get("preco")
    return float(v) if isinstance(v, (int, float)) else None

def _extrair_duplo(ativos_unif, chave):
    """Retorna (Pct Atual, Pct Diario)"""
    item = ativos_unif.get(chave) or {}
    pct = item.get("variacao_pct")
    daily = item.get("change_daily")
    return (
        float(pct) if isinstance(pct, (int, float)) else None,
        float(daily) if isinstance(daily, (int, float)) else None
    )

# ==============================================================================
# RENDERIZADORES DE BLOCOS
# ==============================================================================
def render_bloco_decisao_v2(service: SetupService):
    st.markdown("---")
    st.subheader("🚀 Decisão V2 (motor prioritário)")
    st.info("✅ Esta é a decisão oficial do motor V2. O motor V1 (Core Engine) foi descontinuado.")

    d = service.decisao_v2()
    vies = str(d.get("vies") or "—").upper()
    conf = d.get("confianca")
    conf_str = f"{conf}%" if conf is not None else "—"

    if "COMPRA" in vies or vies == "ALTA": card_class, emoji = "card-bull", "🟢"
    elif "VENDA" in vies or vies == "BAIXA": card_class, emoji = "card-bear", "🔴"
    else: card_class, emoji = "card-neutral", "🟡"

    st.markdown(
        f"""<div class="{card_class}">
            <h3 style="margin:0 0 6px;">{emoji} {vies} · confiança {conf_str}</h3>
            <div>{d.get("invalidacao") or "—"}</div>
            <div style="margin-top:6px;opacity:.9;">Posição vs ajuste: <b>{d.get("posicao_ajuste") or "—"}</b> &nbsp;|&nbsp; Cenário: <b>{d.get("direcao_cenario") or "—"}</b></div>
        </div>""", unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entrada", _fmt(d.get("entrada")))
    c2.metric("Stop", _fmt(d.get("stop")))
    c3.metric("Alvo 1", _fmt(d.get("alvo1")))
    c4.metric("Alvo 2", _fmt(d.get("alvo2")))

    st.markdown("##### 🏦 Referências de Tesouraria & Cost of Carry")
    t1, t2, t3, t4 = st.columns(4)

    ob_delta = "OB Alinhado 🟢" if d.get("ob_alinhado") is True else ("Sem OB" if d.get("ob_alinhado") is False else None)
    t1.metric("POC Ontem (Volume)", _fmt(d.get("poc_ontem"), sufixo=" pts"), delta=ob_delta)
    t2.metric("VWAP Ontem", _fmt(d.get("vwap_ontem"), casas=1, sufixo=" pts"))

    var_txt = f"{d['var_teorica_pct']:+.2f}%" if d.get("var_teorica_pct") is not None else None
    t3.metric("Abertura Teórica WIN", _fmt(d.get("abertura_teorica"), sufixo=" pts"), var_txt)
    t4.metric("Preço Carregado (DI/252)", _fmt(d.get("preco_carregado"), sufixo=" pts"))

    with st.expander("> Motivos"):
        motivos = d.get("motivos", [])
        if motivos:
            for m in motivos: st.markdown(f"• {m}")
        else: st.write("Sem motivos detalhados cadastrados.")


def render_bloco_operacionais(service: SetupService, rom5: dict):
    st.markdown("---")
    st.subheader("🎯 Operacionais de Abertura (Backend Espelhado)")

    op1 = service.operacional_ajuste()
    op2 = service.operacional_explosao()

    if op2.get("status") in ["EXPLOSAO", "EXPLOSÃO"]:
        st.markdown(
            f"""<div class="card-bull">
                <h3 style="margin:0 0 6px;">🚀 PREFERÊNCIA: EXPLOSÃO {op2.get('detalhes', {}).get('lado', '')}</h3>
                <div>Driver: {op2.get('detalhes', {}).get('driver', '—')}</div>
            </div>""", unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""<div class="card-neutral">
                <h3 style="margin:0 0 6px;">⚖️ {op2.get('status', 'AGUARDAR')}</h3>
                <div>Driver: {op2.get('detalhes', {}).get('driver', '—')}</div>
            </div>""", unsafe_allow_html=True
        )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1️⃣ Retorno ao Ajuste")
        st.caption("Alvo 500 / Stop 100")
        status_op1 = op1.get("status", "—")
        status_icon = "⚪"
        if "ATIVO" in status_op1: status_icon = "🟢"
        elif "BLOQUEADO" in status_op1: status_icon = "🔴"
        elif "ENCERRADO" in status_op1: status_icon = "⏹️"
        elif "AGUARDANDO" in status_op1: status_icon = "⏳"
        st.markdown(f"**Status:** {status_icon} `{status_op1}`")
        
        det1 = op1.get("detalhes", {})
        if det1:
            m1, m2, m3 = st.columns(3)
            m1.metric("Dist. ajuste", f"{det1.get('gap_atual', 0):+.0f} pts")
            m2.metric("Lado", det1.get("lado", "—"))
            m3.metric("Alvo/Stop", f"{det1.get('alvo', 0):.0f}/{det1.get('stop', 0):.0f}")
        with st.expander("> Escoras e Barreiras (Op 1)"):
            st.write("**Escoras:**", ", ".join(op1.get("escoras", [])) or "Nenhuma")
            st.write("**Barreiras:**", ", ".join(op1.get("barreiras", [])) or "Nenhuma")

    with c2:
        st.markdown("#### 2️⃣ Explosão Pós-Abertura")
        st.caption("Válido 09:00 - 09:15")
        status_op2 = op2.get("status", "—")
        status_icon = "⚪"
        if "EXPLOSAO" in status_op2 or "EXPLOSÃO" in status_op2: status_icon = "🔥"
        elif "ENCERRADO" in status_op2: status_icon = "⏹️"
        elif "AGUARDANDO" in status_op2: status_icon = "⏳"
        st.markdown(f"**Status:** {status_icon} `{status_op2}`")
        
        det2 = op2.get("detalhes", {})
        if det2:
            m1, m2, m3 = st.columns(3)
            m1.metric("Driver", det2.get("driver", "—"))
            m2.metric("Alvo 1 / 2", f"{det2.get('alvo1', 0):.0f}/{det2.get('alvo2', 0):.0f}")
            m3.metric("Stop", f"{det2.get('stop', 0):.0f}")
        with st.expander("> Escoras e Barreiras (Op 2)"):
            st.write("**Escoras:**", ", ".join(op2.get("escoras", [])) or "Nenhuma")
            st.write("**Barreiras:**", ", ".join(op2.get("barreiras", [])) or "Nenhuma")

# ==============================================================================
# RENDERIZADOR DO FILTRO
# ==============================================================================
def render_bloco_1_filtro_classificacao(service: SetupService, rom5: dict):
    st.markdown("---")
    st.subheader("📌 Filtro de Notícias e Classificação")

    if service.tem_3estrelas:
        st.error("🚨 **NOTÍCIA 3★ BRASIL 09:00** — Filtro de prioridade ATIVADO (ADRs)")
    else:
        st.success("✅ **Sem notícias 3★ críticas às 09:00** — Calendário de abertura normal.")

    ind_mercado = service.ind_mercado_externo
    ind_mercado_d = service.ind_mercado_externo_diario
    ind_adrs = service.ind_adrs
    ind_adrs_d = service.ind_adrs_diario

    pen_m = service.ind_mercado_externo_penultima or calcular_ind_externo_rom5(rom5)
    pen_a = service.ind_adrs_penultima or calcular_ind_adrs_rom5(rom5)

    st.markdown("##### ⏱️ Velocímetros de pressão")

    if service.tem_3estrelas:
        prioridade_mercado, prioridade_adrs = "Secundário", "Prioritário"
    else:
        prioridade_mercado, prioridade_adrs = "Prioritário", "Secundário"

    c1, c2 = st.columns(2)
    with c1:
        mini_velocimetro(
            ind_mercado, "🌍 Mercado Externo",
            f"Ant {pen_m:+.2f}%" if pen_m is not None else "",
            inverter=False, valor_anterior=pen_m, escala=2.0, range_max=15.0,
            var_diaria=ind_mercado_d
        )
        if ind_mercado is not None:
            intensidade = "FORTE_VENDA" if ind_mercado < -4.5 else ("FORTE_COMPRA" if ind_mercado > 4.5 else "MODERADO/LATERAL")
            if pen_m is not None:
                st.caption(f"{intensidade} · {prioridade_mercado} · atual **{ind_mercado:+.2f}%** · Ant **{pen_m:+.2f}%**")
            else:
                st.caption(f"{intensidade} · {prioridade_mercado} · atual **{ind_mercado:+.2f}%**")
        else:
            st.caption("Dados de Mercado Externo indisponíveis")

    with c2:
        mini_velocimetro(
            ind_adrs, "🇧🇷 BR ADRs Brasileiras",
            f"Ant {pen_a:+.2f}%" if pen_a is not None else "",
            inverter=False, valor_anterior=pen_a, escala=2.0, range_max=30.0,
            var_diaria=ind_adrs_d
        )
        if ind_adrs is not None:
            intensidade = "FORTE_COMPRA" if ind_adrs > 4.5 else ("FORTE_VENDA" if ind_adrs < -4.5 else "MODERADO/LATERAL")
            if pen_a is not None:
                st.caption(f"{intensidade} · {prioridade_adrs} · atual **{ind_adrs:+.2f}%** · Ant **{pen_a:+.2f}%**")
            else:
                st.caption(f"{intensidade} · {prioridade_adrs} · atual **{ind_adrs:+.2f}%**")
        else:
            st.caption("Dados de ADRs indisponíveis")

    if service.tem_3estrelas:
        st.warning("⚠️ **Filtro ativado:** Notícia 3★ → prioridade às ADRs.")

    if ind_mercado is not None and ind_adrs is not None:
        if (ind_mercado < 0 and ind_adrs > 0) or (ind_mercado > 0 and ind_adrs < 0):
            st.info("🔀 Divergência detectada entre Mercado Externo e ADRs — seguir ADRs como referência prioritária.")


# ==============================================================================
# ABA 1 — JANELA PRÉ-MARKET (macro, refresh 300s)
# ==============================================================================
@st.fragment(run_every=300)
def _render_tab1_pre_market():
    unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
    tendencias_dados, _ = carregar_json_absoluto("Analise_Tendencias.json")
    rom5 = carregar_rom5()
    ativos_unif = unificados.get("ativos", {})

    win_last_v = _extrair_p(ativos_unif, "WIN_LAST_TICK") or _extrair_p(ativos_unif, "WIN_FECHAMENTO_B3")
    win_ajuste_v = _extrair_p(ativos_unif, "WIN_AJUSTE")
    win_fut_v = _extrair_p(ativos_unif, "WIN_FUT")

    st.markdown("#### 📍 Mini Índice WIN")
    c_w1, c_w2, c_w3, c_w4 = st.columns(4)
    var_win, var_win_d = _extrair_duplo(ativos_unif, "WIN_FUT")
    spread_win = (win_ajuste_v - win_last_v) if win_ajuste_v is not None and win_last_v is not None else None

    c_w1.metric("🎯 Ajuste", _fmt(win_ajuste_v, sufixo=" pts"))
    c_w2.metric("📊 Futuro (Close)", _fmt(win_fut_v, sufixo=" pts"), f"{var_win:+.2f}%" if var_win is not None else None)
    c_w3.metric("🕯️ Last (Candle)", _fmt(win_last_v, sufixo=" pts"))
    c_w4.metric("📏 Spread (Ajuste - Last)", f"{spread_win:+,.0f} pts" if spread_win is not None else "—")
    st.caption("💡 O 'Last' é o último tick negociado no pregão anterior (capturado via MT5).")
    st.markdown("---")

    st.markdown("### 🌐 Termômetro Macro (com %)")
    st.caption("Ponteiro centrado em zero · 🟢 positivo = compra · 🔴 negativo = venda · ⚠️ VIX/DXY invertidos")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        v, vd = _extrair_duplo(ativos_unif, "SP500_FUT")
        mini_velocimetro(v, "🇺🇸 S&P500", _fmt(_extrair_p(ativos_unif, "SP500_FUT"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "SP500_FUT"), var_diaria=vd)
    with m2:
        v, vd = _extrair_duplo(ativos_unif, "NASDAQ_FUT")
        mini_velocimetro(v, "💻 Nasdaq", _fmt(_extrair_p(ativos_unif, "NASDAQ_FUT"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "NASDAQ_FUT"), var_diaria=vd)
    with m3:
        v, vd = _extrair_duplo(ativos_unif, "EWZ")
        mini_velocimetro(v, "🇧🇷 EWZ", f"${_fmt(_extrair_p(ativos_unif, 'EWZ'), casas=2)}" if _extrair_p(ativos_unif, "EWZ") is not None else "", inverter=False, valor_anterior=_get_var_rom5(rom5, "EWZ"), var_diaria=vd)
    with m4:
        v, vd = _extrair_duplo(ativos_unif, "VIX")
        mini_velocimetro(v, "⚠️ VIX", _fmt(_extrair_p(ativos_unif, "VIX"), casas=2), inverter=True, valor_anterior=_get_var_rom5(rom5, "VIX"), var_diaria=vd)
    with m5:
        v, vd = _extrair_duplo(ativos_unif, "DXY")
        mini_velocimetro(v, "💵 DXY", _fmt(_extrair_p(ativos_unif, "DXY"), casas=2), inverter=True, valor_anterior=_get_var_rom5(rom5, "DXY"), var_diaria=vd)
    with m6:
        v, vd = _extrair_duplo(ativos_unif, "IRON_ORE")
        mini_velocimetro(v, "⛏️ Minério", f"${_fmt(_extrair_p(ativos_unif, 'IRON_ORE'), casas=2)}" if _extrair_p(ativos_unif, "IRON_ORE") is not None else "", inverter=False, valor_anterior=_get_var_rom5(rom5, "IRON_ORE"), var_diaria=vd)

    st.markdown("---")
    st.markdown("### 📌 4. Contexto Macro e Confluência")
    st.markdown("##### ADRs Brasileiras")
    a1, a2, a3, a4, a5, a6 = st.columns(6)
    with a1:
        v, vd = _extrair_duplo(ativos_unif, "BBD_ADR")
        mini_velocimetro(v, "BBD", _fmt(_extrair_p(ativos_unif, "BBD_ADR"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "BBD_ADR"), var_diaria=vd)
    with a2:
        v, vd = _extrair_duplo(ativos_unif, "ITUB_ADR")
        mini_velocimetro(v, "ITUB", _fmt(_extrair_p(ativos_unif, "ITUB_ADR"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "ITUB_ADR"), var_diaria=vd)
    with a3:
        v, vd = _extrair_duplo(ativos_unif, "PETR_ADR")
        mini_velocimetro(v, "PETR", _fmt(_extrair_p(ativos_unif, "PETR_ADR"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "PETR_ADR"), var_diaria=vd)
    with a4:
        v, vd = _extrair_duplo(ativos_unif, "VALE_ADR")
        mini_velocimetro(v, "VALE", _fmt(_extrair_p(ativos_unif, "VALE_ADR"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "VALE_ADR"), var_diaria=vd)
    with a5:
        v, vd = _extrair_duplo(ativos_unif, "BBAS_ADR")
        mini_velocimetro(v, "BBAS", _fmt(_extrair_p(ativos_unif, "BBAS_ADR"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "BBAS_ADR"), var_diaria=vd)
    with a6:
        v, vd = _extrair_duplo(ativos_unif, "B3_ADR")
        mini_velocimetro(v, "B3", _fmt(_extrair_p(ativos_unif, "B3_ADR"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "B3_ADR"), var_diaria=vd)

    st.markdown("##### Macro & Taxas")
    mt1, mt2, mt3 = st.columns(3)
    with mt1:
        v, vd = _extrair_duplo(ativos_unif, "CRUDE_OIL")
        mini_velocimetro(v, "🛢️ Petróleo", _fmt(_extrair_p(ativos_unif, "CRUDE_OIL"), casas=2), inverter=False, valor_anterior=_get_var_rom5(rom5, "CRUDE_OIL"), var_diaria=vd)
    with mt2:
        v, vd = _extrair_duplo(ativos_unif, "DI1_2027")
        mini_velocimetro(v, "📈 DI 2027", f"{_fmt(_extrair_p(ativos_unif, 'DI1_2027'), casas=2)}%" if _extrair_p(ativos_unif, "DI1_2027") is not None else "", inverter=True, valor_anterior=_get_var_rom5(rom5, "DI1_2027"), var_diaria=vd)
    with mt3:
        v, vd = _extrair_duplo(ativos_unif, "DI1_2029")
        mini_velocimetro(v, "📈 DI 2029", f"{_fmt(_extrair_p(ativos_unif, 'DI1_2029'), casas=2)}%" if _extrair_p(ativos_unif, "DI1_2029") is not None else "", inverter=True, valor_anterior=_get_var_rom5(rom5, "DI1_2029"), var_diaria=vd)

    st.markdown("##### Confluência com Tendência (últimos 15min)")
    ativos_tend = ["WIN_FUT", "WDO_FUT", "SP500_FUT", "NASDAQ_FUT", "VIX", "EWZ"]
    cols_t = st.columns(6)
    for idx, t_ativo in enumerate(ativos_tend):
        t_alt = next((k for k, v in MAPEAMENTO_TICKERS.items() if v == t_ativo), "")
        info_t = tendencias_dados.get(t_ativo) or tendencias_dados.get(t_alt) or {}
        padrao = info_t.get("padrao_comportamento", "—") if isinstance(info_t, dict) else "—"
        var_15 = info_t.get("intervalo_5_para_0", {}).get("variacao_pct") if isinstance(info_t, dict) else None
        if var_15 is None: var_15 = _extrair_duplo(ativos_unif, t_ativo)[0]
        with cols_t[idx]:
            st.metric(label=t_ativo, value=padrao_bola(padrao) if padrao != "—" else "—", delta=f"{var_15:+.2f}%" if var_15 is not None else None, delta_color="normal" if (var_15 or 0) > 0 else "inverse" if (var_15 or 0) < 0 else "off")


# ==============================================================================
# ABA 2 — SETUP ABERTURA 09:00–09:15 (refresh 300s)
# ==============================================================================
@st.fragment(run_every=300)
def _render_tab2_setup_0900():
    unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
    decisao_v2, _ = carregar_json_absoluto("Decisao_V2.json")
    smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
    estimativas, _ = carregar_json_absoluto("EstimativaAbertura.json")
    noticias_0900, _ = carregar_json_absoluto("Noticias_Calendario_0900.json")
    metricas_calc, _ = carregar_json_absoluto("Metricas_Calculadas.json")
    resultado_op, _ = carregar_json_absoluto("Resultado_Calculadora_Operacional_Abertura.json")
    tendencias_dados, _ = carregar_json_absoluto("Analise_Tendencias.json")
    rom5 = carregar_rom5()

    dados_09h = {
        "noticias_0900": noticias_0900, "metricas": metricas_calc, "estimativa": estimativas,
        "decisao_v2": decisao_v2, "ativos": unificados, "tendencias": tendencias_dados,
        "resultado_operacional": resultado_op, "analise_smc_regras": smc_regras,
    }
    service_09h = SetupService(dados_09h)

    st.header("Setup Abertura 09:00 – 09:15")
    if service_09h.janela_ok(): st.success("🟢 DENTRO DA JANELA (09:00 – 09:15)")
    else: st.warning(f"⏰ Fora da janela • {datetime.now().strftime('%H:%M:%S')}")

    render_bloco_decisao_v2(service_09h)
    render_bloco_operacionais(service_09h, rom5)
    render_bloco_1_filtro_classificacao(service_09h, rom5)

    st.markdown("---")
    st.markdown("### 🔮 Projeção Estatística e Níveis de Pivô")
    pr_col1, pr_col2, pr_col3 = st.columns([1, 1, 1])
    var_teorica = service_09h.var_teorica_pct
    with pr_col1: mini_velocimetro(var_teorica, "🔮 Variação Teórica", f"{var_teorica:+.2f}%" if var_teorica is not None else "", False)
    ctx_aj = service_09h.contexto_ajuste(); gap_pts = ctx_aj.get("dist_pts")
    with pr_col2: mini_velocimetro((gap_pts / 1880.0) if gap_pts is not None else None, "📏 Gap vs Ajuste", f"{gap_pts:+.0f} pts" if gap_pts is not None else "", False)
    with pr_col3: mini_velocimetro((-10.0 if service_09h.tem_3estrelas else 0.0), "📰 Risco Noticiário", "ELEVADO" if service_09h.tem_3estrelas else "BAIXO", True)

    pivots_w = estimativas.get("pivot_points", {}).get("WIN_FUT") or decisao_v2.get("decisao", {}).get("metadados", {}).get("pivots") or {}
    if pivots_w:
        st.markdown("#### Níveis Técnicos de Suporte e Resistência (Floor Pivots)")
        fl1, fl2 = st.columns(2)
        fl1.markdown(f"* **Resistência 2 (R2):** `{_fmt(pivots_w.get('R2'))}`\n* **Resistência 1 (R1):** `{_fmt(pivots_w.get('R1'))}`\n* **Ponto de Pivô (PP):** `{_fmt(pivots_w.get('PP'))}`")
        fl2.markdown(f"* **Suporte 1 (S1):** `{_fmt(pivots_w.get('S1'))}`\n* **Suporte 2 (S2):** `{_fmt(pivots_w.get('S2'))}`")

# ==============================================================================
# ABA 3 — ABERTURA 10:00 (live, refresh 60s)
# ==============================================================================
@st.fragment(run_every=60)
def _render_tab3_abertura_1000():
    unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
    decisao_v2, _ = carregar_json_absoluto("Decisao_V2.json")
    smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
    smc_mtf, _ = carregar_json_absoluto("AnaliseGraficaSMC_MTF.json")
    
    noticias_0900, _ = carregar_json_absoluto("Noticias_Calendario_0900.json")
    metricas_calc, _ = carregar_json_absoluto("Metricas_Calculadas.json")
    resultado_op, _ = carregar_json_absoluto("Resultado_Calculadora_Operacional_Abertura.json")
    tendencias_dados, _ = carregar_json_absoluto("Analise_Tendencias.json")
    estimativas, _ = carregar_json_absoluto("EstimativaAbertura.json")

    st.markdown("<h3 style='color:#00d4ff;'>🎯 Estratégia de Abertura das 10:00h (Backend Espelhado)</h3>", unsafe_allow_html=True)
    st.caption("Foco exclusivo: Mini Índice (WINFUT)")

    dados_10h = {
        "noticias_0900": noticias_0900, "metricas": metricas_calc, "estimativa": estimativas,
        "decisao_v2": decisao_v2, "ativos": unificados, "tendencias": tendencias_dados,
        "resultado_operacional": resultado_op, "analise_smc_regras": smc_regras,
    }
    service = SetupService(dados_10h)
    op3 = service.operacional_orb()
    
    ativos = unificados.get("ativos", {})
    win_last = ativos.get("WIN_FUT", {}).get("preco") or ativos.get("WIN_LAST_TICK", {}).get("preco")
    win_ajuste = ativos.get("WIN_AJUSTE", {}).get("preco")

    decisao_core = decisao_v2.get("decisao", {})
    meta_smc = decisao_core.get("metadados", {}).get("smc", {})
    meta_prec = decisao_core.get("metadados", {}).get("precificacao_teorica", {})

    poc_ontem = meta_smc.get("poc_ontem") or smc_regras.get("niveis_institucionais", {}).get("poc_ontem")
    vwap_ontem = meta_smc.get("vwap_ontem") or smc_regras.get("niveis_institucionais", {}).get("vwap_ontem")
    ob_alinhado = meta_smc.get("ob_alinhado_com_poc")
    preco_carregado = meta_prec.get("preco_carregado_di")

    vies_final = decisao_core.get("vies_final") or smc_regras.get("bias_direcional")
    confianca = decisao_core.get("confianca") or smc_regras.get("confianca_visual")

    # Extração de dados mastigados do Op 3
    op3_status = op3.get("status", "INDISPONIVEL")
    op3_det = op3.get("detalhes", {})
    vela_str = op3_det.get("vela", "—")
    
    gatilho_compra = op3_det.get("gatilho_compra")
    gatilho_venda = op3_det.get("gatilho_venda")
    alvo_compra = op3_det.get("alvo") if op3_status == "COMPRA_ACIONADA" else op3_det.get("cenario_compra", {}).get("alvo")
    alvo_venda = op3_det.get("alvo") if op3_status == "VENDA_ACIONADA" else op3_det.get("cenario_venda", {}).get("alvo")
    
    col_header1, col_header2, col_header3, col_header4 = st.columns(4)

    with col_header1:
        vies_str = str(vies_final or "—").upper()
        conf_str = f"({confianca}%)" if confianca is not None else ""
        if "COMPRA" in vies_str or vies_str == "ALTA": st.success(f"Viés V2: COMPRA {conf_str}")
        elif "VENDA" in vies_str or vies_str == "BAIXA": st.error(f"Viés V2: VENDA {conf_str}")
        else: st.warning(f"Viés V2: {vies_str} {conf_str}")

    with col_header2: st.metric("Preço Atual (MT5)", _fmt(win_last, sufixo=" pts"))
    with col_header3:
        dist_ajuste = (win_last - win_ajuste) if win_last and win_ajuste else None
        st.metric("Distância do Ajuste", f"{dist_ajuste:+.0f} pts" if dist_ajuste is not None else "—")
    with col_header4:
        ob_delta = "OB Alinhado 🟢" if ob_alinhado is True else None
        st.metric("POC Ontem", _fmt(poc_ontem, sufixo=" pts"), delta=ob_delta)

    t1, t2, t3 = st.columns([1, 1, 1.5])
    t1.metric("VWAP Ontem", _fmt(vwap_ontem, casas=1, sufixo=" pts"))
    t2.metric("Preço Carregado (DI)", _fmt(preco_carregado, sufixo=" pts"))
    with t3:
        st.markdown("**Vela Mãe (10h)**")
        st.caption(vela_str)

    st.markdown("---")
    col_sinal, col_metricas = st.columns([1.5, 1])

    with col_sinal:
        st.markdown("### 📡 Status do Sinal Operacional (Rompimento 10h)")
        
        if op3_status == "AGUARDANDO_VELA":
            st.info("⏳ Aguardando a formação da vela das 10:00 para calcular o ORB.")
        elif op3_status == "VELA_EM_FORMACAO":
            st.info("⏱️ Vela das 10:00 em formação (fecha às 10:05).")
        elif op3_status == "BLOQUEADO":
            st.error(f"🚫 **SINAL BLOQUEADO:** {op3_det.get('motivo', 'Amplitude fora do padrão.')}")
        elif op3_status == "ERRO_VELA_AUSENTE":
            st.error("⚠️ **DADOS INDISPONÍVEIS:** A vela das 10:00 não foi encontrada.")
        elif op3_status in ["ATIVO", "COMPRA_ACIONADA", "VENDA_ACIONADA"]:
            
            if op3_status == "ATIVO":
                st.info("⚖️ **AGUARDANDO ROMPIMENTO:** A vela mãe está formada, o preço está dentro do range.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.markdown(f"🟢 **Cenário Compra**\n\n- Gatilho: `{_fmt(gatilho_compra)}`\n- Stop: `{_fmt(op3_det.get('cenario_compra', {}).get('stop'))}`\n- Alvo: `{_fmt(alvo_compra)}`")
                with cc2:
                    st.markdown(f"🔴 **Cenário Venda**\n\n- Gatilho: `{_fmt(gatilho_venda)}`\n- Stop: `{_fmt(op3_det.get('cenario_venda', {}).get('stop'))}`\n- Alvo: `{_fmt(alvo_venda)}`")
            
            elif op3_status == "COMPRA_ACIONADA":
                st.success(f"🚀 **COMPRA ACIONADA:** O preço rompeu a máxima da vela mãe!")
                m1, m2, m3 = st.columns(3)
                m1.metric("Alvo", _fmt(alvo_compra))
                m2.metric("Stop", _fmt(op3_det.get("stop")))
                m3.metric("Gatilho Origem", _fmt(gatilho_compra))

            elif op3_status == "VENDA_ACIONADA":
                st.error(f"🔻 **VENDA ACIONADA:** O preço rompeu a mínima da vela mãe!")
                m1, m2, m3 = st.columns(3)
                m1.metric("Alvo", _fmt(alvo_venda))
                m2.metric("Stop", _fmt(op3_det.get("stop")))
                m3.metric("Gatilho Origem", _fmt(gatilho_venda))

            with st.expander("> Rotas (Escoras e Barreiras) do ORB"):
                st.write("**Escoras (Suporte):**", ", ".join(op3.get("escoras", [])) or "Nenhuma")
                st.write("**Barreiras (Alerta):**", ", ".join(op3.get("barreiras", [])) or "Nenhuma")
        else:
            st.warning(f"Status desconhecido do backend: {op3_status}")

    with col_metricas:
        st.markdown("### 📊 Métricas do ORB")
        c1, c2 = st.columns(2)
        c1.metric("Ajuste Diário", _fmt(win_ajuste, sufixo=" pts"))
        if "Amplitude" in op3_det.get("motivo", ""):
             c2.metric("Motivo do Bloqueio", "Amplitude", delta_color="inverse")

    st.markdown("---")
    if smc_mtf:
        conf = smc_mtf.get("confluencia") or {}
        _ver, _dir, _rac = conf.get("veredito_mtf") or "—", conf.get("direcao_dominante") or "—", conf.get("racional") or ""
        _b15, _b5, _b1 = conf.get("bias_m15") or "—", conf.get("bias_m5") or "—", conf.get("bias_m1") or "—"
        _c15, _c5, _c1 = conf.get("confianca_m15"), conf.get("confianca_m5"), conf.get("confianca_m1")

        st.markdown("### 🧭 Contexto Multi-Timeframe (M15 / M5 / M1)")
        def _cor_bias(_b):
            _s = str(_b or "").upper()
            return "#22c55e" if "ALTA" in _s or "COMPRA" in _s or "BULL" in _s else ("#ef4444" if "BAIXA" in _s or "VENDA" in _s or "BEAR" in _s else "#a3a3a3")

        def _card_bias(col, label, bias, conf):
            _cor, _conf = _cor_bias(bias), f"{conf}%" if conf is not None else "—"
            with col:
                st.markdown(f"<div style='padding:10px 14px;border-radius:8px;background:rgba(255,255,255,0.03);border-left:3px solid {_cor};'><div style='font-size:0.85rem;color:#9ca3af;'>{label}</div><div style='font-size:1.5rem;font-weight:700;color:{_cor};line-height:1.2;margin-top:2px;'>{bias}</div><div style='font-size:0.8rem;color:#6b7280;margin-top:2px;'>Confiança: {_conf}</div></div>", unsafe_allow_html=True)

        _cols = st.columns(3)
        _card_bias(_cols[0], "M15 (macro)", _b15, _c15); _card_bias(_cols[1], "M5 (médio)", _b5, _c5); _card_bias(_cols[2], "M1 (micro)", _b1, _c1)

        _cor = {"ALINHADO_FORTE": "success", "PULLBACK": "info", "REVERSAO_MICRO_MEDIO": "warning", "CONFLITO_MACRO": "warning", "DIVERGENTE": "error", "NEUTRO": "info", "SEM_DIRECAO": "info"}.get(_ver, "info")
        _msg = f"**{_ver}** — direção dominante: `{_dir}`" + (f"\n\n{_rac}" if _rac else "")
        if _cor == "success": st.success(_msg)
        elif _cor == "warning": st.warning(_msg)
        elif _cor == "error": st.error(_msg)
        else: st.info(_msg)

    st.markdown("### 📉 Visão Gráfica e Monitoramento de Rompimento")
    fig = go.Figure()
    
    if win_ajuste is not None: fig.add_trace(go.Scatter(x=[0, 10], y=[win_ajuste, win_ajuste], mode="lines", name="Ajuste Oficial B3", line=dict(color="orange", dash="dash")))
    if poc_ontem is not None: fig.add_trace(go.Scatter(x=[0, 10], y=[poc_ontem, poc_ontem], mode="lines", name="POC Ontem", line=dict(color="#a855f7", dash="dot")))
    if vwap_ontem is not None: fig.add_trace(go.Scatter(x=[0, 10], y=[vwap_ontem, vwap_ontem], mode="lines", name="VWAP Ontem", line=dict(color="#9ca3af", dash="dot")))
    
    if gatilho_compra:
        fig.add_trace(go.Scatter(x=[2, 8], y=[gatilho_compra, gatilho_compra], mode="lines+text", name="Gatilho Compra", line=dict(color="#00d4ff", width=2), text=[f"Compra ({gatilho_compra:,.0f})"], textposition="top center"))
    if gatilho_venda:
        fig.add_trace(go.Scatter(x=[2, 8], y=[gatilho_venda, gatilho_venda], mode="lines+text", name="Gatilho Venda", line=dict(color="#ff6b6b", width=2), text=[f"Venda ({gatilho_venda:,.0f})"], textposition="bottom center"))
    
    if win_last is not None: fig.add_trace(go.Scatter(x=[5], y=[win_last], mode="markers+text", name="Preço Atual B3", marker=dict(color="white", size=14, symbol="diamond"), text=[f"WIN: {win_last:,.0f}"], textposition="middle right"))
    
    fig.update_layout(title="Níveis Críticos para o Rompimento (Backend)", xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(title="Pontuação Mini Índice (WIN)", autorange=True), template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02))
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# CORPO DA PÁGINA
# ==============================================================================
def render_body():
    st.markdown("<h2 style='color:#00d4ff;'>🎯 Painel Unificado de Abertura Pregão B3</h2>", unsafe_allow_html=True)
    st.caption("Orquestração Ativa: V2 · auto-refresh: 300s · ⚪ ponteiro branco = 5 min atrás")
    st.info("🚀 **Fila de Execução V2:** Este painel consome a decisão oficial e a inteligência de rotas gerada pelo motor Python.")

    tab_overnight, tab_0900, tab_1000 = st.tabs([
        "🗓️ 1. Janela Pré-Market (Ajuste)",
        "⚡ 2. Abertura 09:00h (Leilão WIN)",
        "📊 3. Abertura 10:00h (Pregão À Vista)",
    ])

    with tab_overnight: _render_tab1_pre_market()
    with tab_0900: _render_tab2_setup_0900()
    with tab_1000: _render_tab3_abertura_1000()

if __name__ == "__main__":
    render_body()