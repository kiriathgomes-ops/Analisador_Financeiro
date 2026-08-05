# ============================================================
# ARQUIVO: Relatorio.py
# DATA: 29/07/2026
# AUTOR: Arquiteto de Sistemas
# MOTIVO: Fase 5 - Geração do Relatório Executivo e Diagnóstico
#         Sintético Macro e Arbitragem (Terminal + Arquivo).
# ============================================================

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLETAS_DIR = os.path.join(BASE_DIR, "Coletas")
FILE_METRICAS = os.path.join(COLETAS_DIR, "Metricas_Calculadas.json")
FILE_RELATORIO = os.path.join(COLETAS_DIR, "Relatorio_Executivo.md")

def carregar_metricas():
    if not os.path.exists(FILE_METRICAS):
        print(f"[ERRO] Arquivo de métricas não encontrado: {FILE_METRICAS}")
        return None
    with open(FILE_METRICAS, 'r', encoding='utf-8') as f:
        return json.load(f)

def gerar_diagnostico(metricas):
    cambio = metricas.get("cambio_e_arbitragem", {})
    juros = metricas.get("curva_juros_b3", {})
    macro = metricas.get("indicadores_macro", {})
    perf = metricas.get("performance_relativa", {})
    
    # Lógica de Diagnóstico
    sp_pct = perf.get("sp500_fut_change_pct", 0) or 0
    ewz_pct = perf.get("ewz_change_pct", 0) or 0
    descolamento = ewz_pct - sp_pct
    
    spread_pts = cambio.get("spread_wdo_ptax_pontos", 0) or 0
    vix = macro.get("vix", 0) or 0
    inclinacao = juros.get("inclinacao_29_27_bps", 0) or 0
    
    # Status Cambial
    if spread_pts < -10:
        status_cambio = "DESCONTO ACENTUADO (Dólar Futuro abaixo da PTAX - Pressão Vendedora no WDO)"
    elif spread_pts > 10:
        status_cambio = "PRÊMIO ELEVADO (Dólar Futuro acima da PTAX - Pressão Compradora no WDO)"
    else:
        status_cambio = "ALINHADO (Dólar Futuro em equilíbrio com a PTAX)"

    # Status Risco Global
    if vix > 20:
        status_vix = "AVERSÃO AO RISCO / VOLATILIDADE ELEVADA"
    else:
        status_vix = "AMBIENTE NEUTRO / APETITE A RISCO MODERADO"

    # Status Brasil vs Exterior
    if descolamento < -1.5:
        status_brasil = "DESCOLAMENTO NEGATIVO CRÍTICO (Brasil performando bem pior que EUA)"
    elif descolamento > 1.5:
        status_brasil = "OUTPERFORMANCE BRASIL (EWZ superando bolsas americanas)"
    else:
        status_brasil = "CORRELAÇÃO ALINHADA COM MERCADOS INTERNACIONAIS"

    txt = []
    txt.append("# 📈 RELATÓRIO EXECUTIVO DE AUDITORIA E ANÁLISE MACRO")
    txt.append(f"**Data/Hora da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    txt.append("---")
    
    # Ajuste na função gerar_diagnostico() em Relatorio.py:
    txt.append("## 1. PAINEL SINTÉTICO DE AVALIAÇÃO DE MERCADO\n")
    txt.append(f"* **Ambiente Global de Risco (VIX):** `{vix}` → **{status_vix}**")
    txt.append(f"* **Arbitragem Dólar Futuro / PTAX:** `{spread_pts} pts` → **{status_cambio}**")
    txt.append(f"* **Sensibilidade EWZ vs S&P 500:** Spread de `{descolamento:.2f}%` → **{status_brasil}**")
    txt.append(f"* **Estrutura de Juros B3 (DI 29-27):** `{inclinacao} bps` de inclinação entre vértices médio e longo.\n")
    
    txt.append("---")
    txt.append("## 2. DETALHAMENTO DAS MÉTRICAS\n")
    txt.append("### A. Câmbio e Arbitragem")
    txt.append(f"- **USD PTAX (Oficial):** R$ {cambio.get('usd_ptax')}")
    txt.append(f"- **WDO Futuro:** R$ {cambio.get('wdo_fut')}")
    txt.append(f"- **Spread (Pontos):** {cambio.get('spread_wdo_ptax_pontos')} pts")
    txt.append(f"- **Spread (%):** {cambio.get('spread_wdo_ptax_percentual')}%\n")
    
    txt.append("### B. Curva de Juros Futuros (DI1 B3)")
    txt.append(f"- **DI1F2027 (Curto/Médio):** {juros.get('di1_2027_taxa')}%")
    txt.append(f"- **DI1F2029 (Longo):** {juros.get('di1_2029_taxa')}%")
    txt.append(f"- **Inclinação (Spread):** {juros.get('inclinacao_29_27_bps')} bps\n")

    txt.append("### C. Commodities e Drivers Externos")
    txt.append(f"- **Petróleo (Crude Oil WTI):** US$ {macro.get('crude_oil')}")
    txt.append(f"- **Minério de Ferro (SGX):** US$ {macro.get('iron_ore')}")
    txt.append(f"- **DXY (Índice Dólar):** {macro.get('dxy')}\n")

    txt.append("### D. Performance Relativa de ADRs Brasileiras")
    txt.append(f"- **EWZ (ETF Brasil):** {perf.get('ewz_change_pct')}%")
    txt.append(f"- **S&P 500 Futuro:** {perf.get('sp500_fut_change_pct')}%")
    txt.append(f"- **Nasdaq Futuro:** {perf.get('nasdaq_fut_change_pct')}%\n")
    
    txt.append("#### Principais ADRs:")
    adrs = perf.get("adrs_brasileiras", {})
    for k, v in adrs.items():
        txt.append(f"- **{k}:** US$ {v.get('close')} ({v.get('change_percent')}%)")

    txt.append("\n---")
    txt.append("## 3. ALERTAS E RECOMENDAÇÕES QUANTITATIVAS")
    
    if descolamento < -1.5:
        txt.append("⚠️ **Alerta Risco Brasil:** EWZ apresentando forte descolamento negativo frente a Wall Street. Monitorar risco fiscal e saída de fluxo estrangeiro.")
    if spread_pts < -15:
        txt.append("💡 **Oportunidade/Aviso Cambial:** Desconto expressivo no WDO em relação à PTAX. Atentar para possível fechamento de spread ou rolagem de posições.")
    if vix > 20:
        txt.append("🛡️ **Aviso de Volatilidade:** VIX acima de 20 exige redução de lote operacional e ajuste de stop em estratégias de momentum.")

    return "\n".join(txt)

def executar_relatorio():
    metricas = carregar_metricas()
    if not metricas:
        return
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Gerando Relatório Executivo...")
    conteudo_md = gerar_diagnostico(metricas)
    
    # Salva arquivo Markdown
    with open(FILE_RELATORIO, 'w', encoding='utf-8') as f:
        f.write(conteudo_md)
        
    print("\n" + "="*70)
    print(" RELATÓRIO EXECUTIVO GERADO ")
    print("="*70)
    print(conteudo_md)
    print("="*70)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Arquivo salvo: {os.path.basename(FILE_RELATORIO)}\n")

if __name__ == "__main__":
    print("============================================================")
    print(" FASE 5: ENGINE DE RELATÓRIO E DIAGNÓSTICO EXECUTIVO")
    print("============================================================")
    executar_relatorio()