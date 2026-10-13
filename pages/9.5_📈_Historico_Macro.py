# -*- coding: utf-8 -*-
"""
Módulo: pages/9.5_📈_Historico_Macro.py
Versão: 2.1 - Dashboard analítico de série temporal e histórico macro/operacional do WIN.
"""

import json
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import HISTORICO_ABERTURAS_DIR


# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - Histórico Macro", layout="wide")


# ==============================================================================
# CORES (semântica visual)
# ==============================================================================
VERDE = "#22c55e"
VERMELHO = "#ef4444"
CINZA = "#8b949e"
BRANCO = "#e6edf3"
AMARELO = "#fbbf24"


def _cor_direcao(direcao: str) -> str:
    s = str(direcao or "").upper()
    if "ALTA" in s or "COMPRA" in s or "BULL" in s:
        return VERDE
    if "BAIXA" in s or "VENDA" in s or "BEAR" in s:
        return VERMELHO
    return CINZA


# ==============================================================================
# LOADER
# ==============================================================================
def carregar_json_defensivo(caminho_path):
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ==============================================================================
# CABEÇALHO
# ==============================================================================
st.markdown("<h2 style='color:#00d4ff;'>📊 Série Temporal e Histórico Macro Operacional</h2>", unsafe_allow_html=True)
st.caption("Análise estatística retroativa dos fechamentos, ajustes e cenários gravados pelo ecossistema V2")


# ==============================================================================
# FRAGMENT — DASHBOARD
# ==============================================================================
@st.fragment(run_every=300)
def _render_historico():
    # ---- Checagens defensivas ----
    if not HISTORICO_ABERTURAS_DIR.exists():
        st.warning(
            "⚠️ Diretório de histórico de aberturas V2 não encontrado no disco local. "
            "Aguardando primeiras gravações do pregão."
        )
        return

    arquivos_historicos = sorted(list(HISTORICO_ABERTURAS_DIR.glob("*.json")))

    if not arquivos_historicos:
        st.info("ℹ️ Nenhuma sessão diária imutável foi persistida na pasta Historico_Aberturas/ ainda.")
        return

    # ---- Processamento em lote ----
    linhas_serie = []

    for caminho in arquivos_historicos:
        data_sessao = caminho.stem  # ex: 2026-08-30
        dados_dia = carregar_json_defensivo(caminho)
        atualizacoes = dados_dia.get("atualizacoes", [])

        if atualizacoes and isinstance(atualizacoes, list):
            ultimo_snapshot = atualizacoes[-1]

            precos = ultimo_snapshot.get("precos", {})
            distancias = ultimo_snapshot.get("distancias", {})
            cenario = ultimo_snapshot.get("cenario", {})
            contexto = ultimo_snapshot.get("contexto", {})

            linhas_serie.append({
                "Data Sessão": data_sessao,
                "Contrato Principal": ultimo_snapshot.get("metadata", {}).get("contrato_principal", "WIN"),
                "Preço Ajuste B3": precos.get("ajuste"),
                "Último MT5 (Last)": precos.get("last_mt5"),
                "Desvio Ajuste (Pts)": distancias.get("last_vs_ajuste_pts"),
                "VIX (Volatilidade)": contexto.get("vix", {}).get("preco"),
                "Direção Cenário": cenario.get("direcao_provavel", "NEUTRO"),
                "Confiança (%)": cenario.get("confianca_geral", 0.0),
            })

    if not linhas_serie:
        st.info("ℹ️ Sessões encontradas, mas nenhuma possui snapshots válidos.")
        return

    df_historico = pd.DataFrame(linhas_serie).sort_values(by="Data Sessão", ascending=False)

    # =========================================================================
    # KPIs NO TOPO
    # =========================================================================
    total_sessoes = len(df_historico)
    ultima = df_historico.iloc[0]
    ultima_data = ultima["Data Sessão"]
    ultima_direcao = ultima.get("Direção Cenário") or "—"
    ultima_conf = ultima.get("Confiança (%)")

    # Desvio médio (últimos 5 dias úteis)
    ult5 = df_historico.head(5)
    desvios = pd.to_numeric(ult5["Desvio Ajuste (Pts)"], errors="coerce").dropna()
    desvio_medio = round(desvios.mean(), 0) if not desvios.empty else None

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("📁 Total de Sessões", f"{total_sessoes}")
    with k2:
        st.metric("📅 Última Sessão", ultima_data)
    with k3:
        conf_txt = f"{ultima_conf:.0f}% conf." if ultima_conf is not None else "sem conf."
        st.markdown(
            f"<div style='padding:6px 0;'>"
            f"<div style='font-size:0.9rem; color:#8b949e;'>🎯 Viés da Última</div>"
            f"<div style='font-size:1.9rem; font-weight:700; "
            f"color:{_cor_direcao(ultima_direcao)}; line-height:1.1;'>{ultima_direcao}</div>"
            f"<div style='font-size:0.85rem; color:#8b949e;'>{conf_txt}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with k4:
        st.metric(
            "📏 Desvio Médio (últimos 5)",
            f"{desvio_medio:+,.0f} pts" if desvio_medio is not None else "—",
        )

    st.markdown("---")

    # =========================================================================
    # GRÁFICO — Last vs Ajuste
    # =========================================================================
    st.markdown("### 📉 Curva Comparativa: Preço Last vs Ajuste Oficial B3")
    st.caption("Comportamento histórico e fechamento de spreads institucionais ao longo das sessões")

    df_grafico = df_historico.sort_values(by="Data Sessão", ascending=True)

    if not df_grafico.empty and df_grafico["Preço Ajuste B3"].notna().any():
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_grafico["Data Sessão"],
            y=df_grafico["Preço Ajuste B3"],
            mode="lines+markers",
            name="Preço de Ajuste Oficial B3",
            line=dict(color="orange", width=2),
        ))

        fig.add_trace(go.Scatter(
            x=df_grafico["Data Sessão"],
            y=df_grafico["Último MT5 (Last)"],
            mode="lines+markers",
            name="Último Tick MetaTrader 5 (Last)",
            line=dict(color="#00d4ff", width=2, dash="dash"),
        ))

        fig.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Aguardando mais pontos históricos para plotar as curvas de tendência.")

    st.markdown("---")

    # =========================================================================
    # TABELA CONSOLIDADA (com cores na direção)
    # =========================================================================
    st.markdown("### 📋 Histórico Consolidado de Snapshots da Mesa")
    st.caption("Grade analítica com todas as variáveis gravadas em background pelo pipeline")

    df_show = df_historico.set_index("Data Sessão")

    # Estilização: direção colorida
    def _estilizar(row):
        estilos = [''] * len(row)
        for i, col in enumerate(row.index):
            if col == "Direção Cenário":
                estilos[i] = f"color: {_cor_direcao(row[col])}; font-weight: 700;"
        return estilos

    df_style = df_show.style.apply(_estilizar, axis=1).format({
        "Preço Ajuste B3": "{:,.0f}",
        "Último MT5 (Last)": "{:,.0f}",
        "Desvio Ajuste (Pts)": "{:+,.0f}",
        "VIX (Volatilidade)": "{:,.2f}",
        "Confiança (%)": "{:.0f}%",
    }, na_rep="—")

    st.dataframe(df_style, use_container_width=True)

    # =========================================================================
    # RODAPÉ
    # =========================================================================
    st.markdown("---")
    st.caption(
        "🔒 Módulo de inteligência histórica ativo — Em conformidade com o ecossistema de "
        "armazenamento imutável V2 · atualiza a cada 300s"
    )


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
_render_historico()