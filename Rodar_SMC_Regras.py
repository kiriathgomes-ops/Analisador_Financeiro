#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rodar_SMC_Regras.py -- v3 (multi-timeframe)
Roda a analise SMC em 3 timeframes (M1, M5, M15) numa unica conexao MT5.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

try:
    from Motor_SMC_Regras import (
        analisar_smc, salvar_resultado, CONFIG,
        BRT, _candidatos_simbolo,
    )
except ImportError as e:
    print(f"[ERRO] Import Motor_SMC_Regras: {e}")
    sys.exit(1)

from cache_candles import obter_candles_multi_tf

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ATIVO = "WIN$"

# Memória expandida para garantir que o MT5 baixe muitos dias de histórico
TIMEFRAMES: Dict[str, Dict[str, Any]] = {
    "15m": {"min": 15, "qtd": 1000, "arquivo": "AnaliseGraficaSMC_Regras_M15.json"},
    "5m":  {"min": 5,  "qtd": 2000, "arquivo": "AnaliseGraficaSMC_Regras.json"},
    "1m":  {"min": 1,  "qtd": 1000, "arquivo": "AnaliseGraficaSMC_Regras_M1.json"},
}

ARQUIVO_MTF = BASE_DIR / "Coletas" / "AnaliseGraficaSMC_MTF.json"

def _direcao(bias: str) -> str:
    if bias in ("ALTA", "BAIXA"): return bias
    return "LATERAL"

def calcular_confluencia_mtf(r15: Dict[str, Any], r5: Dict[str, Any], r1: Dict[str, Any]) -> Dict[str, Any]:
    tfs_presentes = []
    if r15 and r15.get("bias_direcional"): tfs_presentes.append("15m")
    if r5 and r5.get("bias_direcional"): tfs_presentes.append("5m")
    if r1 and r1.get("bias_direcional"): tfs_presentes.append("1m")
    n_tfs = len(tfs_presentes)
    parcial = n_tfs < 3

    b15 = _direcao(r15.get("bias_direcional", "LATERAL")) if r15 else "LATERAL"
    b5 = _direcao(r5.get("bias_direcional", "LATERAL")) if r5 else "LATERAL"
    b1 = _direcao(r1.get("bias_direcional", "LATERAL")) if r1 else "LATERAL"

    c15 = int(r15.get("confianca_visual", 0) or 0) if r15 else 0
    c5 = int(r5.get("confianca_visual", 0) or 0) if r5 else 0
    c1 = int(r1.get("confianca_visual", 0) or 0) if r1 else 0

    direcoes = [b for b in (b15, b5, b1) if b in ("ALTA", "BAIXA")]
    n_dir = len(direcoes)

    if n_tfs == 0:
        veredito, alinhamento, racional = ("NEUTRO", "SEM_TFS", "Nenhum timeframe retornou dados.")
    elif n_dir == 0:
        veredito, alinhamento, racional = ("NEUTRO", "SEM_DIRECAO", f"Nenhum dos {n_tfs} TFs marcou direcao clara.")
    elif len(set(direcoes)) == 1 and n_dir == n_tfs and n_tfs >= 2:
        veredito, alinhamento, racional = ("ALINHADO_FORTE", f"{n_dir}/{n_tfs}", f"{', '.join(tfs_presentes)} em {direcoes[0]} — sinal forte" + (" (parcial)" if parcial else "") + ".")
    elif n_tfs < 3:
        _dirs_unicas = set(direcoes)
        _alinh = "PARCIAL_DIVERGENTE" if len(_dirs_unicas) >= 2 else ("PARCIAL_ALINHADO" if len(_dirs_unicas) == 1 else "PARCIAL_INDEFINIDO")
        veredito, alinhamento, racional = ("PARCIAL", _alinh, f"Parcial: apenas {', '.join(tfs_presentes)} disponiveis. Direcao = {direcoes[0] if direcoes else 'NEUTRO'}.")
    elif b15 == b5 and b5 != b1 and b1 in ("ALTA", "BAIXA"):
        veredito, alinhamento, racional = ("PULLBACK", "MACRO_MEDIO", f"Macro+Médio em {b15}; micro contra ({b1}). Aguardar pullback no M1.")
    elif b15 != b5 and b5 == b1 and b5 in ("ALTA", "BAIXA"):
        soma_micro_medio = c5 + c1
        limiar_reversao = c15 * 1.8
        if soma_micro_medio >= limiar_reversao:
            veredito, alinhamento, racional = ("REVERSAO_MICRO_MEDIO", "MICRO_MEDIO_CONTRA_MACRO", f"Micro ({b1}, {c1}%) e medio ({b5}, {c5}%) contra macro {b15} ({c15}%). Possivel reversao em curso.")
        else:
            veredito, alinhamento, racional = ("CONFLITO_MACRO", "MICRO_ALINHADO_CONTRA_MACRO", f"Micro e médio em {b5}, macro em {b15}. Nao operar contra M15.")
    else:
        veredito, alinhamento, racional = ("DIVERGENTE", "SEM_CONFLUENCIA", f"Biases: M15={b15}, M5={b5}, M1={b1}. Sem confluencia.")

    pesos = {"15m": 2.0, "5m": 1.5, "1m": 1.0}
    conf_pond = (c15 * pesos["15m"] + c5 * pesos["5m"] + c1 * pesos["1m"]) / sum(pesos.values())

    if veredito == "REVERSAO_MICRO_MEDIO": direcao_dom = b5
    elif b15 in ("ALTA", "BAIXA"): direcao_dom = b15
    elif b5 in ("ALTA", "BAIXA"): direcao_dom = b5
    else: direcao_dom = b1

    try:
        soma_micro_medio_dbg = c5 + c1
        limiar_reversao_dbg = round(c15 * 1.8, 1)
    except NameError:
        soma_micro_medio_dbg = None
        limiar_reversao_dbg = None

    return {
        "bias_m15": b15, "bias_m5": b5, "bias_m1": b1,
        "confianca_m15": c15, "confianca_m5": c5, "confianca_m1": c1,
        "confianca_micro_medio_soma": soma_micro_medio_dbg,
        "limiar_reversao": limiar_reversao_dbg,
        "veredito_mtf": veredito, "alinhamento": alinhamento,
        "direcao_dominante": direcao_dom, "confianca_ponderada": round(conf_pond, 1),
        "racional": racional, "timeframes_disponiveis": tfs_presentes,
        "n_tfs_disponiveis": n_tfs, "parcial": parcial,
        "direcoes_concordam": (len(set(direcoes)) == 1) if len(direcoes) >= 2 else None,
    }

