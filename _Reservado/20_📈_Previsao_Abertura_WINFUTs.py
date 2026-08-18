# ============================================================
# PÁGINA: Previsão de Abertura WINFUT
# FASE 7 — Dashboard operacional V2
#
# Mostra:
#   - Ajuste / Last / Distância
#   - Posição em relação ao ajuste
#   - Cenário principal e alternativo
#   - Comportamentos possíveis
#   - Contexto externo
#   - Níveis
#
# Não gera ordem. Linguagem de cenário / probabilidade.
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Garante import da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.core.services.win_session_builder import build_win_session
from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura
from v2.core.services.session_history import SessionHistoryService, salvar_sessao_hoje

st.set_page_config(
    page_title="Previsão Abertura WINFUT",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Previsão de Abertura — WINFUT")
st.caption("Cenários em relação ao ajuste · Não é ordem de compra/venda")

# ------------------------------------------------------------
# Carregar dados
# ------------------------------------------------------------
@st.cache_data(ttl=60)
def carregar():
    session = build_win_session()
    cenario = gerar_cenario_abertura(session)
    session.cenario = cenario
    return session, cenario


try:
    session, cenario = carregar()
except Exception as e:
    st.error(f"Falha ao montar WinSession: {e}")
    st.stop()

# ------------------------------------------------------------
# Ações
# ------------------------------------------------------------
col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_b:
    if st.button("💾 Gravar no histórico", use_container_width=True):
        path = salvar_sessao_hoje(session, cenario, tag="ui")
        st.success(f"Salvo: {path.name}")

# ------------------------------------------------------------
# 1. Referências de preço
# ------------------------------------------------------------
st.subheader("Referências")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Contrato", session.metadata.contrato_principal or "—")
with c2:
    st.metric("Ajuste", f"{session.precos.ajuste:,.0f}" if session.precos.ajuste else "—")
with c3:
    st.metric("Last MT5", f"{session.precos.last_mt5:,.0f}" if session.precos.last_mt5 else "—")
with c4:
    dist = session.distancias.last_vs_ajuste_pts
    st.metric(
        "Distância",
        f"{dist:+,.0f} pts" if dist is not None else "—",
        delta=f"{session.distancias.last_vs_ajuste_pct:+.3f}%" if session.distancias.last_vs_ajuste_pct else None,
    )
with c5:
    pos = cenario.relacao_com_ajuste.posicao or "—"
    cor = {"ACIMA": "🟢", "ABAIXO": "🔴", "NO_AJUSTE": "🟡"}.get(pos, "⚪")
    st.metric("Posição", f"{cor} {pos}")

st.divider()

# ------------------------------------------------------------
# 2. Cenário principal
# ------------------------------------------------------------
st.subheader("Cenário principal")

dir_ = cenario.direcao_provavel or "NEUTRO"
prob = cenario.probabilidade_direcao
conf = cenario.confianca_geral

badge = {"ALTA": "🟢 ALTA", "BAIXA": "🔴 BAIXA", "NEUTRO": "🟡 NEUTRO"}.get(dir_, dir_)

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"### {badge}")
    st.write(cenario.relacao_com_ajuste.cenario_principal or "—")
    if cenario.cenario_alternativo:
        st.info(f"**Alternativo:** {cenario.cenario_alternativo}")
with col2:
    st.metric("Prob. direção", f"{prob:.0f}%" if prob else "—")
    st.metric("Confiança", f"{conf:.0f}%" if conf else "—")
    st.metric("Prob. cenário", f"{cenario.relacao_com_ajuste.probabilidade_cenario:.0f}%" if cenario.relacao_com_ajuste.probabilidade_cenario else "—")

st.divider()

# ------------------------------------------------------------
# 3. Comportamentos em relação ao ajuste
# ------------------------------------------------------------
st.subheader("Comportamentos possíveis (heurística)")

cb = cenario.comportamentos
itens = [
    ("Romper e continuar", cb.romper_e_continuar),
    ("Testar e rejeitar", cb.testar_e_rejeitar),
    ("Testar e recuperar", cb.testar_e_recuperar),
    ("Retornar ao ajuste", cb.retornar_ao_ajuste),
    ("Falso rompimento", cb.falso_rompimento),
]

for nome, pct in itens:
    if pct is None:
        continue
    st.progress(min(1.0, pct / 100.0), text=f"{nome}: {pct:.0f}%")

st.caption("Probabilidades heurísticas. Serão substituídas por estatística quando houver histórico suficiente.")

st.divider()

# ------------------------------------------------------------
# 4. Níveis e contexto
# ------------------------------------------------------------
col_n, col_x = st.columns(2)

with col_n:
    st.subheader("Níveis")
    n = session.niveis
    niveis_show = [
        ("R2", n.r2),
        ("R1", n.r1),
        ("PP", n.pivot_pp),
        ("S1", n.s1),
        ("S2", n.s2),
        ("Ajuste", session.precos.ajuste),
        ("Last", session.precos.last_mt5),
    ]
    for label, val in niveis_show:
        if val is not None:
            st.write(f"**{label}:** {val:,.0f}")

with col_x:
    st.subheader("Contexto externo")
    if cenario.contexto_resumo:
        for linha in cenario.contexto_resumo:
            st.write(f"• {linha}")
    else:
        st.write("Sem contexto disponível.")

st.divider()

# ------------------------------------------------------------
# 5. Histórico recente
# ------------------------------------------------------------
with st.expander("Histórico recente de sessões"):
    try:
        svc = SessionHistoryService()
        recentes = svc.resumo_recente(7)
        if not recentes:
            st.write("Nenhum histórico ainda.")
        else:
            for r in reversed(recentes):
                st.write(
                    f"**{r.get('data')}** · {r.get('contrato')} · "
                    f"Ajuste {r.get('ajuste')} · Last {r.get('last_mt5')} · "
                    f"{r.get('distancia_pts'):+.0f} pts · {r.get('posicao')} · {r.get('direcao')}"
                )
    except Exception as e:
        st.write(f"Histórico indisponível: {e}")

st.caption(
    f"Fonte last: {session.metadata.fonte_last or '—'} · "
    f"Coleta: {session.metadata.timestamp_coleta or '—'} · "
    "Assistente de cenário — não é recomendação de trade."
)
