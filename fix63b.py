# -*- coding: utf-8 -*-
# fix63b.py — Propaga gap_fonte ate o Decisao_V2.json.
#
# PROBLEMA:
#   fix63 marcou gap_fonte no ResultadoPrevisao do NM, mas o campo nao chega
#   ao payload final da decisao. Verificado em 06/10/2026:
#     Decisao_V2.json: metadados.novo_motor.gap_fonte = None
#   Faltam 3 camadas:
#     - PredictionContext (schema) nao tem o campo
#     - prediction_service._criar_contexto_novo_motor nao le do JSON
#     - v2_orchestrator._ler_novo_motor nao propaga
#
# FIX (3 arquivos, 4 patches):
#   1. PredictionContext ganha campo "gap_fonte" (default "DESCONHECIDO")
#   2. prediction_service le gap.fonte (nested) OU gap_fonte (top-level)
#   3. v2_orchestrator._ler_novo_motor propaga prediction.gap_fonte
#   4. v2_orchestrator expoe gap_fonte em precificacao_teorica (visivel direto)
#
# Uso:
#   python fix63b.py --dry-run
#   python fix63b.py
#   python fix63b.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ_CTX = Path("v2/core/contracts/prediction_context.py")
ARQ_SVC = Path("v2/core/services/prediction_service.py")
ARQ_ORQ = Path("v2/core/engines/v2_orchestrator.py")

PATCHES_CTX = [
    {
        "nome": "ctx_gap_fonte",
        "ancora_antiga": (
            '    fonte_abertura: str = "DESCONHECIDA"\n'
            '\n'
            '    # ---- Campos novos: Cenários probabilísticos ----'
        ),
        "ancora_nova": (
            '    fonte_abertura: str = "DESCONHECIDA"\n'
            '    # fix63b: origem do gap — "LEILAO_REAL" | "TEORICA_FALLBACK" | "AJUSTE_FALLBACK"\n'
            '    gap_fonte: str = "DESCONHECIDO"\n'
            '\n'
            '    # ---- Campos novos: Cenários probabilísticos ----'
        ),
    },
]

PATCHES_SVC = [
    {
        "nome": "svc_le_gap_fonte",
        "ancora_antiga": (
            '            gap_pontos=dados.get("gap", {}).get("pontos", 0.0),\n'
            '            gap_percentual=dados.get("gap", {}).get("percentual", 0.0),\n'
            '            gap_intensidade=dados.get("gap", {}).get("intensidade", "N/A"),\n'
            '            classificacao_gap=dados.get("gap", {}).get("classificacao", "N/A"),'
        ),
        "ancora_nova": (
            '            gap_pontos=dados.get("gap", {}).get("pontos", 0.0),\n'
            '            gap_percentual=dados.get("gap", {}).get("percentual", 0.0),\n'
            '            gap_intensidade=dados.get("gap", {}).get("intensidade", "N/A"),\n'
            '            classificacao_gap=dados.get("gap", {}).get("classificacao", "N/A"),\n'
            '            # fix63b: gap_fonte pode vir nested (gap.fonte) ou top-level (gap_fonte)\n'
            '            gap_fonte=(\n'
            '                (dados.get("gap") or {}).get("fonte")\n'
            '                or dados.get("gap_fonte")\n'
            '                or "DESCONHECIDO"\n'
            '            ),'
        ),
    },
]

PATCHES_ORQ = [
    {
        "nome": "orq_propaga_gap_fonte",
        "ancora_antiga": (
            '                "abertura_teorica_calculada": prediction.abertura_teorica_calculada,\n'
            '                "fonte_abertura": prediction.fonte_abertura,'
        ),
        "ancora_nova": (
            '                "abertura_teorica_calculada": prediction.abertura_teorica_calculada,\n'
            '                "fonte_abertura": prediction.fonte_abertura,\n'
            '                "gap_fonte": getattr(prediction, "gap_fonte", "DESCONHECIDO"),'
        ),
    },
    {
        "nome": "orq_precificacao_gap_fonte",
        "ancora_antiga": (
            '                    "precificacao_teorica": {\n'
            '                        "abertura_teorica": (novo_motor or {}).get("abertura_teorica_calculada", 0.0),\n'
            '                    },'
        ),
        "ancora_nova": (
            '                    "precificacao_teorica": {\n'
            '                        "abertura_teorica": (novo_motor or {}).get("abertura_teorica_calculada", 0.0),\n'
            '                        "gap_fonte": (novo_motor or {}).get("gap_fonte", "DESCONHECIDO"),\n'
            '                    },'
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
            print("---")
            print(antiga)
            print("---")
            return False
        if n > 1:
            print(f"ABORTADO [{arquivo.name}]: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(arquivo, patches):
    conteudo = arquivo.read_text(encoding="utf-8")
    for patch in patches:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK [{arquivo.name}]: patch aplicado: {patch['nome']}")
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
    diff = difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    )
    for linha in diff:
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
    for arq in [ARQ_CTX, ARQ_SVC, ARQ_ORQ]:
        backups = sorted(arq.parent.glob(f"{arq.name}.bak_*"))
        if not backups:
            print(f"AVISO: sem backup para {arq.name}")
            continue
        ultimo = backups[-1]
        shutil.copy(ultimo, arq)
        print(f"OK: revertido {arq.name} de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    print("===== fix63b: propaga gap_fonte ate o Decisao_V2.json =====")
    processar(ARQ_CTX, PATCHES_CTX, args.dry_run)
    processar(ARQ_SVC, PATCHES_SVC, args.dry_run)
    processar(ARQ_ORQ, PATCHES_ORQ, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix63b aplicado nos 3 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()