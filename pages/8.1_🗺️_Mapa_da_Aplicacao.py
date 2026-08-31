# -*- coding: utf-8 -*-
"""
Módulo: pages/8.1_🗺️_Mapa_da_Aplicacao.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Renderizar o mapa de fluxo de dados dinâmico da aplicação (Pipeline V2).
"""

import streamlit as st
import json
from pathlib import Path

# Importação de caminhos centralizados do config.py da V2
from config import FILE_PIPELINE_LOG, COLETAS_DIR

# Definição do caminho do mapa de fluxo dinâmico
FILE_MAPA_FLUXO = COLETAS_DIR / "Mapa_Fluxo.json"

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Mapa da Aplicação", layout="wide")

st.markdown("<h2 style='color:#00d4ff;'>🗺️ Mapa da Aplicação e Esteira do Pipeline</h2>", unsafe_allow_html=True)
st.caption("Arquitetura e fluxo dinâmico de dados entre scripts e arquivos de suporte (V2)")

# --- CARGA DOS ARQUIVOS DE MAPA E STATUS ---
mapa_fluxo = carregar_json_defensivo(FILE_MAPA_FLUXO)
log_pipeline = carregar_json_defensivo(FILE_PIPELINE_LOG)

if not mapa_fluxo:
    st.warning("⚠️ Arquivo 'Mapa_Fluxo.json' não encontrado. Certifique-se de executar o script 'Gerar_Mapa_Fluxo.py' para gerar o mapeamento dinâmico.")
    st.stop()

# --- PAINEL DE CONTROLE / METADADOS DO MAPA ---
meta_mapa = mapa_fluxo.get("metadata", {})
st.info(f"🧬 **Mapeamento Atualizado:** Gerado automaticamente em `{meta_mapa.get('gerado_em', 'N/A')}` para o ecossistema `{meta_mapa.get('projeto', 'N/A')}`.")

# Captura o status da última execução real do pipeline para exibir em tela
status_geral = log_pipeline.get("status_geral", "DESCONHECIDO")
data_exec = log_pipeline.get("data_execucao", "N/A")

if status_geral == "SUCESSO":
    st.success(f"✅ **Último Ciclo do Pipeline:** SUCESSO (Executado em {data_exec})")
else:
    st.error(f"❌ **Último Ciclo do Pipeline:** FALHA ou INTERROMPIDO (Verifique o log em {data_exec})")

st.markdown("---")

# --- RENDERIZAÇÃO ESTILIZADA DA ESTEIRA (PIPELINE) ---
st.markdown("### 🛠️ Sequência Dinâmica de Processamento (Etapas)")
st.caption("Clique em cada etapa para expandir os detalhes de arquitetura, arquivos envolvidos, inputs e outputs.")

etapas = mapa_fluxo.get("pipeline", [])
etapas_status = {item.get("etapa"): item.get("status", "OK") for item in log_pipeline.get("etapas", [])}

for passo in etapas:
    num_etapa = passo.get("etapa", 0)
    nome_etapa = passo.get("nome", "Etapa Sem Nome")
    descricao = list(passo.get("arquivos", ["N/A"]))[0] if passo.get("arquivos") else "N/A"
    
    # Identifica o status real dessa etapa específica no último log de produção
    # O main_pipeline gera strings como "0 - LIMPEZA DE IMAGENS...", vamos casar pelo número do início
    status_etapa_real = "AGUARDANDO"
    for item_log in log_pipeline.get("etapas", []):
        if item_log.get("etapa", "").startswith(str(num_etapa)):
            status_etapa_real = item_log.get("status", "OK")
            break
            
    # Define o emoji de status para o cabeçalho do expander
    emoji_status = "🟢" if status_etapa_real == "OK" else ("🟡" if status_etapa_real == "AGUARDANDO" else "🔴")
    
    # Renderiza o Expander dinâmico contendo a esteira de dados do script
    with st.expander(f"{emoji_status} Etapa {num_etapa} — {nome_etapa}"):
        st.markdown(f"**Description / Função:** {passo.get('descricao', 'Sem descrição mapeada.')}")
        st.markdown(f"**Script Executor (Python):** `{descricao}`")
        
        col_in, col_out = st.columns(2)
        
        with col_in:
            st.markdown("📥 **Fontes de Entrada / Origem:**")
            inputs = passo.get("entrada", [])
            if inputs:
                for inp in inputs:
                    st.markdown(f"- `{inp}`")
            else:
                st.caption("Sem dependências de arquivos externos.")
                
        with col_out:
            st.markdown("📤 **Artefatos Gerados (Saída JSON/MD):**")
            outputs = passo.get("saida", [])
            if outputs:
                for out in outputs:
                    st.markdown(f"- `Coletas/{out}`")
            else:
                st.caption("Script de processo em lote ou no-op (Sem persistência física).")

st.markdown("---")
st.caption("🔒 Módulo de governança arquitetural ativo — Sincronizado automaticamente com a AST (Abstract Syntax Tree) do main_pipeline.py.")
