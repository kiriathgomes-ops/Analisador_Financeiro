# -*- coding: utf-8 -*-
"""
Módulo: pages/6_📈_Matriz_de_Influencia.py
Versão: 2.3 — Pesos/Matriz escondidos em "Material de estudo" + popover simplificado
Objetivo: Guia rápido de correlação/influência + painel de leitura do estado atual do pré-market.
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="WINFUT - Matriz de Influência", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; }
.card-impact-high {
    background-color: #0d381e;
    border-left: 5px solid #00c853;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.card-impact-bear {
    background-color: #380d0d;
    border-left: 5px solid #ff3d00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.card-impact-warn {
    background-color: #382b0d;
    border-left: 5px solid #ffab00;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.badge-ref {
    display: inline-block;
    background: rgba(255, 171, 0, 0.15);
    border: 1px solid #ffab00;
    color: #ffab00;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-left: 8px;
    vertical-align: middle;
}
.painel-atual {
    background-color: #161b24;
    border: 1px solid #2a3a4a;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
}
.card-acao {
    border-radius: 10px;
    padding: 14px 18px;
    margin-top: 14px;
    font-size: 1.05rem;
    line-height: 1.4;
}
.card-acao-verde {
    background-color: rgba(34, 197, 94, 0.12);
    border: 1px solid #22c55e;
    color: #86efac;
}
.card-acao-vermelho {
    background-color: rgba(239, 68, 68, 0.12);
    border: 1px solid #ef4444;
    color: #fca5a5;
}
.card-acao-amarelo {
    background-color: rgba(255, 171, 0, 0.12);
    border: 1px solid #ffab00;
    color: #fcd34d;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CAMINHOS
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_COLETAS = BASE_DIR / "Coletas"

ARQ_UNIFICADO = PASTA_COLETAS / "DadosAtivosUnificados.json"
ARQ_DECISAO = PASTA_COLETAS / "Decisao_V2.json"
ARQ_SMC = PASTA_COLETAS / "AnaliseGraficaSMC_Regras.json"


# ==============================================================================
# LOADERS
# ==============================================================================
@st.cache_data(ttl=2)
def carregar_json(caminho_str: str) -> dict:
    caminho = Path(caminho_str)
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_var(ativos: dict, chave: str):
    v = (ativos.get(chave) or {}).get("variacao_pct")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _get_preco(ativos: dict, chave: str):
    v = (ativos.get(chave) or {}).get("preco")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# ==============================================================================
# HELPERS DE SEMÂNTICA VISUAL
# ==============================================================================
VERDE = "#22c55e"
VERMELHO = "#ef4444"
BRANCO = "#e6edf3"
CINZA = "#8b949e"


def _cor_valor(valor, inverter: bool = False) -> str:
    if valor is None:
        return CINZA
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return CINZA
    real = -v if inverter else v
    if real > 0.005:
        return VERDE
    if real < -0.005:
        return VERMELHO
    return BRANCO


def _cor_vies(v) -> str:
    s = str(v or "").upper()
    if "COMPRA" in s or "ALTA" in s or "BULL" in s:
        return VERDE
    if "VENDA" in s or "BAIXA" in s or "BEAR" in s:
        return VERMELHO
    return BRANCO


def _norm_dir(v) -> str:
    """Normaliza uma string de viés pra COMPRA / VENDA / NEUTRO."""
    s = str(v or "").upper()
    if "COMPRA" in s or "ALTA" in s or "BULL" in s:
        return "COMPRA"
    if "VENDA" in s or "BAIXA" in s or "BEAR" in s:
        return "VENDA"
    return "NEUTRO"


def _metric_card(label: str, valor, format_fn, inverter: bool = False):
    cor = _cor_valor(valor, inverter=inverter)
    if valor is None:
        texto = "—"
    else:
        try:
            texto = format_fn(valor)
        except Exception:
            texto = "—"
    st.markdown(
        f"<div style='text-align:center; padding:6px 0;'>"
        f"<div style='font-size:0.9rem; color:#8b949e; margin-bottom:6px;'>{label}</div>"
        f"<div style='font-size:1.9rem; font-weight:700; color:{cor}; line-height:1.1;'>{texto}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ==============================================================================
# HELPERS DE ANÁLISE
# ==============================================================================
ADRS_LISTA = ["VALE_ADR", "PETR_ADR", "ITUB_ADR", "BBAS_ADR", "BBD_ADR", "B3_ADR"]


def _calc_situacao_atual() -> dict:
    unif = carregar_json(str(ARQ_UNIFICADO))
    ativos = unif.get("ativos", {})

    adrs_vals = [_get_var(ativos, a) for a in ADRS_LISTA]
    adrs_vals = [v for v in adrs_vals if v is not None]
    adrs_med = round(sum(adrs_vals) / len(adrs_vals), 3) if adrs_vals else None

    sp500 = _get_var(ativos, "SP500_FUT")
    vix_var = _get_var(ativos, "VIX")
    petr = _get_var(ativos, "PETR4")
    vale = _get_var(ativos, "VALE3")
    win_ajuste = _get_preco(ativos, "WIN_AJUSTE")
    win_atual = _get_preco(ativos, "WIN_LAST_TICK") or _get_preco(ativos, "WIN_FUT")

    gap_win = None
    if win_atual is not None and win_ajuste is not None:
        gap_win = round(win_atual - win_ajuste, 0)

    di27 = _get_preco(ativos, "DI1_2027")
    di29 = _get_preco(ativos, "DI1_2029")
    di_inclinacao = None
    if di27 is not None and di29 is not None:
        di_inclinacao = round((di29 - di27) * 100.0, 1)

    smc = carregar_json(str(ARQ_SMC))
    vies_smc = smc.get("bias_direcional") or "—"

    dec = carregar_json(str(ARQ_DECISAO))
    vies_v2 = (dec.get("decisao") or {}).get("vies_final") or "—"
    conf_v2 = (dec.get("decisao") or {}).get("confianca")

    return {
        "adrs_med": adrs_med,
        "sp500": sp500,
        "vix_var": vix_var,
        "petr": petr,
        "vale": vale,
        "gap_win": gap_win,
        "di_inclinacao": di_inclinacao,
        "vies_smc": vies_smc,
        "vies_v2": vies_v2,
        "conf_v2": conf_v2,
    }


def _detectar_cenario(s: dict):
    adrs = s.get("adrs_med")
    sp500 = s.get("sp500")
    vix_var = s.get("vix_var") or 0.0
    petr = s.get("petr")
    vale = s.get("vale")

    if adrs is None or sp500 is None:
        return None

    if adrs > 2.0 and sp500 > 0.3 and vix_var < -1.0:
        return 1
    if adrs < -1.0 and sp500 < -1.0 and vix_var > 3.0:
        return 3
    if adrs > 1.0 and sp500 < -0.3:
        return 2
    if petr is not None and vale is not None:
        if (petr > 0.5 and vale < -0.5) or (petr < -0.5 and vale > 0.5):
            return 4
    return None


def _direcao_macro(s: dict) -> str:
    """Conta votos das 5 métricas (VIX/DI invertidos). Retorna COMPRA/VENDA/NEUTRO."""
    adrs = s.get("adrs_med") or 0
    sp500 = s.get("sp500") or 0
    vix = s.get("vix_var") or 0
    gap = s.get("gap_win") or 0
    di = s.get("di_inclinacao") or 0

    votos_alta = 0
    votos_baixa = 0

    if adrs > 0.1: votos_alta += 1
    elif adrs < -0.1: votos_baixa += 1

    if sp500 > 0.1: votos_alta += 1
    elif sp500 < -0.1: votos_baixa += 1

    if vix < -0.1: votos_alta += 1
    elif vix > 0.1: votos_baixa += 1

    if gap > 50: votos_alta += 1
    elif gap < -50: votos_baixa += 1

    if di < -5: votos_alta += 1
    elif di > 5: votos_baixa += 1

    if votos_alta >= 4:
        return "COMPRA"
    if votos_baixa >= 4:
        return "VENDA"
    return "NEUTRO"


def _calcular_acao(s: dict) -> dict:
    dir_macro = _direcao_macro(s)
    dir_smc = _norm_dir(s.get("vies_smc"))
    dir_v2 = _norm_dir(s.get("vies_v2"))

    if dir_macro == "COMPRA" and dir_smc == "COMPRA" and dir_v2 != "VENDA":
        return {
            "direcao": "COMPRA", "emoji": "🟢", "cor": "verde",
            "motivo": "Macro e SMC alinhados em ALTA. V2 não discorda.",
        }

    if dir_macro == "VENDA" and dir_smc == "VENDA" and dir_v2 != "COMPRA":
        return {
            "direcao": "VENDA", "emoji": "🔴", "cor": "vermelho",
            "motivo": "Macro e SMC alinhados em BAIXA. V2 não discorda.",
        }

    if (dir_macro == "COMPRA" and dir_smc == "VENDA") or (dir_macro == "VENDA" and dir_smc == "COMPRA"):
        return {
            "direcao": "AGUARDAR", "emoji": "⚠️", "cor": "amarelo",
            "motivo": f"Macro ({dir_macro}) e SMC ({dir_smc}) divergem. Não operar até alinhamento.",
        }

    return {
        "direcao": "AGUARDAR", "emoji": "⚠️", "cor": "amarelo",
        "motivo": "Sem confluência clara entre Macro, SMC e V2. Prioriza o painel principal de leilão.",
    }


_CENARIO_INFO = {
    1: {"emoji": "🔥", "nome": "Super Confluência de Alta",
        "acao": "🚀 **Não fazer FADE contra o gap.** Foco em compra na retração ou rompimento pós-abertura."},
    2: {"emoji": "⚡", "nome": "Divergência ADRs vs EUA",
        "acao": "⚖️ **Prioridade total às ADRs** (VALE/PETR/Bancos). O peso local supera o exterior."},
    3: {"emoji": "⚠️", "nome": "Aversão Global a Risco (Risk-Off)",
        "acao": "📉 **Aguardar teste no ajuste.** Se perder o ajuste no leilão, preferência por continuação da venda."},
    4: {"emoji": "🛑", "nome": "Divergência Interna de Commodities",
        "acao": "🔄 **Leilão BLOQUEADO.** Operar preferencialmente 'Retorno ao Ajuste (500/100)' após 09:15h."},
}


# ==============================================================================
# CABEÇALHO + POPOVER SIMPLIFICADO
# ==============================================================================
col_titulo, col_ajuda = st.columns([5, 1])

with col_titulo:
    st.markdown(
        "<h2 style='color:#00d4ff; margin-bottom:4px;'>📈 Matriz de Influência e Confluência de Ativos</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Painel de leitura do estado atual + guia de consulta para decisão no leilão e pré-market da B3")

with col_ajuda:
    with st.popover("❓ Como usar", use_container_width=True):
        st.markdown("""
