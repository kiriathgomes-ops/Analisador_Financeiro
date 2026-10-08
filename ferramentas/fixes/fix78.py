# -*- coding: utf-8 -*-
# fix78.py — Adiciona flag --once ao Agendador.py.
#
# DEBITO #2:
#   Agendador so roda em loop continuo. Pra debug, precisa Ctrl+C.
#   Fix: adicionar --once (executa 1 ciclo imediato e sai).
#
# Uso:
#   python Agendador.py           # modo normal (loop continuo)
#   python Agendador.py --once    # 1 ciclo imediato e sai
#
# Uso do fix:
#   python fix78.py --dry-run
#   python fix78.py
#   python fix78.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("Agendador.py")

PATCHES = [
    # ---- 1. Adiciona import argparse ----
    {
        "nome": "add_import_argparse",
        "ancora_antiga": (
            'import os\n'
            'import subprocess\n'
            'import sys\n'
            'import time\n'
            'from datetime import datetime'
        ),
        "ancora_nova": (
            'import argparse\n'
            'import os\n'
            'import subprocess\n'
            'import sys\n'
            'import time\n'
            'from datetime import datetime'
        ),
    },
    # ---- 2. Assinatura + branch --once antes do while ----
    {
        "nome": "iniciar_agendador_once",
        "ancora_antiga": (
            'def iniciar_agendador():\n'
            '    print("============================================================")'
        ),
        "ancora_nova": (
            'def iniciar_agendador(once: bool = False):\n'
            '    print("============================================================")'
        ),
    },
    # ---- 3. Early return --once antes do while True ----
    {
        "nome": "branch_once_antes_do_loop",
        "ancora_antiga": (
            '            contador += 1\n'
            '    print()\n'
            '\n'
            '    while True:'
        ),
        "ancora_nova": (
            '            contador += 1\n'
            '    print()\n'
            '\n'
            '    # fix78: modo --once (debug) — executa 1 ciclo e sai\n'
            '    if once:\n'
            '        print(f"\\n[{datetime.now().strftime(\'%H:%M:%S\')}] 🚀 [--once] Disparando Main Pipeline (imediato)...")\n'
            '        try:\n'
            '            subprocess.run([sys.executable, SCRIPT_PIPELINE], check=True)\n'
            '            print(f"[{datetime.now().strftime(\'%H:%M:%S\')}] ✅ Ciclo unico concluido.")\n'
            '        except subprocess.CalledProcessError as e:\n'
            '            print(f"❌ Erro na execucao do pipeline: {e}")\n'
            '        except Exception as e:\n'
            '            print(f"⚠️ Falha inesperada: {e}")\n'
            '        return\n'
            '\n'
            '    while True:'
        ),
    },
    # ---- 4. Main com parse de args ----
    {
        "nome": "main_com_parse_args",
        "ancora_antiga": (
            'if __name__ == "__main__":\n'
            '    iniciar_agendador()'
        ),
        "ancora_nova": (
            'if __name__ == "__main__":\n'
            '    _parser = argparse.ArgumentParser(\n'
            '        description="Agendador sincronizado do pipeline (grade :05s + especiais)"\n'
            '    )\n'
            '    _parser.add_argument(\n'
            '        "--once", action="store_true",\n'
            '        help="Executa 1 ciclo imediato e sai (modo debug)"\n'
            '    )\n'
            '    _args = _parser.parse_args()\n'
            '    iniciar_agendador(once=_args.once)'
        ),
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        antiga = patch["ancora_antiga"]
        n = conteudo.count(antiga)
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---"); print(antiga); print("---")
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