# -*- coding: utf-8 -*-
"""
fix54.py - Remove ultimos fallbacks para IRON_ORE_2M

Contexto:
    Apos fix53, sobraram 2 referencias a IRON_ORE_2M como fallback
    (nunca sao acionadas porque o ativo nao existe mais). O fix51
    simplificou o sistema pra usar F1 (IRON_ORE). Vamos remover o
    codigo morto.

Mudancas:
    A) v2/core/services/market_service.py
       - iron_ore: remove "or get_ativo IRON_ORE_2M"
    B) v2/pages/2_analise_detalhada.py
       - iron: usa IRON_ORE direto (sem condicional)

Uso:
    python fix54.py --dry-run
    python fix54.py
    python fix54.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Patch 1: market_service.py
ARQ1 = ROOT / "v2" / "core" / "services" / "market_service.py"
P1_OLD = (
    '        iron_ore = self._snapshot_from_dict(\n'
    '            get_ativo("IRON_ORE_2M") or get_ativo("IRON_ORE")\n'
    '        )\n'
)
P1_NEW = (
    '        iron_ore = self._snapshot_from_dict(get_ativo("IRON_ORE"))\n'
)

# Patch 2: 2_analise_detalhada.py
ARQ2 = ROOT / "v2" / "pages" / "2_analise_detalhada.py"
P2_OLD = (
    '        iron = _snapshot(ativos, "IRON_ORE_2M") if _snapshot(ativos, "IRON_ORE_2M")["preco"] > 0 else _snapshot(ativos, "IRON_ORE")\n'
)
P2_NEW = (
    '        iron = _snapshot(ativos, "IRON_ORE")\n'
)

PATCHES = [
    ("market_service: remove fallback IRON_ORE_2M", ARQ1, P1_OLD, P1_NEW),
    ("2_analise_detalhada: usa IRON_ORE direto", ARQ2, P2_OLD, P2_NEW),
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
            faltando.append(f"{nome} (arquivo nao existe: {alvo})")
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