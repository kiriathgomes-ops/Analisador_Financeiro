#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages/9_📊_SMC_Regras.py
========================
Dashboard do Motor SMC por regras (sem IA).

Lê: Coletas/AnaliseGraficaSMC_Regras.json
Permite: atualizar via MT5, ver OBs/FVGs/estrutura, baixar JSON.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS = BASE_DIR / "Coletas"
ARQUIVO_REGRAS = COLETAS / "AnaliseGraficaSMC_Regras.json"
ARQUIVO_VISAO = COLETAS / "AnaliseGraficaSMC.json"
SCRIPT_RODAR = BASE_DIR / "Rodar_SMC_Regras.py"

st.set_page_config(
    page_title="SMC Regras",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
<style>
.stApp { background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%); }
.card {
    background: #161b22; border: 1px solid #30363d; border-radius: 10px;
    padding: 14px 16px; margin-bottom: 10px;
}
.card h4 { margin: 0 0 8px 0; color: #58a6ff; }
.badge-alta { color: #3fb950; font-weight: 700; }
.badge-baixa { color: #f85149; font-weight: 700; }
.badge-lat { color: #d29922; font-weight: 700; }
.nivel {
    background: #1a1c2a; border-left: 4px solid #58a6ff;
    padding: 8px 12px; margin: 4px 0; border-radius: 6px; font-size: 0.9rem;
}
.nivel.ob-compra { border-left-color: #3fb950; }
.nivel.ob-venda { border-left-color: #f85149; }
.nivel.fvg { border-left-color: #d29922; }
.nivel.liq { border-left-color: #58a6ff; }
</style>
""",
    unsafe_allow_html=True,
)


def carregar_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def badge_bias(bias: str) -> str:
    b = (bias or "LATERAL").upper()
    if b == "ALTA":
        return f'<span class="badge-alta">🟢 {b}</span>'
    if b == "BAIXA":
        return f'<span class="badge-baixa">🔴 {b}</span>'
    return f'<span class="badge-lat">🟡 {b}</span>'


def rodar_motor() -> bool:
    if not SCRIPT_RODAR.exists():
        st.error(f"Script não encontrado: {SCRIPT_RODAR}")
        return False
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPT_RODAR)],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(BASE_DIR),
        )
        if r.stdout:
            st.code(r.stdout[-2000:], language="text")
        if r.returncode != 0 and r.stderr:
            st.warning(r.stderr[-1000:])
        return r.returncode == 0
    except Exception as e:
        st.error(str(e))
        return False


# ============================================================
# UI
# ============================================================
st.title("📊 SMC por Regras")
st.caption("Motor local (BOS / CHoCH / OB / FVG / Liquidez) — sem IA")

col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    if st.button("🔄 Atualizar agora (MT5)", type="primary"):
        with st.spinner("Rodando Motor_SMC_Regras via MT5..."):
            ok = rodar_motor()
            if ok:
                st.success("Atualizado")
                st.rerun()
with col_b:
    st.caption(f"Regras: {'✅' if ARQUIVO_REGRAS.exists() else '❌'}")
with col_c:
    st.caption(f"Visão IA: {'✅' if ARQUIVO_VISAO.exists() else '❌'}")

dados = carregar_json(ARQUIVO_REGRAS)
if not dados:
    st.warning(
        "Arquivo `AnaliseGraficaSMC_Regras.json` não encontrado. "
        "Rode o pipeline ou clique em **Atualizar agora**."
    )
    st.stop()

if dados.get("erro"):
    st.error(f"Última execução com erro: {dados['erro']}")

# --- Resumo ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Preço", f"{dados.get('preco_atual', 0):,.0f}")
c2.markdown("**Bias**", unsafe_allow_html=True)
c2.markdown(badge_bias(str(dados.get("bias_direcional", "LATERAL"))), unsafe_allow_html=True)
c3.metric("Confiança", f"{dados.get('confianca_visual', 0)}/100")
c4.metric("BOS", "Sim" if dados.get("bos") else "Não")
c5.metric("CHoCH", "Sim" if dados.get("choch") else "Não")

st.caption(
    f"TF {dados.get('timeframe')} • {dados.get('simbolo_mt5', dados.get('ativo'))} • "
    f"{dados.get('timestamp', '')} • fonte={dados.get('fonte')}"
)

# --- Setup operacional ---
st.markdown("---")
st.subheader("🎯 Setup sugerido")
e1, e2, e3 = st.columns(3)
entrada = dados.get("entrada_sugerida")
stop = dados.get("stop_sugerido")
alvos = dados.get("alvos") or []
e1.metric("Entrada", f"{entrada:,.0f}" if entrada else "—")
e2.metric("Stop", f"{stop:,.0f}" if stop else "—")
e3.metric("Alvos", ", ".join(f"{a:,.0f}" for a in alvos) if alvos else "—")

cenarios = dados.get("zonas_de_interesse_e_cenarios") or []
if cenarios:
    st.markdown("**Cenários**")
    for c in cenarios:
        st.info(c)

# --- Colunas OB / FVG / Liquidez ---
st.markdown("---")
col_ob, col_fvg, col_liq = st.columns(3)

with col_ob:
    st.markdown("### Order Blocks")
    for ob in dados.get("order_blocks") or []:
        cls = "ob-compra" if ob.get("tipo") == "COMPRA" else "ob-venda"
        st.markdown(
            f'<div class="nivel {cls}"><b>OB {ob.get("tipo")}</b> · '
            f'{ob.get("preco", 0):,.0f}<br>'
            f'<span style="opacity:.8">{ob.get("low", 0):,.0f} – {ob.get("high", 0):,.0f}</span></div>',
            unsafe_allow_html=True,
        )
    if not dados.get("order_blocks"):
        st.caption("Nenhum OB")

with col_fvg:
    st.markdown("### Fair Value Gaps")
    for fvg in dados.get("fair_value_gaps") or []:
        st.markdown(
            f'<div class="nivel fvg"><b>FVG {fvg.get("tipo")}</b><br>'
            f'{fvg.get("inferior", 0):,.0f} – {fvg.get("superior", 0):,.0f}'
            f'{" · preenchido" if fvg.get("preenchido") else ""}</div>',
            unsafe_allow_html=True,
        )
    if not dados.get("fair_value_gaps"):
        st.caption("Nenhum FVG aberto")

with col_liq:
    st.markdown("### Liquidez")
    liq = dados.get("liquidez") or {}
    for p in liq.get("bsl") or []:
        st.markdown(
            f'<div class="nivel liq"><b>BSL</b> (acima) · {p:,.0f}</div>',
            unsafe_allow_html=True,
        )
    for p in liq.get("ssl") or []:
        st.markdown(
            f'<div class="nivel liq"><b>SSL</b> (abaixo) · {p:,.0f}</div>',
            unsafe_allow_html=True,
        )
    for t in dados.get("liquidez_relevante") or []:
        st.caption(t)
    if not liq.get("bsl") and not liq.get("ssl"):
        st.caption("Sem equal highs/lows")

# --- Estrutura / eventos ---
st.markdown("---")
c_ev, c_sw = st.columns(2)
with c_ev:
    st.markdown("### Eventos BOS / CHoCH")
    for e in dados.get("eventos_estrutura") or []:
        st.write(
            f"**{e.get('tipo')}** {e.get('direcao')} @ {e.get('preco', 0):,.0f} · {e.get('time', '')}"
        )
with c_sw:
    st.markdown("### Swings recentes")
    for s in (dados.get("swings_recentes") or [])[-8:]:
        st.write(f"{s.get('tipo')} · {s.get('preco', 0):,.0f} · {s.get('time', '')}")

# --- Estruturas texto (prompt) ---
with st.expander("📋 estruturas_coletadas (texto para IA / Profit)"):
    for item in dados.get("estruturas_coletadas") or []:
        st.write(f"- {item}")

# --- Comparar com visão ---
visao = carregar_json(ARQUIVO_VISAO)
if visao:
    with st.expander("🔀 Comparar com AnaliseGraficaSMC.json (visão)"):
        st.write(
            {
                "regras_bias": dados.get("bias_direcional"),
                "visao_bias": visao.get("bias_direcional") or visao.get("direcao_estrutura"),
                "regras_conf": dados.get("confianca_visual"),
                "visao_keys": list(visao.keys())[:20],
            }
        )

with st.expander("📄 JSON completo"):
    st.json(dados)

st.download_button(
    "⬇️ Baixar AnaliseGraficaSMC_Regras.json",
    data=json.dumps(dados, indent=2, ensure_ascii=False),
    file_name="AnaliseGraficaSMC_Regras.json",
    mime="application/json",
)

st.caption("Spike • SMC Regras • BOS/CHoCH/OB/FVG")
