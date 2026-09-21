#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_historico.py — Analise estatistica dos scores do NOVO_MOTOR
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DIR_HISTORICO = Path("Coletas/Historico_Decisoes_V2")


def carregar_amostras() -> list:
    if not DIR_HISTORICO.exists():
        print(f"[ERRO] Pasta nao encontrada: {DIR_HISTORICO}")
        return []

    arquivos = sorted(DIR_HISTORICO.glob("*.json"))
    print(f"[INFO] {len(arquivos)} arquivos encontrados em {DIR_HISTORICO}")

    amostras = []
    erros = 0

    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                dados = json.load(f)

            decisao = dados.get("decisao", {}) or {}
            meta = decisao.get("metadados", {}) or {}
            nm = meta.get("novo_motor", {}) or {}

            amostras.append({
                "arquivo": arq.name,
                "score_magnitude": nm.get("score_magnitude"),
                "score_direcao": nm.get("score_direcao"),
                "score_forca": nm.get("score_forca"),
                "vies_final": decisao.get("vies_final"),
                "confianca": decisao.get("confianca"),
            })
        except Exception:
            erros += 1
            continue

    print(f"[INFO] {len(amostras)} amostras validas, {erros} erros de leitura")
    return amostras


def percentil(valores, p):
    if not valores:
        return 0.0
    n = len(valores)
    idx = int(p / 100 * n)
    return valores[min(idx, n - 1)]


def analisar(amostras: list, limiar: int = 10) -> None:
    if not amostras:
        print("[AVISO] Sem amostras pra analisar.")
        return

    com_score = [a for a in amostras if a.get("score_magnitude") is not None]
    print(f"[INFO] {len(com_score)} amostras com score_magnitude preenchido")

    if not com_score:
        print("[AVISO] Nenhuma amostra tem score_magnitude.")
        return

    total = len(com_score)

    # Histograma
    print()
    print("=" * 60)
    print(f" DISTRIBUICAO DE SCORE_MAGNITUDE (n={total})")
    print("=" * 60)

    bins = Counter()
    for a in com_score:
        m = a["score_magnitude"]
        faixa = int(m // 5) * 5
        bins[faixa] += 1

    for faixa in sorted(bins.keys()):
        qtd = bins[faixa]
        pct = qtd / total * 100
        barra = "#" * int(pct / 2)
        print(f"  [{faixa:3d}-{faixa+4:3d}]  {qtd:4d} ({pct:5.1f}%) {barra}")

    # Forca
    print()
    print("=" * 60)
    print(" DISTRIBUICAO POR FORCA")
    print("=" * 60)
    forcas = Counter(a.get("score_forca") or "N/A" for a in com_score)
    for forca, qtd in forcas.most_common():
        pct = qtd / total * 100
        print(f"  {str(forca):20s}  {qtd:4d} ({pct:5.1f}%)")

    # Direcao
    print()
    print("=" * 60)
    print(" DISTRIBUICAO POR DIRECAO")
    print("=" * 60)
    direcoes = Counter(a.get("score_direcao") or "N/A" for a in com_score)
    for d, qtd in direcoes.most_common():
        pct = qtd / total * 100
        print(f"  {str(d):20s}  {qtd:4d} ({pct:5.1f}%)")

    # Vies final
    print()
    print("=" * 60)
    print(" VIES FINAL (orquestrador)")
    print("=" * 60)
    vieses = Counter(a.get("vies_final") or "N/A" for a in com_score)
    for v, qtd in vieses.most_common():
        pct = qtd / total * 100
        print(f"  {str(v):20s}  {qtd:4d} ({pct:5.1f}%)")

    # Limiar
    print()
    print("=" * 60)
    print(f" ANALISE DO LIMIAR (atual = {limiar})")
    print("=" * 60)

    abaixo = sum(1 for a in com_score if a["score_magnitude"] < limiar)
    acima = sum(1 for a in com_score if a["score_magnitude"] >= limiar)
    pct_abaixo = abaixo / total * 100
    pct_acima = acima / total * 100

    print(f"  Abaixo do limiar ({limiar}):  {abaixo:4d} ({pct_abaixo:5.1f}%)")
    print(f"  Acima/igual        ({limiar}):  {acima:4d} ({pct_acima:5.1f}%)")

    print()
    print("  --- Simulacao de limiares alternativos ---")
    for alt in [3, 5, 8, 10, 12, 15, 20]:
        qtd_passaria = sum(1 for a in com_score if a["score_magnitude"] >= alt)
        pct = qtd_passaria / total * 100
        marcador = " <- ATUAL" if alt == limiar else ""
        print(f"  Limiar {alt:3d}: {qtd_passaria:4d} passariam ({pct:5.1f}%){marcador}")

    # Estatisticas
    print()
    print("=" * 60)
    print(" ESTATISTICAS DESCRITIVAS")
    print("=" * 60)

    valores = sorted(a["score_magnitude"] for a in com_score)
    media = sum(valores) / total

    print(f"  Minimo   : {valores[0]:.1f}")
    print(f"  P25      : {percentil(valores, 25):.1f}")
    print(f"  Mediana  : {percentil(valores, 50):.1f}")
    print(f"  P75      : {percentil(valores, 75):.1f}")
    print(f"  P90      : {percentil(valores, 90):.1f}")
    print(f"  Maximo   : {valores[-1]:.1f}")
    print(f"  Media    : {media:.1f}")

    # Sugestao
    print()
    print("=" * 60)
    print(" SUGESTAO")
    print("=" * 60)

    p50 = percentil(valores, 50)
    p30 = percentil(valores, 30)

    if pct_abaixo > 50:
        print(f"  ATENCAO: {pct_abaixo:.1f}% das leituras estao ABAIXO do limiar {limiar}.")
        print(f"  Sugestao: reduzir para ~{int(p50)} (mediana) para aceitar 50% dos casos.")
    elif pct_abaixo < 20:
        print(f"  OK: apenas {pct_abaixo:.1f}% abaixo do limiar {limiar}.")
        print(f"  O limiar esta calibrado ou ate conservador demais.")
    else:
        print(f"  ZONA CINZA: {pct_abaixo:.1f}% abaixo do limiar {limiar}.")
        print(f"  Considere reduzir para ~{int(p30)} (P30) para aceitar 70% dos casos.")

    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limiar", type=int, default=10)
    args = parser.parse_args()

    print("=" * 60)
    print(" analisar_historico.py — Distribuicao de scores do NOVO_MOTOR")
    print("=" * 60)

    amostras = carregar_amostras()
    analisar(amostras, limiar=args.limiar)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())