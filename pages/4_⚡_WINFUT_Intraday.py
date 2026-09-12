# -*- coding: utf-8 -*-
"""
Módulo: pages/5.1_WINFUT_Intraday.py
Versão: 3.0 - Cockpit com Mini Velocímetros
Objetivo: Cockpit de Decisão Intraday para monitoramento de ativos direcionais do WIN.
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
st.caption(f"Última atualização local: `{datetime.now().strftime('%H:%M:%S')}`")


# ==============================================================================
# MINI VELOCÍMETRO (centro em zero, estilo flat design)
# ==============================================================================
def mini_velocimetro(valor, label: str, preco_fmt: str = "", inverter: bool = False) -> None:
    """
    Mini velocímetro compacto com centro em zero.
    - Positivo → ponteiro à direita, cor verde
    - Negativo → ponteiro à esquerda, cor vermelha
    - Neutro   → ponteiro ao centro, cor amarela
    - Escala fixa: ±10% (satura além disso)
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
            cor = "#00cc44"
        elif real_cor < -0.05:
            cor = "#ff4b4b"
        else:
            cor = "#ffa500"
        texto_valor = f"{real_exibicao:+.2f}%"

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
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 52">
                    <path d="M 4 0 L 5.5 46 L 2.5 46 Z" fill="#ffffff"/>
                </svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-sub">{preco_fmt}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=125, scrolling=False)


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

    return decisao_v2, smc_regras, unificados, dados_mt5, dados_val


decisao_v2, smc_regras, unificados, dados_mt5, dados_val = carregar_dados_absolutos()


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


def buscar_metrica(chaves_busca: list, tipo_campo: str = "var") -> float:
    """Busca o valor (preço ou variação) navegando pelas fontes de dados."""
    fontes = [unificados, dados_val, dados_mt5, decisao_v2]

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


# ==============================================================================
# 1. MOTORES MACRO GLOBAIS E CÂMBIO (COM MINI VELOCÍMETROS)
# ==============================================================================
st.subheader("1. Motores Macro e Correlações em Tempo Real")
st.caption("Ponteiro centrado em zero · ⚠️ DXY/WDO/VIX invertidos (subir = risco)")

ativos_macro = {
    "S&P 500 Futuro": (buscar_metrica(["SP500_FUT", "US500", "SP500", "S&P"], tipo_campo="ultimo"), buscar_metrica(["SP500_FUT", "US500", "SP500", "S&P"]), False),
    "Nasdaq 100": (buscar_metrica(["NASDAQ", "US100", "NDX", "NQ1!"], tipo_campo="ultimo"), buscar_metrica(["NASDAQ", "US100", "NDX", "NQ1!"]), False),
    "EWZ (B3 em NY)": (buscar_metrica(["EWZ", "EWZ_ETF"], tipo_campo="ultimo"), buscar_metrica(["EWZ", "EWZ_ETF"]), False),
    "DXY (Dólar Global)": (buscar_metrica(["DXY", "USDX", "DX1!"], tipo_campo="ultimo"), buscar_metrica(["DXY", "USDX", "DX1!"]), True),
    "WDO (Dólar Futuro)": (buscar_metrica(["WDO", "WDOU26", "WDO$"], tipo_campo="ultimo"), buscar_metrica(["WDO", "WDOU26", "WDO$"]), True),
    "VIX (Medo)": (buscar_metrica(["VIX", "VIX_INDEX"], tipo_campo="ultimo"), buscar_metrica(["VIX", "VIX_INDEX"]), True)
}

col1, col2, col3, col4, col5, col6 = st.columns(6)
cols_macro = [col1, col2, col3, col4, col5, col6]

for i, (label, (preco, var, inverter)) in enumerate(ativos_macro.items()):
    fmt_preco = f"{preco:,.2f}" if preco < 1000 else f"{preco:,.0f}"
    with cols_macro[i]:
        mini_velocimetro(var, label, fmt_preco, inverter=inverter)

st.markdown("---")

# ==============================================================================
# 2. CURVA DE JUROS DI (INCLINAÇÃO E PRESSÃO)
# ==============================================================================
st.subheader("2. Curva de Juros DI (Pressão sobre o Ibovespa)")

col_di1, col_di2, col_di3 = st.columns(3)

di27_taxa = unificados.get("ativos", {}).get("DI1_2027", {}).get("preco", 13.565)
di29_taxa = unificados.get("ativos", {}).get("DI1_2029", {}).get("preco", 13.93)
val_di_exibicao = (di29_taxa - di27_taxa) * 100.0

# Regra de impacto e cor: Empinamento (> 0) é Pressão Vendedora (Ruim -> Vermelho via inverse)
impacto_texto = "Pressão Vendedora" if val_di_exibicao > 0 else "Suporte Comprador"
status_curva = "Empinamento (Step-up)" if val_di_exibicao > 0 else "Achatamento"

with col_di1:
    # Inclinação DI usa escala diferente (bps, não %) — normaliza para escala visual
    # Convertendo bps para escala de velocímetro (10 bps ≈ 1% visual)
    inclinacao_normalizada = val_di_exibicao / 10.0  # 10 bps = 1.0 (dentro da escala)
    mini_velocimetro(
        inclinacao_normalizada,
        "📈 Inclinação DI (29 vs 27)",
        f"{val_di_exibicao:+.1f} bps",
        inverter=True,  # empinamento (subir) = ruim
    )

with col_di2:
    st.metric("Status da Curva", status_curva)

with col_di3:
    st.metric("Impacto Bolsa", impacto_texto)

