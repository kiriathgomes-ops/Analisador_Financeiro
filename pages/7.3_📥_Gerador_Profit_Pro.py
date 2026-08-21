#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pages/8_📥_Gerador_Profit_Pro.py
================================
Gera script .txt de linhas horizontais para o Profit Pro.

Fontes de níveis (nesta ordem de prioridade na UI):
1. AnaliseGraficaSMC_Regras.json  (motor de regras)
2. AnaliseGraficaSMC.json         (visão IA, se existir)
3. Texto colado da IA             (tabela markdown / regex)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Gerador Profit Pro - Spike",
    page_icon="📥",
    layout="wide",
)

st.markdown(
    """
<style>
.stApp {
    background: linear-gradient(180deg, #0a0e17 0%, #0e1117 50%, #121620 100%);
}
.card-gerador {
    background: #161b22;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #2a2d4a;
    margin-top: 12px;
}
.card-gerador h4 { color: #00d4ff; margin-top: 0; }
.card-nivel {
    background: #1a1c2a;
    border-left: 4px solid #58a6ff;
    padding: 10px 16px;
    margin: 6px 0;
    border-radius: 6px;
    font-size: 0.9rem;
}
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = Path(__file__).resolve().parent.parent
COLETAS_DIR = BASE_DIR / "Coletas"
ARQ_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
ARQ_VISAO = COLETAS_DIR / "AnaliseGraficaSMC.json"

MAPEAMENTO_CORES = {
    "STRONG HIGH": "clRed",
    "STRONG LOW": "clGreen",
    "WEAK HIGH": "clRed",
    "WEAK LOW": "clGreen",
    "SUPPLY ZONE": "clRed",
    "DEMAND ZONE": "clGreen",
    "ORDER BLOCK": "clRed",
    "OB VENDA": "clRed",
    "OB COMPRA": "clGreen",
    "FVG": "clYellow",
    "FAIR VALUE GAP": "clYellow",
    "EQH": "clBlue",
    "EQL": "clBlue",
    "LIQUIDEZ": "clBlue",
    "BSL": "clBlue",
    "SSL": "clBlue",
    "PDH": "clFuchsia",
    "PDL": "clFuchsia",
    "PWH": "clAqua",
    "PWL": "clAqua",
    "EQUILIBRIUM": "clWhite",
    "COTAÇÃO ATUAL": "clYellow",
    "REJEIÇÃO": "clSilver",
    "PIVOT": "clSilver",
    "BOS": "clLime",
    "CHOCH": "clLime",
    "ENTRADA": "clAqua",
    "STOP": "clRed",
    "ALVO": "clLime",
    "DEFAULT": "clSilver",
}


def obter_cor(conceito: str) -> str:
    conceito_upper = conceito.upper()
    for chave, cor in MAPEAMENTO_CORES.items():
        if chave in conceito_upper:
            return cor
    return MAPEAMENTO_CORES["DEFAULT"]


def carregar_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def niveis_from_regras(dados: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Converte AnaliseGraficaSMC_Regras.json em lista de níveis Profit."""
    niveis: List[Dict[str, Any]] = []

    def add(preco: float, descricao: str, tipo: str):
        if preco is None:
            return
        try:
            p = float(preco)
        except (TypeError, ValueError):
            return
        if p <= 0:
            return
        niveis.append(
            {
                "tipo": tipo,
                "preco": p,
                "descricao": descricao,
                "observacao": "",
                "cor": obter_cor(tipo + " " + descricao),
            }
        )

    for ob in dados.get("order_blocks") or []:
        tipo = f"OB {ob.get('tipo', '')}".strip()
        add(ob.get("preco"), tipo, tipo)
        # bordas do bloco
        add(ob.get("high"), f"{tipo} High", tipo)
        add(ob.get("low"), f"{tipo} Low", tipo)

    for fvg in dados.get("fair_value_gaps") or []:
        if fvg.get("preenchido"):
            continue
        tipo = f"FVG {fvg.get('tipo', '')}".strip()
        mid = (float(fvg.get("superior", 0)) + float(fvg.get("inferior", 0))) / 2
        add(mid, tipo, "FVG")
        add(fvg.get("superior"), f"{tipo} Top", "FVG")
        add(fvg.get("inferior"), f"{tipo} Bot", "FVG")

    liq = dados.get("liquidez") or {}
    for p in liq.get("bsl") or []:
        add(p, "BSL Liquidez", "BSL")
    for p in liq.get("ssl") or []:
        add(p, "SSL Liquidez", "SSL")

    if dados.get("entrada_sugerida"):
        add(dados["entrada_sugerida"], "Entrada sugerida", "ENTRADA")
    if dados.get("stop_sugerido"):
        add(dados["stop_sugerido"], "Stop sugerido", "STOP")
    for i, a in enumerate(dados.get("alvos") or [], 1):
        add(a, f"Alvo {i}", "ALVO")

    if dados.get("preco_atual"):
        add(dados["preco_atual"], "Cotação atual", "COTAÇÃO ATUAL")

    # dedup por preço arredondado
    vistos = set()
    unicos = []
    for n in niveis:
        chave = round(n["preco"], 0)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(n)
    unicos.sort(key=lambda x: x["preco"], reverse=True)
    return unicos


def extrair_niveis_do_texto(resposta_ia: str) -> List[Dict[str, Any]]:
    niveis: List[Dict[str, Any]] = []
    linhas_tabela = [l.strip() for l in resposta_ia.split("\n") if l.strip().startswith("|")]

    if len(linhas_tabela) >= 2:
        for linha in linhas_tabela:
            if re.match(r"^\|\s*-+", linha):
                continue
            cols = [c.strip() for c in linha.strip("|").split("|")]
            if len(cols) < 2:
                continue
            if cols[0].lower() in ("nível", "nivel", "preço", "preco", "conceito", "tipo"):
                continue
            preco = None
            descricao = cols[0]
            for c in cols:
                m = re.search(r"(\d{2,3}(?:[.\s]\d{3})+(?:[.,]\d+)?|\d{4,})", c.replace(" ", ""))
                if m:
                    try:
                        preco = float(m.group(1).replace(".", "").replace(",", "."))
                        if preco < 1000:
                            preco = float(m.group(1).replace(",", ""))
                    except ValueError:
                        continue
                    break
            if preco and preco > 1000:
                niveis.append(
                    {
                        "tipo": descricao,
                        "preco": preco,
                        "descricao": descricao,
                        "observacao": cols[2] if len(cols) > 2 else "",
                        "cor": obter_cor(descricao),
                    }
                )

    # fallback regex preços
    if not niveis:
        for m in re.finditer(
            r"(OB|FVG|BSL|SSL|Swing|Suporte|Resistência|Alvo|Stop|Entrada)[^\d]{0,40}(\d{2,3}[.\s]?\d{3})",
            resposta_ia,
            flags=re.IGNORECASE,
        ):
            try:
                preco = float(m.group(2).replace(" ", "").replace(".", ""))
                if preco < 10000:
                    preco = float(m.group(2).replace(" ", "").replace(",", "."))
                niveis.append(
                    {
                        "tipo": m.group(1),
                        "preco": preco,
                        "descricao": m.group(0)[:60],
                        "observacao": "",
                        "cor": obter_cor(m.group(1)),
                    }
                )
            except ValueError:
                continue

    vistos = set()
    unicos = []
    for n in niveis:
        chave = (n["tipo"], round(n["preco"], 0))
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(n)
    return unicos


def gerar_script_profit_pro(niveis: List[Dict[str, Any]]) -> str:
    linhas = []
    linhas.append("// ==========================================")
    linhas.append("// SCRIPT GERADO PELO SPIKE - NÍVEIS SMC/ICT")
    linhas.append(f"// DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append(f"// TOTAL DE NÍVEIS: {len(niveis)}")
    linhas.append("// ==========================================")
    linhas.append("")
    linhas.append("var")
    for i in range(1, len(niveis) + 1):
        linhas.append(f"  Linha{i} : float;")
    linhas.append("")
    linhas.append("inicio")
    linhas.append("  // DEFINIÇÃO DOS NÍVEIS DE PREÇO //////////////////////////////////////////////////")
    for i, nivel in enumerate(niveis, start=1):
        preco = nivel["preco"]
        linhas.append(f"  Linha{i} := {preco:.0f}; // {nivel['descricao']}")
    linhas.append("")
    linhas.append("  // PLOTAGEM DE LINHAS HORIZONTAIS CUSTOMIZADAS ////////////////////////////////////")
    for i, nivel in enumerate(niveis, start=1):
        cor = nivel["cor"]
        descricao = nivel["descricao"].replace('"', "")
        linhas.append(
            f'  HorizontalLineCustom(Linha{i}, {cor}, 1, 0, "{descricao}", 10, tpTopRight, Date, 0, MinPriceIncrement);'
        )
    linhas.append("fim;")
    return "\n".join(linhas)


# ============================================================
# UI
# ============================================================
st.title("📥 Gerador de Script para Profit Pro")
st.caption("Níveis SMC por regras, visão IA ou texto colado → script .txt Profit")

fonte = st.radio(
    "Fonte dos níveis",
    [
        "Motor SMC Regras (JSON)",
        "Visão IA (AnaliseGraficaSMC.json)",
        "Colar texto da IA",
    ],
    horizontal=True,
)

niveis: List[Dict[str, Any]] = []
origem = ""

if fonte == "Motor SMC Regras (JSON)":
    dados = carregar_json(ARQ_REGRAS)
    if not dados:
        st.warning("Arquivo `Coletas/AnaliseGraficaSMC_Regras.json` não encontrado. Rode o pipeline ou a página SMC Regras.")
    elif dados.get("erro"):
        st.error(f"JSON de regras com erro: {dados['erro']}")
    else:
        niveis = niveis_from_regras(dados)
        origem = f"regras • bias={dados.get('bias_direcional')} • {dados.get('timestamp', '')}"
        st.success(f"{len(niveis)} níveis extraídos do motor de regras")

elif fonte == "Visão IA (AnaliseGraficaSMC.json)":
    dados = carregar_json(ARQ_VISAO)
    if not dados:
        st.warning("`AnaliseGraficaSMC.json` não encontrado.")
    else:
        # tenta mesmos campos; senão usa estruturas_coletadas como texto
        niveis = niveis_from_regras(dados)
        if not niveis:
            texto = "\n".join(dados.get("estruturas_coletadas") or [])
            texto += "\n" + "\n".join(dados.get("liquidez_relevante") or [])
            niveis = extrair_niveis_do_texto(texto)
        origem = "visão IA"
        st.success(f"{len(niveis)} níveis a partir da visão")

else:
    st.markdown("### Cole a resposta da IA (tabela SMC)")
    resposta_ia = st.text_area(
        "📝 Resposta da IA",
        placeholder="Cole aqui a tabela ou análise SMC...",
        height=240,
    )
    if st.button("🔍 Extrair do texto", type="primary"):
        niveis = extrair_niveis_do_texto(resposta_ia or "")
        origem = "texto colado"
        if not niveis:
            st.warning("Nenhum nível identificado.")
        else:
            st.success(f"{len(niveis)} níveis extraídos")

if niveis:
    st.markdown("---")
    st.markdown(f"### Níveis ({len(niveis)}) · {origem}")
    for n in niveis:
        st.markdown(
            f'<div class="card-nivel"><b>{n["preco"]:,.0f}</b> — {n["descricao"]} '
            f'<span style="opacity:.6">({n["cor"]})</span></div>',
            unsafe_allow_html=True,
        )

    script = gerar_script_profit_pro(niveis)
    st.markdown("### Script Profit Pro")
    st.code(script, language="pascal")
    st.download_button(
        "⬇️ Baixar .txt",
        data=script,
        file_name=f"niveis_smc_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
    )
    st.info("No Profit Pro: abra o editor de estratégia/indicador e cole o script (sintaxe HorizontalLineCustom).")

st.caption("Spike • Gerador Profit Pro • Regras + Visão + Texto")