### 🎯 Como decidir em 10 segundos

**1. Olha o banner (caixa cinza)**
Qual cenário apareceu?
- `#1 🔥` → tudo verde = **alta forte**
- `#3 ⚠️` → tudo vermelho = **baixa forte**
- `#2 ⚡` ou `#4 🛑` → **cuidado redobrado**
- "Sem cenário" → **não opera**

**2. Olha o card colorido (AÇÃO HOJE)**
- 🟢 **COMPRA** → opera comprado
- 🔴 **VENDA** → opera vendido
- ⚠️ **AGUARDAR** → fica de fora

**3. Os dois concordam?**
- ✅ Sim → opera na direção do card
- ❌ Não → **aguarda**

---

### 💡 Regra de ouro
Na dúvida, **fica de fora**. Só opera quando o banner e o card apontam a mesma direção.

---

### 🔍 As 5 métricas do topo (se quiser entender)

| Métrica | 🟢 Verde | 🔴 Vermelho |
|---|---|---|
| ADRs BR | subiu | caiu |
| S&P500 | subiu | caiu |
| VIX | **caiu** (menos medo) | **subiu** (mais medo) |
| Inclinação DI | **caiu** (juro cede) | **subiu** (juro sobe) |
| Gap WIN vs Ajuste | positivo | negativo |

