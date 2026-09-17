# -*- coding: utf-8 -*-
"""
Módulo: pages/2_🎯_Setup_Abertura.py
Versão: 8.1 (Gauges de pressão unificados no padrão SVG — escala 2.0x)
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
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT E CSS UNIFICADO
# ==============================================================================
st.set_page_config(page_title="WINFUT - Setup Abertura", layout="wide")

CSS_CUSTOM = """
<style>
.stApp { background-color: #0e1117; }
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
    "OTC:BOLSY": "B3_ADR",
}

# Mapa chave interna → ticker bruto no rom-5
MAPA_TICKERS_ROM5 = {
    "EWZ": "AMEX:EWZ",
    "VIX": "TVC:VIX",
    "DXY": "TVC:DXY",
    "CRUDE_OIL": "NYMEX:CL1!",
    "IRON_ORE_2M": "SGX:FEF2!",
    "IRON_ORE": "SGX:FEF1!",
    "SP500_FUT": "CME_MINI:ES1!",
    "NASDAQ_FUT": "CME_MINI:NQ1!",
    "VALE_ADR": "NYSE:VALE",
    "PETR_ADR": "NYSE:PBR",
    "ITUB_ADR": "NYSE:ITUB",
    "BBAS_ADR": "OTC:BDORY",
    "BBD_ADR": "NYSE:BBD",
    "B3_ADR": "OTC:BOLSY",
    "DI1_2027": "BMFBOVESPA:DI1F2027",
    "DI1_2029": "BMFBOVESPA:DI1F2029",
    "WIN_AJUSTE": "B3_AJUSTE_WIN",
    "WDO_AJUSTE": "B3_AJUSTE_WDO",
    "WIN_FUT": "BMFBOVESPA:WIN1!",
    "WDO_FUT": "BMFBOVESPA:WDO1!",
    "WIN_LAST_TICK": "WIN_LAST_TICK",
    "WDO_LAST_TICK": "WDO_LAST_TICK",
}

ADRS_COMPOSTO = ["BBD_ADR", "ITUB_ADR", "PETR_ADR", "VALE_ADR", "BBAS_ADR", "B3_ADR"]


def carregar_json_absoluto(nome_arquivo):
    locais_busca = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        RAIZ_PROJETO / "json" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo,
    ]
    for caminho in locais_busca:
        if caminho.is_file():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f), str(caminho)
            except Exception:
                pass
    return {}, None


@st.cache_data(ttl=2)
def carregar_rom5() -> dict:
    """Carrega o Coleta_rom-5.json (5 min atrás)."""
    for path in [RAIZ_PROJETO / "Coletas" / "Coleta_rom-5.json",
                 RAIZ_PROJETO / "Coleta_rom-5.json",
                 Path.cwd() / "Coletas" / "Coleta_rom-5.json"]:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
    return {}


def _get_var_rom5(rom5: dict, chave_interna: str) -> Optional[float]:
    """Retorna change_percent do ativo no rom-5."""
    if not rom5:
        return None
    ticker = MAPA_TICKERS_ROM5.get(chave_interna, chave_interna)
    for item in rom5.get("coletas", []):
        if item.get("ativo") == ticker:
            val = (item.get("dados_reais") or {}).get("change_percent")
            if isinstance(val, (int, float)):
                return float(val)
    return None


def _get_preco_rom5(rom5: dict, chave_interna: str) -> Optional[float]:
    """Retorna close do ativo no rom-5."""
    if not rom5:
        return None
    ticker = MAPA_TICKERS_ROM5.get(chave_interna, chave_interna)
    for item in rom5.get("coletas", []):
        if item.get("ativo") == ticker:
            val = (item.get("dados_reais") or {}).get("close")
            if isinstance(val, (int, float)):
                return float(val)
    return None


def calcular_ind_adrs_rom5(rom5: dict) -> Optional[float]:
    vals = [_get_var_rom5(rom5, adr) for adr in ADRS_COMPOSTO]
    vals = [v for v in vals if v is not None]
    return round(sum(vals), 4) if vals else None


def calcular_ind_externo_rom5(rom5: dict) -> Optional[float]:
    vix = _get_var_rom5(rom5, "VIX")
    crude = _get_var_rom5(rom5, "CRUDE_OIL")
    iron = _get_var_rom5(rom5, "IRON_ORE_2M")
    if vix is None or crude is None or iron is None:
        return None
    return round(-vix + crude + iron, 4)


# ==============================================================================
# FUNÇÃO MT5 — MÁXIMA E MÍNIMA DA VELA M5 DAS 10:00h
# ==============================================================================
@st.cache_data(ttl=60)
def obter_max_min_vela_10h(win_last):
    """Consulta o MT5 para extrair a máxima e mínima exata da 1ª vela de 5min das 10:00h."""
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            for sym in ["WIN$", "WINV26", "WINZ26", "WINFUT"]:
                rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 40)
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    hoje = datetime.now().date()
                    df_hoje = df[df['time'].dt.date == hoje]

                    vela = df_hoje[df_hoje['time'].dt.time >= time(10, 0)]
                    if not vela.empty:
                        primeira_vela = vela.iloc[0]
                        high = float(primeira_vela['high'])
                        low = float(primeira_vela['low'])
                        mt5.shutdown()
                        return high, low
            mt5.shutdown()
    except Exception:
        pass

    return None, None


