"""
fix44.py — Ordena eventos de estrutura por idx (cronologico)

Bug pre-existente: detectar_bos_choch appenda eventos na ordem de
iteracao dos swings, nao na ordem do candle do rompimento. Isso faz
eventos[-1] nao ser o mais recente cronologicamente.

Impacto: bias_direcional podia apontar para direcao de um evento
antigo, ignorando um BOS/CHoCH mais recente de direcao oposta.

Fix: sort por e.idx (indice do candle do break) antes de retornar.

Uso:
    python fix44.py --dry-run
    python fix44.py
    python fix44.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

ANTIGO = """    if eventos:
        vistos = set()
        unicos = []
        for e in eventos:
            chave = (e.idx, e.tipo, e.direcao)
            if chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(e)
        eventos = unicos

    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias
"""

NOVO = """    if eventos:
        # Fix43: dedup por (idx, tipo, direcao)
        vistos = set()
        unicos = []
        for e in eventos:
            chave = (e.idx, e.tipo, e.direcao)
            if chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(e)
        eventos = unicos

        # Fix44: ordena cronologicamente pelo idx do candle de rompimento.
        # Sem isso, eventos[-1] nao era o mais recente (bug pre-existente).
        eventos.sort(key=lambda e: e.idx)

    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias
"""

PATCHES = [("ordena eventos por idx (cronologico)", ANTIGO, NOVO)]


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

    if ANTIGO not in conteudo:
        print("[ABORT] padrao nao encontrado.")
        return 2

    novo = conteudo.replace(ANTIGO, NOVO, 1)

    if dry_run:
        print("  [PATCH OK] ordena eventos por idx (cronologico)")
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print("  [PATCH OK] ordena eventos por idx (cronologico)")
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
