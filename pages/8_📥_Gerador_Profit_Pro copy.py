# ============================================================
# ARQUIVO: pages/8_📥_Gerador_Profit_Pro.py
# MOTIVO: Análise SMC + Gerador de Script .txt para Profit Pro
# CORES FIXAS: OB (Vermelho/Verde), FVG (Amarelo), Liquidez (Azul), etc.
# ============================================================

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
from dotenv import load_dotenv

# ============================================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Gerador Profit Pro - Spike",
    page_icon="📥",
    layout="wide"
)

# ============================================================
# CSS PERSONALIZADO
# ============================================================
st.markdown("""
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
.card-gerador h4 {
    color: #00d4ff;
    margin-top: 0;
}
.card-nivel {
    background: #1a1c2a;
    border-left: 4px solid #58a6ff;
    padding: 10px 16px;
    margin: 6px 0;
    border-radius: 6px;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CAMINHOS
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")

# ============================================================
# MAPEAMENTO DE CORES FIXAS PARA PROFIT PRO
# ============================================================
MAPEAMENTO_CORES = {
    "OB_VENDA": "clRed",
    "OB_COMPRA": "clGreen",
    "FVG": "clYellow",
    "LIQUIDEZ_SUPERIOR": "clBlue",
    "LIQUIDEZ_INFERIOR": "clBlue",
    "ENTRADA": "clLime",
    "STOP_LOSS": "clRed",
    "ALVO_1": "clGreen",
    "ALVO_2": "clGreen",
    "SUPORTE": "clBlue",
    "RESISTENCIA": "clRed",
    "PDH": "clFuchsia",
    "PDL": "clFuchsia",
    "PWH": "clAqua",
    "PWL": "clAqua",
    "DEFAULT": "clSilver"
}

# ============================================================
# FUNÇÃO: EXTRAIR NÍVEIS DA RESPOSTA DA IA
# ============================================================
def extrair_niveis_do_texto(resposta_ia: str) -> List[Dict[str, Any]]:
    """
    Extrai os níveis do texto da IA usando regex e palavras-chave.
    Retorna uma lista de dicionários: [{"tipo": "OB_VENDA", "preco": 180500, "descricao": "OB Venda"}]
    """
    niveis = []
    
    # Dicionário de padrões de busca
    padroes = {
        "OB_VENDA": r"(OB\s*Venda|Order\s*Block\s*Venda|OB\s*de\s*Venda).*?(\d{1,3}\.\d{3})",
        "OB_COMPRA": r"(OB\s*Compra|Order\s*Block\s*Compra|OB\s*de\s*Compra).*?(\d{1,3}\.\d{3})",
        "FVG": r"(FVG|Fair\s*Value\s*Gap).*?(\d{1,3}\.\d{3})",
        "LIQUIDEZ_SUPERIOR": r"(Liquidez\s*Superior|BSL).*?(\d{1,3}\.\d{3})",
        "LIQUIDEZ_INFERIOR": r"(Liquidez\s*Inferior|SSL).*?(\d{1,3}\.\d{3})",
        "ENTRADA": r"(Entrada|Entry).*?(\d{1,3}\.\d{3})",
        "STOP_LOSS": r"(Stop|Stop\s*Loss).*?(\d{1,3}\.\d{3})",
        "ALVO_1": r"(Alvo\s*1|Target\s*1).*?(\d{1,3}\.\d{3})",
        "ALVO_2": r"(Alvo\s*2|Target\s*2).*?(\d{1,3}\.\d{3})",
        "SUPORTE": r"(Suporte|Support).*?(\d{1,3}\.\d{3})",
        "RESISTENCIA": r"(Resistência|Resistance).*?(\d{1,3}\.\d{3})",
        "PDH": r"(PDH|High\s*of\s*Day).*?(\d{1,3}\.\d{3})",
        "PDL": r"(PDL|Low\s*of\s*Day).*?(\d{1,3}\.\d{3})",
        "PWH": r"(PWH|High\s*of\s*Week).*?(\d{1,3}\.\d{3})",
        "PWL": r"(PWL|Low\s*of\s*Week).*?(\d{1,3}\.\d{3})",
    }
    
    # Busca cada padrão no texto
    for tipo, padrao in padroes.items():
        matches = re.findall(padrao, resposta_ia, re.IGNORECASE)
        for match in matches:
            # match pode ser uma tupla: (texto, preco) ou só preco
            if isinstance(match, tuple):
                preco_str = match[-1]  # Pega o último grupo (preço)
            else:
                preco_str = match
            
            try:
                preco = int(preco_str.replace(".", ""))
                niveis.append({
                    "tipo": tipo,
                    "preco": preco,
                    "descricao": tipo.replace("_", " ").title(),
                    "cor": MAPEAMENTO_CORES.get(tipo, "clSilver")
                })
            except:
                continue
    
    # Remove duplicatas (mesmo preço e tipo)
    vistos = set()
    niveis_unicos = []
    for n in niveis:
        chave = (n["tipo"], n["preco"])
        if chave not in vistos:
            vistos.add(chave)
            niveis_unicos.append(n)
    
    return niveis_unicos

# ============================================================
# FUNÇÃO: GERAR SCRIPT PROFIT PRO
# ============================================================
def gerar_script_profit_pro(niveis: List[Dict[str, Any]]) -> str:
    """
    Gera um arquivo .txt no formato exato do Profit Pro
    baseado nos níveis identificados pela IA.
    """
    linhas = []
    
    # Cabeçalho
    linhas.append("// ==========================================")
    linhas.append("// SCRIPT GERADO PELA IA SPIKE - NÍVEIS SMC")
    linhas.append(f"// DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append("// ==========================================")
    linhas.append("")
    linhas.append("var")
    
    # Gera as variáveis (Linha1, Linha2...)
    for i in range(1, len(niveis) + 1):
        linhas.append(f"  Linha{i} : float;")
    
    linhas.append("  //")
    linhas.append("inicio")
    linhas.append("  // VARIAVEIS  ////////////////////////////////////////////////////////////////////////////////")
    
    # Atribui os valores
    for i, nivel in enumerate(niveis, start=1):
        preco = nivel["preco"]
        linhas.append(f"  Linha{i} := {preco:.0f};")
    
    linhas.append("  // Cada Descrição e referente a linha 'ex.: OB, FVG, Sweep etc'")
    linhas.append("  // PLOTAGEM")
    
    # Gera as HorizontalLineCustom
    for i, nivel in enumerate(niveis, start=1):
        preco = nivel["preco"]
        cor = nivel["cor"]
        descricao = nivel["descricao"]
        linhas.append(f"  HorizontalLineCustom(Linha{i}, {cor}, 1, 0, \"{descricao}\", 10, tpTopRight, Date, 0, MinPriceIncrement);")
    
    linhas.append("fim;")
    
    return "\n".join(linhas)

# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("📥 Gerador de Script para Profit Pro")
st.caption("Extraia os níveis da análise SMC/ICT da IA e gere um arquivo .txt pronto para copiar no Profit Pro")

# ============================================================
# INPUT DA IA
# ============================================================
st.markdown("### 1. Cole a resposta da IA (análise SMC)")
st.info("Cole o texto da análise feita pela IA no chat. O sistema vai extrair automaticamente os níveis de preço e tipos (OB, FVG, Entrada, Stop, Alvo...).")

resposta_ia = st.text_area(
    "📝 Resposta da IA",
    placeholder="Cole aqui o texto gerado pela IA no chat (ex: análise SMC/ICT)...",
    height=250
)

# ============================================================
# BOTÃO DE EXTRAÇÃO
# ============================================================
if st.button("🔍 Extrair Níveis e Gerar Script", type="primary", width="stretch"):
    if not resposta_ia.strip():
        st.error("⚠️ Por favor, cole a resposta da IA primeiro.")
    else:
        with st.spinner("🧠 Extraindo níveis do texto da IA..."):
            niveis = extrair_niveis_do_texto(resposta_ia)
            
            if not niveis:
                st.warning("⚠️ Nenhum nível de preço foi encontrado no texto fornecido. Verifique se a resposta da IA contém preços numéricos (ex: 180500, 179200).")
            else:
                st.success(f"✅ {len(niveis)} níveis extraídos com sucesso!")
                
                # ============================================================
                # EXIBIÇÃO DOS NÍVEIS
                # ============================================================
                st.markdown("### 📊 Níveis Extraídos")
                
                for nivel in niveis:
                    cor_hex = {
                        "clRed": "#ff3d00",
                        "clGreen": "#00c853",
                        "clYellow": "#ffc107",
                        "clBlue": "#58a6ff",
                        "clLime": "#00ff88",
                        "clFuchsia": "#ff00ff",
                        "clAqua": "#00ffff",
                        "clSilver": "#c0c0c0"
                    }.get(nivel["cor"], "#ffffff")
                    
                    st.markdown(f"""
                    <div class="card-nivel" style="border-left-color: {cor_hex};">
                        <b>{nivel['descricao']}</b> — <span style="color:{cor_hex}; font-weight:bold;">{nivel['preco']:,.0f}</span>
                        <span style="color:#8b949e; font-size:0.8rem; margin-left:12px;">Cor: {nivel['cor']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # ============================================================
                # GERAR E BAIXAR O SCRIPT
                # ============================================================
                codigo_profit = gerar_script_profit_pro(niveis)
                
                st.markdown("### 📄 Script Gerado (Pronto para o Profit Pro)")
                st.code(codigo_profit, language="pascal")
                
                st.download_button(
                    label="⬇️ Baixar Script .txt (Profit Pro)",
                    data=codigo_profit,
                    file_name=f"Spike_SMC_Levels_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    width="stretch"
                )

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.caption("Gerador de Script Profit Pro • Versão 1.0 • Integrado ao Analisador Financeiro")