def _resumo_tf(r: Dict[str, Any]) -> Dict[str, Any]:
    niveis = r.get("niveis_institucionais") or {}
    return {
        "bias": r.get("bias_direcional"), "confianca": r.get("confianca_visual"),
        "preco_atual": r.get("preco_atual"), "poc_ontem": niveis.get("poc_ontem"),
        "vwap_ontem": niveis.get("vwap_ontem"), "ob_alinhado_com_poc": niveis.get("ob_alinhado_com_poc"),
        "n_obs": len(r.get("order_blocks") or []), "n_fvgs": len(r.get("fair_value_gaps") or []),
        "entrada": r.get("entrada_sugerida"), "stop": r.get("stop_sugerido"), "alvos": r.get("alvos") or [],
    }

def _salvar_mtf(resultados: Dict[str, Dict[str, Any]], ativo_real: str) -> Path:
    confluencia = calcular_confluencia_mtf(resultados.get("15m", {}), resultados.get("5m", {}), resultados.get("1m", {}))
    preco_atual = (resultados.get("1m", {}).get("preco_atual") or resultados.get("5m", {}).get("preco_atual") or resultados.get("15m", {}).get("preco_atual"))
    payload = {
        "timestamp": datetime.now(BRT).isoformat(), "ativo": ativo_real, "preco_atual": preco_atual,
        "timeframes": {"15m": _resumo_tf(resultados.get("15m", {})), "5m": _resumo_tf(resultados.get("5m", {})), "1m": _resumo_tf(resultados.get("1m", {}))},
        "confluencia": confluencia,
    }
    ARQUIVO_MTF.parent.mkdir(parents=True, exist_ok=True)
    with open(ARQUIVO_MTF, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return ARQUIVO_MTF

def executar() -> int:
    print("=" * 62)
    print(" SMC Multi-Timeframe (M1 / M5 / M15)")
    print("=" * 62)

    try:
        print(f"-> Coletando {ATIVO} em 3 TFs numa conexao MT5...")
        tf_qtd = {1: TIMEFRAMES["1m"]["qtd"], 5: TIMEFRAMES["5m"]["qtd"], 15: TIMEFRAMES["15m"]["qtd"]}
        mapa_labels = {1: "1m", 5: "5m", 15: "15m"}
        coletas_por_tf = obter_candles_multi_tf(ATIVO, tf_qtd)
        coletas = {}
        for tf_min, (candles, contrato) in coletas_por_tf.items():
            coletas[mapa_labels[tf_min]] = (candles, contrato)
    except Exception as e:
        print(f"[ERRO] Coleta MT5: {e}")
        return 1

    resultados: Dict[str, Dict[str, Any]] = {}
    for tf_label, spec in TIMEFRAMES.items():
        candles, simbolo_real = coletas.get(tf_label, ([], ""))
        if not candles:
            print(f"[AVISO] {tf_label}: sem candles, pulando.")
            continue

        resultado = analisar_smc(dados_candles=candles, ativo=simbolo_real or ATIVO, timeframe=tf_label, config=CONFIG)
        resultados[tf_label] = resultado

        arquivo = BASE_DIR / "Coletas" / spec["arquivo"]
        salvar_resultado(resultado, caminho=arquivo)
        print(f"   [OK] {tf_label}: bias={resultado.get('bias_direcional')} conf={resultado.get('confianca_visual')}% -> {arquivo.name}")

    if not resultados:
        print("[ERRO] Nenhum TF processado.")
        return 1

    ativo_real = (coletas.get("5m") or ("", ""))[1] or ATIVO
    caminho_mtf = _salvar_mtf(resultados, ativo_real)
    print(f"   [OK] MTF -> {caminho_mtf.name}")

    print("\n" + "-" * 62)
    print(" RESUMO MTF")
    print("-" * 62)
    confluencia = calcular_confluencia_mtf(resultados.get("15m", {}), resultados.get("5m", {}), resultados.get("1m", {}))
    for k in ("bias_m15", "bias_m5", "bias_m1", "veredito_mtf", "alinhamento", "direcao_dominante", "confianca_ponderada"):
        print(f"  {k:22s}: {confluencia[k]}")
    print(f"  racional              : {confluencia['racional']}")
    print("=" * 62)
    return 0

if __name__ == "__main__":
    sys.exit(executar())