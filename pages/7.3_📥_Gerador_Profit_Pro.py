# -*- coding: utf-8 -*-
"""
Módulo: pages/7.3_📥_Gerador_Profit_Pro.py
Versão: 4.0 - SMC Multi-Levels (Produção V2)
Objetivo: Gerar scripts NTSL dinâmicos plotando TODOS os níveis mapeados pelo Motor e pela Visão IA.
"""

import streamlit as st
import json
import re
import pandas as pd 
from datetime import datetime
from pathlib import Path

# Importação de caminhos centralizados do seu config.py
from config import COLETAS_DIR, FILE_DECISAO_V2, FILE_SMC_REGRAS

# Definição do caminho do arquivo de Visão IA
FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho_path):
    """Carrega arquivos JSON de forma defensiva protegendo a UI contra falhas."""
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# --- CONFIGURAÇÃO GLOBAL ---
st.set_page_config(page_title="Quant Terminal - Gerador Multi-Levels", layout="wide")

# Carga de arquivos V2
regras_algo = carregar_json_defensivo(FILE_SMC_REGRAS)
visao_ia = carregar_json_defensivo(FILE_SMC_VISAO_IA)

# --- CORPO DA INTERFACE ---
st.markdown("<h2 style='color:#00d4ff;'>📥 Gerador ProfitPro - Plotagem de Níveis em Massa</h2>", unsafe_allow_html=True)
st.caption("Exportador dinâmico de código NTSL contendo mapeamento completo de estruturas macro e micro")

# --- SELEÇÃO DE INTELIGÊNCIA ---
fonte_dados = st.selectbox(
    "🧠 Selecione a matriz de dados para extração de níveis:",
    ["Motor de Regras Algorítmico (AnaliseGraficaSMC_Regras.json)", "Visão Inteligência Artificial (AnaliseGraficaSMC.json)"]
)

st.markdown("---")

# Dicionário unificado para guardar os níveis e suas respectivas cores de exibição no Profit
# Chave: Preço (int) | Valor: Cor do Profit (clVerde, clVermelho, clAzul, etc)
niveis_mapeados = {}

if "Motor de Regras" in fonte_dados:
    st.markdown("### 📊 Níveis Identificados: Motor Matemático MT5")
    
    # 1. Coleta de Order Blocks
    for ob in regras_algo.get("order_blocks", []):
        preco = int(ob.get("preco", 0))
        if preco > 0:
            niveis_mapeados[preco] = "clVerde" if ob.get("tipo") == "COMPRA" else "clVermelho"
            
    # 2. Coleta de Fair Value Gaps (Usa o ponto médio do Gap para traçar a linha)
    for fvg in regras_algo.get("fair_value_gaps", []):
        sup = fvg.get("superior", 0)
        inf = fvg.get("inferior", 0)
        if sup > 0 and inf > 0:
            meio_fvg = int((sup + inf) / 2)
            niveis_mapeados[meio_fvg] = "clAmarelo"
            
    # 3. Coleta de Liquidez (BSL e SSL)
    liq = regras_algo.get("liquidez", {})
    for p in liq.get("bsl", []):
        niveis_mapeados[int(p)] = "clAzul"
    for p in liq.get("ssl", []):
        niveis_mapeados[int(p)] = "clFucsia"
        
    # 4. Gatilhos operacionais adicionais se houverem
    if regras_algo.get("entrada_sugeriga"):
        niveis_mapeados[int(regras_algo["entrada_sugerida"])] = "clBranco"

