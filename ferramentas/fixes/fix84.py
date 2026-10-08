# -*- coding: utf-8 -*-
# fix84.py — Arquiva utilitarios da raiz em ferramentas/<subpasta>/.
#
# Move 14 arquivos + ajusta paths internos + atualiza .gitignore.
#
# ARQUIVOS QUE FICAM NA RAIZ (nao movem):
#   - win_abertura_sniper.py (entrypoint 08:55)
#   - analisar_rompimento_10h.py (analise de rompimento)
#   - MapearTendencia15Min.py (chamado por .bat launcher)
#
# Uso:
#   python fix84.py --dry-run
#   python fix84.py
#   python fix84.py --reverter

import sys
import shutil
import argparse
import subprocess
import difflib
from pathlib import Path
from datetime import datetime

# Mapa: arquivo_origem -> destino
MOVE = {
    "audit_camada1.py": "ferramentas/auditoria/audit_camada1.py",
    "audit_camada2.py": "ferramentas/auditoria/audit_camada2.py",
    "analisar_divergencia.py": "ferramentas/analises/analisar_divergencia.py",
    "analisar_historico.py": "ferramentas/analises/analisar_historico.py",
    "analisar_historico_v2.py": "ferramentas/analises/analisar_historico_v2.py",
    "analise_trilha_c_v2.py": "ferramentas/analises/analise_trilha_c_v2.py",
    "backtest_bias_estabilidade.py": "ferramentas/analises/backtest_bias_estabilidade.py",
    "diag_orb_10h.py": "ferramentas/debug/diag_orb_10h.py",
    "ver_componentes_hoje.py": "ferramentas/debug/ver_componentes_hoje.py",
    "gerar_docs.py": "ferramentas/docs/gerar_docs.py",
    "gerar_dump_completo.py": "ferramentas/docs/gerar_dump_completo.py",
    "Gerar_Mapa_Fluxo.py": "ferramentas/mapas/Gerar_Mapa_Fluxo.py",
    "Gerar_Mapa_Inventario_Tecnico.py": "ferramentas/mapas/Gerar_Mapa_Inventario_Tecnico.py",
    "Gerar_Mapa_Projeto.py": "ferramentas/mapas/Gerar_Mapa_Projeto.py",
}

# Ajuste de path interno: arquivos que precisam `__file__.parent` -> 3 niveis
PATH_FIXES = {
    "diag_orb_10h.py": [
        (
            "ROOT = Path(__file__).resolve().parent",
            "ROOT = Path(__file__).resolve().parent.parent.parent",
        ),
    ],
    "gerar_docs.py": [
        (
            "RAIZ = Path(__file__).resolve().parent",
            "RAIZ = Path(__file__).resolve().parent.parent.parent",
        ),
    ],
    "gerar_dump_completo.py": [
        (
            "RAIZ = Path(__file__).resolve().parent",
            "RAIZ = Path(__file__).resolve().parent.parent.parent",
        ),
    ],
    "Gerar_Mapa_Fluxo.py": [
        (
            "BASE_DIR = Path(__file__).resolve().parent",
            "BASE_DIR = Path(__file__).resolve().parent.parent.parent",
        ),
    ],
}


def git_mv(origem: str, destino: str):
    """git mv origem destino"""
    subprocess.run(["git", "mv", origem, destino], check=True)


def git_status_short():
    r = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, check=True,
    )
    return r.stdout


def pre_validar():
    """Verifica que todas as origens existem e nenhum destino ja existe."""
    erros = []
    for orig, dest in MOVE.items():
        p_orig = Path(orig)
        p_dest = Path(dest)
        if not p_orig.exists():
            erros.append(f"ORIGEM NAO EXISTE: {orig}")
        if p_dest.exists():
            erros.append(f"DESTINO JA EXISTE: {dest}")
    if erros:
        print("ABORTADO:")
        for e in erros:
            print(f"  {e}")
        return False
    print(f"OK: pre-validacao ({len(MOVE)} arquivos pra mover)")
    return True


def aplicar_path_fix(origem: str, dry_run: bool):
    """Aplica substituicao de path interno (se houver)."""
    if origem not in PATH_FIXES:
        return

    p = Path(origem)
    conteudo = p.read_text(encoding="utf-8")
    original = conteudo

    for antigo, novo in PATH_FIXES[origem]:
        n = conteudo.count(antigo)
        if n != 1:
            print(f"  AVISO [{origem}]: '{antigo[:50]}...' aparece {n}x (esperado 1). Pulando.")
            continue
        conteudo = conteudo.replace(antigo, novo, 1)
        print(f"  OK [{origem}]: path ajustado ({antigo[:40]} -> 3 niveis)")

    if conteudo != original:
        if dry_run:
            print(f"  DRY-RUN [{origem}]: diff (path)")
            for linha in difflib.unified_diff(
                original.splitlines(), conteudo.splitlines(),
                lineterm="", fromfile=origem, tofile=f"{origem} (fix84)",
            ):
                print(f"    {linha}")
        else:
            p.write_text(conteudo, encoding="utf-8")


