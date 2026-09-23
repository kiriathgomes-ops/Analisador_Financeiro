#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_fase1.py — Limpeza conservadora da raiz do projeto
=============================================================

Move arquivos descartaveis para lixeira_analise/DATA/cleanup_fase1/
Nunca deleta — sempre move (100% reversivel).

Categorias cobertas (Fase 1):
  - fix_scripts/       : fix*.py (scripts de patch one-shot)
  - debug_tests/       : _debug_*.py, _teste_*.py
  - analises_one_shot/ : analisar_historico*.py, analisar_divergencia.py
  - dumps/             : *.bak_*, *.bak_mss, dump_v2.txt, consolidado_projeto.txt

Uso:
    python cleanup_fase1.py                        # dry-run (padrao, NAO move)
    python cleanup_fase1.py --execute              # move (so arquivos untracked)
    python cleanup_fase1.py --execute --include-tracked  # move tambem tracked
    python cleanup_fase1.py --reverter             # restaura do manifest

Seguranca:
  - Arquivos tracked no git sao PULADOS por padrao (avisa)
  - Se o arquivo ja existe no destino, renomeia com _v2, _v3...
  - Grava _manifest.json pra permitir reverter
  - Mostra tamanho total movido
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(".").resolve()
HOJE = datetime.now().strftime("%Y-%m-%d")
PASTA_LIXEIRA = BASE_DIR / "lixeira_analise" / HOJE / "cleanup_fase1"
MANIFEST_PATH = PASTA_LIXEIRA / "_manifest.json"


CATEGORIAS = {
    "fix_scripts": ["fix*.py"],
    "debug_tests": ["_debug_*.py", "_teste_*.py"],
    "analises_one_shot": [
        "analisar_historico.py",
        "analisar_historico_v2.py",
        "analisar_divergencia.py",
    ],
    "dumps": [
        "*.bak_*",
        "*.bak_mss",
        "dump_v2.txt",
        "consolidado_projeto.txt",
    ],
}


