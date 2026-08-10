"""
Dashboard de Notícias e Calendário Econômico
============================================
Versão Melhorada - Com IA e análise de impacto no WIN
"""

from datetime import datetime
import json
import os
import sys
import re
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# Configuração da Página
st.set_page_config(
    page_title="Calendário Econômico & Impacto WIN",
    page_icon="📊",
    layout="wide",
)

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()

# ============================================================
# CSS PERSONALIZADO
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
    }

    .card-impacto-alto {
        background: linear-gradient(145deg, #2d0d0d 0%, #1a0a0a 100%);
        border-left: 4px solid #ff3d00;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border: 1px solid #3d1a1a;
    }
    .card-impacto-medio {
        background: linear-gradient(145deg, #2d1f0d 0%, #1a120a 100%);
        border-left: 4px solid #ffa100;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border: 1px solid #3d2a1a;
    }
    .card-impacto-baixo {
        background: linear-gradient(145deg, #0d1a2d 0%, #0a111a 100%);
        border-left: 4px solid #00c853;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border: 1px solid #1a2a3d;
    }

    .badge-impacto {
        display: inline-block;
        padding: 2px 12px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    .badge-impacto.alto {
        background: rgba(255, 61, 0, 0.2);
        color: #ff3d00;
        border: 1px solid rgba(255, 61, 0, 0.3);
    }
    .badge-impacto.medio {
        background: rgba(255, 161, 0, 0.2);
        color: #ffa100;
        border: 1px solid rgba(255, 161, 0, 0.3);
    }
    .badge-impacto.baixo {
        background: rgba(0, 200, 83, 0.2);
        color: #00c853;
        border: 1px solid rgba(0, 200, 83, 0.3);
    }

    .card-noticia {
        background: #161b22;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #2a2d3a;
        margin-bottom: 10px;
        transition: all 0.3s ease;
    }
    .card-noticia:hover {
        border-color: #58a6ff;
        box-shadow: 0 4px 20px rgba(88,166,255,0.1);
    }

    .card-ai {
        background: linear-gradient(145deg, #12141c 0%, #1a1c2a 100%);
        border-left: 4px solid #7c5cfc;
        padding: 16px 20px;
        border-radius: 10px;
        border: 1px solid #2a2d4a;
    }
    .card-ai h4 {
        color: #a78bfa;
        margin-top: 0;
    }

    .stat-box {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border: 1px solid #2a2d3a;
    }
    .stat-box .number {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #58a6ff, #7c5cfc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .stat-box .label {
        color: #8b949e;
        font-size: 0.8rem;
        margin-top: 4px;
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

    .sidebar-info {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2a2d4a;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
ARQUIVO_IMPACTO = os.path.join(COLETAS_DIR, "Noticias_Impacto_Dia.json")
ARQUIVO_CALENDARIO = os.path.join(COLETAS_DIR, "Noticias_Calendario.json")

# Adiciona Raiz ao Path para Importações Globais
sys.path.append(BASE_DIR)

try:
    from Analise_Noticias import analisar_noticias
    from Coleta_Noticias_Calendario import obter_noticias_hoje
except ImportError:
    st.error("⚠️ Certifique-se de que os scripts de coleta estão na raiz do projeto.")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def verificar_e_executar_coleta():
    """Garante que a coleta ocorra se os arquivos JSON não existirem."""
    os.makedirs(COLETAS_DIR, exist_ok=True)
    if not os.path.exists(ARQUIVO_CALENDARIO) or not os.path.exists(ARQUIVO_IMPACTO):
        with st.spinner("📊 Coletando dados da API do TradingView..."):
            obter_noticias_hoje()
            analisar_noticias()

def obter_status_impacto(pontos):
    """Retorna status baseado na pontuação de impacto."""
    if pontos >= 15:
        return "EXTREMO", "🔴", "alto"
    elif pontos >= 9:
        return "ALTO", "🟠", "alto"
    elif pontos >= 4:
        return "ATENÇÃO", "🟡", "medio"
    else:
        return "BAIXO", "🟢", "baixo"

def analisar_noticias_com_ia(api_key: str, eventos: List[Dict]) -> str:
    """Analisa as notícias com IA para impacto no WIN."""
    try:
        client = Groq(api_key=api_key)
        
        # Resume as notícias principais (3 estrelas)
        noticias_principais = []
        for ev in eventos:
            if ev.get("importancia", 0) >= 3:
                noticias_principais.append(
                    f"- {ev.get('hora', '')} | {ev.get('evento', '')} | {ev.get('pais', '')}"
                )
        
        if not noticias_principais:
            return "📊 Nenhuma notícia de alto impacto hoje. Mercado deve operar com volatilidade controlada."
        
        prompt = f"""
        Você é um analista de mercado especializado em Mini Índice (WIN) da B3.

        NOTÍCIAS DE ALTO IMPACTO HOJE:
        {chr(10).join(noticias_principais)}

        ANALISE:
        1. Qual o impacto esperado no WIN?
        2. Qual horário merece mais atenção?
        3. Recomendação para o trader: o que fazer?

        Responda em português, seja direto e objetivo. Máximo 5 frases.
        """
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Você é um analista de mercado. Responda em português."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"⚠️ Erro na análise IA: {e}"

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 Notícias")
st.sidebar.caption("Calendário Econômico")
st.sidebar.markdown("---")

st.sidebar.markdown("### Status dos Dados")
arquivos_status = {
    "Calendário": ARQUIVO_CALENDARIO,
    "Impacto": ARQUIVO_IMPACTO,
}
for nome, caminho in arquivos_status.items():
    existe = "✅" if os.path.exists(caminho) else "❌"
    st.sidebar.caption(f"{existe} {nome}")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados", width="stretch"):
    with st.spinner("Coletando dados..."):
        obter_noticias_hoje()
        analisar_noticias()
        st.rerun()

# ============================================================
# RENDERIZAÇÃO DO DASHBOARD
# ============================================================

def renderizar_dashboard():
    st.title("📊 Dashboard de Impacto Macro & Calendário Econômico")
    st.caption("Foco Institucional SMC / ICT — Mini Índice B3")

    verificar_e_executar_coleta()

    if not os.path.exists(ARQUIVO_IMPACTO) or not os.path.exists(ARQUIVO_CALENDARIO):
        st.error("❌ Não foi possível carregar os arquivos JSON na pasta `Coletas/`.")
        return

    with open(ARQUIVO_IMPACTO, "r", encoding="utf-8") as f:
        dados_analise = json.load(f)

    with open(ARQUIVO_CALENDARIO, "r", encoding="utf-8") as f:
        dados_calendario = json.load(f)

    resumo = dados_analise.get("resumo", {})
    alertas = dados_analise.get("alertas", {})
    eventos_completos = dados_calendario.get("calendario_eventos", {}).get("eventos", [])

    st.markdown("---")

    # ============================================================
    # 1. KPIs E RESULTADOS DE IMPACTO
    # ============================================================
    st.subheader("📊 Resumo de Impacto do Dia")
    
    pontos = resumo.get("impacto_total", 0)
    status, emoji, classe = obter_status_impacto(pontos)
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="number">{pontos}</div>
            <div class="label">Pontuação Total</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="number">{emoji} {status}</div>
            <div class="label">Nível de Risco</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        status_texto = "⚠️ ATIVADO" if alertas.get("risco_abertura_WIN") else "🟢 LIBERADO"
        st.markdown(f"""
        <div class="stat-box">
            <div class="number" style="font-size:1.5rem;">{status_texto}</div>
            <div class="label">Risco Abertura WIN</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        status_brasil = "🚨 CRÍTICO" if alertas.get("tem_3_estrelas_brasil_0900") else "🟢 LIBERADO"
        st.markdown(f"""
        <div class="stat-box">
            <div class="number" style="font-size:1.5rem;">{status_brasil}</div>
            <div class="label">Alerta Brasil 09:00</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ============================================================
    # 2. FILTROS
    # ============================================================
    st.subheader("🔍 Filtros")

    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filtro_moeda = st.multiselect(
            "Moeda",
            options=sorted(list(set(e.get("moeda", "") for e in eventos_completos))),
            default=sorted(list(set(e.get("moeda", "") for e in eventos_completos))),
        )
    
    with col_f2:
        filtro_estrelas = st.multiselect(
            "Impacto (Estrelas)",
            options=[2, 3],
            default=[2, 3],
            format_func=lambda x: f"{x}★ {('Alto' if x==3 else 'Médio')}",
        )
    
    with col_f3:
        filtro_hora = st.multiselect(
            "Horário",
            options=sorted(list(set(e.get("hora", "") for e in eventos_completos if e.get("hora")))),
            default=sorted(list(set(e.get("hora", "") for e in eventos_completos if e.get("hora")))),
        )

    # Aplica filtros
    eventos_filtrados = []
    for ev in eventos_completos:
        moeda = ev.get("moeda", "")
        estrelas = ev.get("importancia", 0)
        hora = ev.get("hora", "")
        
        if moeda in filtro_moeda and estrelas in filtro_estrelas and hora in filtro_hora:
            eventos_filtrados.append(ev)

    st.markdown("---")

    # ============================================================
    # 3. ANÁLISE IA DAS NOTÍCIAS
    # ============================================================
    st.subheader("🧠 Análise IA - Impacto no WIN")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(BASE_DIR, ".env"))
            groq_key = os.getenv("GROQ_API_KEY", "")
        except Exception:
            pass

    with st.expander("⚙️ Configurações IA", expanded=not bool(groq_key)):
        groq_key_input = st.text_input(
            "Groq API Key",
            type="password",
            value=groq_key,
            help="Obtenha em https://console.groq.com",
            key="groq_key_noticias"
        )

    if st.button("📊 Analisar Notícias com IA", type="primary"):
        key_final = groq_key_input or groq_key
        if not key_final:
            st.error("⚠️ Informe a Groq API Key")
        else:
            with st.spinner("🧠 Analisando impacto das notícias no WIN..."):
                try:
                    resposta = analisar_noticias_com_ia(key_final, eventos_filtrados)
                    st.markdown(f"""
                    <div class="card-ai">
                        <h4>🤖 Análise IA - Impacto no WIN</h4>
                        <div style="color:#c9d1d9; font-size:0.95rem; line-height:1.6;">
                            {resposta.replace(chr(10), '<br>')}
                        </div>
                        <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
                            <span class="smc-tag">📊 Notícias</span>
                            <span class="smc-tag">🎯 WIN</span>
                            <span class="smc-tag">📈 Macro</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Erro: {e}")

    st.markdown("---")

    # ============================================================
    # 4. CARDS DAS NOTÍCIAS
    # ============================================================
    st.subheader(f"📰 Notícias do Dia ({len(eventos_filtrados)} eventos)")

    if not eventos_filtrados:
        st.info("📭 Nenhuma notícia encontrada para os filtros selecionados.")
        return

    # Grid de Cards (2 por linha)
    cols = st.columns(2)
    card_idx = 0

    for ev in eventos_filtrados:
        moeda = ev.get("moeda", "")
        estrelas = ev.get("importancia", 0)
        hora = ev.get("hora", "")
        evento = ev.get("evento", "")
        pais = ev.get("pais", "")
        anterior = ev.get("anterior", "N/A")
        previsao = ev.get("previsao", "N/A")
        atual = ev.get("atual", "")

        col_atual = cols[card_idx % 2]
        card_idx += 1

        # Define classe do card baseado no impacto
        if estrelas == 3:
            classe_card = "card-impacto-alto"
            badge = '<span class="badge-impacto alto">🔴 3★ ALTO IMPACTO</span>'
            emoji_pais = "🇧🇷" if moeda == "BRL" else "🇺🇸"
        else:
            classe_card = "card-impacto-medio"
            badge = '<span class="badge-impacto medio">🟡 2★ MÉDIO IMPACTO</span>'
            emoji_pais = "🇧🇷" if moeda == "BRL" else "🇺🇸"

        with col_atual:
            st.markdown(f"""
            <div class="{classe_card}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-weight:700; font-size:1.1rem;">{emoji_pais} {hora} — {moeda}</span>
                    {badge}
                </div>
                <div style="font-size:1rem; color:#e6edf3; margin-bottom:8px;">
                    <strong>{evento}</strong>
                </div>
                <div style="display:flex; gap:20px; font-size:0.9rem; color:#8b949e;">
                    <div><span style="color:#8b949e;">Anterior:</span> <strong style="color:#e6edf3;">{anterior}</strong></div>
                    <div><span style="color:#8b949e;">Previsão:</span> <strong style="color:#e6edf3;">{previsao}</strong></div>
                    <div><span style="color:#8b949e;">Atual:</span> <strong style="color:{'#00c853' if atual else '#ffc107'};">{atual if atual else '⏳ Pendente'}</strong></div>
                </div>
                <div style="margin-top:6px; font-size:0.75rem; color:#6e7681;">
                    {pais}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ============================================================
    # 5. TABELA RESUMO
    # ============================================================
    with st.expander("📋 Ver tabela completa de eventos"):
        if eventos_filtrados:
            df = pd.DataFrame(eventos_filtrados)
            df = df[["hora", "pais", "moeda", "evento", "importancia", "anterior", "previsao", "atual"]]
            df.columns = ["Hora", "País", "Moeda", "Evento", "★", "Anterior", "Previsão", "Atual"]
            st.dataframe(df, width="stretch", hide_index=True)

    # ============================================================
    # 6. ALERTAS DETALHADOS
    # ============================================================
    st.markdown("---")
    st.subheader("⚠️ Alertas do Dia")

    alertas_lista = []
    
    if alertas.get("tem_3_estrelas_brasil_0900"):
        alertas_lista.append("🚨 **Notícia ⭐⭐⭐ no Brasil às 09:00!** Volatilidade na abertura do WIN.")
    
    if alertas.get("tem_3_estrelas_outros_horarios"):
        noticias_3 = alertas.get("noticias_3_estrelas_outros_horarios", [])
        for n in noticias_3:
            alertas_lista.append(f"⚠️ **{n.get('hora', '')}** | {n.get('pais', '')} | {n.get('evento', '')} (⭐⭐⭐)")
    
    if alertas.get("tem_multiplas_2_estrelas_mesmo_horario"):
        horarios = alertas.get("horarios_multiplas_2_estrelas", [])
        for h in horarios:
            alertas_lista.append(f"🟡 **{h.get('hora', '')}** | {h.get('quantidade_2_estrelas', 0)} notícias ⭐⭐ no mesmo horário")

    if not alertas_lista:
        st.success("✅ Nenhum alerta crítico hoje. Mercado deve operar com tranquilidade.")
    else:
        for alerta in alertas_lista:
            st.warning(alerta)

# ============================================================
# EXECUTA O DASHBOARD
# ============================================================

renderizar_dashboard()