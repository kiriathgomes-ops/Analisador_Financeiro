#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_fase2a.py — Limpeza Fase 2A (lixo claro + orfaos)
===========================================================

Move arquivos sem uso detectado para lixeira_analise/DATA/cleanup_fase2a/.
Antes de mover, faz busca defensiva: se o arquivo for mencionado em qualquer
outro .py, .bat ou .ps1 do projeto, PULA (avisa o usuario).

Arquivos candidatos (Fase 2A):
  - dump_essencial.md       (1.3 MB — output regeneravel)
  - dump_project.py         (gerador de dump)
  - dump_projeto.py         (gerador de dump)
  - dump_v2.py              (gerador de dump)
  - Gerar_App_Completo.py   (dump monolítico)
  - Gerar_ColetasArquivosApp.py
  - Gerar_Mapa_Arquivos_OK.py
  - monitor_preco_teorico.py
  - win_abertura_pro.py

Uso:
    python cleanup_fase2a.py                 # dry-run
    python cleanup_fase2a.py --execute       # aplica
    python cleanup_fase2a.py --reverter      # restaura do manifest
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
PASTA_LIXEIRA = BASE_DIR / "lixeira_analise" / HOJE / "cleanup_fase2a"
MANIFEST = PASTA_LIXEIRA / "_manifest.json"


CANDIDATOS = [
    "dump_essencial.md",
    "dump_project.py",
    "dump_projeto.py",
    "dump_v2.py",
    "Gerar_App_Completo.py",
    "Gerar_ColetasArquivosApp.py",
    "Gerar_Mapa_Arquivos_OK.py",
    "monitor_preco_teorico.py",
    "win_abertura_pro.py",
]


# ============================================================
# HELPERS
# ============================================================
def _tamanho_legivel(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.1f} MB"


def _git_tracked() -> set:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(BASE_DIR), check=True,
        )
        return set(result.stdout.splitlines())
    except Exception:
        return set()


def _tem_mencoes(nome_arquivo: str) -> list:
    """Busca mencoes ao arquivo em outros .py/.bat/.ps1 do projeto."""
    stem = Path(nome_arquivo).stem
    # Regex simples: buscar por stem do arquivo (sem extensão)
    mencoes = []
    for ext in ("*.py", "*.bat", "*.ps1"):
        for arq in BASE_DIR.rglob(ext):
            if arq.name == nome_arquivo:
                continue  # ignora o proprio arquivo
            if "lixeira_analise" in str(arq):
                continue
            try:
                conteudo = arq.read_text(encoding="utf-8", errors="replace")
                if stem in conteudo:
                    mencoes.append(arq.relative_to(BASE_DIR).as_posix())
            except Exception:
                continue
    return mencoes


def _resolver_conflito(destino: Path) -> Path:
    if not destino.exists():
        return destino
    i = 2
    while True:
        novo = destino.with_name(f"{destino.stem}_v{i}{destino.suffix}")
        if not novo.exists():
            return novo
        i += 1


