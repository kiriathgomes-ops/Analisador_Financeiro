#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: CalculadoraEstimativaAbertura.py (Versão Otimizada V2)
Objetivo: Processar estimativas e pivôs para o WIN eliminando ruído de leilão.
Regra: 09:00 usa o Last Tick congelado da noite. 10:00 usa o último close de M1/M5.
"""

import json
import os
from datetime import datetime, time
from config import (
    COLETAS_DIR,
    FILE_VALIDADOS as FILE_INPUT,
    FILE_ESTIMATIVA_ABERTURA as FILE_OUTPUT,
    PESOS_ESTIMATIVA_ABERTURA,
)





def extrair_variacao(ativos_dict: dict, ativo_id: str) -> float:
    dados = ativos_dict.get(ativo_id, {}).get("change_percent")
    return float(dados) if isinstance(dados, (int, float)) else 0.0

def calcular_abertura_win(ativos_dict: dict, preco_referencia_base: float) -> dict:
    """Aplica o modelo ponderado com base no preço base definido pela janela temporal."""
    ewz = extrair_variacao(ativos_dict, "EWZ")
    sp500 = extrair_variacao(ativos_dict, "SP500_FUT")
    vale = extrair_variacao(ativos_dict, "VALE_ADR")
    petr = extrair_variacao(ativos_dict, "PETR_ADR")
    
    pesos = PESOS_ESTIMATIVA_ABERTURA
    cesta_adrs = (vale * pesos.get("adr_vale", 0.30)) + (petr * pesos.get("adr_petr", 0.25))
    
    var_pct = (ewz * pesos.get("ewz", 0.30)) + (cesta_adrs * pesos.get("cesta_adrs", 0.35)) + (sp500 * pesos.get("sp500_fut", 0.20))
    
    abertura_estimada = 0.0
    if preco_referencia_base > 0:
        abertura_estimada = preco_referencia_base * (1 + (var_pct / 100))
        
    return {
        "variacao_teorica_pct": round(var_pct, 4),
        "preco_referencia_base": preco_referencia_base,
        "abertura_teorica_pontos": round(abertura_estimada, 0)
    }

def processar_calculos_operacionais():
    if not os.path.exists(FILE_INPUT):
        return

    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        dados_json = json.load(f)

    ativos_dict = {item["ativo_id"]: item for item in dados_json.get("ativos_validados", [])}
    agora_time = datetime.now().time()

    # --- DEFINIÇÃO DINÂMICA DO PREÇO DE REFERÊNCIA (Fim do Bug de Leilão) ---
    if agora_time < time(9, 45, 0):
        # 1. Preparação para a Abertura do Futuro (09:00): Usa o Last Tick congelado do Overnight (coletado até 08:50)
        preco_base = ativos_dict.get("WIN_LAST_TICK", {}).get("close", 0.0)
        contexto_janela = "REFERENCIA_0900_OVERNIGHT"
    else:
        # 2. Preparação para a Abertura do À Vista (10:00): Usa o último close disponível antes das 10:00 (Fim da vela de 09:55-09:59)
        preco_base = ativos_dict.get("WIN_FUT", {}).get("close", 0.0)
        contexto_janela = "REFERENCIA_1000_INTRADAY"

    win_metrics = calcular_abertura_win(ativos_dict, preco_base)
    win_metrics["contexto_janela"] = contexto_janela

    # Pontos de Pivô clássicos calculados estritamente sobre a estrutura do Diário (D1) anterior
    win_fut = ativos_dict.get("WIN_FUT", {})
    high_d1 = win_fut.get("high", 0.0)
    low_d1 = win_fut.get("low", 0.0)
    close_d1 = win_fut.get("previous_close", 0.0) or win_fut.get("close", 0.0)

    pivots = {}
    if high_d1 > 0 and low_d1 > 0 and close_d1 > 0:
        pp = (high_d1 + low_d1 + close_d1) / 3
        pivots = {
            "PP": round(pp, 2),
            "R1": round((2 * pp) - low_d1, 2),
            "R2": round(pp + (high_d1 - low_d1), 2),
            "S1": round((2 * pp) - high_d1, 2),
            "S2": round(pp - (high_d1 - low_d1), 2)
        }

    payload = {
        "metadata_calculo": {
            "timestamp_calculo": datetime.now().isoformat(),
            "janela_ativa": contexto_janela
        },
        "estimativa_abertura": {"WIN_INDICE": win_metrics},
        "pivot_points": {"WIN_FUT": pivots}
    }

    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    processar_calculos_operacionais()
