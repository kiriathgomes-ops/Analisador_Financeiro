# -*- coding: utf-8 -*-
"""
Módulo: pages/7.1_📊_SMC_Regras.py
Versão: 2.0 - Otimizado para Produção V2 (SMC Sem IA)
Objetivo: Renderizar as estruturas de Smart Money (BOS, CHoCH, OB, FVG) calculadas pelo motor.
"""

import streamlit as st
import json
from datetime import datetime

# Importação do caminho centralizado vindo do config.py do seu projeto
from config import FILE_SMC_REGRAS

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - SMC por Regras", layout="wide")

# --- CARGA DOS DADOS SMC V2 ---
dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)

# --- CABEÇALHO DA INTERFACE ---
st.markdown("<h2 style='color:#00d4ff;'>🧠 Smart Money Concepts (SMC) & ICT</h2>", unsafe_allow_html=True)
st.caption(f"Análise algorítmica pura (Sem IA) atualizada em: {dados_smc.get('timestamp', 'N/A')}")

if not dados_smc or "erro" in dados_smc:
    st.error(f"⚠️ Erro ao carregar dados do Motor SMC: {dados_smc.get('erro', 'Arquivo não gerado ou sem candles suficientes')}")
    st.stop()

# --- BLOCOS DE DESTAQUE OPERACIONAL (KPIs) ---
vies = dados_smc.get("bias_direcional", "LATERAL")
confianca = dados_smc.get("confianca_visual", 0)
preco_atual = dados_smc.get("preco_atual", 0.0)

c1, c2, c3 = st.columns(3)

if vies == "ALTA":
    c1.markdown(f"<div style='background-color:rgba(0, 255, 136, 0.1); padding:10px; border-radius:8px; border-left:5px solid #00ff88;'>📊 <b>Viés Estrutural HTF:</b><br><span style='font-size:1.5rem; color:#00ff88; font-weight:bold;'>🐂 BULLISH / ALTA</span></div>", unsafe_allow_html=True)
elif vies == "BAIXA":
    c1.markdown(f"<div style='background-color:rgba(255, 107, 107, 0.1); padding:10px; border-radius:8px; border-left:5px solid #ff6b6b;'>📊 <b>Viés Estrutural HTF:</b><br><span style='font-size:1.5rem; color:#ff6b6b; font-weight:bold;'>🐻 BEARISH / BAIXA</span></div>", unsafe_allow_html=True)
else:
    c1.markdown(f"<div style='background-color:rgba(255, 255, 255, 0.05); padding:10px; border-radius:8px; border-left:5px solid #888;'>📊 <b>Viés Estrutural HTF:</b><br><span style='font-size:1.5rem; color:#ccc; font-weight:bold;'>⚖️ LATERAL / RANGE</span></div>", unsafe_allow_html=True)

c2.metric("Confiança do Setup", f"{confianca}%", delta="Sinal Forte" if confianca >= 70 else "Aguardar Confluência", delta_color="normal" if confianca >= 70 else "off")
c3.metric("Último Preço (B3)", f"{preco_atual:,.0f} pts")

st.markdown("---")

# --- CENTRAL GATILHO: ENTRADAS E LIMITES TÉCNICOS ---
st.markdown("### 🎯 Parâmetros de Execução Gerados pelo Motor")
col_trade, col_status_filtro = st.columns([2, 1])

