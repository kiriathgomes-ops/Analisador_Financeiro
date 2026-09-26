# -*- coding: utf-8 -*-
"""
fix48.py - Documenta semantica de calcular_confianca (sem mudanca funcional)

Contexto:
    O campo confianca_visual pode bater 100% mesmo em setups com pouca
    estrutura (ex: 2 OBs + 1 FVG). Isso NAO e bug — a formula mede presenca
    de criterios, nao probabilidade de acerto.

    Verificado em 26/09/2026 (M1 com 100% apos fix47).

Mudanca:
    - Docstring expandida em calcular_confianca explicando o que mede.
    - Comentario no call site em analisar_smc.
    - ZERO mudanca funcional.

Uso:
    python fix48.py --dry-run
    python fix48.py
    python fix48.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

# --- PATCH 1: docstring da funcao ---
DOC_ANTIGO = '''def calcular_confianca(
    bias: str,
    bos: bool,
    choch: bool,
    fvgs_abertos: List[FVG],
    obs: List[OrderBlock],
    ob_confluente: bool,
) -> int:
    pesos = {'''

DOC_NOVO = '''def calcular_confianca(
    bias: str,
    bos: bool,
    choch: bool,
    fvgs_abertos: List[FVG],
    obs: List[OrderBlock],
    ob_confluente: bool,
) -> int:
    """
    Calcula um SCORE TECNICO de presenca de criterios (0-100).

    IMPORTANTE: NAO e probabilidade de acerto.

    Mede a presenca dos 6 criterios tecnicos com pesos fixos:
        bias (25) + bos (20) + choch (10) + fvg (15) + ob (15) + ob_confluente (15)

    Um setup com 1 OB e 1 FVG pode legitimamente bater 100% se todos os
    criterios forem atendidos. Para setups com pouca estrutura, esse numero
    tende a superestimar a qualidade percebida.

    Interpretar como "score tecnico", nao como "confianca operacional".

    Ref: fix48 (2026-09-26) - semantica documentada apos caso M1 com 100%
    em setup de 2 OBs + 1 FVG.
    """
    pesos = {'''

# --- PATCH 2: comentario no call site ---
CALL_ANTIGO = '''    # 9. Confiança
    conf = calcular_confianca(bias, bos, choch, fvgs_abertos, obs, ob_confluente)'''

CALL_NOVO = '''    # 9. Confiança
    # Nota (fix48): confianca_visual e score de PRESENCA de criterios,
    # nao probabilidade de acerto. Pode bater 100% em setups com pouca
    # estrutura (1 OB, 1 FVG). Ver docstring de calcular_confianca.
    conf = calcular_confianca(bias, bos, choch, fvgs_abertos, obs, ob_confluente)'''

PATCHES = [
    ("docstring de calcular_confianca", DOC_ANTIGO, DOC_NOVO),
    ("comentario no call site", CALL_ANTIGO, CALL_NOVO),
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
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] padroes nao encontrados:")
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