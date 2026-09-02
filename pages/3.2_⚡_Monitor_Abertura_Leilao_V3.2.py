# -*- coding: utf-8 -*-
"""
Módulo: pages/3.2_⚡_Monitor_Abertura_Leilao_V3.2.py
Versão: 3.3.0 - Unificada (Monitor de Leilão + Termômetro de Fluxo & ADRs)
Objetivo: Monitorar formação de preço, leilão, fluxo institucional externo e spreads de arbitragem B3 vs ADRs
"""

import logging
from pathlib import Path
import json
import streamlit as st
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

@st.cache_data(ttl=5) # Cache leve para evitar I/O excessivo em disco a cada rerun do Streamlit
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

# --- SEÇÃO 0: TERMÔMETRO ESTATÍSTICO DE FLUXO ESTRANGEIRO (Incorporado da 3.3) ---
st.markdown("### 🏦 Termômetro Estatístico de Fluxo Estrangeiro")
ind_compostos = dados_metricas.get("indicadores_compostos", {})
ind_adrs = ind_compostos.get("indicador_adrs_brasileiras")
ind_externo = ind_compostos.get("indicador_mercado_externo")

c1, c2, c3 = st.columns(3)

# Indicador de ADRs (Soma/Média das variações das ADRs Brasileiras)[cite: 1]
if ind_adrs is not None:
    c1.metric(
        label="Indicador Composto ADRs BR", 
        value=f"{ind_adrs:+.2f}%",
        delta="Fluxo Comprador" if ind_adrs > 0.5 else ("Fluxo Vendedor" if ind_adrs < -0.5 else "Estável"),
        delta_color="normal" if abs(ind_adrs) > 0.5 else "off"
    )
else:
    c1.metric(label="Indicador Composto ADRs BR", value="Aguardando dados...")

# Indicador de Mercado Externo (VIX, Petróleo, Minério combinados)[cite: 1]
if ind_externo is not None:
    c2.metric(
        label="Indicador de Mercado Externo", 
        value=f"{ind_externo:+.2f}%",
        delta="Favorável ao Risco" if ind_externo > 0 else "Aversão ao Risco",
        delta_color="normal"
    )
else:
    c2.metric(label="Indicador de Mercado Externo", value="Aguardando dados...")

# ETF EWZ (Fundo de índice do Brasil negociado em NY)[cite: 1]
ewz_pct = dados_metricas.get("performance_relativa", {}).get("ewz_change_pct", 0.0)
if ewz_pct is not None:
    c3.metric(
        label="EWZ (ETF Brasil em NY)", 
        value=f"{ewz_pct:+.2f}%",
        delta_color="off"
    )

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

# --- SEÇÃO 4: NOTA DE TRADING (Incorporada da 3.3) ---
st.markdown("---")
st.markdown("💡 **Nota de Trading:** Grandes descolamentos (maiores que ±0.50%) em papéis de alta liquidez como VALE3 e PETR4 costumam ser fechados rapidamente por robôs de arbitragem institucionais de alta frequência nas primeiras horas do pregão à vista brasileiro[cite: 1].")