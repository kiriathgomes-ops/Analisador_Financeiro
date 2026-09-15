# ============================================================
# pages/1_⚡_Dashboard_Leilao_AoVivo.py
# Dashboard de Leilão Ao Vivo — V2
#
# Mostra LADO A LADO:
#   - Abertura Teórica CALCULADA (CalculadoraEstimativaAbertura)
#   - Abertura do LEILÃO (OCR via LeilaoService)
#
# Contexto macro + SMC + veredito operacional.
# ============================================================

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Leilão Ao Vivo",
    page_icon="⚡",
    layout="wide",
)

# Caminhos
BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_COLETAS = BASE_DIR / "Coletas"

ARQUIVO_CSV = PASTA_COLETAS / "preco_teorico_win_fluxo.csv"
ARQUIVO_JSON_MACRO = PASTA_COLETAS / "DadosAtivosUnificados.json"
ARQUIVO_JSON_SMC = PASTA_COLETAS / "AnaliseGraficaSMC_Regras.json"
ARQUIVO_JSON_ESTIMATIVA = PASTA_COLETAS / "EstimativaAbertura.json"


st.title("⚡ Cockpit de Leilão Ao Vivo - WIN")
st.markdown("Monitoramento em tempo real do preço teórico, fluxo de ordens e confluência macro/institucional.")


# ------------------------------------------------------------
# Helpers de carregamento
# ------------------------------------------------------------

def carregar_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def carregar_estimativa_calculada() -> dict:
    """
    Lê o EstimativaAbertura.json (produzido pelo CalculadoraEstimativaAbertura).
    Retorna dict com:
      - abertura_teorica: preço calculado
      - preco_referencia_base: preço usado como base
      - variacao_teorica_pct: variação aplicada
    """
    dados = carregar_json(ARQUIVO_JSON_ESTIMATIVA)
    est = (
        dados.get("estimativa_abertura", {}).get("WIN_INDICE")
        or dados.get("estimativas_abertura", {}).get("WIN_INDICE")
        or {}
    )
    return {
        "abertura_teorica": float(est.get("abertura_teorica_pontos", 0.0) or 0.0),
        "preco_referencia_base": float(est.get("preco_referencia_base", 0.0) or 0.0),
        "variacao_teorica_pct": float(est.get("variacao_teorica_pct", 0.0) or 0.0),
    }


def carregar_leilao_ocr() -> dict:
    """
    Lê o preço do leilão via LeilaoService (OCR).
    Retorna dict do service. Em caso de erro, retorna indisponível.
    """
    try:
        from v2.core.services.leilao_service import LeilaoService
        svc = LeilaoService(PASTA_COLETAS)
        return svc.obter_preco_leilao()
    except Exception as e:
        return {
            "disponivel": False,
            "preco": None,
            "timestamp": None,
            "fonte": f"ERRO: {e}",
        }


