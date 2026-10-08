# -*- coding: utf-8 -*-
# fix76.py — Propaga "fonte" e "timestamp_coleta" no DadosAtivosUnificados.json.
#
# BUG (Coletor.py:819-841):
#   A funcao gerar_arquivo_unificado() monta ativos_map[nome] com 4 campos
#   (preco, variacao_pct, ticker_original, status), mas PERDE o campo "fonte"
#   do item original.
#
#   Resultado: DadosAtivosUnificados.json nao tem rastreabilidade de origem
#   (0/33 ativos com fonte). Os consumidores V2 (v2_orchestrator, pages,
#   NOVO_MOTOR/coletor_dados) leem esse arquivo e nao sabem de onde veio cada
#   ativo.
#
#   Nota: Dados_Validados.json (saida do Validador) JA preserva fonte
#   (33/33 ativos). O bug esta so no unificado.
#
# FIX:
#   1. Adiciona "fonte" no ativos_map (com fallback "DESCONHECIDA")
#   2. Adiciona "timestamp_coleta" (complementa rastreabilidade)
#
# Uso:
#   python fix76.py --dry-run
#   python fix76.py
#   python fix76.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("Coletor.py")

PATCHES = [
    {
        "nome": "unificado_propaga_fonte",
        "ancora_antiga": (
            '        ativos_map[nome] = {\n'
            '            "preco": float(dados.get("close") or 0.0),\n'
            '            "variacao_pct": float(dados.get("change_percent") or 0.0),\n'
            '            "ticker_original": ativo_raw,\n'
            '            "status": item.get("status", "OK"),\n'
            '        }'
        ),
        "ancora_nova": (
            '        ativos_map[nome] = {\n'
            '            "preco": float(dados.get("close") or 0.0),\n'
            '            "variacao_pct": float(dados.get("change_percent") or 0.0),\n'
            '            "ticker_original": ativo_raw,\n'
            '            "status": item.get("status", "OK"),\n'
            '            # fix76: propaga rastreabilidade (perdida antes do fix)\n'
            '            "fonte": item.get("fonte") or "DESCONHECIDA",\n'
            '            "timestamp_coleta": item.get("timestamp"),\n'
            '        }'
        ),
    },
]


def pre_validar(conteudo):
    for patch in PATCHES:
        n = conteudo.count(patch["ancora_antiga"])
        if n == 0:
            print(f"ABORTADO: ancora nao encontrada: {patch['nome']}")
            print("---"); print(patch["ancora_antiga"]); print("---")
            return False
        if n > 1:
            print(f"ABORTADO: ancora ambigua ({n}x): {patch['nome']}")
            return False
    return True


def aplicar(conteudo):
    for patch in PATCHES:
        conteudo = conteudo.replace(patch["ancora_antiga"], patch["ancora_nova"], 1)
        print(f"OK: patch aplicado: {patch['nome']}")
    return conteudo


def validar_sintaxe(conteudo):
    try:
        compile(conteudo, str(ARQ), "exec")
    except SyntaxError as e:
        print(f"ABORTADO: sintaxe invalida: {e}")
        return False
    print("OK: sintaxe validada")
    return True


def mostrar_diff(antes, depois):
    print("\n--- DRY-RUN: diff ---")
    for linha in difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ):
        print(linha)
    print("--- DRY-RUN: nada foi salvo ---")


def reverter():
    backups = sorted(ARQ.parent.glob(f"{ARQ.name}.bak_*"))
    if not backups:
        print("ERRO: nenhum backup encontrado")
        sys.exit(1)
    ultimo = backups[-1]
    shutil.copy(ultimo, ARQ)
    print(f"OK: revertido de {ultimo.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reverter", action="store_true")
    args = parser.parse_args()

    if args.reverter:
        reverter()
        return

    if not ARQ.exists():
        print(f"ERRO: {ARQ} nao encontrado")
        sys.exit(1)

    original = ARQ.read_text(encoding="utf-8")
    if not pre_validar(original):
        sys.exit(1)

    novo = aplicar(original)
    if not validar_sintaxe(novo):
        sys.exit(1)

    if args.dry_run:
        mostrar_diff(original, novo)
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ARQ.parent / f"{ARQ.name}.bak_{ts}"
    shutil.copy(ARQ, backup)
    print(f"OK: backup={backup.name}")
    ARQ.write_text(novo, encoding="utf-8")
    print(f"OK: {ARQ} atualizado")


if __name__ == "__main__":
    main()