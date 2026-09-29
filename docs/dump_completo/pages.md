# Dump completo - pages

Gerado em: 2026-09-29 08:09:22
Total de arquivos: 16

## Arvore

```
pages
|-- 1_⚡_Dashboard_Leilao_AoVivo.py
|-- 2_🎯_Setup_Abertura.py
|-- 3_⚡_Monitor_Abertura_Leilao.py
|-- 4_⚡_WINFUT_Intraday.py
|-- 5_📡_Ativos_Monitorados.py
|-- 6_📈_Matriz_de_Influencia.py
|-- 7.1_📊_SMC_Regras.py
|-- 7.2_🤖_IA_SpikeImagem.py
|-- 7.3_📥_Gerador_Profit_Pro.py
|-- 7.4_🤖_IA_Imagem.py
|-- 7.5_📅_Noticias.py
|-- 7_🔬_Analise_Tendencia.py
|-- 8.1_🗺️_Mapa_da_Aplicacao.py
|-- 8.2_🔢_Calculadora.py
|-- 8.3_🔑_Status_Chaves.py
`-- 9.5_📈_Historico_Macro.py
```

## Conteudo dos arquivos

### `pages/1_⚡_Dashboard_Leilao_AoVivo.py`

```python
# ============================================================
# pages/1_⚡_Dashboard_Leilao_AoVivo.py
# Dashboard de Leilão Ao Vivo — V2
#
# Mostra LADO A LADO:
#   - Abertura Teórica CALCULADA (CalculadoraEstimativaAbertura)
#   - Abertura do LEILÃO (OCR via LeilaoService)
#
# Contexto macro + SMC + veredito operacional.
# ============================================================

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Leilão Ao Vivo",
    page_icon="⚡",
    layout="wide",
)

# Caminhos
BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_COLETAS = BASE_DIR / "Coletas"

ARQUIVO_CSV = PASTA_COLETAS / "preco_teorico_win_fluxo.csv"
ARQUIVO_JSON_MACRO = PASTA_COLETAS / "DadosAtivosUnificados.json"
ARQUIVO_JSON_SMC = PASTA_COLETAS / "AnaliseGraficaSMC_Regras.json"
ARQUIVO_JSON_MTF = PASTA_COLETAS / "AnaliseGraficaSMC_MTF.json"
ARQUIVO_JSON_ESTIMATIVA = PASTA_COLETAS / "EstimativaAbertura.json"


st.title("⚡ Cockpit de Leilão Ao Vivo - WIN")
st.markdown("Monitoramento em tempo real do preço teórico, fluxo de ordens e confluência macro/institucional.")


# ------------------------------------------------------------
# Helpers de carregamento
# ------------------------------------------------------------

def carregar_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def carregar_estimativa_calculada() -> dict:
    """
    Lê o EstimativaAbertura.json (produzido pelo CalculadoraEstimativaAbertura).
    Retorna dict com:
      - abertura_teorica: preço calculado
      - preco_referencia_base: preço usado como base
      - variacao_teorica_pct: variação aplicada
    """
    dados = carregar_json(ARQUIVO_JSON_ESTIMATIVA)
    est = (
        dados.get("estimativa_abertura", {}).get("WIN_INDICE")
        or dados.get("estimativas_abertura", {}).get("WIN_INDICE")
        or {}
    )
    return {
        "abertura_teorica": float(est.get("abertura_teorica_pontos", 0.0) or 0.0),
        "preco_referencia_base": float(est.get("preco_referencia_base", 0.0) or 0.0),
        "variacao_teorica_pct": float(est.get("variacao_teorica_pct", 0.0) or 0.0),
    }


def carregar_leilao_ocr() -> dict:
    """
    Lê o preço do leilão via LeilaoService (OCR).
    Retorna dict do service. Em caso de erro, retorna indisponível.
    """
    try:
        from v2.core.services.leilao_service import LeilaoService
        svc = LeilaoService(PASTA_COLETAS)
        return svc.obter_preco_leilao()
    except Exception as e:
        return {
            "disponivel": False,
            "preco": None,
            "timestamp": None,
            "fonte": f"ERRO: {e}",
        }


