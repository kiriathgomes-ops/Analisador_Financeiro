# -*- coding: utf-8 -*-
# fix77.py — Elimina fallback arbitrario dos pivots + reduz aviso MT5 fora do spread.
#
# DEBITO #1 (market_service._extrair_pivots, l.77-87):
#   Quando pivots ausentes/zerados, o sistema INVENTA niveis com preco+/-150/300.
#   O decision_engine consome como se fossem reais.
#   Fix: retornar {} vazio + log. O decision_engine ja tem fallback proprio
#   (pivots.get("pp") or ajuste or last).
#
# DEBITO #6 (Coletor.py l.1006-1009):
#   Aviso "WIN last fora do spread" e cosmico (defesa ja usa mid). Polui log
#   como se fosse erro. Reduzir nivel de ⚠️ para ℹ️.
#
# Uso:
#   python fix77.py --dry-run
#   python fix77.py
#   python fix77.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ_MS = Path("v2/core/services/market_service.py")
ARQ_COL = Path("Coletor.py")

PATCHES_MS = [
    {
        "nome": "pivots_sem_fallback_arbitrario",
        "ancora_antiga": (
            '        # Fallback quando pivots ausentes ou zerados\n'
            '        if not any(pivots.values()):\n'
            '            preco = win_fut.preco or win_ajuste or 0.0\n'
            '            base = win_ajuste if win_ajuste else preco\n'
            '            pivots = {\n'
            '                "r2": preco + 300,\n'
            '                "r1": preco + 150,\n'
            '                "pp": base,\n'
            '                "s1": preco - 150,\n'
            '                "s2": preco - 300,\n'
            '            }\n'
            '        return pivots'
        ),
        "ancora_nova": (
            '        # fix77: sem fallback arbitrario. Se pivots ausentes/zerados,\n'
            '        # retorna {} e loga. O decision_engine tem fallback proprio\n'
            '        # (pivots.get("pp") or ajuste or last). NAO inventar niveis.\n'
            '        if not any(pivots.values()):\n'
            '            print(\n'
            '                "   [INFO] _extrair_pivots: pivots indisponiveis/zerados "\n'
            '                "(EstimativaAbertura.json sem pivot_points.WIN_FUT). "\n'
            '                "Retornando {}. decision_engine usara fallback interno."\n'
            '            )\n'
            '            return {}\n'
            '        return pivots'
        ),
    },
]

PATCHES_COL = [
    {
        "nome": "aviso_spread_reduzido",
        "ancora_antiga": (
            '                print(\n'
            '                    f"   ⚠️ {prefixo} last={last_fut} fora do spread "\n'
            '                    f"[{bid},{ask}] → mid={mid} (apenas FUT)"\n'
            '                )'
        ),
        "ancora_nova": (
            '                # fix77: aviso cosmico (defesa ja usa mid). Reduzido\n'
            '                # para INFO — nao e erro, e normal fora do pregao.\n'
            '                print(\n'
            '                    f"   [INFO] {prefixo} last={last_fut} fora do spread "\n'
            '                    f"[{bid},{ask}] → mid={mid} (apenas FUT)"\n'
            '                )'
        ),
    },
]


def pre_validar(arquivo, patches):
    if not arquivo.exists():
        print(f"ABORTADO: {arquivo} nao encontrado")
        return False
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        antiga = patch["ancora_antiga"]
        n = conteudo.count(antiga)
        if n == 0:
            print(f"ABORTADO [{arquivo.name}]: ancora nao encontrada: {patch['nome']}")
            print("---"); print(antiga); print("---")
            return False
        if n > 1:
            print(f"ABORTADO [{arquivo.name}]: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(arquivo, patches):
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK [{arquivo.name}]: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo, nome):
    try:
        compile(conteudo, nome, "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida em {nome}: {e}")
        return False
    print(f"OK [{nome}]: sintaxe validada")
    return True


def mostrar_diff(antes, depois, nome):
    print(f"\n--- DRY-RUN: diff {nome} ---")
    for linha in difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ):
        print(linha)
    print(f"--- DRY-RUN {nome}: nada foi salvo ---")


def processar(arquivo, patches, dry_run):
    if not pre_validar(arquivo, patches):
        sys.exit(1)
    antes = arquivo.read_text(encoding="utf-8")
    depois = aplicar(arquivo, patches)
    if not validar_sintaxe(depois, arquivo.name):
        sys.exit(1)
    if dry_run:
        mostrar_diff(antes, depois, arquivo.name)
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = arquivo.parent / f"{arquivo.name}.bak_{ts}"
    shutil.copy(arquivo, backup)
    arquivo.write_text(depois, encoding="utf-8")
    print(f"OK [{arquivo.name}]: backup={backup.name}")


def reverter():
    for arq in [ARQ_MS, ARQ_COL]:
        backups = sorted(arq.parent.glob(f"{arq.name}.bak_*"))
        if not backups:
            print(f"AVISO: sem backup para {arq.name}")
            continue
        ultimo = backups[-1]
        shutil.copy(ultimo, arq)
        print(f"OK: revertido {arq.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    print("===== fix77: pivots sem fallback arbitrario + aviso spread reduzido =====")
    processar(ARQ_MS, PATCHES_MS, args.dry_run)
    processar(ARQ_COL, PATCHES_COL, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix77 aplicado nos 2 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()