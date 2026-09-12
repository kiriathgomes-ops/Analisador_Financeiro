# -*- coding: utf-8 -*-
"""
Módulo: pages/3.2_⚡_Monitor_Abertura_Leilao_V3.2.py
Versão: 3.4.0 - Unificada (Monitor de Leilão + Termômetro de Fluxo & ADRs com Mini Velocímetros)
Objetivo: Monitorar formação de preço, leilão, fluxo institucional externo e spreads de arbitragem B3 vs ADRs
"""

import logging
from pathlib import Path
import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

# Importações de caminhos padronizados do config.py da V2
from config import FILE_MT5_V2, FILE_UNIFICADO, FILE_DECISAO_V2, FILE_METRICAS, MAPEAMENTO_ADR_B3

# Configuração de Logging para auditoria em produção
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página Streamlit (DEVE SER A PRIMEIRA CHAMADA ST)
st.set_page_config(
    page_title="Quant Terminal - Monitor de Leilão & Fluxo",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==============================================================================
# MINI VELOCÍMETRO (centro em zero, estilo flat design)
# ==============================================================================
def mini_velocimetro(valor, label: str, preco_fmt: str = "", inverter: bool = False) -> None:
    """
    Mini velocímetro compacto com centro em zero.

    - Valor positivo → ponteiro à direita, cor verde
    - Valor negativo → ponteiro à esquerda, cor vermelha
    - Valor zero    → ponteiro ao centro (topo), cor amarela
    - Escala fixa: ±10% (satura além disso).

    Parâmetro `inverter`:
    - True  → inverte a cor/lado (para ativos onde subir é ruim: VIX, DXY, juros)
    - False → comportamento literal (positivo = verde)
    """
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
            cor = "#00cc44"   # verde
        elif real_cor < -0.05:
            cor = "#ff4b4b"   # vermelho
        else:
            cor = "#ffa500"   # amarelo (neutro)
        texto_valor = f"{real_exibicao:+.2f}%"

    # -10% → -90° | 0% → 0° (topo) | +10% → +90°
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
            margin-top: 1px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
        }}
        .mini-sub {{
            font-size: 10px;
            color: #8b949e;
            text-align: center;
            margin-top: -1px;
        }}
    </style>
    </head>
    <body>
        <div class="mini-wrap">
            <div class="mini-label">{label}</div>
            <div class="mini-gauge">
                <div class="mini-arc"></div>
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 58">
                    <path d="M 4 0 L 5.5 52 L 2.5 52 Z" fill="#ffffff"/>
                </svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-sub">{preco_fmt}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=135, scrolling=False)


@st.cache_data(ttl=5)  # Cache leve para evitar I/O excessivo em disco a cada rerun do Streamlit
def carregar_json_defensivo(caminho: Path) -> dict:
    """
    Carrega arquivo JSON de forma defensiva com tratamento de exceções específico
    e logging de erros para diagnóstico em produção.
    """
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


# --- CARGA DE DADOS V2 ---
dados_mt5 = carregar_json_defensivo(FILE_MT5_V2)
dados_unificados = carregar_json_defensivo(FILE_UNIFICADO)
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
dados_metricas = carregar_json_defensivo(FILE_METRICAS)

# Cabeçalho Principal
st.markdown("<h2 style='color:#00d4ff;'>⚡ Monitor de Abertura e Leilão B3</h2>", unsafe_allow_html=True)
timestamp_snapshot = dados_mt5.get('timestamp', 'N/A')
st.caption(f"Último snapshot capturado pelo pipeline: `{timestamp_snapshot}`")

# --- SEÇÃO 0: TERMÔMETRO ESTATÍSTICO DE FLUXO ESTRANGEIRO (COM MINI VELOCÍMETROS) ---
st.markdown("### 🏦 Termômetro Estatístico de Fluxo Estrangeiro")
st.caption("Ponteiro centrado em zero · 🟢 positivo = favorável ao risco · 🔴 negativo = aversão ao risco")

ind_compostos = dados_metricas.get("indicadores_compostos", {})
ind_adrs = ind_compostos.get("indicador_adrs_brasileiras")
ind_externo = ind_compostos.get("indicador_mercado_externo")

# EWZ (ETF Brasil em NY)
ewz_pct = dados_metricas.get("performance_relativa", {}).get("ewz_change_pct", 0.0)

c1, c2, c3 = st.columns(3)

with c1:
    # ADRs — literal (positivo = fluxo comprador)
    mini_velocimetro(
        ind_adrs,
        "🇧🇷 Indicador Composto ADRs BR",
        f"{ind_adrs:+.2f}%" if ind_adrs is not None else "",
        inverter=False,
    )
    if ind_adrs is not None:
        if ind_adrs > 0.5:
            st.caption("📈 **Fluxo Comprador** — ADRs sinalizando entrada de capital")
        elif ind_adrs < -0.5:
            st.caption("📉 **Fluxo Vendedor** — ADRs sinalizando saída de capital")
        else:
            st.caption("⚖️ **Estável** — sem direção clara")