def carregar_historico_csv_recente(limite: int = 15) -> pd.DataFrame:
    """
    Lê as últimas N leituras do CSV do OCR.
    Usa o mesmo parser do LeilaoService (evita BOM, header, formato de data).
    """
    if not ARQUIVO_CSV.exists():
        return pd.DataFrame()

    registros = []
    try:
        with open(ARQUIVO_CSV, "r", encoding="utf-8-sig") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or not linha[0].isdigit():
                    continue
                partes = linha.split(",")
                if len(partes) < 2:
                    continue
                try:
                    dt = datetime.strptime(partes[0].strip(), "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        dt = datetime.strptime(partes[0].strip(), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                try:
                    preco = float(partes[1])
                    conf = float(partes[2]) if len(partes) > 2 else 0.0
                except ValueError:
                    continue
                registros.append({
                    "DataHora": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "PrecoTeorico": int(preco),
                    "Confianca": f"{conf:.3f}",
                })
    except Exception:
        return pd.DataFrame()

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    return df.tail(limite).iloc[::-1]


# ------------------------------------------------------------
# Fragmento em tempo real
# ------------------------------------------------------------

@st.fragment(run_every=1)
def renderizar_dashboard_tempo_real():
    # ---- Carrega dados ----
    macro_data = carregar_json(ARQUIVO_JSON_MACRO).get("ativos", {})
    smc_data = carregar_json(ARQUIVO_JSON_SMC)
    estimativa_calc = carregar_estimativa_calculada()
    leilao = carregar_leilao_ocr()

    # ---- Valores de referência ----
    win_ajuste = macro_data.get("WIN_AJUSTE", {}).get("preco", 0)
    win_fechamento = macro_data.get("WIN_LAST_TICK", {}).get("preco", 0)
    poc_ontem = smc_data.get("niveis_institucionais", {}).get("poc_ontem", 0)
    vies_smc = smc_data.get("bias_direcional", "NEUTRO")

    # ---- Viés macro (simples) ----
    ewz_var = macro_data.get("EWZ", {}).get("variacao_pct", 0)
    sp500_var = macro_data.get("SP500_FUT", {}).get("variacao_pct", 0)
    score_macro = ((ewz_var * 2) + sp500_var) / 3
    if score_macro > 0.3:
        vies_macro = "ALTA 🟢"
    elif score_macro < -0.3:
        vies_macro = "BAIXA 🔴"
    else:
        vies_macro = "NEUTRO 🟡"

    # ---- Valores das duas aberturas ----
    abertura_leilao = float(leilao.get("preco") or 0.0)
    abertura_calculada = float(estimativa_calc.get("abertura_teorica") or 0.0)

    # ------------------------------------------------------------
    # SEÇÃO 1 — Duas aberturas LADO A LADO
    # ------------------------------------------------------------
    st.markdown("## 💰 Aberturas Teóricas (Lado a Lado)")

    col_calc, col_leilao = st.columns(2)

    # ---- Coluna Esquerda: Abertura Calculada ----
    with col_calc:
        st.markdown("### 📊 Abertura Teórica (Calculada)")
        if abertura_calculada > 0:
            gap_calc = abertura_calculada - win_ajuste if win_ajuste > 0 else 0
            st.metric(
                label="Preço Teórico Calculado",
                value=f"{abertura_calculada:,.0f}",
                delta=f"{gap_calc:+.0f} pts vs ajuste",
            )
            st.caption(
                f"Base: {estimativa_calc.get('preco_referencia_base', 0):,.0f} | "
                f"Var: {estimativa_calc.get('variacao_teorica_pct', 0):+.4f}%"
            )
            st.caption("Fonte: `CalculadoraEstimativaAbertura.py`")
        else:
            st.info("⏳ Abertura calculada indisponível")

    # ---- Coluna Direita: Abertura do Leilão (OCR) ----
    with col_leilao:
        st.markdown("### 🎯 Abertura Teórica (Leilão OCR)")
        if leilao.get("disponivel") and abertura_leilao > 0:
            gap_leilao = abertura_leilao - win_ajuste if win_ajuste > 0 else 0
            ts = leilao.get("timestamp", "")
            st.metric(
                label="Preço Teórico do Leilão",
                value=f"{abertura_leilao:,.0f}",
                delta=f"{gap_leilao:+.0f} pts vs ajuste",
            )
            st.caption(
                f"Última leitura: {ts} | "
                f"Total: {leilao.get('total_leituras', 0)}"
            )
            st.caption(
                f"Faixa do leilão: {leilao.get('preco_min', 0):,.0f} "
                f"→ {leilao.get('preco_max', 0):,.0f}"
            )
        else:
            st.warning("⏳ OCR do leilão indisponível")
            st.caption(f"Motivo: {leilao.get('fonte', 'N/A')}")

    # ---- Divergência entre os dois ----
    if abertura_calculada > 0 and abertura_leilao > 0:
        divergencia = abertura_leilao - abertura_calculada
        if abs(divergencia) > 200:
            st.warning(
                f"⚠️ **Divergência entre as duas fontes:** {divergencia:+,.0f} pts. "
                "O OCR e o cálculo estão distantes — verifique qual usar."
            )
        else:
            st.success(
                f"✅ **Fontes alinhadas:** diferença de {divergencia:+,.0f} pts."
            )

    st.markdown("---")

    # ------------------------------------------------------------
    # SEÇÃO 2 — Métricas principais
    # ------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📈 Ajuste B3", f"{win_ajuste:,.0f}")
    with col2:
        st.metric("📉 Último Fechamento", f"{win_fechamento:,.0f}")
    with col3:
        st.metric("🏢 POC Ontem", f"{poc_ontem:,.0f}")
    with col4:
        gap_poc = (abertura_leilao or abertura_calculada) - poc_ontem if poc_ontem > 0 else 0
        st.metric("📊 Distância da POC", f"{gap_poc:+,.0f} pts")

    st.markdown("---")

    # ------------------------------------------------------------
    # SEÇÃO 3 — Contexto e Veredito
    # ------------------------------------------------------------
    c_left, c_right = st.columns([1, 2])

    with c_left:
        st.subheader("🌐 Contexto Macro / SMC")
        st.info(f"**Viés Macro:** {vies_macro}")
        st.info(f"**Viés Estrutural SMC:** {vies_smc}")
        st.text(f"Score Macro: {score_macro:+.3f}")

    with c_right:
        st.subheader("🎯 Veredito Operacional")

        # Usa o preço do LEILÃO como base (mais realista)
        preco_ref = abertura_leilao if abertura_leilao > 0 else abertura_calculada
        gap_ajuste = preco_ref - win_ajuste if win_ajuste > 0 and preco_ref > 0 else 0

        if preco_ref > 0:
            if "ALTA" in vies_macro and gap_ajuste > 0:
                st.success(
                    "### 🟢 COMPRA A MERCADO\n"
                    "Confluência de alta entre macro e leilão."
                )
            elif "BAIXA" in vies_macro and gap_ajuste < 0:
                st.error(
                    "### 🔴 VENDA A MERCADO\n"
                    "Pressão vendedora confirmada nos ativos globais e no book."
                )
            else:
                st.warning(
                    "### ⚠️ INDEFINIDO / FINTA\n"
                    "Divergência entre macro e preço teórico. Fique de fora."
                )
        else:
            st.warning("⏳ Aguardando captura válida do preço teórico...")

    # ------------------------------------------------------------
    # SEÇÃO 4 — Histórico recente do CSV
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📜 Histórico Recente de Capturas do Leilão")

    df_historico = carregar_historico_csv_recente(limite=15)
    if not df_historico.empty:
        st.dataframe(df_historico, use_container_width=True, hide_index=True)
    else:
        st.info("O arquivo CSV será exibido assim que a coleta iniciar.")


# Executa o bloco em tempo real
renderizar_dashboard_tempo_real()