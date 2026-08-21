# ============================================================
# ARQUIVO: pages/22_⚡_Monitor_Abertura_Leilao.py
# VERSÃO: 3.2 (Corrigida) - Projeção Avançada com MT5 Estável
# ============================================================

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

# Tenta importar MetaTrader5 defensivamente
try:
    import MetaTrader5 as mt5
    MT5_DISPONIVEL = True
except ImportError:
    MT5_DISPONIVEL = False

# ------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="Monitor de Abertura & Leilão - Analisador Financeiro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização em Dark Theme
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%); }
    .metric-card {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2a2d4a;
        margin-bottom: 12px;
    }
    .separator { border: none; height: 2px; background: linear-gradient(90deg, #2a2d4a, transparent); margin: 20px 0; }
    .badge-vies-compra { color: #00e676; font-weight: bold; font-size: 1.1rem; }
    .badge-vies-venda { color: #ff5252; font-weight: bold; font-size: 1.1rem; }
    .badge-vies-neutro { color: #ffe66d; font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# DIRETÓRIOS E CONSTANTES
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"
COLETAS_DIR.mkdir(parents=True, exist_ok=True)

ARQUIVO_HISTORICO_LEILAO = COLETAS_DIR / "historico_leilao_win.csv"

MAPEAMENTO_ADR = {
    "VALE3": "VALE",
    "PETR4": "PBR-A",
    "PETR3": "PBR",
    "ITUB4": "ITUB",
    "BBDC4": "BBD",
}

PESOS_WIN = {
    "EWZ": 0.35,
    "SPY": 0.25,
    "VALE": 0.20,
    "PBR": 0.20,
}

# ------------------------------------------------------------
# FUNÇÕES AUXILIARES E DE MERCADO
# ------------------------------------------------------------
def obter_simbolo_win_ativo() -> str:
    """Retorna o símbolo de Mini Índice ativo no MT5 sem interromper a sessão."""
    if not MT5_DISPONIVEL:
        return "WIN$"
    
    simbolos = ["WIN$", "WIN1!"]
    for s in simbolos:
        info = mt5.symbol_info(s)
        if info is not None:
            return s
            
    return "WIN$"

def buscar_referencias_win_coletas() -> tuple[float | None, float | None]:
    """Varre os arquivos JSON na pasta Coletas."""
    ajuste = None
    fechamento = None

    arquivos_json = sorted(list(COLETAS_DIR.glob("*.json")), reverse=True)
    for arq in arquivos_json:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if "ativos" in dados and "WIN" in dados["ativos"]:
                win_data = dados["ativos"]["WIN"]
                if win_data.get("status") == "OK":
                    if fechamento is None and win_data.get("last", 0) > 0:
                        fechamento = float(win_data["last"])

            coletas = dados.get("coletas", [])
            for item in coletas:
                ativo = item.get("ativo")
                val_close = item.get("dados_reais", {}).get("close")
                
                if val_close is not None:
                    if ativo == "B3_AJUSTE_WIN" and ajuste is None:
                        ajuste = float(val_close)
                    elif ativo in ["WIN_LAST_TICK", "WIN1!", "WIN_FUT"] and fechamento is None:
                        fechamento = float(val_close)

            if ajuste is not None and fechamento is not None:
                break
        except Exception:
            continue

    return ajuste, fechamento

def obter_quote_finnhub(ticker: str) -> dict | None:
    """Coleta o quote individual do Finnhub com fallback de tratamento."""
    if not FINNHUB_KEY or not ticker:
        return None
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
    try:
        res = requests.get(url, timeout=5).json()
        if "c" in res and res["c"] != 0:
            return {
                "Preco": float(res["c"]),
                "Var_%": round(float(res.get("dp", 0.0)), 2),
                "Var_$": round(float(res.get("d", 0.0)), 2),
            }
    except Exception:
        pass
    return None

def calcular_gap_win_projecao() -> dict:
    """Calcula a variação teórica e a projeção de abertura utilizando Ajuste e Fechamento."""
    variacoes = {}
    var_teorica_pct = 0.0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(obter_quote_finnhub, t): t for t in PESOS_WIN.keys()}
        for future in futures:
            ticker = futures[future]
            q = future.result()
            var_pct = q["Var_%"] if q else 0.0
            variacoes[ticker] = var_pct
            var_teorica_pct += var_pct * PESOS_WIN[ticker]

    var_teorica_pct = round(var_teorica_pct, 2)

    preco_ajuste, preco_fechamento = buscar_referencias_win_coletas()

    if (not preco_ajuste or not preco_fechamento) and MT5_DISPONIVEL and mt5.initialize():
        simbolo_ativo = obter_simbolo_win_ativo()
        info_win = mt5.symbol_info(simbolo_ativo)
        if info_win:
            if not preco_fechamento and getattr(info_win, "session_close", 0) > 0:
                preco_fechamento = float(info_win.session_close)
            if not preco_ajuste and getattr(info_win, "session_price_settlement", 0) > 0:
                preco_ajuste = float(info_win.session_price_settlement)
        mt5.shutdown()

    preco_ref = preco_ajuste if (preco_ajuste and preco_ajuste > 0) else (preco_fechamento or 0.0)

    if preco_ref > 0:
        preco_abertura_est = preco_ref * (1 + (var_teorica_pct / 100))
        gap_pts_ajuste = round(preco_abertura_est - preco_ajuste) if preco_ajuste else 0
        gap_pts_fech = round(preco_abertura_est - preco_fechamento) if preco_fechamento else 0
    else:
        gap_pts_ajuste = 0
        gap_pts_fech = 0
        preco_abertura_est = 0.0

    # Classificação do Viés
    if var_teorica_pct >= 0.60:
        vies = "FORTE COMPRA 🟢🟢"
    elif var_teorica_pct >= 0.20:
        vies = "COMPRA MODERADA 🟢"
    elif var_teorica_pct <= -0.60:
        vies = "FORTE VENDA 🔴🔴"
    elif var_teorica_pct <= -0.20:
        vies = "VENDA MODERADA 🔴"
    else:
        vies = "NEUTRO / CONSOLIDADO 🟡"

    return {
        "Preco_Ajuste_B3": preco_ajuste or 0.0,
        "Fechamento_Anterior_WIN": preco_fechamento or 0.0,
        "Preco_Referencia_Usado": preco_ref,
        "Var_Teorica_Projetada_%": var_teorica_pct,
        "Gap_vs_Ajuste_Pts": gap_pts_ajuste,
        "Gap_vs_Fechamento_Pts": gap_pts_fech,
        "Preco_Abertura_Projetado": round(preco_abertura_est),
        "Vies_Abertura": vies,
        "Detalhes_Ativos": variacoes,
    }

def analisar_descasamento_leilao(limiar_spread=0.5) -> pd.DataFrame:
    """Compara variações das ADRs vs Leilão B3."""
    relatorio = []
    mt5_ok = MT5_DISPONIVEL and mt5.initialize()

    for ticker_b3, ticker_adr in MAPEAMENTO_ADR.items():
        quote_adr = obter_quote_finnhub(ticker_adr)
        var_adr = quote_adr["Var_%"] if quote_adr else 0.0

        preco_leilao = 0.0
        var_b3 = 0.0

        if mt5_ok:
            mt5.symbol_select(ticker_b3, True)
            tick = mt5.symbol_info_tick(ticker_b3)
            info = mt5.symbol_info(ticker_b3)
            if tick and info and getattr(info, "session_close", 0) > 0:
                teorico = getattr(info, "price_theoretical", 0.0)
                preco_leilao = teorico if (teorico and teorico > 0) else tick.last
                
                if preco_leilao > 0:
                    var_b3 = round(((preco_leilao / info.session_close) - 1) * 100, 2)

        spread = round(var_adr - var_b3, 2)
        sinal = "NEUTRO"
        if spread >= limiar_spread:
            sinal = "🟢 COMPRA B3 (Atrás da ADR)"
        elif spread <= -limiar_spread:
            sinal = "🔴 VENDA B3 (Esticada vs ADR)"

        relatorio.append({
            "Ação B3": ticker_b3,
            "Preço Leilão B3": preco_leilao if preco_leilao > 0 else "Em Leilão/Sem Tick",
            "Var B3 %": var_b3,
            "ADR (NY)": ticker_adr,
            "Var ADR %": var_adr,
            "Spread %": spread,
            "Sinal Operacional": sinal,
        })

    if mt5_ok:
        mt5.shutdown()

    return pd.DataFrame(relatorio)

def obter_snapshot_leilao_win() -> dict | None:
    """Captura tick/preço teórico do leilão em tempo real no MT5."""
    if not MT5_DISPONIVEL:
        st.error("Biblioteca MetaTrader5 não está disponível.")
        return None

    if not mt5.initialize():
        st.error(f"Falha ao conectar no MT5: {mt5.last_error()}")
        return None

    symbol = obter_simbolo_win_ativo()
    mt5.symbol_select(symbol, True)

    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if info is None or tick is None:
        st.error(f"Símbolo '{symbol}' não respondeu no MT5. Verifique se ele está no Market Watch.")
        mt5.shutdown()
        return None

    ajuste_coleta, fechamento_coleta = buscar_referencias_win_coletas()
    fechamento_ant = fechamento_coleta or getattr(info, "session_close", 0.0)
    ajuste_ant = ajuste_coleta or getattr(info, "session_price_settlement", 0.0)

    teorico = getattr(info, "price_theoretical", 0.0)
    preco_leilao = float(teorico) if (teorico and teorico > 0) else float(tick.last)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dados = {
        "Data_Hora": now_str,
        "Ativo": info.name,
        "Fechamento_Anterior": fechamento_ant,
        "Preco_Ajuste_Referencia": ajuste_ant,
        "Ultimo_Preco_Leilao": preco_leilao,
        "Bid": tick.bid,
        "Ask": tick.ask,
        "Gap_vs_Fechamento_Pts": round(preco_leilao - fechamento_ant) if fechamento_ant > 0 else 0,
        "Gap_vs_Ajuste_Pts": round(preco_leilao - ajuste_ant) if ajuste_ant > 0 else 0,
    }

    mt5.shutdown()

    # Gravação no arquivo CSV
    df_row = pd.DataFrame([dados])
    escrever_cabecalho = not ARQUIVO_HISTORICO_LEILAO.exists()
    df_row.to_csv(ARQUIVO_HISTORICO_LEILAO, mode="a", header=escrever_cabecalho, index=False)

    return dados

# ------------------------------------------------------------
# INTERFACE PRINCIPAL STREAMLIT
# ------------------------------------------------------------
st.title("⚡ Monitor de Abertura & Leilão")
st.caption("Visão Integrada: Projeção de GAP • Ajuste B3 vs Fechamento • Arbitragem B3 vs ADRs")

# Sidebar
st.sidebar.title("⚙️ Painel de Controle")
auto_refresh = st.sidebar.checkbox("Atualização Automática (5s)", value=False)
limiar_spread = st.sidebar.slider("Sensibilidade do Spread (%)", 0.2, 2.0, 0.5, 0.1)

if st.sidebar.button("🔄 Atualizar Agora"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Status MT5: {'🟢 Conectado' if MT5_DISPONIVEL else '🔴 Indisponível'}")
st.sidebar.caption(f"Status Finnhub: {'🟢 Conectado' if FINNHUB_KEY else '🔴 Chave Ausente'}")

# ============================================================
# SEÇÃO 1: PROJEÇÃO DE ABERTURA
# ============================================================
st.markdown("### 🎯 Projeção Teórica de Abertura (WIN)")

with st.spinner("Calculando modelo estatístico de GAP..."):
    gap_info = calcular_gap_win_projecao()

col1, col2, col3, col4, col5 = st.columns(5)

vies_str = gap_info["Vies_Abertura"]
if "COMPRA" in vies_str:
    badge_class = "badge-vies-compra"
elif "VENDA" in vies_str:
    badge_class = "badge-vies-venda"
else:
    badge_class = "badge-vies-neutro"

with col1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.caption("Viés do Mercado")
    st.markdown(f"<span class='{badge_class}'>{vies_str}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.metric(
        "Var. Teórica Global",
        f"{gap_info['Var_Teorica_Projetada_%']:+.2f}%",
        delta=f"{gap_info['Gap_vs_Ajuste_Pts']} pts (vs Ajuste)",
    )

with col3:
    fmt_ajuste = f"{gap_info['Preco_Ajuste_B3']:,.0f}" if gap_info['Preco_Ajuste_B3'] > 0 else "N/A"
    st.metric("Ajuste B3 (Anterior)", fmt_ajuste)

with col4:
    fmt_fech = f"{gap_info['Fechamento_Anterior_WIN']:,.0f}" if gap_info['Fechamento_Anterior_WIN'] > 0 else "N/A"
    st.metric("Fechamento B3", fmt_fech, delta=f"{gap_info['Gap_vs_Fechamento_Pts']} pts (vs Fech)")

with col5:
    fmt_proj = f"{gap_info['Preco_Abertura_Projetado']:,.0f}" if gap_info['Preco_Abertura_Projetado'] > 0 else "N/A"
    st.metric("Preço Teórico Estimado", fmt_proj)

st.markdown("**Pesos dos Ativos Internacionais:**")
detalhes_cols = st.columns(len(gap_info["Detalhes_Ativos"]))
for i, (k_ticker, v_var) in enumerate(gap_info["Detalhes_Ativos"].items()):
    peso_pct = int(PESOS_WIN.get(k_ticker, 0) * 100)
    detalhes_cols[i].metric(f"{k_ticker} ({peso_pct}%)", f"{v_var:+.2f}%")

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ============================================================
# SEÇÃO 2: LEILÃO DE ABERTURA B3 VS ADRS NY
# ============================================================
st.markdown("### ⚖️ Oportunidades de Arbitragem (Ações B3 vs ADRs NY)")

df_descasamento = analisar_descasamento_leilao(limiar_spread=limiar_spread)

if not df_descasamento.empty:
    st.dataframe(
        df_descasamento,
        column_config={
            "Var B3 %": st.column_config.NumberColumn(format="%.2f%%"),
            "Var ADR %": st.column_config.NumberColumn(format="%.2f%%"),
            "Spread %": st.column_config.NumberColumn(format="%.2f%%"),
        },
        use_container_width=True,
        hide_index=True,
    )

st.markdown('<hr class="separator">', unsafe_allow_html=True)

# ============================================================
# SEÇÃO 3: MONITORAMENTO & SNAPSHOT DO LEILÃO
# ============================================================
st.markdown("### ⏱️ Leilão em Tempo Real (MT5)")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("#### Snapshot do Leilão")
    if st.button("📸 Gravar Snapshot do Leilão"):
        snapshot = obter_snapshot_leilao_win()
        if snapshot:
            st.success("Snapshot gravado com sucesso!")
            st.json(snapshot)

with col_right:
    st.markdown("#### Histórico do Leilão Registrado")
    if ARQUIVO_HISTORICO_LEILAO.exists():
        try:
            df_hist = pd.read_csv(ARQUIVO_HISTORICO_LEILAO)
            if not df_hist.empty:
                st.dataframe(df_hist.tail(8), use_container_width=True, hide_index=True)
                
                if len(df_hist) >= 2:
                    fig_leilao = px.line(
                        df_hist,
                        x="Data_Hora",
                        y=["Ultimo_Preco_Leilao", "Preco_Ajuste_Referencia", "Fechamento_Anterior"],
                        title="Formação de Preço do Leilão vs Referências",
                        labels={"value": "Pontos", "Data_Hora": "Horário"},
                    )
                    fig_leilao.update_layout(
                        plot_bgcolor="#0e1117",
                        paper_bgcolor="#0e1117",
                        font_color="#e6edf3",
                        height=300,
                        margin=dict(l=10, r=10, t=30, b=10),
                    )
                    st.plotly_chart(fig_leilao, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao ler o histórico: {e}")

st.caption(f"Última execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if auto_refresh:
    time.sleep(5)
    st.rerun()