#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar_coletas_agora.py — Auditoria visual e rápida dos dados brutos e unificados.
Útil para ver se o EWZ ou outro ativo está com "bad tick" antes de rodar o pipeline.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"

def check_time(path):
    if path.exists():
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        idade = (datetime.now() - mtime).total_seconds() / 60
        return mtime.strftime("%H:%M:%S"), idade
    return "N/A", 0

def main():
    print("=" * 75)
    print(" 🕵️ AUDITORIA DE COLETAS (Bad Ticks e Sanidade)")
    print("=" * 75)

    # 1. Verifica o arquivo Unificado (o que as páginas e o Spike leem)
    unif_path = COLETAS / "DadosAtivosUnificados.json"
    if unif_path.exists():
        ts, idade = check_time(unif_path)
        print(f"\n📦 DadosAtivosUnificados.json (Atualizado às {ts} | Há {idade:.1f} min)")
        
        with open(unif_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
            
        ativos = dados.get("ativos", {})
        
        alertas = 0
        print(f"{'ATIVO':<15} | {'PREÇO':>10} | {'VARIAÇÃO':>10} | STATUS")
        print("-" * 60)
        
        # Ativos de foco para checar primeiro
        ativos_foco = ["EWZ", "VIX", "DXY", "SP500_FUT", "WIN_LAST_TICK", "WDO_FUT"]
        # Adiciona os ADRs
        ativos_foco.extend([k for k in ativos.keys() if "ADR" in k])
        
        for nome in ativos_foco:
            if nome not in ativos:
                continue
            item = ativos[nome]
            preco = item.get("preco", 0)
            var = item.get("variacao_pct", 0)
            
            status = "✅ OK"
            if abs(var) > 15.0:
                status = "🚨 BAD TICK!"
                alertas += 1
            elif abs(var) > 5.0:
                status = "⚠️ ATENÇÃO (Volátil)"
                
            print(f"{nome:<15} | {preco:>10.2f} | {var:>+9.2f}% | {status}")

        if alertas > 0:
            print(f"\n🚨 ALERTA: {alertas} ativos com variação maior que 15%. Verifique a API!")
        else:
            print("\n✅ Nenhum 'Bad Tick' (>15%) detectado nos ativos de foco.")
            
    else:
        print("\n❌ DadosAtivosUnificados.json não encontrado.")

    # 2. Verifica a Coleta Bruta (rom-0)
    rom0_path = COLETAS / "Coleta_rom-0.json"
    if rom0_path.exists():
        ts, idade = check_time(rom0_path)
        print(f"\n📦 Coleta_rom-0.json (Atualizado às {ts} | Há {idade:.1f} min)")
        
        with open(rom0_path, "r", encoding="utf-8") as f:
            rom0 = json.load(f)
            
        coletas = rom0.get("coletas", [])
        print(f"Total de registros brutos: {len(coletas)}")
        
        # Busca o EWZ especificamente
        for item in coletas:
            if item.get("ativo") == "AMEX:EWZ" or item.get("ativo") == "EWZ":
                var = (item.get("dados_reais") or {}).get("change_percent")
                print(f"   -> Leitura bruta do EWZ: {var}% (Fonte: {item.get('fonte')})")
                if var is not None and abs(var) > 15:
                    print("      🚨 EWZ corrompido na coleta bruta!")
                else:
                    print("      ✅ EWZ normal na coleta bruta.")

    print("\n" + "=" * 75)

if __name__ == "__main__":
    main()