# -*- coding: utf-8 -*-
"""
Módulo: pages/6_📡_Ativos_Monitorados.py
Versão: 2.3 - Fix race condition (rom-0 como fonte do "atual") + cosméticos
Objetivo: Dashboard de integridade e monitoramento dos 32 ativos validados do ecossistema.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import pandas as pd
from datetime import datetime

from config import FILE_VALIDADOS, COLETAS_DIR


# ==============================================================================
# MAPA TICKERS ROM-5 (canônico — idêntico às pages 2, 3 e 4)
# ==============================================================================
MAPA_TICKERS_ROM5 = {
    "SP500_FUT": "CME_MINI:ES1!",
    "NASDAQ_FUT": "CME_MINI:NQ1!",
    "VIX": "TVC:VIX",
    "DXY": "TVC:DXY",
    "USD_MXN": "FX_IDC:USDMXN",
    "CRUDE_OIL": "NYMEX:CL1!",
    "IRON_ORE": "SGX:FEF1!",
    "IRON_ORE_2M": "SGX:FEF2!",
    "GOLD": "TVC:GOLD",
    "EWZ": "AMEX:EWZ",
    "VALE_ADR": "NYSE:VALE",
    "PETR_ADR": "NYSE:PBR",
    "ITUB_ADR": "NYSE:ITUB",
    "BBAS_ADR": "OTC:BDORY",
    "BBD_ADR": "NYSE:BBD",
    "B3_ADR": "OTC:BOLSY",
    "WIN_AJUSTE": "B3_AJUSTE_WIN",
    "WDO_AJUSTE": "B3_AJUSTE_WDO",
    "WIN_FUT": "BMFBOVESPA:WIN1!",
    "WDO_FUT": "BMFBOVESPA:WDO1!",
    "WIN_LAST_TICK": "WIN_LAST_TICK",
    "WDO_LAST_TICK": "WDO_LAST_TICK",
    "DI1_2027": "BMFBOVESPA:DI1F2027",
    "DI1_2029": "BMFBOVESPA:DI1F2029",
    "VALE3": "VALE3",
    "PETR4": "PETR4",
    "ITUB4": "ITUB4",
    "BBAS3": "BBAS3",
    "BBDC4": "BBDC4",
    "B3SA3": "B3SA3",
}


# Nomes curtos (fix do corte [:18])
NOMES_CURTOS = {
    "🇧🇷 Mercado Local (Futuros B3)": "🏦 B3 Futuros",
    "🇺🇸 Drivers Globais & Risco": "🌍 Drivers",
    "🪵 Commodities Cíclicas": "🪵 Commodities",
    "📈 ADRs Brasileiras (Sentiment NY)": "🇧🇷 ADRs NY",
    "🏦 Mercado à Vista (Ações Locais)": "📊 À Vista",
}


# ==============================================================================
# MINI VELOCÍMETRO (padrão consolidado das páginas 2/3/4)
# ==============================================================================
def mini_velocimetro(
    valor,
    label: str,
    preco_fmt: str = "",
    inverter: bool = False,
    valor_anterior=None,
) -> None:
    # ---------- Valor ATUAL ----------
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

    # ---------- Valor ANTERIOR ----------
    tem_anterior = False
    angulo_anterior = 0.0
    if valor_anterior is not None:
        try:
            ant_exibicao = max(-10.0, min(10.0, float(valor_anterior)))
            angulo_anterior = (ant_exibicao / 10.0) * 90.0
            tem_anterior = True
        except (TypeError, ValueError):
            tem_anterior = False

    # ---------- Δ ----------
    # Threshold cosmético: 0.005 evita "Δ +0.00%" verde que parece bug
    if valor is not None and valor_anterior is not None:
        try:
            delta = float(valor) - float(valor_anterior)
            if abs(delta) < 0.005:
                cor_delta = "#8b949e"
                texto_delta = "Δ 0,00%"
            else:
                delta_real = -delta if inverter else delta
                if delta_real > 0.005:
                    cor_delta = "#00cc44"
                elif delta_real < -0.005:
                    cor_delta = "#ff4b4b"
                else:
                    cor_delta = "#8b949e"
                texto_delta = f"Δ {delta:+.2f}%"
        except (TypeError, ValueError):
            cor_delta = "#8b949e"
            texto_delta = "Δ —"
    else:
        cor_delta = "#8b949e"
        texto_delta = "Δ —"

    # ---------- SVG do ponteiro anterior ----------
    if tem_anterior:
        svg_anterior = (
            f'<svg class="mini-needle-ant" '
            f'style="transform: rotate({angulo_anterior}deg);" '
            f'viewBox="0 0 14 52">'
            f'<path d="M 7 0 L 9.5 46 L 4.5 46 Z" '
            f'fill="rgba(220, 220, 255, 0.85)"/>'
            f'</svg>'
        )
    else:
        svg_anterior = ""

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
        .mini-needle-ant {{
            position: absolute;
            left: 50%;
            bottom: 3px;
            width: 14px;
            height: 48px;
            margin-left: -7px;
            transform-origin: 50% 100%;
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 2;
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
            margin-top: 4px;
            transition: color 0.5s ease;
            letter-spacing: 0.3px;
            line-height: 1.1;
        }}
        .mini-delta {{
            font-size: 10px;
            font-weight: 700;
            color: {cor_delta};
            text-align: center;
            margin-top: 3px;
            letter-spacing: 0.2px;
            opacity: 0.9;
            line-height: 1.1;
        }}
        .mini-sub {{
            font-size: 10px;
            color: #8b949e;
            text-align: center;
            margin-top: 2px;
            line-height: 1.1;
        }}
    </style>
    </head>
    <body>
        <div class="mini-wrap">
            <div class="mini-label">{label}</div>
            <div class="mini-gauge">
                <div class="mini-arc"></div>
                {svg_anterior}
                <svg class="mini-needle" style="transform: rotate({angulo}deg);" viewBox="0 0 8 52">
                    <path d="M 4 0 L 5.5 46 L 2.5 46 Z" fill="#ffffff"/>
                </svg>
                <div class="mini-pivot"></div>
            </div>
            <div class="mini-value">{texto_valor}</div>
            <div class="mini-delta">{texto_delta}</div>
            <div class="mini-sub">{preco_fmt}</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=155, scrolling=False)


# ==============================================================================
# LOADERS DEFENSIVOS
# ==============================================================================
def carregar_json_defensivo(caminho):
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def carregar_rom_dict(nome_arquivo: str) -> dict:
    """
    Lê um Coleta_rom-X.json e devolve {ticker_rom5: change_percent}.
    Suporta formato {"coletas": [...]}.
    """
    caminho = COLETAS_DIR / nome_arquivo
    dados = carregar_json_defensivo(caminho)
    resultado: dict = {}

    if isinstance(dados, dict):
        coletas = dados.get("coletas")
        if isinstance(coletas, list):
            for item in coletas:
                if not isinstance(item, dict):
                    continue
                ativo_key = item.get("ativo")
                if not ativo_key:
                    continue
                dados_reais = item.get("dados_reais") or {}
                cp = dados_reais.get("change_percent")
                if cp is None:
                    continue
                try:
                    resultado[ativo_key] = float(cp)
                except (TypeError, ValueError):
                    continue
    return resultado


def buscar_valor(ativo_id: str, rom_dict: dict):
    """Traduz ativo_id interno → ticker rom → change_percent."""
    ticker = MAPA_TICKERS_ROM5.get(ativo_id)
    if not ticker:
        return None
    return rom_dict.get(ticker)


# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Quant Terminal - Ativos Monitorados", layout="wide")


# ==============================================================================
# CATEGORIAS OPERACIONAIS
# ==============================================================================
CATEGORIAS = {
    "🇧🇷 Mercado Local (Futuros B3)": ["WIN_AJUSTE", "WDO_AJUSTE", "WIN_FUT", "WDO_FUT", "DI1_2027", "DI1_2029"],
    "🇺🇸 Drivers Globais & Risco": ["VIX", "SP500_FUT", "NASDAQ_FUT", "DXY", "USD_MXN"],
    "🪵 Commodities Cíclicas": ["IRON_ORE", "IRON_ORE_2M", "CRUDE_OIL", "GOLD"],
    "📈 ADRs Brasileiras (Sentiment NY)": ["EWZ", "VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"],
    "🏦 Mercado à Vista (Ações Locais)": ["VALE3", "PETR4", "ITUB4", "BBAS3", "BBDC4", "B3SA3"],
}


def calcular_media_categoria(ids_categoria, ativos_validados, rom_dict, ignorar_invertidos=False, usar_rom=False):
    """
    Média das variações % da categoria.
    Se usar_rom=True → lê de rom_dict (atual ou anterior).
    Se usar_rom=False → lê de ativos_validados (Dados_Validados).
    """
    if ignorar_invertidos:
        ids_excluir = {"VIX", "DXY"}
        ids_categoria = [x for x in ids_categoria if x not in ids_excluir]

    variacoes = []
    if usar_rom:
        for ativo_id in ids_categoria:
            v = buscar_valor(ativo_id, rom_dict)
            if v is not None:
                variacoes.append(v)
    else:
        for ativo in ativos_validados:
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


# ==============================================================================
# CORPO (auto-refresh a cada 60s)
# ==============================================================================
@st.fragment(run_every=60)
def render_body():
    # --- CARGA DOS DADOS (DENTRO do fragment!) ---
    payload_validado = carregar_json_defensivo(FILE_VALIDADOS)
    rom0_dict = carregar_rom_dict("Coleta_rom-0.json")   # ATUAL (fix race)
    rom5_dict = carregar_rom_dict("Coleta_rom-5.json")   # 5min atrás

    # --- CABEÇALHO ---
    st.markdown(
        "<h2 style='color:#00d4ff;'>📡 Status e Integridade de Ativos Monitorados</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Central de Auditoria · Cruzamento Multimercados · "
        f"🔄 {datetime.now().strftime('%H:%M:%S')} · "
        f"⚪ ponteiro branco = 5 min atrás (rom-0: {len(rom0_dict)} · rom-5: {len(rom5_dict)})"
    )

    if not payload_validado:
        st.warning(
            "⚠️ Arquivo de dados validados não encontrado. "
            "Certifique-se de que a etapa de validação (Validador.py) rodou no pipeline."
        )
        st.stop()

    metadata = payload_validado.get("metadata_validacao", {})
    total_recebidos = metadata.get("total_recebidos", 0)
    total_aprovados = metadata.get("total_aprovados", 0)
    total_rejeitados = metadata.get("total_rejeitados", 0)

    # --- KPIs DE SAÚDE DOS DADOS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Carga Útil Recebida", f"{total_recebidos} ativos")
    c2.metric(
        "Aprovados pelo Validador",
        f"{total_aprovados} OK",
        delta=f"{total_aprovados/total_recebidos*100:.1f}% Eficiência" if total_recebidos > 0 else "0%",
    )

    if total_rejeitados > 0:
        c3.metric("Ativos Rejeitados / Falhas", f"{total_rejeitados} Erros",
                  delta="- Problema na API", delta_color="inverse")
    else:
        c3.metric("Ativos Rejeitados / Falhas", "0 Erros",
                  delta="Estabilidade 100%", delta_color="normal")

    c4.markdown(
        f"<div style='background-color:#161b24; padding:10px; border-radius:8px; "
        f"border:1px solid #2a3a4a; height:100%; text-align:center;'>"
        f"<span style='font-size:0.85rem; color:#8b949e;'>ÚLTIMA AUDITORIA V2</span><br>"
        f"<span style='font-size:1.25rem; font-weight:bold; color:#00ff88;'>"
        f"{datetime.fromisoformat(metadata.get('timestamp_validacao', datetime.now().isoformat())).strftime('%H:%M:%S')}"
        f"</span></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    ativos_lista = payload_validado.get("ativos_validados", [])
    ordem_categorias = list(CATEGORIAS.keys())

    # ==========================================================================
    # TERMÔMETRO POR CATEGORIA
    # ✅ Agora usa rom-0 (atual) vs rom-5 (anterior) — sem race
    # ==========================================================================
    st.markdown("### 🌡️ Termômetro de Sentimento por Categoria")
    st.caption(
        "Variação média dos ativos de cada grupo · 🟢 verde = favorável · 🔴 vermelho = pressão · "
        "⚪ ponteiro branco = média de 5 min atrás · ⚠️ VIX/DXY excluídos (semântica inversa)"
    )

    cols_cat = st.columns(5)

    for idx, nome_cat in enumerate(ordem_categorias):
        ids_cat = CATEGORIAS[nome_cat]
        ign_inv = "Drivers Globais" in nome_cat

        # ✅ Atual = rom-0 (fix race). Fallback p/ Dados_Validados se rom-0 vazio
        media, qtd = calcular_media_categoria(
            ids_cat, ativos_lista, rom0_dict,
            ignorar_invertidos=ign_inv, usar_rom=True,
        )
        if media is None:
            media, qtd = calcular_media_categoria(
                ids_cat, ativos_lista, rom0_dict,
                ignorar_invertidos=ign_inv, usar_rom=False,
            )

        # ✅ Anterior = rom-5
        media_ant, _ = calcular_media_categoria(
            ids_cat, ativos_lista, rom5_dict,
            ignorar_invertidos=ign_inv, usar_rom=True,
        )

        nome_curto = NOMES_CURTOS.get(nome_cat, nome_cat[:16])

        with cols_cat[idx]:
            mini_velocimetro(
                media,
                nome_curto,
                f"{qtd} ativos" if qtd > 0 else "sem dados",
                inverter=False,
                valor_anterior=media_ant,
            )

    st.markdown("---")

    # ==========================================================================
    # SUB-ABAS POR CATEGORIA
    # ==========================================================================
    abas_nomes = list(CATEGORIAS.keys())
    abas = st.tabs(abas_nomes)

    for idx_aba, nome_aba in enumerate(abas_nomes):
        with abas[idx_aba]:
            ids_categoria = CATEGORIAS[nome_aba]
            linhas_categoria = []
            variacoes_para_velocimetro = []

            for ativo in ativos_lista:
                if ativo.get("ativo_id") not in ids_categoria:
                    continue

                ativo_id = ativo.get("ativo_id")
                var_pct = ativo.get("change_percent")
                var_txt = f"{var_pct:+.2f}%" if var_pct is not None else "—"
                vol = ativo.get("volume")
                vol_txt = f"{vol:,.0f}" if vol is not None else "—"

                linhas_categoria.append({
                    "Identificador V2": ativo_id,
                    "Ticker Original": ativo.get("ticker_original"),
                    "Preço / Taxa": (
                        f"{ativo.get('close'):,.4f}" if ativo.get("close", 0) < 100
                        else f"{ativo.get('close'):,.2f}"
                    ),
                    "Variação Diária": var_txt,
                    "Volume Turn": vol_txt,
                    "Fonte de Coleta": ativo.get("fonte", "N/A"),
                    "Timestamp": (
                        ativo.get("timestamp_coleta", "N/A")[-14:-5]
                        if "T" in str(ativo.get("timestamp_coleta"))
                        else "N/A"
                    ),
                })

                # ✅ Gauge por ativo: atual = rom-0, anterior = rom-5
                # Fallback para o valor de Dados_Validados se rom-0 não tiver
                v_atual = buscar_valor(ativo_id, rom0_dict)
                if v_atual is None:
                    try:
                        v_atual = float(var_pct) if var_pct is not None else None
                    except (TypeError, ValueError):
                        v_atual = None

                if v_atual is not None:
                    v_ant = buscar_valor(ativo_id, rom5_dict)
                    variacoes_para_velocimetro.append({
                        "label": ativo_id,
                        "valor": v_atual,
                        "valor_anterior": v_ant,
                    })

            # -------- MINI VELOCÍMETROS POR ATIVO --------
            if variacoes_para_velocimetro:
                st.markdown("##### 📊 Sentimento por Ativo")
                variacoes_para_velocimetro.sort(key=lambda x: abs(x["valor"]), reverse=True)

                top = variacoes_para_velocimetro[:6]
                n_cols = min(len(top), 6)
                cols_ativo = st.columns(n_cols)

                for idx_a, item in enumerate(top):
                    inv = item["label"] in ("VIX", "DXY")
                    with cols_ativo[idx_a % n_cols]:
                        mini_velocimetro(
                            item["valor"],
                            item["label"],
                            f"{item['valor']:+.2f}%",
                            inverter=inv,
                            valor_anterior=item["valor_anterior"],
                        )

                st.markdown("")

            # -------- TABELA DE DADOS (segue usando Dados_Validados) --------
            if linhas_categoria:
                df_cat = pd.DataFrame(linhas_categoria)
                st.dataframe(df_cat.set_index("Identificador V2"), use_container_width=True)
            else:
                st.caption("ℹ️ Nenhum ativo desta categoria foi processado nesta janela de execução.")

    # --- RELATÓRIO DE REJEIÇÕES ---
    rejeicoes = payload_validado.get("relatorio_rejeicoes", [])
    if rejeicoes:
        st.markdown("### 🚨 Relatório de Ativos Rejeitados / Fora do Ar")
        st.warning(
            "Os ativos abaixo falharam nos testes estritos de integridade quantitativa. "
            "O orquestrador isolou esses campos para proteger a pontuação final de viés."
        )
        st.table(pd.DataFrame(rejeicoes))


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
render_body()