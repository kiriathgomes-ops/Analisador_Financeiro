"""
fix25.py — MapearTendencia15Min.py: tolerancia 0.0001 -> 0.005

Fixes APENAS a tolerancia (mudanca de 1 linha, sem quebra).
Nao altera estrutura do output — 4 consumidores ativos dependem
do formato atual (root plano de ativos).

Mudanca:
    0.0001 (0.0001%)  ->  0.005 (0.005%)
    No WIN (~190k): ~0,19 pts  ->  ~9,5 pts
    No WDO (~5.1k): ~0,005 pts ->  ~0,25 pts

Uso:
    python fix25.py --dry-run
    python fix25.py
    python fix25.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "MapearTendencia15Min.py"

PATCHES = [
    (
        "tolerancia 0.0001 -> 0.005",
        "# Tolerância em % para desconsiderar ruídos insignificantes (0.001 = 0.001%)\n"
        "TOLERANCIA_PERCENTUAL = 0.0001\n",
        "# Tolerancia em % para desconsiderar ruidos insignificantes.\n"
        "# 0.005 = 0.005%: no WIN (~190k) ~9,5 pts; no WDO (~5.1k) ~0,25 pts.\n"
        "# Bate com o threshold do mini_velocimetro (0.005).\n"
        "TOLERANCIA_PERCENTUAL = 0.005\n",
    ),
]


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def aplicar(dry_run: bool) -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo

    for nome, old, new in PATCHES:
        if old not in novo:
            print(f"  [ABORT] padrao nao encontrado: {nome}")
            return 2
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if novo == conteudo:
        print("[INFO] nada mudou.")
        return 0

    if dry_run:
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter() -> int:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
    