# ============================================================
# REVERTER
# ============================================================
def reverter() -> int:
    if not MANIFEST.exists():
        candidatos = sorted(
            (BASE_DIR / "lixeira_analise").glob("*/cleanup_fase2a/_manifest.json"),
            reverse=True,
        )
        if not candidatos:
            print("[ERRO] Nenhum manifest encontrado.")
            return 1
        manifest_path = candidatos[0]
    else:
        manifest_path = MANIFEST

    print(f"[INFO] Lendo manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    arquivos = manifest.get("arquivos", [])
    restaurados = 0
    for item in arquivos:
        origem = Path(item["origem"])
        destino = Path(item["destino"])
        if not destino.exists():
            print(f"   [SKIP] Nao existe mais: {destino.name}")
            continue
        try:
            origem.parent.mkdir(parents=True, exist_ok=True)
            if origem.exists():
                origem = _resolver_conflito(origem)
            shutil.move(str(destino), str(origem))
            print(f"   [OK] {destino.name} restaurado")
            restaurados += 1
        except Exception as e:
            print(f"   [ERRO] {destino.name}: {e}")

    print(f"\n[OK] Restaurados: {restaurados}")
    return 0


# ============================================================
# APLICAR
# ============================================================
def aplicar(execute: bool = False) -> int:
    print("=" * 60)
    print(" cleanup_fase2a — Limpeza conservadora com busca defensiva")
    print("=" * 60)
    print(f" Base      : {BASE_DIR}")
    print(f" Lixeira   : {PASTA_LIXEIRA}")
    print(f" Modo      : {'EXECUTE' if execute else 'DRY-RUN'}")
    print()

    tracked = _git_tracked()
    print(f"[INFO] {len(tracked)} arquivos tracked no git")
    print()

    movidos = []
    pulados_mencoes = []
    pulados_inexistentes = []
    pulados_tracked = []
    total_bytes = 0

    for nome in CANDIDATOS:
        arq = BASE_DIR / nome

        if not arq.exists():
            pulados_inexistentes.append(nome)
            continue

        # Busca mencoes em outros arquivos
        mencoes = _tem_mencoes(nome)
        if mencoes:
            print(f"[PULA-MENCOES] {nome}")
            for m in mencoes[:3]:
                print(f"   mencionado em: {m}")
            if len(mencoes) > 3:
                print(f"   ... e mais {len(mencoes) - 3}")
            pulados_mencoes.append((nome, mencoes))
            print()
            continue

        is_tracked = nome in tracked
        if is_tracked:
            print(f"[PULA-TRACKED] {nome} (versionado no git)")
            pulados_tracked.append(nome)
            print()
            continue

        tamanho = arq.stat().st_size
        total_bytes += tamanho

        if execute:
            destino_pasta = PASTA_LIXEIRA
            destino_pasta.mkdir(parents=True, exist_ok=True)
            destino = destino_pasta / nome
            destino = _resolver_conflito(destino)
            try:
                shutil.move(str(arq), str(destino))
                movidos.append((arq, destino))
                print(f"[OK] {nome} ({_tamanho_legivel(tamanho)})")
            except Exception as e:
                print(f"[ERRO] {nome}: {e}")
        else:
            print(f"[MOVERIA] {nome} ({_tamanho_legivel(tamanho)})")

    # Relatorio
    print()
    print("=" * 60)
    print(" RELATORIO")
    print("=" * 60)
    print(f"  Movidos      : {len(movidos)}")
    print(f"  Pulados (mencoes)    : {len(pulados_mencoes)}")
    print(f"  Pulados (tracked)    : {len(pulados_tracked)}")
    print(f"  Pulados (inexistentes): {len(pulados_inexistentes)}")
    print(f"  Tamanho total        : {_tamanho_legivel(total_bytes)}")

    if pulados_mencoes:
        print()
        print("  Arquivos com mencoes (revisar antes de mover):")
        for nome, mencoes in pulados_mencoes:
            print(f"    - {nome}")
            for m in mencoes[:2]:
                print(f"        mencionado em: {m}")

    if pulados_tracked:
        print()
        print("  Tracked no git (mover com --include-tracked):")
        for nome in pulados_tracked:
            print(f"    - {nome}")

    if pulados_inexistentes:
        print()
        print("  Nao existem mais (ja limpos):")
        for nome in pulados_inexistentes:
            print(f"    - {nome}")

    # Manifest + gitignore
    if execute and movidos:
        PASTA_LIXEIRA.mkdir(parents=True, exist_ok=True)
        manifest = {
            "data_limpeza": datetime.now().isoformat(),
            "versao_script": "cleanup_fase2a.py",
            "arquivos": [
                {"origem": str(o), "destino": str(d)} for o, d in movidos
            ],
        }
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print()
        print(f"  [OK] Manifest: {MANIFEST}")
        print(f"       Reverter: python cleanup_fase2a.py --reverter")
    elif not execute:
        print()
        print("  [DRY-RUN] Nada foi movido. Rode com --execute pra aplicar.")

    print("=" * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        return reverter()
    return aplicar(execute=args.execute)


if __name__ == "__main__":
    sys.exit(main())