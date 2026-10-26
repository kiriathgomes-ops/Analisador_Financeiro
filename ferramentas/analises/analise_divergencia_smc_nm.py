# -*- coding: utf-8 -*-
import json
import glob
from pathlib import Path
from collections import Counter

# Filtro pós-fix66
ARQS = sorted([
    a for a in glob.glob("Coletas/Historico_Decisoes_V2/*.json")
    if Path(a).name[:15] >= "20261006_163142"
])

divergentes = []

for arq in ARQS:
    try:
        d = json.load(open(arq, encoding="utf-8"))
    except Exception:
        continue
    
    dec = d.get("decisao", {})
    mets = dec.get("metadados", {}) or {}
    conf_bloco = mets.get("confluencia", {}) or {}
    motivo = conf_bloco.get("motivo_saida")
    
    if motivo == "divergencia_smc_nm":
        motivos = dec.get("motivos", [])
        divergentes.append({
            "arquivo": Path(arq).name,
            "motivos": motivos
        })

print(f"Total de runs com divergência SMC x NM: {len(divergentes)}\n")
print("=== EXEMPLO DOS 5 PRIMEIROS RUNS DIVERGENTES ===\n")

for i, run in enumerate(divergentes[:5], 1):
    print(f"--- RUN {i}: {run['arquivo']} ---")
    for m in run['motivos']:
        if "SMC:" in m or "NOVO_MOTOR:" in m:
            print(f"  {m}")
    print()

# Estatística: quais motivos aparecem juntos
print("=== PADRÕES DE MOTIVOS NAS DIVERGÊNCIAS ===")
padroes = Counter()
for run in divergentes:
    motivos_smc = [m for m in run['motivos'] if "SMC:" in m]
    motivos_nm = [m for m in run['motivos'] if "NOVO_MOTOR:" in m]
    if motivos_smc and motivos_nm:
        padroes[(motivos_smc[0][:50], motivos_nm[0][:50])] += 1

for (smc, nm), qtd in padroes.most_common(5):
    print(f"  [{qtd}x] SMC: {smc}... vs NM: {nm}...")