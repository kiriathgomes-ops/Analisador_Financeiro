# ============================================================
# PÁGINA: Mapa da Aplicação
#
# Objetivo:
# Visualização automática da arquitetura
# do Analisador Financeiro
#
# VERSÃO MELHORADA - Com visual profissional e métricas
#
# ============================================================

import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Mapa da Aplicação",
    page_icon="🗺️",
    layout="wide"
)

# ============================================================
# CSS PERSONALIZADO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }

    .card-status {
        background: #161b22;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #2a2d3a;
        text-align: center;
    }
    .card-status .numero {
        font-size: 2rem;
        font-weight: 700;
    }
    .card-status .label {
        color: #8b949e;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .card-status .numero.ok {
        color: #00c853;
    }
    .card-status .numero.erro {
        color: #ff3d00;
    }
    .card-status .numero.atencao {
        color: #ffc107;
    }

    .card-modulo {
        background: #161b22;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #2a2d3a;
        margin-bottom: 10px;
        transition: all 0.3s ease;
    }
    .card-modulo:hover {
        border-color: #58a6ff;
        box-shadow: 0 4px 20px rgba(88,166,255,0.1);
    }
    .card-modulo .titulo {
        font-weight: 600;
        color: #e6edf3;
    }
    .card-modulo .descricao {
        color: #8b949e;
        font-size: 0.85rem;
    }
    .card-modulo .badge {
        font-size: 0.7rem;
        padding: 2px 10px;
        border-radius: 12px;
        display: inline-block;
    }
    .card-modulo .badge.ok {
        background: rgba(0, 200, 83, 0.15);
        color: #00c853;
    }
    .card-modulo .badge.erro {
        background: rgba(255, 61, 0, 0.15);
        color: #ff3d00;
    }
    .card-modulo .badge.atencao {
        background: rgba(255, 193, 7, 0.15);
        color: #ffc107;
    }

    .sidebar-info {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2a2d4a;
        margin-bottom: 12px;
    }
    .sidebar-info .label {
        color: #8b949e;
        font-size: 0.75rem;
    }
    .sidebar-info .value {
        color: #e6edf3;
        font-size: 0.95rem;
        font-weight: 600;
    }

    .info-box {
        background-color: #1a1c2a;
        border: 1px solid #2a2d3a;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.85rem;
        color: #cccccc;
        margin-top: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# CAMINHOS DO PROJETO
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_COLETAS = os.path.join(BASE_DIR, "Coletas")

# ============================================================
# FUNÇÃO LEITURA JSON SEGURA
# ============================================================

@st.cache_data(ttl=30, show_spinner=False)
def carregar_json(nome):
    caminho = os.path.join(PASTA_COLETAS, nome)
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except Exception as erro:
        return None

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🗺️ Mapa da Aplicação")
st.sidebar.caption("Documentação automática")
st.sidebar.markdown("---")

# Status dos arquivos
st.sidebar.markdown("### Status dos Arquivos")
arquivos_status = {
    "Mapa do Projeto": "Mapa_Projeto.json",
    "Mapa de Fluxo": "Mapa_Fluxo.json",
    "Pipeline Log": "Pipeline_Log.json",
}
for nome, arquivo in arquivos_status.items():
    caminho = os.path.join(PASTA_COLETAS, arquivo)
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome}")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# CABEÇALHO
# ============================================================

st.title("🗺️ Mapa da Aplicação")
st.subheader("Analisador Financeiro - Documentação Automática")

st.markdown("""
Esta página lê os mapas gerados automaticamente pelo próprio projeto,
fornecendo uma visão completa da arquitetura e do status do sistema.
""")

# ============================================================
# STATUS DO SISTEMA
# ============================================================

st.divider()
st.header("🟢 Status do Sistema")

