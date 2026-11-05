#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditoria_final_coletas.py — Verificação profunda das coletas brutas.
"""
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
COLETAS = BASE_DIR / "Coletas"

def auditar():
    print("=" * 70)
    print(" 🕵️ AUDITORIA FINAL DAS COLETAS (33 ATIVOS)")
    print("=" * 70)

    # 1. Verifica Coleta_rom-0 (o "agora")
    rom0_path = COLETAS / "Coleta_rom-0.json"
    if not rom0_path.exists():
        print("❌ Coleta_rom-0.json não encontrado.")
        return

    with open(rom0_path, "r", encoding="utf-8") as f:
        rom0 = json.load(f)

    coletas = rom0.get("coletas", [])
    print(f"\n📦 ROM-0 ({len(coletas)} ativos coletados)")

    erros = []
    nulos = []

    for item in coletas:
        ativo = item.get("ativo", "?")
        status = item.get("status")
        dados = item.get("dados_reais") or {}
        close = dados.get("close")

        if status != "OK":
            erros.append(f"{ativo} (Status: {status})")
        elif close is None or not isinstance(close, (int, float)) or close <= 0:
            nulos.append(f"{ativo} (close: {close})")

    if not erros and not nulos:
        print("   ✅ Todos os ativos têm Status OK e Close numérico.")
    else:
        if erros:
            print(f"   ⚠️ {len(erros)} ativos com Status != OK:")
            for e in erros[:10]: print(f"      - {e}")
        if nulos:
            print(f"   ⚠️ {len(nulos)} ativos com close nulo/inválido:")
            for n in nulos[:10]: print(f"      - {n}")

    # 2. Verifica Dados_Validados
    val_path = COLETAS / "Dados_Validados.json"
    if val_path.exists():
        with open(val_path, "r", encoding="utf-8") as f:
            val = json.load(f)
        meta = val.get("metadata_validacao", {})
        print(f"\n📦 Dados_Validados.json")
        print(f"   Recebidos: {meta.get('total_recebidos')} | Aprovados: {meta.get('total_aprovados')} | Rejeitados: {meta.get('total_rejeitados')}")
        
        rejeicoes = val.get("relatorio_rejeicoes", [])
        if rejeicoes:
            print(f"   ⚠️ Ativos rejeitados pelo Validador:")
            for r in rejeicoes: print(f"      - {r.get('ativo')}: {r.get('motivo')}")
        else:
            print("   ✅ Nenhuma rejeição.")
    else:
        print("\n❌ Dados_Validados.json não encontrado.")

    # 3. Verifica Timestamp da coleta
    meta_coleta = rom0.get("metadata_coleta", {})
    ts_str = meta_coleta.get("timestamp_coleta")
    if ts_str:
        ts = datetime.fromisoformat(ts_str)
        idade = (datetime.now() - ts).total_seconds() / 60
        print(f"\n⏱️ Última coleta: {ts.strftime('%H:%M:%S')} (Há {idade:.0f} minutos)")
        if idade > 15:
            print("   ⚠️ ATENÇÃO: A última coleta tem mais de 15 minutos! O pipeline pode estar parado.")
        else:
            print("   ✅ Coleta fresca.")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    auditar()