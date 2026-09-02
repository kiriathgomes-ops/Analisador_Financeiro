import json
import os
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(page_title="WINFUT - Cockpit Intraday", layout="wide")

st.title("⚡ WINFUT — Cockpit de Decisão Intraday")
st.caption(f"Última atualização local: {datetime.now().strftime('%H:%M:%S')}")

# ==============================================================================
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[2] if len(ARQUIVO_ATUAL.parents) >= 3 else ARQUIVO_ATUAL.parent

@st.cache_data(ttl=2)
def carregar_dados_absolutos():
    def buscar_json(nome):
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

    decisao_v2, p_v2 = buscar_json("Decisao_V2.json")
    smc_regras, p_smc = buscar_json("AnaliseGraficaSMC_Regras.json")
    if not smc_regras:
        smc_regras, p_smc = buscar_json("Resultado_SMC.json")
        
    unificados, p_unf = buscar_json("DadosAtivosUnificados.json")
    dados_mt5, p_mt5 = buscar_json("Dados_MT5_v2_2.json")
    dados_val, p_val = buscar_json("Dados_Validados.json")

    return decisao_v2, smc_regras, unificados, dados_mt5, dados_val

decisao_v2, smc_regras, unificados, dados_mt5, dados_val = carregar_dados_absolutos()

# ==============================================================================
# FUNÇÃO UNIVERSAL DE BUSCA DE COTAÇÕES E VARIÁVEIS
# ==============================================================================
def extrair_valor_objeto(obj, comp_chave="var"):
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        if comp_chave == "ultimo":
            chaves_val = ["last", "ultimo", "close", "preco", "price", "bid", "ask"]
        else:
            chaves_val = ["var", "variacao", "change", "pct", "pct_change", "v", "value", "variacao_pct"]
            
        for k in chaves_val:
            if k in obj and isinstance(obj[k], (int, float)):
                return float(obj[k])
    return None

def buscar_var(chaves_busca, tipo_campo="var"):
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

sp500_var = buscar_var(["SP500_FUT", "US500", "SP500", "S&P", "US500.F"])
nasdaq_var = buscar_var(["NASDAQ", "US100", "NDX", "NQ1!"])
ewz_var = buscar_var(["EWZ", "EWZ_ETF", "iShares MSCI Brazil"])
dxy_var = buscar_var(["DXY", "USDX", "DX1!"])
wdo_var = buscar_var(["WDO", "WDOU26", "WDO$", "DOLAR_FUT"])
vix_val = buscar_var(["VIX", "VIX_INDEX"], tipo_campo="ultimo")

col1.metric("S&P 500 Futuro", f"{sp500_var:+.2f}%")
col2.metric("Nasdaq 100", f"{nasdaq_var:+.2f}%")
col3.metric("EWZ (B3 em NY)", f"{ewz_var:+.2f}%")
col4.metric("DXY (Dólar Global)", f"{dxy_var:+.2f}%", delta_color="inverse")
col5.metric("WDO (Dólar Futuro)", f"{wdo_var:+.2f}%", delta_color="inverse")
col6.metric("VIX (Medo)", f"{vix_val:.2f}" if vix_val > 0 else "N/A")

st.markdown("---")

# ==============================================================================
# 2. CURVA DE JUROS DI (INCLINAÇÃO E PRESSÃO)
# ==============================================================================
st.subheader("2. Curva de Juros DI (Pressão sobre o Ibovespa)")

col_di1, col_di2, col_di3 = st.columns(3)

di27_var = buscar_var(["DI1F27", "DI_27", "DI1F2027", "DI1F27_rate"])
di29_var = buscar_var(["DI1F29", "DI_29", "DI1F2029", "DI1F29_rate"])
di31_var = buscar_var(["DI1F31", "DI_31", "DI1F2031", "DI1F31_rate"])
di_inc_bps = buscar_var(["DI_INCLINACAO", "DI_SPREAD", "DI_INCLINACAO_BPS"])

if di_inc_bps != 0.0:
    val_di_exibicao = di_inc_bps
else:
    val_di_exibicao = di27_var * 100.0 if abs(di27_var) < 5.0 else di27_var

col_di1.metric("Inclinação DI (Bps)", f"{val_di_exibicao:+.2f} bps", delta_color="inverse")
col_di2.metric("Status da Curva", "Empinamento" if val_di_exibicao > 0 else "Achatamento")
col_di3.metric("Impacto Bolsa", "Pressão Vendedora" if val_di_exibicao > 0 else "Suporte Comprador")

st.markdown("---")

# ==============================================================================
# 3. BLUE CHIPS B3 (PONDERAÇÃO REAL DO IBOVESPA)
# ==============================================================================
st.subheader("3. Peso das Ações Líderes na B3")

col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns(7)

valev3 = buscar_var(["VALE3", "VALE"])
petr4 = buscar_var(["PETR4", "PETR"])
itub4 = buscar_var(["ITUB4", "ITUB"])
bbdc4 = buscar_var(["BBDC4", "BBDC"])
bbas3 = buscar_var(["BBAS3", "BBAS"])
wege3 = buscar_var(["WEGE3", "WEGE"])
abev3 = buscar_var(["ABEV3", "ABEV"])

col_a.metric("VALE3", f"{valev3:+.2f}%")
col_b.metric("PETR4", f"{petr4:+.2f}%")
col_c.metric("ITUB4", f"{itub4:+.2f}%")
col_d.metric("BBDC4", f"{bbdc4:+.2f}%")
col_e.metric("BBAS3", f"{bbas3:+.2f}%")
col_f.metric("WEGE3", f"{wege3:+.2f}%")
col_g.metric("ABEV3", f"{abev3:+.2f}%")

# Definição garantida das variáveis de setor
vies_commodities = (valev3 * 0.55) + (petr4 * 0.45)
vies_bancos = (itub4 * 0.45) + (bbdc4 * 0.30) + (bbas3 * 0.25)

st.caption(f"📊 **Viés de Setores:** Commodities ({vies_commodities:+.2f}%) | Financeiro/Bancos ({vies_bancos:+.2f}%)")

st.markdown("---")

# ==============================================================================
# 4. SINAIS TÉCNICOS SMC / ICT (DO MOTOR DECISÃO V2 E SMC REGRAS)
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
vwap_val = buscar_var(["WIN", "WIN$", "WINV26"], tipo_campo="ultimo")

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