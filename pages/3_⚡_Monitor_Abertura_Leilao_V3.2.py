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

from config import FILE_MT5_V2, FILE_UNIFICADO, FILE_DECISAO_V2, FILE_METRICAS, MAPEAMENTO_ADR_B3

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
MAPA_TICKERS_ROM5 = {
    "EWZ": "AMEX:EWZ",
    "VIX": "TVC:VIX",
    "CRUDE_OIL": "NYMEX:CL1!",
    "IRON_ORE_2M": "SGX:FEF2!",
    "IRON_ORE": "SGX:FEF1!",
    "VALE_ADR": "NYSE:VALE",
    "PETR_ADR": "NYSE:PBR",
    "ITUB_ADR": "NYSE:ITUB",
    "BBAS_ADR": "OTC:BDORY",
    "BBD_ADR": "NYSE:BBD",
    "B3_ADR": "OTC:BOLSY",
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBAS3": "BBAS3",
    "BBDC4": "BBDC4",
    "B3SA3": "B3SA3",
}

# ✅ Direto: Ação B3 → chave do ADR no unificado/rom-5
MAPA_B3_PARA_ADR = {
    "VALE3": "VALE_ADR",
    "PETR4": "PETR_ADR",
    "ITUB4": "ITUB_ADR",
    "BBAS3": "BBAS_ADR",
    "BBDC4": "BBD_ADR",
    "B3SA3": "B3_ADR",
}

ADRS_COMPOSTO = ["BBD_ADR", "ITUB_ADR", "PETR_ADR", "VALE_ADR", "BBAS_ADR", "B3_ADR"]


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
    ticker = MAPA_TICKERS_ROM5.get(chave_interna, chave_interna)
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