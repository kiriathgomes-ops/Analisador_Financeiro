# -*- coding: utf-8 -*-
"""
Módulo: pages/7.3_📥_Gerador_Profit_Pro.py
Versão: 5.4 - Exportação NTSL com projeção de linha até o presente (EndDate=0)
"""

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import COLETAS_DIR, FILE_DECISAO_V2, FILE_SMC_REGRAS

FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho_path: Path) -> dict:
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def obter_tempo_ntsl(data_iso: str) -> tuple[str, str]:
    """
    Converte string ISO para o formato do NTSL.
    Retorna (data_string, hora_string).
    Ex: "2026-10-13T10:30:00" -> ("ELDate(2026, 10, 13)", "1030")
    """
    if not data_iso:
        return "0", "0"
    try:
        dt = datetime.fromisoformat(data_iso)
        data_str = f"ELDate({dt.year}, {dt.month}, {dt.day})"
        hora_str = dt.strftime("%H%M")
        # Se for meia-noite, envia 0 para preencher o dia inteiro
        if hora_str == "0000":
            hora_str = "0"
        return data_str, hora_str
    except ValueError:
        return "0", "0"

st.set_page_config(page_title="Quant Terminal - Gerador Multi-Levels", layout="wide")
st.markdown("<h2 style='color:#00d4ff;'>📥 Gerador ProfitPro - Níveis (NTSL)</h2>", unsafe_allow_html=True)
st.caption("Exportador dinâmico via `HorizontalLineCustom` com marcação temporal (ELDate).")

fonte_dados = st.selectbox(
    "🧠 Selecione a matriz de dados:",
    ["Motor de Regras Algorítmico (AnaliseGraficaSMC_Regras.json)", "Visão Inteligência Artificial (AnaliseGraficaSMC.json)"]
)

st.markdown("### 🎛️ Filtros de Exportação")
c1, c2, c3, c4 = st.columns(4)
with c1: exp_ob = st.checkbox("Order Blocks (OB)", value=True)
with c2: exp_fvg = st.checkbox("Fair Value Gaps (FVG)", value=True)
with c3: exp_liq = st.checkbox("Liquidez (BSL/SSL)", value=True)
with c4: exp_pivots = st.checkbox("Pivôs, POC e VWAP", value=True)

st.markdown("---")

regras_algo = carregar_json_defensivo(FILE_SMC_REGRAS)
visao_ia = carregar_json_defensivo(FILE_SMC_VISAO_IA)
decisao_v2 = carregar_json_defensivo(FILE_DECISAO_V2)

niveis_mapeados = {}

if "Motor de Regras" in fonte_dados:
    st.markdown("### 📊 Níveis Identificados: Motor Matemático MT5")
    
    # 1. Order Blocks
    if exp_ob:
        for ob in regras_algo.get("order_blocks", []):
            high = ob.get("high", 0)
            low = ob.get("low", 0)
            if high > 0 and low > 0:
                preco_central = int((high + low) / 2)
                variacao = int((high - low) / 2)
                cor = "clVerde" if ob.get("tipo") == "COMPRA" else "clVermelho"
                texto = "OB COMPRA" if ob.get("tipo") == "COMPRA" else "OB VENDA"
                data_ntsl, hora_ntsl = obter_tempo_ntsl(ob.get("time", ""))
                
                niveis_mapeados[f"OB_{preco_central}"] = {
                    "preco": preco_central, "variacao": variacao, "cor": cor, "texto": texto, "estilo": 0, "data": data_ntsl, "hora": hora_ntsl
                }

    # 2. Fair Value Gaps
    if exp_fvg:
        for i, fvg in enumerate(regras_algo.get("fair_value_gaps", [])):
            sup = fvg.get("superior", 0)
            inf = fvg.get("inferior", 0)
            if sup > 0 and inf > 0:
                preco_central = int((sup + inf) / 2)
                variacao = int((sup - inf) / 2)
                data_ntsl, hora_ntsl = obter_tempo_ntsl(fvg.get("time", ""))
                
                niveis_mapeados[f"FVG_{i}"] = {
                    "preco": preco_central, "variacao": variacao, "cor": "clAmarelo", "texto": "FVG", "estilo": 1, "data": data_ntsl, "hora": hora_ntsl
                }

    # 3. Liquidez
    if exp_liq:
        liq = regras_algo.get("liquidez", {})
        for p in liq.get("bsl", []):
            if p > 0:
                niveis_mapeados[f"BSL_{p}"] = {"preco": int(p), "variacao": 0, "cor": "clAzul", "texto": "BSL", "estilo": 1, "data": "0", "hora": "0"}
        for p in liq.get("ssl", []):
            if p > 0:
                niveis_mapeados[f"SSL_{p}"] = {"preco": int(p), "variacao": 0, "cor": "clFucsia", "texto": "SSL", "estilo": 1, "data": "0", "hora": "0"}

