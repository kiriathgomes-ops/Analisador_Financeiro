# -*- coding: utf-8 -*-
"""
Módulo: Gerar_Relatorio.py
Versão: 3.0 - Produção Unificada V2
Objetivo: Fase 5 - Geração do Relatório Executivo e Diagnóstico Sintético Macro.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Ingestão de caminhos centralizados do config.py da V2
from config import COLETAS_DIR, FILE_METRICAS, FILE_DECISAO_V2

# Definição do arquivo de saída baseado na governança do config
FILE_RELATORIO = COLETAS_DIR / "Relatorio_Executivo.md"

def carregar_json_defensivo(caminho_path) -> dict:
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def gerar_diagnostico(metricas: dict, decisao_v2: dict) -> str:
    cambio = metricas.get("cambio_e_arbitragem", {})
    juros = metricas.get("curva_juros_b3", {})
    macro = metricas.get("indicadores_macro", {})
    perf = metricas.get("performance_relativa", {})
    
    # Extração de dados inteligentes processados na V2
    sp_pct = perf.get("sp500_fut_change_pct", 0) or 0
    ewz_pct = perf.get("ewz_change_pct", 0) or 0
    descolamento = ewz_pct - sp_pct
    
    spread_pts = cambio.get("spread_wdo_ptax_pontos", 0) or 0
    vix = macro.get("vix", 0) or 0
    inclinacao = juros.get("inclinacao_29_27_bps", 0) or 0
    
    vies_core = decisao_v2.get("decisao", {}).get("vies_final", "NEUTRO")
    confianca = decisao_v2.get("decisao", {}).get("confianca", 0)

    # Status de Arbitragem Cambial
    if spread_pts < -10:
        status_cambio = "DESCONTO ACENTUADO (WDO abaixo da PTAX - Pressão Vendedora)"
    elif spread_pts > 10:
        status_cambio = "PRÊMIO ELEVADO (WDO acima da PTAX - Pressão Compradora)"
    else:
        status_cambio = "ALINHADO (Dólar Futuro em equilíbrio com a PTAX)"

    # Status Risco Global
    status_vix = "AVERSÃO AO RISCO / VOLATILIDADE ELEVADA" if vix > 20 else "AMBIENTE NEUTRO / APETITE A RISCO MODERADO"

    # Status Brasil vs Exterior
    if descolamento < -1.5:
        status_brasil = "DESCOLAMENTO NEGATIVO CRÍTICO (Brasil performando pior que EUA)"
    elif descolamento > 1.5:
        status_brasil = "OUTPERFORMANCE BRASIL (EWZ superando bolsas americanas)"
    else:
        status_brasil = "CORRELAÇÃO ALINHADA COM MERCADOS INTERNACIONAIS"

    txt = [
        "# 📈 RELATÓRIO EXECUTIVO DE AUDITORIA E ANÁLISE MACRO V2",
        f"**Data/Hora da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n",
        "---",
        "## 🎯 1. ORQUESTRAÇÃO CORE E TOMADA DE DECISÃO",
        f"* **Direção Institucional Ativa:** `{vies_core}`",
        f"* **Força de Confluência do Sinal:** `{confianca}%` de relevância operacional.\n",
        "---",
        "## 📊 2. PAINEL SINTÉTICO DE AVALIAÇÃO DE MERCADO",
        f"* **Ambiente Global de Risco (VIX):** `{vix}` → **{status_vix}**",
        f"* **Arbitragem Dólar Futuro / PTAX:** `{spread_pts} pts` → **{status_cambio}**",
        f"* **Sensibilidade EWZ vs S&P 500:** Spread de `{descolamento:.2f}%` → **{status_brasil}**",
        f"* **Estrutura de Juros B3 (DI 29-27):** `{inclinacao} bps` de inclinação entre vértices médio e longo.\n",
        "---",
        "## 🔍 3. DETALHAMENTO DAS MÉTRICAS EM PROFUNDIDADE\n",
        "### A. Câmbio e Arbitragem",
        f"- **USD PTAX (Oficial):** R$ {cambio.get('usd_ptax', '—')}",
        f"- **WDO Futuro (Last MT5):** R$ {cambio.get('wdo_fut', '—')}",
        f"- **Spread (Pontos):** {cambio.get('spread_wdo_ptax_pontos', '—')} pts",
        f"- **Spread (%):** {cambio.get('spread_wdo_ptax_percentual', '—')}%\n",
        "### B. Curva de Juros Futuros (DI1 B3)",
        f"- **DI1F2027 (Curto/Médio):** {juros.get('di1_2027_taxa', '—')}%",
        f"- **DI1F2029 (Longo):** {juros.get('di1_2029_taxa', '—')}%",
        f"- **Inclinação (Spread):** {juros.get('inclinacao_29_27_bps', '—')} bps\n",
        "### C. Commodities e Drivers Externos",
        f"- **Petróleo (Crude Oil WTI):** US$ {macro.get('crude_oil', '—')}",
        f"- **Minério de Ferro (SGX 2M):** US$ {macro.get('iron_ore_fef2', {}).get('close', '—')}",
        f"- **DXY (Índice Dólar Global):** {macro.get('dxy', '—')}\n",
        "### D. Performance Relativa de ADRs Brasileiras",
        f"- **EWZ (ETF Brasil em NY):** {perf.get('ewz_change_pct', '—')}%",
        f"- **S&P 500 Futuro:** {perf.get('sp500_fut_change_pct', '—')}%",
        f"- **Nasdaq Futuro:** {perf.get('nasdaq_fut_change_pct', '—')}%\n",
        "#### Cesta de ADRs Individuais:"
    ]
    
    adrs = perf.get("adrs_brasileiras", {})
    if isinstance(adrs, dict):
        for k, v in adrs.items():
            txt.append(f"- **{k.replace('_ADR', '')}:** US$ {v.get('close', 0):,.2f} ({v.get('change_percent', 0):+.2f}%)")

    txt.extend([
        "\n---",
        "## 🛡️ 4. ALERTAS E RECOMENDAÇÕES QUANTITATIVAS DE RISCO"
    ])
    
    # Injeção de travas baseadas nas métricas processadas
    if descolamento < -1.5:
        txt.append("- ⚠️ **Alerta Risco Brasil:** EWZ apresentando forte descolamento negativo frente a Wall Street. Monitorar risco fiscal e saída de fluxo estrangeiro.")
    if spread_pts < -15:
        txt.append("- 💡 **Oportunidade/Aviso Cambial:** Desconto expressivo no WDO em relação à PTAX. Atentar para possível fechamento de spread ou exaustão de venda.")
    if vix > 20:
        txt.append("- 🛡️ **Aviso de Volatilidade:** VIX acima de 20 exige redução de lote operacional e ajuste estrito de stop loss por proteção patrimonial.")
    if len(txt) == 23: # Caso não caia em nenhuma trava acima
        txt.append("- 🟢 **Normalidade Operacional:** Parâmetros macro dentro das bandas estatísticas de controle.")

    return "\n".join(txt)

def executar_relatorio_macro():
    # Carrega os dados gerados pelo pipeline V2 de forma independente
    metricas = carregar_json_defensivo(FILE_METRICAS)
    decisao_v2 = carregar_json_defensivo(FILE_DECISAO_V2)
    
    if not metricas or not decisao_v2:
        print("❌ [ERRO] Falha ao carregar matrizes de dados V2 para geração do relatório.")
        return
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Compilando Relatório Executivo Macro...")
    conteudo_md = gerar_diagnostico(metricas, decisao_v2)
    
    # Persistência estável e segura do arquivo Markdown no disco
    try:
        with open(FILE_RELATORIO, 'w', encoding='utf-8') as f:
            f.write(conteudo_md)
            
        print("\n" + "="*70)
        print(" ✅ RELATÓRIO EXECUTIVO MACRO GERADO COM SUCESSO ")
        print("="*70)
        print(conteudo_md)
        print("="*70)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Arquivo salvo em: {FILE_RELATORIO.name}\n")
    except Exception as e:
        print(f"❌ Erro ao gravar o arquivo {FILE_RELATORIO.name}: {e}")

if __name__ == "__main__":
    print("============================================================")
    print(" FASE 5: ENGINE DE RELATÓRIO E DIAGNÓSTICO EXECUTIVO V2")
    print("============================================================")
    executar_relatorio_macro()
