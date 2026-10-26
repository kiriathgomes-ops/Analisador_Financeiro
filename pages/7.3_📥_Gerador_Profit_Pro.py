# -*- coding: utf-8 -*-
"""
Módulo: pages/7.3_📥_Gerador_Profit_Pro.py
Versão: 6.3 - Master Script NTSL com espessura por TF e sufixos nos textos
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from config import COLETAS_DIR, FILE_DECISAO_V2

# Arquivos do Motor SMC para cada Timeframe
FILE_SMC_M5 = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"
FILE_SMC_M1 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json"
FILE_SMC_M15 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json"

def carregar_json_defensivo(caminho_path: Path) -> dict:
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def obter_tempo_ntsl(data_iso: str) -> tuple[str, str]:
    if not data_iso: return "0", "0"
    try:
        dt = datetime.fromisoformat(data_iso)
        data_str = f"ELDate({dt.year}, {dt.month}, {dt.day})"
        hora_str = dt.strftime("%H%M")
        if hora_str == "0000": hora_str = "0"
        return data_str, hora_str
    except ValueError:
        return "0", "0"

def formatar_linha_ntsl(preco, cor, line_width, estilo, texto, data_str, hora_str, variacao):
    if data_str != "0":
        param_tempo = f", {data_str}, 0, {variacao}, {hora_str}, 0"
    else:
        param_tempo = ", 0, 0, 0, 0, 0"
        
    # Agora recebe line_width dinâmico
    return f"        HorizontalLineCustom({int(preco)}, {cor}, {line_width}, {estilo}, \"{texto}\", 10, tpTopLeft{param_tempo});"

def construir_bloco_ntsl(dados_tf: dict, tipo_desejado: str, cor: str, estilo: int, line_width: int, tf_suf: str) -> list[str]:
    linhas = []
    
    if tipo_desejado in ["OB_COMPRA", "OB_VENDA"]:
        for ob in dados_tf.get("order_blocks", []):
            if tipo_desejado == "OB_COMPRA" and ob.get("tipo") != "COMPRA": continue
            if tipo_desejado == "OB_VENDA" and ob.get("tipo") != "VENDA": continue
            
            preco_abertura = ob.get("abertura")
            if preco_abertura is None or preco_abertura == 0:
                high, low = ob.get("high", 0), ob.get("low", 0)
                preco_abertura = int((high + low) / 2) if high > 0 and low > 0 else 0

            if preco_abertura > 0:
                variacao = 0 
                # Texto encurtado: "OB C-1" ou "OB V-15"
                texto = f"OB C-{tf_suf}" if ob.get("tipo") == "COMPRA" else f"OB V-{tf_suf}"
                dt, hr = obter_tempo_ntsl(ob.get("time", ""))
                linhas.append(formatar_linha_ntsl(int(preco_abertura), cor, line_width, estilo, texto, dt, hr, variacao))

    elif tipo_desejado == "FVG":
        for fvg in dados_tf.get("fair_value_gaps", []):
            sup, inf = fvg.get("superior", 0), fvg.get("inferior", 0)
            if sup > 0 and inf > 0:
                preco_central = int((sup + inf) / 2)
                variacao = int((sup - inf) / 2)
                dt, hr = obter_tempo_ntsl(fvg.get("time", ""))
                texto = f"FVG-{tf_suf}"
                linhas.append(formatar_linha_ntsl(preco_central, cor, line_width, estilo, texto, dt, hr, variacao))

    elif tipo_desejado in ["BSL", "SSL"]:
        liq = dados_tf.get("liquidez", {})
        lista = liq.get("bsl", []) if tipo_desejado == "BSL" else liq.get("ssl", [])
        for p in lista:
            if p > 0:
                texto = f"{tipo_desejado}-{tf_suf}"
                linhas.append(formatar_linha_ntsl(int(p), cor, line_width, estilo, texto, "0", "0", 0))
                
    return linhas

st.set_page_config(page_title="Quant Terminal - Master NTSL", layout="wide")
st.markdown("<h2 style='color:#00d4ff;'>📥 Gerador ProfitPro - Master Script</h2>", unsafe_allow_html=True)
st.warning("⚠️ **IMPORTANTE:** No Profit Pro, crie como **INDICADOR** e não como Estratégia. Se criar como estratégia, os botões de ligar/desligar vão aparecer escritos no gráfico.")

dados_m1 = carregar_json_defensivo(FILE_SMC_M1)
dados_m5 = carregar_json_defensivo(FILE_SMC_M5)
dados_m15 = carregar_json_defensivo(FILE_SMC_M15)
decisao_v2 = carregar_json_defensivo(FILE_DECISAO_V2)

# Montagem dos Inputs
linhas_input = ["input"]
for tf in ["1Min", "5Min", "15Min"]:
    linhas_input.append(f"    Habilitar{tf}(true);")
    for tipo in ["FVG", "SSL", "BSL", "OB"]:
        linhas_input.append(f"    Habilitar{tipo}_{tf}(true);")
linhas_input.append("    HabilitarPivo_POC(true);")
linhas_input.append("    HabilitarVWAP(true);")

linhas_inicio = ["Inicio"]

def gerar_bloco_se(condicao, linhas_codigo):
    if not linhas_codigo: return []
    bloco = [f"    Se {condicao} entao", "    Inicio"]
    bloco.extend(linhas_codigo)
    bloco.extend(["    Fim;", ""])
    return bloco

# --- Processamento dos Timeframes ---
# Lista com: (Nome, Dados, Espessura, Sufixo)
timeframes_config = [
    ("1Min", dados_m1, 1, "1"),
    ("5Min", dados_m5, 2, "5"),
    ("15Min", dados_m15, 3, "15")
]

for tf_nome, dados, width, tf_suf in timeframes_config:
    linhas_inicio.append(f"    // --- {tf_nome} (Espessura {width}) ---")
    linhas_inicio.append(f"    Se Habilitar{tf_nome} entao")
    linhas_inicio.append("    Inicio")
    linhas_inicio.append("")

    linhas_ob_c = construir_bloco_ntsl(dados, "OB_COMPRA", "clVerde", 0, width, tf_suf)
    linhas_ob_v = construir_bloco_ntsl(dados, "OB_VENDA", "clVermelho", 0, width, tf_suf)
    linhas_fvg  = construir_bloco_ntsl(dados, "FVG", "clAmarelo", 1, width, tf_suf)
    linhas_bsl  = construir_bloco_ntsl(dados, "BSL", "clAzul", 1, width, tf_suf)
    linhas_ssl  = construir_bloco_ntsl(dados, "SSL", "clFucsia", 1, width, tf_suf)

    linhas_ob = linhas_ob_c + linhas_ob_v
    
    linhas_inicio.extend(gerar_bloco_se(f"HabilitarOB_{tf_nome}", linhas_ob))
    linhas_inicio.extend(gerar_bloco_se(f"HabilitarFVG_{tf_nome}", linhas_fvg))
    linhas_inicio.extend(gerar_bloco_se(f"HabilitarBSL_{tf_nome}", linhas_bsl))
    linhas_inicio.extend(gerar_bloco_se(f"HabilitarSSL_{tf_nome}", linhas_ssl))

    linhas_inicio.append("    Fim;")
    linhas_inicio.append("")

# --- Processamento de POC, VWAP e Pivôs (Fora dos TFs, espessura 1) ---
dec = decisao_v2.get("decisao", {})
meta = dec.get("metadados", {})
smc_meta = meta.get("smc", {})
pivots = meta.get("pivots", {})

linhas_poc = []
poc = smc_meta.get("poc_ontem")
if poc:
    linhas_poc.append(formatar_linha_ntsl(int(poc), "clPurpura", 1, 1, "POC Ontem", "0", "0", 0))

for k, v in pivots.items():
    if v:
        linhas_poc.append(formatar_linha_ntsl(int(v), "clBranco", 1, 2, f"Pivô {k.upper()}", "0", "0", 0))

linhas_vwap = []
vwap = smc_meta.get("vwap_ontem")
if vwap:
    linhas_vwap.append(formatar_linha_ntsl(int(vwap), "clCinza", 1, 1, "VWAP Ontem", "0", "0", 0))

linhas_inicio.append("    // --- Níveis Institucionais e Pivôs ---")
linhas_inicio.extend(gerar_bloco_se("HabilitarPivo_POC", linhas_poc))
linhas_inicio.extend(gerar_bloco_se("HabilitarVWAP", linhas_vwap))

linhas_inicio.append("Fim;")

script_final = "\n".join(linhas_input) + "\n\n" + "\n".join(linhas_inicio)

st.markdown(f"#### 📜 Código NTSL Master Gerado")
st.code(script_final, language="pascal")

with st.expander("🔍 Resumo do que foi injetado no código"):
    st.markdown(f"""
    - **M1:** {len(dados_m1.get('order_blocks', []))} OBs, {len(dados_m1.get('fair_value_gaps', []))} FVGs. (Espessura 1)
    - **M5:** {len(dados_m5.get('order_blocks', []))} OBs, {len(dados_m5.get('fair_value_gaps', []))} FVGs. (Espessura 2)
    - **M15:** {len(dados_m15.get('order_blocks', []))} OBs, {len(dados_m15.get('fair_value_gaps', []))} FVGs. (Espessura 3)
    """)