with col_trade:
    entrada = dados_smc.get("entrada_sugerida")
    stop = dados_smc.get("stop_sugerido")
    alvos = dados_smc.get("alvos", [])
    
    if entrada and stop:
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.markdown(f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>🟢 <b>ORDEM BUY/SELL STOP:</b><br><span style='font-size:1.4rem; font-weight:bold; color:#00d4ff;'>{entrada:,.0f}</span></div>", unsafe_allow_html=True)
        t_col2.markdown(f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>🛑 <b>STOP LOSS TÉCNICO:</b><br><span style='font-size:1.4rem; font-weight:bold; color:#ff6b6b;'>{stop:,.0f}</span></div>", unsafe_allow_html=True)
        
        alvos_txt = " | ".join([f"{x:,.0f}" for x in alvos]) if alvos else "Aguardando Alvo por Liquidez"
        t_col3.markdown(f"<div style='background-color:#161b24; padding:15px; border-radius:8px; text-align:center;'>🏁 <b>ALVOS DE MITIGAÇÃO:</b><br><span style='font-size:1.1rem; font-weight:bold; color:#00ff88;'>{alvos_txt}</span></div>", unsafe_allow_html=True)
    else:
        st.info("⚖️ **Modo de Observação Ativo:** O preço atual não mitigou nenhum Order Block relevante com confirmação de volume. Aguardando gatilho institucional.")

with col_status_filtro:
    meta = dados_smc.get("metadados", {})
    vol_filtro = meta.get("filtro_volume_aplicado", False)
    
    st.markdown("**Status das Validações:**")
    st.markdown(f"• Filtro de Volume Institucional: {'✅ **ATIVO**' if vol_filtro else '❌ Inativo'}")
    st.markdown(f"• Candles Analisados (Lookback): `{meta.get('n_candles', 0)}` bars")
    st.markdown(f"• Estruturas Históricas Mapeadas: `{meta.get('n_swings', 0)}` swings")

st.markdown("---")

# --- COLUNAS DE ESTRUTURAS INSTITUCIONAIS ---
col_ob, col_fvg, col_liq = st.columns(3)

with col_ob:
    st.markdown("#### 🏢 Order Blocks (Zonas de Defesa)")
    obs = dados_smc.get("order_blocks", [])
    if obs:
        for ob in obs:
            cor = "#00ff88" if ob["tipo"] == "COMPRA" else "#ff6b6b"
            st.markdown(f"""
            <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                🔹 <b>OB de {ob['tipo']}</b><br>
                • Preço Referência: <b>{ob['preco']:,.0f}</b><br>
                • Cobertura: {ob['low']:,.0f} - {ob['high']:,.0f}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Nenhum Order Block ativo detectado com os filtros de volume atuais.")

with col_fvg:
    st.markdown("#### 🕳️ Fair Value Gaps (Desequilíbrio)")
    fvgs = dados_smc.get("fair_value_gaps", [])
    if fvgs:
        for fvg in fvgs:
            cor = "#00ff88" if fvg["tipo"] == "COMPRA" else "#ff6b6b"
            st.markdown(f"""
            <div style='background-color:#161b24; padding:10px; border-radius:6px; margin-bottom:8px; border-left:4px solid {cor};'>
                🔸 <b>FVG Ineficiente - {fvg['tipo']}</b><br>
                • Faixa: {fvg['inferior']:,.0f} ➔ {fvg['superior']:,.0f}<br>
                • Preenchido: {'⚠️ Sim' if fvg.get('preenchido') else '🟢 Aberto / Ímã de Preço'}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("Preço consolidado de forma eficiente. Nenhum FVG em aberto.")

with col_liq:
    st.markdown("#### 🎯 Alvos de Liquidez Institucional")
    liq = dados_smc.get("liquidez", {})
    bsl = liq.get("bsl", [])
    ssl = liq.get("ssl", [])
    
    st.markdown("**🌐 BSL (Buy Side Liquidity - Topos)**")
    if bsl:
        for p in bsl:
            st.markdown(f"• Preço: `{p:,.0f}` ➔ *Equal Highs / Stop de Compradores*")
    else:
        st.caption("Nenhuma piscina de liquidez compradora mapeada acima.")
        
    st.markdown("<br>**🩸 SSL (Sell Side Liquidity - Fundos)**", unsafe_allow_html=True)
    if ssl:
        for p in ssl:
            st.markdown(f"• Preço: `{p:,.0f}` ➔ *Equal Lows / Stop de Vendedores*")
    else:
        st.caption("Nenhuma piscina de liquidez vendedora mapeada abaixo.")

st.markdown("---")

# --- SEÇÃO 4: CENÁRIOS E MAPA DO FLUXO OPERACIONAL ---
st.markdown("### 🗺️ Cenários Operacionais Mapeados (Zonas de Interesse)")
cenarios = dados_smc.get("zonas_de_interesse_e_cenarios", [])
if cenarios:
    for i, cenario in enumerate(cenarios, start=1):
        st.markdown(f"**{i}.** {cenario}")
else:
    st.caption("Aguardando consolidação do range para desenhar os mapas de projeção de cenários.")