⚠️ **VIX e DI são invertidos:** valor verde = notícia boa pra bolsa.
""")


# ==============================================================================
# 1. PAINEL — SITUAÇÃO ATUAL (fragment 60s)
# ==============================================================================
@st.fragment(run_every=60)
def _render_situacao_atual():
    s = _calc_situacao_atual()
    cenario_id = _detectar_cenario(s)
    acao = _calcular_acao(s)

    st.markdown("### 📊 Situação Atual do Pré-Market")
    st.caption(
        f"Leitura em tempo quase-real · atualiza a cada 60s · "
        f"🕒 {datetime.now().strftime('%H:%M:%S')}"
    )

    # ---- 5 métricas ----
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        _metric_card("🇧🇷 ADRs BR (média)", s.get("adrs_med"),
                     lambda v: f"{v:+.2f}%", inverter=False)
    with c2:
        _metric_card("🇺🇸 S&P500 Fut", s.get("sp500"),
                     lambda v: f"{v:+.2f}%", inverter=False)
    with c3:
        _metric_card("⚠️ VIX", s.get("vix_var"),
                     lambda v: f"{v:+.2f}%", inverter=True)
    with c4:
        _metric_card("📈 Inclinação DI (29-27)", s.get("di_inclinacao"),
                     lambda v: f"{v:+.1f} bps", inverter=True)
    with c5:
        _metric_card("📏 Gap WIN vs Ajuste", s.get("gap_win"),
                     lambda v: f"{v:+.0f} pts", inverter=False)

    # ---- Banner de cenário ----
    if cenario_id is None:
        st.markdown(
            "<div class='painel-atual'>"
            "<h4 style='margin:0 0 6px;'>⚪ Sem cenário claro detectado</h4>"
            "<div style='opacity:.8;'>Mercado em ruído / confluência fraca. "
            "Priorize leitura caso-a-caso no painel principal de leilão.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        info = _CENARIO_INFO[cenario_id]
        st.markdown(
            f"<div class='painel-atual'>"
            f"<h4 style='margin:0 0 6px;'>{info['emoji']} Cenário ativo hoje: "
            f"<b>#{cenario_id} — {info['nome']}</b></h4>"
            f"<div>{info['acao']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ---- Rodapé com viés V2/SMC ----
    v2 = s.get("vies_v2") or "—"
    cor_v2 = _cor_vies(v2)
    conf = s.get("conf_v2")
    smc = s.get("vies_smc") or "—"
    cor_smc = _cor_vies(smc)

    conf_html = (
        f" <span style='color:#8b949e;'>· confiança</span> "
        f"<b style='color:{BRANCO};'>{conf}%</b>"
        if conf is not None else ""
    )

    st.markdown(
        f"<div style='font-size:1.15rem; margin-top:6px;'>"
        f"<span style='color:#c9d1d9;'>Viés V2:</span> "
        f"<b style='color:{cor_v2};'>{v2}</b>"
        f"{conf_html}"
        f" <span style='color:#8b949e;'>· Viés SMC:</span> "
        f"<b style='color:{cor_smc};'>{smc}</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- 🎯 AÇÃO HOJE ----
    cor_css = f"card-acao-{acao['cor']}"
    st.markdown(
        f"<div class='card-acao {cor_css}'>"
        f"<b style='font-size:1.15rem;'>{acao['emoji']} AÇÃO HOJE: {acao['direcao']}</b>"
        f"<div style='margin-top:6px; opacity:.95;'>{acao['motivo']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")


# ==============================================================================
# 2. CENÁRIOS — SEGUNDO
# ==============================================================================
def _render_cenarios():
    st.subheader("🧩 Cenários de Confluência e Divergência na Prática")
    st.caption(
        "Os 4 cenários abaixo são referência. **Qual está ativo hoje** é indicado no painel do topo "
        "(pelo número do cenário)."
    )

    cenarios_data = [
        {
            "num": 1,
            "Cenário": "🔥 Super Confluência de Alta",
            "ADRs BR": "🟢 Forte Alta (+2.0%)",
            "S&P / Nasdaq": "🟢 Positivos",
            "VIX / DI": "🔴 Queda / Estável",
            "Comportamento Projetado (WIN)": "🚀 GAP de Alta Forte + Explosão",
            "Estratégia": "Não fazer FADE/Venda contra o gap. Foco em compra na retração ou rompimento pós-abertura.",
        },
        {
            "num": 2,
            "Cenário": "⚡ Divergência: ADRs vs EUA",
            "ADRs BR": "🟢 Forte Alta (+1.5%)",
            "S&P / Nasdaq": "🔴 Baixa (-0.8%)",
            "VIX / DI": "🟡 Neutro",
            "Comportamento Projetado (WIN)": "⚖️ Abertura Autônoma / Rali do Ibovespa",
            "Estratégia": "Prioridade total às ADRs (VALE/PETR/Bancos). O peso local supera o exterior quando ADRs estão compradas.",
        },
        {
            "num": 3,
            "Cenário": "⚠️ Aversão Global a Risco (Risk-Off)",
            "ADRs BR": "🔴 Em Queda",
            "S&P / Nasdaq": "🔴 Em Queda Forte",
            "VIX / DI": "🟢 VIX Dispara / DI Sobe",
            "Comportamento Projetado (WIN)": "📉 GAP de Baixa Agressivo",
            "Estratégia": "Aguardar teste no ajuste. Se perder o ajuste no leilão, preferência por continuação da venda (Explosão Venda).",
        },
        {
            "num": 4,
            "Cenário": "🛑 Divergência Interna de Commodities",
            "ADRs BR": "🟡 Mistas (PETR subindo, VALE caindo)",
            "S&P / Nasdaq": "🟢 Leve Alta",
            "VIX / DI": "🟡 Estável",
            "Comportamento Projetado (WIN)": "🔄 Mercado Travado / Leilão Sujo",
            "Estratégia": "Operacional de Leilão fica BLOQUEADO. Operar preferencialmente 'Retorno ao Ajuste (500/100)' após 09:15h.",
        },
    ]

    for c in cenarios_data:
        if "Super Confluência" in c["Cenário"]:
            css = "card-impact-high"
        elif "Divergência" in c["Cenário"]:
            css = "card-impact-warn"
        else:
            css = "card-impact-bear"

        st.markdown(f"""
        <div class="{css}">
            <h4 style="margin:0 0 8px;">#{c['num']} — {c['Cenário']}</h4>
            <p><b>• ADRs BR:</b> {c['ADRs BR']} | <b>• EUA:</b> {c['S&P / Nasdaq']} | <b>• VIX/DI:</b> {c['VIX / DI']}</p>
            <p><b>📉 Expectativa no Índice:</b> <code style="color:#00d4ff;">{c['Comportamento Projetado (WIN)']}</code></p>
            <p style="margin-bottom:0;">💡 <b>Estratégia Operacional:</b> {c['Estratégia']}</p>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# 3. PESOS — REFERÊNCIA TEÓRICA
