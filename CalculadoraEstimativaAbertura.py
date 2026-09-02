#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo: CalculadoraEstimativaAbertura.py (Versão Otimizada V2 + Cost of Carry + SMC)
Objetivo: Processar estimativas e pivôs para o WIN eliminando ruído de leilão.
Regra: 09:00 usa o Last Tick congelado da noite. 10:00 usa o último close de M1/M5.
Preserva: Cálculos originais de Pivô Clássico (Floor Pockets) para consumo em páginas externas.
"""

import json
import os
import sys
from datetime import datetime, time
from pathlib import Path

from config import (
    COLETAS_DIR,
    FILE_VALIDADOS as FILE_INPUT,
    FILE_ESTIMATIVA_ABERTURA as FILE_OUTPUT,
    PESOS_ESTIMATIVA_ABERTURA,
)

# Força codificação UTF-8 no terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

FILE_SMC_DADOS = Path(COLETAS_DIR) / "AnaliseGraficaSMC_Regras.json"


def extrair_variacao(ativos_dict: dict, ativo_id: str) -> float:
    dados = ativos_dict.get(ativo_id, {}).get("change_percent")
    return float(dados) if isinstance(dados, (int, float)) else 0.0


def carregar_niveis_institucionais_smc() -> dict:
    """Lê a POC e a VWAP do dia anterior geradas pelo motor SMC."""
    if not os.path.exists(FILE_SMC_DADOS):
        return {"poc_ontem": 0.0, "vwap_ontem": 0.0}
    try:
        with open(FILE_SMC_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("niveis_institucionais", {})
    except Exception:
        return {"poc_ontem": 0.0, "vwap_ontem": 0.0}


def calcular_abertura_win(ativos_dict: dict, preco_referencia_base: float) -> dict:
    """Calcula a estimativa de abertura combinando o Delta Overnight com o Cost of Carry."""
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

    # --- CUSTO DE CARREGAMENTO (COST OF CARRY INSTITUCIONAL) ---
    taxa_di1 = ativos_dict.get("DI1_2027", {}).get("close", 13.5) / 100.0
    dias_uteis_ano = 252.0
    fator_carregamento_diario = (1 + taxa_di1) ** (1.0 / dias_uteis_ano) - 1
    preco_cost_of_carry = preco_referencia_base * (1 + fator_carregamento_diario) if preco_referencia_base > 0 else 0.0

    return {
        "variacao_teorica_pct": round(var_pct, 4),
        "preco_referencia_base": preco_referencia_base,
        "abertura_teorica_pontos": round(abertura_estimada, 0),
        "cost_of_carry": {
            "taxa_di_anual_pct": round(taxa_di1 * 100, 2),
            "fator_diario_pct": round(fator_carregamento_diario * 100, 6),
            "preco_teorico_carregado": round(preco_cost_of_carry, 0)
        }
    }


def processar_calculos_operacionais():
    print("=" * 60)
    print(" 🧮 CALCULADORA DE ESTIMATIVA DE ABERTURA & COST OF CARRY")
    print("=" * 60)

    if not os.path.exists(FILE_INPUT):
        print(f"❌ Arquivo de entrada não encontrado: {FILE_INPUT}")
        return

    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        dados_json = json.load(f)

    ativos_dict = {item["ativo_id"]: item for item in dados_json.get("ativos_validados", [])}
    agora_time = datetime.now().time()

    # --- DEFINIÇÃO DINÂMICA DO PREÇO DE REFERÊNCIA ---
    if agora_time < time(9, 45, 0):
        preco_base = ativos_dict.get("WIN_LAST_TICK", {}).get("close", 0.0)
        contexto_janela = "REFERENCIA_0900_OVERNIGHT"
    else:
        preco_base = ativos_dict.get("WIN_FUT", {}).get("close", 0.0)
        contexto_janela = "REFERENCIA_1000_INTRADAY"

    print(f"🕒 Horário da Consulta    : {datetime.now().strftime('%H:%M:%S')}")
    print(f"📌 Janela Temporal        : {contexto_janela}")
    print(f"💰 Preço Base Referência  : {preco_base}")

    win_metrics = calcular_abertura_win(ativos_dict, preco_base)
    win_metrics["contexto_janela"] = contexto_janela

    # --- PONTOS DE PIVÔ CLÁSSICOS (MANTIDOS INTEGRALMENTE PARA SUAS PAGES) ---
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

    # --- PONTOS DE PIVÔ INSTITUCIONAIS (SMC / VOLUME PROFILE) ---
    niveis_smc = carregar_niveis_institucionais_smc()

    payload = {
        "metadata_calculo": {
            "timestamp_calculo": datetime.now().isoformat(),
            "janela_ativa": contexto_janela
        },
        "estimativa_abertura": {"WIN_INDICE": win_metrics},
        "pivot_points": {"WIN_FUT": pivots},
        "pivots_institucionais": {
            "poc_ontem": niveis_smc.get("poc_ontem", 0.0),
            "vwap_ontem": niveis_smc.get("vwap_ontem", 0.0)
        }
    }

    with open(FILE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # --- SAÍDA FORMATADA NO TERMINAL ---
    print("\n" + "-" * 60)
    print(" 🎯 ESTIMATIVAS DE ABERTURA & CARREGAMENTO")
    print("-" * 60)
    print(f" Variação Teórica (Delta) : {win_metrics['variacao_teorica_pct']}%")
    print(f" Abertura Teórica WIN     : {win_metrics['abertura_teorica_pontos']} pts")
    
    coc = win_metrics["cost_of_carry"]
    print(f" Taxa DI Referência       : {coc['taxa_di_anual_pct']}% a.a.")
    print(f" Preço Carregado (DI/252) : {coc['preco_teorico_carregado']} pts")

    print("\n" + "-" * 60)
    print(" 📍 PONTOS DE PIVÔ CLÁSSICOS (PÁGINAS EXTERNAS)")
    print("-" * 60)
    print(f" R2: {pivots.get('R2')} | R1: {pivots.get('R1')} | PP: {pivots.get('PP')} | S1: {pivots.get('S1')} | S2: {pivots.get('S2')}")

    print("\n" + "-" * 60)
    print(" 🏦 PIVÔS INSTITUCIONAIS (SMC / VOLUME PROFILE)")
    print("-" * 60)
    print(f" POC (Ontem)  : {niveis_smc.get('poc_ontem')} pts")
    print(f" VWAP (Ontem) : {niveis_smc.get('vwap_ontem')} pts")

    print("\n" + "=" * 60)
    print(f" ✅ Resultados gravados com sucesso em: {FILE_OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    processar_calculos_operacionais()