# -*- coding: utf-8 -*-
"""
Módulo: pages/5.1_WINFUT_Intraday.py
Versão: 2.7 - Inclinação DI limpa (Valor em cima, Impacto operacional embaixo com cor dinâmica)
Objetivo: Cockpit de Decisão Intraday para monitoramento de ativos direcionais do WIN.
"""

import json
from datetime import datetime
from pathlib import Path
import streamlit as st
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
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[2] if len(ARQUIVO_ATUAL.parents) >= 3 else ARQUIVO_ATUAL.parent

@st.cache_data(ttl=2)
def carregar_dados_absolutos() -> tuple:
    """Carrega de forma defensiva os arquivos JSON do pipeline quant."""
    def buscar_json(nome: str) -> tuple[dict, str | None]:
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
def extrair_valor_objeto(obj: any, comp_chave: str = "var") -> float | None:
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

def buscar_metrica(chaves_busca: list[str], tipo_campo: str = "var") -> float:
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
# 1. MOTORES MACRO GLOBAIS E CÂMBIO
# ==============================================================================
st.subheader("1. Motores Macro e Correlações em Tempo Real")

col1, col2, col3, col4, col5, col6 = st.columns(6)

ativos_macro = {
    "S&P 500 Futuro": (buscar_metrica(["SP500_FUT", "US500", "SP500", "S&P"], tipo_campo="ultimo"), buscar_metrica(["SP500_FUT", "US500", "SP500", "S&P"])),
    "Nasdaq 100": (buscar_metrica(["NASDAQ", "US100", "NDX", "NQ1!"], tipo_campo="ultimo"), buscar_metrica(["NASDAQ", "US100", "NDX", "NQ1!"])),
    "EWZ (B3 em NY)": (buscar_metrica(["EWZ", "EWZ_ETF"], tipo_campo="ultimo"), buscar_metrica(["EWZ", "EWZ_ETF"])),
    "DXY (Dólar Global)": (buscar_metrica(["DXY", "USDX", "DX1!"], tipo_campo="ultimo"), buscar_metrica(["DXY", "USDX", "DX1!"])),
    "WDO (Dólar Futuro)": (buscar_metrica(["WDO", "WDOU26", "WDO$"], tipo_campo="ultimo"), buscar_metrica(["WDO", "WDOU26", "WDO$"])),
    "VIX (Medo)": (buscar_metrica(["VIX", "VIX_INDEX"], tipo_campo="ultimo"), buscar_metrica(["VIX", "VIX_INDEX"]))
}

for i, (label, (preco, var)) in enumerate(ativos_macro.items()):
    col = [col1, col2, col3, col4, col5, col6][i]
    fmt_preco = f"{preco:,.2f}" if preco < 1000 else f"{preco:,.0f}"
    if label.startswith("DXY") or label.startswith("VIX"):
        fmt_preco = f"{preco:,.2f}"
    
    delta_color_val = "inverse" if "DXY" in label or "WDO" in label or "VIX" in label else "normal"
    col.metric(label, fmt_preco, delta=f"{var:+.2f}%", delta_color=delta_color_val)

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

col_di1.metric(
    "Inclinação DI (29 vs 27)", 
    f"{val_di_exibicao:+.1f} bps", 
    delta=impacto_texto, 
    delta_color="inverse"
)
col_di2.metric("Status da Curva", status_curva)
col_di3.metric("Impacto Bolsa", impacto_texto)

st.markdown("---")

# ==============================================================================
# 3. BLUE CHIPS B3 (PONDERAÇÃO REAL DO IBOVESPA)
# ==============================================================================
st.subheader("3. Peso das Ações Líderes na B3")

col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns(7)

acoes_b3 = {
    "VALE3": (buscar_metrica(["VALE3", "VALE"], tipo_campo="ultimo"), buscar_metrica(["VALE3", "VALE"])),
    "PETR4": (buscar_metrica(["PETR4", "PETR"], tipo_campo="ultimo"), buscar_metrica(["PETR4", "PETR"])),
    "ITUB4": (buscar_metrica(["ITUB4", "ITUB"], tipo_campo="ultimo"), buscar_metrica(["ITUB4", "ITUB"])),
    "BBDC4": (buscar_metrica(["BBDC4", "BBDC"], tipo_campo="ultimo"), buscar_metrica(["BBDC4", "BBDC"])),
    "BBAS3": (buscar_metrica(["BBAS3", "BBAS"], tipo_campo="ultimo"), buscar_metrica(["BBAS3", "BBAS"])),
    "WEGE3": (buscar_metrica(["WEGE3", "WEGE"], tipo_campo="ultimo"), buscar_metrica(["WEGE3", "WEGE"])),
    "ABEV3": (buscar_metrica(["ABEV3", "ABEV"], tipo_campo="ultimo"), buscar_metrica(["ABEV3", "ABEV"]))
}

valev3 = acoes_b3["VALE3"][1]
petr4 = acoes_b3["PETR4"][1]
itub4 = acoes_b3["ITUB4"][1]
bbdc4 = acoes_b3["BBDC4"][1]
bbas3 = acoes_b3["BBAS3"][1]

for i, (ativo, (preco, var)) in enumerate(acoes_b3.items()):
    col = [col_a, col_b, col_c, col_d, col_e, col_f, col_g][i]
    col.metric(ativo, f"R$ {preco:,.2f}" if preco > 0 else "N/A", delta=f"{var:+.2f}%", delta_color="normal" if var != 0 else "off")

vies_commodities = (valev3 * 0.55) + (petr4 * 0.45)
vies_bancos = (itub4 * 0.45) + (bbdc4 * 0.30) + (bbas3 * 0.25)

st.caption(f"📊 **Viés de Setores:** Commodities (`{vies_commodities:+.2f}%`) | Financeiro/Bancos (`{vies_bancos:+.2f}%`)")

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
# 5. SCORE INTRADAY UNIFICADO
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

st.markdown(f"### Score de Viés Intraday: **{score:+.1f}**")

if score >= 4.0:
    st.success("🟢 **FORTE VIÉS COMPRADOR:** Alinhamento de S&P500, EWZ e Ações Líderes a favor da alta.")
elif score <= -4.0:
    st.error("🔴 **FORTE VIÉS VENDEDOR:** Pressão de Juros/Dólar e queda generalizada nas Blue Chips.")
else:
    st.warning("🟡 **VIÉS NEUTRO / CONSOLIDADO:** Sinais divergentes. Priorize trades em regiões extremas de Liquidez/FVG.")