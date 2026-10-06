# -*- coding: utf-8 -*-
# fix66b.py — Validador aceita status "OK_*" (OK_TV_FALLBACK do fix66).
#
# BUG (furo do fix66):
#   fix66 criou status "OK_TV_FALLBACK" pra ADRs que caem no fallback TV.
#   Validador.py:78 tem `if status_fonte != "OK"` — rejeita os 2 OTCs.
#   Efeito: indicador_adrs perde 2 componentes em vez de ganhar.
#
# FIX:
#   Aceitar status.startswith("OK") — cobre OK, OK_TV_FALLBACK, e futuros
#   status OK_* (OK_BRAPI, OK_MT5, etc). Mantem rejeicao de STALE/ERRO/None.
#
# Uso:
#   python fix66b.py --dry-run
#   python fix66b.py
#   python fix66b.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("Validador.py")

PATCHES = [
    {
        "nome": "validador_aceita_status_ok_prefix",
        "ancora_antiga": (
            '    # 1. Validação do Status da Coleta e Estrutura dos Dados\n'
            '    if status_fonte != "OK" or not dados:\n'
            '        return False, f"Status de coleta inválido: {status_fonte}", None'
        ),
        "ancora_nova": (
            '    # 1. Validação do Status da Coleta e Estrutura dos Dados\n'
            '    # fix66b: aceita OK e OK_* (ex: OK_TV_FALLBACK do fix66).\n'
            '    # Rejeita STALE, ERRO, None e qualquer status nao-OK.\n'
            '    _status_ok = isinstance(status_fonte, str) and status_fonte.startswith("OK")\n'
            '    if not _status_ok or not dados:\n'
            '        return False, f"Status de coleta inválido: {status_fonte}", None'
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