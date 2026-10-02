# -*- coding: utf-8 -*-
"""
fix55b.py - Atualiza docstring do Validador.py

Contexto:
    fix55 alinhou a contagem de ativos em 33 (main_pipeline, smoke, print
    do Validador). Faltou a docstring do modulo (linha 6) que ainda
    menciona 34. Aproveita e atualiza a data de "Atualizado".

Mudancas:
    - linha 3: atualiza data para 02/10/2026
    - linha 6: 34 ativos -> 33 ativos

Uso:
    python fix55b.py --dry-run
    python fix55b.py
    python fix55b.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Validador.py"

DATA_OLD = "# DATA: 30/07/2026 | Atualizado 18/09/2026\n"
DATA_NEW = "# DATA: 30/07/2026 | Atualizado 02/10/2026\n"

CONT_OLD = "#         34 ativos (com WIN e WDO Ajustes separados).\n"
CONT_NEW = "#         33 ativos (com WIN e WDO Ajustes separados).\n"

PATCHES = [
    ("Validador: data de atualizacao", DATA_OLD, DATA_NEW),
    ("Validador: contagem 34 -> 33 na docstring", CONT_OLD, CONT_NEW),
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
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []

    for nome, old, new in PATCHES:
        if old not in novo:
            if new in novo:
                print(f"  [INFO] ja aplicado: {nome}")
                continue
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {len(faltando)} patch(es) nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print("[INFO] nada mudou.")
        return 0

    if dry_run:
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"\n[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter():
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] nenhum backup.")
        return 1
    shutil.copy2(bak, ALVO)
    print(f"[REVERTER] {ALVO.name} restaurado de {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))