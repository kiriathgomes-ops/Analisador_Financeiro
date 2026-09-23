#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_fase2b.py — Limpeza Fase 2A com ignore-list correto
============================================================

Versao corrigida: ignora mencoes em arquivos auto-gerados / scripts de cleanup
/ outros arquivos da mesma lista de candidatos (eles vao embora juntos).

Uso:
    python cleanup_fase2b.py
    python cleanup_fase2b.py --execute
    python cleanup_fase2b.py --reverter
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
PASTA_LIXEIRA = BASE_DIR / "lixeira_analise" / HOJE / "cleanup_fase2b"
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


# Arquivos/pastas a IGNORAR na busca por mencoes (evita falsos positivos)
IGNORAR_EM_BUSCA = [
    "lixeira_analise/",
    "Coletas/",              # inventarios auto-gerados
    "cleanup_fase",          # scripts de cleanup em si
    "dump_project.py",       # dumps mencionam outros dumps
    "dump_projeto.py",
    "dump_v2.py",
    "Gerar_App_Completo.py",
    "Gerar_Mapa_Arquivos_OK.py",
    "Gerar_ColetasArquivosApp.py",
]


def _tamanho_legivel(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.1f} MB"


def _git_tracked() -> set:
    try:
        r = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(BASE_DIR), check=True,
        )
        return set(r.stdout.splitlines())
    except Exception:
        return set()


def _deve_ignorar_na_busca(caminho_rel: str) -> bool:
    """Retorna True se o arquivo deve ser ignorado na busca por mencoes."""
    cr = caminho_rel.replace("\\", "/")
    for ignore in IGNORAR_EM_BUSCA:
        if ignore in cr:
            return True
    return False


def _tem_mencoes_reais(nome_arquivo: str) -> list:
    """
    Busca mencoes ao arquivo em .py/.bat/.ps1, ignorando:
      - o proprio arquivo
      - arquivos auto-gerados (Coletas/ArquivosApp.py)
      - scripts de cleanup
      - outros arquivos da lista de candidatos
    """
    stem = Path(nome_arquivo).stem
    mencoes = []
    for ext in ("*.py", "*.bat", "*.ps1"):
        for arq in BASE_DIR.rglob(ext):
            rel = arq.relative_to(BASE_DIR).as_posix()

            # Ignorar o proprio arquivo
            if arq.name == nome_arquivo:
                continue
            # Ignorar arquivos/pastas da ignore-list
            if _deve_ignorar_na_busca(rel):
                continue

            try:
                conteudo = arq.read_text(encoding="utf-8", errors="replace")
                if stem in conteudo:
                    mencoes.append(rel)
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


def reverter() -> int:
    if not MANIFEST.exists():
        candidatos = sorted(
            (BASE_DIR / "lixeira_analise").glob("*/cleanup_fase2b/_manifest.json"),
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

    for item in manifest.get("arquivos", []):
        origem = Path(item["origem"])
        destino = Path(item["destino"])
        if not destino.exists():
            print(f"   [SKIP] {destino.name} (nao existe mais)")
            continue
        try:
            origem.parent.mkdir(parents=True, exist_ok=True)
            if origem.exists():
                origem = _resolver_conflito(origem)
            shutil.move(str(destino), str(origem))
            print(f"   [OK] {destino.name} restaurado")
        except Exception as e:
            print(f"   [ERRO] {destino.name}: {e}")
    return 0


def aplicar(execute: bool = False) -> int:
    print("=" * 60)
    print(" cleanup_fase2b — Limpeza conservadora (ignore-list)")
    print("=" * 60)
    print(f" Base    : {BASE_DIR}")
    print(f" Lixeira : {PASTA_LIXEIRA}")
    print(f" Modo    : {'EXECUTE' if execute else 'DRY-RUN'}")
    print()

    tracked = _git_tracked()
    print(f"[INFO] {len(tracked)} arquivos tracked no git")
    print()

    movidos = []
    pulados = []
    inexistentes = []
    total_bytes = 0

    for nome in CANDIDATOS:
        arq = BASE_DIR / nome
        if not arq.exists():
            inexistentes.append(nome)
            continue

        mencoes = _tem_mencoes_reais(nome)
        if mencoes:
            print(f"[PULA] {nome}")
            for m in mencoes[:3]:
                print(f"   mencionado em: {m}")
            pulados.append((nome, mencoes))
            print()
            continue

        is_tracked = nome in tracked
        tag = " [tracked]" if is_tracked else ""
        tamanho = arq.stat().st_size
        total_bytes += tamanho

        if execute:
            PASTA_LIXEIRA.mkdir(parents=True, exist_ok=True)
            destino = PASTA_LIXEIRA / nome
            destino = _resolver_conflito(destino)
            try:
                shutil.move(str(arq), str(destino))
                movidos.append((arq, destino))
                print(f"[OK] {nome} ({_tamanho_legivel(tamanho)}){tag}")
            except Exception as e:
                print(f"[ERRO] {nome}: {e}")
        else:
            print(f"[MOVERIA] {nome} ({_tamanho_legivel(tamanho)}){tag}")

    print()
    print("=" * 60)
    print(" RELATORIO")
    print("=" * 60)
    print(f"  Movidos               : {len(movidos)}")
    print(f"  Pulados (mencoes reais): {len(pulados)}")
    print(f"  Inexistentes          : {len(inexistentes)}")
    print(f"  Tamanho total         : {_tamanho_legivel(total_bytes)}")

    if pulados:
        print()
        print("  Arquivos com mencoes reais:")
        for nome, mencoes in pulados:
            print(f"    - {nome}: {mencoes[:2]}")

    if inexistentes:
        print()
        print("  Ja nao existem:")
        for nome in inexistentes:
            print(f"    - {nome}")

    if execute and movidos:
        PASTA_LIXEIRA.mkdir(parents=True, exist_ok=True)
        manifest = {
            "data_limpeza": datetime.now().isoformat(),
            "versao_script": "cleanup_fase2b.py",
            "arquivos": [{"origem": str(o), "destino": str(d)} for o, d in movidos],
        }
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print()
        print(f"  [OK] Manifest: {MANIFEST}")
        print(f"       Reverter: python cleanup_fase2b.py --reverter")
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