with c2:
    # Mercado Externo — literal (positivo = favorável ao risco)
    mini_velocimetro(
        ind_externo,
        "🌍 Indicador de Mercado Externo",
        f"{ind_externo:+.2f}%" if ind_externo is not None else "",
        inverter=False,
    )
    if ind_externo is not None:
        if ind_externo > 0.5:
            st.caption("✅ **Favorável ao Risco** — VIX/Petróleo/Minério colaborando")
        elif ind_externo < -0.5:
            st.caption("⚠️ **Aversão ao Risco** — pressão externa negativa")
        else:
            st.caption("⚖️ **Neutro** — sem pressão clara")

with c3:
    # EWZ — literal (positivo = fundo Brasil em NY subindo)
    mini_velocimetro(
        ewz_pct,
        "🇺🇸 EWZ (ETF Brasil em NY)",
        f"{ewz_pct:+.2f}%" if ewz_pct is not None else "",
        inverter=False,
    )
    if ewz_pct is not None:
        if ewz_pct > 0.5:
            st.caption("🟢 **Brasil atrativo** — fundo NY comprando B3")
        elif ewz_pct < -0.5:
            st.caption("🔴 **Brasil rejeitado** — fundo NY vendendo B3")
        else:
            st.caption("⚖️ **Neutro** — fluxo equilibrado")

st.markdown("---")

# --- SEÇÃO 1: STATUS DO MINI ÍNDICE (WIN) E MINI DÓLAR (WDO) ---
st.markdown("### 📊 Status dos Contratos Vigentes")

ativos_mt5 = dados_mt5.get("ativos", {})
win_data = ativos_mt5.get("WIN", {})
wdo_data = ativos_mt5.get("WDO", {})

col_win, col_wdo = st.columns(2)


def renderizar_cartao_futuro(titulo: str, data_ativo: dict, eh_dolar: bool = False):
    """Renderiza de forma modular e segura o card de WIN ou WDO."""
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

    # Formatação condicional baseada no tipo de ativo (Índice vs Dólar)
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
        st.metric(
            "Preço Teórico do Leilão",
            f"{preco_teorico:{fmt_str}}{sufixo}",
            delta=delta_str
        )
    else:
        st.metric("Último Preço (Mercado Aberto/Ajustado)", f"{last_price:{fmt_str}}{sufixo}")
        st.caption("💡 Preço teórico indisponível fora do horário de leilão (08:50 - 09:00).")


with col_win:
    renderizar_cartao_futuro("🔹 Mini Índice Future", win_data, eh_dolar=False)

with col_wdo:
    renderizar_cartao_futuro("💵 Mini Dólar Future", wdo_data, eh_dolar=True)

st.markdown("---")

# --- SEÇÃO 2: MONITOR DE ARBITRAGEM DE AÇÕES (09:45 - 10:00) ---
st.markdown("### 🏦 Leilão do Mercado à Vista vs ADRs (Arbitragem)")
st.caption("Análise de descasamento e spread para abertura das ações às 10:00h")

acoes_foco = ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"]
ativos_unificados = dados_unificados.get("ativos", {})

# Mapeamento exato estruturado com base no DadosAtivosUnificados.json
MAPEAMENTO_ADRS = {
    "VALE3": "VALE_ADR",
    "PETR4": "PETR_ADR",
    "ITUB4": "ITUB_ADR",
    "BBAS3": "BBAS_ADR",
    "BBDC4": "BBD_ADR",
    "B3SA3": "B3_ADR"
}

linhas_tabela = []
for acao in acoes_foco:
    if acao in ativos_unificados:
        dados_acao = ativos_unificados[acao]

        # Puxa a chave exata do ADR correspondente via dicionário de de-para
        ticker_adr = MAPEAMENTO_ADRS.get(acao, f"{acao}_ADR")

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
            "Sinal Arbitragem": sinal
        })

if linhas_tabela:
    df_arbitragem = pd.DataFrame(linhas_tabela)
    st.dataframe(df_arbitragem, use_container_width=True, hide_index=True)
else:
    st.info("ℹ️ Aguardando atualização do arquivo de ativos unificados para calcular spreads de arbitragem.")

# --- SEÇÃO 2B: MINI VELOCÍMETROS DE ARBITRAGEM (SPREAD NY vs B3) ---
if linhas_tabela:
    st.markdown("##### 📊 Spreads por Ação (NY − B3)")
    st.caption("Ponteiro centrado em zero · 🟢 positivo = B3 atrasada (compra) · 🔴 negativo = B3 esticada (venda)")

    cols_arb = st.columns(6)
    for idx, linha in enumerate(linhas_tabela):
        with cols_arb[idx]:
            # Converte string formatada de volta para float
            spread_str = linha["Spread (NY - B3)"].replace("%", "").replace("+", "")
            try:
                spread_val = float(spread_str)
            except (ValueError, TypeError):
                spread_val = 0.0

            mini_velocimetro(
                spread_val,
                linha["Ativo B3"],
                f"{spread_val:+.2f}%",
                inverter=False,
            )

# --- SEÇÃO 3: TRAVA DE RISCO MACRO V2 ---
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

# --- SEÇÃO 4: NOTA DE TRADING ---
st.markdown("---")
st.markdown("💡 **Nota de Trading:** Grandes descolamentos (maiores que ±0.50%) em papéis de alta liquidez como VALE3 e PETR4 costumam ser fechados rapidamente por robôs de arbitragem institucionais de alta frequência nas primeiras horas do pregão à vista brasileiro.")