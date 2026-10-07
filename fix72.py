# -*- coding: utf-8 -*-
# fix72.py — Corrige leitura de "filtro_volume_aplicado" (page 7.2).
#
# BUG (pages/7.2_🤖_IA_SpikeImagem.py:84):
#   meta_regras.get("filtro_volume_aplicado")
#                     ^ faltava "_real" no meio
#
# Motor_SMC_Regras.py:1178 grava "filtro_volume_real_aplicado" (nome correto).
# A page le "filtro_volume_aplicado" (nome truncado) -> sempre False ->
# a secao "Auditoria do Motor Contextual" nunca mostra que o filtro foi
# aplicado, mesmo quando foi.
#
# FIX: 1 string.
#
# Uso:
#   python fix72.py --dry-run
#   python fix72.py
#   python fix72.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/7.2_🤖_IA_SpikeImagem.py")

PATCHES = [
    {
        "nome": "page72_filtro_volume_real",
        "ancora_antiga": (
            '    # fix71: "filtro_volume_aplicado" nunca e gravado no SMC.\n'
            '    # TODO: Motor_SMC_Regras deve expor esse campo no payload.\n'
            '    filtro_vol = (\n'
            '        meta_regras.get("filtro_volume_aplicado")\n'
            '        or meta_regras.get("filtro_volume")\n'
            '        or False\n'
            '    )'
        ),
        "ancora_nova": (
            '    # fix72: Motor_SMC_Regras grava "filtro_volume_real_aplicado" (com "_real").\n'
            '    # Page lia "filtro_volume_aplicado" (sem "_real") — sempre False.\n'
            '    filtro_vol = (\n'
            '        meta_regras.get("filtro_volume_real_aplicado")\n'
            '        or meta_regras.get("filtro_volume_aplicado")\n'
            '        or False\n'
            '    )'
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