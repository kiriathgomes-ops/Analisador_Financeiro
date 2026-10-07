# -*- coding: utf-8 -*-
# fix74.py — Adiciona "Cenario engine" no card 2 (Explosao Pos-Abertura).
#
# PROBLEMA:
#   O card "Explosao Pos-Abertura" mostra Status, Direcao e Forca, mas nao
#   mostra a posicao vs ajuste nem o cenario do opening_scenario_engine.
#   Esses dados agora estao disponiveis (pos-fix73) via service.decisao_v2().
#
# FIX (opcao C — so no card 2; card 1 ja tem campo "posicao"):
#   - Chama d = service.decisao_v2() dentro de render_bloco_operacionais
#   - Adiciona linha no card 2 apos "Direcao: ... Forca: ..."
#
# Uso:
#   python fix74.py --dry-run
#   python fix74.py
#   python fix74.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/2_🎯_Setup_Abertura.py")

PATCHES = [
    {
        "nome": "operacionais_carrega_d",
        "ancora_antiga": (
            '    aj = service.operacional_ajuste()\n'
            '    ex = service.operacional_explosao()'
        ),
        "ancora_nova": (
            '    aj = service.operacional_ajuste()\n'
            '    ex = service.operacional_explosao()\n'
            '    # fix74: cenario do engine (disponivel pos-fix73) pra usar no card 2\n'
            '    d = service.decisao_v2()'
        ),
    },
    {
        "nome": "card2_linha_cenario",
        "ancora_antiga": (
            '        status_ex = ex.get("status") or "—"\n'
            '        st.markdown(f"**Status:** {status_ex}")\n'
            '        st.markdown(f"**Direção:** `{ex.get(\'direcao\') or \'—\'}` · **Força:** `{ex.get(\'forca\') or \'—\'}`")'
        ),
        "ancora_nova": (
            '        status_ex = ex.get("status") or "—"\n'
            '        st.markdown(f"**Status:** {status_ex}")\n'
            '        st.markdown(f"**Direção:** `{ex.get(\'direcao\') or \'—\'}` · **Força:** `{ex.get(\'forca\') or \'—\'}`")\n'
            '        # fix74: cenario do engine (opening_scenario) — complementa a direcao do card\n'
            '        _cen = d.get("direcao_cenario") or "—"\n'
            '        _pos = d.get("posicao_ajuste") or "—"\n'
            '        st.caption(f"Cenário engine: `{_cen}` · Posição vs ajuste: `{_pos}`")'
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