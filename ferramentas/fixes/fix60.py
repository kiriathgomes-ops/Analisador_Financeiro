# -*- coding: utf-8 -*-
# fix60.py — Pivots classicos do WIN passam a vir do WIN_AJUSTE (ultimo D1 fechado).
#
# BUG (linhas 198-201):
#   H/L vinham do WIN_FUT (MT5 ao vivo, rally de hoje)
#   C vinha do previous_close do mesmo WIN_FUT (settlement de sexta)
#   Resultado: close (193000) < low (206290) -> pivots desordenados
#
# FIX:
#   1. Ler H/L/C todos de WIN_AJUSTE (settlement B3, mesmo dia).
#   2. Validacao low <= close <= high embutida (nunca mais pivot invertido).
#   3. Fallback explicito: se WIN_AJUSTE sumir, pivots = {} (nao cai pra WIN_FUT).
#
# Uso:
#   python fix60.py --dry-run     # mostra diff, nao salva
#   python fix60.py               # aplica
#   python fix60.py --reverter    # restaura backup mais recente

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQUIVO = Path("CalculadoraEstimativaAbertura.py")

PATCHES = [
    {
        "nome": "pivots_win_ajuste",
        "ancora_antiga": (
            '    win_fut = ativos_dict.get("WIN_FUT", {})\n'
            '    high_d1 = win_fut.get("high", 0.0)\n'
            '    low_d1 = win_fut.get("low", 0.0)\n'
            '    close_d1 = win_fut.get("previous_close", 0.0) or win_fut.get("close", 0.0)'
        ),
        "ancora_nova": (
            '    # fix60: pivots classicos devem vir do ULTIMO D1 FECHADO (WIN_AJUSTE = settlement B3).\n'
            '    # NAO usar WIN_FUT (preco ao vivo mistura H/L de hoje com C de ontem -> pivots desordenados).\n'
            '    win_ajuste = ativos_dict.get("WIN_AJUSTE", {})\n'
            '    high_d1 = win_ajuste.get("high", 0.0)\n'
            '    low_d1 = win_ajuste.get("low", 0.0)\n'
            '    close_d1 = win_ajuste.get("close", 0.0)'
        ),
    },
    {
        "nome": "validacao_coerencia_pivots",
        "ancora_antiga": (
            '    pivots = {}\n'
            '    if high_d1 > 0 and low_d1 > 0 and close_d1 > 0:\n'
            '        pp = (high_d1 + low_d1 + close_d1) / 3\n'
            '        pivots = {\n'
            '            "PP": round(pp, 2),\n'
            '            "R1": round((2 * pp) - low_d1, 2),\n'
            '            "R2": round(pp + (high_d1 - low_d1), 2),\n'
            '            "S1": round((2 * pp) - high_d1, 2),\n'
            '            "S2": round(pp - (high_d1 - low_d1), 2)\n'
            '        }'
        ),
        "ancora_nova": (
            '    pivots = {}\n'
            '    if high_d1 > 0 and low_d1 > 0 and close_d1 > 0 and low_d1 <= close_d1 <= high_d1:\n'
            '        pp = (high_d1 + low_d1 + close_d1) / 3\n'
            '        pivots = {\n'
            '            "PP": round(pp, 2),\n'
            '            "R1": round((2 * pp) - low_d1, 2),\n'
            '            "R2": round(pp + (high_d1 - low_d1), 2),\n'
            '            "S1": round((2 * pp) - high_d1, 2),\n'
            '            "S2": round(pp - (high_d1 - low_d1), 2)\n'
            '        }\n'
            '    else:\n'
            '        print(f"AVISO: Pivots nao calculados (H={high_d1} L={low_d1} C={close_d1} incoerentes ou ausentes)")'
        ),
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        antiga = patch["ancora_antiga"]
        n = conteudo.count(antiga)
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---")
            print(antiga)
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
        compile(conteudo, str(ARQUIVO), "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida apos patch: {e}")
        return False
    print("OK: sintaxe validada")
    return True


def mostrar_diff(antes, depois):
    print("\n--- DRY-RUN: diff ---")
    diff = difflib.unified_diff(
        antes.splitlines(),
        depois.splitlines(),
        lineterm="",
        fromfile="antes",
        tofile="depois",
    )
    for linha in diff:
        print(linha)
    print("--- DRY-RUN: nada foi salvo ---")


def reverter():
    backups = sorted(ARQUIVO.parent.glob(f"{ARQUIVO.name}.bak_*"))
    if not backups:
        print("ERRO: nenhum backup encontrado")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy(ultimo, ARQUIVO)
    print(f"OK: revertido de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if not ARQUIVO.exists():
        print(f"ERRO: {ARQUIVO} nao encontrado")
        sys.exit(1)

    if args.reverter:
        reverter()
        return

    original = ARQUIVO.read_text(encoding="utf-8")

    if not pre_validar(original):
        sys.exit(1)

    novo = aplicar(original)

    if not validar_sintaxe(novo):
        sys.exit(1)

    if args.dry_run:
        mostrar_diff(original, novo)
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ARQUIVO.parent / f"{ARQUIVO.name}.bak_{ts}"
    shutil.copy(ARQUIVO, backup)
    print(f"OK: backup criado: {backup.name}")

    ARQUIVO.write_text(novo, encoding="utf-8")
    print(f"OK: {ARQUIVO} atualizado")


if __name__ == "__main__":
    main()