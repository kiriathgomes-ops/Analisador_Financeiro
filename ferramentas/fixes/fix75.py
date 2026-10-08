# -*- coding: utf-8 -*-
# fix75.py — Unifica nomenclatura: score_magnitude/score_direcao sao canonicos.
#
# CONTEXTO:
#   `score_magnitude`/`score_direcao` (novo_motor) e
#   `nm_magnitude`/`nm_direcao_score` (confluencia) apontam pro mesmo dado.
#   nm_magnitude/nm_direcao_score sao ORFAOS (so no debug, nunca lidos).
#
# PLANO:
#   1. Adiciona score_magnitude/score_direcao no _debug_confluencia (canonicos)
#   2. MANTEM nm_* como aliases deprecated (retrocompat backtest)
#   3. audit_camada2.py passa a auditar tambem os canonicos
#
# Uso:
#   python fix75.py --dry-run
#   python fix75.py
#   python fix75.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ_ORQ = Path("v2/core/engines/v2_orchestrator.py")
ARQ_AUD = Path("audit_camada2.py")

PATCHES_ORQ = [
    {
        "nome": "orq_debug_score_canonico_inicializa",
        "ancora_antiga": (
            '            "nm_magnitude": None,\n'
            '            "nm_direcao_score": None,\n'
            '            "nm_divergencia_interna": None,'
        ),
        "ancora_nova": (
            '            "nm_magnitude": None,\n'
            '            "nm_direcao_score": None,\n'
            '            "nm_divergencia_interna": None,\n'
            '            # fix75: nomes canonicos (mesmo valor, nomenclatura unificada)\n'
            '            "score_magnitude": None,\n'
            '            "score_direcao": None,'
        ),
    },
    {
        "nome": "orq_debug_score_canonico_preenche",
        "ancora_antiga": (
            '        self._debug_confluencia["nm_magnitude"] = float(nm_conf)\n'
            '        self._debug_confluencia["nm_direcao_score"] = nm_score_dir'
        ),
        "ancora_nova": (
            '        self._debug_confluencia["nm_magnitude"] = float(nm_conf)\n'
            '        self._debug_confluencia["nm_direcao_score"] = nm_score_dir\n'
            '        # fix75: aliases canonicos (mesmo valor, nome unificado)\n'
            '        self._debug_confluencia["score_magnitude"] = float(nm_conf)\n'
            '        self._debug_confluencia["score_direcao"] = nm_score_dir'
        ),
    },
]

PATCHES_AUD = [
    {
        "nome": "audit_lista_canonicos",
        "ancora_antiga": (
            '        for k in ["smc_conf_bruto", "mtf_veredito", "mtf_delta",\n'
            '                  "smc_conf_ajustado", "nm_conf", "peso_smc", "peso_nm",\n'
            '                  "confianca_final", "passou_gate_confluencia",\n'
            '                  "passou_gate_final"]:'
        ),
        "ancora_nova": (
            '        for k in ["smc_conf_bruto", "mtf_veredito", "mtf_delta",\n'
            '                  "smc_conf_ajustado", "nm_conf", "peso_smc", "peso_nm",\n'
            '                  "score_magnitude", "score_direcao",  # fix75: canonicos\n'
            '                  "confianca_final", "passou_gate_confluencia",\n'
            '                  "passou_gate_final"]:'
        ),
    },
]


def pre_validar(arquivo, patches):
    if not arquivo.exists():
        print(f"ABORTADO: {arquivo} nao encontrado")
        return False
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        antiga = patch["ancora_antiga"]
        n = conteudo.count(antiga)
        if n == 0:
            print(f"ABORTADO [{arquivo.name}]: ancora nao encontrada: {patch['nome']}")
            print("---"); print(antiga); print("---")
            return False
        if n > 1:
            print(f"ABORTADO [{arquivo.name}]: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(arquivo, patches):
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK [{arquivo.name}]: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo, nome):
    try:
        compile(conteudo, nome, "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida em {nome}: {e}")
        return False
    print(f"OK [{nome}]: sintaxe validada")
    return True


def mostrar_diff(antes, depois, nome):
    print(f"\n--- DRY-RUN: diff {nome} ---")
    for linha in difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ):
        print(linha)
    print(f"--- DRY-RUN {nome}: nada foi salvo ---")


def processar(arquivo, patches, dry_run):
    if not pre_validar(arquivo, patches):
        sys.exit(1)
    antes = arquivo.read_text(encoding="utf-8")
    depois = aplicar(arquivo, patches)
    if not validar_sintaxe(depois, arquivo.name):
        sys.exit(1)
    if dry_run:
        mostrar_diff(antes, depois, arquivo.name)
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = arquivo.parent / f"{arquivo.name}.bak_{ts}"
    shutil.copy(arquivo, backup)
    arquivo.write_text(depois, encoding="utf-8")
    print(f"OK [{arquivo.name}]: backup={backup.name}")


def reverter():
    for arq in [ARQ_ORQ, ARQ_AUD]:
        backups = sorted(arq.parent.glob(f"{arq.name}.bak_*"))
        if not backups:
            print(f"AVISO: sem backup para {arq.name}")
            continue
        ultimo = backups[-1]
        shutil.copy(ultimo, arq)
        print(f"OK: revertido {arq.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    print("===== fix75: unifica nomenclatura score_magnitude/score_direcao =====")
    processar(ARQ_ORQ, PATCHES_ORQ, args.dry_run)
    processar(ARQ_AUD, PATCHES_AUD, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix75 aplicado nos 2 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()