# ==============================================================================
def _render_pesos():
    st.subheader("⚖️ Pesos e Vetores de Influência Direta")
    st.markdown(
        "<span class='badge-ref'>📌 REFERÊNCIA TEÓRICA — não recalculada dos dados</span>",
        unsafe_allow_html=True,
    )
    st.caption("Composição de forças explicativas do WIN e do WDO na abertura. Valores históricos de referência.")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 🟢 Drivers Principais do Mini Índice (WIN)")
        df_win_peso = pd.DataFrame([
            {"Ativo": "ADRs Brasileiras (VALE, PETR, Bancos)", "Peso Proporcional": 55, "Impacto Direto": "Direto (+ / +)"},
            {"Ativo": "Índices US (S&P500 / Nasdaq)", "Peso Proporcional": 25, "Impacto Direto": "Direto (+ / +)"},
            {"Ativo": "Commodities (Petróleo / Minério)", "Peso Proporcional": 10, "Impacto Direto": "Direto (+ / +)"},
            {"Ativo": "VIX (Índice do Medo)", "Peso Proporcional": -5, "Impacto Direto": "Inverso (+ / -)"},
            {"Ativo": "Curva de Juros DI (DI1 2027/2029)", "Peso Proporcional": -5, "Impacto Direto": "Inverso (+ / -)"},
        ])

        fig_win = px.bar(
            df_win_peso, x="Peso Proporcional", y="Ativo", orientation='h',
            color="Peso Proporcional",
            color_continuous_scale=["#ff3d00", "#ffab00", "#00c853"],
            title="Força Explicativa no Pregão de Abertura do WIN",
        )
        fig_win.update_layout(
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#e6edf3"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_win, use_container_width=True)

    with col_right:
        st.markdown("#### 🔴 Drivers Principais do Mini Dólar (WDO)")
        df_wdo_peso = pd.DataFrame([
            {"Ativo": "DXY (Índice Dólar Global)", "Peso Proporcional": 45, "Impacto Direto": "Direto (+ / +)"},
            {"Ativo": "Curva de Juros DI (DI1 2027/2029)", "Peso Proporcional": 25, "Impacto Direto": "Direto (+ / +)"},
            {"Ativo": "EWZ (ETF Brasil no Exterior)", "Peso Proporcional": -20, "Impacto Direto": "Inverso (+ / -)"},
            {"Ativo": "VIX (Aversão Global a Risco)", "Peso Proporcional": 10, "Impacto Direto": "Direto (+ / +)"},
        ])

        fig_wdo = px.bar(
            df_wdo_peso, x="Peso Proporcional", y="Ativo", orientation='h',
            color="Peso Proporcional",
            color_continuous_scale=["#ff3d00", "#ffab00", "#00c853"],
            title="Força Explicativa no Pregão de Abertura do WDO",
        )
        fig_wdo.update_layout(
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#e6edf3"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_wdo, use_container_width=True)


# ==============================================================================
# 4. MATRIZ — REFERÊNCIA HISTÓRICA
# ==============================================================================
def _render_matriz():
    st.subheader("🔥 Matriz de Correlação Cruzada")
    st.markdown(
        "<span class='badge-ref'>⚠️ REFERÊNCIA HISTÓRICA — sem série intraday longa pra recalcular</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Coeficientes típicos de correlação durante o leilão de abertura (WIN_FUT, ADRs BR, S&P500, VIX, DI1, WDO_FUT). "
        "Apenas janelas de ~55 min estão disponíveis nas coletas atuais — insuficiente pra rolling 30d."
    )

    matriz_corr = pd.DataFrame(
        [
            [1.00, 0.85, 0.72, -0.68, -0.62, -0.78],
            [0.85, 1.00, 0.65, -0.55, -0.50, -0.72],
            [0.72, 0.65, 1.00, -0.45, -0.40, -0.58],
            [-0.68, -0.55, -0.45, 1.00, 0.75, 0.62],
            [-0.62, -0.50, -0.40, 0.75, 1.00, 0.55],
            [-0.78, -0.72, -0.58, 0.62, 0.55, 1.00],
        ],
        columns=["WIN_FUT", "ADRs BR", "S&P500", "VIX", "DI1", "WDO_FUT"],
        index=["WIN_FUT", "ADRs BR", "S&P500", "VIX", "DI1", "WDO_FUT"],
    )

    fig_heatmap = px.imshow(
        matriz_corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        title="Coeficiente de Correlação Típico do Leilão de Abertura",
    )
    fig_heatmap.update_layout(
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e6edf3"},
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)


# ==============================================================================
# 5. REGRAS — CONSULTA RÁPIDA
# ==============================================================================
def _render_regras():
    st.markdown("---")
    st.markdown("### 📌 Regras de Ouro no Pré-Market")
    st.caption("Consulta rápida. Os valores atuais (VIX, DI) estão no painel do topo.")

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.markdown("""
        **1. Prioridade das ADRs**
        Quando há notícia Relevante de 3★ no Brasil às 09:00, as **ADRs Brasileiras** (VALE, PETR, ITUB) possuem **60%+ da prioridade** operacional sobre os índices S&P500/Nasdaq.
        """)

    with col_r2:
        st.markdown("""
        **2. Trava do VIX**
        Se o **VIX** estiver subindo acima de **+5.00%**, qualquer alta do Mini Índice deve ser operada com desconfiança (alvo mais curto), pois o risco de pullback abrupto é elevado.
        """)

    with col_r3:
        st.markdown("""
        **3. Regra dos DIs Curto vs Longo**
        Se a Curva de **DI (2027/2029)** estiver subindo forte, o Mini Índice tende a pressionar para baixo e o Mini Dólar atua na ponta compradora.
        """)


# ==============================================================================
# CORPO — ORDEM DE LEITURA (fluxo de decisão)
# ==============================================================================
def render_body():
    _render_situacao_atual()   # 1º — estado + AÇÃO HOJE
    _render_cenarios()         # 2º — cenário ativo + os 4 cards

    # Pesos + Matriz escondidos atrás de expander
    with st.expander("📚 Material de estudo (referência — clique pra abrir)"):
        _render_pesos()
        st.markdown("---")
        _render_matriz()

    _render_regras()           # último — regras de ouro


# ==============================================================================
# EXECUÇÃO
# ==============================================================================
render_body()