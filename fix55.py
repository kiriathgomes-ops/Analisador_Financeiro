# -*- coding: utf-8 -*-
"""
fix55.py - Alinha contagem de ativos em 33 (apos remover IRON_ORE_2M)

Contexto:
    fix51 removeu IRON_ORE_2M. Total caiu de 34 para 33 ativos.
    Validador.py ja foi atualizado (34 -> 33), mas duas outras
    mensagens ainda dizem numeros antigos:
        - main_pipeline.py: "Validador de Dados (34 Ativos)"
        - Temp_Validacao_Smoke.py: "Sanitizacao 32 Ativos"

Uso:
    python fix55.py --dry-run
    python fix55.py
    python fix55.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Patch 1: main_pipeline.py
ARQ1 = ROOT / "main_pipeline.py"
P1_OLD = '"Validador de Dados (34 Ativos)"'
P1_NEW = '"Validador de Dados (33 Ativos)"'

# Patch 2: Temp_Validacao_Smoke.py
ARQ2 = ROOT / "Temp_Validacao_Smoke.py"
P2_OLD = '"Validador.py (Sanitização 32 Ativos)"'
P2_NEW = '"Validador.py (Sanitização 33 Ativos)"'

PATCHES = [
    ("main_pipeline: 34 -> 33 ativos", ARQ1, P1_OLD, P1_NEW),
    ("smoke test: 32 -> 33 ativos", ARQ2, P2_OLD, P2_NEW),
]


def _backup(p):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def aplicar(dry_run):
    mudancas = 0
    faltando = []

    for nome, alvo, old, new in PATCHES:
        if not alvo.exists():
            faltando.append(f"{nome} (arquivo nao existe)")
            continue
        conteudo = alvo.read_text(encoding="utf-8")
        if old not in conteudo:
            if new in conteudo:
                print(f"  [INFO] ja aplicado: {nome}")
                continue
            faltando.append(f"{nome} (ancora nao encontrada)")
            continue
        novo = conteudo.replace(old, new, 1)
        if not dry_run:
            bak = _backup(alvo)
            print(f"  [BACKUP] {bak.name}")
            alvo.write_text(novo, encoding="utf-8")
        print(f"  [PATCH OK] {nome}")
        mudancas += 1

    if faltando:
        print(f"\n[ABORT] {len(faltando)} patch(es) nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if mudancas == 0:
        print("\n[INFO] nada a fazer.")
        return 0

    if dry_run:
        print(f"\n[DRY-RUN] {mudancas} patch(es) seriam aplicados.")
        return 0

    print(f"\n[OK] {mudancas} patch(es) aplicados.")
    return 0


def reverter():
    for nome, alvo, old, new in PATCHES:
        if not alvo.exists():
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[SKIP] {alvo.name}: sem backup")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} <- {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))