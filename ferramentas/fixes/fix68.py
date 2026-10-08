# -*- coding: utf-8 -*-
# fix68.py — Corrige typo "eventos_structure" na page IA Spike Imagem.
#
# BUG (pages/7.2_🤖_IA_SpikeImagem.py:93):
#   eventos_est = dados_smc_regras.get("eventos_structure", [])
#                                          ^ faltava 'A' (portugues: estrutura)
#
# O .get() com a chave errada sempre retorna [], o if nunca imprime nada,
# e a secao "Ultimos Eventos de Estrutura Registrados (LTF)" fica vazia
# PERMANENTEMENTE. Bug silencioso — sem erro no log.
#
# Confirmado: Motor_SMC_Regras.py:1160 GRAVA "eventos_estrutura" (com A).
# pages/7.1 le CORRETO. So a page 7.2 tem o typo.
#
# FIX: 1 caractere (eventos_structure -> eventos_estrutura)
#
# Uso:
#   python fix68.py --dry-run
#   python fix68.py
#   python fix68.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/7.2_🤖_IA_SpikeImagem.py")

PATCHES = [
    {
        "nome": "corrige_typo_eventos_estrutura",
        "ancora_antiga": (
            '    eventos_est = dados_smc_regras.get("eventos_structure", [])'
        ),
        "ancora_nova": (
            '    eventos_est = dados_smc_regras.get("eventos_estrutura", [])'
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