# -*- coding: utf-8 -*-
"""
fix52.py - Remove referencias a TICKER_FEF2 no Coletor

Contexto:
    fix51 removeu TICKER_FEF2 do config.py, mas o Coletor.py ainda
    importava a constante e usava numa linha de logica. Gera ImportError
    ao carregar.

Mudancas:
    A) Remove TICKER_FEF2 do import
    B) Simplifica linha de ticker_chave (a condicional nao faz mais sentido)

Uso:
    python fix52.py --dry-run
    python fix52.py
    python fix52.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Coletor.py"

IMPORT_ANTIGO = (
    '    FINNHUB_API_KEY,\n'
    '    TICKER_FEF2,\n'
    '    TICKERS_TRADINGVIEW,\n'
)
IMPORT_NOVO = (
    '    FINNHUB_API_KEY,\n'
    '    TICKERS_TRADINGVIEW,\n'
)

LOGICA_ANTIGO = (
    '                ticker_chave = "SGX:FEF2!" if ticker == TICKER_FEF2 else ticker\n'
)
LOGICA_NOVO = (
    '                ticker_chave = ticker  # fix52: sem tratamento especial de FEF2\n'
)

PATCHES = [
    ("Coletor: remove TICKER_FEF2 do import", IMPORT_ANTIGO, IMPORT_NOVO),
    ("Coletor: simplifica ticker_chave", LOGICA_ANTIGO, LOGICA_NOVO),
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