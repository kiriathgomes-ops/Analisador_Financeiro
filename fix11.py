#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix11.py — Auto-abrir snapshot no Notepad ao terminar
======================================================

Adiciona, no final do analisar_rompimento_10h.py, uma chamada que abre
automaticamente o arquivo snapshot_rompimento_10h.txt no Notepad.

Assim voce roda apenas 1 comando (python analisar_rompimento_10h.py) e o
arquivo abre sozinho — economiza os ~5 segundos de abrir manualmente as
10:05, quando cada segundo conta.

Uso:
    python fix11.py --dry-run
    python fix11.py
    python fix11.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("analisar_rompimento_10h.py")


PATCH = (
    "Auto-abre Notepad com o snapshot gerado",
    '''    print()
    print("=" * 60)
    print(" SNAPSHOT GERADO")
    print("=" * 60)
    print(f"  Arquivo : {SAIDA_PATH}")
    print(f"  Tamanho : {len(texto)} caracteres")
    if vela:
        print(f"  Vela    : {vela['status']} | O={vela['open']:.0f} H={vela['high']:.0f} L={vela['low']:.0f} C={vela['close']:.0f}")
    print()
    print("  Proximo passo:")
    print("    1. Abra o arquivo no Notepad:")
    print(f"       notepad {SAIDA_PATH}")
    print("    2. Ctrl+A, Ctrl+C")
    print("    3. Cole na IA (Claude, GPT-4, etc)")
    print()
    return 0''',
    '''    print()
    print("=" * 60)
    print(" SNAPSHOT GERADO")
    print("=" * 60)
    print(f"  Arquivo : {SAIDA_PATH}")
    print(f"  Tamanho : {len(texto)} caracteres")
    if vela:
        print(f"  Vela    : {vela['status']} | O={vela['open']:.0f} H={vela['high']:.0f} L={vela['low']:.0f} C={vela['close']:.0f}")
    print()
    print("  Abrindo no Notepad...")
    print()
    print("  Proximo passo (dentro do Notepad):")
    print("    1. Ctrl+A (seleciona tudo)")
    print("    2. Ctrl+C (copia)")
    print("    3. Cola na IA (Claude, GPT-4, etc)")
    print()

    # Abre automaticamente no Notepad (Windows)
    try:
        import subprocess
        subprocess.Popen(["notepad.exe", str(SAIDA_PATH)])
        print("  [OK] Notepad aberto.")
    except FileNotFoundError:
        # Fallback: os.startfile (abre com app padrao do .txt)
        try:
            import os
            os.startfile(str(SAIDA_PATH))
            print("  [OK] Arquivo aberto no app padrao.")
        except Exception as e:
            print(f"  [AVISO] Nao foi possivel abrir automaticamente: {e}")
            print(f"  Abra manualmente: notepad {SAIDA_PATH}")
    except Exception as e:
        print(f"  [AVISO] Falha ao abrir Notepad: {e}")
        print(f"  Abra manualmente: notepad {SAIDA_PATH}")

    print()
    return 0''',
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

    if "subprocess.Popen([\"notepad.exe\"" in conteudo_original:
        print("[AVISO] Auto-abertura ja foi aplicada. Nada a fazer.")
        return 0

    nome, antigo, novo = PATCH
    if antigo not in conteudo_original:
        print(f"[FALHA] Patch nao bateu: {nome}")
        print("        O bloco de saida do snapshot foi alterado.")
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
    print(" fix11.py — Auto-abrir snapshot no Notepad")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())