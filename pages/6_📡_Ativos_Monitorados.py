# -*- coding: utf-8 -*-
"""
Módulo: pages/5.0_📡_Ativos_Monitorados.py
Versão: 2.1 - Otimizado para Produção V2 + Termômetro por Categoria
Objetivo: Dashboard de integridade e monitoramento dos 32 ativos validados do ecossistema.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from datetime import datetime

# Importações de caminhos padronizados e tabelas do config.py da V2
from config import FILE_VALIDADOS, id_interno


# ==============================================================================
# MINI VELOCÍMETRO (centro em zero, estilo flat design)
# ==============================================================================
def mini_velocimetro(valor, label: str, preco_fmt: str = "", inverter: bool = False) -> None:
    """
    Mini velocímetro compacto com centro em zero.
    - Positivo → ponteiro à direita, cor verde
    - Negativo → ponteiro à esquerda, cor vermelha
    - Neutro   → ponteiro ao centro, cor amarela
    - Escala fixa: ±10% (satura além disso)
    """
    if valor is None:
        real_exibicao = 0.0
        cor = "#8b949e"
        texto_valor = "—"
    else:
        try:
            real_exibicao = max(-10.0, min(10.0, float(valor)))
        except (TypeError, ValueError):
            real_exibicao = 0.0
        real_cor = -real_exibicao if inverter else real_exibicao
        if real_cor > 0.05:
            cor = "#00cc44"
        elif real_cor < -0.05:
            cor = "#ff4b4b"
        else:
            cor = "#ffa500"
        texto_valor = f"{real_exibicao:+.2f}%"

    angulo = (real_exibicao / 10.0) * 90.0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        html, body {{
            margin: 0; padding: 0; background: transparent;
            font-family: Arial, sans-serif;
            color: #e6edf3;
            overflow: hidden;
        }}
        .mini-wrap {{
            display: flex; flex-direction: column; align-items: center;
            padding: 2px 0;
        }}
        .mini-label {{
            font-size: 11px;
            color: #c9d1d9;
            margin-bottom: 1px;
            text-align: center;
            font-weight: 700;
            white-space: nowrap;
        }}
        .mini-gauge {{
            position: relative;
            width: 120px;
            height: 62px;
        }}
        .mini-arc {{
            position: absolute; left: 5px; top: 3px;
            width: 110px; height: 55px;
            border-radius: 110px 110px 0 0;
            background: conic-gradient(
                from 270deg at 50% 100%,
                #ff2020 0deg 30deg,
                #b02020 30deg 60deg,
                #602020 60deg 90deg,
                #206020 90deg 120deg,
                #00a030 120deg 150deg,
                #00cc44 150deg 180deg
            );
            -webkit-mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
                    mask: radial-gradient(circle at 50% 100%, transparent 34px, black 35px);
        }}
        .mini-needle {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 8px;
            height: 52px;
            margin-left: -4px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 3;
        }}
        .mini-pivot {{
            position: absolute;
            left: 50%;
            bottom: 0px;
            width: 12px; height: 12px;
            margin-left: -6px;
            border-radius: 50%;
            background: {cor};
            z-index: 4;
            transition: background 0.5s ease;
        }}
        .mini-value {{
            font-size: 14px;
            font-weight: 900;
            color: {cor};
            text-align: center;
            margin-top: 1px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
        }}
        .mini-sub {{
            font-size: 10px;
            color: #8b949e;
            text-align: center;
            margin-top: -1px;
        }}
    </style>
    </head>
    <body>
        <div class="mini-wrap">
            <div class="mini-label">{label}</div>
            <div class="mini-gauge">
                <div class="mini-arc"></div>
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 52">
                    <path d="M 4 0 L 5.5 46 L 2.5 46 Z" fill="#ffffff"/>
                </svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-sub">{preco_fmt}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=125, scrolling=False)


def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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


# ==============================================================================
# TERMÔMETRO POR CATEGORIA (nova seção)
# ==============================================================================
def calcular_media_categoria(ids_categoria, ativos, ignorar_invertidos=False):
    """
    Calcula a média das variações % dos ativos de uma categoria.
    Se ignorar_invertidos=True, descarta VIX e DXY (que têm semântica inversa).
    Retorna (media, quantidade).
    """
    if ignorar_invertidos:
        ids_excluir = {"VIX", "DXY"}
        ids_categoria = [x for x in ids_categoria if x not in ids_excluir]

    variacoes = []
    for ativo in ativos:
        if ativo.get("ativo_id") in ids_categoria:
            v = ativo.get("change_percent")
            if v is not None:
                try:
                    variacoes.append(float(v))
                except (TypeError, ValueError):
                    pass
    if not variacoes:
        return None, 0
    return sum(variacoes) / len(variacoes), len(variacoes)


st.markdown("### 🌡️ Termômetro de Sentimento por Categoria")
st.caption(
    "Variação média dos ativos de cada grupo · 🟢 verde = favorável · 🔴 vermelho = pressão · "
    "⚠️ VIX/DXY excluídos da média (têm semântica inversa)"
)

cols_cat = st.columns(5)

# Ordem dos mini velocímetros (mesma ordem das tabs)
ordem_categorias = list(categorias.keys())

for idx, nome_cat in enumerate(ordem_categorias):
    ids_cat = categorias[nome_cat]

    # Drivers Globais: ignora VIX e DXY na média (são inversos)
    ign_inv = "Drivers Globais" in nome_cat

    media, qtd = calcular_media_categoria(ids_cat, ativos_lista, ignorar_invertidos=ign_inv)

    # Encurta o nome da categoria para caber no mini velocímetro
    nome_curto = nome_cat.split(" ", 1)[1] if " " in nome_cat else nome_cat
    nome_curto = nome_curto.replace("(", "").replace(")", "").strip()
    # Corta ainda mais para caber
    nome_curto = nome_curto[:18]

    with cols_cat[idx]:
        mini_velocimetro(
            media,
            nome_curto,
            f"{qtd} ativos" if qtd > 0 else "sem dados",
            inverter=False,
        )

st.markdown("---")


# ==============================================================================
# RENDERIZAÇÃO DAS SUB-ABAS POR CATEGORIA
# ==============================================================================
abas_nomes = list(categorias.keys())
abas = st.tabs(abas_nomes)

for idx_aba, nome_aba in enumerate(abas_nomes):
    with abas[idx_aba]:
        ids_categoria = categorias[nome_aba]
        linhas_categoria = []
        variacoes_para_velocimetro = []  # (label, valor, formatado)

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

                # Guarda para mini velocímetro (se tiver variação válida)
                if var_pct is not None:
                    try:
                        variacoes_para_velocimetro.append({
                            "label": ativo.get("ativo_id", "?"),
                            "valor": float(var_pct),
                        })
                    except (TypeError, ValueError):
                        pass

        # ---------- MINI VELOCÍMETROS POR ATIVO (dentro da aba) ----------
        if variacoes_para_velocimetro:
            st.markdown("##### 📊 Sentimento por Ativo")
            n_cols = min(len(variacoes_para_velocimetro), 6)
            cols_ativo = st.columns(n_cols)

            # Ordena por magnitude (maiores oscilações primeiro)
            variacoes_para_velocimetro.sort(key=lambda x: abs(x["valor"]), reverse=True)

            for idx_a, item in enumerate(variacoes_para_velocimetro[:6]):
                # Inverte VIX e DXY (subir = ruim = vermelho)
                ign_inv = item["label"] in ("VIX", "DXY")
                with cols_ativo[idx_a % n_cols]:
                    mini_velocimetro(
                        item["valor"],
                        item["label"],
                        f"{item['valor']:+.2f}%",
                        inverter=ign_inv,
                    )

            st.markdown("")  # espaço

        # ---------- TABELA DE DADOS ----------
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