# ============================================================
# HELPERS
# ============================================================
def _git_tracked() -> set:
    """Retorna set com nomes de arquivos tracked pelo git (relativos a BASE_DIR)."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(BASE_DIR),
            check=True,
        )
        return set(result.stdout.splitlines())
    except Exception as e:
        print(f"[AVISO] Falha ao listar git tracked: {e}")
        return set()


def _tamanho_legivel(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / (1024 * 1024):.1f} MB"


def _coletar_candidatos() -> dict:
    """Retorna {categoria: [(Path, categoria_destino), ...]}."""
    resultado = {}
    for cat, padroes in CATEGORIAS.items():
        arquivos = []
        for padrao in padroes:
            for path in BASE_DIR.glob(padrao):
                if path.is_file():
                    arquivos.append(path)
        # Deduplica (arquivo pode casar em 2 padroes)
        resultado[cat] = sorted(set(arquivos))
    return resultado


def _resolver_conflito(destino: Path) -> Path:
    """Se destino existe, retorna destino_v2, _v3, etc."""
    if not destino.exists():
        return destino
    stem = destino.stem
    suffix = destino.suffix
    i = 2
    while True:
        novo = destino.with_name(f"{stem}_v{i}{suffix}")
        if not novo.exists():
            return novo
        i += 1


def _salvar_manifest(movidos: list, lixeira: Path) -> None:
    manifest = {
        "data_limpeza": datetime.now().isoformat(),
        "versao_script": "cleanup_fase1.py",
        "lixeira": str(lixeira),
        "arquivos": [
            {"origem": str(o), "destino": str(d)} for o, d in movidos
        ],
    }
    lixeira.mkdir(parents=True, exist_ok=True)
    with open(lixeira / "_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


# ============================================================
# REVERTER
# ============================================================
def reverter() -> int:
    # Procura manifest mais recente
    if not MANIFEST_PATH.exists():
        # Busca em pastas anteriores
        candidatos = sorted(
            (BASE_DIR / "lixeira_analise").glob("*/cleanup_fase1/_manifest.json"),
            reverse=True,
        )
        if not candidatos:
            print("[ERRO] Nenhum manifest encontrado em lixeira_analise/*/cleanup_fase1/")
            return 1
        manifest_path = candidatos[0]
    else:
        manifest_path = MANIFEST_PATH

    print(f"[INFO] Lendo manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    arquivos = manifest.get("arquivos", [])
    if not arquivos:
        print("[AVISO] Manifest vazio. Nada a reverter.")
        return 1

    print(f"[INFO] {len(arquivos)} arquivos para restaurar")
    restaurados = 0
    erros = 0

    for item in arquivos:
        origem_original = Path(item["origem"])
        destino_atual = Path(item["destino"])

        if not destino_atual.exists():
            print(f"   [SKIP] Nao existe mais: {destino_atual.name}")
            continue

        try:
            # Garante que a pasta pai existe
            origem_original.parent.mkdir(parents=True, exist_ok=True)
            # Se já existe algo na origem, renomeia
            if origem_original.exists():
                origem_original = _resolver_conflito(origem_original)
            shutil.move(str(destino_atual), str(origem_original))
            restaurados += 1
        except Exception as e:
            print(f"   [ERRO] {destino_atual.name}: {e}")
            erros += 1

    print(f"\n[OK] Restaurados: {restaurados} | Erros: {erros}")
    print(f"[INFO] Os arquivos voltaram pra raiz do projeto.")
    return 0


# ============================================================
# APLICAR
# ============================================================
def aplicar(execute: bool = False, include_tracked: bool = False) -> int:
    print("=" * 60)
    print(" cleanup_fase1 — Move arquivos descartaveis pra lixeira")
    print("=" * 60)
    print(f" Base      : {BASE_DIR}")
    print(f" Lixeira   : {PASTA_LIXEIRA}")
    print(f" Modo      : {'EXECUTE (vai mover)' if execute else 'DRY-RUN (nao move)'}")
    print(f" Tracked   : {'INCLUI' if include_tracked else 'PULA (default)'}")
    print()

    # Coleta tracked
    tracked = _git_tracked()
    if tracked:
        print(f"[INFO] {len(tracked)} arquivos tracked no git")
    else:
        print("[AVISO] git nao respondeu. Assumindo que nada e tracked.")
    print()

    # Coleta candidatos
    candidatos = _coletar_candidatos()

    # Processa
    movidos = []  # [(origem, destino), ...]
    pulados_tracked = []
    total_bytes = 0
    erros = []

    for cat, arquivos in candidatos.items():
        if not arquivos:
            continue

        print(f">> {cat} ({len(arquivos)} arquivo(s))")
        for arq in arquivos:
            rel = arq.name
            is_tracked = rel in tracked or str(arq.relative_to(BASE_DIR)) in tracked

            if is_tracked and not include_tracked:
                print(f"   [PULA-TRACKED] {rel}")
                pulados_tracked.append(arq)
                continue

            tamanho = arq.stat().st_size
            total_bytes += tamanho

            if execute:
                destino_pasta = PASTA_LIXEIRA / cat
                destino_pasta.mkdir(parents=True, exist_ok=True)
                destino = destino_pasta / arq.name
                destino = _resolver_conflito(destino)

                try:
                    shutil.move(str(arq), str(destino))
                    movidos.append((arq, destino))
                    print(f"   [OK] {rel} ({_tamanho_legivel(tamanho)}) -> {cat}/")
                except Exception as e:
                    erros.append((arq, str(e)))
                    print(f"   [ERRO] {rel}: {e}")
            else:
                acao = "MOVERIA" if not is_tracked else "MOVERIA-TRACKED"
                print(f"   [{acao}] {rel} ({_tamanho_legivel(tamanho)}) -> {cat}/")
                movidos.append((arq, PASTA_LIXEIRA / cat / arq.name))

        print()

    # Relatorio
    print("=" * 60)
    print(" RELATORIO")
    print("=" * 60)
    print(f"  Arquivos processados : {len(movidos)}")
    print(f"  Pulados (tracked)    : {len(pulados_tracked)}")
    print(f"  Erros                : {len(erros)}")
    print(f"  Tamanho total        : {_tamanho_legivel(total_bytes)}")

    if pulados_tracked:
        print()
        print("  Arquivos tracked pulados (use --include-tracked pra mover):")
        for arq in pulados_tracked[:10]:
            print(f"    - {arq.name}")
        if len(pulados_tracked) > 10:
            print(f"    ... e mais {len(pulados_tracked) - 10}")

    if erros:
        print()
        print("  Erros detalhados:")
        for arq, msg in erros:
            print(f"    - {arq.name}: {msg}")

    # Grava manifest se executou
    if execute and movidos:
        PASTA_LIXEIRA.mkdir(parents=True, exist_ok=True)
        _salvar_manifest(movidos, PASTA_LIXEIRA)
        print()
        print(f"  [OK] Manifest salvo: {MANIFEST_PATH}")
        print(f"       Reverter: python cleanup_fase1.py --reverter")
    elif not execute:
        print()
        print("  [DRY-RUN] Nada foi movido. Rode com --execute pra aplicar.")

    # Adiciona lixeira ao .gitignore (uma vez)
    if execute:
        gitignore = BASE_DIR / ".gitignore"
        try:
            conteudo = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
            if "lixeira_analise/" not in conteudo:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n# Pasta de limpeza local\nlixeira_analise/\n")
                print(f"  [OK] '.gitignore' atualizado (lixeira_analise/)")
        except Exception as e:
            print(f"  [AVISO] Falha ao atualizar .gitignore: {e}")

    print("=" * 60)
    return 0


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Limpeza Fase 1: move arquivos descartaveis pra lixeira_analise/"
    )
    parser.add_argument("--execute", action="store_true",
                        help="Aplica de verdade (default: dry-run)")
    parser.add_argument("--include-tracked", action="store_true",
                        help="Move tambem arquivos versionados no git")
    parser.add_argument("--reverter", action="store_true",
                        help="Restaura tudo do ultimo manifest")

    args = parser.parse_args()

    if args.reverter:
        return reverter()
    return aplicar(execute=args.execute, include_tracked=args.include_tracked)


if __name__ == "__main__":
    sys.exit(main())