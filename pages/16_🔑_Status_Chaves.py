# pages/16_🔑_Status_Chaves.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.KeyManager import key_manager

st.set_page_config(
    page_title="Status das Chaves API",
    page_icon="🔑",
    layout="wide"
)

st.title("🔑 Status das Chaves API")

# Carrega status
status = key_manager.get_status()

if status:
    # Converte para DataFrame
    df = pd.DataFrame.from_dict(status, orient='index')
    df.index.name = "Chave"
    df = df.reset_index()
    
    # Formata colunas
    df["total_tokens"] = df["total_tokens"].apply(lambda x: f"{x:,}")
    df["rate_limit_ate"] = df["rate_limit_ate"].fillna("Disponível")
    
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Chave": "Chave",
            "ativa": st.column_config.CheckboxColumn("Ativa"),
            "total_tokens": "Total Tokens",
            "rate_limit_ate": "Rate Limit Até",
            "ultimo_uso": "Último Uso"
        }
    )
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Chaves", len(status))
    with col2:
        ativas = sum(1 for k in status.values() if k["ativa"])
        st.metric("Chaves Ativas", ativas)
    with col3:
        em_rate = sum(1 for k in status.values() if k["rate_limit_ate"] is not None)
        st.metric("Em Rate Limit", em_rate)
    
    # Botão para resetar rate limit (forçar)
    if st.button("🔄 Resetar Status de Rate Limit"):
        for k in key_manager.keys:
            k["rate_limit_ate"] = None
        st.success("✅ Rate limits resetados!")
        st.rerun()
else:
    st.warning("⚠️ Nenhuma chave configurada!")
    st.info("Adicione GROQ_API_KEY_1, GROQ_API_KEY_2, ... no arquivo .env")