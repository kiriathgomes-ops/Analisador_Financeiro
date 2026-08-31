# -*- coding: utf-8 -*-
"""
Módulo: pages/7.3_📥_Gerador_Profit_Pro.py
Versão: 3.0 - Produção Completa V2
Objetivo: Gerar códigos NTSL (Nelogica) dinâmicos injetando níveis do Motor de Regras e da Visão IA.
"""

import streamlit as st
import json
from datetime import datetime
from pathlib import Path

# Importação de caminhos centralizados e seguros do seu config.py
from config import COLETAS_DIR, FILE_DECISAO_V2, FILE_SMC_REGRAS

# Definição do caminho do arquivo de Visão IA (que não possui constante direta no config)
FILE_SMC_VISAO_IA = COLETAS_DIR / "AnaliseGraficaSMC.json"

def carregar_json_defensivo(caminho_path):
    """Carrega arquivos JSON de forma segura sem quebrar a renderização da UI."""
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# --- CONFIGURAÇÃO GLOBAL ---
st.set_page_config(page_title="Quant Terminal - Gerador ProfitPro", layout="wide")

# Carga assíncrona de arquivos do ecossistema V2
dados_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
regras_algo = carregar_json_defensivo(FILE_SMC_REGRAS)
visao_ia = carregar_json_defensivo(FILE_SMC_VISAO_IA)

# --- CORPO DA INTERFACE ---
st.markdown("<h2 style='color:#00d4ff;'>📥 Gerador Avançado ProfitPro (NTSL)</h2>", unsafe_allow_html=True)
st.caption("Converte a inteligência algorítmica e visual da sua mesa em indicadores reais para a B3")

st.info("💡 **Diretriz:** Cole o código gerado no Editor de Estratégias do ProfitPro (`Alt + Estrutura/Editor de Estratégias`).")

# --- SELEÇÕES DO OPERADOR (OPÇÕES DE SINAL) ---
col_param1, col_param2 = st.columns(2)

with col_param1:
    fonte_dados = st.selectbox(
        "🧠 Escolha a Fonte de Inteligência SMC:",
        ["Motor de Regras Algorítmico (SMC_Regras.json)", "Visão Inteligência Artificial (AnaliseGraficaSMC.json)"]
    )

with col_param2:
    tipo_indicador = st.selectbox(
        "🔷 Tipo de Script Nelogica (NTSL):",
        ["Linhas de Suporte / Resistência Institucional", "Regra de Coloração por Viés de Momentum"]
    )

# --- MAPEAMENTO E EXTRAÇÃO DE PREÇOS DINÂMICOS ---
precos_injetados = {}
vies_referencia = dados_v2.get("decisao", {}).get("vies_final", "NEUTRO")

if "Motor de Regras" in fonte_dados:
    st.markdown("### 📊 Dados Ativos: Motor Matemático MT5")
    # Tenta ler a entrada sugerida, se não houver usa o preço atual ou preço de OB
    ob_venda = next((ob for ob in regras_algo.get("order_blocks", []) if ob["tipo"] == "VENDA"), {})
    ob_compra = next((ob for ob in regras_algo.get("order_blocks", []) if ob["tipo"] == "COMPRA"), {})
    
    precos_injetados["Gatilho"] = regras_algo.get("entrada_sugerida") or regras_algo.get("preco_atual", 175000.0)
    precos_injetados["Resistencia"] = ob_venda.get("preco") or regras_algo.get("stop_sugerido") or (precos_injetados["Gatilho"] + 300)
    precos_injetados["Suporte"] = ob_compra.get("preco") or (precos_injetados["Gatilho"] - 300)
    vies_referencia = regras_algo.get("bias_direcional", vies_referencia)

