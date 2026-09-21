#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analisa os tipos de divergencia no leilao."""

import json
import re
from collections import Counter
from pathlib import Path

DIR = Path("Coletas/Historico_Decisoes_V2")
LEILAO_INICIO = 8 * 60 + 45
LEILAO_FIM = 9 * 60 + 30


def _hora(nome):
    m = re.search(r"_(\d{2})(\d{2})\d{2}\.json$", nome)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


print("=" * 60)
print(" Analise de divergencia no LEILAO")
print("=" * 60)

tipos = Counter()
exemplos = {}

for arq in sorted(DIR.glob("*.json")):
    h = _hora(arq.name)
    if h is None or not (LEILAO_INICIO <= h <= LEILAO_FIM):
        continue

    try:
        d = json.load(open(arq, "r", encoding="utf-8"))
    except Exception:
        continue

    dec = d.get("decisao", {}) or {}
    nm = (dec.get("metadados") or {}).get("novo_motor") or {}
    gap_dir = nm.get("direcao") or "?"
    score_dir = nm.get("score_direcao") or "?"
    diverg = nm.get("divergencia_direcao")

    if not diverg:
        tipos["SEM_DIVERGENCIA"] += 1
        continue

    # Classifica
    if score_dir == "NEUTRO":
        tipo = f"{gap_dir}_vs_NEUTRO"
    elif gap_dir == "NEUTRO":
        tipo = f"NEUTRO_vs_{score_dir}"
    else:
        tipo = f"{gap_dir}_vs_{score_dir}"

    tipos[tipo] += 1
    if tipo not in exemplos:
        exemplos[tipo] = {
            "arquivo": arq.name,
            "gap_pontos": nm.get("gap_pontos"),
            "score_magnitude": nm.get("score_magnitude"),
            "motivos": dec.get("motivos", [])[:3],
        }

print()
print("TIPOS DE DIVERGENCIA (leilao):")
for tipo, qtd in tipos.most_common():
    print(f"  {tipo:30s} {qtd:3d}")

print()
print("EXEMPLO DE CADA TIPO:")
for tipo, info in exemplos.items():
    print(f"\n  [{tipo}] {info['arquivo']}")
    print(f"    gap_pontos: {info['gap_pontos']}")
    print(f"    score_magnitude: {info['score_magnitude']}")
    print(f"    motivos: {info['motivos']}")