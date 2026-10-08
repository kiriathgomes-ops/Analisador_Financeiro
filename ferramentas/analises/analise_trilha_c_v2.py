# -*- coding: utf-8 -*-
# analise_trilha_c_v2.py — Analise profunda dos runs historicos (Trilha C).
#
# Melhorias sobre v1:
#   - Parseia "motivos" para extrair SMC direcao + confianca
#   - Reconstroi score_signed (direcao x magnitude)
#   - Matriz de confusao SMC x NM
#   - Serie temporal por dia
#   - Correlacao motivo_saida x score_magnitude

import json
import glob
import re
from collections import Counter, defaultdict
from statistics import mean, median

ARQS = sorted(glob.glob("Coletas/Historico_Decisoes_V2/*.json"))
print(f"Total de runs: {len(ARQS)}\n")

re_smc = re.compile(r"SMC:\s*(\w+)\s*\(conf\.\s*(\d+)%\)")
re_nm = re.compile(r"NOVO_MOTOR:\s*(\w+)\s*\(score\s*([\d.]+),\s*gap\s*([+-]?\d+)\s*pts\)")

# ---- Coleta ----
registros = []
for arq in ARQS:
    try:
        d = json.load(open(arq, encoding="utf-8"))
    except Exception:
        continue
    dec = d.get("decisao", {})
    mets = dec.get("metadados", {}) or {}
    nm = mets.get("novo_motor", {}) or {}
    conf_bloco = mets.get("confluencia", {}) or {}
    motivos = dec.get("motivos", []) or []

    smc_dir, smc_conf = None, None
    nm_dir_motivo, nm_score_motivo, nm_gap_motivo = None, None, None
    for m in motivos:
        g = re_smc.search(m)
        if g:
            smc_dir, smc_conf = g.group(1), int(g.group(2))
        g = re_nm.search(m)
        if g:
            nm_dir_motivo = g.group(1)
            nm_score_motivo = float(g.group(2))
            nm_gap_motivo = int(g.group(3))

    registros.append({
        "arq": arq,
        "nome": arq.split("\\")[-1],
        "data": arq.split("\\")[-1][:8],
        "smc_dir": smc_dir,
        "smc_conf": smc_conf,
        "nm_dir_motivo": nm_dir_motivo,
        "nm_score_motivo": nm_score_motivo,
        "nm_dir_payload": nm.get("score_direcao"),
        "nm_mag_payload": nm.get("score_magnitude"),
        "nm_forca": nm.get("score_forca"),
        "nm_gap": nm.get("gap_pontos"),
        "gap_fonte": nm.get("gap_fonte"),
        "motivo_saida": conf_bloco.get("motivo_saida"),
        "smc_conf_ajustado": conf_bloco.get("smc_conf_ajustado"),
    })

# ---- 1. Serie temporal ----
print("=== 1. Serie temporal (por dia) ===")
por_dia = defaultdict(list)
for r in registros:
    por_dia[r["data"]].append(r)

for data in sorted(por_dia.keys()):
    runs = por_dia[data]
    smc_dirs = Counter(r["smc_dir"] for r in runs if r["smc_dir"])
    nm_dirs = Counter(r["nm_dir_motivo"] for r in runs if r["nm_dir_motivo"])
    div = sum(1 for r in runs if r["smc_dir"] and r["nm_dir_motivo"]
              and r["smc_dir"] != r["nm_dir_motivo"])
    print(f"  {data}: {len(runs):>3} runs | SMC={dict(smc_dirs)} | NM={dict(nm_dirs)} | divergentes={div}")
print()

# ---- 2. Matriz de confusao SMC x NM ----
print("=== 2. Matriz de confusao SMC x NM ===")
matriz = Counter()
for r in registros:
    if r["smc_dir"] and r["nm_dir_motivo"]:
        matriz[(r["smc_dir"], r["nm_dir_motivo"])] += 1
for (s, n), v in sorted(matriz.items(), key=lambda x: -x[1]):
    print(f"  SMC={s:<8} NM={n:<8} → {v:>3} ({100*v/sum(matriz.values()):.1f}%)")
print()

# ---- 3. Distribuicao de SMC confianca ----
print("=== 3. Distribuicao de SMC confianca ===")
confs = [r["smc_conf"] for r in registros if r["smc_conf"] is not None]
if confs:
    c = Counter(confs)
    for k, v in sorted(c.items()):
        print(f"  conf={k}%: {v} ({100*v/len(confs):.1f}%)")
print()

# ---- 4. Score signed reconstruido ----
print("=== 4. Score signed reconstruido (direcao x magnitude) ===")
signed = []
for r in registros:
    mag = r["nm_mag_payload"]
    dir_ = r["nm_dir_payload"]
    if mag is None or dir_ is None:
        continue
    if dir_ == "COMPRA":
        signed.append(+float(mag))
    elif dir_ == "VENDA":
        signed.append(-float(mag))
    else:
        signed.append(0.0)

if signed:
    neg = sum(1 for s in signed if s < 0)
    pos = sum(1 for s in signed if s > 0)
    zero = sum(1 for s in signed if s == 0)
    print(f"  N: {len(signed)}")
    print(f"  Negativos (VENDA): {neg} ({100*neg/len(signed):.1f}%)")
    print(f"  Positivos (COMPRA): {pos} ({100*pos/len(signed):.1f}%)")
    print(f"  Neutros (zero):     {zero} ({100*zero/len(signed):.1f}%)")
    # Histograma em faixas de 20
    faixas = defaultdict(int)
    for s in signed:
        faixa = int(abs(s) // 20) * 20
        faixas[faixa] += 1
    print("  Distribuicao por magnitude:")
    for faixa in sorted(faixas.keys()):
        n = faixas[faixa]
        barra = "#" * int(50 * n / len(signed))
        print(f"    |score| in [{faixa:>3}-{faixa+19:>3}]: {n:>4} {barra}")
print()

# ---- 5. Motivo de saida x magnitude ----
print("=== 5. Motivo de saida x magnitude NM ===")
por_motivo = defaultdict(list)
for r in registros:
    if r["motivo_saida"] and r["nm_mag_payload"] is not None:
        por_motivo[r["motivo_saida"]].append(float(r["nm_mag_payload"]))

for motivo, mags in sorted(por_motivo.items(), key=lambda x: -len(x[1])):
    if mags:
        print(f"  {motivo}: N={len(mags)} mag_media={mean(mags):.1f} mag_mediana={median(mags):.1f}")
print()

# ---- 6. gap_fonte ----
print("=== 6. Distribuicao de gap_fonte ===")
fontes = Counter(r["gap_fonte"] for r in registros)
for k, v in fontes.most_common():
    print(f"  {k}: {v} ({100*v/len(registros):.1f}%)")
print()

# ---- 7. % NEUTRO hipotetico com limiares alternativos ----
print("=== 7. Simulacao: % NEUTRO com LIMIAR_DIRECAO alternativos ===")
print("  (usando score_magnitude como proxy do |score_signed|)")
mags = [float(r["nm_mag_payload"]) for r in registros if r["nm_mag_payload"] is not None]
if mags:
    for limiar in [5, 10, 15, 20, 25, 30, 40]:
        neutros = sum(1 for m in mags if m <= limiar)
        print(f"  LIMIAR={limiar:>3}: {100*neutros/len(mags):>5.1f}% NEUTRO ({neutros}/{len(mags)})")