pipeline = carregar_json("Pipeline_Log.json")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="card-status">
        <div class="numero ok">✅</div>
        <div class="label">Projeto</div>
        <div style="font-size:0.8rem; color:#e6edf3;">Analisador Financeiro</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    status_pipeline = "ok" if pipeline else "erro"
    texto_status = "OK" if pipeline else "Sem dados"
    st.markdown(f"""
    <div class="card-status">
        <div class="numero {status_pipeline}">{texto_status}</div>
        <div class="label">Pipeline</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="card-status">
        <div class="numero atencao">{datetime.now().strftime('%H:%M')}</div>
        <div class="label">Última Verificação</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    # Conta arquivos na pasta Coletas
    if os.path.exists(PASTA_COLETAS):
        num_arquivos = len([f for f in os.listdir(PASTA_COLETAS) if os.path.isfile(os.path.join(PASTA_COLETAS, f))])
    else:
        num_arquivos = 0
    st.markdown(f"""
    <div class="card-status">
        <div class="numero ok">{num_arquivos}</div>
        <div class="label">Arquivos em Coletas</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# PIPELINE LOG - GRÁFICO DE FLUXO
# ============================================================

st.header("📋 Pipeline de Execução")

if pipeline:
    etapas = pipeline.get("etapas", [])
    
    if etapas:
        # Cria gráfico de fluxo
        etapas_nomes = [e.get("script", "").replace(".py", "") for e in etapas]
        etapas_status = [e.get("status", "") for e in etapas]
        etapas_tempo = [f"{e.get('inicio', '')[:8]} → {e.get('fim', '')[:8]}" for e in etapas]
        
        # DataFrame para exibição
        df_etapas = pd.DataFrame({
            "Etapa": [f"{i+1}" for i in range(len(etapas))],
            "Script": etapas_nomes,
            "Status": etapas_status,
            "Horário": etapas_tempo,
        })
        
        # Cores para status
        cor_status = {"OK": "🟢", "ERRO": "🔴", "WARNING": "🟡"}
        df_etapas["Status"] = df_etapas["Status"].map(lambda x: cor_status.get(x, "⚪"))
        
        st.dataframe(
            df_etapas,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Etapa": st.column_config.TextColumn("Etapa", width="small"),
                "Script": st.column_config.TextColumn("Script"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Horário": st.column_config.TextColumn("Horário"),
            }
        )
        
        # Gráfico de barras do fluxo
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=etapas_nomes,
            y=[1] * len(etapas_nomes),
            marker_color=["#00c853" if s == "OK" else "#ff3d00" for s in etapas_status],
            text=[s for s in etapas_status],
            textposition="inside",
            name="Status",
        ))
        fig.update_layout(
            title="Fluxo da Pipeline",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#e6edf3",
            showlegend=False,
            height=200,
            yaxis_visible=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Resumo
        total_ok = sum(1 for s in etapas_status if s == "OK")
        total_erro = sum(1 for s in etapas_status if s == "ERRO")
        st.info(f"📊 **Resumo:** {total_ok} etapas OK | {total_erro} etapas com erro")

else:
    st.warning("Pipeline_Log.json não encontrado. Execute `main_pipeline.py` para gerar o log.")

st.markdown("---")

# ============================================================
# INVENTÁRIO DO PROJETO
# ============================================================

st.header("📁 Inventário do Projeto")

arquivos = carregar_json("Mapa_Projeto.json")

if arquivos:
    total = arquivos.get("total_arquivos", 0)
    estrutura = arquivos.get("estrutura", {})
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Total de arquivos", total)
    
    with col2:
        # Exibe categorias em cards
        cols = st.columns(min(4, len(estrutura)))
        for i, (categoria, lista) in enumerate(estrutura.items()):
            with cols[i % len(cols)]:
                st.metric(categoria, len(lista))
    
    st.markdown("---")
    
    # ============================================================
    # ESTRUTURA DOS MÓDULOS (COM FILTRO)
    # ============================================================
    st.subheader("🏗️ Estrutura dos Módulos")
    
    categorias_lista = list(estrutura.keys())
    filtro_categoria = st.selectbox("Filtrar por categoria", ["Todas"] + categorias_lista)
    
    for categoria, lista in estrutura.items():
        if filtro_categoria != "Todas" and filtro_categoria != categoria:
            continue
            
        with st.expander(f"📦 {categoria} ({len(lista)})", expanded=filtro_categoria == categoria):
            for item in lista[:20]:  # Limita a 20 para não sobrecarregar
                st.markdown(f"""
                <div class="card-modulo">
                    <div class="titulo">📄 {item['arquivo']}</div>
                    <div class="descricao">
                        📂 {item['local']} · 📏 {item['tamanho_kb']:.1f} KB · 
                        🕐 {item['ultima_alteracao']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            if len(lista) > 20:
                st.caption(f"... e mais {len(lista) - 20} arquivos")

else:
    st.warning("Mapa_Projeto.json não encontrado. Execute `Gerar_Mapa_Projeto.py` para gerar o mapa.")

st.markdown("---")

# ============================================================
# FLUXO OPERACIONAL
# ============================================================

st.header("🔄 Fluxo Operacional")

fluxo = carregar_json("Mapa_Fluxo.json")

if fluxo:
    etapas = fluxo.get("pipeline", [])
    
    for etapa in etapas:
        with st.expander(f"{etapa['etapa']} - {etapa['nome']}"):
            st.write(etapa.get("descricao", ""))
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📂 Arquivos:**")
                for arq in etapa.get("arquivos", []):
                    st.code(arq, language="python")
            
            with col2:
                st.write("**📤 Saídas:**")
                for saida in etapa.get("saida", []):
                    st.success(f"📄 {saida}")
else:
    st.warning("Mapa_Fluxo.json não encontrado. Execute `Gerar_Mapa_Fluxo.py` para gerar o mapa.")

# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.caption(
    f"Gerado automaticamente pelo Analisador Financeiro - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)