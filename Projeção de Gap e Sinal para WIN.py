# -*- coding: utf-8 -*-
"""
Módulo: Projeção de Gap e Sinal para WIN.py
Versão: 3.0 - Otimizado para Produção V2 (Local Pura)
Objetivo: Calcular a variação teórica ponderada e a projeção do preço de abertura 
          do WIN baseando-se estritamente no arquivo unificado atualizado pelo Coletor V2.
"""

import json
import os
from pathlib import Path

# Ingestão de caminhos centralizados e pesos baseados nas constantes do config.py
from config import COLETAS_DIR, FILE_UNIFICADO, PESOS_ESTIMATIVA_ABERTURA

def carregar_json_defensivo(caminho_path) -> dict:
    if not caminho_path.exists():
        return {}
    try:
        with open(caminho_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def calcular_gap_win_v2() -> dict | None:
    print("=" * 60)
    print(" 📊 PROJEÇÃO DE ABERTURA DO WIN FUTURO (MÓDULO LOCAL V2)")
    print("=" * 60)

    # 1. Carrega o arquivo unificado gerado em background pelo Coletor.py
    if not FILE_UNIFICADO.exists():
        print(f"❌ [ERRO] Arquivo unificado não localizado: {FILE_UNIFICADO.name}")
        print("   Execute o Coletor.py primeiro para atualizar as cotações.")
        return None

    dados_unificados = carregar_json_defensivo(FILE_UNIFICADO)
    ativos = dados_unificados.get("ativos", {})

    # 2. Resgata os Preços de Referência locais do WIN (Overnight / Ajuste)
    # Tenta obter o último tick coletado no MetaTrader 5 (Prioridade Máxima)
    win_ref = ativos.get("WIN_LAST_TICK", {}).get("preco") or \
              ativos.get("WIN_AJUSTE", {}).get("preco") or \
              ativos.get("WIN_FUT", {}).get("preco", 0.0)

    if not win_ref or win_ref <= 0:
        print("❌ [ERRO] Não foi possível capturar um preço de referência válido para o WIN.")
        return None

    print(f"✅ Preço de Referência Base localizado: {win_ref:,.0f} pts")

    # 3. EXTRAÇÃO DAS VARIAÇÕES DAS API LOCAIS (Sem requisições HTTP redundantes)
    # Captura as variações percentuais que o seu Coletor V2 salvou no JSON unificado
    var_ewz = ativos.get("EWZ", {}).get("variacao_pct", 0.0)
    var_sp500 = ativos.get("SP500_FUT", {}).get("variacao_pct", 0.0)
    var_vale = ativos.get("VALE_ADR", {}).get("variacao_pct", 0.0)
    var_petr = ativos.get("PETR_ADR", {}).get("variacao_pct", 0.0)
    var_iron = ativos.get("IRON_ORE_2M", {}).get("variacao_pct", 0.0)
    var_oil = ativos.get("CRUDE_OIL", {}).get("variacao_pct", 0.0)

    # 4. APLICAÇÃO DOS PESOS OFICIAIS DO SEU CONFIG.PY
    # Consome os pesos centralizados definidos na sua migração A2
    pesos = PESOS_ESTIMATIVA_ABERTURA
    
    # Monta a cesta ponderada setorial do Ibovespa no exterior
    cesta_adrs = (var_vale * pesos.get("adr_vale", 0.30)) + (var_petr * pesos.get("adr_petr", 0.25))
    cesta_commodities = (var_iron * pesos.get("iron_ore", 0.50)) + (var_oil * pesos.get("crude_oil", 0.50))
    
    # Cálculo final da variação teórica ponderada macro
    var_teorica_pct = (var_ewz * pesos.get("ewz", 0.30)) + \
                      (cesta_adrs * pesos.get("cesta_adrs", 0.35)) + \
                      (var_sp500 * pesos.get("sp500_fut", 0.20)) + \
                      (cesta_commodities * pesos.get("cesta_commodities", 0.15))

    var_teorica_pct = round(var_teorica_pct, 4)

    # 5. CÁLCULO DA PROJEÇÃO EM PONTOS E GAPS
    preco_abertura_projetado = win_ref * (1 + (var_teorica_pct / 100))
    gap_pontos_estimado = round(preco_abertura_projetado - win_ref)

    # Classificação quantitativa do viés de abertura
    if var_teorica_pct >= 0.30:
        vies = "COMPRADO (GAP DE ALTA)"
    elif var_teorica_pct <= -0.30:
        vies = "VENDIDO (GAP DE BAIXA)"
    else:
        vies = "NEUTRO (GAP PEQUENO / EQUILÍBRIO)"

    resultado = {
        "Preco_Referencia_WIN": float(win_ref),
        "Var_Teorica_Projetada_%": var_teorica_pct,
        "Gap_Estimado_Pontos": int(gap_pontos_estimado),
        "Preco_Abertura_Projetado": int(round(preco_abertura_projetado)),
        "Vies_Abertura": vies,
        "Detalhes_Cesta": {
            "EWZ": var_ewz,
            "SP500_FUT": var_sp500,
            "VALE_ADR": var_vale,
            "PETR_ADR": var_petr,
            "Minério_SGX": var_iron,
            "Petróleo_WTI": var_oil
        }
    }

    # Painel Informativo de Console (Logs rápidos)
    print(f"  └─ Variação Teórica Ponderada : {var_teorica_pct:+.2f}%")
    print(f"  └─ Gap Estimado (Pontos)      : {gap_pontos_estimado:+.0f} pts")
    print(f"  └─ Preço Projetado Abertura   : {resultado['Preco_Abertura_Projetado']:,} pts")
    print(f"  └─ Viés Preliminar de Tela    : {vies}")
    print("=" * 60 + "\n")

    return resultado

if __name__ == "__main__":
    calcular_gap_win_v2()
