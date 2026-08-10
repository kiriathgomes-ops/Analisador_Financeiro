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
    # Mapeamentos para tabela Markdown
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
    "DEFAULT": "clSilver"
}

def obter_cor(conceito: str) -> str:
    """Mapeia o nome do conceito para uma cor do Profit Pro."""
    conceito_upper = conceito.upper()
    for chave, cor in MAPEAMENTO_CORES.items():
        if chave in conceito_upper:
            return cor
    return MAPEAMENTO_CORES["DEFAULT"]

# ============================================================
# FUNÇÃO: EXTRAIR NÍVEIS DA TABELA MARKDOWN E TEXTO
# ============================================================
def extrair_niveis_do_texto(resposta_ia: str) -> List[Dict[str, Any]]:
    """
    Extrai os níveis da resposta da IA.
    Suporta tabelas em Markdown geradas pela IA SMC/ICT e fallback com regex.
    """
    niveis = []
    
    # 1. TENTATIVA DE EXTRAÇÃO POR TABELA MARKDOWN
    linhas_tabela = [l.strip() for l in resposta_ia.split("\n") if l.strip().startswith("|")]
    
    if len(linhas_tabela) >= 2:
        for linha in linhas_tabela:
            # Ignora o cabeçalho e divisor
            if "Ordem" in linha or "---" in linha:
                continue
            
            colunas = [c.strip() for c in linha.split("|")[1:-1]]
            if len(colunas) >= 3:
                # Esperado: [Ordem, Preço, Conceito, Timeframe, Observações]
                preco_raw = colunas[1] if len(colunas) > 1 else ""
                conceito_raw = colunas[2] if len(colunas) > 2 else "Nível SMC"
                tf_raw = colunas[3] if len(colunas) > 3 else ""
                obs_raw = colunas[4] if len(colunas) > 4 else ""
                
                # Trata valor numérico (ex: 179.000 ou 179,000 ou 179000 -> 179000)
                preco_limpo = re.sub(r"[^\d]", "", preco_raw)
                if preco_limpo:
                    try:
                        preco = int(preco_limpo)
                        cor = obter_cor(conceito_raw)
                        
                        desc_curta = f"{conceito_raw}".replace('"', "'")
                        if tf_raw:
                            desc_curta += f" ({tf_raw})"

                        niveis.append({
                            "tipo": conceito_raw,
                            "preco": preco,
                            "descricao": desc_curta,
                            "observacao": obs_raw.replace('"', "'"),
                            "cor": cor
                        })
                    except ValueError:
                        continue

    # 2. FALLBACK SE NÃO ENCONTRAR TABELA (USANDO REGEX)
    if not niveis:
        padroes = {
            "OB_VENDA": r"(OB\s*Venda|Order\s*Block\s*Venda|Supply\s*Zone).*?(\d{1,3}[\.,]?\d{3})",
            "OB_COMPRA": r"(OB\s*Compra|Order\s*Block\s*Compra|Demand\s*Zone).*?(\d{1,3}[\.,]?\d{3})",
            "FVG": r"(FVG|Fair\s*Value\s*Gap).*?(\d{1,3}[\.,]?\d{3})",
            "EQH": r"(EQH|Equal\s*Highs).*?(\d{1,3}[\.,]?\d{3})",
            "EQL": r"(EQL|Equal\s*Lows).*?(\d{1,3}[\.,]?\d{3})",
            "PDH": r"(PDH|Previous\s*Day\s*High).*?(\d{1,3}[\.,]?\d{3})",
            "PDL": r"(PDL|Previous\s*Day\s*Low).*?(\d{1,3}[\.,]?\d{3})",
        }
        
        for tipo, padrao in padroes.items():
            matches = re.findall(padrao, resposta_ia, re.IGNORECASE)
            for match in matches:
                preco_str = match[-1] if isinstance(match, tuple) else match
                preco_limpo = re.sub(r"[^\d]", "", preco_str)
                try:
                    preco = int(preco_limpo)
                    niveis.append({
                        "tipo": tipo,
                        "preco": preco,
                        "descricao": tipo.replace("_", " ").title(),
                        "observacao": "",
                        "cor": MAPEAMENTO_CORES.get(tipo, "clSilver")
                    })
                except ValueError:
                    continue

    # Remove duplicatas preservando os melhores dados
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
    linhas.append("// SCRIPT GERADO PELA IA SPIKE - NÍVEIS SMC/ICT")
    linhas.append(f"// DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append(f"// TOTAL DE NÍVEIS: {len(niveis)}")
    linhas.append("// ==========================================")
    linhas.append("")
    linhas.append("var")
    
    # Gera as variáveis (Linha1, Linha2...)
    for i in range(1, len(niveis) + 1):
        linhas.append(f"  Linha{i} : float;")
    
    linhas.append("")
    linhas.append("inicio")
    linhas.append("  // DEFINIÇÃO DOS NÍVEIS DE PREÇO //////////////////////////////////////////////////")
    
    # Atribui os valores
    for i, nivel in enumerate(niveis, start=1):
        preco = nivel["preco"]
        linhas.append(f"  Linha{i} := {preco:.0f}; // {nivel['descricao']}")
    
    linhas.append("")
    linhas.append("  // PLOTAGEM DE LINHAS HORIZONTAIS CUSTOMIZADAS ////////////////////////////////////")
    
    # Gera as HorizontalLineCustom
    for i, nivel in enumerate(niveis, start=1):
        cor = nivel["cor"]
        descricao = nivel["descricao"]
        linhas.append(
            f'  HorizontalLineCustom(Linha{i}, {cor}, 1, 0, "{descricao}", 10, tpTopRight, Date, 0, MinPriceIncrement);'
        )
    
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
st.markdown("### 1. Cole a resposta da IA (Análise SMC em Tabela)")
st.info("Cole o texto da tabela Markdown gerada pela IA no chat. O sistema vai extrair automaticamente os níveis de preço, rótulos e cores para o Profit.")

resposta_ia = st.text_area(
    "📝 Resposta da IA",
    placeholder="Cole aqui a tabela gerada pela IA no chat...",
    height=280
)

# ============================================================
# BOTÃO DE EXTRAÇÃO
# ============================================================
if st.button("🔍 Extrair Níveis e Gerar Script", type="primary", width="stretch"):
    if not resposta_ia.strip():
        st.error("⚠️ Por favor, cole a resposta da IA primeiro.")
    else:
        with st.spinner("🧠 Extraindo níveis da tabela SMC/ICT..."):
            niveis = extrair_niveis_do_texto(resposta_ia)
            
            if not niveis:
                st.warning("⚠️ Nenhum nível de preço foi identificado. Verifique se colou a tabela Markdown corretamente.")
            else:
                st.success(f"✅ {len(niveis)} níveis extraídos com sucesso!")
                
                # ============================================================
                # EXIBIÇÃO DOS NÍVEIS
                # ============================================================
                st.markdown("### 📊 Níveis Identificados")
                
                mudar_cor_hex = {
                    "clRed": "#ff3d00",
                    "clGreen": "#00c853",
                    "clYellow": "#ffc107",
                    "clBlue": "#58a6ff",
                    "clLime": "#00ff88",
                    "clFuchsia": "#ff00ff",
                    "clAqua": "#00ffff",
                    "clWhite": "#ffffff",
                    "clSilver": "#c0c0c0"
                }
                
                for nivel in niveis:
                    cor_hex = mudar_cor_hex.get(nivel["cor"], "#ffffff")
                    obs_str = f" — <span style='color:#8b949e;'>{nivel['observacao']}</span>" if nivel['observacao'] else ""
                    
                    st.markdown(f"""
                    <div class="card-nivel" style="border-left-color: {cor_hex};">
                        <b>{nivel['descricao']}</b> — <span style="color:{cor_hex}; font-weight:bold;">{nivel['preco']:,}</span>
                        {obs_str}
                        <span style="color:#8b949e; font-size:0.8rem; float:right;">Cor Profit: {nivel['cor']}</span>
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
st.caption("Gerador de Script Profit Pro • Versão 2.0 • Integrado ao Analisador Financeiro")