def carregar_historico_csv_recente(limite: int = 15) -> pd.DataFrame:
    """
    Lê as últimas N leituras do CSV do OCR.
    Usa o mesmo parser do LeilaoService (evita BOM, header, formato de data).
    """
    if not ARQUIVO_CSV.exists():
        return pd.DataFrame()

    registros = []
    try:
        with open(ARQUIVO_CSV, "r", encoding="utf-8-sig") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or not linha[0].isdigit():
                    continue
                partes = linha.split(",")
                if len(partes) < 2:
                    continue
                try:
                    dt = datetime.strptime(partes[0].strip(), "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        dt = datetime.strptime(partes[0].strip(), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                try:
                    preco = float(partes[1])
                    conf = float(partes[2]) if len(partes) > 2 else 0.0
                except ValueError:
                    continue
                registros.append({
                    "DataHora": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "PrecoTeorico": int(preco),
                    "Confianca": f"{conf:.3f}",
                })
    except Exception:
        return pd.DataFrame()

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    return df.tail(limite).iloc[::-1]


# ------------------------------------------------------------
# Fragmento em tempo real
# ------------------------------------------------------------

@st.fragment(run_every=1)
def renderizar_dashboard_tempo_real():
    # ---- Carrega dados ----
    macro_data = carregar_json(ARQUIVO_JSON_MACRO).get("ativos", {})
    smc_data = carregar_json(ARQUIVO_JSON_SMC)
    smc_mtf = carregar_json(ARQUIVO_JSON_MTF)
    estimativa_calc = carregar_estimativa_calculada()
    leilao = carregar_leilao_ocr()

    # ---- Valores de referência ----
    win_ajuste = macro_data.get("WIN_AJUSTE", {}).get("preco", 0)
    win_fechamento = macro_data.get("WIN_LAST_TICK", {}).get("preco", 0)
    poc_ontem = smc_data.get("niveis_institucionais", {}).get("poc_ontem", 0)
    vies_smc = smc_data.get("bias_direcional", "NEUTRO")

    # ---- Viés macro (simples) ----
    ewz_var = macro_data.get("EWZ", {}).get("variacao_pct", 0)
    sp500_var = macro_data.get("SP500_FUT", {}).get("variacao_pct", 0)
    score_macro = ((ewz_var * 2) + sp500_var) / 3
    if score_macro > 0.3:
        vies_macro = "ALTA 🟢"
    elif score_macro < -0.3:
        vies_macro = "BAIXA 🔴"
    else:
        vies_macro = "NEUTRO 🟡"

    # ---- Valores das duas aberturas ----
    abertura_leilao = float(leilao.get("preco") or 0.0)
    abertura_calculada = float(estimativa_calc.get("abertura_teorica") or 0.0)

    # ------------------------------------------------------------
    # SEÇÃO 1 — Duas aberturas LADO A LADO
    # ------------------------------------------------------------
    st.markdown("## 💰 Aberturas Teóricas (Lado a Lado)")

    col_calc, col_leilao = st.columns(2)

    # ---- Coluna Esquerda: Abertura Calculada ----
    with col_calc:
        st.markdown("### 📊 Abertura Teórica (Calculada)")
        if abertura_calculada > 0:
            gap_calc = abertura_calculada - win_ajuste if win_ajuste > 0 else 0
            st.metric(
                label="Preço Teórico Calculado",
                value=f"{abertura_calculada:,.0f}",
                delta=f"{gap_calc:+.0f} pts vs ajuste",
            )
            st.caption(
                f"Base: {estimativa_calc.get('preco_referencia_base', 0):,.0f} | "
                f"Var: {estimativa_calc.get('variacao_teorica_pct', 0):+.4f}%"
            )
            st.caption("Fonte: `CalculadoraEstimativaAbertura.py`")
        else:
            st.info("⏳ Abertura calculada indisponível")

    # ---- Coluna Direita: Abertura do Leilão (OCR) ----
    with col_leilao:
        st.markdown("### 🎯 Abertura Teórica (Leilão OCR)")
        if leilao.get("disponivel") and abertura_leilao > 0:
            gap_leilao = abertura_leilao - win_ajuste if win_ajuste > 0 else 0
            ts = leilao.get("timestamp", "")
            st.metric(
                label="Preço Teórico do Leilão",
                value=f"{abertura_leilao:,.0f}",
                delta=f"{gap_leilao:+.0f} pts vs ajuste",
            )
            st.caption(
                f"Última leitura: {ts} | "
                f"Total: {leilao.get('total_leituras', 0)}"
            )
            st.caption(
                f"Faixa do leilão: {leilao.get('preco_min', 0):,.0f} "
                f"→ {leilao.get('preco_max', 0):,.0f}"
            )
        else:
            st.warning("⏳ OCR do leilão indisponível")
            st.caption(f"Motivo: {leilao.get('fonte', 'N/A')}")

    # ---- Divergência entre os dois ----
    if abertura_calculada > 0 and abertura_leilao > 0:
        divergencia = abertura_leilao - abertura_calculada
        if abs(divergencia) > 200:
            st.warning(
                f"⚠️ **Divergência entre as duas fontes:** {divergencia:+,.0f} pts. "
                "O OCR e o cálculo estão distantes — verifique qual usar."
            )
        else:
            st.success(
                f"✅ **Fontes alinhadas:** diferença de {divergencia:+,.0f} pts."
            )

    st.markdown("---")

    # ------------------------------------------------------------
    # SEÇÃO 2 — Métricas principais
    # ------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📈 Ajuste B3", f"{win_ajuste:,.0f}")
    with col2:
        st.metric("📉 Último Fechamento", f"{win_fechamento:,.0f}")
    with col3:
        st.metric("🏢 POC Ontem", f"{poc_ontem:,.0f}")
    with col4:
        gap_poc = (abertura_leilao or abertura_calculada) - poc_ontem if poc_ontem > 0 else 0
        st.metric("📊 Distância da POC", f"{gap_poc:+,.0f} pts")

    st.markdown("---")

    # ------------------------------------------------------------
    # SEÇÃO 3 — Contexto e Veredito
    # ------------------------------------------------------------
    c_left, c_right = st.columns([1, 2])

    with c_left:
        st.subheader("🌐 Contexto Macro / SMC")
        st.info(f"**Viés Macro:** {vies_macro}")
        st.info(f"**Viés Estrutural SMC:** {vies_smc}")
        st.text(f"Score Macro: {score_macro:+.3f}")

        # ---------- MTF: contexto multi-timeframe (fix32) ----------
        _conf_mtf = (smc_mtf or {}).get("confluencia") or {}
        if _conf_mtf:
            _ver = _conf_mtf.get("veredito_mtf") or "—"
            _dir = _conf_mtf.get("direcao_dominante") or "—"
            _rac = _conf_mtf.get("racional") or ""
            _b15 = _conf_mtf.get("bias_m15") or "—"
            _b5 = _conf_mtf.get("bias_m5") or "—"
            _b1 = _conf_mtf.get("bias_m1") or "—"
            _c15 = _conf_mtf.get("confianca_m15")
            _c5 = _conf_mtf.get("confianca_m5")
            _c1 = _conf_mtf.get("confianca_m1")

            st.markdown("#### 🧭 Multi-Timeframe (M15 / M5 / M1)")

            def _cor_bias(_b):
                _s = str(_b or "").upper()
                if "ALTA" in _s or "COMPRA" in _s or "BULL" in _s:
                    return "#22c55e"
                if "BAIXA" in _s or "VENDA" in _s or "BEAR" in _s:
                    return "#ef4444"
                return "#a3a3a3"

            def _card_bias(col, label, bias, conf):
                _cor = _cor_bias(bias)
                _conf = f"{conf}%" if conf is not None else "—"
                with col:
                    st.markdown(
                        f"<div style='padding:10px 14px;border-radius:8px;"
                        f"background:rgba(255,255,255,0.03);"
                        f"border-left:3px solid {_cor};'>"
                        f"<div style='font-size:0.85rem;color:#9ca3af;'>{label}</div>"
                        f"<div style='font-size:1.5rem;font-weight:700;color:{_cor};"
                        f"line-height:1.2;margin-top:2px;'>{bias}</div>"
                        f"<div style='font-size:0.8rem;color:#6b7280;margin-top:2px;'>"
                        f"Confiança: {_conf}</div></div>",
                        unsafe_allow_html=True,
                    )

            _ccols = st.columns(3)
            _card_bias(_ccols[0], "M15 (macro)", _b15, _c15)
            _card_bias(_ccols[1], "M5 (médio)", _b5, _c5)
            _card_bias(_ccols[2], "M1 (micro)", _b1, _c1)

            _msg = f"**{_ver}** — direção dominante: `{_dir}`"
            if _rac:
                _msg += f"\n\n{_rac}"

            if _ver == "ALINHADO_FORTE":
                st.success(_msg)
            elif _ver in ("REVERSAO_MICRO_MEDIO", "CONFLITO_MACRO"):
                st.warning(_msg)
            elif _ver == "DIVERGENTE":
                st.error(_msg)
            else:
                st.info(_msg)
        # ---------- fim MTF ----------

    with c_right:
        st.subheader("🎯 Veredito Operacional (Confluência)")

        # Usa o preço do LEILÃO como base (mais realista)
        preco_ref = abertura_leilao if abertura_leilao > 0 else abertura_calculada
        gap_ajuste = preco_ref - win_ajuste if win_ajuste > 0 and preco_ref > 0 else 0

        # ---- Normaliza direções pra COMPRA / VENDA / NEUTRO ----
        def normalizar(v: str) -> str:
            if not v:
                return "NEUTRO"
            s = str(v).upper()
            if "ALTA" in s or "COMPRA" in s or "BULL" in s:
                return "COMPRA"
            if "BAIXA" in s or "VENDA" in s or "BEAR" in s:
                return "VENDA"
            return "NEUTRO"

        dir_macro = normalizar(vies_macro)
        dir_smc = normalizar(vies_smc)
        dir_gap = "COMPRA" if gap_ajuste > 100 else "VENDA" if gap_ajuste < -100 else "NEUTRO"

        # ---- Conta votos ----
        votos = {"COMPRA": 0, "VENDA": 0, "NEUTRO": 0}
        votos[dir_macro] += 1
        votos[dir_smc] += 1
        votos[dir_gap] += 1

        # ---- Renderiza os 3 contextos ----
        st.markdown(
            f"**Macro:** `{dir_macro}` &nbsp;&nbsp; "
            f"**SMC:** `{dir_smc}` &nbsp;&nbsp; "
            f"**Gap Leilão:** `{dir_gap}` ({gap_ajuste:+.0f} pts)"
        )

        # ---- Veredito por confluência ----
        if preco_ref <= 0:
            st.warning("⏳ Aguardando captura válida do preço teórico...")

        elif votos["COMPRA"] == 3:
            st.success(
                "### 🟢 COMPRA A MERCADO\n"
                "**Confluência total:** Macro + SMC + Gap alinhados em ALTA."
            )

        elif votos["VENDA"] == 3:
            st.error(
                "### 🔴 VENDA A MERCADO\n"
                "**Confluência total:** Macro + SMC + Gap alinhados em BAIXA."
            )

        elif votos["COMPRA"] == 2:
            st.info(
                "### 🟡 COMPRA MODERADA\n"
                "2 de 3 contextos em ALTA. Reduza tamanho ou aguarde confirmação."
            )

        elif votos["VENDA"] == 2:
            st.info(
                "### 🟡 VENDA MODERADA\n"
                "2 de 3 contextos em BAIXA. Reduza tamanho ou aguarde confirmação."
            )

        else:
            st.warning(
                "### ⚠️ NEUTRO / FINTA\n"
                "Contextos divergentes. **Fique de fora** até alinhamento."
            )
                    
    # ------------------------------------------------------------
    # SEÇÃO 4 — Histórico recente do CSV
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📜 Histórico Recente de Capturas do Leilão")

    df_historico = carregar_historico_csv_recente(limite=15)
    if not df_historico.empty:
        st.dataframe(df_historico, use_container_width=True, hide_index=True)
    else:
        st.info("O arquivo CSV será exibido assim que a coleta iniciar.")


# Executa o bloco em tempo real
renderizar_dashboard_tempo_real()
```

### `pages/2_🎯_Setup_Abertura.py`

```python
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
from config import MAPEAMENTO_TICKERS, MAPEAMENTO_TICKERS_INVERSO, ADRS_COMPOSTO

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


# Mapa chave interna → ticker bruto no rom-5



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
    ticker = MAPEAMENTO_TICKERS_INVERSO.get(chave_interna, chave_interna)
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
    ticker = MAPEAMENTO_TICKERS_INVERSO.get(chave_interna, chave_interna)
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
                f"Ant {score_ant:+.2f}" if score_ant is not None else "",
                inverter=False,
                valor_anterior=score_ant,
            )
        with e2:
            mini_velocimetro(
                ind_adrs, "🇧🇷 Σ ADRs",
                f"Ant {ind_adrs_ant:+.2f}%" if ind_adrs_ant is not None else "",
                inverter=False,
                valor_anterior=ind_adrs_ant,
            )
        with e3:
            mini_velocimetro(
                ind_ext, "🌍 Σ Macro",
                f"Ant {ind_ext_ant:+.2f}%" if ind_ext_ant is not None else "",
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
            f"Ant {pen_m:+.2f}%" if pen_m is not None else "",
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
            f"Ant {pen_a:+.2f}%" if pen_a is not None else "",
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
    smc_mtf, _ = carregar_json_absoluto("AnaliseGraficaSMC_MTF.json")
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
    # Fallback: se WIN_LAST_TICK nao existe (durante o pregao, pois o
    # LastTick_Congelado.json so e gravado fora do pregao), usa o fechamento
    # oficial da brapi (WIN_FECHAMENTO_B3), que e o mesmo valor conceitual.
    if win_last_v is None:
        win_last_v = get_p_num("WIN_FECHAMENTO_B3")
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
            t_alt = next((k for k, v in MAPEAMENTO_TICKERS.items() if v == t_ativo), "")
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
        # ---------- MTF: contexto multi-timeframe (fix28) ----------
        if smc_mtf:
            conf = smc_mtf.get("confluencia") or {}
            _ver = conf.get("veredito_mtf") or "—"
            _dir = conf.get("direcao_dominante") or "—"
            _rac = conf.get("racional") or ""
            _b15 = conf.get("bias_m15") or "—"
            _b5 = conf.get("bias_m5") or "—"
            _b1 = conf.get("bias_m1") or "—"
            _c15 = conf.get("confianca_m15")
            _c5 = conf.get("confianca_m5")
            _c1 = conf.get("confianca_m1")

            st.markdown("### 🧭 Contexto Multi-Timeframe (M15 / M5 / M1)")

            def _cor_bias(_b):
                _s = str(_b or "").upper()
                if "ALTA" in _s or "COMPRA" in _s or "BULL" in _s:
                    return "#22c55e"
                if "BAIXA" in _s or "VENDA" in _s or "BEAR" in _s:
                    return "#ef4444"
                return "#a3a3a3"

            def _card_bias(col, label, bias, conf):
                _cor = _cor_bias(bias)
                _conf = f"{conf}%" if conf is not None else "—"
                with col:
                    st.markdown(
                        f"<div style='padding:10px 14px;border-radius:8px;"
                        f"background:rgba(255,255,255,0.03);"
                        f"border-left:3px solid {_cor};'>"
                        f"<div style='font-size:0.85rem;color:#9ca3af;'>{label}</div>"
                        f"<div style='font-size:1.5rem;font-weight:700;color:{_cor};"
                        f"line-height:1.2;margin-top:2px;'>{bias}</div>"
                        f"<div style='font-size:0.8rem;color:#6b7280;margin-top:2px;'>"
                        f"Confiança: {_conf}</div></div>",
                        unsafe_allow_html=True,
                    )

            _cols = st.columns(3)
            _card_bias(_cols[0], "M15 (macro)", _b15, _c15)
            _card_bias(_cols[1], "M5 (médio)", _b5, _c5)
            _card_bias(_cols[2], "M1 (micro)", _b1, _c1)

            _cor = {
                "ALINHADO_FORTE": "success",
                "PULLBACK": "info",
                "REVERSAO_MICRO_MEDIO": "warning",
                "CONFLITO_MACRO": "warning",
                "DIVERGENTE": "error",
                "NEUTRO": "info",
                "SEM_DIRECAO": "info",
            }.get(_ver, "info")

            _msg = f"**{_ver}** — direção dominante: `{_dir}`"
            if _rac:
                _msg += f"\n\n{_rac}"

            if _cor == "success":
                st.success(_msg)
            elif _cor == "warning":
                st.warning(_msg)
            elif _cor == "error":
                st.error(_msg)
            else:
                st.info(_msg)
        # ---------- fim MTF ----------

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
```

### `pages/3_⚡_Monitor_Abertura_Leilao.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/3.2_⚡_Monitor_Abertura_Leilao_V3.2.py
Versão: 3.6.0 - Monitor de Leilão + Termômetro + Auto-refresh (60s)
Objetivo: Monitorar formação de preço, leilão, fluxo institucional externo e spreads de arbitragem B3 vs ADRs.
"""

import logging
from pathlib import Path
from typing import Optional
import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

from config import FILE_MT5_V2, FILE_UNIFICADO, FILE_DECISAO_V2, FILE_METRICAS, MAPEAMENTO_ADR_B3, MAPEAMENTO_TICKERS_INVERSO, MAPA_B3_PARA_ADR, ADRS_COMPOSTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Quant Terminal - Monitor de Leilão & Fluxo",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==============================================================================
# MAPEAMENTOS
# ==============================================================================

# ✅ Direto: Ação B3 → chave do ADR no unificado/rom-5



# ==============================================================================
# MINI VELOCÍMETRO (com ponteiro anterior + delta)
# ==============================================================================
def mini_velocimetro(
    valor,
    label: str,
    preco_fmt: str = "",
    inverter: bool = False,
    valor_anterior=None,
) -> None:
    # Valor atual
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

    # Valor anterior (ponteiro branco)
    svg_anterior = ""
    texto_delta = ""
    if valor_anterior is not None:
        try:
            real_ant = max(-10.0, min(10.0, float(valor_anterior)))
            angulo_ant = (real_ant / 10.0) * 90.0
            # ✅ Ponteiro branco mais visível (mais largo e mais opaco)
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
            padding: 2px 0;
        }}
        .mini-label {{
            font-size: 12px;
            color: #c9d1d9;
            margin-bottom: 1px;
            text-align: center;
            font-weight: 700;
            white-space: nowrap;
        }}
        .mini-gauge {{
            position: relative;
            width: 130px;
            height: 68px;
        }}
        .mini-arc {{
            position: absolute; left: 5px; top: 3px;
            width: 120px; height: 60px;
            border-radius: 120px 120px 0 0;
            background: conic-gradient(
                from 270deg at 50% 100%,
                #ff2020 0deg 30deg,
                #b02020 30deg 60deg,
                #602020 60deg 90deg,
                #206020 90deg 120deg,
                #00a030 120deg 150deg,
                #00cc44 150deg 180deg
            );
            -webkit-mask: radial-gradient(circle at 50% 100%, transparent 38px, black 39px);
                    mask: radial-gradient(circle at 50% 100%, transparent 38px, black 39px);
        }}
        .mini-needle {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 8px;
            height: 58px;
            margin-left: -4px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 3;
        }}
        .mini-needle-ant {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 14px;
            height: 52px;
            margin-left: -7px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2;
        }}
        .mini-pivot {{
            position: absolute;
            left: 50%;
            bottom: 0px;
            width: 12px; height: 12px;
            margin-left: -6px;
            border-radius: 50%;
            background: {cor};
            z-index: 4;
            transition: background 0.5s ease;
        }}
        .mini-value {{
            font-size: 15px;
            font-weight: 900;
            color: {cor};
            text-align: center;
            margin-top: 4px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
            line-height: 1.1;
        }}
        .mini-sub {{
            font-size: 10px;
            color: #8b949e;
            text-align: center;
            margin-top: 2px;
            line-height: 1.1;
        }}
        .mini-delta {{
            font-size: 10px;
            color: #c9d1d9;
            text-align: center;
            margin-top: 4px;
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
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 58">
                    <path d="M 4 0 L 5.5 52 L 2.5 52 Z" fill="#ffffff"/>
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
    components.html(html, height=145, scrolling=False)


@st.cache_data(ttl=5)
def carregar_json_defensivo(caminho) -> dict:
    if not caminho or not Path(caminho).exists():
        logger.warning(f"Arquivo não encontrado: {caminho}")
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Erro de decodificação JSON no arquivo {caminho}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Erro inesperado ao ler {caminho}: {e}")
        return {}


def carregar_rom5() -> dict:
    from config import COLETAS_DIR
    caminho = Path(COLETAS_DIR) / "Coleta_rom-5.json"
    return carregar_json_defensivo(caminho)


# ==============================================================================
# HELPERS PARA RECALCULAR INDICADORES A PARTIR DO ROM-5
# ==============================================================================
def _get_var_rom5(rom5: dict, chave_interna: str) -> Optional[float]:
    if not rom5:
        return None
    ticker = MAPEAMENTO_TICKERS_INVERSO.get(chave_interna, chave_interna)
    for item in rom5.get("coletas", []):
        if item.get("ativo") == ticker:
            val = (item.get("dados_reais") or {}).get("change_percent")
            if isinstance(val, (int, float)):
                return float(val)
    return None


def calcular_ind_adrs_rom5(rom5: dict) -> Optional[float]:
    vals = []
    for adr in ADRS_COMPOSTO:
        v = _get_var_rom5(rom5, adr)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    return round(sum(vals), 4)


def calcular_ind_externo_rom5(rom5: dict) -> Optional[float]:
    vix = _get_var_rom5(rom5, "VIX")
    crude = _get_var_rom5(rom5, "CRUDE_OIL")
    iron = _get_var_rom5(rom5, "IRON_ORE_2M")
    if vix is None or crude is None or iron is None:
        return None
    return round(-vix + crude + iron, 4)


def calcular_ewz_rom5(rom5: dict) -> Optional[float]:
    return _get_var_rom5(rom5, "EWZ")


def calcular_spread_rom5(acao: str, rom5: dict) -> Optional[float]:
    """
    Recalcula o spread NY - B3 para uma ação usando dados do rom-5.
    ✅ Usa MAPA_B3_PARA_ADR diretamente (sem inversão).
    """
    adr_key = MAPA_B3_PARA_ADR.get(acao)
    if not adr_key:
        return None

    var_adr = _get_var_rom5(rom5, adr_key)
    var_b3 = _get_var_rom5(rom5, acao)

    if var_adr is None or var_b3 is None:
        return None
    return round(var_adr - var_b3, 2)


# ==============================================================================
# CARD DE FUTURO (WIN/WDO)
# ==============================================================================
def renderizar_cartao_futuro(titulo: str, data_ativo: dict, eh_dolar: bool = False):
    st.markdown(f"#### {titulo}")

    if not data_ativo or data_ativo.get("status") != "OK":
        st.warning("⚠️ Dados do leilão indisponíveis no snapshot do MT5.")
        return

    contrato = data_ativo.get("contrato_principal", "N/A")
    vencimento_bruto = data_ativo.get("vencimento", "N/A")
    vencimento = vencimento_bruto[:10] if isinstance(vencimento_bruto, str) and len(vencimento_bruto) >= 10 else "N/A"

    preco_teorico = data_ativo.get("preco_teorico", 0.0) or 0.0
    last_price = data_ativo.get("last", 0.0) or 0.0

    st.markdown(f"**Contrato Ativo:** `{contrato}` | **Vencimento:** `{vencimento}`")

    if eh_dolar:
        fmt_str = ",.4f"
        delta_val = preco_teorico - last_price
        delta_str = f"{delta_val:+.4f} vs Último"
        sufixo = ""
    else:
        fmt_str = ",.0f"
        delta_val = preco_teorico - last_price
        delta_str = f"{delta_val:+.0f} pts vs Último"
        sufixo = " pts"

    if preco_teorico > 0:
        st.metric("Preço Teórico do Leilão", f"{preco_teorico:{fmt_str}}{sufixo}", delta=delta_str)
    else:
        st.metric("Último Preço (Mercado Aberto/Ajustado)", f"{last_price:{fmt_str}}{sufixo}")
        st.caption("💡 Preço teórico indisponível fora do horário de leilão (08:50 - 09:00).")


# ==============================================================================
# CORPO DA PÁGINA (AUTO-REFRESH 60s)
# ==============================================================================
@st.fragment(run_every=60)
def render_body():
    dados_mt5 = carregar_json_defensivo(FILE_MT5_V2)
    dados_unificados = carregar_json_defensivo(FILE_UNIFICADO)
    dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
    dados_metricas = carregar_json_defensivo(FILE_METRICAS)
    rom5 = carregar_rom5()

    st.markdown("<h2 style='color:#00d4ff;'>⚡ Monitor de Abertura e Leilão B3</h2>", unsafe_allow_html=True)
    timestamp_snapshot = dados_mt5.get('timestamp', 'N/A')
    st.caption(
        f"Último snapshot capturado pelo pipeline: `{timestamp_snapshot}` · "
        f"auto-refresh: 60s · ⚪ ponteiro branco = valor de 5 min atrás"
    )

    # --- SEÇÃO 0: TERMÔMETRO DE FLUXO ESTRANGEIRO ---
    st.markdown("### 🏦 Termômetro Estatístico de Fluxo Estrangeiro")
    st.caption("Ponteiro centrado em zero · 🟢 positivo = favorável ao risco · 🔴 negativo = aversão ao risco")

    ind_compostos = dados_metricas.get("indicadores_compostos", {})
    ind_adrs = ind_compostos.get("indicador_adrs_brasileiras")
    ind_externo = ind_compostos.get("indicador_mercado_externo")
    ewz_pct = dados_metricas.get("performance_relativa", {}).get("ewz_change_pct", 0.0)

    ind_adrs_ant = calcular_ind_adrs_rom5(rom5)
    ind_externo_ant = calcular_ind_externo_rom5(rom5)
    ewz_pct_ant = calcular_ewz_rom5(rom5)

    c1, c2, c3 = st.columns(3)

    with c1:
        mini_velocimetro(
            ind_adrs,
            "🇧🇷 Indicador Composto ADRs BR",
            f"{ind_adrs:+.2f}%" if ind_adrs is not None else "",
            inverter=False,
            valor_anterior=ind_adrs_ant,
        )
        if ind_adrs is not None:
            if ind_adrs > 0.5:
                st.caption("📈 **Fluxo Comprador** — ADRs sinalizando entrada de capital")
            elif ind_adrs < -0.5:
                st.caption("📉 **Fluxo Vendedor** — ADRs sinalizando saída de capital")
            else:
                st.caption("⚖️ **Estável** — sem direção clara")

    with c2:
        mini_velocimetro(
            ind_externo,
            "🌍 Indicador de Mercado Externo",
            f"{ind_externo:+.2f}%" if ind_externo is not None else "",
            inverter=False,
            valor_anterior=ind_externo_ant,
        )
        if ind_externo is not None:
            if ind_externo > 0.5:
                st.caption("✅ **Favorável ao Risco** — VIX/Petróleo/Minério colaborando")
            elif ind_externo < -0.5:
                st.caption("⚠️ **Aversão ao Risco** — pressão externa negativa")
            else:
                st.caption("⚖️ **Neutro** — sem pressão clara")

    with c3:
        mini_velocimetro(
            ewz_pct,
            "🇺🇸 EWZ (ETF Brasil em NY)",
            f"{ewz_pct:+.2f}%" if ewz_pct is not None else "",
            inverter=False,
            valor_anterior=ewz_pct_ant,
        )
        if ewz_pct is not None:
            if ewz_pct > 0.5:
                st.caption("🟢 **Brasil atrativo** — fundo NY comprando B3")
            elif ewz_pct < -0.5:
                st.caption("🔴 **Brasil rejeitado** — fundo NY vendendo B3")
            else:
                st.caption("⚖️ **Neutro** — fluxo equilibrado")

    st.markdown("---")

    # --- SEÇÃO 1: WIN E WDO ---
    st.markdown("### 📊 Status dos Contratos Vigentes")

    ativos_mt5 = dados_mt5.get("ativos", {})
    win_data = ativos_mt5.get("WIN", {})
    wdo_data = ativos_mt5.get("WDO", {})

    col_win, col_wdo = st.columns(2)
    with col_win:
        renderizar_cartao_futuro("🔹 Mini Índice Future", win_data, eh_dolar=False)
    with col_wdo:
        renderizar_cartao_futuro("💵 Mini Dólar Future", wdo_data, eh_dolar=True)

    st.markdown("---")

    # --- SEÇÃO 2: ARBITRAGEM ---
    st.markdown("### 🏦 Leilão do Mercado à Vista vs ADRs (Arbitragem)")
    st.caption("Análise de descasamento e spread para abertura das ações às 10:00h")

    acoes_foco = ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"]
    ativos_unificados = dados_unificados.get("ativos", {})

    linhas_tabela = []
    for acao in acoes_foco:
        if acao in ativos_unificados:
            dados_acao = ativos_unificados[acao]
            ticker_adr = MAPA_B3_PARA_ADR.get(acao, f"{acao}_ADR")

            var_adr = ativos_unificados.get(ticker_adr, {}).get("variacao_pct", 0.0) or 0.0
            var_b3 = dados_acao.get("variacao_pct", 0.0) or 0.0
            preco_acao = dados_acao.get("preco", 0.0) or 0.0

            spread = var_adr - var_b3

            if spread >= 0.5:
                sinal = "🟢 COMPRA B3 (Atrasada)"
            elif spread <= -0.5:
                sinal = "🔴 VENDA B3 (Esticada)"
            else:
                sinal = "⚖️ Alinhado"

            linhas_tabela.append({
                "Ativo B3": acao,
                "Preço Indicativo": f"R$ {preco_acao:,.2f}",
                "Var B3 (%)": f"{var_b3:+.2f}%",
                "Var ADR NY (%)": f"{var_adr:+.2f}%",
                "Spread (NY - B3)": f"{spread:+.2f}%",
                "Sinal Arbitragem": sinal,
                "_spread_raw": spread,
            })

    if linhas_tabela:
        df_arbitragem = pd.DataFrame([{k: v for k, v in l.items() if k != "_spread_raw"} for l in linhas_tabela])
        st.dataframe(df_arbitragem, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Aguardando atualização do arquivo de ativos unificados para calcular spreads de arbitragem.")

    if linhas_tabela:
        st.markdown("##### 📊 Spreads por Ação (NY − B3)")
        st.caption("Ponteiro centrado em zero · 🟢 positivo = B3 atrasada (compra) · 🔴 negativo = B3 esticada (venda)")

        cols_arb = st.columns(6)
        for idx, linha in enumerate(linhas_tabela):
            with cols_arb[idx]:
                spread_val = linha["_spread_raw"]
                spread_ant = calcular_spread_rom5(linha["Ativo B3"], rom5)

                mini_velocimetro(
                    spread_val,
                    linha["Ativo B3"],
                    f"{spread_val:+.2f}%",
                    inverter=False,
                    valor_anterior=spread_ant,
                )

    # --- SEÇÃO 3: TRAVA DE RISCO ---
    st.markdown("---")
    st.markdown("### 🛡️ Alinhamento de Risco do Orquestrador V2")

    decisao_data = dados_v2.get("decisao", {})
    vies_macro = decisao_data.get("vies_final", "NEUTRO")
    riscos_v2 = decisao_data.get("riscos", [])

    col_vies, col_status_risco = st.columns([1, 3])
    with col_vies:
        st.metric("Viés Consolidado V2", vies_macro)

    with col_status_risco:
        if riscos_v2:
            st.markdown("**Alertas de Risco Ativos para a Abertura:**")
            for risco in riscos_v2:
                st.markdown(f"⚠️ `{risco}`")
        else:
            st.success("🟢 Zero travas quantitativas ou riscos extremos reportados pelo Orquestrador V2.")

    # --- SEÇÃO 4: NOTA ---
    st.markdown("---")
    st.markdown("💡 **Nota de Trading:** Grandes descolamentos (maiores que ±0.50%) em papéis de alta liquidez como VALE3 e PETR4 costumam ser fechados rapidamente por robôs de arbitragem institucionais de alta frequência nas primeiras horas do pregão à vista brasileiro.")


render_body()
```

### `pages/4_⚡_WINFUT_Intraday.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/5.1_WINFUT_Intraday.py
Versão: 3.4 - Cockpit com Mini Velocímetros + Ponteiro Anterior + Auto-refresh (60s)
Objetivo: Cockpit de Decisão Intraday para monitoramento de ativos direcionais do WIN.

Notas:
  - A cada 60s o corpo da página é re-renderizado via @st.fragment(run_every=60).
  - Cada velocímetro mostra:
      • Ponteiro colorido  → valor ATUAL
      • Ponteiro branco    → valor ANTERIOR (coleta de 5 min atrás)
      • Delta (Δ)          → diferença entre os dois
"""

import json
from datetime import datetime
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Quant Terminal - Cockpit Intraday WINFUT",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚡ WINFUT — Cockpit de Decisão Intraday")


# ==============================================================================
# MAPEAMENTO: chaves amigáveis → nomes de tickers no rom-5
# ==============================================================================
ALIASES_BUSCA_ROM5 = {
    "SP500_FUT": ["CME_MINI:ES1!", "SP500_FUT"],
    "NASDAQ_FUT": ["CME_MINI:NQ1!", "NASDAQ_FUT"],
    "EWZ": ["AMEX:EWZ", "EWZ"],
    "DXY": ["TVC:DXY", "DXY"],
    "WDO": ["BMFBOVESPA:WDO1!", "WDO_FUT", "WDO"],
    "VIX": ["TVC:VIX", "VIX"],
    "VALE3": ["VALE3"],
    "PETR4": ["PETR4"],
    "ITUB4": ["ITUB4"],
    "BBDC4": ["BBDC4"],
    "BBAS3": ["BBAS3"],
    "IRON_ORE": ["SGX:FEF1!", "IRON_ORE"],
    "CRUDE_OIL": ["NYMEX:CL1!", "CRUDE_OIL"],
    "DI1_2027": ["BMFBOVESPA:DI1F2027", "DI1_2027"],
    "DI1_2029": ["BMFBOVESPA:DI1F2029", "DI1_2029"],
}


