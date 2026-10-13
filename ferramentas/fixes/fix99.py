# -*- coding: utf-8 -*-
"""
fix99 — Limpeza de constantes mortas no config.py

Remove 12 constantes sem uso confirmado (0 referências no código):
  - FILE_PIPELINE_LOG, FILE_TOKEN_USAGE    (arquivos nunca criados)
  - FILE_SMC_M1, FILE_SMC_M15              (lidos via hardcode na page 7.1)
  - BASE_DIR_STR, COLETAS_DIR_STR          (aliases legados órfãos)
  - FILE_UNIFICADO_STR, FILE_RAM_STR, FILE_ROM0_STR, FILE_MT5_V2_STR, FILE_DECISAO_V2_STR

Uso:
    python ferramentas/fixes/fix99.py              # dry-run
    python ferramentas/fixes/fix99.py --aplicar    # aplica
    python ferramentas/fixes/fix99.py --reverter   # restaura último backup
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ARQUIVO = BASE_DIR / "config.py"
BACKUP_DIR = BASE_DIR / "ferramentas" / "fixes" / "backups"


# ==============================================================================
# PATCHES — pares (de, para) aplicados em ordem
# ==============================================================================
PATCHES = [
    # ---- Patch 1A: remove bloco "Pipeline / logs" ----
    (
        "# Pipeline / logs\n"
        'FILE_PIPELINE_LOG = COLETAS_DIR / "Pipeline_Log.json"\n'
        'FILE_TOKEN_USAGE = COLETAS_DIR / "token_usage.log"\n'
        "\n",
        "",
    ),
    # ---- Patch 1B: remove FILE_SMC_M1/M15 (mantém SMC_REGRAS/MTF) ----
    (
        'FILE_SMC_M1 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json"\n'
        'FILE_SMC_M15 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json"\n',
        "",
    ),
    # ---- Patch 2: remove bloco inteiro de "Aliases string" ----
    (
        "\n"
        "# Aliases string (módulos legados que ainda usam os.path)\n"
        "BASE_DIR_STR = str(BASE_DIR)\n"
        "COLETAS_DIR_STR = str(COLETAS_DIR)\n"
        "FILE_UNIFICADO_STR = str(FILE_UNIFICADO)\n"
        "FILE_RAM_STR = str(FILE_RAM)\n"
        "FILE_ROM0_STR = str(FILE_ROM0)\n"
        "FILE_MT5_V2_STR = str(FILE_MT5_V2)\n"
        "FILE_DECISAO_V2_STR = str(FILE_DECISAO_V2)\n",
        "",
    ),
]


# ==============================================================================
# HELPERS
# ==============================================================================
def _backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUP_DIR / f"config_py_pre_fix99_{ts}.bak"
    shutil.copy2(ARQUIVO, destino)
    return destino


def _reverter():
    backups = sorted(BACKUP_DIR.glob("config_py_pre_fix99_*.bak"))
    if not backups:
        print("❌ Nenhum backup encontrado em", BACKUP_DIR)
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy2(ultimo, ARQUIVO)
    print(f"✅ Revertido a partir de {ultimo.name}")


def _aplicar_patches(conteudo: str, dry_run: bool) -> tuple[str, list[dict]]:
    relatorio = []
    atual = conteudo

    for idx, (de, para) in enumerate(PATCHES, start=1):
        if de not in atual:
            relatorio.append({
                "patch": idx,
                "status": "❌ NÃO ENCONTRADO",
                "linhas_removidas": 0,
            })
            continue

        ocorrencias = atual.count(de)
        if ocorrencias > 1:
            relatorio.append({
                "patch": idx,
                "status": f"⚠️ {ocorrencias} ocorrências — ambíguo",
                "linhas_removidas": 0,
            })
            continue

        linhas_rem = de.count("\n")
        if not dry_run:
            atual = atual.replace(de, para, 1)
        relatorio.append({
            "patch": idx,
            "status": "✅ aplicado" if not dry_run else "🟡 aplicaria",
            "linhas_removidas": linhas_rem,
        })

    return atual, relatorio


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="fix99 — limpa constantes mortas em config.py")
    parser.add_argument("--aplicar", action="store_true", help="aplica de verdade")
    parser.add_argument("--reverter", action="store_true", help="restaura último backup")
    args = parser.parse_args()

    if args.reverter:
        _reverter()
        return

    if not ARQUIVO.exists():
        print(f"❌ {ARQUIVO} não encontrado")
        sys.exit(1)

    conteudo_original = ARQUIVO.read_text(encoding="utf-8")
    linhas_antes = len(conteudo_original.splitlines())

    dry_run = not args.aplicar
    modo = "🔴 APLICANDO" if args.aplicar else "🟡 DRY-RUN"

    print("=" * 70)
    print(f" fix99 — LIMPEZA DE CONSTANTES MORTAS — {modo}")
    print("=" * 70)
    print(f" Arquivo: {ARQUIVO.relative_to(BASE_DIR)}")
    print(f" Linhas antes: {linhas_antes}")
    print()

    # Backup
    backup_path = None
    if not dry_run:
        backup_path = _backup()
        print(f" 📦 Backup: {backup_path.relative_to(BASE_DIR)}")
        print()

    # Aplica patches
    conteudo_novo, relatorio = _aplicar_patches(conteudo_original, dry_run)

    # Relatório
    print(f"{'PATCH':<8} {'STATUS':<25} {'LINHAS REMOVIDAS':>18}")
    print("-" * 70)
    total_removidas = 0
    for r in relatorio:
        print(f"#{r['patch']:<7} {r['status']:<25} {r['linhas_removidas']:>18}")
        total_removidas += r["linhas_removidas"]

    linhas_depois = len(conteudo_novo.splitlines())
    print()
    print("=" * 70)
    print(f" Total linhas removidas: {total_removidas}")
    print(f" Linhas antes:  {linhas_antes}")
    print(f" Linhas depois: {linhas_depois} ({linhas_antes - linhas_depois} removidas)")
    print("=" * 70)

    # Aplica no disco
    if not dry_run:
        ARQUIVO.write_text(conteudo_novo, encoding="utf-8")
        print()
        print(f" ✅ Arquivo salvo: {ARQUIVO.relative_to(BASE_DIR)}")
        print(f" 💡 Para reverter: python ferramentas/fixes/fix99.py --reverter")
    else:
        print()
        print(" 💡 Para aplicar de verdade:")
        print("    python ferramentas/fixes/fix99.py --aplicar")


if __name__ == "__main__":
    main()