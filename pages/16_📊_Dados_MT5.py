# pages/16_📊_Dados_MT5.py
import streamlit as st
from pathlib import Path
import sys
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from Coletor_MT5 import executar_coleta_mt5, carregar_dados_mt5, obter_melhor_contrato

st.set_page_config(
    page_title="Dados MT5 - B3",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dados MetaTrader5 - B3")
st.caption("Coleta de dados dos contratos B3 via MT5")

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 MT5")
st.sidebar.caption("Dados B3")

if st.sidebar.button("🔄 Coletar Agora", width="stretch"):
    with st.spinner("Coletando dados do MT5..."):
        dados = executar_coleta_mt5()
        if dados:
            st.success("✅ Coleta realizada com sucesso!")
        st.rerun()

# ============================================================
# MAIN
# ============================================================

dados = carregar_dados_mt5()

if not dados:
    st.warning("⚠️ Nenhum dado MT5 encontrado. Clique em 'Coletar Agora'.")
    st.stop()

# Timestamp
timestamp = dados.get("timestamp", "N/A")
st.info(f"🕒 Última coleta: {timestamp}")

# Status
status = dados.get("status", "UNKNOWN")
if status == "OK":
    st.success("✅ Conexão MT5 OK")
else:
    st.error(f"❌ Erro: {dados.get('mensagem', 'Desconhecido')}")

# Contratos
st.subheader("📊 Contratos Coletados")

contratos = dados.get("contratos", {})
if contratos:
    # Cria tabela
    dados_tabela = []
    for contrato, info in contratos.items():
        dados_tabela.append({
            "Contrato": contrato,
            "Último": f"{info['last']:.2f}",
            "Bid": f"{info['bid']:.2f}",
            "Ask": f"{info['ask']:.2f}",
            "Volume": info['volume'],
            "Horário": info['time'][11:16] if info.get('time') else "N/A"
        })
    
    st.dataframe(dados_tabela, width="stretch")
    
    # ============================================================
    # 🔥 CORREÇÃO: Removido o parâmetro 'contrato'
    # ============================================================
    col1, col2, col3 = st.columns(3)
    
    with col1:
        win = obter_melhor_contrato("WIN")
        if win:
            st.metric("WIN (Melhor Contrato)", f"{win['last']:.0f}")
            st.caption(f"📌 Contrato: {win['contrato']}")
        else:
            st.metric("WIN (Melhor Contrato)", "N/A")
    
    with col2:
        wdo = obter_melhor_contrato("WDO")
        if wdo:
            st.metric("WDO (Melhor Contrato)", f"{wdo['last']:.2f}")
            st.caption(f"📌 Contrato: {wdo['contrato']}")
        else:
            st.metric("WDO (Melhor Contrato)", "N/A")
    
    with col3:
        st.metric("Total Contratos", len(contratos))
else:
    st.warning("Nenhum contrato encontrado")

# ============================================================
# BOTÃO PARA ATUALIZAR
# ============================================================

st.markdown("---")
if st.button("🔄 Atualizar Dados", width="stretch"):
    with st.spinner("Coletando dados do MT5..."):
        dados = executar_coleta_mt5()
        if dados:
            st.success("✅ Coleta realizada com sucesso!")
        st.rerun()

# ============================================================
# DADOS BRUTOS (para debug)
# ============================================================

with st.expander("📄 Ver Dados Brutos (JSON)"):
    st.json(dados)