# ==============================================================================
# MINI VELOCÍMETRO (com parâmetro ESCALA opcional)
# - escala=1.0 → padrão das páginas 3/4/6
# - escala=2.0 → usado na seção de pressão (Mercado Externo / ADRs)
# ==============================================================================
def mini_velocimetro(
    valor: Optional[float],
    label: str,
    preco_fmt: str = "",
    inverter: bool = False,
    valor_anterior: Optional[float] = None,
    escala: float = 1.0,
) -> None:
    # ---- Valor atual ----
    if valor is None:
        real_exibicao = 0.0
        cor = "#8b949e"
        texto_valor = "—"
    else:
        try:
            real_exibicao = max(-10.0, min(10.0, float(valor)))
        except (TypeError, ValueError):
            real_exibicao = 0.0
        real_cor = -real_exibicao if inverter else real_exibicao
        if real_cor > 0.05:
            cor = "#00cc44"
        elif real_cor < -0.05:
            cor = "#ff4b4b"
        else:
            cor = "#ffa500"
        texto_valor = f"{real_exibicao:+.2f}%"

    # ---- Valor anterior ----
    svg_anterior = ""
    texto_delta = ""
    if valor_anterior is not None:
        try:
            real_ant = max(-10.0, min(10.0, float(valor_anterior)))
            angulo_ant = (real_ant / 10.0) * 90.0
            svg_anterior = (
                f'<svg class="mini-needle-ant" '
                f'style="transform: rotate({angulo_ant}deg);" '
                f'viewBox="0 0 14 58">'
                f'<path d="M 7 0 L 9.5 46 L 4.5 46 Z" '
                f'fill="rgba(220, 220, 255, 0.85)"/>'
                f'</svg>'
            )
            delta = real_exibicao - real_ant
            if abs(delta) < 0.005:
                texto_delta = "Δ 0.00%"
            else:
                texto_delta = f"Δ {delta:+.2f}%"
        except (TypeError, ValueError):
            pass

    angulo = (real_exibicao / 10.0) * 90.0

    # ---- Escala (multiplica todas as dimensões) ----
    s = max(0.5, float(escala))

    gauge_w = 120 * s
    gauge_h = 62 * s
    arc_left = 5 * s
    arc_top = 3 * s
    arc_w = 110 * s
    arc_h = 55 * s
    arc_mask_inner = 34 * s
    arc_mask_outer = 35 * s
    needle_w = 8 * s
    needle_h = 52 * s
    needle_margin = -4 * s
    needle_ant_w = 14 * s
    needle_ant_h = 48 * s
    needle_ant_margin = -7 * s
    pivot_w = 12 * s
    pivot_h = 12 * s
    pivot_margin = -6 * s
    label_fs = 11 * s
    value_fs = 14 * s
    delta_fs = 10 * s
    sub_fs = 10 * s
    value_mt = 4 * s
    delta_mt = 3 * s
    sub_mt = 2 * s

    # Altura do widget HTML (deve caber tudo)
    altura_widget = int(155 * s) if s <= 1.5 else int(150 * s + 30)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        html, body {{
            margin: 0; padding: 0; background: transparent;
            font-family: Arial, sans-serif;
            color: #e6edf3;
            overflow: hidden;
        }}
        .mini-wrap {{
            display: flex; flex-direction: column; align-items: center;
            padding: {2 * s}px 0;
        }}
        .mini-label {{
            font-size: {label_fs}px;
            color: #c9d1d9;
            margin-bottom: {1 * s}px;
            text-align: center;
            font-weight: 700;
            white-space: nowrap;
        }}
        .mini-gauge {{
            position: relative;
            width: {gauge_w}px;
            height: {gauge_h}px;
        }}
        .mini-arc {{
            position: absolute; left: {arc_left}px; top: {arc_top}px;
            width: {arc_w}px; height: {arc_h}px;
            border-radius: {arc_w}px {arc_w}px 0 0;
            background: conic-gradient(
                from 270deg at 50% 100%,
                #ff2020 0deg 30deg,
                #b02020 30deg 60deg,
                #602020 60deg 90deg,
                #206020 90deg 120deg,
                #00a030 120deg 150deg,
                #00cc44 150deg 180deg
            );
            -webkit-mask: radial-gradient(circle at 50% 100%, transparent {arc_mask_inner}px, black {arc_mask_outer}px);
                    mask: radial-gradient(circle at 50% 100%, transparent {arc_mask_inner}px, black {arc_mask_outer}px);
        }}
        .mini-needle {{
            position: absolute;
            left: 50%;
            bottom: {3 * s}px;
            width: {needle_w}px;
            height: {needle_h}px;
            margin-left: {needle_margin}px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 3;
        }}
        .mini-needle-ant {{
            position: absolute;
            left: 50%;
            bottom: {3 * s}px;
            width: {needle_ant_w}px;
            height: {needle_ant_h}px;
            margin-left: {needle_ant_margin}px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2;
        }}
        .mini-pivot {{
            position: absolute;
            left: 50%;
            bottom: 0px;
            width: {pivot_w}px; height: {pivot_h}px;
            margin-left: {pivot_margin}px;
            border-radius: 50%;
            background: {cor};
            z-index: 4;
            transition: background 0.5s ease;
        }}
        .mini-value {{
            font-size: {value_fs}px;
            font-weight: 900;
            color: {cor};
            text-align: center;
            margin-top: {value_mt}px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
            line-height: 1.1;
        }}
        .mini-sub {{
            font-size: {sub_fs}px;
            color: #8b949e;
            text-align: center;
            margin-top: {sub_mt}px;
            line-height: 1.1;
        }}
        .mini-delta {{
            font-size: {delta_fs}px;
            color: #c9d1d9;
            text-align: center;
            margin-top: {delta_mt}px;
            font-weight: 700;
            letter-spacing: 0.3px;
            line-height: 1.1;
        }}
    </style>
    </head>
    <body>
        <div class="mini-wrap">
            <div class="mini-label">{label}</div>
            <div class="mini-gauge">
                <div class="mini-arc"></div>
                {svg_anterior}
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 52">
                    <path d="M 4 0 L 5.5 46 L 2.5 46 Z" fill="#ffffff"/>
                </svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-sub">{preco_fmt}</div>
            {f'<div class="mini-delta">{texto_delta}</div>' if texto_delta else ''}
        </div>
    </body>
    </html>
    """
    components.html(html, height=altura_widget, scrolling=False)


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

    def _f(self, v):
        try:
            if v is None:
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

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

        self.v2_vies = d2.get("vies_final")
        self.v2_confianca = d2.get("confianca")
        self.v2_entrada = d2.get("entrada")
        self.v2_stop = d2.get("stop_loss")
        alvos = d2.get("alvos") or []
        self.v2_alvo1 = d2.get("alvo_1") or (alvos[0] if len(alvos) > 0 else None)
        self.v2_alvo2 = d2.get("alvo_2") or (alvos[1] if len(alvos) > 1 else None)
        self.v2_invalidacao = d2.get("invalidacao")
        self.v2_motivos = d2.get("motivos") or []

        cenario = self.decisao_v2_raw.get("opening_scenario") or {}
        self.v2_direcao_cenario = cenario.get("direcao_provavel")
        rel = cenario.get("relacao_com_ajuste") or {}
        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else None

        self.poc_ontem = smc_meta.get("poc_ontem") or self.dados.get("analise_smc_regras", {}).get("niveis_institucionais", {}).get("poc_ontem")
        self.vwap_ontem = smc_meta.get("vwap_ontem") or self.dados.get("analise_smc_regras", {}).get("niveis_institucionais", {}).get("vwap_ontem")
        self.ob_alinhado = smc_meta.get("ob_alinhado_com_poc")

        self.abertura_teorica = prec_meta.get("abertura_teorica") or self.win_est.get("abertura_teorica_pontos")
        self.preco_carregado = prec_meta.get("preco_carregado_di") or self.win_est.get("cost_of_carry", {}).get("preco_teorico_carregado")
        self.var_teorica_pct = self.win_est.get("variacao_teorica_pct")

    def decisao_v2(self) -> Dict[str, Any]:
        return {
            "vies": self.v2_vies, "confianca": self.v2_confianca,
            "entrada": self.v2_entrada, "stop": self.v2_stop,
            "alvo1": self.v2_alvo1, "alvo2": self.v2_alvo2,
            "invalidacao": self.v2_invalidacao, "motivos": self.v2_motivos,
            "direcao_cenario": self.v2_direcao_cenario,
            "posicao_ajuste": self.v2_posicao_ajuste,
            "poc_ontem": self.poc_ontem, "vwap_ontem": self.vwap_ontem,
            "ob_alinhado": self.ob_alinhado,
            "abertura_teorica": self.abertura_teorica,
            "preco_carregado": self.preco_carregado,
            "var_teorica_pct": self.var_teorica_pct,
        }

    def contexto_ajuste(self) -> Dict[str, Any]:
        ativos = (self.dados.get("ativos") or {}).get("ativos") or self.dados.get("ativos") or {}
        def preco(chave):
            item = ativos.get(chave) or {}
            if isinstance(item, dict):
                return self._f(item.get("preco"))
            return None

        ajuste = preco("WIN_AJUSTE")
        last = preco("WIN_LAST_TICK") or preco("WIN_FUT")

        dist = round(last - ajuste, 0) if ajuste is not None and last is not None else None
        posicao = None
        if dist is not None:
            posicao = "ACIMA" if dist > 20 else ("ABAIXO" if dist < -20 else "NO_AJUSTE")

        return {"ajuste": ajuste, "last": last, "dist_pts": dist, "posicao": posicao}

    def operacional_ajuste(self) -> Dict[str, Any]:
        ctx = self.contexto_ajuste()
        dist = ctx["dist_pts"]
        pos = ctx["posicao"]
        alvo_pts, loss_pts = 500, 100

        lado = "VENDA" if pos == "ACIMA" else ("COMPRA" if pos == "ABAIXO" else "NEUTRO")
        entrada = ctx["ajuste"]

        stop = alvo = None
        if entrada is not None:
            if lado == "VENDA":
                stop = entrada + loss_pts
                alvo = entrada - alvo_pts
            elif lado == "COMPRA":
                stop = entrada - loss_pts
                alvo = entrada + alvo_pts

        bloqueios = []
        status = "AGUARDAR"
        if dist is not None:
            abs_dist = abs(dist)
            bloqueios.append(f"Distância do ajuste: {dist:+.0f} pts")
            if abs_dist >= 200:
                status = "BLOQUEADO"
                bloqueios.append(f"Gap grande ({dist:+.0f} pts) — R:R do alvo {alvo_pts} inviável")
            elif abs_dist >= 100:
                status = "CAUTELA"
                bloqueios.append(f"Gap moderado/alto ({dist:+.0f} pts) — R:R do alvo {alvo_pts} piora")
            else:
                status = "DISPONÍVEL"
        else:
            bloqueios.append("Sem distância do ajuste calculável")

        return {
            "nome": "Retorno ao Ajuste", "lado": lado, "status": status,
            "bloqueios": bloqueios, "entrada": entrada, "stop": stop,
            "alvo": alvo, "alvo_pts": alvo_pts, "loss_pts": loss_pts, "dist_pts": dist,
            "posicao": pos, "ajuste": ctx["ajuste"], "last": ctx["last"],
        }

    def operacional_explosao(self) -> Dict[str, Any]:
        metricas = self.dados.get("metricas") or {}
        compostos = metricas.get("indicadores_compostos") or {}
        ind_adrs = self._f(compostos.get("indicador_adrs_brasileiras"))
        ind_ext = self._f(compostos.get("indicador_mercado_externo"))
        ctx = self.contexto_ajuste()
        dist = ctx.get("dist_pts")

        driver = ind_adrs if self.tem_3estrelas else (ind_ext if ind_ext is not None else ind_adrs)
        driver_nome = "ADRs" if self.tem_3estrelas else ("Mercado Externo" if ind_ext is not None else "ADRs")

        score = None
        if ind_adrs is not None and ind_ext is not None:
            score = round((ind_adrs * 0.6) + (ind_ext * 0.4), 2)
        elif ind_adrs is not None:
            score = round(ind_adrs, 2)
        elif ind_ext is not None:
            score = round(ind_ext, 2)

        direcao = "NEUTRO"
        forca = "BAIXA"
        status = "AGUARDAR"
        motivo = "Dados insuficientes para definir explosão"

        gap_ok = dist is not None and abs(dist) >= 80
        gap_dir = None
        if dist is not None:
            if dist > 20:
                gap_dir = "COMPRA"
            elif dist < -20:
                gap_dir = "VENDA"

        if driver is not None:
            if driver > 4.5:
                direcao, forca = "COMPRA", "ALTA"
            elif driver < -4.5:
                direcao, forca = "VENDA", "ALTA"
            elif abs(driver) > 1.5:
                direcao = "COMPRA" if driver > 0 else "VENDA"
                forca = "MODERADA"

            alinhado = gap_dir is not None and direcao == gap_dir
            if gap_ok and alinhado and forca in ("ALTA", "MODERADA"):
                status = "EXPLOSÃO"
                motivo = f"Gap {dist:+.0f} pts alinhado com {driver_nome} ({driver:+.2f}%) — seguir o gap, não fade"
            elif gap_ok and not alinhado and forca == "ALTA":
                status = "MONITORAR"
                motivo = f"Gap {dist:+.0f} pts CONTRA {driver_nome} ({driver:+.2f}%) — retorno ao ajuste ganha prioridade"
            elif not gap_ok:
                status = "MONITORAR"
                motivo = (f"Gap fraco ({dist:+.0f} pts)" if dist is not None else "Gap indisponível") + " — sem combustível de explosão"
            else:
                status = "MONITORAR"
                motivo = f"Drivers {driver_nome} moderados/neutros"

        return {
            "nome": "Explosão Pós-Abertura", "direcao": direcao, "forca": forca,
            "status": status, "motivo": motivo, "score": score,
            "ind_adrs": ind_adrs, "ind_externo": ind_ext, "gap_pts": dist,
            "driver_prioritario": driver_nome,
        }

    def operacional_leilao(self) -> Dict[str, Any]:
        ctx = self.contexto_ajuste()
        exp = self.operacional_explosao()
        dist = ctx.get("dist_pts")
        ind_adrs = exp.get("ind_adrs")

        aviso_noticia = "Notícia ⭐⭐⭐ Brasil 09:00 — leilão pode ser sujo" if self.tem_3estrelas else "Sem restrições severas de notícias"

        bloqueios = []
        if dist is not None:
            bloqueios.append(f"Gap last×ajuste: {dist:+.0f} pts")
        if self.tem_3estrelas:
            bloqueios.insert(0, "Notícia 3 estrelas (Brasil 09:00) — não entrar no 1º segundo")

        if dist is not None:
            if dist > 80:
                direcao_gap = "ALTA"
            elif dist < -80:
                direcao_gap = "BAIXA"
            elif dist > 20:
                direcao_gap = "ALTA (FRACA)"
            elif dist < -20:
                direcao_gap = "BAIXA (FRACA)"
            else:
                direcao_gap = "NEUTRO"
        else:
            direcao_gap = None

        rec = "NÃO OPERAR LEILÃO"
        if self.tem_3estrelas:
            rec = "AGUARDAR — SEM EDGE NO LEILÃO (notícia 3★)"
        elif dist is not None and ind_adrs is not None:
            if dist > 80 and ind_adrs > 4.5:
                rec = "BIAS COMPRA NO LEILÃO"
            elif dist < -80 and ind_adrs < -4.5:
                rec = "BIAS VENDA NO LEILÃO"
            elif abs(dist) >= 80:
                rec = "LEILÃO MONITORADO (gap ok, drivers fracos)"
            else:
                rec = "NÃO OPERAR LEILÃO (gap fraco)"
        elif dist is not None and abs(dist) >= 80:
            rec = "LEILÃO MONITORADO"

        return {
            "nome": "Operacional de Leilão", "teorico": ctx["last"], "ajuste": ctx["ajuste"],
            "dist_pts": dist, "direcao_gap": direcao_gap,
            "drivers_direcao": exp["direcao"], "score_drivers": exp["score"],
            "recomendacao": rec, "alerta_noticia": aviso_noticia, "bloqueios": bloqueios,
        }

    def janela_ok(self) -> bool:
        agora = datetime.now().time()
        return self.cfg.janela_inicio <= agora <= self.cfg.janela_fim


# ==============================================================================
# HELPERS DE APRESENTAÇÃO
# ==============================================================================
def _fmt(valor, casas=0, sufixo=""):
    if valor is None:
        return "—"
    try:
        if casas == 0:
            return f"{float(valor):,.0f}{sufixo}"
        return f"{float(valor):,.{casas}f}{sufixo}"
    except (TypeError, ValueError):
        return "—"


def padrao_bola(padrao_str):
    mapa = {"Alta": "🟢", "Baixa": "🔴", "Estavel": "🟡"}
    partes = str(padrao_str).split("_E_")
    if len(partes) != 2:
        return f"⚪ {padrao_str}"
    return f"{mapa.get(partes[0], '⚪')} → {mapa.get(partes[1], '⚪')}"


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

    if "COMPRA" in vies or vies == "ALTA":
        card_class, emoji = "card-bull", "🟢"
    elif "VENDA" in vies or vies == "BAIXA":
        card_class, emoji = "card-bear", "🔴"
    else:
        card_class, emoji = "card-neutral", "🟡"

    st.markdown(
        f"""
        <div class="{card_class}">
            <h3 style="margin:0 0 6px;">{emoji} {vies} · confiança {conf_str}</h3>
            <div>{d.get("invalidacao") or "—"}</div>
            <div style="margin-top:6px;opacity:.9;">Posição vs ajuste: <b>{d.get("posicao_ajuste") or "—"}</b> &nbsp;|&nbsp; Cenário: <b>{d.get("direcao_cenario") or "—"}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entrada", _fmt(d.get("entrada")))
    c2.metric("Stop", _fmt(d.get("stop")))
    c3.metric("Alvo 1", _fmt(d.get("alvo1")))
    c4.metric("Alvo 2", _fmt(d.get("alvo2")))

    st.markdown("##### 🏦 Referências de Tesouraria & Cost of Carry")
    t1, t2, t3, t4 = st.columns(4)

    ob_delta = None
    if d.get("ob_alinhado") is True:
        ob_delta = "OB Alinhado 🟢"
    elif d.get("ob_alinhado") is False:
        ob_delta = "Sem OB"

    t1.metric("POC Ontem (Volume)", _fmt(d.get("poc_ontem"), sufixo=" pts"), delta=ob_delta)
    t2.metric("VWAP Ontem", _fmt(d.get("vwap_ontem"), casas=1, sufixo=" pts"))

    var_txt = None
    if d.get("var_teorica_pct") is not None:
        var_txt = f"{d['var_teorica_pct']:+.2f}%"
    t3.metric("Abertura Teórica WIN", _fmt(d.get("abertura_teorica"), sufixo=" pts"), var_txt)
    t4.metric("Preço Carregado (DI/252)", _fmt(d.get("preco_carregado"), sufixo=" pts"))

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
    st.caption("Usa preço teórico/last vs ajuste + Σ ADRs/Macro para preparar o lado antes da abertura.")

    lei = service.operacional_leilao()

    st.markdown(
        f"""
        <div class="card-neutral">
            <h3 style="margin:0 0 6px;">🟡 {lei.get('recomendacao') or "—"}</h3>
            <div>{lei.get('alerta_noticia') or "—"}</div>
            <div style="margin-top:6px;opacity:.9;">Gap leilão: <b>{lei.get('direcao_gap') or "—"}</b> | Drivers: <b>{lei.get('drivers_direcao') or "—"}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preço teórico / last", _fmt(lei.get("teorico")))
    c2.metric("Ajuste", _fmt(lei.get("ajuste")))

    dist = lei.get("dist_pts")
    c3.metric("Gap projetado", f"{dist:+.0f} pts" if dist is not None else "—")

    score = lei.get("score_drivers")
    c4.metric("Score drivers", f"{score:+.2f}" if score is not None else "—")

    alerta_icone = "🚨 Notícia ⭐⭐⭐ no horário" if service.tem_3estrelas else "✅ Sem alerta crítico de notícias"
    st.caption(f"Drivers: {lei.get('drivers_direcao') or '—'} · {alerta_icone}")

    with st.expander("> Bloqueios / alertas do leilão"):
        bloq = lei.get("bloqueios", [])
        if bloq:
            for b in bloq:
                st.markdown(f"• {b}")
        else:
            st.write("Nenhum bloqueio identificado.")

    st.info("Fluxo sugerido: leilão define a *preparação* → após abrir, confirme com o bloco Operacionais.")


def render_bloco_operacionais(service: SetupService, rom5: dict):
    st.markdown("---")
    st.subheader("🎯 Operacionais de Abertura")

    aj = service.operacional_ajuste()
    ex = service.operacional_explosao()

    if ex.get("status") == "EXPLOSÃO":
        st.markdown(
            f"""
            <div class="card-bull">
                <h3 style="margin:0 0 6px;">🚀 PREFERÊNCIA: EXPLOSÃO {ex.get('direcao')}</h3>
                <div>Viés de explosão {ex.get('direcao')} ({ex.get('forca')})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="card-neutral">
                <h3 style="margin:0 0 6px;">⚖️ SEM EXPLOSÃO CLARA</h3>
                <div>Status: {ex.get('status')} · Direção: {ex.get('direcao')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1️⃣ Retorno ao Ajuste")
        st.caption(f"Abre acima → VENDA no ajuste | Abre abaixo → COMPRA no ajuste · Alvo {aj['alvo_pts']} / Loss {aj['loss_pts']}")

        st_aj = aj.get("status") or "—"
        if st_aj == "BLOQUEADO":
            status_icon = "🔴"
        elif st_aj == "CAUTELA":
            status_icon = "🟡"
        elif st_aj == "DISPONÍVEL":
            status_icon = "🟢"
        else:
            status_icon = "⚪"
        st.markdown(f"**Status:** {status_icon} {st_aj}")
        st.markdown(f"**Lado:** `{aj.get('lado') or '—'}`")

        m1, m2, m3 = st.columns(3)
        dist = aj.get("dist_pts")
        m1.metric("Dist. ajuste", f"{dist:+.0f} pts" if dist is not None else "—")
        m2.metric("Entrada", _fmt(aj.get("entrada")))
        m3.metric("Alvo / Stop", f"{aj['alvo_pts']}/{aj['loss_pts']}")

        st.caption(f"Stop: {_fmt(aj.get('stop'))} · Alvo: {_fmt(aj.get('alvo'))} · Posição: {aj.get('posicao') or '—'} · Last: {_fmt(aj.get('last'))}")

        with st.expander("> Bloqueios"):
            for b in aj.get("bloqueios", []):
                st.markdown(f"• {b}")

    with c2:
        st.markdown("#### 2️⃣ Explosão Pós-Abertura")
        st.caption("Soma ADRs + Mercado Externo → combustível de continuação")

        status_ex = ex.get("status") or "—"
        st.markdown(f"**Status:** {status_ex}")
        st.markdown(f"**Direção:** `{ex.get('direcao') or '—'}` · **Força:** `{ex.get('forca') or '—'}`")

        e1, e2, e3 = st.columns(3)

        score = ex.get("score")
        ind_adrs = ex.get("ind_adrs")
        ind_ext = ex.get("ind_externo")

        # Valores anteriores do rom-5
        score_ant = None
        ind_adrs_ant = calcular_ind_adrs_rom5(rom5)
        ind_ext_ant = calcular_ind_externo_rom5(rom5)
        if ind_adrs_ant is not None and ind_ext_ant is not None:
            score_ant = round((ind_adrs_ant * 0.6) + (ind_ext_ant * 0.4), 2)

        with e1:
            mini_velocimetro(
                score, "⚡ Score",
                f"{score:+.2f}" if score is not None else "",
                inverter=False,
                valor_anterior=score_ant,
            )
        with e2:
            mini_velocimetro(
                ind_adrs, "🇧🇷 Σ ADRs",
                f"{ind_adrs:+.2f}%" if ind_adrs is not None else "",
                inverter=False,
                valor_anterior=ind_adrs_ant,
            )
        with e3:
            mini_velocimetro(
                ind_ext, "🌍 Σ Macro",
                f"{ind_ext:+.2f}%" if ind_ext is not None else "",
                inverter=False,
                valor_anterior=ind_ext_ant,
            )

        st.caption(ex.get("motivo") or "—")
        st.info("Como usar: drivers a favor do gap → não fade; drivers neutros/contra → retorno ao ajuste ganha prioridade.")


def render_bloco_1_filtro_classificacao(service: SetupService, rom5: dict):
    st.markdown("---")
    st.subheader("📌 Filtro de Notícias e Classificação")

    if service.tem_3estrelas:
        st.error("🚨 **NOTÍCIA 3★ BRASIL 09:00** — Filtro de prioridade ATIVADO (ADRs)")
    else:
        st.success("✅ **Sem notícias 3★ críticas às 09:00** — Calendário de abertura normal.")

    ind_mercado = service.ind_mercado_externo
    ind_adrs = service.ind_adrs

    # Valores anteriores: preferir o "anterior" do JSON (já existe), com fallback pro rom-5
    pen_m = service.ind_mercado_externo_penultima or calcular_ind_externo_rom5(rom5)
    pen_a = service.ind_adrs_penultima or calcular_ind_adrs_rom5(rom5)

    st.markdown("##### ⏱️ Velocímetros de pressão")

    if service.tem_3estrelas:
        prioridade_mercado, prioridade_adrs = "Secundário", "Prioritário"
    else:
        prioridade_mercado, prioridade_adrs = "Prioritário", "Secundário"

    # ✅ Agora os dois gauges usam o MESMO estilo SVG (mini_velocimetro) com escala=2.0
    c1, c2 = st.columns(2)
    with c1:
        mini_velocimetro(
            ind_mercado,
            "🌍 Mercado Externo",
            f"{ind_mercado:+.2f}%" if ind_mercado is not None else "",
            inverter=False,
            valor_anterior=pen_m,
            escala=2.0,
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
            ind_adrs,
            "🇧🇷 BR ADRs Brasileiras",
            f"{ind_adrs:+.2f}%" if ind_adrs is not None else "",
            inverter=False,
            valor_anterior=pen_a,
            escala=2.0,
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
# CORPO DA PÁGINA (AUTO-REFRESH 60s)
# ==============================================================================
@st.fragment(run_every=60)
def render_body():
    # ---- Carregamento de dados ----
    unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
    decisao_v2, _ = carregar_json_absoluto("Decisao_V2.json")
    smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
    estimativas, _ = carregar_json_absoluto("EstimativaAbertura.json")
    if not estimativas:
        estimativas, _ = carregar_json_absoluto("Resultado_Calculadora.json")

    noticias_impacto, _ = carregar_json_absoluto("Noticias_Impacto_Dia.json")
    noticias_0900, _ = carregar_json_absoluto("Noticias_Calendario_0900.json")
    metricas_calc, _ = carregar_json_absoluto("Metricas_Calculadas.json")
    resultado_op, _ = carregar_json_absoluto("Resultado_Calculadora_Operacional_Abertura.json")
    tendencias_dados, _ = carregar_json_absoluto("Analise_Tendencias.json")
    rom5 = carregar_rom5()

    ativos_unif = unificados.get("ativos", {})

    def get_p_num(chave):
        if chave in ativos_unif:
            v = ativos_unif[chave].get("preco")
            if v is not None and isinstance(v, (int, float)):
                return float(v)
        return None

    def get_v_num(chave):
        if chave in ativos_unif:
            v = ativos_unif[chave].get("variacao_pct")
            if v is not None and isinstance(v, (int, float)):
                return float(v)
        return None

    win_last_v = get_p_num("WIN_LAST_TICK")
    win_ajuste_v = get_p_num("WIN_AJUSTE")
    win_fut_v = get_p_num("WIN_FUT")

    # --- Título ---
    st.markdown("<h2 style='color:#00d4ff;'>🎯 Painel Unificado de Abertura Pregão B3</h2>", unsafe_allow_html=True)
    ts_decisao = decisao_v2.get("metadata", {}).get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.caption(
        f"Orquestração Ativa: V2 ({ts_decisao}) · "
        f"auto-refresh: 60s · ⚪ ponteiro branco = valor de 5 min atrás"
    )
    st.info("🚀 **Fila de Execução V2:** Este painel consome a decisão oficial gerada pelo motor de confluência.")

    tab_overnight, tab_0900, tab_1000 = st.tabs([
        "🗓️ 1. Janela Pré-Market (Ajuste)",
        "⚡ 2. Abertura 09:00h (Leilão WIN)",
        "📊 3. Abertura 10:00h (Pregão À Vista)",
    ])

    # ============================================================
    # ABA 1
    # ============================================================
    with tab_overnight:
        st.markdown("#### 📍 Mini Índice WIN")
        c_w1, c_w2, c_w3, c_w4 = st.columns(4)
        var_win = get_v_num("WIN_FUT")

        spread_win = None
        if win_ajuste_v is not None and win_last_v is not None:
            spread_win = win_ajuste_v - win_last_v

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
            mini_velocimetro(
                get_v_num("SP500_FUT"), "🇺🇸 S&P500",
                _fmt(get_p_num("SP500_FUT"), casas=2),
                inverter=False,
                valor_anterior=_get_var_rom5(rom5, "SP500_FUT"),
            )
        with m2:
            mini_velocimetro(
                get_v_num("NASDAQ_FUT"), "💻 Nasdaq",
                _fmt(get_p_num("NASDAQ_FUT"), casas=2),
                inverter=False,
                valor_anterior=_get_var_rom5(rom5, "NASDAQ_FUT"),
            )
        with m3:
            mini_velocimetro(
                get_v_num("EWZ"), "🇧🇷 EWZ",
                f"${_fmt(get_p_num('EWZ'), casas=2)}" if get_p_num("EWZ") is not None else "",
                inverter=False,
                valor_anterior=_get_var_rom5(rom5, "EWZ"),
            )
        with m4:
            mini_velocimetro(
                get_v_num("VIX"), "⚠️ VIX",
                _fmt(get_p_num("VIX"), casas=2),
                inverter=True,
                valor_anterior=_get_var_rom5(rom5, "VIX"),
            )
        with m5:
            mini_velocimetro(
                get_v_num("DXY"), "💵 DXY",
                _fmt(get_p_num("DXY"), casas=2),
                inverter=True,
                valor_anterior=_get_var_rom5(rom5, "DXY"),
            )
        with m6:
            mini_velocimetro(
                get_v_num("IRON_ORE"), "⛏️ Minério",
                f"${_fmt(get_p_num('IRON_ORE'), casas=2)}" if get_p_num("IRON_ORE") is not None else "",
                inverter=False,
                valor_anterior=_get_var_rom5(rom5, "IRON_ORE"),
            )

        st.markdown("---")
        st.markdown("### 📌 4. Contexto Macro e Confluência")

        st.markdown("##### ADRs Brasileiras")
        a1, a2, a3, a4, a5, a6 = st.columns(6)

        with a1:
            mini_velocimetro(
                get_v_num("BBD_ADR"), "BBD",
                _fmt(get_p_num("BBD_ADR"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "BBD_ADR"),
            )
        with a2:
            mini_velocimetro(
                get_v_num("ITUB_ADR"), "ITUB",
                _fmt(get_p_num("ITUB_ADR"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "ITUB_ADR"),
            )
        with a3:
            mini_velocimetro(
                get_v_num("PETR_ADR"), "PETR",
                _fmt(get_p_num("PETR_ADR"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "PETR_ADR"),
            )
        with a4:
            mini_velocimetro(
                get_v_num("VALE_ADR"), "VALE",
                _fmt(get_p_num("VALE_ADR"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "VALE_ADR"),
            )
        with a5:
            mini_velocimetro(
                get_v_num("BBAS_ADR"), "BBAS",
                _fmt(get_p_num("BBAS_ADR"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "BBAS_ADR"),
            )
        with a6:
            mini_velocimetro(
                get_v_num("B3_ADR"), "B3",
                _fmt(get_p_num("B3_ADR"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "B3_ADR"),
            )

        st.markdown("##### Macro & Taxas")
        mt1, mt2, mt3 = st.columns(3)

        with mt1:
            mini_velocimetro(
                get_v_num("CRUDE_OIL"), "🛢️ Petróleo",
                _fmt(get_p_num("CRUDE_OIL"), casas=2), inverter=False,
                valor_anterior=_get_var_rom5(rom5, "CRUDE_OIL"),
            )
        with mt2:
            di27_val = get_p_num("DI1_2027")
            mini_velocimetro(
                get_v_num("DI1_2027"), "📈 DI 2027",
                f"{_fmt(di27_val, casas=2)}%" if di27_val is not None else "",
                inverter=True,
                valor_anterior=_get_var_rom5(rom5, "DI1_2027"),
            )
        with mt3:
            di29_val = get_p_num("DI1_2029")
            mini_velocimetro(
                get_v_num("DI1_2029"), "📈 DI 2029",
                f"{_fmt(di29_val, casas=2)}%" if di29_val is not None else "",
                inverter=True,
                valor_anterior=_get_var_rom5(rom5, "DI1_2029"),
            )

        st.markdown("##### Confluência com Tendência (últimos 15min)")
        ativos_tend = ["WIN_FUT", "WDO_FUT", "SP500_FUT", "NASDAQ_FUT", "VIX", "EWZ"]
        cols_t = st.columns(6)
        for idx, t_ativo in enumerate(ativos_tend):
            t_alt = next((k for k, v in TICKER_MAP.items() if v == t_ativo), "")
            info_t = tendencias_dados.get(t_ativo) or tendencias_dados.get(t_alt) or {}
            padrao = info_t.get("padrao_comportamento", "—") if isinstance(info_t, dict) else "—"
            var_15 = None
            if isinstance(info_t, dict):
                var_15 = info_t.get("intervalo_5_para_0", {}).get("variacao_pct")
            if var_15 is None:
                var_15 = get_v_num(t_ativo)
            with cols_t[idx]:
                delta_str = f"{var_15:+.2f}%" if var_15 is not None else None
                st.metric(
                    label=t_ativo,
                    value=padrao_bola(padrao) if padrao != "—" else "—",
                    delta=delta_str,
                    delta_color="normal" if (var_15 or 0) > 0 else "inverse" if (var_15 or 0) < 0 else "off",
                )

    # ============================================================
    # ABA 2
    # ============================================================
    dados_09h = {
        "noticias_0900": noticias_0900,
        "metricas": metricas_calc,
        "estimativa": estimativas,
        "decisao_v2": decisao_v2,
        "ativos": unificados,
        "tendencias": tendencias_dados,
        "resultado_operacional": resultado_op,
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
        render_bloco_operacionais(service_09h, rom5)
        render_bloco_1_filtro_classificacao(service_09h, rom5)

        st.markdown("---")
        st.markdown("### 🔮 Projeção Estatística e Níveis de Pivô")

        pr_col1, pr_col2, pr_col3 = st.columns([1, 1, 1])

        var_teorica = service_09h.var_teorica_pct

        with pr_col1:
            mini_velocimetro(
                var_teorica, "🔮 Variação Teórica",
                f"{var_teorica:+.2f}%" if var_teorica is not None else "",
                inverter=False,
            )

        ctx_aj = service_09h.contexto_ajuste()
        gap_pts = ctx_aj.get("dist_pts")

        with pr_col2:
            gap_pct_equiv = (gap_pts / 1880.0) if gap_pts is not None else None
            mini_velocimetro(
                gap_pct_equiv, "📏 Gap vs Ajuste",
                f"{gap_pts:+.0f} pts" if gap_pts is not None else "",
                inverter=False,
            )

        with pr_col3:
            risco_val = -10.0 if service_09h.tem_3estrelas else 0.0
            mini_velocimetro(
                risco_val, "📰 Risco Noticiário",
                "ELEVADO" if service_09h.tem_3estrelas else "BAIXO",
                inverter=True,
            )

        pivots_w = estimativas.get("pivot_points", {}).get("WIN_FUT") or decisao_v2.get("decisao", {}).get("metadados", {}).get("pivots") or {}

        if pivots_w:
            st.markdown("#### Níveis Técnicos de Suporte e Resistência (Floor Pivots)")
            fl1, fl2 = st.columns(2)
            r2 = pivots_w.get("R2") or pivots_w.get("r2")
            r1 = pivots_w.get("R1") or pivots_w.get("r1")
            pp = pivots_w.get("PP") or pivots_w.get("pp")
            s1 = pivots_w.get("S1") or pivots_w.get("s1")
            s2 = pivots_w.get("S2") or pivots_w.get("s2")

            fl1.markdown(f"* **Resistência 2 (R2):** `{_fmt(r2)}`\n* **Resistência 1 (R1):** `{_fmt(r1)}`\n* **Ponto de Pivô (PP):** `{_fmt(pp)}`")
            fl2.markdown(f"* **Suporte 1 (S1):** `{_fmt(s1)}`\n* **Suporte 2 (S2):** `{_fmt(s2)}`")
        else:
            st.caption("Níveis de pivô não disponíveis nos dados.")

    # ============================================================
    # ABA 3
    # ============================================================
    with tab_1000:
        st.markdown("<h3 style='color:#00d4ff;'>🎯 Estratégia de Abertura das 10:00h</h3>", unsafe_allow_html=True)
        st.caption("Foco exclusivo: Mini Índice (WINFUT)")

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

        candle_high_10h, candle_low_10h = obter_max_min_vela_10h(win_last)

        amplitude_range = None
        if candle_high_10h is not None and candle_low_10h is not None:
            amplitude_range = candle_high_10h - candle_low_10h

        col_header1, col_header2, col_header3, col_header4 = st.columns(4)

        with col_header1:
            vies_str = str(vies_final or "—").upper()
            conf_str = f"({confianca}%)" if confianca is not None else ""
            if "COMPRA" in vies_str or vies_str == "ALTA":
                st.success(f"Viés V2: COMPRA {conf_str}")
            elif "VENDA" in vies_str or vies_str == "BAIXA":
                st.error(f"Viés V2: VENDA {conf_str}")
            else:
                st.warning(f"Viés V2: {vies_str} {conf_str}")

        with col_header2:
            st.metric("Preço Atual (MT5)", _fmt(win_last, sufixo=" pts"))

        with col_header3:
            dist_ajuste = None
            if win_last is not None and win_ajuste is not None:
                dist_ajuste = win_last - win_ajuste
            st.metric("Distância do Ajuste", f"{dist_ajuste:+.0f} pts" if dist_ajuste is not None else "—")

        with col_header4:
            ob_delta = "OB Alinhado 🟢" if ob_alinhado is True else None
            st.metric("POC Ontem", _fmt(poc_ontem, sufixo=" pts"), delta=ob_delta)

        t1, t2, t3 = st.columns(3)
        t1.metric("VWAP Ontem", _fmt(vwap_ontem, casas=1, sufixo=" pts"))
        t2.metric("Preço Carregado (DI)", _fmt(preco_carregado, sufixo=" pts"))
        t3.metric("Amplitude Vela 10h", f"{amplitude_range:.0f} pts" if amplitude_range is not None else "—")

        st.markdown("---")

        col_sinal, col_metricas = st.columns([1.5, 1])

        with col_sinal:
            st.markdown("### 📡 Status do Sinal Operacional (Rompimento 10h)")

            if amplitude_range is None:
                st.markdown(
                    "<div style='background-color:#1e2230; padding:15px; border-radius:8px;'>"
                    "⚠️ <b>DADOS INDISPONÍVEIS:</b> Não foi possível obter a vela M5 das 10:00h via MT5.</div>",
                    unsafe_allow_html=True,
                )
            elif amplitude_range > 700 or amplitude_range < 50:
                st.markdown(
                    f"<div style='background-color:rgba(255,107,107,0.15); padding:15px; border-radius:8px; border:1px solid #ff6b6b;'>"
                    f"⚠️ <b>SINAL OPERACIONAL BLOQUEADO:</b> Amplitude fora do padrão "
                    f"({amplitude_range:.0f} pts).</div>",
                    unsafe_allow_html=True,
                )
            else:
                vies_str = str(vies_final or "").upper()
                if "COMPRA" in vies_str or vies_str == "ALTA":
                    entrada = candle_high_10h + 5
                    stop = candle_low_10h - 20
                    alvo = entrada + amplitude_range
                    st.markdown(
                        f"<div style='background-color:rgba(0,212,255,0.1); padding:15px; border-radius:8px; border:1px solid #00d4ff;'>"
                        f"🟢 <b>PREPARADO PARA COMPRA:</b><br>"
                        f"• <b>Buy Stop:</b> {entrada:,.0f} pts<br>"
                        f"• <b>Stop:</b> {stop:,.0f} pts<br>"
                        f"• <b>Alvo:</b> {alvo:,.0f} pts</div>",
                        unsafe_allow_html=True,
                    )
                elif "VENDA" in vies_str or vies_str == "BAIXA":
                    entrada = candle_low_10h - 5
                    stop = candle_high_10h + 20
                    alvo = entrada - amplitude_range
                    st.markdown(
                        f"<div style='background-color:rgba(255,107,107,0.1); padding:15px; border-radius:8px; border:1px solid #ff6b6b;'>"
                        f"🔴 <b>PREPARADO PARA VENDA:</b><br>"
                        f"• <b>Sell Stop:</b> {entrada:,.0f} pts<br>"
                        f"• <b>Stop:</b> {stop:,.0f} pts<br>"
                        f"• <b>Alvo:</b> {alvo:,.0f} pts</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='background-color:#1e2230; padding:15px; border-radius:8px;'>"
                        "⚖️ <b>AGUARDANDO:</b> Orquestrador V2 aponta neutralidade macro.</div>",
                        unsafe_allow_html=True,
                    )

        with col_metricas:
            st.markdown("### 📊 Métricas da Vela 10:00h (M5)")
            c1, c2 = st.columns(2)
            c1.metric("Máxima (10h)", _fmt(candle_high_10h, sufixo=" pts"))
            c1.metric("Mínima (10h)", _fmt(candle_low_10h, sufixo=" pts"))
            c2.metric("Amplitude", f"{amplitude_range:.0f} pts" if amplitude_range is not None else "—")
            c2.metric("Ajuste Diário", _fmt(win_ajuste, sufixo=" pts"))

        st.markdown("---")
        st.markdown("### 🧠 Filtros e Estruturas de Liquidez Ativas (SMC V2.6)")
        col_ob, col_fvg, col_liq = st.columns(3)

        with col_ob:
            st.markdown("**Order Blocks Recentes**")
            obs = meta_smc.get("order_blocks") or smc_regras.get("order_blocks", [])
            if obs:
                for ob in obs[:3]:
                    tipo = ob.get("tipo", "OB")
                    cor = "#00ff88" if tipo == "COMPRA" else "#ff6b6b"
                    preco = ob.get("preco") or ob.get("high")
                    low = ob.get("low")
                    high = ob.get("high")
                    st.markdown(
                        f"• <span style='color:{cor};'>OB de {tipo}</span> em `{_fmt(preco)}` "
                        f"(Níveis: {_fmt(low)}-{_fmt(high)})",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Nenhum Order Block validado.")

        with col_fvg:
            st.markdown("**Fair Value Gaps Abertos**")
            fvgs = meta_smc.get("fvgs") or smc_regras.get("fair_value_gaps", [])
            fvgs_abertos = [f for f in fvgs if not f.get("preenchido", False)]
            if fvgs_abertos:
                for fvg in fvgs_abertos[:3]:
                    tipo = fvg.get("tipo", "COMPRA")
                    cor = "#00ff88" if tipo == "COMPRA" else "#ff6b6b"
                    st.markdown(
                        f"• <span style='color:{cor};'>FVG {tipo}</span> | "
                        f"Zona: `{_fmt(fvg.get('inferior'))}` - `{_fmt(fvg.get('superior'))}`",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Mercado eficiente.")

        with col_liq:
            st.markdown("**Piscinas de Liquidez Pendentes**")
            liq = smc_regras.get("liquidez", {})
            bsl = liq.get("bsl", [])
            ssl = liq.get("ssl", [])
            if bsl:
                st.markdown(f"🔼 **BSL:** `{_fmt(bsl[0])}` pts — Alvo de caça comprador.")
            if ssl:
                st.markdown(f"🔽 **SSL:** `{_fmt(ssl[0])}` pts — Alvo de caça vendedor.")
            if not bsl and not ssl:
                st.caption("Sem topos ou fundos duplos mapeados.")

        st.markdown("---")
        st.markdown("### 📉 Visão Gráfica e Monitoramento de Rompimento")

        fig = go.Figure()

        if win_ajuste is not None:
            fig.add_trace(go.Scatter(x=[0, 10], y=[win_ajuste, win_ajuste], mode="lines", name="Ajuste Oficial B3", line=dict(color="orange", dash="dash")))

        if poc_ontem is not None:
            fig.add_trace(go.Scatter(x=[0, 10], y=[poc_ontem, poc_ontem], mode="lines", name="POC Ontem", line=dict(color="#a855f7", dash="dot")))
        if vwap_ontem is not None:
            fig.add_trace(go.Scatter(x=[0, 10], y=[vwap_ontem, vwap_ontem], mode="lines", name="VWAP Ontem", line=dict(color="#9ca3af", dash="dot")))

        if candle_high_10h is not None:
            fig.add_trace(go.Scatter(
                x=[2, 8], y=[candle_high_10h, candle_high_10h],
                mode="lines+text", name="Máxima Mãe",
                line=dict(color="#00d4ff", width=2),
                text=[f"Gatilho Compra ({candle_high_10h:,.0f})"],
                textposition="top center",
            ))
        if candle_low_10h is not None:
            fig.add_trace(go.Scatter(
                x=[2, 8], y=[candle_low_10h, candle_low_10h],
                mode="lines+text", name="Mínima Mãe",
                line=dict(color="#ff6b6b", width=2),
                text=[f"Gatilho Venda ({candle_low_10h:,.0f})"],
                textposition="bottom center",
            ))

        if win_last is not None:
            fig.add_trace(go.Scatter(
                x=[5], y=[win_last],
                mode="markers+text", name="Preço Atual B3",
                marker=dict(color="white", size=14, symbol="diamond"),
                text=[f"WIN: {win_last:,.0f}"],
                textposition="middle right",
            ))

        fig.update_layout(
            title="Níveis Críticos para a Janela de Rompimento Institucional",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(title="Pontuação Mini Índice (WIN)", autorange=True),
            template="plotly_dark",
            height=450,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        )

        st.plotly_chart(fig, use_container_width=True)


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
render_body()