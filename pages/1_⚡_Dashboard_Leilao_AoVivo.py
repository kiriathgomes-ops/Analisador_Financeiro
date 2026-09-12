import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Leilão Ao Vivo",
    page_icon="⚡",
    layout="wide"
)

# Caminhos dos arquivos (dentro da pasta Coletas)
PASTA_COLETAS = "Coletas"
ARQUIVO_CSV = os.path.join(PASTA_COLETAS, "preco_teorico_win_fluxo.csv")
ARQUIVO_JSON_MACRO = os.path.join(PASTA_COLETAS, "DadosAtivosUnificados.json")
ARQUIVO_JSON_SMC = os.path.join(PASTA_COLETAS, "AnaliseGraficaSMC_Regras.json")

st.title("⚡ Cockpit de Leilão Ao Vivo - WIN")
st.markdown("Monitoramento em tempo real do preço teórico, fluxo de ordens e confluência macro/institucional.")

# Função para carregar dados do JSON Macro e SMC
def carregar_dados_estaticos():
    macro, smc = {}, {}
    try:
        if os.path.exists(ARQUIVO_JSON_MACRO):
            with open(ARQUIVO_JSON_MACRO, 'r', encoding='utf-8') as f:
                macro = json.load(f).get("ativos", {})
    except: pass
    
    try:
        if os.path.exists(ARQUIVO_JSON_SMC):
            with open(ARQUIVO_JSON_SMC, 'r', encoding='utf-8') as f:
                smc = json.load(f)
    except: pass
    
    return macro, smc

# Definimos um fragmento que atualiza a cada 1 segundo automaticamente
@st.fragment(run_every=1)
def renderizar_dashboard_tempo_real():
    macro_data, smc_data = carregar_dados_estaticos()
    
    # Valores de referência globais
    win_ajuste = macro_data.get("WIN_AJUSTE", {}).get("preco", 0)
    win_fechamento = macro_data.get("WIN_LAST_TICK", {}).get("preco", 0)
    poc_ontem = smc_data.get("niveis_institucionais", {}).get("poc_ontem", 0)
    vies_smc = smc_data.get("bias_direcional", "NEUTRO")
    
    # Cálculo simples do viés macro
    ewz_var = macro_data.get("EWZ", {}).get("variacao_pct", 0)
    sp500_var = macro_data.get("SP500_FUT", {}).get("variacao_pct", 0)
    score_macro = ((ewz_var * 2) + sp500_var) / 3
    vies_macro = "ALTA 🟢" if score_macro > 0.3 else "BAIXA 🔴" if score_macro < -0.3 else "NEUTRO 🟡"

    preco_teorico, confianca, ultima_hora = 0, 0.0, "Aguardando..."
    df_historico = pd.DataFrame()

    # Ler o CSV gerado pelo coletor OCR de forma blindada
    if os.path.exists(ARQUIVO_CSV):
        try:
            # Força a leitura com os nomes corretos das colunas para evitar erros de mapeamento
            df_historico = pd.read_csv(ARQUIVO_CSV, names=["DataHora", "PrecoTeorico", "Confianca"], header=0)
            df_historico = df_historico.dropna()
            
            if not df_historico.empty:
                ultimo_registro = df_historico.iloc[-1]
                preco_teorico = int(float(ultimo_registro["PrecoTeorico"]))
                confianca = float(ultimo_registro["Confianca"])
                ultima_hora = str(ultimo_registro["DataHora"])
        except Exception as e:
            ultima_hora = f"Erro ao ler CSV: {e}"

    # Cálculos de Gaps
    gap_ajuste = preco_teorico - win_ajuste if win_ajuste > 0 and preco_teorico > 0 else 0
    gap_fechto = preco_teorico - win_fechamento if win_fechamento > 0 and preco_teorico > 0 else 0
    dist_poc = preco_teorico - poc_ontem if poc_ontem > 0 and preco_teorico > 0 else 0

    # Layout superior: Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Preço Teórico (PTA)", f"{preco_teorico}", f"Conf: {confianca:.2f}")
    with col2:
        st.metric("📊 Gap do Ajuste", f"{gap_ajuste:+.0f} pts", f"Ajuste: {win_ajuste}")
    with col3:
        st.metric("📉 Gap do Fechamento", f"{gap_fechto:+.0f} pts", f"Último: {win_fechamento}")
    with col4:
        st.metric("🏢 Distância da POC", f"{dist_poc:+.0f} pts", f"POC: {poc_ontem}")

    st.markdown("---")

    # Layout central: Indicadores de Contexto e Veredito
    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        st.subheader("🌐 Contexto Macro / SMC")
        st.info(f"**Viés Macro:** {vies_macro}")
        st.info(f"**Viés Estrutural SMC:** {vies_smc}")
        st.text(f"Última atualização OCR:\n{ultima_hora}")

    with c_right:
        st.subheader("🎯 Veredito Operacional")
        
        if preco_teorico > 0:
            if "ALTA" in vies_macro and gap_ajuste > 0:
                st.success("### 🟢 COMPRA A MERCADO\nConfluência de alta identificada entre o macro e o leilão teóricos.")
            elif "BAIXA" in vies_macro and gap_ajuste < 0:
                st.error("### 🔴 VENDA A MERCADO\nPressão vendedora confirmada nos ativos globais e no book.")
            else:
                st.warning("### ⚠️ MERCADO INDEFINIDO / FINTA\nDivergência entre o contexto global e o preço teórico. Fique de fora.")
        else:
            st.warning("⏳ Aguardando captura válida do preço teórico pelo script...")

    # Seção inferior: Histórico recente do CSV em tabela dinâmica
    st.markdown("---")
    st.subheader("📜 Histórico Recente de Capturas do Leilão")
    if not df_historico.empty:
        st.dataframe(df_historico.tail(10).iloc[::-1], use_container_width=True)
    else:
        st.info("O arquivo CSV será exibido assim que a coleta iniciar.")

# Executa o bloco em tempo real
renderizar_dashboard_tempo_real()