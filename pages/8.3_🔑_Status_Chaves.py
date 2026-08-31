# -*- coding: utf-8 -*-
"""
Módulo: pages/8.3_🔑_Status_Chaves.py
Versão: 2.0 - Otimizado para Governança V2
Objetivo: Painel de auditoria visual de chaves de API, tokens e conectores externos.
"""

import streamlit as st
import os
from pathlib import Path

# Tenta importar as chaves e o KeyManager do seu ecossistema centralizado
from config import FINNHUB_API_KEY

def mascarar_chave(chave_str):
    """Mascara chaves de API para exibição segura em tela (ex: gsk_u...xxxx)."""
    if not chave_str:
        return "❌ NÃO CONFIGURADO (Ausente no .env)"
    if len(chave_str) <= 8:
        return "✅ CONFIGURADO (Chave Curta)"
    return f"✅ ATIVO ({chave_str[:5]}...{chave_str[-4:]})"

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Status de Chaves", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🔑 Status e Validação de Chaves de API</h2>", unsafe_allow_html=True)
st.caption("Central de Auditoria de Conectores Externos e Credenciais de Segurança (V2)")

st.info("🔒 **Segurança Operacional:** Este painel apenas audita a presença e o carregamento dos tokens na memória do servidor. As credenciais confidenciais permanecem mascaradas no terminal.")

st.markdown("---")

# --- CENTRAL DE AUDITORIA: QUADRO DE CONECTORES ---
st.markdown("### 📡 Conectores e Provedores de Dados Ativos")

# 1. Captura as variáveis direto do ambiente operacional (carregadas via config/.env)
groq_key = os.getenv("GROQ_API_KEY")
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat = os.getenv("TELEGRAM_CHAT")
mt5_login = os.getenv("MT5_LOGIN")

# 2. Estruturação da Matriz de Auditoria para exibição limpa
linhas_chaves = [
    {
        "Provedor / API": "Finnhub API",
        "Finalidade": "Performance de ADRs e Cotações Internacionais (Opção A)",
        "Variável do Sistema": "FINNHUB_API_KEY",
        "Status de Conexão": mascarar_chave(FINNHUB_API_KEY)
    },
    {
        "Provedor / API": "Groq Cloud API",
        "Finalidade": "Modelos LMs de Grande Porte (Módulos de Texto/Auditoria)",
        "Variável do Sistema": "GROQ_API_KEY",
        "Status de Conexão": mascarar_chave(groq_key)
    },
    {
        "Provedor / API": "Telegram Bot API",
        "Finalidade": "Notificações Automatizadas de Sinais e Alertas Macro",
        "Variável do Sistema": "TELEGRAM_TOKEN",
        "Status de Conexão": mascarar_chave(telegram_token)
    },
    {
        "Provedor / API": "Telegram Chat Config",
        "Finalidade": "Canal Destino das Mensagens Operacionais",
        "Variável do Sistema": "TELEGRAM_CHAT",
        "Status de Conexão": "✅ CONFIGURADO" if telegram_chat else "❌ NÃO CONFIGURADO"
    },
    {
        "Provedor / API": "MetaTrader 5 Link",
        "Finalidade": "Autenticação e Roteamento de Ordens B3 (Genial)",
        "Variável do Sistema": "MT5_LOGIN",
        "Status de Conexão": f"✅ CONTA ID: {mt5_login}" if mt5_login else "❌ NÃO CONFIGURADO"
    }
]

# Renderização da tabela de auditoria
import pandas as pd
df_chaves = pd.DataFrame(linhas_chaves)
st.dataframe(df_chaves.set_index("Provedor / API"), use_container_width=True)

st.markdown("---")

# --- CHECKLIST DE VERIFICAÇÃO DE INFRAESTRUTURA ---
st.markdown("### 🛠️ Diagnóstico de Prontidão de Produção (Smoke Check)")

falhas = 0
if not FINNHUB_API_KEY: falhas += 1
if not groq_key: falhas += 1
if not mt5_login: falhas += 1

if falhas == 0:
    st.success("🎉 **PRODUÇÃO V2 TOTALMENTE OPERACIONAL:** Todas as chaves e conectores críticos foram validados com sucesso na memória da aplicação. Terminal pronto para operar a abertura do mercado.")
else:
    st.warning(f"⚠️ **PRODUÇÃO PARCIAL:** O terminal identificou `{falhas}` ausência(s) de credenciais no seu arquivo `.env`. Algumas sub-abas operacionais de relatórios podem apresentar comportamento degradado.")
