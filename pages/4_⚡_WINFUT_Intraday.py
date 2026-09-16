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
MAPA_TICKERS_ROM5 = {
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
    "WEGE3": ["WEGE3"],
    "ABEV3": ["ABEV3"],
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
    Usa o MAPA_TICKERS_ROM5 para traduzir a chave interna nos tickers originais.
    """
    if not rom5:
        return 0.0

    coletas = rom5.get("coletas")
    if not isinstance(coletas, list):
        return 0.0

    tickers_buscar = MAPA_TICKERS_ROM5.get(chave_interna, [chave_interna])
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
        "WEGE3": {
            "preco": buscar_metrica(["WEGE3", "WEGE"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["WEGE3", "WEGE"], fontes=fontes_dados),
            "chave_rom5": "WEGE3",
        },
        "ABEV3": {
            "preco": buscar_metrica(["ABEV3", "ABEV"], tipo_campo="ultimo", fontes=fontes_dados),
            "var": buscar_metrica(["ABEV3", "ABEV"], fontes=fontes_dados),
            "chave_rom5": "ABEV3",
        },
    }

    col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns(7)
    cols_acoes = [col_a, col_b, col_c, col_d, col_e, col_f, col_g]

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