# -*- coding: utf-8 -*-
# fix65.py — Propaga score.detalhes (componentes do score NM) ate o payload final.
#
# CONTEXTO:
#   motor_previsao.py (l.264) JA grava "score.detalhes" no JSON do NM.
#   Mas o campo nao chega ao Decisao_V2.json porque 3 camadas nao o leem:
#     - PredictionContext (schema) nao tem campo score_detalhes
#     - prediction_service nao le do JSON
#     - v2_orchestrator._ler_novo_motor nao propaga
#
# USO:
#   python fix65.py --dry-run
#   python fix65.py
#   python fix65.py --reverter

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
        "nome": "ctx_score_detalhes",
        "ancora_antiga": (
            '    score_magnitude: float = 0.0\n'
            '\n'
            '    # ---- Campos novos: Divergência ----'
        ),
        "ancora_nova": (
            '    score_magnitude: float = 0.0\n'
            '    # fix65: contribuicao individual por componente do score\n'
            '    # (mercado_externo, adrs, vix, tendencia, gap, noticias)\n'
            '    score_detalhes: Dict[str, float] = field(default_factory=dict)\n'
            '\n'
            '    # ---- Campos novos: Divergência ----'
        ),
    },
]

PATCHES_SVC = [
    {
        "nome": "svc_le_score_detalhes",
        "ancora_antiga": (
            '            score=score_obj.get("valor", 0.0),\n'
            '            score_classificacao=score_obj.get("classificacao", "N/A"),'
        ),
        "ancora_nova": (
            '            score=score_obj.get("valor", 0.0),\n'
            '            score_classificacao=score_obj.get("classificacao", "N/A"),\n'
            '            # fix65: contribuicao por componente do score (do JSON do NM)\n'
            '            score_detalhes=score_obj.get("detalhes", {}) or {},'
        ),
    },
]

PATCHES_ORQ = [
    {
        "nome": "orq_propaga_score_detalhes",
        "ancora_antiga": (
            '                "score_direcao": prediction.score_direcao,\n'
            '                "score_forca": prediction.score_forca,\n'
            '                "score_magnitude": float(prediction.score_magnitude or 0.0),'
        ),
        "ancora_nova": (
            '                "score_direcao": prediction.score_direcao,\n'
            '                "score_forca": prediction.score_forca,\n'
            '                "score_magnitude": float(prediction.score_magnitude or 0.0),\n'
            '                "score_detalhes": getattr(prediction, "score_detalhes", {}) or {},'
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

    print("===== fix65: propaga score_detalhes ate o Decisao_V2.json =====")
    processar(ARQ_CTX, PATCHES_CTX, args.dry_run)
    processar(ARQ_SVC, PATCHES_SVC, args.dry_run)
    processar(ARQ_ORQ, PATCHES_ORQ, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix65 aplicado nos 3 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()