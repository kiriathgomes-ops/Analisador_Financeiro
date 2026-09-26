# -*- coding: utf-8 -*-
"""
fix46.py - Sobe QTD_REFRESH_INCREMENTAL de 15 para 60

Problema:
    O cache faz fetch incremental de apenas 15 candles a cada chamada.
    Se a pagina/motor ficar sem chamar obter_candles por mais de 75 min
    (15 x 5min), o proximo fetch nao cobre o gap.

    Diagnosticos de 2026-09-25 mostraram 3 gaps de 65-120 min durante o
    pregao (12:10->14:10, 09:35->10:45, 13:10->14:15).

Fix:
    Sobe QTD_REFRESH_INCREMENTAL de 15 para 60 (cobre 5h M5 / 1h M1).
    Custo adicional: ~30ms por fetch (ainda barato).

Uso:
    python fix46.py --dry-run
    python fix46.py
    python fix46.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "cache_candles.py"

ANTIGO = "QTD_REFRESH_INCREMENTAL = 15"
NOVO = "QTD_REFRESH_INCREMENTAL = 60"


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

    if NOVO in conteudo:
        print("[INFO] ja aplicado (60).")
        return 0

    if ANTIGO not in conteudo:
        print("[ABORT] padrao nao encontrado")
        print(f"  esperado: {ANTIGO}")
        return 2

    novo = conteudo.replace(ANTIGO, NOVO, 1)

    if dry_run:
        print(f"  [PATCH OK] {ANTIGO} -> {NOVO}")
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"  [PATCH OK] {ANTIGO} -> {NOVO}")
    print(f"  [BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"  [OK] {ALVO.name} atualizado.")
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