else:
    st.markdown("### 🤖 Níveis Identificados: Visão IA / Spike Imagem")
    
    # Varre as estruturas textuais e extrai os números usando Regex de forma defensiva
    estruturas = visao_ia.get("estruturas_coletadas", [])
    
    for est in estruturas:
        # Encontra a pontuação no início da string (ex: "178.270: OB VENDA")
        match = re.match(r"^([\d\.]+)", est.strip())
        if match:
            try:
                preco_limpo = int(match.group(1).replace(".", ""))
                
                # Heurística de cor baseada no texto descritivo capturado pela IA
                est_lower = est.lower()
                if "compra" in est_lower or "low" in est_lower or "suporte" in est_lower:
                    cor = "clVerde"
                elif "venda" in est_lower or "high" in est_lower or "resistencia" in est_lower:
                    cor = "clVermelho"
                elif "fvg" in est_lower:
                    cor = "clAmarelo"
                else:
                    cor = "clBranco"
                    
                niveis_mapeados[preco_limpo] = cor
            except:
                continue

# --- CONSTRUÇÃO DINÂMICA DO CÓDIGO NTSL (PROFITPRO) ---
if niveis_mapeados:
    # Remove duplicidades mantendo a ordenação por preço
    precos_ordenados = sorted(list(niveis_mapeados.keys()))
    total_niveis = len(precos_ordenados)
    
    # 1. Montagem do Bloco de Variáveis (Var)
    linhas_var = []
    for idx in range(1, total_niveis + 1):
        linhas_var.append(f"  Nivel_{idx} : Real;")
    bloco_var = "\n".join(linhas_var)
    
    # 2. Montagem do Bloco de Atribuição e Plotagem (Inicio)
    linhas_codigo = []
    for idx, preco in enumerate(precos_ordenados, start=1):
        cor_escolhida = niveis_mapeados[preco]
        
        # Constrói o bloco Pascal para cada linha achada no JSON do seu ecossistema
        linhas_codigo.append(f"  Nivel_{idx} := {preco};")
        
        if idx == 1:
            linhas_codigo.append(f"  Plot(Nivel_{idx});")
            linhas_codigo.append(f"  SetPlotColor(1, {cor_escolhida});")
        else:
            linhas_codigo.append(f"  Plot{idx}(Nivel_{idx});")
            linhas_codigo.append(f"  SetPlotColor({idx}, {cor_escolhida});")
            
        # Linha pontilhada (estilo 1) para FVGs e Liquidez, contínua para OBs
        if cor_escolhida in ["clAmarelo", "clAzul", "clFucsia"]:
            linhas_codigo.append(f"  SetPlotStyle({idx}, 1);")
            
    bloco_atribuicao = "\n".join(linhas_codigo)
    
    # 3. Compilação do Script NTSL Final
    script_final = f"""{{
    Script NTSL gerado automaticamente pelo Quant Terminal V2 Python
    Fonte de Inteligencia: {fonte_dados}
    Total de Niveis Identificados: {total_niveis}
    Data de Geracao: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
    
    Legenda de Cores Injetadas:
    • Verde    ➔ Regiões de Compra / OB Compra / Strong Low
    • Vermelho ➔ Regiões de Venda / OB Venda / Strong High
    • Amarelo  ➔ Fair Value Gaps (FVG) / Desequilíbrio
    • Azul     ➔ Liquidez Compradora (BSL)
    • Fucsia   ➔ Liquidez Vendedora (SSL)
}}
Var
{bloco_var}

Inicio
{bloco_atribuicao}
Fim;"""

    # --- EXIBIÇÃO NA UI STREAMLIT ---
    st.markdown(f"#### 📜 Código NTSL Gerado ({total_niveis} Níveis Ativos)")
    st.code(script_final, language="pascal")
    
    # Painel de conferência em colunas ou expander
    with st.expander("🔍 Visualizar Tabela de Auditoria dos Níveis Injetados"):
        linhas_auditoria = []
        for p in precos_ordenados:
            linhas_auditoria.append({"Preço (Pontos)": f"{p:,.0f}", "Cor Associada": niveis_mapeados[p].replace("cl", "")})
        st.table(pd.DataFrame(linhas_auditoria))

else:
    st.warning("⚠️ Nenhum nível válido foi encontrado no arquivo JSON selecionado. Aguardando processamento do pipeline.")