else:
    st.markdown("### 🤖 Dados Ativos: Visão IA / Spike Imagem")
    # Parse dinâmico da lista de strings textuais do "AnaliseGraficaSMC.json" para extrair os números
    estruturas = visao_ia.get("estruturas_coletadas", [])
    niveis_extraidos = []
    
    for est in estruturas:
        try:
            # Pega o número que antecede o caractere ":"
            numero = float(est.split(":")[0].replace(".", "").strip())
            niveis_extraidos.append(numero)
        except:
            continue
            
    niveis_extraidos = sorted(niveis_extraidos)
    
    # Monta a hierarquia com os dados capturados pela visão computacional
    if len(niveis_extraidos) >= 3:
        precos_injetados["Suporte"] = niveis_extraidos[0]
        precos_injetados["Gatilho"] = niveis_extraidos[len(niveis_extraidos)//2]
        precos_injetados["Resistencia"] = niveis_extraidos[-1]
    else:
        # Fallback defensivo
        precos_injetados["Gatilho"] = preco_atual = dados_v2.get("decisao", {}).get("entrada", 175000.0)
        precos_injetados["Resistencia"] = precos_injetados["Gatilho"] + 400
        precos_injetados["Suporte"] = precos_injetados["Gatilho"] - 400
        
    vies_referencia = visao_ia.get("bias_direcional", vies_referencia)

# --- PROCESSAMENTO DOS SCRIPTS COMPILADOS ---
st.markdown("---")

if "Linhas" in tipo_indicador:
    st.markdown("#### 🛠️ Script NTSL: Indicador de Alvos e Níveis Críticos")
    
    codigo_ntsl = f"""{{
    Script NTSL gerado automaticamente pelo Quant Terminal V2 Python
    Fonte de Inteligencia: {fonte_dados}
    Data de Geracao: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
}}
Var
  LinhaResistencia : Real;
  LinhaGatilho     : Real;
  LinhaSuporte     : Real;

Inicio
  // Injecao dinamica de niveis calculados no ecossistema Python
  LinhaResistencia := {precos_injetados['Resistencia']:.0f};
  LinhaGatilho     := {precos_injetados['Gatilho']:.0f};
  LinhaSuporte     := {precos_injetados['Suporte']:.0f};

  // Plotagem e configuracao visual no ProfitPro
  Plot(LinhaResistencia);
  SetPlotColor(1, clVermelho);
  SetPlotStyle(1, 1); // Estilo Pontilhado institucional
  
  Plot2(LinhaGatilho);
  SetPlotColor(2, clBranco);
  SetPlotWidth(2, 2); // Destaque na regiao de gatilho
  
  Plot3(LinhaSuporte);
  SetPlotColor(3, clVerde);
  SetPlotStyle(3, 1);
Fim;"""

    st.code(codigo_ntsl, language="pascal")
    
    # Métricas de conferência do dia
    m1, m2, m3 = st.columns(3)
    m1.metric("Resistência Alvo", f"{precos_injetados['Resistencia']:,.0f} pts")
    m2.metric("Gatilho Central", f"{precos_injetados['Gatilho']:,.0f} pts")
    m3.metric("Suporte de Defesa", f"{precos_injetados['Suporte']:,.0f} pts")

else:
    st.markdown("#### 🎨 Script NTSL: Regra de Coloração por Viés Estrutural")
    
    # Normalização e higienização da string de viés para o ProfitPro
    vies_upper = vies_referencia.upper()
    if "COMPRA" in vies_upper or "BULL" in vies_upper or "ALTA" in vies_upper:
        cor_profit = "clVerde"
        status_label = "🟢 BULLISH / COMPRA"
    elif "VENDA" in vies_upper or "BEAR" in vies_upper or "BAIXA" in vies_upper:
        cor_profit = "clVermelho"
        status_label = "🔴 BEARISH / VENDA"
    else:
        cor_profit = "clBranco"
        status_label = "⚖️ NEUTRO / EQUILÍBRIO"
        
    codigo_ntsl_coloracao = f"""{{
    Script NTSL gerado automaticamente pelo Quant Terminal V2 Python
    Fonte de Inteligencia: {fonte_dados}
    Vies Mapeado: {vies_referencia}
}}
Inicio
  // Filtro de coloracao alinhado a confluencia institucional de hoje
  if (Close >= Open) entao
    PaintBar({cor_profit})
  senao
    PaintBar({cor_profit});
Fim;"""

    st.code(codigo_ntsl_coloracao, language="pascal")
    st.markdown(f"**Comportamento ativo da coloração:** `{status_label}`")

st.markdown("---")
st.caption("Módulo de geração em conformidade com as matrizes de dados do pipeline estruturado V2.")

