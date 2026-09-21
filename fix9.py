#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix9.py — Corrige UnicodeEncodeError do Limpar_Imagens_TradingView em subprocess
================================================================================

Problema:
  O script Limpar_Imagens_TradingView.py imprime emojis (🧹, ✅, ✨). Rodado
  direto no PowerShell, funciona (UTF-8 ativo). Rodado via subprocess.run()
  do main_pipeline.py, quebra com UnicodeEncodeError no cp1252 → exit 1.

Fix:
  1. Adiciona sys.stdout.reconfigure(encoding="utf-8") no topo do script
     (padrao ja usado em Motor_SMC_Regras.py, CalculadoraEstimativaAbertura.py, etc).
  2. Melhora o main_pipeline.run_sync_module() para capturar stdout/stderr do
     subprocess e exibir o erro real quando falha.

Uso:
    python fix9.py --dry-run
    python fix9.py
    python fix9.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# PATCHES MULTI-ARQUIVO
# ============================================================
ALVOS = {
    Path("Limpar_Imagens_TradingView.py"): [
        (
            "Adiciona reconfigure UTF-8 no stdout",
            '''import glob
import os
import re
import shutil
from pathlib import Path''',
            '''import glob
import os
import re
import shutil
import sys
from pathlib import Path

# Forca UTF-8 no terminal Windows (evita UnicodeEncodeError com emojis
# quando o script e chamado via subprocess.run() no main_pipeline.py)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass''',
        ),
    ],

    Path("main_pipeline.py"): [
        (
            "run_sync_module captura stdout/stderr e mostra erro real",
            '''def run_sync_module(module_object, name: str):
    """
    Executor dinâmico para módulos síncronos.
    Tenta invocar .main(), .executar(), .run(). Caso o script execute o código
    diretamente no bloco `if __name__ == '__main__'`, ele roda via subprocess.
    """
    start = time.perf_counter()
    logging.info(f"🚀 Iniciando: {name}")
    try:
        if hasattr(module_object, "main") and callable(module_object.main):
            module_object.main()
        elif hasattr(module_object, "executar") and callable(module_object.executar):
            module_object.executar()
        elif hasattr(module_object, "run") and callable(module_object.run):
            module_object.run()
        else:
            script_path = getattr(module_object, "__file__", None)
            if script_path:
                subprocess.run([sys.executable, script_path], check=True)
            else:
                importlib.reload(module_object)

        elapsed = time.perf_counter() - start
        logging.info(f"✅ Concluído: {name} em {elapsed:.2f}s")
    except Exception as e:
        logging.error(f"❌ Erro crítico na execução de {name}: {e}", exc_info=True)
        raise e''',
            '''def run_sync_module(module_object, name: str):
    """
    Executor dinâmico para módulos síncronos.
    Tenta invocar .main(), .executar(), .run(). Caso o script execute o código
    diretamente no bloco `if __name__ == '__main__'`, ele roda via subprocess.

    Quando roda via subprocess, captura stdout/stderr e exibe o traceback real
    do script filho em caso de falha (evita "returned non-zero exit status 1"
    sem contexto).
    """
    start = time.perf_counter()
    logging.info(f"🚀 Iniciando: {name}")
    try:
        if hasattr(module_object, "main") and callable(module_object.main):
            module_object.main()
        elif hasattr(module_object, "executar") and callable(module_object.executar):
            module_object.executar()
        elif hasattr(module_object, "run") and callable(module_object.run):
            module_object.run()
        else:
            script_path = getattr(module_object, "__file__", None)
            if script_path:
                # Captura stdout/stderr para exibir erro real do script filho
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    logging.error(
                        f"❌ Subprocess '{name}' falhou (exit {result.returncode})"
                    )
                    if result.stdout:
                        logging.error(f"--- STDOUT ---\\n{result.stdout}")
                    if result.stderr:
                        logging.error(f"--- STDERR ---\\n{result.stderr}")
                    raise subprocess.CalledProcessError(
                        result.returncode, result.args, result.stdout, result.stderr
                    )
            else:
                importlib.reload(module_object)

        elapsed = time.perf_counter() - start
        logging.info(f"✅ Concluído: {name} em {elapsed:.2f}s")
    except Exception as e:
        logging.error(f"❌ Erro crítico na execução de {name}: {e}", exc_info=True)
        raise e''',
        ),
    ],
}


# ============================================================
# LOGICA
# ============================================================
def _backups_do_alvo(alvo: Path):
    return sorted(alvo.parent.glob(f"{alvo.name}.bak_*"), reverse=True)


def reverter() -> int:
    restaurados = 0
    for alvo in ALVOS.keys():
        backups = _backups_do_alvo(alvo)
        if not backups:
            print(f"[AVISO] Sem backup para {alvo}")
            continue
        shutil.copy2(backups[0], alvo)
        print(f"[OK] {alvo} restaurado de {backups[0].name}")
        restaurados += 1
    return 0 if restaurados else 1


def _validar_sintaxe(caminho: Path) -> tuple[bool, str]:
    import ast
    try:
        ast.parse(caminho.read_text(encoding="utf-8"))
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError linha {e.lineno}: {e.msg}"


def aplicar(dry_run: bool = False) -> int:
    problemas = []
    for alvo, patches in ALVOS.items():
        if not alvo.exists():
            problemas.append(f"arquivo nao encontrado: {alvo}")
            continue
        conteudo = alvo.read_text(encoding="utf-8")
        for nome, antigo, _ in patches:
            if antigo not in conteudo:
                problemas.append(f"{alvo.name}: patch nao bate — '{nome}'")

    if problemas:
        print("[FALHA] Pre-validacao encontrou problemas:")
        for p in problemas:
            print(f"   - {p}")
        print("\nNenhuma alteracao foi feita.")
        return 2

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not dry_run:
        for alvo in ALVOS.keys():
            backup = alvo.with_suffix(f"{alvo.suffix}.bak_{timestamp}")
            shutil.copy2(alvo, backup)
            print(f"[OK] Backup: {backup.name}")
    else:
        print("[DRY-RUN] Backup nao sera criado")

    for alvo, patches in ALVOS.items():
        print(f"\n>> {alvo}")
        conteudo = alvo.read_text(encoding="utf-8")
        for i, (nome, antigo, novo) in enumerate(patches, start=1):
            if antigo in conteudo:
                conteudo = conteudo.replace(antigo, novo, 1)
                print(f"   [OK] Patch {i}/{len(patches)}: {nome}")
            else:
                print(f"   [AVISO] Patch {i}/{len(patches)}: {nome} — nao encontrado")
                return 3

        if not dry_run:
            alvo.write_text(conteudo, encoding="utf-8")
            ok, msg = _validar_sintaxe(alvo)
            if not ok:
                print(f"   [ERRO] Sintaxe invalida: {msg}")
                return 4
            print(f"   [OK] Sintaxe validada")

    print(f"\n[OK] {len(ALVOS)} arquivo(s) atualizado(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corrige UnicodeEncodeError em subprocess"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix9.py — Corrige UnicodeEncodeError do Limpar_Imagens")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())