else:
    st.markdown("### 🤖 Níveis Identificados: Visão IA")
    estruturas = visao_ia.get("estruturas_coletadas", [])
    for i, est in enumerate(estruturas):
        match = re.match(r"^([\d\.]+)", est.strip())
        if match:
            try:
                preco_limpo = int(match.group(1).replace(".", ""))
                est_lower = est.lower()
                if "compra" in est_lower or "low" in est_lower or "suporte" in est_lower:
                    cor, texto = "clVerde", "IA Suporte"
                elif "venda" in est_lower or "high" in est_lower or "resistencia" in est_lower:
                    cor, texto = "clVermelho", "IA Resist."
                elif "fvg" in est_lower:
                    cor, texto = "clAmarelo", "IA FVG"
                else:
                    cor, texto = "clBranco", "IA Nível"
                    
                niveis_mapeados[f"IA_{i}"] = {"preco": preco_limpo, "variacao": 0, "cor": cor, "texto": texto, "estilo": 1, "data": "0", "hora": "0"}
            except Exception:
                continue

if exp_pivots:
    dec = decisao_v2.get("decisao", {})
    meta = dec.get("metadados", {})
    smc_meta = meta.get("smc", {})
    pivots = meta.get("pivots", {})

    poc = smc_meta.get("poc_ontem")
    if poc:
        niveis_mapeados["POC"] = {"preco": int(poc), "variacao": 0, "cor": "clPurpura", "texto": "POC Ontem", "estilo": 1, "data": "0", "hora": "0"}
        
    vwap = smc_meta.get("vwap_ontem")
    if vwap:
        niveis_mapeados["VWAP"] = {"preco": int(vwap), "variacao": 0, "cor": "clCinza", "texto": "VWAP Ontem", "estilo": 1, "data": "0", "hora": "0"}

    for k, v in pivots.items():
        if v:
            niveis_mapeados[f"PIV_{k}"] = {"preco": int(v), "variacao": 0, "cor": "clBranco", "texto": f"Pivô {k.upper()}", "estilo": 2, "data": "0", "hora": "0"}

if niveis_mapeados:
    linhas_codigo = []
    niveis_ordenados = sorted(niveis_mapeados.values(), key=lambda x: x["preco"])

    for item in niveis_ordenados:
        p, var, cor, txt, est, dt, hr = item["preco"], item["variacao"], item["cor"], item["texto"], item["estilo"], item["data"], item["hora"]
        
        # Monta os parâmetros opcionais
        # Se tem data: StartDate=dt, EndDate=0 (até o presente), PriceVariation=var, StartTime=hr, EndTime=0 (até o fim)
        if dt != "0":
            param_tempo = f", {dt}, 0, {var}, {hr}, 0"
        # Se não tem data, mas tem preenchimento (PriceVariation)
        elif var > 0:
            param_tempo = f", 0, 0, {var}"
        # Se não tem data e nem preenchimento
        else:
            param_tempo = ""

        # HorizontalLineCustom(Price, Color, LineWidth, Style, Text, FontSize, TextPosition, StartDate, EndDate, PriceVariation, StartTime, EndTime)
        linha_ntsl = (
            f"HorizontalLineCustom({p}, {cor}, 1, {est}, \"{txt}\", "
            f"10, tpTopRight{param_tempo});"
        )
        linhas_codigo.append(linha_ntsl)

    script_final = f"""{{
    Script NTSL gerado pelo Quant Terminal V2
    Fonte: {fonte_dados}
    Total de Niveis: {len(niveis_ordenados)}
    Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    
    Nota: As linhas de OB/FVG estendem até o presente (EndDate=0) e duram todo o dia (EndTime=0).
}}
Inicio
{chr(10).join(linhas_codigo)}
Fim;"""

    st.markdown(f"#### 📜 Código NTSL Gerado ({len(niveis_ordenados)} Níveis Ativos)")
    st.code(script_final, language="pascal")
    
    st.info("💡 Dica: Copie o código acima e cole no editor de indicadores do Profit Pro.")

    with st.expander("🔍 Visualizar Tabela de Auditoria dos Níveis Injetados"):
        linhas_auditoria = []
        for item in niveis_ordenados:
            data_str = str(item["data"]) if item["data"] != "0" else "Início do Gráfico"
            hora_str = str(item["hora"]) if item["hora"] != "0" else "Todo o dia"
            linhas_auditoria.append({
                "Preço": f"{item['preco']:,.0f}",
                "Texto": item["texto"],
                "Cor": item["cor"].replace("cl", ""),
                "Zona (Var)": item["variacao"],
                "Data": data_str,
                "Hora": hora_str
            })
        st.table(pd.DataFrame(linhas_auditoria))

else:
    st.warning("⚠️ Nenhum nível válido foi selecionado ou encontrado nos arquivos JSON.")