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
FILE_CACHE_VAR_TEORICA = Path(COLETAS_DIR) / "EstimativaAbertura_Cache.json"


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


def _carregar_cache_var() -> dict:
    """Le o cache da variacao teorica, se existir."""
    if not os.path.exists(FILE_CACHE_VAR_TEORICA):
        return {}
    try:
        with open(FILE_CACHE_VAR_TEORICA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_cache_var(payload: dict) -> None:
    """Persiste o cache da variacao teorica."""
    try:
        os.makedirs(os.path.dirname(FILE_CACHE_VAR_TEORICA), exist_ok=True)
        with open(FILE_CACHE_VAR_TEORICA, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[AVISO] Falha ao salvar cache var teorica: {e}")


def _resolver_var_teorica(data_ref: str, ajuste: float, var_teorica_atual: float):
    """
    Resolve a var_teorica_pct a ser usada neste ciclo.

    Retorna (var_final, veio_do_cache, timestamp_cache).
      - Se cache existe e bate (data + ajuste): usa cache
      - Se nao: salva o valor atual no cache e retorna ele

    `timestamp_cache` e None quando recalculado agora.
    """
    cache = _carregar_cache_var()
    ajuste_arredondado = round(float(ajuste or 0.0), 0)

    cache_data = cache.get("data_ref")
    cache_ajuste = cache.get("ajuste")
    if cache_data is not None:
        try:
            cache_ajuste = round(float(cache_ajuste), 0)
        except (TypeError, ValueError):
            cache_ajuste = None

    if cache_data == data_ref and cache_ajuste == ajuste_arredondado:
        var = cache.get("variacao_teorica_pct")
        ts = cache.get("timestamp_geracao")
        if var is not None:
            return float(var), True, ts

    # Cache invalido ou inexistente -> salva o atual
    novo = {
        "data_ref": data_ref,
        "ajuste": ajuste_arredondado,
        "variacao_teorica_pct": float(var_teorica_atual) if var_teorica_atual is not None else 0.0,
        "timestamp_geracao": datetime.now().isoformat(),
    }
    _salvar_cache_var(novo)
    return float(var_teorica_atual) if var_teorica_atual is not None else 0.0, False, None


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

        # --- PREÇO BASE DE REFERÊNCIA (sempre o ajuste oficial) ---
    # O ajuste oficial da B3 é estável durante o dia e é o padrão institucional
    # para cálculo de gap de abertura. NÃO usar WIN_FUT.close (preço atual),
    # que muda a cada tick e faz a "abertura teórica" variar.
    preco_base = ativos_dict.get("WIN_AJUSTE", {}).get("close", 0.0)

    if preco_base <= 0:
        # Fallback: se o ajuste não estiver disponível, usa o fechamento congelado
        preco_base = ativos_dict.get("WIN_LAST_TICK", {}).get("close", 0.0)
        contexto_janela = "FALLBACK_LAST_TICK"
    else:
        contexto_janela = "REFERENCIA_AJUSTE_OFICIAL"

    print(f"🕒 Horário da Consulta    : {datetime.now().strftime('%H:%M:%S')}")
    print(f"📌 Janela Temporal        : {contexto_janela}")
    print(f"💰 Preço Base Referência  : {preco_base}")

    win_metrics = calcular_abertura_win(ativos_dict, preco_base)
    win_metrics["contexto_janela"] = contexto_janela

    # ---- CONGELA variacao_teorica_pct por dia (data + ajuste) ----
    var_teorica_calculada = win_metrics.get("variacao_teorica_pct")
    var_teorica_final, do_cache, ts_cache = _resolver_var_teorica(
        data_ref=datetime.now().date().isoformat(),
        ajuste=preco_base,
        var_teorica_atual=var_teorica_calculada,
    )

    # Recalcula a abertura teorica com a var congelada
    abertura_congelada = round(preco_base * (1 + var_teorica_final / 100), 0) if preco_base > 0 else 0.0

    win_metrics["variacao_teorica_pct"] = round(var_teorica_final, 4)
    win_metrics["abertura_teorica_pontos"] = abertura_congelada
    win_metrics["var_teorica_congelada"] = True
    win_metrics["var_teorica_do_cache"] = bool(do_cache)
    win_metrics["var_teorica_timestamp_cache"] = ts_cache
    win_metrics["var_teorica_calculada_agora"] = (
        round(var_teorica_calculada, 4) if var_teorica_calculada is not None else None
    )

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
            "janela_ativa": contexto_janela,
            "var_teorica_congelada": win_metrics.get("var_teorica_congelada", False),
            "var_teorica_do_cache": win_metrics.get("var_teorica_do_cache", False),
            "var_teorica_timestamp_cache": win_metrics.get("var_teorica_timestamp_cache"),
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
    if win_metrics.get("var_teorica_do_cache"):
        ts_cache = win_metrics.get("var_teorica_timestamp_cache") or "?"
        ts_curto = ts_cache[11:19] if len(ts_cache) >= 19 else ts_cache
        origem_var = f"🔒 CONGELADA (do cache, gerada {ts_curto})"
    else:
        origem_var = "🆕 RECALCULADA AGORA (primeira vez hoje ou ajuste mudou)"

    print(f" Variação Teórica (Delta) : {win_metrics['variacao_teorica_pct']}%")
    print(f"   └─ Origem              : {origem_var}")
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