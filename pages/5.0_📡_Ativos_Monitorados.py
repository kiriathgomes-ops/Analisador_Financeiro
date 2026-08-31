# -*- coding: utf-8 -*-
"""
Módulo: pages/5.0_📡_Ativos_Monitorados.py
Versão: 2.0 - Otimizado para Produção V2
Objetivo: Dashboard de integridade e monitoramento dos 32 ativos validados do ecossistema.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime

# Importações de caminhos padronizados e tabelas do config.py da V2
from config import FILE_VALIDADOS, id_interno

def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Configuração da página Streamlit
st.set_page_config(page_title="Quant Terminal - Ativos Monitorados", layout="wide")

# --- CARGA DOS DADOS HIGIENIZADOS V2 ---
payload_validado = carregar_json_defensivo(FILE_VALIDADOS)

# --- CABEÇALHO ---
st.markdown("<h2 style='color:#00d4ff;'>📡 Status e Integridade de Ativos Monitorados</h2>", unsafe_allow_html=True)
st.caption("Central de Auditoria de Ingestão de Dados: Cruzamento Multimercados em Tempo Real")

if not payload_validado:
    st.warning("⚠️ Arquivo de dados validados não encontrado. Certifique-se de que a etapa de validação (Validador.py) rodou no pipeline.")
    st.stop()

metadata = payload_validado.get("metadata_validacao", {})
total_recebidos = metadata.get("total_recebidos", 0)
total_aprovados = metadata.get("total_aprovados", 0)
total_rejeitados = metadata.get("total_rejeitados", 0)

# --- PAINEL DE KPIs DE SAÚDE DOS DADOS ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Carga Útil Recebida", f"{total_recebidos} ativos")
c2.metric("Aprovados pelo Validador", f"{total_aprovados} OK", delta=f"{total_aprovados/total_recebidos*100:.1f}% Eficiência" if total_recebidos > 0 else "0%")

if total_rejeitados > 0:
    c3.metric("Ativos Rejeitados / Falhas", f"{total_rejeitados} Erros", delta="- Problema na API", delta_color="inverse")
else:
    c3.metric("Ativos Rejeitados / Falhas", "0 Erros", delta="Estabilidade 100%", delta_color="normal")
    
c4.markdown(f"<div style='background-color:#161b24; padding:10px; border-radius:8px; border:1px solid #2a3a4a; height:100%; text-align:center;'><span style='font-size:0.85rem; color:#8b949e;'>ÚLTIMA AUDITORIA V2</span><br><span style='font-size:1.25rem; font-weight:bold; color:#00ff88;'>{datetime.fromisoformat(metadata.get('timestamp_validacao', datetime.now().isoformat())).strftime('%H:%M:%S')}</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- PROCESSAMENTO E AGRUPAMENTO OPERACIONAL ---
ativos_lista = payload_validado.get("ativos_validados", [])

# Estruturação por categorias conforme as regras de negócio da V2
categorias = {
    "🇧🇷 Mercado Local (Futuros B3)": ["WIN_AJUSTE", "WDO_AJUSTE", "WIN_FUT", "WDO_FUT", "DI1_2027", "DI1_2029"],
    "🇺🇸 Drivers Globais & Risco": ["VIX", "SP500_FUT", "NASDAQ_FUT", "DXY", "USD_MXN"],
    "🪵 Commodities Cíclicas": ["IRON_ORE", "IRON_ORE_2M", "CRUDE_OIL", "GOLD"],
    "📈 ADRs Brasileiras (Sentiment NY)": ["EWZ", "VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"],
    "🏦 Mercado à Vista (Ações Locais)": ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"]
}

# --- RENDERIZAÇÃO DAS SUB-ABAS POR CATEGORIA ---
abas_nomes = list(categorias.keys())
abas = st.tabs(abas_nomes)

for idx_aba, nome_aba in enumerate(abas_nomes):
    with abas[idx_aba]:
        ids_categoria = categorias[nome_aba]
        linhas_categoria = []
        
        for ativo in ativos_lista:
            if ativo.get("ativo_id") in ids_categoria:
                # Tratamento de nulos para campos opcionais
                var_pct = ativo.get("change_percent")
                var_txt = f"{var_pct:+.2f}%" if var_pct is not None else "—"
                vol = ativo.get("volume")
                vol_txt = f"{vol:,.0f}" if vol is not None else "—"
                
                linhas_categoria.append({
                    "Identificador V2": ativo.get("ativo_id"),
                    "Ticker Original": ativo.get("ticker_original"),
                    "Preço / Taxa": f"{ativo.get('close'):,.4f}" if ativo.get('close', 0) < 100 else f"{ativo.get('close'):,.2f}",
                    "Variação Diária": var_txt,
                    "Volume Turn": vol_txt,
                    "Fonte de Coleta": ativo.get("fonte", "N/A"),
                    "Timestamp": ativo.get("timestamp_coleta", "N/A")[-14:-5] if "T" in str(ativo.get("timestamp_coleta")) else "N/A"
                })
                
        if linhas_categoria:
            df_cat = pd.DataFrame(linhas_categoria)
            st.dataframe(df_cat.set_index("Identificador V2"), use_container_width=True)
        else:
            st.caption("ℹ️ Nenhum ativo desta categoria foi processado nesta janela de execução.")

# --- RELATÓRIO DE ERROS / REJEIÇÕES (CIRCUIT BREAKER VISUAL) ---
rejeicoes = payload_validado.get("relatorio_rejeicoes", [])
if rejeicoes:
    st.markdown("### 🚨 Relatório de Ativos Rejeitados / Fora do Ar")
    st.warning("Os ativos abaixo falharam nos testes estritos de integridade quantitativa (dados ausentes ou preço zerado nas APIs). O orquestrador isolou esses campos para proteger a pontuação final de viés.")
    
    df_rejeitados = pd.DataFrame(rejeicoes)
    st.table(df_rejeitados)
