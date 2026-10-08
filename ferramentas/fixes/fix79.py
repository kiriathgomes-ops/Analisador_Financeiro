# -*- coding: utf-8 -*-
# fix79.py — Corrige fix73: le cenario de atualizacoes[-1], nao de "ultimo".
#
# BUG (introduzido pelo fix73):
#   _ult = _hist.get("ultimo") or (_hist.get("atualizacoes") or [{}])[-1]
#   cenario = _ult.get("cenario", {}) or {}
#
#   O dict "ultimo" EXISTE (resumo achatado), entao o "or" nunca cai no
#   fallback atualizacoes[-1]. E "ultimo" nao tem campo "cenario" — so tem
#   posicao/direcao/cenario_principal (strings). Resultado: cenario={} sempre.
#
# ESTRUTURA REAL (verificado 07/10):
#   - historico["ultimo"]: resumo achatado (sem "cenario")
#   - historico["atualizacoes"][-1]["cenario"]: dict completo (8 chaves)
#
# FIX:
#   Tentar atualizacoes[-1].cenario PRIMEIRO, fallback em "ultimo".
#
# Uso:
#   python fix79.py --dry-run
#   python fix79.py
#   python fix79.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/2_🎯_Setup_Abertura.py")

PATCHES = [
    {
        "nome": "page2_le_cenario_de_atualizacoes",
        "ancora_antiga": (
            '            _hist, _ = carregar_json_absoluto(f"Historico_Aberturas/{_hoje}.json")\n'
            '            if _hist:\n'
            '                _ult = _hist.get("ultimo") or (_hist.get("atualizacoes") or [{}])[-1]\n'
            '                cenario = _ult.get("cenario", {}) or {}'
        ),
        "ancora_nova": (
            '            _hist, _ = carregar_json_absoluto(f"Historico_Aberturas/{_hoje}.json")\n'
            '            if _hist:\n'
            '                # fix79: "cenario" vive em atualizacoes[-1].cenario.\n'
            '                # "ultimo" e um resumo achatado SEM "cenario" (bug fix73).\n'
            '                _atu = _hist.get("atualizacoes") or []\n'
            '                if _atu:\n'
            '                    cenario = (_atu[-1].get("cenario") or {})\n'
            '                if not cenario:\n'
            '                    # fallback: tentar "ultimo" (caso o schema mude)\n'
            '                    _ult = _hist.get("ultimo") or {}\n'
            '                    cenario = _ult.get("cenario", {}) or {}'
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