# ==============================================================================
# MINI VELOCÍMETRO (centro em zero, estilo flat design)
# ==============================================================================
def mini_velocimetro(
    valor,
    label: str,
    preco_fmt: str = "",
    inverter: bool = False,
    valor_anterior=None,
) -> None:
    """
    Mini velocímetro com ponteiro duplo:
    - Ponteiro colorido  → valor ATUAL
    - Ponteiro branco    → valor ANTERIOR (5 min atrás)
    - Delta (Δ)          → diferença atual - anterior
    """
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
                f'viewBox="0 0 8 52">'
                f'<path d="M 4 0 L 5 46 L 3 46 Z" fill="rgba(255,255,255,0.55)"/>'
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
            padding: 2px 0;
        }}
        .mini-label {{
            font-size: 11px;
            color: #c9d1d9;
            margin-bottom: 1px;
            text-align: center;
            font-weight: 700;
            white-space: nowrap;
        }}
        .mini-gauge {{
            position: relative;
            width: 120px;
            height: 62px;
        }}
        .mini-arc {{
            position: absolute; left: 5px; top: 3px;
            width: 110px; height: 55px;
            border-radius: 110px 110px 0 0;
            background: conic-gradient(
                from 270deg at 50% 100%,
                #ff2020 0deg 30deg,
                #b02020 30deg 60deg,
                #602020 60deg 90deg,
                #206020 90deg 120deg,
                #00a030 120deg 150deg,
                #00cc44 150deg 180deg
            );
            -webkit-mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
                    mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
        }}
        .mini-needle {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 8px;
            height: 52px;
            margin-left: -4px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 3;
        }}
        .mini-needle-ant {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 8px;
            height: 48px;
            margin-left: -4px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2;
        }}
        .mini-pivot {{
            position: absolute;
            left: 50%;
            bottom: 0px;
            width: 12px; height: 12px;
            margin-left: -6px;
            border-radius: 50%;
            background: {cor};
            z-index: 4;
            transition: background 0.5s ease;
        }}
        .mini-value {{
            font-size: 14px;
            font-weight: 900;
            color: {cor};
            text-align: center;
            margin-top: 4px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
            line-height: 1.1;
        }}
        .mini-sub {{
            font-size: 10px;
            color: #8b949e;
            text-align: center;
            margin-top: 2px;
            line-height: 1.1;
        }}
        .mini-delta {{
            font-size: 10px;
            color: #c9d1d9;
            text-align: center;
            margin-top: 4px;
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
    components.html(html, height=145, scrolling=False)


# ==============================================================================
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[2] if len(ARQUIVO_ATUAL.parents) >= 3 else ARQUIVO_ATUAL.parent


@st.cache_data(ttl=2)
def carregar_dados_absolutos() -> tuple:
    """Carrega de forma defensiva os arquivos JSON do pipeline quant."""
    def buscar_json(nome: str) -> tuple:
        locais = [
            RAIZ_PROJETO / nome,
            RAIZ_PROJETO / "Coletas" / nome,
            RAIZ_PROJETO / "v2" / nome,
            RAIZ_PROJETO / "json" / nome,
            Path.cwd() / nome,
            Path.cwd() / "Coletas" / nome
        ]
        for path in locais:
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f), str(path)
                except Exception:
                    pass
        return {}, None

    decisao_v2, _ = buscar_json("Decisao_V2.json")
    smc_regras, _ = buscar_json("AnaliseGraficaSMC_Regras.json")
    if not smc_regras:
        smc_regras, _ = buscar_json("Resultado_SMC.json")

    unificados, _ = buscar_json("DadosAtivosUnificados.json")
    dados_mt5, _ = buscar_json("Dados_MT5_v2_2.json")
    dados_val, _ = buscar_json("Dados_Validados.json")

    # Coleta de 5 minutos atrás (para o ponteiro anterior)
    rom5, _ = buscar_json("Coleta_rom-5.json")

    return decisao_v2, smc_regras, unificados, dados_mt5, dados_val, rom5


# ==============================================================================
# FUNÇÕES DE BUSCA DE DADOS (PREÇO E VARIAÇÃO)
# ==============================================================================
def extrair_valor_objeto(obj, comp_chave: str = "var"):
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        chaves_val = (
            ["last", "ultimo", "close", "preco", "price", "bid", "ask"]
            if comp_chave == "ultimo"
            else ["var", "variacao", "change", "pct", "pct_change", "v", "value", "variacao_pct"]
        )
        for k in chaves_val:
            if k in obj and isinstance(obj[k], (int, float)):
                return float(obj[k])
    return None


def buscar_metrica(chaves_busca: list, tipo_campo: str = "var", fontes: list = None) -> float:
    """Busca o valor (preço ou variação) navegando pelas fontes de dados."""
    if fontes is None:
        return 0.0

    for fonte in fontes:
        if not fonte:
            continue

        if isinstance(fonte, list):
            for item in fonte:
                if isinstance(item, dict):
                    nome = str(item.get("ativo") or item.get("symbol") or item.get("nome") or item.get("ticker") or "").upper()
                    if any(k.upper() in nome for k in chaves_busca):
                        res = extrair_valor_objeto(item, tipo_campo)
                        if res is not None:
                            return res

        elif isinstance(fonte, dict):
            for k_fonte, v_fonte in fonte.items():
                if any(k.upper() in str(k_fonte).upper() for k in chaves_busca):
                    res = extrair_valor_objeto(v_fonte, tipo_campo)
                    if res is not None:
                        return res

            sub_dict = fonte.get("ativos") or fonte.get("cotacoes") or fonte.get("dados") or {}
            if isinstance(sub_dict, dict):
                for k_fonte, v_fonte in sub_dict.items():
                    if any(k.upper() in str(k_fonte).upper() for k in chaves_busca):
                        res = extrair_valor_objeto(v_fonte, tipo_campo)
                        if res is not None:
                            return res
    return 0.0


def buscar_metrica_rom5(chave_interna: str, rom5: dict, tipo_campo: str = "var") -> float:
    """
    Busca variação no Coleta_rom-5.json (coleta de 5 min atrás).
    Usa o ALIASES_BUSCA_ROM5 para traduzir a chave interna nos tickers originais.
    """
    if not rom5:
        return 0.0

    coletas = rom5.get("coletas")
    if not isinstance(coletas, list):
        return 0.0

    tickers_buscar = ALIASES_BUSCA_ROM5.get(chave_interna, [chave_interna])
    tickers_buscar_upper = [t.upper() for t in tickers_buscar]

    for item in coletas:
        if not isinstance(item, dict):
            continue
        nome = str(item.get("ativo", "")).upper()
        if nome in tickers_buscar_upper:
            dados = item.get("dados_reais") or {}
            chave = "close" if tipo_campo == "ultimo" else "change_percent"
            val = dados.get(chave)
            if isinstance(val, (int, float)):
                return float(val)

    return 0.0


def calcular_score_intraday(
    sp500_var: float,
    ewz_var: float,
    wdo_var: float,
    val_di: float,
    vies_bancos: float,
    vies_commodities: float,
) -> float:
    """Calcula o score intraday a partir dos componentes. Reutilizável."""
    score = 0.0

    if sp500_var > 0.3: score += 1.5
    elif sp500_var < -0.3: score -= 1.5

    if ewz_var > 0.5: score += 1.5
    elif ewz_var < -0.5: score -= 1.5

    if wdo_var < -0.2: score += 1.0
    elif wdo_var > 0.2: score -= 1.0

    if val_di < -0.2: score += 1.5
    elif val_di > 0.2: score -= 1.5

    if vies_bancos > 0.3: score += 2.0
    elif vies_bancos < -0.3: score -= 2.0

    if vies_commodities > 0.3: score += 1.5
    elif vies_commodities < -0.3: score -= 1.5

    return score


# ==============================================================================
# CORPO DA PÁGINA (AUTO-REFRESH A CADA 60s)
# ==============================================================================
@st.fragment(run_every=60)
def render_body():
    st.caption(
        f"Última atualização local: `{datetime.now().strftime('%H:%M:%S')}` · "
        f"auto-refresh: 60s · "
        f"⚪ ponteiro branco = valor de 5 min atrás"
    )

    decisao_v2, smc_regras, unificados, dados_mt5, dados_val, rom5 = carregar_dados_absolutos()
    fontes_dados = [unificados, dados_val, dados_mt5, decisao_v2]

    # ==============================================================================
    # 1. MOTORES MACRO GLOBAIS E CÂMBIO
    # ==============================================================================
    st.subheader("1. Motores Macro e Correlações em Tempo Real")
    st.caption("Ponteiro centrado em zero · ⚠️ DXY/WDO/VIX invertidos (subir = risco)")

    ativos_macro = {
        "S&P 500 Futuro": {
            "preco": buscar_metrica(["SP500_FUT", "US500", "SP500", "S&P"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["SP500_FUT", "US500", "SP500", "S&P"], fontes=fontes_dados),
            "inverter": False,
            "chave_rom5": "SP500_FUT",
        },
        "Nasdaq 100": {
            "preco": buscar_metrica(["NASDAQ", "US100", "NDX", "NQ1!"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["NASDAQ", "US100", "NDX", "NQ1!"], fontes=fontes_dados),
            "inverter": False,
            "chave_rom5": "NASDAQ_FUT",
        },
        "EWZ (B3 em NY)": {
            "preco": buscar_metrica(["EWZ", "EWZ_ETF"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["EWZ", "EWZ_ETF"], fontes=fontes_dados),
            "inverter": False,
            "chave_rom5": "EWZ",
        },
        "DXY (Dólar Global)": {
            "preco": buscar_metrica(["DXY", "USDX", "DX1!"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["DXY", "USDX", "DX1!"], fontes=fontes_dados),
            "inverter": True,
            "chave_rom5": "DXY",
        },
        "WDO (Dólar Futuro)": {
            "preco": buscar_metrica(["WDO", "WDOU26", "WDO$"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["WDO", "WDOU26", "WDO$"], fontes=fontes_dados),
            "inverter": True,
            "chave_rom5": "WDO",
        },
        "VIX (Medo)": {
            "preco": buscar_metrica(["VIX", "VIX_INDEX"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["VIX", "VIX_INDEX"], fontes=fontes_dados),
            "inverter": True,
            "chave_rom5": "VIX",
        },
    }

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    cols_macro = [col1, col2, col3, col4, col5, col6]

    for i, (label, dados) in enumerate(ativos_macro.items()):
        fmt_preco = f"{dados['preco']:,.2f}" if dados['preco'] < 1000 else f"{dados['preco']:,.0f}"
        var_ant = buscar_metrica_rom5(dados["chave_rom5"], rom5)
        with cols_macro[i]:
            mini_velocimetro(
                dados["var"],
                label,
                fmt_preco,
                inverter=dados["inverter"],
                valor_anterior=var_ant if var_ant != 0.0 else None,
            )

    st.markdown("---")

    # ==============================================================================
    # 2. CURVA DE JUROS DI
    # ==============================================================================
    st.subheader("2. Curva de Juros DI (Pressão sobre o Ibovespa)")

    col_di1, col_di2, col_di3 = st.columns(3)

    di27_taxa = unificados.get("ativos", {}).get("DI1_2027", {}).get("preco", 13.565)
    di29_taxa = unificados.get("ativos", {}).get("DI1_2029", {}).get("preco", 13.93)
    val_di_exibicao = (di29_taxa - di27_taxa) * 100.0

    # Valor anterior (5 min atrás)
    di27_rom5 = buscar_metrica_rom5("DI1_2027", rom5, tipo_campo="ultimo")
    di29_rom5 = buscar_metrica_rom5("DI1_2029", rom5, tipo_campo="ultimo")
    val_di_anterior = None
    if di27_rom5 > 0 and di29_rom5 > 0:
        val_di_anterior = (di29_rom5 - di27_rom5) * 100.0 / 10.0  # normalizado

    impacto_texto = "Pressão Vendedora" if val_di_exibicao > 0 else "Suporte Comprador"
    status_curva = "Empinamento (Step-up)" if val_di_exibicao > 0 else "Achatamento"

    with col_di1:
        inclinacao_normalizada = val_di_exibicao / 10.0
        mini_velocimetro(
            inclinacao_normalizada,
            "📈 Inclinação DI (29 vs 27)",
            f"{val_di_exibicao:+.1f} bps",
            inverter=True,
            valor_anterior=val_di_anterior,
        )

    with col_di2:
        st.metric("Status da Curva", status_curva)

    with col_di3:
        st.metric("Impacto Bolsa", impacto_texto)

    st.markdown("---")

    # ==============================================================================
    # 3. BLUE CHIPS B3
    # ==============================================================================
    st.subheader("3. Peso das Ações Líderes na B3")
    st.caption("Variação diária das 7 principais blue chips · 🟢 positivo = compra · 🔴 negativo = venda")

    acoes_b3 = {
        "VALE3": {
            "preco": buscar_metrica(["VALE3", "VALE"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["VALE3", "VALE"], fontes=fontes_dados),
            "chave_rom5": "VALE3",
        },
        "PETR4": {
            "preco": buscar_metrica(["PETR4", "PETR"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["PETR4", "PETR"], fontes=fontes_dados),
            "chave_rom5": "PETR4",
        },
        "ITUB4": {
            "preco": buscar_metrica(["ITUB4", "ITUB"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["ITUB4", "ITUB"], fontes=fontes_dados),
            "chave_rom5": "ITUB4",
        },
        "BBDC4": {
            "preco": buscar_metrica(["BBDC4", "BBDC"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["BBDC4", "BBDC"], fontes=fontes_dados),
            "chave_rom5": "BBDC4",
        },
        "BBAS3": {
            "preco": buscar_metrica(["BBAS3", "BBAS"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["BBAS3", "BBAS"], fontes=fontes_dados),
            "chave_rom5": "BBAS3",
        },
    }

    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    cols_acoes = [col_a, col_b, col_c, col_d, col_e]

    for i, (ativo, dados) in enumerate(acoes_b3.items()):
        var_ant = buscar_metrica_rom5(dados["chave_rom5"], rom5)
        with cols_acoes[i]:
            mini_velocimetro(
                dados["var"],
                ativo,
                f"R$ {dados['preco']:,.2f}" if dados['preco'] > 0 else "—",
                inverter=False,
                valor_anterior=var_ant if var_ant != 0.0 else None,
            )

    valev3 = acoes_b3["VALE3"]["var"]
    petr4 = acoes_b3["PETR4"]["var"]
    itub4 = acoes_b3["ITUB4"]["var"]
    bbdc4 = acoes_b3["BBDC4"]["var"]
    bbas3 = acoes_b3["BBAS3"]["var"]

    vies_commodities = (valev3 * 0.55) + (petr4 * 0.45)
    vies_bancos = (itub4 * 0.45) + (bbdc4 * 0.30) + (bbas3 * 0.25)

    st.caption(f"📊 **Viés de Setores:** Commodities (`{vies_commodities:+.2f}%`) | Financeiro/Bancos (`{vies_bancos:+.2f}%`)")

    st.markdown("##### 🏭 Viés Setorial Consolidado")

    # ---- Valores ANTERIORES (recalculados a partir do rom-5) ----
    valev3_ant = buscar_metrica_rom5("VALE3", rom5)
    petr4_ant = buscar_metrica_rom5("PETR4", rom5)
    itub4_ant = buscar_metrica_rom5("ITUB4", rom5)
    bbdc4_ant = buscar_metrica_rom5("BBDC4", rom5)
    bbas3_ant = buscar_metrica_rom5("BBAS3", rom5)

    tem_dados_setores_ant = any(
        v != 0.0 for v in [valev3_ant, petr4_ant, itub4_ant, bbdc4_ant, bbas3_ant]
    )

    if tem_dados_setores_ant:
        vies_commodities_ant = (valev3_ant * 0.55) + (petr4_ant * 0.45)
        vies_bancos_ant = (itub4_ant * 0.45) + (bbdc4_ant * 0.30) + (bbas3_ant * 0.25)
    else:
        vies_commodities_ant = None
        vies_bancos_ant = None

    col_set1, col_set2 = st.columns(2)

    with col_set1:
        mini_velocimetro(
            vies_commodities,
            "⛏️ Commodities (Vale + Petro)",
            f"{vies_commodities:+.2f}%",
            inverter=False,
            valor_anterior=vies_commodities_ant,
        )

    with col_set2:
        mini_velocimetro(
            vies_bancos,
            "🏦 Financeiro (Itaú + Bradesco + BB)",
            f"{vies_bancos:+.2f}%",
            inverter=False,
            valor_anterior=vies_bancos_ant,
        )

    st.markdown("---")

    # ==============================================================================
    # 4. SINAIS TÉCNICOS SMC / ICT
    # ==============================================================================
    st.subheader("4. Leitura SMC / ICT (Sinais Direcionais)")

    col_smc1, col_smc2 = st.columns(2)

    obj_decisao = decisao_v2.get("decisao", {})
    obj_smc = obj_decisao.get("metadados", {}).get("smc", {})

    tendencia = str(obj_decisao.get("vies_final") or smc_regras.get("bias_direcional") or "NEUTRO").upper()

    obs = obj_smc.get("order_blocks") or smc_regras.get("order_blocks") or []
    if obs:
        primeiro_ob = obs[0]
        ob_txt = f"{primeiro_ob.get('tipo', 'OB')} em {primeiro_ob.get('preco', primeiro_ob.get('high', 0)):,.0f}"
    else:
        ob_txt = "Sem Order Block ativo no momento"

    fvgs = obj_smc.get("fvgs") or smc_regras.get("fair_value_gaps") or []
    if fvgs:
        primeiro_fvg = fvgs[0]
        fvg_txt = f"FVG {primeiro_fvg.get('tipo', 'COMPRA')} ({primeiro_fvg.get('inferior', 0):,.0f} - {primeiro_fvg.get('superior', 0):,.0f})"
    else:
        fvg_txt = "Sem FVG próximo"

    liquidez = smc_regras.get("liquidez", {})
    bsl_list = liquidez.get("bsl", [])
    ssl_list = liquidez.get("ssl", [])
    bsl = f"{bsl_list[0]:,.0f}" if bsl_list else "183,342"
    ssl = f"{ssl_list[0]:,.0f}" if ssl_list else "179,948"
    vwap_val = buscar_metrica(["WIN", "WIN$", "WINV26"], tipo_campo="ultimo", fontes=fontes_dados)

    with col_smc1:
        st.markdown("### 🎯 Estrutura do Mercado")
        st.info(f"**Tendência Atual:** {tendencia}")
        st.warning(f"**FVG Ativo (Ineficiência):** {fvg_txt}")
        st.success(f"**Order Block Institucional:** {ob_txt}")

    with col_smc2:
        st.markdown("### 📍 Liquidez & Alvos")
        st.write(f"📌 **Último Preço WIN:** `{vwap_val:,.0f}`" if vwap_val > 0 else "📌 **VWAP Diária:** `Aguardando Ticks`")
        st.write(f"🚀 **Buy Side Liquidity (BSL / Alvo Alta):** `{bsl}`")
        st.write(f"🔻 **Sell Side Liquidity (SSL / Alvo Baixa):** `{ssl}`")

    st.markdown("---")

    # ==============================================================================
    # 5. SCORE INTRADAY UNIFICADO
    # ==============================================================================
    st.subheader("5. Score Operacional em Tempo Real")

    sp500_var = ativos_macro["S&P 500 Futuro"]["var"]
    ewz_var = ativos_macro["EWZ (B3 em NY)"]["var"]
    wdo_var = ativos_macro["WDO (Dólar Futuro)"]["var"]

    score = calcular_score_intraday(
        sp500_var=sp500_var,
        ewz_var=ewz_var,
        wdo_var=wdo_var,
        val_di=val_di_exibicao,
        vies_bancos=vies_bancos,
        vies_commodities=vies_commodities,
    )

    # ---- Score ANTERIOR (recriado com dados do rom-5) ----
    sp500_var_ant = buscar_metrica_rom5("SP500_FUT", rom5)
    ewz_var_ant = buscar_metrica_rom5("EWZ", rom5)
    wdo_var_ant = buscar_metrica_rom5("WDO", rom5)

    tem_dados_ant = any(v != 0.0 for v in [sp500_var_ant, ewz_var_ant, wdo_var_ant])

    if tem_dados_ant:
        vies_commodities_ant_score = (valev3_ant * 0.55) + (petr4_ant * 0.45)
        vies_bancos_ant_score = (itub4_ant * 0.45) + (bbdc4_ant * 0.30) + (bbas3_ant * 0.25)

        # DI anterior
        if di27_rom5 > 0 and di29_rom5 > 0:
            val_di_ant_pts = (di29_rom5 - di27_rom5) * 100.0
        else:
            val_di_ant_pts = val_di_exibicao  # fallback

        score_anterior = calcular_score_intraday(
            sp500_var=sp500_var_ant,
            ewz_var=ewz_var_ant,
            wdo_var=wdo_var_ant,
            val_di=val_di_ant_pts,
            vies_bancos=vies_bancos_ant_score,
            vies_commodities=vies_commodities_ant_score,
        )
    else:
        score_anterior = None

    col_score_vis, col_score_txt = st.columns([1, 2])

    with col_score_vis:
        mini_velocimetro(
            score,
            "🎯 SCORE INTRADAY",
            f"{score:+.1f} pontos",
            inverter=False,
            valor_anterior=score_anterior,
        )

    with col_score_txt:
        st.markdown(f"### Score de Viés Intraday: **{score:+.1f}**")

        if score >= 4.0:
            st.success("🟢 **FORTE VIÉS COMPRADOR:** Alinhamento de S&P500, EWZ e Ações Líderes a favor da alta.")
        elif score <= -4.0:
            st.error("🔴 **FORTE VIÉS VENDEDOR:** Pressão de Juros/Dólar e queda generalizada nas Blue Chips.")
        else:
            st.warning("🟡 **VIÉS NEUTRO / CONSOLIDADO:** Sinais divergentes. Priorize trades em regiões extremas de Liquidez/FVG.")


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
render_body()
```

### `pages/5_📡_Ativos_Monitorados.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/6_📡_Ativos_Monitorados.py
Versão: 2.3 - Fix race condition (rom-0 como fonte do "atual") + cosméticos
Objetivo: Dashboard de integridade e monitoramento dos 32 ativos validados do ecossistema.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from datetime import datetime

from config import FILE_VALIDADOS, COLETAS_DIR, MAPEAMENTO_TICKERS_INVERSO


# ==============================================================================
# MAPA TICKERS ROM-5 (importado do config.py — MAPEAMENTO_TICKERS_INVERSO)
# ==============================================================================


# Nomes curtos (fix do corte [:18])
NOMES_CURTOS = {
    "🇧🇷 Mercado Local (Futuros B3)": "🏦 B3 Futuros",
    "🇺🇸 Drivers Globais & Risco": "🌍 Drivers",
    "🪵 Commodities Cíclicas": "🪵 Commodities",
    "📈 ADRs Brasileiras (Sentiment NY)": "🇧🇷 ADRs NY",
    "🏦 Mercado à Vista (Ações Locais)": "📊 À Vista",
}


# ==============================================================================
# MINI VELOCÍMETRO (padrão consolidado das páginas 2/3/4)
# ==============================================================================
def mini_velocimetro(
    valor,
    label: str,
    preco_fmt: str = "",
    inverter: bool = False,
    valor_anterior=None,
) -> None:
    # ---------- Valor ATUAL ----------
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

    angulo = (real_exibicao / 10.0) * 90.0

    # ---------- Valor ANTERIOR ----------
    tem_anterior = False
    angulo_anterior = 0.0
    if valor_anterior is not None:
        try:
            ant_exibicao = max(-10.0, min(10.0, float(valor_anterior)))
            angulo_anterior = (ant_exibicao / 10.0) * 90.0
            tem_anterior = True
        except (TypeError, ValueError):
            tem_anterior = False

    # ---------- Δ ----------
    # Threshold cosmético: 0.005 evita "Δ +0.00%" verde que parece bug
    if valor is not None and valor_anterior is not None:
        try:
            delta = float(valor) - float(valor_anterior)
            if abs(delta) < 0.005:
                cor_delta = "#8b949e"
                texto_delta = "Δ 0,00%"
            else:
                delta_real = -delta if inverter else delta
                if delta_real > 0.005:
                    cor_delta = "#00cc44"
                elif delta_real < -0.005:
                    cor_delta = "#ff4b4b"
                else:
                    cor_delta = "#8b949e"
                texto_delta = f"Δ {delta:+.2f}%"
        except (TypeError, ValueError):
            cor_delta = "#8b949e"
            texto_delta = "Δ —"
    else:
        cor_delta = "#8b949e"
        texto_delta = "Δ —"

    # ---------- SVG do ponteiro anterior ----------
    if tem_anterior:
        svg_anterior = (
            f'<svg class="mini-needle-ant" '
            f'style="transform: rotate({angulo_anterior}deg);" '
            f'viewBox="0 0 14 52">'
            f'<path d="M 7 0 L 9.5 46 L 4.5 46 Z" '
            f'fill="rgba(220, 220, 255, 0.85)"/>'
            f'</svg>'
        )
    else:
        svg_anterior = ""

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
            padding: 2px 0;
        }}
        .mini-label {{
            font-size: 11px;
            color: #c9d1d9;
            margin-bottom: 1px;
            text-align: center;
            font-weight: 700;
            white-space: nowrap;
        }}
        .mini-gauge {{
            position: relative;
            width: 120px;
            height: 62px;
        }}
        .mini-arc {{
            position: absolute; left: 5px; top: 3px;
            width: 110px; height: 55px;
            border-radius: 110px 110px 0 0;
            background: conic-gradient(
                from 270deg at 50% 100%,
                #ff2020 0deg 30deg,
                #b02020 30deg 60deg,
                #602020 60deg 90deg,
                #206020 90deg 120deg,
                #00a030 120deg 150deg,
                #00cc44 150deg 180deg
            );
            -webkit-mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
                    mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
        }}
        .mini-needle-ant {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 14px;
            height: 48px;
            margin-left: -7px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2;
        }}
        .mini-needle {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 8px;
            height: 52px;
            margin-left: -4px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 3;
        }}
        .mini-pivot {{
            position: absolute;
            left: 50%;
            bottom: 0px;
            width: 12px; height: 12px;
            margin-left: -6px;
            border-radius: 50%;
            background: {cor};
            z-index: 4;
            transition: background 0.5s ease;
        }}
        .mini-value {{
            font-size: 14px;
            font-weight: 900;
            color: {cor};
            text-align: center;
            margin-top: 4px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
            line-height: 1.1;
        }}
        .mini-delta {{
            font-size: 10px;
            font-weight: 700;
            color: {cor_delta};
            text-align: center;
            margin-top: 3px;
            letter-spacing: 0.2px;
            opacity: 0.9;
            line-height: 1.1;
        }}
        .mini-sub {{
            font-size: 10px;
            color: #8b949e;
            text-align: center;
            margin-top: 2px;
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
            <div class="mini-delta">{texto_delta}</div>
            <div class="mini-sub">{preco_fmt}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=155, scrolling=False)


# ==============================================================================
# LOADERS DEFENSIVOS
# ==============================================================================
def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def carregar_rom_dict(nome_arquivo: str) -> dict:
    """
    Lê um Coleta_rom-X.json e devolve {ticker_rom5: change_percent}.
    Suporta formato {"coletas": [...]}.
    """
    caminho = COLETAS_DIR / nome_arquivo
    dados = carregar_json_defensivo(caminho)
    resultado: dict = {}

    if isinstance(dados, dict):
        coletas = dados.get("coletas")
        if isinstance(coletas, list):
            for item in coletas:
                if not isinstance(item, dict):
                    continue
                ativo_key = item.get("ativo")
                if not ativo_key:
                    continue
                dados_reais = item.get("dados_reais") or {}
                cp = dados_reais.get("change_percent")
                if cp is None:
                    continue
                try:
                    resultado[ativo_key] = float(cp)
                except (TypeError, ValueError):
                    continue
    return resultado


def buscar_valor(ativo_id: str, rom_dict: dict):
    """Traduz ativo_id interno → ticker rom → change_percent."""
    ticker = MAPEAMENTO_TICKERS_INVERSO.get(ativo_id)
    if not ticker:
        return None
    return rom_dict.get(ticker)


# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - Ativos Monitorados", layout="wide")


# ==============================================================================
# CATEGORIAS OPERACIONAIS
# ==============================================================================
CATEGORIAS = {
    "🇧🇷 Mercado Local (Futuros B3)": ["WIN_AJUSTE", "WDO_AJUSTE", "WIN_FUT", "WDO_FUT", "DI1_2027", "DI1_2029"],
    "🇺🇸 Drivers Globais & Risco": ["VIX", "SP500_FUT", "NASDAQ_FUT", "DXY", "USD_MXN"],
    "🪵 Commodities Cíclicas": ["IRON_ORE", "IRON_ORE_2M", "CRUDE_OIL", "GOLD"],
    "📈 ADRs Brasileiras (Sentiment NY)": ["EWZ", "VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"],
    "🏦 Mercado à Vista (Ações Locais)": ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"],
}


def calcular_media_categoria(ids_categoria, ativos_validados, rom_dict, ignorar_invertidos=False, usar_rom=False):
    """
    Média das variações % da categoria.
    Se usar_rom=True → lê de rom_dict (atual ou anterior).
    Se usar_rom=False → lê de ativos_validados (Dados_Validados).
    """
    if ignorar_invertidos:
        ids_excluir = {"VIX", "DXY"}
        ids_categoria = [x for x in ids_categoria if x not in ids_excluir]

    variacoes = []
    if usar_rom:
        for ativo_id in ids_categoria:
            v = buscar_valor(ativo_id, rom_dict)
            if v is not None:
                variacoes.append(v)
    else:
        for ativo in ativos_validados:
            if ativo.get("ativo_id") in ids_categoria:
                v = ativo.get("change_percent")
                if v is not None:
                    try:
                        variacoes.append(float(v))
                    except (TypeError, ValueError):
                        pass

    if not variacoes:
        return None, 0
    return sum(variacoes) / len(variacoes), len(variacoes)


# ==============================================================================
# CORPO (auto-refresh a cada 60s)
# ==============================================================================
@st.fragment(run_every=60)
def render_body():
    # --- CARGA DOS DADOS (DENTRO do fragment!) ---
    payload_validado = carregar_json_defensivo(FILE_VALIDADOS)
    rom0_dict = carregar_rom_dict("Coleta_rom-0.json")   # ATUAL (fix race)
    rom5_dict = carregar_rom_dict("Coleta_rom-5.json")   # 5min atrás

    # --- CABEÇALHO ---
    st.markdown(
        "<h2 style='color:#00d4ff;'>📡 Status e Integridade de Ativos Monitorados</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Central de Auditoria · Cruzamento Multimercados · "
        f"🔄 {datetime.now().strftime('%H:%M:%S')} · "
        f"⚪ ponteiro branco = 5 min atrás (rom-0: {len(rom0_dict)} · rom-5: {len(rom5_dict)})"
    )

    if not payload_validado:
        st.warning(
            "⚠️ Arquivo de dados validados não encontrado. "
            "Certifique-se de que a etapa de validação (Validador.py) rodou no pipeline."
        )
        st.stop()

    metadata = payload_validado.get("metadata_validacao", {})
    total_recebidos = metadata.get("total_recebidos", 0)
    total_aprovados = metadata.get("total_aprovados", 0)
    total_rejeitados = metadata.get("total_rejeitados", 0)

    # --- KPIs DE SAÚDE DOS DADOS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Carga Útil Recebida", f"{total_recebidos} ativos")
    c2.metric(
        "Aprovados pelo Validador",
        f"{total_aprovados} OK",
        delta=f"{total_aprovados/total_recebidos*100:.1f}% Eficiência" if total_recebidos > 0 else "0%",
    )

    if total_rejeitados > 0:
        c3.metric("Ativos Rejeitados / Falhas", f"{total_rejeitados} Erros",
                  delta="- Problema na API", delta_color="inverse")
    else:
        c3.metric("Ativos Rejeitados / Falhas", "0 Erros",
                  delta="Estabilidade 100%", delta_color="normal")

    c4.markdown(
        f"<div style='background-color:#161b24; padding:10px; border-radius:8px; "
        f"border:1px solid #2a3a4a; height:100%; text-align:center;'>"
        f"<span style='font-size:0.85rem; color:#8b949e;'>ÚLTIMA AUDITORIA V2</span><br>"
        f"<span style='font-size:1.25rem; font-weight:bold; color:#00ff88;'>"
        f"{datetime.fromisoformat(metadata.get('timestamp_validacao', datetime.now().isoformat())).strftime('%H:%M:%S')}"
        f"</span></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    ativos_lista = payload_validado.get("ativos_validados", [])
    ordem_categorias = list(CATEGORIAS.keys())

    # ==========================================================================
    # TERMÔMETRO POR CATEGORIA
    # ✅ Agora usa rom-0 (atual) vs rom-5 (anterior) — sem race
    # ==========================================================================
    st.markdown("### 🌡️ Termômetro de Sentimento por Categoria")
    st.caption(
        "Variação média dos ativos de cada grupo · 🟢 verde = favorável · 🔴 vermelho = pressão · "
        "⚪ ponteiro branco = média de 5 min atrás · ⚠️ VIX/DXY excluídos (semântica inversa)"
    )

    cols_cat = st.columns(5)

    for idx, nome_cat in enumerate(ordem_categorias):
        ids_cat = CATEGORIAS[nome_cat]
        ign_inv = "Drivers Globais" in nome_cat

        # ✅ Atual = rom-0 (fix race). Fallback p/ Dados_Validados se rom-0 vazio
        media, qtd = calcular_media_categoria(
            ids_cat, ativos_lista, rom0_dict,
            ignorar_invertidos=ign_inv, usar_rom=True,
        )
        if media is None:
            media, qtd = calcular_media_categoria(
                ids_cat, ativos_lista, rom0_dict,
                ignorar_invertidos=ign_inv, usar_rom=False,
            )

        # ✅ Anterior = rom-5
        media_ant, _ = calcular_media_categoria(
            ids_cat, ativos_lista, rom5_dict,
            ignorar_invertidos=ign_inv, usar_rom=True,
        )

        nome_curto = NOMES_CURTOS.get(nome_cat, nome_cat[:16])

        with cols_cat[idx]:
            mini_velocimetro(
                media,
                nome_curto,
                f"{qtd} ativos" if qtd > 0 else "sem dados",
                inverter=False,
                valor_anterior=media_ant,
            )

    st.markdown("---")

    # ==========================================================================
    # SUB-ABAS POR CATEGORIA
    # ==========================================================================
    abas_nomes = list(CATEGORIAS.keys())
    abas = st.tabs(abas_nomes)

    for idx_aba, nome_aba in enumerate(abas_nomes):
        with abas[idx_aba]:
            ids_categoria = CATEGORIAS[nome_aba]
            linhas_categoria = []
            variacoes_para_velocimetro = []

            for ativo in ativos_lista:
                if ativo.get("ativo_id") not in ids_categoria:
                    continue

                ativo_id = ativo.get("ativo_id")
                var_pct = ativo.get("change_percent")
                var_txt = f"{var_pct:+.2f}%" if var_pct is not None else "—"
                vol = ativo.get("volume")
                vol_txt = f"{vol:,.0f}" if vol is not None else "—"

                linhas_categoria.append({
                    "Identificador V2": ativo_id,
                    "Ticker Original": ativo.get("ticker_original"),
                    "Preço / Taxa": (
                        f"{ativo.get('close'):,.4f}" if ativo.get("close", 0) < 100
                        else f"{ativo.get('close'):,.2f}"
                    ),
                    "Variação Diária": var_txt,
                    "Volume Turn": vol_txt,
                    "Fonte de Coleta": ativo.get("fonte", "N/A"),
                    "Timestamp": (
                        ativo.get("timestamp_coleta", "N/A")[-14:-5]
                        if "T" in str(ativo.get("timestamp_coleta"))
                        else "N/A"
                    ),
                })

                # ✅ Gauge por ativo: atual = rom-0, anterior = rom-5
                # Fallback para o valor de Dados_Validados se rom-0 não tiver
                v_atual = buscar_valor(ativo_id, rom0_dict)
                if v_atual is None:
                    try:
                        v_atual = float(var_pct) if var_pct is not None else None
                    except (TypeError, ValueError):
                        v_atual = None

                if v_atual is not None:
                    v_ant = buscar_valor(ativo_id, rom5_dict)
                    variacoes_para_velocimetro.append({
                        "label": ativo_id,
                        "valor": v_atual,
                        "valor_anterior": v_ant,
                    })

            # -------- MINI VELOCÍMETROS POR ATIVO --------
            if variacoes_para_velocimetro:
                st.markdown("##### 📊 Sentimento por Ativo")
                variacoes_para_velocimetro.sort(key=lambda x: abs(x["valor"]), reverse=True)

                top = variacoes_para_velocimetro[:6]
                n_cols = min(len(top), 6)
                cols_ativo = st.columns(n_cols)

                for idx_a, item in enumerate(top):
                    inv = item["label"] in ("VIX", "DXY")
                    with cols_ativo[idx_a % n_cols]:
                        mini_velocimetro(
                            item["valor"],
                            item["label"],
                            f"{item['valor']:+.2f}%",
                            inverter=inv,
                            valor_anterior=item["valor_anterior"],
                        )

                st.markdown("")

            # -------- TABELA DE DADOS (segue usando Dados_Validados) --------
            if linhas_categoria:
                df_cat = pd.DataFrame(linhas_categoria)
                st.dataframe(df_cat.set_index("Identificador V2"), use_container_width=True)
            else:
                st.caption("ℹ️ Nenhum ativo desta categoria foi processado nesta janela de execução.")

    # --- RELATÓRIO DE REJEIÇÕES ---
    rejeicoes = payload_validado.get("relatorio_rejeicoes", [])
    if rejeicoes:
        st.markdown("### 🚨 Relatório de Ativos Rejeitados / Fora do Ar")
        st.warning(
            "Os ativos abaixo falharam nos testes estritos de integridade quantitativa. "
            "O orquestrador isolou esses campos para proteger a pontuação final de viés."
        )
        st.table(pd.DataFrame(rejeicoes))


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
render_body()
```

### `pages/6_📈_Matriz_de_Influencia.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/1.2_📈_Matriz_de_Influencia.py
Versão: 1.0
Objetivo: Guia rápido e visual de correlação/influência dos ativos internacionais e taxas no WIN/WDO
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="WINFUT - Matriz de Influência", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; }
.card-impact-high {
    background-color: #0d381e;
    border-left: 5px solid #00c853;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.card-impact-bear {
    background-color: #380d0d;
    border-left: 5px solid #ff3d00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.card-impact-warn {
    background-color: #382b0d;
    border-left: 5px solid #ffab00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CABEÇALHO TÉCNICO
# ==============================================================================
st.markdown("<h2 style='color:#00d4ff;'>📈 Matriz de Influência e Confluência de Ativos</h2>", unsafe_allow_html=True)
st.caption("Guia de consulta rápida para tomada de decisão no leilão e pré-market da B3")

# ==============================================================================
# 1. PESO E IMPACTO DIRETO DOS ATIVOS NO WIN/WDO
# ==============================================================================
st.markdown("---")
st.subheader("⚖️ Pesos e Vetores de Influência Directa")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 🟢 Drivers Principais do Mini Índice (WIN)")
    df_win_peso = pd.DataFrame([
        {"Ativo": "ADRs Brasileiras (VALE, PETR, Bancos)", "Peso Proporcional": 55, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "Índices US (S&P500 / Nasdaq)", "Peso Proporcional": 25, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "Commodities (Petróleo / Minério)", "Peso Proporcional": 10, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "VIX (Índice do Medo)", "Peso Proporcional": -5, "Impacto Directo": "Inverso (+ / -)"},
        {"Ativo": "Curva de Juros DI (DI1 2027/2029)", "Peso Proporcional": -5, "Impacto Directo": "Inverso (+ / -)"}
    ])
    
    fig_win = px.bar(
        df_win_peso, x="Peso Proporcional", y="Ativo", orientation='h',
        color="Peso Proporcional",
        color_continuous_scale=["#ff3d00", "#ffab00", "#00c853"],
        title="Força Explicativa no Pregão de Abertura do WIN"
    )
    fig_win.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"}, coloraxis_showscale=False)
    st.plotly_chart(fig_win, use_container_width=True)

with col_right:
    st.markdown("#### 🔴 Drivers Principais do Mini Dólar (WDO)")
    df_wdo_peso = pd.DataFrame([
        {"Ativo": "DXY (Índice Dólar Global)", "Peso Proporcional": 45, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "Curva de Juros DI (DI1 2027/2029)", "Peso Proporcional": 25, "Impacto Directo": "Direto (+ / +)"},
        {"Ativo": "EWZ (ETF Brasil no Exterior)", "Peso Proporcional": -20, "Impacto Directo": "Inverso (+ / -)"},
        {"Ativo": "VIX (Aversão Global a Risco)", "Peso Proporcional": 10, "Impacto Directo": "Direto (+ / +)"}
    ])
    
    fig_wdo = px.bar(
        df_wdo_peso, x="Peso Proporcional", y="Ativo", orientation='h',
        color="Peso Proporcional",
        color_continuous_scale=["#00c853", "#ffab00", "#ff3d00"],
        title="Força Explicativa no Pregão de Abertura do WDO"
    )
    fig_wdo.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"}, coloraxis_showscale=False)
    st.plotly_chart(fig_wdo, use_container_width=True)

# ==============================================================================
# 2. TABELA INTERATIVA DE CENÁRIOS E DIVERGÊNCIAS (CONSULTA RÁPIDA)
# ==============================================================================
st.markdown("---")
st.subheader("🧩 Cenários de Confluência e Divergência na Prática")

cenarios_data = [
    {
        "Cenário": "🔥 Super Confluência de Alta",
        "ADRs BR": "🟢 Forte Alta (+2.0%)",
        "S&P / Nasdaq": "🟢 Positivos",
        "VIX / DI": "🔴 Queda / Estável",
        "Comportamento Projetado (WIN)": "🚀 GAP de Alta Forte + Explosão",
        "Estratégia": "Não fazer FADE/Venda contra o gap. Foco em compra no retração ou rompimento pós-abertura."
    },
    {
        "Cenário": "⚡ Divergência: ADRs vs EUA (Seu Exemplo)",
        "ADRs BR": "🟢 Forte Alta (+1.5%)",
        "S&P / Nasdaq": "🔴 Baixa (-0.8%)",
        "VIX / DI": "🟡 Neutro",
        "Comportamento Projetado (WIN)": "⚖️ Abertura Autônoma / Rali do Ibovespa",
        "Estratégia": "Prioridade total às ADRs (VALE/PETR/Bancos). O peso local supera o exterior se commodities/commodities financeiras estiverem compradas."
    },
    {
        "Cenário": "⚠️ Aversão Global a Risco (Risk-Off)",
        "ADRs BR": "🔴 Em Queda",
        "S&P / Nasdaq": "🔴 Em Queda Forte",
        "VIX / DI": "🟢 VIX Dispara / DI Sobe",
        "Comportamento Projetado (WIN)": "📉 GAP de Baixa Agressivo",
        "Estratégia": "Aguardar teste no ajuste. Se perder o ajuste no leilão, preferência por continuação da venda (Explosão Venda)."
    },
    {
        "Cenário": "🛑 Divergência Interna de Commodities",
        "ADRs BR": "🟡 Mistas (PETR subindo, VALE caindo)",
        "S&P / Nasdaq": "🟢 Leve Alta",
        "VIX / DI": "🟡 Estável",
        "Comportamento Projetado (WIN)": "🔄 Mercado Travado / Leilão Sujo",
        "Estratégia": "Operacional de Leilão fica BLOQUEADO. Operar preferencialmente 'Retorno ao Ajuste (500/100)' após 09:15h."
    }
]

for c in cenarios_data:
    if "Super Confluência" in c["Cenário"]:
        css = "card-impact-high"
    elif "Divergência" in c["Cenário"]:
        css = "card-impact-warn"
    else:
        css = "card-impact-bear"
        
    st.markdown(f"""
    <div class="{css}">
        <h4 style="margin:0 0 8px;">{c['Cenário']}</h4>
        <p><b>• ADRs BR:</b> {c['ADRs BR']} | <b>• EUA:</b> {c['S&P / Nasdaq']} | <b>• VIX/DI:</b> {c['VIX / DI']}</p>
        <p><b>📉 Expectativa no Índice:</b> <code style="color:#00d4ff;">{c['Comportamento Projetado (WIN)']}</code></p>
        <p style="margin-bottom:0;">💡 <b>Estratégia Operacional:</b> {c['Estratégia']}</p>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. MAPA DE CALOR DE MATRIZ DE CORRELAÇÃO ESTÁTICA/HISTÓRICA
# ==============================================================================
st.markdown("---")
st.subheader("🔥 Matriz de Correlação Cruzada (Referência Pré-Market)")

matriz_corr = pd.DataFrame(
    [
        [1.00, 0.85, 0.72, -0.68, -0.62, -0.78],
        [0.85, 1.00, 0.65, -0.55, -0.50, -0.72],
        [0.72, 0.65, 1.00, -0.45, -0.40, -0.58],
        [-0.68, -0.55, -0.45, 1.00, 0.75, 0.62],
        [-0.62, -0.50, -0.40, 0.75, 1.00, 0.55],
        [-0.78, -0.72, -0.58, 0.62, 0.55, 1.00]
    ],
    columns=["WIN_FUT", "ADRs BR", "S&P500", "VIX", "DI1", "WDO_FUT"],
    index=["WIN_FUT", "ADRs BR", "S&P500", "VIX", "DI1", "WDO_FUT"]
)

fig_heatmap = px.imshow(
    matriz_corr,
    text_auto=".2f",
    color_continuous_scale="RdBu_r",
    title="Coeficiente de Correlação Típico do Leilão de Abertura"
)
fig_heatmap.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"})
st.plotly_chart(fig_heatmap, use_container_width=True)

# ==============================================================================
# 4. REGRAS DE OURO PARA CONSULTA RÁPIDA
# ==============================================================================
st.markdown("---")
st.markdown("### 📌 Regras de Ouro no Pré-Market")

col_r1, col_r2, col_r3 = st.columns(3)

with col_r1:
    st.markdown("""
    **1. Prioridade das ADRs**
    Quando há notícia Relevante de 3★ no Brasil às 09:00, as **ADRs Brasileiras** (VALE, PETR, ITUB) possuem **60%+ da prioridade** operacional sobre os índices S&P500/Nasdaq.
    """)

with col_r2:
    st.markdown("""
    **2. Trava do VIX**
    Se o **VIX** estiver subindo acima de **+5.00%**, qualquer alta do Mini Índice deve ser operada com desconfiança (alvo mais curto), pois o risco de pullback abrupto é elevado.
    """)

with col_r3:
    st.markdown("""
    **3. Regra dos DIs Curto vs Longo**
    Se a Curva de **DI (2027/2029)** estiver subindo forte, o Mini Índice tende a pressionar para baixo e o Mini Dólar atua na ponta compradora.
    """)
```

### `pages/7.1_📊_SMC_Regras.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/7.1_📊_SMC_Regras.py
Versão: 4.2 - Candlestick + Zonas SMC (POC/VWAP/OB/FVG/BSL/SSL)
                  + Zoom inicial nas últimas pernadas
                  + Auto-refresh de 5 min (sincronizado com o Agendador)
Objetivo: Renderizar estruturas SMC/ICT em gráfico de candles reais (MT5)
         com todas as zonas institucionais sobrepostas.
         Exibe por padrão apenas os últimos N candles (pernadas recentes).
"""

import streamlit as st
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from config import FILE_SMC_REGRAS

# 🔄 Auto-refresh (instalar: pip install streamlit-autorefresh)
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_DISPONIVEL = True
except ImportError:
    AUTOREFRESH_DISPONIVEL = False


# ==============================================================================
# CONFIGURAÇÕES DE VISUALIZAÇÃO (AJUSTE AQUI O PADRÃO)
# ==============================================================================
QTD_CANDLES_PADRAO = 30              # Padrão (compat M5): 30 candles (~2.5h)
OPCOES_CANDLES = [30, 60, 100, 150, 200]

# Defaults por timeframe (fix40 — multi-TF visual)
# chave = timeframe em minutos; valor = quantidade de candles inicial
QTD_CANDLES_POR_TF = {
    1:  60,   # M1:  1h de leitura micro
    5:  30,   # M5:  2.5h (mantém o atual)
    15: 20,   # M15: 5h de leitura macro
}
OPCOES_CANDLES_POR_TF = {
    1:  [30, 60, 120, 180, 240],
    5:  [30, 60, 100, 150, 200],
    15: [10, 20, 40, 60, 80],
}

# Intervalo do auto-refresh em minutos (alinhado com Agendador.py)
INTERVALO_REFRESH_MIN = 5


# ==============================================================================
# CARREGAMENTO DEFENSIVO
# ==============================================================================
def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def carregar_candles_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 200):
    """
    fix41: usa cache_candles.obter_candles() em vez de puxar tudo do MT5.

    O cache faz fetch incremental dos ultimos candles, entao essa funcao
    fica barata mesmo com TTL de 60s — o M1 atualiza a cada minuto.
    """
    try:
        from cache_candles import obter_candles
        candles, contrato = obter_candles(symbol, timeframe_min, qtd)
        return candles, contrato
    except Exception as e:
        return [], str(e)


# ==============================================================================
# CONFIG
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - SMC por Regras", layout="wide")


# ==============================================================================
# AUTO-REFRESH + CONTROLES NA SIDEBAR
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Controles SMC")
    auto_refresh = st.checkbox(
        f"🔄 Auto-atualizar ({INTERVALO_REFRESH_MIN} min)",
        value=True,
        help="Atualiza a página automaticamente para buscar novos dados do pipeline.",
        key="smc_auto_refresh_toggle",
    )

    if auto_refresh and AUTOREFRESH_DISPONIVEL:
        st_autorefresh(
            interval=INTERVALO_REFRESH_MIN * 60 * 1000,
            key="smc_autorefresh_key",
        )
        st.caption(f"✅ Ativo — refresh a cada {INTERVALO_REFRESH_MIN} min")
    elif auto_refresh and not AUTOREFRESH_DISPONIVEL:
        st.warning("⚠️ Instale: `pip install streamlit-autorefresh`")
    else:
        st.caption("⏸️ Auto-refresh pausado")


dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)

# fix45: variaveis de conveniencia (removidas pelo fix42)
vies = dados_smc.get("bias_direcional", "LATERAL")
confianca = dados_smc.get("confianca_visual", 0)
preco_atual = dados_smc.get("preco_atual", 0.0)

# --- CABEÇALHO ---
st.markdown("<h2 style='color:#00d4ff;'>🧠 Smart Money Concepts (SMC) & ICT</h2>", unsafe_allow_html=True)

# Mostra o timestamp do JSON + horário da última leitura
ts_dados = dados_smc.get('timestamp', 'N/A')
ts_pagina = datetime.now().strftime("%H:%M:%S")
st.caption(f"Análise algorítmica pura (Sem IA) · Dados: **{ts_dados}** · Página lida às **{ts_pagina}**")

if not dados_smc or "erro" in dados_smc:
    st.error(f"⚠️ Erro ao carregar dados do Motor SMC: {dados_smc.get('erro', 'Arquivo não gerado ou sem candles suficientes')}")
    st.stop()


# ==============================================================================
# GRÁFICO DE CANDLESTICK COM ZONAS SMC
# ==============================================================================
def render_grafico_candles(
    dados: dict,
    qtd_visivel: int = QTD_CANDLES_PADRAO,
    timeframe_min: int = 5,
    tf_label: str = "M5",
) -> go.Figure:
    # --- fix40: usa dados do dict, não globais (bug latente corrigido) ---
    vies = dados.get("bias_direcional", "LATERAL")
    confianca = dados.get("confianca_visual", 0)
    preco_atual = dados.get("preco_atual", 0.0)
    """
    Gráfico de candlestick do WIN M5 com sobreposição:
    - POC / VWAP de ontem
    - Order Blocks (bandas horizontais)
    - Fair Value Gaps abertos (zonas)
    - BSL / SSL (linhas de liquidez)
    - Entrada / Stop / Alvos
    - Swing Highs / Lows (marcadores)
    - BOS / CHoCH (anotações)

    Parâmetros:
        qtd_visivel: número de candles exibidos (foco nas últimas pernadas).
        timeframe_min: timeframe em minutos (1, 5, 15).
        tf_label: rótulo do TF para título (ex: "M5", "M15").
    """
    # ---------- Coleta de dados do SMC ----------
    niveis = dados.get("niveis_institucionais", {}) or {}
    poc = niveis.get("poc_ontem", 0.0)
    vwap = niveis.get("vwap_ontem", 0.0)

    obs = dados.get("order_blocks", []) or []
    fvgs = dados.get("fair_value_gaps", []) or []
    liq = dados.get("liquidez", {}) or {}
    bsl = liq.get("bsl", []) or []
    ssl = liq.get("ssl", []) or []

    entrada = dados.get("entrada_sugerida")
    stop = dados.get("stop_sugerido")
    alvos = dados.get("alvos", []) or []

    swings = list(dados.get("swings_recentes", []) or [])
    eventos = list(dados.get("eventos_estrutura", []) or [])

    # ---------- Busca candles do MT5 ----------
    # Sempre puxamos 200 para ter contexto, mas exibimos apenas os últimos N
    candles, simbolo_ok = carregar_candles_mt5("WIN$", timeframe_min, 200)

    # ---------- FATIA APENAS AS ÚLTIMAS PERNADAS ----------
    if candles and qtd_visivel and qtd_visivel < len(candles):
        candles = candles[-qtd_visivel:]

        # Janela temporal visível (para filtrar swings e eventos fora do range)
        t_min = candles[0]["time"]
        t_max = candles[-1]["time"]

        # Filtra swings que caem dentro da janela visível
        swings = [s for s in swings if t_min <= str(s.get("time", "")) <= t_max]

        # Filtra eventos (BOS/CHoCH) que caem dentro da janela visível
        eventos = [e for e in eventos if t_min <= str(e.get("time", "")) <= t_max]

    fig = go.Figure()

    # ---------- 1. Zonas horizontais (shapes) — por baixo dos candles ----------

    # Order Blocks
    for ob in obs:
        tipo = ob.get("tipo", "")
        low = ob.get("low")
        high = ob.get("high")
        if low is None or high is None:
            continue
        cor_fill = "rgba(0, 255, 136, 0.14)" if tipo == "COMPRA" else "rgba(255, 107, 107, 0.14)"
        cor_borda = "#00ff88" if tipo == "COMPRA" else "#ff6b6b"
        validado = ob.get("validado_por", "")
        label = f"OB {tipo} [{validado}]" if validado else f"OB {tipo}"

        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=low, y1=high,
            fillcolor=cor_fill,
            line=dict(color=cor_borda, width=1, dash="dot"),
            layer="below",
        )
        fig.add_annotation(
            xref="paper", x=0.005,
            yref="y", y=(low + high) / 2,
            text=label,
            showarrow=False,
            font=dict(color=cor_borda, size=10),
            xanchor="left",
        )

    # FVGs abertos
    for fvg in fvgs:
        if fvg.get("preenchido"):
            continue
        tipo = fvg.get("tipo", "")
        sup = fvg.get("superior")
        inf = fvg.get("inferior")
        if sup is None or inf is None:
            continue
        cor = "rgba(0, 212, 255, 0.10)" if tipo == "COMPRA" else "rgba(255, 165, 0, 0.10)"
        cor_borda = "#00d4ff" if tipo == "COMPRA" else "#ffa500"

        fig.add_shape(
            type="rect",
            xref="paper", x0=0, x1=1,
            yref="y", y0=inf, y1=sup,
            fillcolor=cor,
            line=dict(color=cor_borda, width=1, dash="dashdot"),
            layer="below",
        )
        fig.add_annotation(
            xref="paper", x=0.995,
            yref="y", y=(inf + sup) / 2,
            text=f"FVG {tipo}",
            showarrow=False,
            font=dict(color=cor_borda, size=9),
            xanchor="right",
        )

    # ---------- 2. Candles ----------
    if candles:
        x_vals = [c["time"] for c in candles]
        fig.add_trace(go.Candlestick(
            x=x_vals,
            open=[c["open"] for c in candles],
            high=[c["high"] for c in candles],
            low=[c["low"] for c in candles],
            close=[c["close"] for c in candles],
            name="WIN M5",
            increasing=dict(line=dict(color="#00ff88", width=1), fillcolor="#00ff88"),
            decreasing=dict(line=dict(color="#ff6b6b", width=1), fillcolor="#ff6b6b"),
            hovertext=[
                f"O: {c['open']:,.0f}<br>H: {c['high']:,.0f}<br>L: {c['low']:,.0f}<br>C: {c['close']:,.0f}<br>V: {c['volume']:,.0f}"
                for c in candles
            ],
            hoverinfo="x+text",
        ))
        x_min = x_vals[0]
        x_max = x_vals[-1]
    else:
        # Fallback: sem candles do MT5 — usa range fictício
        st.warning(f"⚠️ Não foi possível buscar candles do MT5 ({simbolo_ok}). Exibindo apenas níveis.")
        x_min, x_max = 0, 1

    # ---------- 3. Níveis horizontais ----------

    if candles:
        x_line = [x_min, x_max]
    else:
        x_line = [0, 1]

    # POC
    if poc and poc > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[poc, poc],
            mode="lines",
            name=f"POC Ontem ({poc:,.0f})",
            line=dict(color="#a855f7", width=2, dash="dot"),
            hovertemplate=f"<b>POC Ontem</b><br>{poc:,.0f} pts<extra></extra>",
        ))

    # VWAP
    if vwap and vwap > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[vwap, vwap],
            mode="lines",
            name=f"VWAP Ontem ({vwap:,.1f})",
            line=dict(color="#9ca3af", width=2, dash="dot"),
            hovertemplate=f"<b>VWAP Ontem</b><br>{vwap:,.1f} pts<extra></extra>",
        ))

    # Entrada
    if entrada and entrada > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[entrada, entrada],
            mode="lines",
            name=f"Entrada ({entrada:,.0f})",
            line=dict(color="#00d4ff", width=2, dash="dash"),
            hovertemplate=f"<b>Entrada</b><br>{entrada:,.0f}<extra></extra>",
        ))

    # Stop
    if stop and stop > 0:
        fig.add_trace(go.Scatter(
            x=x_line, y=[stop, stop],
            mode="lines",
            name=f"Stop ({stop:,.0f})",
            line=dict(color="#ff3d00", width=2, dash="dash"),
            hovertemplate=f"<b>Stop</b><br>{stop:,.0f}<extra></extra>",
        ))

    # Alvos
    for i, alvo in enumerate(alvos[:2]):
        if alvo and alvo > 0:
            fig.add_trace(go.Scatter(
                x=x_line, y=[alvo, alvo],
                mode="lines",
                name=f"Alvo {i+1} ({alvo:,.0f})",
                line=dict(color="#00ff88", width=1.5, dash="longdash"),
                hovertemplate=f"<b>Alvo {i+1}</b><br>{alvo:,.0f}<extra></extra>",
            ))

    # BSL
    for i, nivel in enumerate(bsl[:3]):
        fig.add_trace(go.Scatter(
            x=x_line, y=[nivel, nivel],
            mode="lines",
            name=f"BSL #{i+1} ({nivel:,.0f})",
            line=dict(color="#00bfff", width=1, dash="dot"),
            opacity=0.6,
            hovertemplate=f"<b>BSL</b><br>{nivel:,.0f}<extra></extra>",
        ))

    # SSL
    for i, nivel in enumerate(ssl[:3]):
        fig.add_trace(go.Scatter(
            x=x_line, y=[nivel, nivel],
            mode="lines",
            name=f"SSL #{i+1} ({nivel:,.0f})",
            line=dict(color="#ff6b6b", width=1, dash="dot"),
            opacity=0.6,
            hovertemplate=f"<b>SSL</b><br>{nivel:,.0f}<extra></extra>",
        ))

    # ---------- 4. Swing Highs / Lows (marcadores) ----------
    if candles and swings:
        swings_high = [s for s in swings if str(s.get("tipo", "")).startswith("HIGH")]
        swings_low = [s for s in swings if str(s.get("tipo", "")).startswith("LOW")]

        if swings_high:
            fig.add_trace(go.Scatter(
                x=[s["time"] for s in swings_high],
                y=[s["preco"] for s in swings_high],
                mode="markers",
                name="Swing High",
                marker=dict(color="#ff6b6b", size=8, symbol="triangle-down", line=dict(color="#ffffff", width=1)),
                hovertemplate="<b>Swing High</b><br>%{y:,.0f}<extra></extra>",
            ))

        if swings_low:
            fig.add_trace(go.Scatter(
                x=[s["time"] for s in swings_low],
                y=[s["preco"] for s in swings_low],
                mode="markers",
                name="Swing Low",
                marker=dict(color="#00ff88", size=8, symbol="triangle-up", line=dict(color="#ffffff", width=1)),
                hovertemplate="<b>Swing Low</b><br>%{y:,.0f}<extra></extra>",
            ))

    # ---------- 5. BOS / CHoCH (anotações) ----------
    if candles and eventos:
        for e in eventos[-4:]:
            tipo_ev = e.get("tipo", "")
            direcao = e.get("direcao", "")
            preco_ev = e.get("preco")
            time_ev = e.get("time")
            if preco_ev is None or time_ev is None:
                continue

            cor = "#00d4ff" if direcao == "ALTA" else "#ff6b6b"
            simbolo_seta = "↑" if direcao == "ALTA" else "↓"
            label = f"{tipo_ev} {simbolo_seta}"

            fig.add_annotation(
                x=time_ev, y=preco_ev,
                text=label,
                showarrow=True,
                arrowhead=2,
                arrowsize=1.2,
                arrowcolor=cor,
                ax=0,
                ay=-30 if direcao == "ALTA" else 30,
                font=dict(color=cor, size=10, family="Arial Black"),
                bgcolor="rgba(0,0,0,0.5)",
                bordercolor=cor,
                borderwidth=1,
                borderpad=2,
            )

    # ---------- 6. Preço atual (linha) ----------
    if preco_atual and preco_atual > 0:
        fig.add_hline(
            y=preco_atual,
            line=dict(color="white", width=1.5, dash="dot"),
            annotation_text=f"  Atual: {preco_atual:,.0f}",
            annotation_position="right",
            annotation_font=dict(color="white", size=11),
        )

    # ---------- Layout ----------
    fig.update_layout(
        title=dict(
            text=f"<b>WIN {tf_label} — Zonas Institucionais SMC</b> · "
                 f"Viés: <span style='color:{'#00ff88' if vies == 'ALTA' else '#ff6b6b' if vies == 'BAIXA' else '#ccc'}'>{vies}</span> · "
                 f"Confiança: {confianca}% · "
                 f"<span style='font-size:0.85em; color:#8b949e;'>últimos {len(candles) if candles else 0} candles</span>",
            font=dict(size=15),
        ),
        height=680,
        margin=dict(l=40, r=120, t=60, b=40),
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#1f2937",
            rangeslider=dict(visible=False),
            type="date" if candles else "-",
        ),
        yaxis=dict(
            title="Pontos (WIN)",
            showgrid=True,
            gridcolor="#1f2937",
            zeroline=False,
            autorange=True,
            side="right",
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(22, 27, 34, 0.85)",
            bordercolor="#30363d",
            borderwidth=1,
            font=dict(size=10),
        ),
        hovermode="x unified",
    )

    # Remove rangeslider nativo
    fig.update_xaxes(rangeslider_visible=False)

    return fig


# ==============================================================================
# MULTI-TIMEFRAME VISUAL (fix40): M1 → M5 → M15 empilhados
# ==============================================================================
def _carregar_dados_tf(tf_min: int) -> dict:
    """Carrega o JSON do SMC correspondente ao timeframe."""
    from config import COLETAS_DIR, FILE_SMC_REGRAS
    mapa = {
        1: COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json",
        5: FILE_SMC_REGRAS,
        15: COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json",
    }
    return carregar_json_defensivo(mapa.get(tf_min, FILE_SMC_REGRAS))


def _render_bloco_tf(tf_min: int, tf_label: str) -> None:
    """Renderiza header + seletor + gráfico de um timeframe."""
    dados_tf = _carregar_dados_tf(tf_min)

    st.markdown(f"### 🕯️ {tf_label} — Zonas SMC")

    if not dados_tf or "erro" in dados_tf:
        st.warning(
            f"⚠️ Arquivo SMC de {tf_label} não disponível. "
            f"Rode `python Rodar_SMC_Regras.py` pra gerar."
        )
        return

    # Cabeçalho com bias + confiança deste TF
    _bias_tf = dados_tf.get("bias_direcional", "LATERAL")
    _conf_tf = dados_tf.get("confianca_visual", 0)
    _cor = "#00ff88" if _bias_tf == "ALTA" else ("#ff6b6b" if _bias_tf == "BAIXA" else "#ccc")
    st.markdown(
        f"<div style='padding:6px 12px; border-left:4px solid {_cor}; "
        f"background:rgba(255,255,255,0.03); border-radius:6px;'>"
        f"Viés {tf_label}: <b style='color:{_cor};'>{_bias_tf}</b> · "
        f"Confiança: <b>{_conf_tf}%</b></div>",
        unsafe_allow_html=True,
    )

    # Seletor de candles deste TF
    _opcoes = OPCOES_CANDLES_POR_TF.get(tf_min, [30, 60, 100])
    _default = QTD_CANDLES_POR_TF.get(tf_min, 30)
    _qtd = st.selectbox(
        f"Candles visíveis ({tf_label}):",
        options=_opcoes,
        index=_opcoes.index(_default) if _default in _opcoes else 0,
        key=f"smc_qtd_tf_{tf_min}",
    )

    # Renderiza
    fig_tf = render_grafico_candles(
        dados_tf,
        qtd_visivel=_qtd,
        timeframe_min=tf_min,
        tf_label=tf_label,
    )
    st.plotly_chart(
        fig_tf,
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"plot_tf_{tf_min}",
    )


st.markdown("---")
st.markdown("## 📊 Visão Multi-Timeframe (M1 · M5 · M15)")
st.caption(
    "Sequência **micro → médio → macro**. Cada gráfico mostra as zonas SMC "
    "do timeframe correspondente, permitindo leitura visual da confluência."
)

# M1 (micro)
_render_bloco_tf(1, "M1")

st.markdown("<br>", unsafe_allow_html=True)

# M5 (médio — mantém comportamento atual)
_render_bloco_tf(5, "M5")

st.markdown("<br>", unsafe_allow_html=True)

# M15 (macro)
_render_bloco_tf(15, "M15")

# ---------- Sumário de distâncias ----------
st.markdown("##### 📌 Distâncias até o preço atual")
d1, d2, d3, d4 = st.columns(4)

poc = dados_smc.get("niveis_institucionais", {}).get("poc_ontem", 0.0)
vwap = dados_smc.get("niveis_institucionais", {}).get("vwap_ontem", 0.0)

if preco_atual and poc:
    d_poc = preco_atual - poc
    d1.metric("Δ até POC", f"{d_poc:+,.0f} pts", delta_color="normal" if d_poc > 0 else "inverse")
else:
    d1.metric("Δ até POC", "—")

if preco_atual and vwap:
    d_vwap = preco_atual - vwap
    d2.metric("Δ até VWAP", f"{d_vwap:+,.0f} pts", delta_color="normal" if d_vwap > 0 else "inverse")
else:
    d2.metric("Δ até VWAP", "—")

bsl_list = dados_smc.get("liquidez", {}).get("bsl", [])
bsl_acima = sorted([x for x in bsl_list if x > (preco_atual or 0)])
if bsl_acima and preco_atual:
    prox_bsl = bsl_acima[0]
    d3.metric("Próx. BSL (acima)", f"{prox_bsl:,.0f}", f"{prox_bsl - preco_atual:+,.0f} pts")
else:
    d3.metric("Próx. BSL (acima)", "—")

ssl_list = dados_smc.get("liquidez", {}).get("ssl", [])
ssl_abaixo = sorted([x for x in ssl_list if x < (preco_atual or 0)], reverse=True)
if ssl_abaixo and preco_atual:
    prox_ssl = ssl_abaixo[0]
    d4.metric("Próx. SSL (abaixo)", f"{prox_ssl:,.0f}", f"{prox_ssl - preco_atual:+,.0f} pts")
else:
    d4.metric("Próx. SSL (abaixo)", "—")

st.markdown("---")


# ==============================================================================
# PARÂMETROS DE EXECUÇÃO
# ==============================================================================
st.markdown("### 🎯 Parâmetros de Execução Gerados pelo Motor")
col_trade, col_status_filtro = st.columns([2, 1])

with col_trade:
    entrada = dados_smc.get("entrada_sugerida")
    stop = dados_smc.get("stop_sugerido")
    alvos = dados_smc.get("alvos", [])

    if entrada and stop:
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.markdown(
            f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>"
            f"🟢 <b>ORDEM BUY/SELL STOP:</b><br>"
            f"<span style='font-size:1.4rem; font-weight:bold; color:#00d4ff;'>{entrada:,.0f}</span></div>",
            unsafe_allow_html=True,
        )
        t_col2.markdown(
            f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>"
            f"🛑 <b>STOP LOSS TÉCNICO:</b><br>"
            f"<span style='font-size:1.4rem; font-weight:bold; color:#ff6b6b;'>{stop:,.0f}</span></div>",
            unsafe_allow_html=True,
        )
        alvos_txt = " | ".join([f"{x:,.0f}" for x in alvos]) if alvos else "Aguardando Alvo por Liquidez"
        t_col3.markdown(
            f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>"
            f"🏁 <b>ALVOS DE MITIGAÇÃO:</b><br>"
            f"<span style='font-size:1.1rem; font-weight:bold; color:#00ff88;'>{alvos_txt}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("⚖️ **Modo de Observação Ativo:** O preço atual não mitigou nenhum Order Block relevante com confirmação de volume.")

with col_status_filtro:
    meta = dados_smc.get("metadados", {})
    vol_filtro = meta.get("filtro_volume_real_aplicado", False)

    st.markdown("**Status das Validações:**")
    st.markdown(f"• Filtro de Volume: {'✅ **ATIVO**' if vol_filtro else '❌ Inativo'}")
    st.markdown(f"• Candles (Lookback): `{meta.get('n_candles', 0)}` bars")
    st.markdown(f"• Swings Mapeados: `{meta.get('n_swings', 0)}`")
    st.markdown(f"• Motor: `v{meta.get('versao_motor', 'N/A')}`")

st.markdown("---")


# ==============================================================================
# ESTRUTURAS INSTITUCIONAIS
# ==============================================================================
col_ob, col_fvg, col_liq = st.columns(3)

with col_ob:
    st.markdown("#### 🏢 Order Blocks")
    obs = dados_smc.get("order_blocks", [])
    if obs:
        for ob in obs:
            cor = "#00ff88" if ob["tipo"] == "COMPRA" else "#ff6b6b"
            validado = ob.get("validado_por", "")
            badge = f" <span style='color:#00d4ff; font-size:0.8em;'>[{validado}]</span>" if validado else ""
            st.markdown(f"""
            <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                🔹 <b>OB de {ob['tipo']}</b>{badge}<br>
                • Ref: <b>{ob['preco']:,.0f}</b><br>
                • Range: {ob['low']:,.0f} - {ob['high']:,.0f}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Nenhum Order Block ativo detectado.")

with col_fvg:
    st.markdown("#### 🕳️ Fair Value Gaps")
    fvgs = dados_smc.get("fair_value_gaps", [])
    if fvgs:
        for fvg in fvgs:
            cor = "#00ff88" if fvg["tipo"] == "COMPRA" else "#ff6b6b"
            st.markdown(f"""
            <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                🔸 <b>FVG {fvg['tipo']}</b><br>
                • Faixa: {fvg['inferior']:,.0f} ➔ {fvg['superior']:,.0f}<br>
                • Status: {'⚠️ Preenchido' if fvg.get('preenchido') else '🟢 Aberto'}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Nenhum FVG em aberto.")

with col_liq:
    st.markdown("#### 🎯 Liquidez Institucional")
    liq = dados_smc.get("liquidez", {})
    bsl = liq.get("bsl", [])
    ssl = liq.get("ssl", [])

    st.markdown("**🌐 BSL (Topos)**")
    if bsl:
        for p in bsl:
            st.markdown(f"• `{p:,.0f}` — *Equal Highs*")
    else:
        st.caption("Sem BSL mapeado.")

    st.markdown("**🩸 SSL (Fundos)**")
    if ssl:
        for p in ssl:
            st.markdown(f"• `{p:,.0f}` — *Equal Lows*")
    else:
        st.caption("Sem SSL mapeado.")

st.markdown("---")


# ==============================================================================
# CENÁRIOS E NÍVEIS INSTITUCIONAIS
# ==============================================================================
st.markdown("### 🗺️ Cenários Operacionais Mapeados")
cenarios = dados_smc.get("zonas_de_interesse_e_cenarios", [])
if cenarios:
    for i, cenario in enumerate(cenarios, start=1):
        if "DIVERGÊNCIA" in cenario:
            st.warning(f"**{i}.** {cenario}")
        else:
            st.markdown(f"**{i}.** {cenario}")
else:
    st.caption("Aguardando consolidação do range.")

st.markdown("---")
st.markdown("### 🏦 Níveis Institucionais (Resumo)")

ni1, ni2, ni3, ni4 = st.columns(4)
niveis = dados_smc.get("niveis_institucionais", {})
poc_v = niveis.get("poc_ontem", 0.0)
vwap_v = niveis.get("vwap_ontem", 0.0)
ob_alin = niveis.get("ob_alinhado_com_poc", False)

ni1.metric("POC Ontem", f"{poc_v:,.0f} pts")
ni2.metric("VWAP Ontem", f"{vwap_v:,.1f} pts")
ni3.metric("Preço Atual", f"{preco_atual:,.0f} pts")
ni4.metric("OB Alinhado com POC", "🟢 SIM" if ob_alin else "⚪ NÃO")

if preco_atual and poc_v:
    dist_poc = preco_atual - poc_v
    if abs(dist_poc) <= 100:
        st.success(f"📌 Preço **sobre a POC** de ontem ({dist_poc:+.0f} pts) — equilíbrio institucional.")
    elif dist_poc > 0:
        st.info(f"📌 Preço **{dist_poc:+,.0f} pts acima** da POC — viés comprador vs. referência.")
    else:
        st.warning(f"📌 Preço **{dist_poc:+,.0f} pts abaixo** da POC — viés vendedor vs. referência.")
```

### `pages/7.2_🤖_IA_SpikeImagem.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/7.2_🤖_IA_SpikeImagem.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar a análise de anomalias visuais e Spikes institucionais no tempo gráfico de 1min.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Importação de caminhos centralizados do config.py da V2
from config import COLETAS_DIR, FILE_WIN_1MIN, FILE_SMC_REGRAS

# Definição do caminho do arquivo de resultado da Visão IA (Mapeado via ecossistema)
FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - IA Spike Imagem", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🤖 IA Spike Imagem — Detecção de Anomalias LTF</h2>", unsafe_allow_html=True)
st.caption("Monitoramento quantitativo de picos de volume e volatilidade no tempo gráfico de 1 Minuto (LTF)")

st.info("⚡ **Módulo de Volatilidade:** Esta tela monitora movimentos abruptos (Spikes) e desequilíbrios de curtíssimo prazo capturados em background pelo pipeline V2.")

# --- CARGA DOS DADOS DE SUPORTE V2 ---
dados_visao = carregar_json_defensivo(FILE_SMC_VISAO_IA)
dados_smc_regras = carregar_json_defensivo(FILE_SMC_REGRAS)

# --- DIVISION DESIGN: GRÁFICO DE 1MIN VS DIAGNÓSTICO DE SPIKE ---
col_grafico, col_insights = st.columns([1.2, 1], gap="large")

with col_grafico:
    st.markdown("### 📉 Gráfico de Execução Rápida (WIN 1 Minuto)")
    
    # Exibe a imagem do gráfico de 1 minuto para o trader auditar o Spike visualmente
    if FILE_WIN_1MIN.exists():
        st.image(str(FILE_WIN_1MIN), caption="WIN_1min.png — Captura de momentum e fluxo em tempo real", use_container_width=True)
    else:
        st.warning("⚠️ Imagem 'WIN_1min.png' não encontrada na pasta Coletas/. Executando carregamento defensivo.")
        st.markdown(
            "<div style='background-color:#161b24; padding:60px 20px; text-align:center; border-radius:8px; border:1px solid #2a3a4a; color:#8b949e;'>",
            unsafe_allow_html=True
        )
        st.markdown("Aguardando nova captura de anomalia visual pelo orquestrador.")
        st.markdown("</div>", unsafe_allow_html=True)

with col_insights:
    st.markdown("### 🚨 Diagnóstico de Momentum e Fluxo")
    
    # KPIs Rápidos do Motor de Regras LTF
    preco_atual = dados_smc_regras.get("preco_atual", 0.0)
    bias_ltf = dados_smc_regras.get("bias_direcional", "NEUTRO")
    confianca_ltf = dados_smc_regras.get("confianca_visual", 0)
    
    c1, c2 = st.columns(2)
    c1.metric("Preço de Tela (WIN)", f"{preco_atual:,.0f} pts")
    
    if bias_ltf == "ALTA":
        c2.markdown("<div style='background-color:rgba(0, 255, 136, 0.1); padding:8px; border-radius:6px; text-align:center; border:1px solid #00ff88;'><span style='font-size:0.85rem; color:#ccc;'>MOMENTUM LTF</span><br><b style='color:#00ff88; font-size:1.1rem;'>🐂 COMPRA ACELERADA</b></div>", unsafe_allow_html=True)
    elif bias_ltf == "BAIXA":
        c2.markdown("<div style='background-color:rgba(255, 107, 107, 0.1); padding:8px; border-radius:6px; text-align:center; border:1px solid #ff6b6b;'><span style='font-size:0.85rem; color:#ccc;'>MOMENTUM LTF</span><br><b style='color:#ff6b6b; font-size:1.1rem;'>Bearish / Venda Forte</b></div>", unsafe_allow_html=True)
    else:
        c2.markdown("<div style='background-color:rgba(255, 255, 255, 0.05); padding:8px; border-radius:6px; text-align:center; border:1px solid #888;'><span style='font-size:0.85rem; color:#ccc;'>MOMENTUM LTF</span><br><b style='color:#ccc; font-size:1.1rem;'>⚖️ Acumulação / Range</b></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Cruzamento com os metadados do motor para validar se houve Vela de Expansão (Inbalance Real)
    meta_regras = dados_smc_regras.get("metadados", {})
    filtro_vol = meta_regras.get("filtro_volume_aplicado", False)
    
    st.markdown("**Auditoria do Motor Contextual (Filtro Institucional):**")
    if filtro_vol:
        st.success("✅ **Filtro de Deslocamento de Volume Ativo:** O movimento atual foi validado acima da média móvel institucional (Vela de Expansão Realizada).")
    else:
        st.info("⚖️ **Volume Normal:** Oscilação dentro da média aritmética. Sem atuação de grandes lotes (ruído de varejo).")
        
    st.markdown("---")
    
    # Exibição dos Eventos de Estrutura de Curto Prazo (LTF) capturados
    st.markdown("**Últimos Eventos de Estrutura Registrados (LTF):**")
    eventos_est = dados_smc_regras.get("eventos_structure", [])
    
    if eventos_est:
        linhas_eventos = []
        for ev in eventos_est[-4:]:  # Exibe os 4 mais recentes para não poluir
            linhas_eventos.append({
                "Horário": ev.get("time", "N/A")[-8:],
                "Evento": f"⚠️ {ev.get('tipo')}" if ev.get('tipo') == "CHoCH" else f"🔷 {ev.get('tipo')}",
                "Direção": "🔼 ALTA" if ev.get("direcao") == "ALTA" else "🔽 BAIXA",
                "Preço": f"{ev.get('preco'):,.0f} pts"
            })
        df_ev = pd.DataFrame(linhas_eventos)
        st.table(df_ev.set_index("Horário"))
    else:
        st.caption("Sem quebras de estrutura (BOS/CHoCH) registradas no histórico recente de 1min.")

```

### `pages/7.3_📥_Gerador_Profit_Pro.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/7.3_📥_Gerador_Profit_Pro.py
Versão: 4.0 - SMC Multi-Levels (Produção V2)
Objetivo: Gerar scripts NTSL dinâmicos plotando TODOS os níveis mapeados pelo Motor e pela Visão IA.
"""

import streamlit as st
import json
import re
import pandas as pd 
from datetime import datetime
from pathlib import Path

# Importação de caminhos centralizados do seu config.py
from config import COLETAS_DIR, FILE_DECISAO_V2, FILE_SMC_REGRAS

# Definição do caminho do arquivo de Visão IA
FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho_path):
    """Carrega arquivos JSON de forma defensiva protegendo a UI contra falhas."""
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# --- CONFIGURAÇÃO GLOBAL ---
st.set_page_config(page_title="Quant Terminal - Gerador Multi-Levels", layout="wide")

# Carga de arquivos V2
regras_algo = carregar_json_defensivo(FILE_SMC_REGRAS)
visao_ia = carregar_json_defensivo(FILE_SMC_VISAO_IA)

# --- CORPO DA INTERFACE ---
st.markdown("<h2 style='color:#00d4ff;'>📥 Gerador ProfitPro - Plotagem de Níveis em Massa</h2>", unsafe_allow_html=True)
st.caption("Exportador dinâmico de código NTSL contendo mapeamento completo de estruturas macro e micro")

# --- SELEÇÃO DE INTELIGÊNCIA ---
fonte_dados = st.selectbox(
    "🧠 Selecione a matriz de dados para extração de níveis:",
    ["Motor de Regras Algorítmico (AnaliseGraficaSMC_Regras.json)", "Visão Inteligência Artificial (AnaliseGraficaSMC.json)"]
)

st.markdown("---")

# Dicionário unificado para guardar os níveis e suas respectivas cores de exibição no Profit
# Chave: Preço (int) | Valor: Cor do Profit (clVerde, clVermelho, clAzul, etc)
niveis_mapeados = {}

if "Motor de Regras" in fonte_dados:
    st.markdown("### 📊 Níveis Identificados: Motor Matemático MT5")
    
    # 1. Coleta de Order Blocks
    for ob in regras_algo.get("order_blocks", []):
        preco = int(ob.get("preco", 0))
        if preco > 0:
            niveis_mapeados[preco] = "clVerde" if ob.get("tipo") == "COMPRA" else "clVermelho"
            
    # 2. Coleta de Fair Value Gaps (Usa o ponto médio do Gap para traçar a linha)
    for fvg in regras_algo.get("fair_value_gaps", []):
        sup = fvg.get("superior", 0)
        inf = fvg.get("inferior", 0)
        if sup > 0 and inf > 0:
            meio_fvg = int((sup + inf) / 2)
            niveis_mapeados[meio_fvg] = "clAmarelo"
            
    # 3. Coleta de Liquidez (BSL e SSL)
    liq = regras_algo.get("liquidez", {})
    for p in liq.get("bsl", []):
        niveis_mapeados[int(p)] = "clAzul"
    for p in liq.get("ssl", []):
        niveis_mapeados[int(p)] = "clFucsia"
        
    # 4. Gatilhos operacionais adicionais se houverem
    if regras_algo.get("entrada_sugeriga"):
        niveis_mapeados[int(regras_algo["entrada_sugerida"])] = "clBranco"

else:
    st.markdown("### 🤖 Níveis Identificados: Visão IA / Spike Imagem")
    
    # Varre as estruturas textuais e extrai os números usando Regex de forma defensiva
    estruturas = visao_ia.get("estruturas_coletadas", [])
    
    for est in estruturas:
        # Encontra a pontuação no início da string (ex: "178.270: OB VENDA")
        match = re.match(r"^([\d\.]+)", est.strip())
        if match:
            try:
                preco_limpo = int(match.group(1).replace(".", ""))
                
                # Heurística de cor baseada no texto descritivo capturado pela IA
                est_lower = est.lower()
                if "compra" in est_lower or "low" in est_lower or "suporte" in est_lower:
                    cor = "clVerde"
                elif "venda" in est_lower or "high" in est_lower or "resistencia" in est_lower:
                    cor = "clVermelho"
                elif "fvg" in est_lower:
                    cor = "clAmarelo"
                else:
                    cor = "clBranco"
                    
                niveis_mapeados[preco_limpo] = cor
            except:
                continue

# --- CONSTRUÇÃO DINÂMICA DO CÓDIGO NTSL (PROFITPRO) ---
if niveis_mapeados:
    # Remove duplicidades mantendo a ordenação por preço
    precos_ordenados = sorted(list(niveis_mapeados.keys()))
    total_niveis = len(precos_ordenados)
    
    # 1. Montagem do Bloco de Variáveis (Var)
    linhas_var = []
    for idx in range(1, total_niveis + 1):
        linhas_var.append(f"  Nivel_{idx} : Real;")
    bloco_var = "\n".join(linhas_var)
    
    # 2. Montagem do Bloco de Atribuição e Plotagem (Inicio)
    linhas_codigo = []
    for idx, preco in enumerate(precos_ordenados, start=1):
        cor_escolhida = niveis_mapeados[preco]
        
        # Constrói o bloco Pascal para cada linha achada no JSON do seu ecossistema
        linhas_codigo.append(f"  Nivel_{idx} := {preco};")
        
        if idx == 1:
            linhas_codigo.append(f"  Plot(Nivel_{idx});")
            linhas_codigo.append(f"  SetPlotColor(1, {cor_escolhida});")
        else:
            linhas_codigo.append(f"  Plot{idx}(Nivel_{idx});")
            linhas_codigo.append(f"  SetPlotColor({idx}, {cor_escolhida});")
            
        # Linha pontilhada (estilo 1) para FVGs e Liquidez, contínua para OBs
        if cor_escolhida in ["clAmarelo", "clAzul", "clFucsia"]:
            linhas_codigo.append(f"  SetPlotStyle({idx}, 1);")
            
    bloco_atribuicao = "\n".join(linhas_codigo)
    
    # 3. Compilação do Script NTSL Final
    script_final = f"""{{
    Script NTSL gerado automaticamente pelo Quant Terminal V2 Python
    Fonte de Inteligencia: {fonte_dados}
    Total de Niveis Identificados: {total_niveis}
    Data de Geracao: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
    
    Legenda de Cores Injetadas:
    • Verde    ➔ Regiões de Compra / OB Compra / Strong Low
    • Vermelho ➔ Regiões de Venda / OB Venda / Strong High
    • Amarelo  ➔ Fair Value Gaps (FVG) / Desequilíbrio
    • Azul     ➔ Liquidez Compradora (BSL)
    • Fucsia   ➔ Liquidez Vendedora (SSL)
}}
Var
{bloco_var}

Inicio
{bloco_atribuicao}
Fim;"""

    # --- EXIBIÇÃO NA UI STREAMLIT ---
    st.markdown(f"#### 📜 Código NTSL Gerado ({total_niveis} Níveis Ativos)")
    st.code(script_final, language="pascal")
    
    # Painel de conferência em colunas ou expander
    with st.expander("🔍 Visualizar Tabela de Auditoria dos Níveis Injetados"):
        linhas_auditoria = []
        for p in precos_ordenados:
            linhas_auditoria.append({"Preço (Pontos)": f"{p:,.0f}", "Cor Associada": niveis_mapeados[p].replace("cl", "")})
        st.table(pd.DataFrame(linhas_auditoria))

else:
    st.warning("⚠️ Nenhum nível válido foi encontrado no arquivo JSON selecionado. Aguardando processamento do pipeline.")

```

### `pages/7.4_🤖_IA_Imagem.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/7.4_🤖_IA_Imagem.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar os insights de Smart Money gerados pela Visão Computacional (IA) sobre os gráficos do WIN.
"""

import streamlit as st
import json
from pathlib import Path

# Importação de caminhos centralizados do config.py da V2
from config import COLETAS_DIR, FILE_WIN_5MIN

# Definição do caminho do arquivo de resultado da Visão IA
FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - IA Spike Imagem", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🤖 IA Spike Imagem — Visão Computacional SMC</h2>", unsafe_allow_html=True)
st.caption("Auditoria de insights e estruturas gráficas extraídas por modelos de visão em background")

st.info("💡 **Arquitetura V2:** Para mitigar latência na UI, o processamento de imagem é executado de forma assíncrona pelo backend. Esta tela exibe o último snapshot auditado.")

# --- CARGA DOS RESULTADOS DA VISÃO IA ---
dados_visao = carregar_json_defensivo(FILE_SMC_VISAO_IA)

# --- DIVISION DESIGN: IMAGEM VS TEXTO DA IA ---
col_grafico, col_insights = st.columns([1.2, 1], gap="large")

with col_grafico:
    st.markdown("### 📈 Gráfico Analisado (MT5 / TradingView)")
    
    # Exibe a imagem física que o backend enviou para a IA
    if FILE_WIN_5MIN.exists():
        st.image(str(FILE_WIN_5MIN), caption="WIN_5min.png — Captura utilizada na última janela analítica", use_container_width=True)
    else:
        st.warning("⚠️ Arquivo físico de imagem 'WIN_5min.png' não encontrado na pasta Coletas/. Execute o script de limpeza/captura.")
        # Fallback visual caso a imagem não exista
        st.markdown(
            "<div style='background-color:#161b24; padding:60px 20px; text-align:center; border-radius:8px; border:1px solid #2a3a4a; color:#8b949e;'>"
            "📊 Aguardando nova captura de tela do gráfico do Mini Índice."
            "</div>", 
            unsafe_allow_html=True
        )

with col_insights:
    st.markdown("### 🧠 Diagnóstico de Estruturas (Leitura da IA)")
    
    if not dados_visao:
        st.error("❌ Erro: O arquivo 'AnaliseGraficaSMC.json' não foi encontrado ou está corrompido. O motor contextual de visão precisa ser executado pelo Orquestrador V2.")
    else:
        # Exibição do Viés Computacional Interpretado pelo Modelo
        bias_ia = dados_visao.get("bias_direcional", "NEUTRO / LATERAL")
        tf_identificado = dados_visao.get("timeframes_identificados", "Não Mapeado")
        
        st.markdown(f"**Timeframe Detectado pela IA:** `{tf_identificado}`")
        
        if "COMPRA" in bias_ia.upper() or "BULL" in bias_ia.upper() or "ALTA" in bias_ia.upper():
            st.success(f"Viés da IA: {bias_ia}")
        elif "VENDA" in bias_ia.upper() or "BEAR" in bias_ia.upper() or "BAIXA" in bias_ia.upper():
            st.error(f"Viés da IA: {bias_ia}")
        else:
            st.warning(f"Viés da IA: {bias_ia}")
            
        st.markdown("---")
        
        # 1. Renderização das Estruturas Coletadas Textualmente
        st.markdown("**Níveis e Blocos de Preço Identificados no Gráfico:**")
        estruturas = dados_visao.get("estruturas_coletadas", [])
        if estruturas:
            for est in estruturas:
                st.markdown(f"• {est}")
        else:
            st.caption("Nenhum nível estrutural extraído textualmente neste snapshot.")
            
        st.markdown("---")
        
        # 2. Piscinas de Liquidez Mapeadas Visualmente
        st.markdown("**Mapeamento de Liquidez (Zonas de Caça):**")
        liquidez = dados_visao.get("liquidez_relevante", [])
        if liquidez:
            for liq in liquidez:
                st.markdown(f"🎯 {liq}")
        else:
            st.caption("Nenhuma piscina de liquidez expressiva apontada pelo modelo de visão.")
            
        st.markdown("---")
        
        # 3. Cenários Operacionais Sugeridos pela IA
        st.markdown("**Mapeamento de Cenários para o Pregão:**")
        cenarios = dados_visao.get("zonas_de_interesse_e_cenarios", [])
        if cenarios:
            for idx, cenario in enumerate(cenarios, start=1):
                st.markdown(f"**{idx}.** *{cenario}*")
        else:
            st.caption("Sem cenários preditivos gerados para esta janela de preço.")

```

### `pages/7.5_📅_Noticias.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/6.2_📅_Noticias.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar o calendário econômico do dia e os alertas de impacto/travas gerados pelo pipeline.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
from config import FILE_NOTICIAS_IMPACTO  # Caminho centralizado da V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Calendário Econômico", layout="wide")

# --- CARGA DOS DADOS DE IMPACTO V2 ---
dados_noticias = carregar_json_defensivo(FILE_NOTICIAS_IMPACTO)

st.markdown("<h2 style='color:#00d4ff;'>📅 Calendário Econômico e Impacto Macro</h2>", unsafe_allow_html=True)
st.caption(f"Análise quantitativa de risco gerada pelo pipeline | Auditoria: {dados_noticias.get('metadata', {}).get('timestamp', 'N/A')}")

if not dados_noticias:
    st.warning("⚠️ Arquivo de impacto de notícias não encontrado. Certifique-se de que o pipeline (Analise_Noticias.py) foi executado com sucesso.")
    st.stop()

resumo = dados_noticias.get("resumo", {})
alertas = dados_noticias.get("alertas", {})
impacto_total = resumo.get("impacto_total", 0)
classificacao = resumo.get("classificacao", "BAIXO")

# --- PAINEL DE METRICAS E ALERTAS OPERACIONAIS ---
c1, c2, c3 = st.columns(3)
c1.metric("Pontuação de Impacto Global", f"{impacto_total} pts", delta=f"Risco: {classificacao}")

# Alerta de Risco para a Abertura do Mini Índice (WIN)
risco_win = alertas.get("risco_abertura_WIN", False)
if risco_win or impacto_total >= 10:
    c2.markdown("<div style='background-color:rgba(255, 107, 107, 0.15); padding:10px; border-radius:8px; border:1px solid #ff6b6b; text-align:center; height:100%;'><span style='color:#ff6b6b; font-weight:bold; font-size:1.1rem;'>⚠️ ALERTA: RISCO ELEVADO</span><br><span style='font-size:0.85rem; color:#ccc;'>Janela de Abertura do WIN instável.</span></div>", unsafe_allow_html=True)
else:
    c2.markdown("<div style='background-color:rgba(0, 255, 136, 0.1); padding:10px; border-radius:8px; border:1px solid #00ff88; text-align:center; height:100%;'><span style='color:#00ff88; font-weight:bold; font-size:1.1rem;'>🟢 ABERTURA LIBERADA</span><br><span style='font-size:0.85rem; color:#ccc;'>Sem volatilidade abusiva nas notícias.</span></div>", unsafe_allow_html=True)

# Trava do leilão das 09:00h
trava_0900 = alertas.get("tem_3_estrelas_brasil_0900", False)
if trava_0900:
    c3.markdown("<div style='background-color:rgba(255, 170, 0, 0.15); padding:10px; border-radius:8px; border:1px solid #ffaa00; text-align:center; height:100%;'><span style='color:#ffaa00; font-weight:bold; font-size:1.1rem;'>🚨 TRAVA OPERACIONAL CRÍTICA</span><br><span style='font-size:0.85rem; color:#ccc;'>Notícia BRL 3 Estrelas às 09:00h.</span></div>", unsafe_allow_html=True)
else:
    c3.markdown("<div style='background-color:#161b24; padding:10px; border-radius:8px; border:1px solid #2a3a4a; text-align:center; height:100%;'><span style='color:#8b949e; font-weight:bold; font-size:1.1rem;'>🟢 SEM TRAVA 09:00H</span><br><span style='font-size:0.85rem; color:#ccc;'>Abertura livre de IPCA/PIB institucional.</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- EXIBIÇÃO DE ADVERTÊNCIAS ESPECÍFICAS ---
if alertas.get("tem_3_estrelas_outros_horarios", False):
    st.markdown("**🚨 Eventos de 3 Estrelas (Alto Impacto) Agendados para Hoje:**")
    for item in alertas.get("noticias_3_estrelas_outros_horarios", []):
        st.error(f"• **Horário: {item['hora']}** | [{item['moeda']}] {item['pais']} - *{item['evento']}*")
        
if alertas.get("tem_multiplas_2_estrelas_mesmo_horario", False):
    st.markdown("**⚠️ Concentração de Notícias de Médio Impacto (2 Estrelas):**")
    for item in alertas.get("horarios_multiplas_2_estrelas", []):
        st.warning(f"• **Horário: {item['hora']}** acumula `{item['quantidade_2_estrelas']}` eventos simultâneos de 2 estrelas. Potencial de volatilidade combinada.")

st.markdown("---")

# --- GRADE COMPLETA DO CRONOGRAMA ECONÔMICO ---
st.markdown("### 📋 Agenda Cronológica do Pregão")
horarios_data = dados_noticias.get("horarios", [])

linhas_tabela = []
for h_bloco in horarios_data:
    hora = h_bloco.get("hora", "N/A")
    pontos_hora = h_bloco.get("pontuacao", 0)
    risco_hora = h_bloco.get("classificacao", "BAIXO")
    
    for evento in h_bloco.get("eventos", []):
        linhas_tabela.append({
            "Horário (BR)": hora,
            "Moeda / País": f"[{evento.get('moeda')}] {evento.get('pais')}",
            "Evento Econômico": evento.get("nome"),
            "Peso Quant": evento.get("peso", 0),
            "Importância": "⭐" * evento.get("estrelas", 1),
            "Risco do Bloco Horário": f"{pontos_hora} pts ({risco_hora})"
        })

if linhas_tabela:
    df_noticias = pd.DataFrame(linhas_tabela)
    # Ordena cronologicamente pelo horário
    df_noticias = df_noticias.sort_values(by="Horário (BR)")
    st.dataframe(df_noticias.set_index("Horário (BR)"), use_container_width=True)
else:
    st.info("🟢 Nenhuma notícia de médio ou alto impacto agendada para o dia de hoje.")

```

### `pages/7_🔬_Analise_Tendencia.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/6.1_🔬_Analise_Tendencia.py
Versão: 2.10 - Limpeza Definitiva (Sem colunas auxiliares, lógica baseada na própria UI)
Objetivo: Renderizar a análise de tendência sequencial (10m ➔ 5m ➔ 0m) categorizada e estilizada.
"""

import streamlit as st
import json
import pandas as pd
from config import FILE_TENDENCIAS  # Importação centralizada do config V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Análise de Tendência", layout="wide")

# --- CARGA DOS DADOS V2 ---
dados_tendencias = carregar_json_defensivo(FILE_TENDENCIAS)

st.markdown("<h2 style='color:#00d4ff;'>🔬 Análise Cíclica de Tendência (Janela Móvel)</h2>", unsafe_allow_html=True)
st.caption("Mapeamento sequencial de variação de preços a cada 5 minutos (10m ➔ 5m ➔ Atual)")

if not dados_tendencias:
    st.warning("⚠️ Arquivo de tendências não encontrado ou vazio. Certifique-se de que o pipeline rodou a rotação temporal (rodar_pipeline_3x.bat).")
    st.stop()

# --- SEÇÃO 1: OS MAIORES DRIVERS DO MINI ÍNDICE (WIN) ---
st.markdown("### 🎯 Direcionadores Críticos do WIN")
st.caption("Acompanhamento imediato dos ativos com maior peso de correlação com o Mini Índice")

drivers_win = ["WIN_FUT", "CME_MINI:ES1!", "AMEX:EWZ", "VALE3", "PETR4", "BMFBOVESPA:DI1F2029"]

cols = st.columns(len(drivers_win))

for idx, ativo in enumerate(drivers_win):
    with cols[idx]:
        if ativo in dados_tendencias:
            info = dados_tendencias[ativo]
            padrao = info.get("padrao_comportamento", "Estavel_E_Estavel")
            var_atual = info.get("intervalo_5_para_0", {}).get("variacao_pct", 0.0)
            
            nome_exibicao = ativo.replace("CME_MINI:", "").replace("AMEX:", "").replace("BMFBOVESPA:", "")
            
            if "Alta_E_Alta" in padrao:
                cor_box = "rgba(0, 255, 136, 0.15)"
                border_color = "#00ff88"
                txt_status = "🚀 Forte Alta"
            elif "Baixa_E_Baixa" in padrao:
                cor_box = "rgba(255, 107, 107, 0.15)"
                border_color = "#ff6b6b"
                txt_status = "📉 Forte Baixa"
            elif "Alta" in padrao.split("_E_")[-1]:
                cor_box = "rgba(0, 212, 255, 0.1)"
                border_color = "#00d4ff"
                txt_status = "🔺 Recompondo"
            elif "Baixa" in padrao.split("_E_")[-1]:
                cor_box = "rgba(255, 170, 0, 0.1)"
                border_color = "#ffaa00"
                txt_status = "🔻 Corrigindo"
            else:
                cor_box = "rgba(255, 255, 255, 0.05)"
                border_color = "#888"
                txt_status = "⚖️ Estável"
                
            st.markdown(
                f"<div style='background-color:{cor_box}; padding:12px; border-radius:8px; border:1px solid {border_color}; text-align:center; height:100%;'>"
                f"<b style='font-size:1.1rem; color:#fff;'>{nome_exibicao}</b><br>"
                f"<span style='font-size:1.3rem; font-weight:bold;'>{var_atual:+.3f}%</span><br>"
                f"<span style='font-size:0.85rem; color:#ccc;'>{txt_status}</span>"
                f"</div>", 
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='text-align:center; padding:15px; color:#555;'>Falta Snapshot</div>", unsafe_allow_html=True)

st.markdown("---")

# --- SEÇÃO 2: GRADE GERAL SEPARADA POR TIPO DE ATIVO ---
st.markdown("### 📋 Grade Geral de Rotação de Memória Temporal (Por Categoria)")
st.caption("Histórico milimétrico categorizado com cores calibradas pelo impacto direto ou inverso no WINFUT")

TICKERS_EXCLUIDOS = ["WDO_LAST_TICK", "WIN_LAST_TICK"]

def categorizar_ativo(nome_ativo):
    n = nome_ativo.upper()
    if any(k in n for k in ["WIN", "WDO", "DI1", "PTAX"]):
        return "1. Futuros & Taxas B3"
    elif any(k in n for k in ["SP500", "NASDAQ", "VIX", "DXY", "ES1", "NQ1"]):
        return "2. Índices Globais & Câmbio"
    elif any(k in n for k in ["IRON", "CRUDE", "GOLD", "FEF", "CL1"]):
        return "3. Commodities & Metais"
    else:
        return "4. Ações & ADRs Brasileiras"

# Ativos de correlação inversa com o WIN
ATIVOS_INVERSOS = ["DXY", "VIX", "WDO", "USDBRL"]

categorias_dict = {}

for ativo, info in dados_tendencias.items():
    if ativo in TICKERS_EXCLUIDOS:
        continue
        
    cat = categorizar_ativo(ativo)
    if cat not in categorias_dict:
        categorias_dict[cat] = []
        
    precos = info.get("precos", {})
    int_10_5 = info.get("intervalo_10_para_5", {})
    int_5_0 = info.get("intervalo_5_para_0", {})
    
    nome_limpo = ativo.split(":")[-1] if ":" in ativo else ativo
    padrao = info.get("padrao_comportamento", "Estavel_E_Estavel")
    
    if "Alta_E_Alta" in padrao:
        padrao_formatado = "🚀 Alta Contínua"
    elif "Baixa_E_Baixa" in padrao:
        padrao_formatado = "📉 Queda Contínua"
    elif "Baixa" in padrao.split("_E_")[0] and "Alta" in padrao.split("_E_")[1]:
        padrao_formatado = "🔄 Reversão p/ Alta"
    elif "Alta" in padrao.split("_E_")[0] and "Baixa" in padrao.split("_E_")[1]:
        padrao_formatado = "⚠️ Perda de Momento"
    else:
        padrao_formatado = f"⚖️ {padrao.replace('_E_', ' ➔ ')}"
    
    # Adicionamos direto o DataFrame limpo sem colunas ocultas
    categorias_dict[cat].append({
        "Ativo": nome_limpo,
        "Preço 10m": precos.get('10m', 0.0) if precos.get('10m') else 0.0,
        "Preço 5m": precos.get('5m', 0.0) if precos.get('5m') else 0.0,
        "Preço Atual (0m)": precos.get('0m', 0.0) if precos.get('0m') else 0.0,
        "Var. 10m ➔ 5m (%)": int_10_5.get('variacao_pct', 0.0),
        "Var. 5m ➔ Atual (%)": int_5_0.get('variacao_pct', 0.0),
        "Padrão Dinâmico": padrao_formatado
    })

# Renderização organizada de todas as tabelas na página
for categoria in sorted(categorias_dict.keys()):
    st.markdown(f"#### **{categoria}**")
    linhas = categorias_dict[categoria]
    df_cat = pd.DataFrame(linhas)
    
    def colorir_impacto_win(row):
        estilos = [''] * len(row)
        nome_ativo = row["Ativo"].upper()
        padrao_txt = row["Padrão Dinâmico"]
        is_inverso = any(inv in nome_ativo for inv in ATIVOS_INVERSOS)
        
        for idx, col_name in enumerate(row.index):
            # Colunas de Variação
            if "Var." in col_name:
                val = row[col_name]
                if isinstance(val, (int, float)):
                    if val > 0:
                        cor = '#ff6b6b' if is_inverso else '#00ff88'
                        estilos[idx] = f'color: {cor}; font-weight: bold;'
                    elif val < 0:
                        cor = '#00ff88' if is_inverso else '#ff6b6b'
                        estilos[idx] = f'color: {cor}; font-weight: bold;'
            
            # Coluna de Padrão Dinâmico (pintada com base no texto exibido)
            elif col_name == "Padrão Dinâmico":
                if "Alta Contínua" in padrao_txt or "Reversão p/ Alta" in padrao_txt:
                    cor = '#ff6b6b' if is_inverso else '#00ff88'
                    estilos[idx] = f'color: {cor}; font-weight: bold;'
                elif "Queda Contínua" in padrao_txt:
                    cor = '#00ff88' if is_inverso else '#ff6b6b'
                    estilos[idx] = f'color: {cor}; font-weight: bold;'
                    
        return estilos

    # Aplica o estilo diretamente sobre o dataframe final limpo
    df_estilizado = df_cat.style.apply(colorir_impacto_win, axis=1).format({
        "Preço 10m": "{:,.3f}",
        "Preço 5m": "{:,.3f}",
        "Preço Atual (0m)": "{:,.3f}",
        "Var. 10m ➔ 5m (%)": "{:+.3f}%",
        "Var. 5m ➔ Atual (%)": "{:+.3f}%"
    })
    
    st.dataframe(
        df_estilizado, 
        use_container_width=True, 
        hide_index=True
    )
    st.markdown("")
```

### `pages/8.1_🗺️_Mapa_da_Aplicacao.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/8.1_🗺️_Mapa_da_Aplicacao.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar o mapa de fluxo de dados dinâmico da aplicação (Pipeline V2).
"""

import streamlit as st
import json
from pathlib import Path

# Importação de caminhos centralizados do config.py da V2
from config import FILE_PIPELINE_LOG, COLETAS_DIR

# Definição do caminho do mapa de fluxo dinâmico
FILE_MAPA_FLUXO = COLETAS_DIR / "Mapa_Fluxo.json"

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Mapa da Aplicação", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🗺️ Mapa da Aplicação e Esteira do Pipeline</h2>", unsafe_allow_html=True)
st.caption("Arquitetura e fluxo dinâmico de dados entre scripts e arquivos de suporte (V2)")

# --- CARGA DOS ARQUIVOS DE MAPA E STATUS ---
mapa_fluxo = carregar_json_defensivo(FILE_MAPA_FLUXO)
log_pipeline = carregar_json_defensivo(FILE_PIPELINE_LOG)

if not mapa_fluxo:
    st.warning("⚠️ Arquivo 'Mapa_Fluxo.json' não encontrado. Certifique-se de executar o script 'Gerar_Mapa_Fluxo.py' para gerar o mapeamento dinâmico.")
    st.stop()

# --- PAINEL DE CONTROLE / METADADOS DO MAPA ---
meta_mapa = mapa_fluxo.get("metadata", {})
st.info(f"🧬 **Mapeamento Atualizado:** Gerado automaticamente em `{meta_mapa.get('gerado_em', 'N/A')}` para o ecossistema `{meta_mapa.get('projeto', 'N/A')}`.")

# Captura o status da última execução real do pipeline para exibir em tela
status_geral = log_pipeline.get("status_geral", "DESCONHECIDO")
data_exec = log_pipeline.get("data_execucao", "N/A")

if status_geral == "SUCESSO":
    st.success(f"✅ **Último Ciclo do Pipeline:** SUCESSO (Executado em {data_exec})")
else:
    st.error(f"❌ **Último Ciclo do Pipeline:** FALHA ou INTERROMPIDO (Verifique o log em {data_exec})")

st.markdown("---")

# --- RENDERIZAÇÃO ESTILIZADA DA ESTEIRA (PIPELINE) ---
st.markdown("### 🛠️ Sequência Dinâmica de Processamento (Etapas)")
st.caption("Clique em cada etapa para expandir os detalhes de arquitetura, arquivos envolvidos, inputs e outputs.")

etapas = mapa_fluxo.get("pipeline", [])
etapas_status = {item.get("etapa"): item.get("status", "OK") for item in log_pipeline.get("etapas", [])}

for passo in etapas:
    num_etapa = passo.get("etapa", 0)
    nome_etapa = passo.get("nome", "Etapa Sem Nome")
    descricao = list(passo.get("arquivos", ["N/A"]))[0] if passo.get("arquivos") else "N/A"
    
    # Identifica o status real dessa etapa específica no último log de produção
    # O main_pipeline gera strings como "0 - LIMPEZA DE IMAGENS...", vamos casar pelo número do início
    status_etapa_real = "AGUARDANDO"
    for item_log in log_pipeline.get("etapas", []):
        if item_log.get("etapa", "").startswith(str(num_etapa)):
            status_etapa_real = item_log.get("status", "OK")
            break
            
    # Define o emoji de status para o cabeçalho do expander
    emoji_status = "🟢" if status_etapa_real == "OK" else ("🟡" if status_etapa_real == "AGUARDANDO" else "🔴")
    
    # Renderiza o Expander dinâmico contendo a esteira de dados do script
    with st.expander(f"{emoji_status} Etapa {num_etapa} — {nome_etapa}"):
        st.markdown(f"**Description / Função:** {passo.get('descricao', 'Sem descrição mapeada.')}")
        st.markdown(f"**Script Executor (Python):** `{descricao}`")
        
        col_in, col_out = st.columns(2)
        
        with col_in:
            st.markdown("📥 **Fontes de Entrada / Origem:**")
            inputs = passo.get("entrada", [])
            if inputs:
                for inp in inputs:
                    st.markdown(f"- `{inp}`")
            else:
                st.caption("Sem dependências de arquivos externos.")
                
        with col_out:
            st.markdown("📤 **Artefatos Gerados (Saída JSON/MD):**")
            outputs = passo.get("saida", [])
            if outputs:
                for out in outputs:
                    st.markdown(f"- `Coletas/{out}`")
            else:
                st.caption("Script de processo em lote ou no-op (Sem persistência física).")

st.markdown("---")
st.caption("🔒 Módulo de governança arquitetural ativo — Sincronizado automaticamente com a AST (Abstract Syntax Tree) do main_pipeline.py.")

```

### `pages/8.2_🔢_Calculadora.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/8.2_🔢_Calculadora.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Calculadora operacional de risco, simulação de ordens e dimensionamento de lote para WIN.
"""

import streamlit as st
import json
from config import FILE_UNIFICADO  # Importação centralizada do config V2

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Calculadora Operacional", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🔢 Calculadora Operacional e Gestão de Risco</h2>", unsafe_allow_html=True)
st.caption("Simulador quantitativo para dimensionamento de posição e gerenciamento de capital (WIN)")

# --- CARGA DE PREÇOS V2 PARA PREENCHIMENTO PADRÃO ---
unificados = carregar_json_defensivo(FILE_UNIFICADO)
ativos = unificados.get("ativos", {})
win_last = ativos.get("WIN_LAST_TICK", {}).get("preco", 175000.0) # Fallback seguro se vazio

# --- INTERFACE DE ENTRADA DE DADOS ---
st.markdown("### 🛠️ Parâmetros da Operação (Simulação)")

col_params, col_fibo = st.columns(2, gap="large")

with col_params:
    st.markdown("**Dimensionamento de Lote e Capital:**")
    capital_total = st.number_input("Capital Total Alocado na Corretora (R$):", min_value=100.0, value=5000.0, step=500.0)
    numero_contratos = st.number_input("Quantidade de Contratos (Lote WIN):", min_value=1, value=5, step=1)
    
    st.markdown("<br>**Níveis de Preço do Trade (SMC/ICT):**", unsafe_allow_html=True)
    preco_entrada = st.number_input("Preço de Entrada (Gatilho Stop Entry):", min_value=1000.0, value=float(win_last), step=5.0)
    preco_stop = st.number_input("Preço de Invalidação (Stop Loss Técnico):", min_value=1000.0, value=float(win_last - 150), step=5.0)
    preco_alvo = st.number_input("Preço de Mitigação (Take Profit 1):", min_value=1000.0, value=float(win_last + 300), step=5.0)

# --- MOTORES DE CÁLCULO DE RISCO ---
# 1. Distâncias em pontos
pts_stop = abs(preco_entrada - preco_stop)
pts_alvo = abs(preco_alvo - preco_entrada)

# 2. Valores financeiros (WIN = R$ 0,20 por ponto por contrato)
financeiro_stop = pts_stop * 0.20 * numero_contratos
financeiro_alvo = pts_alvo * 0.20 * numero_contratos

# 3. Percentual de risco sobre o capital da conta
pct_risco_capital = (financeiro_stop / capital_total) * 100

# 4. Relação Risco vs Recompensa (R:R)
relacao_rr = pts_alvo / pts_stop if pts_stop > 0 else 0.0

# --- EXIBIÇÃO DO PAINEL DE RISCO (OUTPUT VISUAL) ---
with col_fibo:
    st.markdown("**🛡️ Diagnóstico de Risco e Alocação:**")
    
    # Caixa de status baseada no gerenciamento de risco profissional (máximo 2% por trade)
    if pct_risco_capital > 2.5:
        st.markdown(
            f"<div style='background-color:rgba(255,107,107,0.12); padding:15px; border-radius:8px; border:1px solid #ff6b6b; margin-bottom:15px;'>"
            f"❌ <b>ALERTA DE ALTA EXPOSIÇÃO:</b> Este trade arrisca <b>{pct_risco_capital:.2f}%</b> do seu capital. "
            f"Recomendado reduzir o lote ou o stop para ficar abaixo do limite institucional de 2.00%.</div>", 
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='background-color:rgba(0,255,136,0.1); padding:15px; border-radius:8px; border:1px solid #00ff88; margin-bottom:15px;'> "
            f"🟢 <b>RISCO SOBRE CONTROLE:</b> Exposição de <b>{pct_risco_capital:.2f}%</b> do capital. "
            f"Parâmetros dentro do gerenciamento profissional seguro.</div>", 
            unsafe_allow_html=True
        )

    # Painel de KPIs Financeiros
    m1, m2 = st.columns(2)
    m1.metric("Stop Loss Estimado", f"R$ {financeiro_stop:,.2f}", f"{pts_stop:.0f} pts", delta_color="inverse")
    m2.metric("Take Profit Estimado", f"R$ {financeiro_alvo:,.2f}", f"{pts_alvo:.0f} pts")
    
    st.markdown("---")
    st.markdown(f"📐 **Relação Risco vs Recompensa (R:R):** `1 : {relacao_rr:.2f}`")
    
    if relacao_rr >= 2.0:
        st.caption("🎯 **Matemática Matemática Favorável:** Relação maior que 1:2. Setup estatisticamente lucrativo no longo prazo.")
    else:
        st.caption("⚠️ **Atenção:** Relação R:R menor que 1:2. O risco pode não compensar o ganho potencial para este tamanho de stop.")

st.markdown("---")
st.caption("🔒 Módulo matemático auxiliar — Focado estritamente na preservação de capital e proteção da conta de trading.")

```

### `pages/8.3_🔑_Status_Chaves.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/8.3_🔑_Status_Chaves.py
Versão: 2.0 - Otimizado para Governança V2
Objetivo: Painel de auditoria visual de chaves de API, tokens e conectores externos.
"""

import streamlit as st
import os
from pathlib import Path

# Tenta importar as chaves e o KeyManager do seu ecossistema centralizado
from config import FINNHUB_API_KEY

def mascarar_chave(chave_str):
    """Mascara chaves de API para exibição segura em tela (ex: gsk_u...xxxx)."""
    if not chave_str:
        return "❌ NÃO CONFIGURADO (Ausente no .env)"
    if len(chave_str) <= 8:
        return "✅ CONFIGURADO (Chave Curta)"
    return f"✅ ATIVO ({chave_str[:5]}...{chave_str[-4:]})"

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Status de Chaves", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🔑 Status e Validação de Chaves de API</h2>", unsafe_allow_html=True)
st.caption("Central de Auditoria de Conectores Externos e Credenciais de Segurança (V2)")

st.info("🔒 **Segurança Operacional:** Este painel apenas audita a presença e o carregamento dos tokens na memória do servidor. As credenciais confidenciais permanecem mascaradas no terminal.")

st.markdown("---")

# --- CENTRAL DE AUDITORIA: QUADRO DE CONECTORES ---
st.markdown("### 📡 Conectores e Provedores de Dados Ativos")

# 1. Captura as variáveis direto do ambiente operacional (carregadas via config/.env)
groq_key = os.getenv("GROQ_API_KEY")
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat = os.getenv("TELEGRAM_CHAT")
mt5_login = os.getenv("MT5_LOGIN")

# 2. Estruturação da Matriz de Auditoria para exibição limpa
linhas_chaves = [
    {
        "Provedor / API": "Finnhub API",
        "Finalidade": "Performance de ADRs e Cotações Internacionais (Opção A)",
        "Variável do Sistema": "FINNHUB_API_KEY",
        "Status de Conexão": mascarar_chave(FINNHUB_API_KEY)
    },
    {
        "Provedor / API": "Groq Cloud API",
        "Finalidade": "Modelos LMs de Grande Porte (Módulos de Texto/Auditoria)",
        "Variável do Sistema": "GROQ_API_KEY",
        "Status de Conexão": mascarar_chave(groq_key)
    },
    {
        "Provedor / API": "Telegram Bot API",
        "Finalidade": "Notificações Automatizadas de Sinais e Alertas Macro",
        "Variável do Sistema": "TELEGRAM_TOKEN",
        "Status de Conexão": mascarar_chave(telegram_token)
    },
    {
        "Provedor / API": "Telegram Chat Config",
        "Finalidade": "Canal Destino das Mensagens Operacionais",
        "Variável do Sistema": "TELEGRAM_CHAT",
        "Status de Conexão": "✅ CONFIGURADO" if telegram_chat else "❌ NÃO CONFIGURADO"
    },
    {
        "Provedor / API": "MetaTrader 5 Link",
        "Finalidade": "Autenticação e Roteamento de Ordens B3 (Genial)",
        "Variável do Sistema": "MT5_LOGIN",
        "Status de Conexão": f"✅ CONTA ID: {mt5_login}" if mt5_login else "❌ NÃO CONFIGURADO"
    }
]

# Renderização da tabela de auditoria
import pandas as pd
df_chaves = pd.DataFrame(linhas_chaves)
st.dataframe(df_chaves.set_index("Provedor / API"), use_container_width=True)

st.markdown("---")

# --- CHECKLIST DE VERIFICAÇÃO DE INFRAESTRUTURA ---
st.markdown("### 🛠️ Diagnóstico de Prontidão de Produção (Smoke Check)")

falhas = 0
if not FINNHUB_API_KEY: falhas += 1
if not groq_key: falhas += 1
if not mt5_login: falhas += 1

if falhas == 0:
    st.success("🎉 **PRODUÇÃO V2 TOTALMENTE OPERACIONAL:** Todas as chaves e conectores críticos foram validados com sucesso na memória da aplicação. Terminal pronto para operar a abertura do mercado.")
else:
    st.warning(f"⚠️ **PRODUÇÃO PARCIAL:** O terminal identificou `{falhas}` ausência(s) de credenciais no seu arquivo `.env`. Algumas sub-abas operacionais de relatórios podem apresentar comportamento degradado.")

```

### `pages/9.5_📈_Historico_Macro.py`

```python
# -*- coding: utf-8 -*-
"""
Módulo: pages/21_📈_Historico_Macro.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Dashboard analítico de série temporal e histórico macro/operacional do WIN.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go

# Importação da constante de diretório configurada no config.py da V2
from config import HISTORICO_ABERTURAS_DIR

def carregar_json_defensivo(caminho_path):
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Histórico Macro", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>📊 Série Temporal e Histórico Macro Operacional</h2>", unsafe_allow_html=True)
st.caption("Análise estatística retroativa dos fechamentos, ajustes e cenários gravados pelo ecossistema V2")

# --- CENTRAL DE INGESTÃO DO HISTÓRICO FÍSICO V2 ---
if not HISTORICO_ABERTURAS_DIR.exists():
    st.warning("⚠️ Diretório de histórico de aberturas V2 não encontrado no disco local. Aguardando primeiras gravações do pregão.")
    st.stop()

# Varre os arquivos JSON salvos na pasta de histórico
arquivos_historicos = sorted(list(HISTORICO_ABERTURAS_DIR.glob("*.json")))

if not arquivos_historicos:
    st.info("ℹ️ Nenhuma sessão diária imutável foi persistida na pasta Historico_Aberturas/ ainda.")
    st.stop()

# Processamento em lote dos arquivos para montar a série temporal (Dataframe)
linhas_Série = []

for caminho in arquivos_historicos:
    # O nome do arquivo é a data da sessão (ex: 2026-08-30.json)
    data_sessao = caminho.stem
    
    dados_dia = carregar_json_defensivo(caminho)
    atualizacoes = dados_dia.get("atualizacoes", [])
    
    if atualizacoes and isinstance(atualizacoes, list):
        # Captura o último snapshot consolidado do dia (mais atual)
        ultimo_snapshot = atualizacoes[-1]
        
        precos = ultimo_snapshot.get("precos", {})
        distancias = ultimo_snapshot.get("distancias", {})
        cenario = ultimo_snapshot.get("cenario", {})
        contexto = ultimo_snapshot.get("contexto", {})
        
        # Injeta na lista de tuplas para consolidação do Pandas
        linhas_Série.append({
            "Data Sessão": data_sessao,
            "Contrato Principal": ultimo_snapshot.get("metadata", {}).get("contrato_principal", "WIN"),
            "Preço Ajuste B3": precos.get("ajuste"),
            "Último MT5 (Last)": precos.get("last_mt5"),
            "Desvio Ajuste (Pts)": distancias.get("last_vs_ajuste_pts"),
            "VIX (Volatilidade)": contexto.get("vix", {}).get("preco"),
            "Direção Cenário": cenario.get("direcao_provavel", "NEUTRO"),
            "Confiança (%)": cenario.get("confianca_geral", 0.0)
        })

# Converte a lista em Dataframe estruturado do Pandas
df_historico = pd.DataFrame(linhas_Série).sort_values(by="Data Sessão", ascending=False)

# --- RENDERIZAÇÃO DA VISÃO GRÁFICA INTERATIVA (PLOTLY) ---
st.markdown("### 📉 Curva Comparativa: Preço Last vs Ajuste Oficial B3")
st.caption("Monitore o comportamento histórico e o fechamento de spreads institucionais ao longo das sessões")

# Garante que temos dados numéricos para plotar
df_grafico = df_historico.sort_values(by="Data Sessão", ascending=True)

if not df_grafico.empty and df_grafico["Preço Ajuste B3"].notna().any():
    fig = go.Figure()
    
    # Linha do Ajuste
    fig.add_trace(go.Scatter(
        x=df_grafico["Data Sessão"], 
        y=df_grafico["Preço Ajuste B3"],
        mode="lines+markers",
        name="Preço de Ajuste Oficial B3",
        line=dict(color="orange", width=2)
    ))
    
    # Linha do Último Preço do MT5
    fig.add_trace(go.Scatter(
        x=df_grafico["Data Sessão"], 
        y=df_grafico["Último MT5 (Last)"],
        mode="lines+markers",
        name="Último Tick MetaTrader 5 (Last)",
        line=dict(color="#00d4ff", width=2, dash="dash")
    ))
    
    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Aguardando mais pontos históricos para plotar as curvas de tendência.")

st.markdown("---")

# --- CENTRAL DE DADOS: GRADE HISTÓRICA COMPLETA ---
st.markdown("### 📋 Histórico Consolidado de Snapshots da Mesa")
st.caption("Grade analítica contendo todas as variáveis gravadas em background pelo pipeline")

# Formata exibição da tabela Streamlit
st.dataframe(df_historico.set_index("Data Sessão"), use_container_width=True)

st.markdown("---")
st.caption("🔒 Módulo de inteligência histórica ativo — Em conformidade com o ecossistema de armazenamento imutável V2.")

```
