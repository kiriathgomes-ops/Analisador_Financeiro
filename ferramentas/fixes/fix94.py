# -*- coding: utf-8 -*-
# fix94.py — Afasta a legenda do gráfico e aumenta a fonte.
#
# PROBLEMA:
#   Legenda colada no canto direito do plot (x=1.02) + fonte pequena (10)
#   atrapalha a visualização dos candles.
#
# FIX (3 patches):
#   1. x=1.02 -> x=1.10 (afasta ~8% mais pra direita)
#   2. margin r=120 -> r=180 (reserva mais espaço)
#   3. font size=10 -> size=12 na legenda
#
# Uso:
#   python fix94.py --dry-run
#   python fix94.py
#   python fix94.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/7.1_📊_SMC_Regras.py")

PATCHES = [
    {
        "nome": "legenda_x_110",
        "ancora_antiga": (
            '        legend=dict(\n'
            '            orientation="v",\n'
            '            yanchor="top",\n'
            '            y=1.0,\n'
            '            xanchor="left",\n'
            '            x=1.02,'
        ),
        "ancora_nova": (
            '        legend=dict(\n'
            '            orientation="v",\n'
            '            yanchor="top",\n'
            '            y=1.0,\n'
            '            xanchor="left",\n'
            '            x=1.10,'
        ),
    },
    {
        "nome": "legenda_fonte_12",
        "ancora_antiga": (
            '            bgcolor="rgba(22, 27, 34, 0.85)",\n'
            '            bordercolor="#30363d",\n'
            '            borderwidth=1,\n'
            '            font=dict(size=10),\n'
            '        ),'
        ),
        "ancora_nova": (
            '            bgcolor="rgba(22, 27, 34, 0.85)",\n'
            '            bordercolor="#30363d",\n'
            '            borderwidth=1,\n'
            '            font=dict(size=12),\n'
            '        ),'
        ),
    },
    {
        "nome": "margin_r_180",
        "ancora_antiga": (
            '        margin=dict(l=40, r=120, t=60, b=40),'
        ),
        "ancora_nova": (
            '        margin=dict(l=40, r=180, t=60, b=40),'
        ),
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        n = conteudo.count(patch["ancora_antiga"])
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---primeiras 200 chars---")
            print(patch["ancora_antiga"][:200])
            print("---")
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