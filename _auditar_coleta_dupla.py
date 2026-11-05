#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditar_coleta_dupla.py — Auditoria visual da Coleta Dupla (Pré + Diário)
Verifica se o Coletor.py e o Validador.py estão salvando os campos corretamente.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"

def ler_json(path):
    if not path.exists(): return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro lendo {path.name}: {e}")
        return {}

def main():
    print("=" * 80)
    print(" 🕵️ AUDITORIA DA COLETA DUPLA (PRÉ/PÓS + DIÁRIO)")
    print("=" * 80)

    # 1. Verifica o Coleta_rom-0 (Bruto)
    rom0 = ler_json(COLETAS / "Coleta_rom-0.json")
    coletas = rom0.get("coletas", [])
    
    print(f"\n📦 Coleta_rom-0.json ({len(coletas)} ativos brutos)")
    
    ativos_foco = ["NYSE:VALE", "NYSE:PBR", "NYSE:ITUB", "OTC:BDORY", "NYSE:BBD", "OTC:BOLSY", "AMEX:EWZ"]
    
    for ativo in ativos_foco:
        # Busca na lista de coletas brutas
        item = next((x for x in coletas if x.get("ativo") == ativo), None)
        
        if not item:
            print(f"  ❌ {ativo:<12} | NÃO ENCONTRADO (Descartado pela API?)")
            continue
            
        dados = item.get("dados_reais") or {}
        cp = dados.get("change_percent")
        cd = dados.get("change_daily")
        
        status = item.get("status")
        if status != "OK":
            print(f"  ⚠️ {ativo:<12} | Status: {status} | Dados: {dados}")
            continue
            
        print(f"  ✅ {ativo:<12} | Agora (Pré): {cp:>6.2f}% | Diário: {cd:>6.2f}%")

    # 2. Verifica o Dados_Validados
    validados = ler_json(COLETAS / "Dados_Validados.json")
    ativos_val = validados.get("ativos_validados", [])
    
    print(f"\n📦 Dados_Validados.json ({len(ativos_val)} ativos aprovados)")
    
    # Filtra apenas os que devem ter os dois campos (ADRs)
    adrs_validados = [a for a in ativos_val if a.get("ativo_id", "").endswith("_ADR") or a.get("ativo_id") == "EWZ"]
    
    if not adrs_validados:
        print("  ❌ Nenhuma ADR passou pelo Validador!")
        
    for a in adrs_validados:
        nome = a.get("ativo_id")
        cp = a.get("change_percent")
        cd = a.get("change_daily")
        
        # Verifica se os campos existem nas chaves
        tem_cd = "change_daily" in a
        
        cd_str = f"{cd:>6.2f}%" if cd is not None else "  None"
        print(f"  {'✅' if tem_cd else '⚠️'} {nome:<12} | Agora (Pré): {cp:>6.2f}% | Diário: {cd_str}")

    print("\n" + "=" * 80)
    print(" FIM DA AUDITORIA")
    print("=" * 80)

if __name__ == "__main__":
    main()