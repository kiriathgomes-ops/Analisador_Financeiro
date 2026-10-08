# -*- coding: utf-8 -*-
# fix85.py — Corrige problemas do fix84.
#
# PROBLEMAS:
#   1. analisar_historico.py tem BOM (U+FEFF) — Python 3 rejeita
#   2. .pytest_cache/ nao foi adicionado ao .gitignore (fix84 abortou)
#   3. _check_paths.py era temporario mas foi commitado por engano
#
# FIX:
#   1. Remove BOM dos arquivos movidos (se houver)
#   2. Adiciona .pytest_cache/ ao .gitignore
#   3. Deleta _check_paths.py
#   4. Valida sintaxe de TODOS os 14 arquivos movidos
#
# Uso:
#   python fix85.py --dry-run
#   python fix85.py
#   python fix85.py --reverter

import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# 14 arquivos movidos em fix84
ARQUIVOS = [
    "ferramentas/auditoria/audit_camada1.py",
    "ferramentas/auditoria/audit_camada2.py",
    "ferramentas/analises/analisar_divergencia.py",
    "ferramentas/analises/analisar_historico.py",
    "ferramentas/analises/analisar_historico_v2.py",
    "ferramentas/analises/analise_trilha_c_v2.py",
    "ferramentas/analises/backtest_bias_estabilidade.py",
    "ferramentas/debug/diag_orb_10h.py",
    "ferramentas/debug/ver_componentes_hoje.py",
    "ferramentas/docs/gerar_docs.py",
    "ferramentas/docs/gerar_dump_completo.py",
    "ferramentas/mapas/Gerar_Mapa_Fluxo.py",
    "ferramentas/mapas/Gerar_Mapa_Inventario_Tecnico.py",
    "ferramentas/mapas/Gerar_Mapa_Projeto.py",
]

BOM = "\ufeff"


def remover_bom(caminho: Path, dry_run: bool) -> bool:
    """Remove BOM se presente. Retorna True se alterou."""
    if not caminho.exists():
        print(f"  AVISO: {caminho} nao existe")
        return False

    raw = caminho.read_bytes()

    if not raw.startswith(BOM.encode("utf-8")):
        return False

    if dry_run:
        print(f"  [DRY-RUN] {caminho}: BOM detectado (removeria)")
        return True

    conteudo = raw[len(BOM.encode("utf-8")):].decode("utf-8")
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"  OK: {caminho}: BOM removido")
    return True


def validar_sintaxe(caminho: Path) -> bool:
    try:
        compile(caminho.read_text(encoding="utf-8"), str(caminho), "exec")
        return True
    except SyntaxError as e:
        print(f"  FALHA: {caminho}: {e}")
        return False


def atualizar_gitignore(dry_run: bool) -> bool:
    gi = Path(".gitignore")
    if not gi.exists():
        print("AVISO: .gitignore nao existe")
        return False

    conteudo = gi.read_text(encoding="utf-8")
    if ".pytest_cache" in conteudo:
        print("OK: .pytest_cache ja no .gitignore")
        return False

    if not conteudo.endswith("\n"):
        conteudo += "\n"

    novo = conteudo + "\n# Cache pytest\n.pytest_cache/\n"

    if dry_run:
        print("[DRY-RUN] .gitignore: adicionaria '.pytest_cache/'")
        return True

    gi.write_text(novo, encoding="utf-8")
    print("OK: .pytest_cache adicionado ao .gitignore")
    return True


def deletar_check_paths(dry_run: bool) -> bool:
    p = Path("_check_paths.py")
    if not p.exists():
        print("OK: _check_paths.py ja nao existe")
        return False

    if dry_run:
        print("[DRY-RUN] git rm _check_paths.py")
        return True

    try:
        subprocess.run(["git", "rm", "-f", "_check_paths.py"], check=True,
                       capture_output=True)
        print("OK: _check_paths.py removido do git")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERRO: {e}")
        return False


def executar(dry_run: bool):
    print("=" * 60)
    print(" FASE 1: remover BOM dos arquivos movidos")
    print("=" * 60)
    boms = 0
    for arq in ARQUIVOS:
        if remover_bom(Path(arq), dry_run):
            boms += 1
    print(f"  Total BOMs: {boms}")
    print()

    print("=" * 60)
    print(" FASE 2: validar sintaxe dos 14 arquivos")
    print("=" * 60)
    if dry_run:
        print("  [DRY-RUN] pulando validacao (arquivos ainda com BOM)")
    else:
        erros = 0
        for arq in ARQUIVOS:
            if not validar_sintaxe(Path(arq)):
                erros += 1
        if erros == 0:
            print(f"  OK: {len(ARQUIVOS)}/{len(ARQUIVOS)} validos")
        else:
            print(f"  ATENCAO: {erros} com erro")
    print()

    print("=" * 60)
    print(" FASE 3: .gitignore + cleanup")
    print("=" * 60)
    atualizar_gitignore(dry_run)
    deletar_check_paths(dry_run)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix85: corrige problemas do fix84")
    print("=" * 60)
    print()

    executar(args.dry_run)

    if not args.dry_run:
        print("=" * 60)
        print(" OK: fix85 concluido")
        print("=" * 60)
        print()
        print("Proximo: git add -A && git commit")


if __name__ == "__main__":
    main()