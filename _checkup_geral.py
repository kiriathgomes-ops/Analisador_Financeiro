#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checkup_geral.py — Auditoria de Sanidade dos Dados do Pipeline
Verifica se os JSONs essenciais existem, têm timestamps recentes e contêm valores válidos.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"

def check_file(nome):
    path = COLETAS / nome
    if not path.exists():
        print(f"❌ {nome}: Arquivo não encontrado!")
        return None
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        idade_min = (datetime.now() - mtime).total_seconds() / 60
        if idade_min > 30:
            print(f"⚠️ {nome}: Arquivo antigo (Modificado há {idade_min:.0f} min)")
        else:
            print(f"✅ {nome}: Recente (Modificado há {idade_min:.0f} min)")
        
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ {nome}: Erro ao ler JSON ({e})")
        return None

def check_val(val, nome_campo, esperado_positivo=True):
    if val is None:
        print(f"   ❌ {nome_campo}: NULO")
        return False
    if isinstance(val, (int, float)):
        if esperado_positivo and val <= 0:
            print(f"   ❌ {nome_campo}: Valor inválido ({val})")
            return False
        print(f"   ✅ {nome_campo}: {val}")
        return True
    print(f"   ✅ {nome_campo}: {val}")
    return True

def main():
    print("=" * 60)
    print(" 🩺 CHECK-UP GERAL DO PIPELINE (Coletas e Cálculos)")
    print("=" * 60)

    # 1. Coletas Brutas
    print("\n📦 1. Coletas Brutas")
    mt5 = check_file("Dados_MT5_v2_2.json")
    if mt5:
        win = mt5.get("ativos", {}).get("WIN", {})
        check_val(win.get("last"), "WIN Last MT5")
        check_val(win.get("high"), "WIN High D1")
        check_val(win.get("low"), "WIN Low D1")
        wdo = mt5.get("ativos", {}).get("WDO", {})
        check_val(wdo.get("last"), "WDO Last MT5")

    unif = check_file("DadosAtivosUnificados.json")
    if unif:
        ativos = unif.get("ativos", {})
        check_val(ativos.get("WIN_AJUSTE", {}).get("preco"), "WIN_AJUSTE (BRAPI)")
        check_val(ativos.get("VIX", {}).get("preco"), "VIX (TradingView)")
        check_val(ativos.get("SP500_FUT", {}).get("preco"), "S&P500 (TradingView)")

    # 2. Cálculos e Pivôs
    print("\n🧮 2. Cálculos e Pivôs")
    calc = check_file("EstimativaAbertura.json")
    if calc:
        est = calc.get("estimativa_abertura", {}).get("WIN_INDICE", {})
        check_val(est.get("preco_referencia_base"), "Preço Base (Ajuste)")
        check_val(est.get("abertura_teorica_pontos"), "Abertura Teórica")

        pivots = calc.get("pivot_points", {}).get("WIN_FUT", {})
        if not pivots:
            print("   ❌ Pivôs Clássicos: Vazios")
        else:
            for p in ["PP", "R1", "R2", "S1", "S2"]:
                check_val(pivots.get(p), f"Pivô {p}")

        inst = calc.get("pivots_institucionais", {})
        check_val(inst.get("poc_ontem"), "POC Ontem")
        check_val(inst.get("vwap_ontem"), "VWAP Ontem")

    # 3. Motor SMC
    print("\n🧠 3. Motor SMC")
    smc = check_file("AnaliseGraficaSMC_Regras.json")
    if smc:
        check_val(smc.get("bias_direcional"), "Bias Direcional", esperado_positivo=False)
        check_val(smc.get("confianca_visual"), "Confiança Visual")
        check_val(smc.get("stale"), "Status Stale", esperado_positivo=False)
        
        obs = smc.get("order_blocks", [])
        if obs:
            print(f"   ✅ Order Blocks: {len(obs)} mapeados")
        else:
            print("   ⚠️ Order Blocks: Nenhum")
            
        fvgs = smc.get("fair_value_gaps", [])
        if fvgs:
            print(f"   ✅ FVGs: {len(fvgs)} mapeados")
        else:
            print("   ⚠️ FVGs: Nenhum")

    # 4. Tendências e Métricas
    print("\n📈 4. Tendências e Métricas")
    tend = check_file("Analise_Tendencias.json")
    if tend:
        win_tend = tend.get("BMFBOVESPA:WIN1!", {})
        if win_tend:
            print(f"   ✅ WIN Tendência: Padrão {win_tend.get('padrao_comportamento')}")
        else:
            print("   ❌ WIN não encontrado nas tendências")

    metricas = check_file("Metricas_Calculadas.json")
    if metricas:
        ind = metricas.get("indicadores_compostos", {})
        check_val(ind.get("indicador_mercado_externo"), "Indicador Merc. Externo", esperado_positivo=False)
        check_val(ind.get("indicador_adrs_brasileiras"), "Indicador ADRs", esperado_positivo=False)

    # 5. Decisão V2
    print("\n🎯 5. Decisão V2 (Orquestrador)")
    v2 = check_file("Decisao_V2.json")
    if v2:
        dec = v2.get("decisao", {})
        check_val(dec.get("vies_final"), "Viés Final", esperado_positivo=False)
        check_val(dec.get("confianca"), "Confiança", esperado_positivo=False)
        print(f"   ℹ️  Motivo de Saída: {dec.get('motivo_saida', 'N/A')}")

    print("\n" + "=" * 60)
    print(" 🩺 FIM DO CHECK-UP. Se tudo estiver ✅, o Spike está seguro.")
    print("=" * 60)

if __name__ == "__main__":
    main()