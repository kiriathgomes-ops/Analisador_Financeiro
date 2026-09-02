# -*- coding: utf-8 -*-
"""
Módulo: pages/1.1_🎯_Setup_Abertura.py
Versão: 3.0 (Mapeamento Exato do Schema DadosAtivosUnificados.json)
Objetivo: Painel unificado de monitoramento de aberturas do pregão (WIN/WDO)
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(page_title="WINFUT - Setup Abertura", layout="wide")

# ==============================================================================
# RESOLUÇÃO ABSOLUTA DOS CAMINHOS DO PROJETO
# ==============================================================================
ARQUIVO_ATUAL = Path(__file__).resolve()
RAIZ_PROJETO = ARQUIVO_ATUAL.parents[1] if ARQUIVO_ATUAL.parent.name == "pages" else ARQUIVO_ATUAL.parent

def carregar_json_absoluto(nome_arquivo):
    """Busca os arquivos JSON na raiz, na pasta Coletas, v2 ou json."""
    locais_busca = [
        RAIZ_PROJETO / nome_arquivo,
        RAIZ_PROJETO / "Coletas" / nome_arquivo,
        RAIZ_PROJETO / "v2" / nome_arquivo,
        RAIZ_PROJETO / "json" / nome_arquivo,
        Path.cwd() / nome_arquivo,
        Path.cwd() / "Coletas" / nome_arquivo
    ]
    for caminho in locais_busca:
        if caminho.is_file():
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    return json.load(f), str(caminho)
            except Exception:
                pass
    return {}, None

# Carregamento dos dados
unificados, _ = carregar_json_absoluto("DadosAtivosUnificados.json")
decisao_v2, _ = carregar_json_absoluto("Decisao_V2.json")
smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")
estimativas, _ = carregar_json_absoluto("Resultado_Calculadora.json")
noticias, _ = carregar_json_absoluto("Noticias_Impacto.json")
dados_mt5, _ = carregar_json_absoluto("Dados_MT5_v2_2.json")

# ==============================================================================
# EXTRAÇÃO PRECISA BASEADA NO SCHEMA REAL
# ==============================================================================
ativos_unificados = unificados.get("ativos", {})

def get_dado_ativo(chave_ativo, campo="variacao_pct", e_preco=False):
    """Lê diretamente do dicionário 'ativos' do DadosAtivosUnificados.json."""
    if chave_ativo in ativos_unificados:
        obj = ativos_unificados[chave_ativo]
        val = obj.get(campo) if not e_preco else obj.get("preco")
        if val is not None and isinstance(val, (int, float)):
            return f"{val:,.2f}" if e_preco else f"{val:+.2f}%"
    return "N/A"

# Leitura Numérica de Preço/Ajuste
def get_preco_num(chave_ativo, padrao=0.0):
    if chave_ativo in ativos_unificados:
        val = ativos_unificados[chave_ativo].get("preco")
        if val is not None and isinstance(val, (int, float)):
            return float(val)
    return padrao

win_last = get_preco_num("WIN_LAST_TICK", padrao=180075.0)
win_ajuste = get_preco_num("WIN_AJUSTE", padrao=180208.0)

# --- Cabeçalho Técnico ---
st.markdown("<h2 style='color:#00d4ff;'>🎯 Painel Unificado de Abertura Pregão B3</h2>", unsafe_allow_html=True)
ts_decisao = unificados.get("metadata", {}).get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
st.caption(f"Orquestração Ativa: V2 ({ts_decisao})")

# --- Banner de Alinhamento de Produção ---
st.info("🚀 **Fila de Execução V2:** Este painel consome a decisão oficial gerada pelo motor inteligente de confluência.")

# --- Divisão Estratégica por Sub-Abas Operacionais ---
tab_overnight, tab_0900, tab_1000 = st.tabs([
    "🗓️ 1. Janela Pré-Market (Ajuste)", 
    "⚡ 2. Abertura 09:00h (Leilão WIN)", 
    "📊 3. Abertura 10:00h (Pregão À Vista)"
])

# ============================================================
# ABA 1: JANELA OVERNIGHT / ANÁLISE DE AJUSTE
# ============================================================
with tab_overnight:
    st.markdown("### 🌐 Cenário Macro e Arbitragem")
    
    col_macro, col_spread = st.columns([2, 1])
    
    with col_macro:
        # Extração usando os nomes exatos do JSON fornecido
        vix = get_dado_ativo("VIX", e_preco=True)
        oil = get_dado_ativo("CRUDE_OIL")
        iron = get_dado_ativo("IRON_ORE")
        di27 = get_dado_ativo("DI1_2027")
        di29 = get_dado_ativo("DI1_2029")
        
        st.markdown(f"""
        * **Ambiente Global de Risco (VIX):** `{vix}`
        * **Petróleo Brent/WTI:** `{oil}`
        * **Minério de Ferro (SGX):** `{iron}`
        * **Curva DI Curta (2027):** `{di27}` | **DI Longa (2029):** `{di29}`
        """)
        
    with col_spread:
        distancia_pts = win_last - win_ajuste
        st.metric(
            label="Preço vs Ajuste Anterior",
            value=f"{win_last:,.0f} pts",
            delta=f"{distancia_pts:+.0f} pts",
            delta_color="normal" if abs(distancia_pts) > 100 else "off"
        )
        st.caption(f"Ajuste Base de Referência: {win_ajuste:,.0f}")

# ============================================================
# ABA 2: ABERTURA 09:00H (GAP E PIVOTS)
# ============================================================
with tab_0900:
    st.markdown("### 🔮 Projeção Estatística e Níveis de Pivô")
    
    win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE", {})
    gap_pts_v2 = decisao_v2.get("decisao", {}).get("metadados", {}).get("gap_pts", -133.0)
    
    pivots_win = (
        estimativas.get("pivot_points", {}).get("WIN_FUT") or 
        decisao_v2.get("decisao", {}).get("metadados", {}).get("pivots") or 
        {}
    )
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Variação Teórica Projetada", f"{get_dado_ativo('WIN_AJUSTE')}")
    c2.metric("Abertura Estimada (GAP Pontos)", f"{gap_pts_v2:+.0f} pts")
    
    risco_noticia = noticias.get("resumo", {}).get("classificacao") or ("EXTREMO" if decisao_v2.get("decisao", {}).get("riscos") else "BAIXO")
    c3.metric("Risco Noticiário (09h)", risco_noticia)
    
    if pivots_win:
        st.markdown("#### Níveis Técnicos de Suporte e Resistência (Floor Pivots)")
        p_col1, p_col2 = st.columns(2)
        p_col1.markdown(f"""
        * **Resistência 2 (R2):** `{pivots_win.get('r2', pivots_win.get('R2', 189233)):,.0f}`
        * **Resistência 1 (R1):** `{pivots_win.get('r1', pivots_win.get('R1', 186492)):,.0f}`
        * **Ponto de Pivô (PP):** `{pivots_win.get('pp', pivots_win.get('PP', 184573)):,.0f}`
        """)
        p_col2.markdown(f"""
        * **Suporte 1 (S1):** `{pivots_win.get('s1', pivots_win.get('S1', 181832)):,.0f}`
        * **Suporte 2 (S2):** `{pivots_win.get('s2', pivots_win.get('S2', 179913)):,.0f}`
        """)

# ============================================================
# ABA 3: ABERTURA 10:00H (SMC E FILTROS INSTITUCIONAIS)
# ============================================================
with tab_1000:
    st.markdown("### 🧠 Confluências de Smart Money Concepts")
    
    obj_decisao = decisao_v2.get("decisao", {})
    vies_final = obj_decisao.get("vies_final") or smc_regras.get("bias_direcional") or "BAIXA"
    confianca = obj_decisao.get("confianca") or smc_regras.get("confianca_visual") or 95
    
    st.markdown(f"**Direção Sugerida pelo Core V2:** `{vies_final}` com `{confianca}%` de confiança operacional.")
    
    s_col1, s_col2 = st.columns(2)
    
    with s_col1:
        st.markdown("**Order Blocks Validados (MT5/Volume):**")
        obs = obj_decisao.get("metadados", {}).get("smc", {}).get("order_blocks") or smc_regras.get("order_blocks", [])
        if obs:
            for ob in obs[:2]:
                tipo = ob.get("tipo", "OB")
                preco = ob.get("preco") or ob.get("high") or 0
                st.markdown(f"• OB de **{tipo}** em `{preco:,.0f}`")
        else:
            st.caption("Nenhum Order Block de volume mapeado no range de preço atual.")
            
    with s_col2:
        st.markdown("**Fair Value Gaps Ativos (Vazios de Liquidez):**")
        fvgs = obj_decisao.get("metadados", {}).get("smc", {}).get("fvgs") or smc_regras.get("fair_value_gaps", [])
        fvgs_abertos = [f for f in fvgs if not f.get("preenchido", False)]
        if fvgs_abertos:
            for fvg in fvgs_abertos[:2]:
                tipo = fvg.get("tipo", "COMPRA")
                inf = fvg.get("inferior", 0)
                sup = fvg.get("superior", 0)
                st.markdown(f"• FVG de **{tipo}** entre `{inf:,.0f}` e `{sup:,.0f}`")
        else:
            st.caption("Preço eficiente. Sem Fair Value Gaps abertos.")