#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_historico_v2.py — Analise segmentada por horario e divergencia
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


DIR_HISTORICO = Path("Coletas/Historico_Decisoes_V2")

# Janela de leilao (a que importa operacionalmente)
LEILAO_INICIO = 8 * 60 + 45   # 08:45
LEILAO_FIM = 9 * 60 + 30      # 09:30
PREGAO_INICIO = 9 * 60        # 09:00
PREGAO_FIM = 18 * 60 + 25     # 18:25


def _extrair_hora(nome_arquivo: str) -> int | None:
    """Extrai HH*60+MM do nome tipo '20260903_084901.json'."""
    m = re.search(r"_(\d{2})(\d{2})\d{2}\.json$", nome_arquivo)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def carregar_amostras() -> list:
    if not DIR_HISTORICO.exists():
        print(f"[ERRO] Pasta nao encontrada: {DIR_HISTORICO}")
        return []

    arquivos = sorted(DIR_HISTORICO.glob("*.json"))
    print(f"[INFO] {len(arquivos)} arquivos encontrados")

    amostras = []
    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                dados = json.load(f)

            decisao = dados.get("decisao", {}) or {}
            meta = decisao.get("metadados", {}) or {}
            nm = meta.get("novo_motor", {}) or {}

            hora = _extrair_hora(arq.name)

            amostras.append({
                "arquivo": arq.name,
                "hora_min": hora,
                "score_magnitude": nm.get("score_magnitude"),
                "score_direcao": nm.get("score_direcao"),
                "gap_pontos": nm.get("gap_pontos"),
                "gap_pct": nm.get("gap_pct"),
                "divergencia": nm.get("divergencia_direcao"),
                "vies_final": decisao.get("vies_final"),
                "confianca": decisao.get("confianca"),
                "motivos": decisao.get("motivos") or [],
            })
        except Exception:
            continue

    print(f"[INFO] {len(amostras)} amostras validas")
    return amostras


def filtrar(amostras: list, inicio: int, fim: int) -> list:
    return [a for a in amostras if a.get("hora_min") is not None and inicio <= a["hora_min"] <= fim]


def analisar_grupo(nome: str, amostras: list) -> None:
    total = len(amostras)
    if total == 0:
        print(f"\n### {nome}: SEM AMOSTRAS")
        return

    com_score = [a for a in amostras if a.get("score_magnitude") is not None]
    if not com_score:
        print(f"\n### {nome}: {total} amostras, sem score_magnitude")
        return

    n = len(com_score)
    mediana = sorted(a["score_magnitude"] for a in com_score)[n // 2]
    media = sum(a["score_magnitude"] for a in com_score) / n

    # Contadores
    direcionais = sum(1 for a in com_score if a.get("vies_final") in ("COMPRA", "VENDA"))
    neutros = sum(1 for a in com_score if a.get("vies_final") == "NEUTRO")
    divergencias = sum(1 for a in com_score if a.get("divergencia") is True)
    sem_diverg = sum(1 for a in com_score if a.get("divergencia") is False)

    print(f"\n### {nome} (n={n})")
    print(f"  Score  : mediana={mediana:.1f} | media={media:.1f}")
    print(f"  Vies   : direcional={direcionais} ({direcionais/n*100:.1f}%) | neutro={neutros} ({neutros/n*100:.1f}%)")
    print(f"  Diverg : True={divergencias} ({divergencias/n*100:.1f}%) | False={sem_diverg} ({sem_diverg/n*100:.1f}%)")

    # Motivos mais comuns
    motivos_counter = Counter()
    for a in com_score:
        for m in a.get("motivos", []):
            # Simplifica: pega so o prefixo antes de ":"
            prefixo = m.split(":")[0].strip() if ":" in m else m[:40]
            motivos_counter[prefixo] += 1

    print(f"  Motivos top 5:")
    for motivo, qtd in motivos_counter.most_common(5):
        pct = qtd / n * 100
        print(f"    - {motivo[:60]:60s} {qtd:4d} ({pct:5.1f}%)")


def main() -> int:
    print("=" * 60)
    print(" analisar_historico_v2.py — Segmentacao por horario")
    print("=" * 60)

    amostras = carregar_amostras()
    if not amostras:
        return 1

    # Cobertura por faixa
    print()
    print("=" * 60)
    print(" COBERTURA POR HORARIO")
    print("=" * 60)

    leilao = filtrar(amostras, LEILAO_INICIO, LEILAO_FIM)
    pregao = filtrar(amostras, PREGAO_INICIO, PREGAO_FIM)
    fora = [a for a in amostras if a.get("hora_min") is None or
            a["hora_min"] < PREGAO_INICIO or a["hora_min"] > PREGAO_FIM]

    print(f"  Janela leilao (08:45-09:30): {len(leilao)}")
    print(f"  Janela pregao (09:00-18:25): {len(pregao)}")
    print(f"  Fora do pregao            : {len(fora)}")

    # Analisa os 3 grupos
    analisar_grupo("LEILAO (08:45-09:30)", leilao)
    analisar_grupo("PREGAO (09:00-18:25)", pregao)
    analisar_grupo("FORA (resto)", fora)

    print()
    print("=" * 60)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())