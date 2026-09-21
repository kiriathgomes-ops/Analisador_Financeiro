#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix10b.py — Seta PYTHONUTF8 no topo do main_pipeline.py
========================================================

Estrategia mais simples que o fix10:
  Em vez de passar env={...} em cada subprocess.run(), seta as env vars no
  topo do main_pipeline.py. Como o subprocess herda o env do pai, TODOS os
  scripts filhos usam UTF-8 sem precisar modificar mais nada.

Arquivos alterados:
  - main_pipeline.py (1 patch)

Uso:
    python fix10b.py --dry-run
    python fix10b.py
    python fix10b.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("main_pipeline.py")


PATCH = (
    "Adiciona import os + env vars UTF-8 no topo do main_pipeline",
    '''import asyncio
import importlib
import logging
import time
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor''',
    '''import asyncio
import importlib
import logging
import os
import time
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

# Forca UTF-8 em TODOS os subprocess filhos (evita UnicodeEncodeError com
# emojis no cp1252 do Windows). Setar no processo pai faz o filho herdar.
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"''',
)


def _backup_mais_recente():
    backups = sorted(
        ARQUIVO_ALVO.parent.glob(f"{ARQUIVO_ALVO.name}.bak_*"),
        reverse=True,
    )
    return backups[0] if backups else None


def reverter() -> int:
    backup = _backup_mais_recente()
    if not backup:
        print(f"[ERRO] Nenhum backup para {ARQUIVO_ALVO}")
        return 1
    print(f"[INFO] Restaurando de: {backup.name}")
    shutil.copy2(backup, ARQUIVO_ALVO)
    print(f"[OK] {ARQUIVO_ALVO} restaurado")
    return 0


def _validar_sintaxe(caminho: Path) -> tuple[bool, str]:
    import ast
    try:
        ast.parse(caminho.read_text(encoding="utf-8"))
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError linha {e.lineno}: {e.msg}"


def aplicar(dry_run: bool = False) -> int:
    if not ARQUIVO_ALVO.exists():
        print(f"[ERRO] Arquivo nao encontrado: {ARQUIVO_ALVO.resolve()}")
        return 1

    conteudo_original = ARQUIVO_ALVO.read_text(encoding="utf-8")

    # Pre-check: se ja foi aplicado, abortar
    if "PYTHONUTF8" in conteudo_original:
        print("[AVISO] 'PYTHONUTF8' ja existe no main_pipeline.py — nada a fazer.")
        return 0

    nome, antigo, novo = PATCH
    if antigo not in conteudo_original:
        print(f"[FALHA] Patch nao bateu: {nome}")
        print("        Bloco de imports do topo nao encontrado.")
        return 2

    if not dry_run:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = ARQUIVO_ALVO.with_suffix(f".py.bak_{ts}")
        shutil.copy2(ARQUIVO_ALVO, backup)
        print(f"[OK] Backup: {backup.name}")
    else:
        print("[DRY-RUN] Backup nao sera criado")

    conteudo_novo = conteudo_original.replace(antigo, novo, 1)

    if not dry_run:
        ARQUIVO_ALVO.write_text(conteudo_novo, encoding="utf-8")
        ok, msg = _validar_sintaxe(ARQUIVO_ALVO)
        if not ok:
            print(f"[ERRO] Sintaxe invalida: {msg}")
            return 3
        print(f"[OK] Sintaxe validada")
        print(f"\n[OK] {ARQUIVO_ALVO} atualizado com sucesso")
    else:
        print(f"\n[DRY-RUN] Simulacao concluida — arquivo NAO foi salvo")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix10b.py — Seta UTF-8 no topo do main_pipeline.py")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())