def validar_sintaxe(arquivo: Path):
    try:
        compile(arquivo.read_text(encoding="utf-8"), str(arquivo), "exec")
        return True
    except SyntaxError as e:
        print(f"  ABORTADO: sintaxe invalida em {arquivo}: {e}")
        return False


def atualizar_gitignore(dry_run: bool):
    gi = Path(".gitignore")
    if not gi.exists():
        print("AVISO: .gitignore nao existe. Pulando.")
        return

    conteudo = gi.read_text(encoding="utf-8")
    if ".pytest_cache" in conteudo:
        print("OK: .pytest_cache ja no .gitignore")
        return

    if not conteudo.endswith("\n"):
        conteudo += "\n"

    adicao = "\n# Cache pytest\n.pytest_cache/\n"
    novo = conteudo + adicao

    if dry_run:
        print("DRY-RUN: adicionaria '.pytest_cache/' ao .gitignore")
    else:
        gi.write_text(novo, encoding="utf-8")
        print("OK: .pytest_cache adicionado ao .gitignore")


def executar(dry_run: bool):
    if not pre_validar():
        sys.exit(1)

    print()
    print("=" * 60)
    print(" FASE 1: ajustar paths internos")
    print("=" * 60)
    for orig in PATH_FIXES.keys():
        aplicar_path_fix(orig, dry_run)

    print()
    print("=" * 60)
    print(f" FASE 2: mover {len(MOVE)} arquivos")
    print("=" * 60)

    if dry_run:
        for orig, dest in MOVE.items():
            print(f"  [DRY-RUN] git mv {orig} {dest}")
        print()
        print("=" * 60)
        print(" FASE 3: atualizar .gitignore")
        print("=" * 60)
        atualizar_gitignore(dry_run)
        print()
        print("--- DRY-RUN concluido: nada foi salvo ---")
        return

    # Movimento real
    for orig, dest in MOVE.items():
        p_dest = Path(dest)
        p_dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            git_mv(orig, dest)
            print(f"  OK: {orig} -> {dest}")
        except subprocess.CalledProcessError as e:
            print(f"  ERRO git mv {orig}: {e}")
            sys.exit(1)

    # Validar sintaxe de cada arquivo movido
    print()
    print("=" * 60)
    print(" FASE 3: validar sintaxe dos movidos")
    print("=" * 60)
    erros = 0
    for _, dest in MOVE.items():
        if not validar_sintaxe(Path(dest)):
            erros += 1
    if erros > 0:
        print(f"ABORTADO: {erros} arquivo(s) com sintaxe quebrada. Rode --reverter.")
        sys.exit(1)
    print(f"OK: {len(MOVE)} arquivos com sintaxe valida")

    # Gitignore
    print()
    print("=" * 60)
    print(" FASE 4: .gitignore")
    print("=" * 60)
    atualizar_gitignore(dry_run)


def reverter():
    """Reverte git mv + path fixes + gitignore."""
    print("Revertendo...")
    for orig, dest in MOVE.items():
        if Path(dest).exists() and not Path(orig).exists():
            try:
                git_mv(dest, orig)
                print(f"  OK: {dest} -> {orig}")
            except subprocess.CalledProcessError as e:
                print(f"  ERRO reverter {dest}: {e}")

    # Desfaz path fixes
    for orig, fixes in PATH_FIXES.items():
        p = Path(orig)
        if not p.exists():
            continue
        conteudo = p.read_text(encoding="utf-8")
        for antigo, novo in fixes:
            if novo in conteudo:
                conteudo = conteudo.replace(novo, antigo, 1)
        p.write_text(conteudo, encoding="utf-8")
        print(f"  OK: paths revertidos em {orig}")

    # Remove .pytest_cache do gitignore
    gi = Path(".gitignore")
    if gi.exists():
        c = gi.read_text(encoding="utf-8")
        c = c.replace("\n# Cache pytest\n.pytest_cache/\n", "")
        gi.write_text(c, encoding="utf-8")
        print("  OK: .pytest_cache removido do .gitignore")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    print("=" * 60)
    print(" fix84: arquiva utilitarios em ferramentas/")
    print("=" * 60)
    print()

    executar(args.dry_run)

    if not args.dry_run:
        print()
        print("=" * 60)
        print(" OK: fix84 concluido")
        print("=" * 60)
        print()
        print("Proximo passo: git add -A && git commit")


if __name__ == "__main__":
    main()