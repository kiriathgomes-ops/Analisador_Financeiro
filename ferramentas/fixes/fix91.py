# -*- coding: utf-8 -*-
# fix91.py — Ajusta bounds do rangebreak de [18.5, 9] pra [18.6, 9].
#
# MOTIVO:
#   Os candles vao ate 18:24 (ultimo do pregao). Rangebreak [18.5, 9]
#   corta de 18:30 -> 09:00, deixando 6 min (18:24-18:30) sem sobreposicao.
#   Rangebreak [18.6, 9] corta de 18:36 -> 09:00 — preserva todos os
#   candles reais sem gap visual.
#
# Uso:
#   python fix91.py --dry-run
#   python fix91.py
#   python fix91.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/7.1_📊_SMC_Regras.py")

PATCHES = [
    {
        "nome": "bounds_186",
        "ancora_antiga": (
            'RANGEBREAKS_B3 = [\n'
            '    dict(bounds=["sat", "mon"]),\n'
            '    dict(bounds=[18.5, 9], pattern="hour"),\n'
            ']'
        ),
        "ancora_nova": (
            'RANGEBREAKS_B3 = [\n'
            '    dict(bounds=["sat", "mon"]),\n'
            '    # fix91: 18.6 = 18:36 (ultimo candle M1 e 18:24; preserva os 6min finais)\n'
            '    dict(bounds=[18.6, 9], pattern="hour"),\n'
            ']'
        ),
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        n = conteudo.count(patch["ancora_antiga"])
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---"); print(patch["ancora_antiga"]); print("---")
            return False
        if n > 1:
            print(f"ABORTADO: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(conteudo):
    for patch in PATCHES:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK: patch aplicado: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo):
    try:
        compile(conteudo, str(ARQ), "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida: {e}")
        return False
    print("OK: sintaxe validada")
    return True


def mostrar_diff(antes, depois):
    print("\n--- DRY-RUN: diff ---")
    for linha in difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ):
        print(linha)
    print("--- DRY-RUN: nada foi salvo ---")


def reverter():
    backups = sorted(ARQ.parent.glob(f"{ARQ.name}.bak_*"))
    if not backups:
        print("ERRO: nenhum backup encontrado")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy(ultimo, ARQ)
    print(f"OK: revertido de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    if not ARQ.exists():
        print(f"ERRO: {ARQ} nao encontrado")
        sys.exit(1)

    original = ARQ.read_text(encoding="utf-8")
    if not pre_validar(original):
        sys.exit(1)

    novo = aplicar(original)
    if not validar_sintaxe(novo):
        sys.exit(1)

    if args.dry_run:
        mostrar_diff(original, novo)
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ARQ.parent / f"{ARQ.name}.bak_{ts}"
    shutil.copy(ARQ, backup)
    print(f"OK: backup={backup.name}")
    ARQ.write_text(novo, encoding="utf-8")
    print(f"OK: {ARQ} atualizado")


if __name__ == "__main__":
    main()