st.markdown("---")

# ==============================================================================
# 3. BLUE CHIPS B3 (PONDERAÇÃO REAL DO IBOVESPA) — COM MINI VELOCÍMETROS
# ==============================================================================
st.subheader("3. Peso das Ações Líderes na B3")
st.caption("Variação diária das 7 principais blue chips · 🟢 positivo = compra · 🔴 negativo = venda")

acoes_b3 = {
    "VALE3": (buscar_metrica(["VALE3", "VALE"], tipo_campo="ultimo"), buscar_metrica(["VALE3", "VALE"])),
    "PETR4": (buscar_metrica(["PETR4", "PETR"], tipo_campo="ultimo"), buscar_metrica(["PETR4", "PETR"])),
    "ITUB4": (buscar_metrica(["ITUB4", "ITUB"], tipo_campo="ultimo"), buscar_metrica(["ITUB4", "ITUB"])),
    "BBDC4": (buscar_metrica(["BBDC4", "BBDC"], tipo_campo="ultimo"), buscar_metrica(["BBDC4", "BBDC"])),
    "BBAS3": (buscar_metrica(["BBAS3", "BBAS"], tipo_campo="ultimo"), buscar_metrica(["BBAS3", "BBAS"])),
    "WEGE3": (buscar_metrica(["WEGE3", "WEGE"], tipo_campo="ultimo"), buscar_metrica(["WEGE3", "WEGE"])),
    "ABEV3": (buscar_metrica(["ABEV3", "ABEV"], tipo_campo="ultimo"), buscar_metrica(["ABEV3", "ABEV"]))
}

col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns(7)
cols_acoes = [col_a, col_b, col_c, col_d, col_e, col_f, col_g]

for i, (ativo, (preco, var)) in enumerate(acoes_b3.items()):
    with cols_acoes[i]:
        mini_velocimetro(var, ativo, f"R$ {preco:,.2f}" if preco > 0 else "—", inverter=False)

valev3 = acoes_b3["VALE3"][1]
petr4 = acoes_b3["PETR4"][1]
itub4 = acoes_b3["ITUB4"][1]
bbdc4 = acoes_b3["BBDC4"][1]
bbas3 = acoes_b3["BBAS3"][1]

vies_commodities = (valev3 * 0.55) + (petr4 * 0.45)
vies_bancos = (itub4 * 0.45) + (bbdc4 * 0.30) + (bbas3 * 0.25)

st.caption(f"📊 **Viés de Setores:** Commodities (`{vies_commodities:+.2f}%`) | Financeiro/Bancos (`{vies_bancos:+.2f}%`)")

# ---------- Mini velocímetros dos setores agregados ----------
st.markdown("##### 🏭 Viés Setorial Consolidado")
col_set1, col_set2 = st.columns(2)

with col_set1:
    mini_velocimetro(
        vies_commodities,
        "⛏️ Commodities (Vale + Petro)",
        f"{vies_commodities:+.2f}%",
        inverter=False,
    )

with col_set2:
    mini_velocimetro(
        vies_bancos,
        "🏦 Financeiro (Itaú + Bradesco + BB)",
        f"{vies_bancos:+.2f}%",
        inverter=False,
    )

st.markdown("---")

# ==============================================================================
# 4. SINAIS TÉCNICOS SMC / ICT (sem velocímetros — é texto puro)
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
vwap_val = buscar_metrica(["WIN", "WIN$", "WINV26"], tipo_campo="ultimo")

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
# 5. SCORE INTRADAY UNIFICADO — COM MINI VELOCÍMETRO GRANDE
# ==============================================================================
st.subheader("5. Score Operacional em Tempo Real")

sp500_var = ativos_macro["S&P 500 Futuro"][1]
ewz_var = ativos_macro["EWZ (B3 em NY)"][1]
wdo_var = ativos_macro["WDO (Dólar Futuro)"][1]

score = 0.0

if sp500_var > 0.3: score += 1.5
elif sp500_var < -0.3: score -= 1.5

if ewz_var > 0.5: score += 1.5
elif ewz_var < -0.5: score -= 1.5

if wdo_var < -0.2: score += 1.0
elif wdo_var > 0.2: score -= 1.0

if val_di_exibicao < -0.2: score += 1.5
elif val_di_exibicao > 0.2: score -= 1.5

if vies_bancos > 0.3: score += 2.0
elif vies_bancos < -0.3: score -= 2.0

if vies_commodities > 0.3: score += 1.5
elif vies_commodities < -0.3: score -= 1.5

# ---------- Layout em 3 colunas: velocímetro grande à esquerda + status ----------
col_score_vis, col_score_txt = st.columns([1, 2])

with col_score_vis:
    # Score varia de -10 a +10 → encaixa direto na escala do mini velocímetro
    mini_velocimetro(
        score,
        "🎯 SCORE INTRADAY",
        f"{score:+.1f} pontos",
        inverter=False,
    )

with col_score_txt:
    st.markdown(f"### Score de Viés Intraday: **{score:+.1f}**")

    if score >= 4.0:
        st.success("🟢 **FORTE VIÉS COMPRADOR:** Alinhamento de S&P500, EWZ e Ações Líderes a favor da alta.")
    elif score <= -4.0:
        st.error("🔴 **FORTE VIÉS VENDEDOR:** Pressão de Juros/Dólar e queda generalizada nas Blue Chips.")
    else:
        st.warning("🟡 **VIÉS NEUTRO / CONSOLIDADO:** Sinais divergentes. Priorize trades em regiões extremas de Liquidez/FVG.")