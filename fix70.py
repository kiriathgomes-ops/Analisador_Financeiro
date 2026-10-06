# -*- coding: utf-8 -*-
# fix70.py — Remove bloco de codigo morto em prediction_service.py.
#
# BUG (v2/core/services/prediction_service.py:45-90):
#   if ENGINE_VIES_COMO_FALLBACK and LEGADO_DISPONIVEL:
#       ...
#       win = dados_legado.get("analise_operacional", {}).get("WIN_INDICE", {})
#       ...
#
# ENGINE_VIES_COMO_FALLBACK e SEMPRE False (config.py nao exporta essa
# constante; ImportError na l.11-13 cai em False). O bloco inteiro e
# inalcancavel. Dentro dele, le chave "analise_operacional" que foi
# renomeada para "estimativa_abertura" — mais um motivo pra ser inutil.
#
# FIX: remove o bloco inteiro (l.45-90) e substitui por comentario curto.
#
# Uso:
#   python fix70.py --dry-run
#   python fix70.py
#   python fix70.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("v2/core/services/prediction_service.py")

PATCHES = [
    {
        "nome": "remove_codigo_morto_fallback_engine_vies",
        "ancora_antiga": (
            '        # ------------------------------------------------------------\n'
            '        # 2. Fallback condicional (Engine_Vies legado)\n'
            '        # ------------------------------------------------------------\n'
            '        if ENGINE_VIES_COMO_FALLBACK and LEGADO_DISPONIVEL:\n'
            '            print("⚠️ PredictionService: usando fallback Engine_Vies (flag ativa)")\n'
            '            try:\n'
            '                dados_legado = executar_core()\n'
            '                if dados_legado:\n'
            '                    win = dados_legado.get("analise_operacional", {}).get("WIN_INDICE", {})\n'
            '                    vies = win.get("vies_final", "NEUTRO")\n'
            '                    score = win.get("score_numeric", 0)\n'
            '\n'
            '                    if "COMPRA" in vies.upper() and score > 1.0:\n'
            '                        direcao = "COMPRA"\n'
            '                    elif "VENDA" in vies.upper() and score < -1.0:\n'
            '                        direcao = "VENDA"\n'
            '                    else:\n'
            '                        return self._criar_contexto_neutro(\n'
            '                            motivo="Engine_Vies retornou NEUTRO ou score baixo"\n'
            '                        )\n'
            '\n'
            '                    score_norm = min(100, max(30, abs(score) * 20))\n'
            '                    return PredictionContext(\n'
            '                        timestamp=datetime.now(),\n'
            '                        ativo="WIN",\n'
            '                        abertura_projetada=0.0,\n'
            '                        faixa_provavel_inferior=0.0,\n'
            '                        faixa_provavel_superior=0.0,\n'
            '                        gap_pontos=0.0,\n'
            '                        gap_percentual=0.0,\n'
            '                        gap_intensidade="N/A",\n'
            '                        classificacao_gap="N/A",\n'
            '                        direcao_prevista=direcao,\n'
            '                        score=score_norm,\n'
            '                        score_classificacao="FORTE" if score_norm > 70 else "MODERADO",\n'
            '                        score_detalhes={"legado_score": score},\n'
            '                        analise_ajuste={},\n'
            '                        cenario_principal={},\n'
            '                        cenario_alternativo={},\n'
            '                        metadados={"fonte": "Engine_Vies (fallback)"},\n'
            '                        score_direcao=direcao,\n'
            '                        score_forca="FORTE" if score_norm > 70 else "MODERADO",\n'
            '                        score_magnitude=score_norm,\n'
            '                    )\n'
            '            except Exception as e:\n'
            '                print(f"⚠️ PredictionService: erro no fallback: {e}")\n'
            '\n'
            '        # ------------------------------------------------------------\n'
            '        # 3. Nenhuma fonte disponível\n'
            '        # ------------------------------------------------------------'
        ),
        "ancora_nova": (
            '        # ------------------------------------------------------------\n'
            '        # 2. Fallback condicional (Engine_Vies legado) — REMOVIDO (fix70)\n'
            '        # ------------------------------------------------------------\n'
            '        # fix70: bloco removido por ser codigo morto inalcancavel.\n'
            '        # ENGINE_VIES_COMO_FALLBACK = False sempre (config.py nao exporta\n'
            '        # a constante; ImportError na l.11-13 cai no default False).\n'
            '        # Alem disso, lia chave "analise_operacional" que foi renomeada\n'
            '        # para "estimativa_abertura" no calculador atual.\n'
            '        # Se um dia o fallback legado voltar a ser necessario, reaproveitar\n'
            '        # este bloco via commit 0ca5b5a (historico git) com a chave correta.\n'
            '\n'
            '        # ------------------------------------------------------------\n'
            '        # 3. Nenhuma fonte disponível\n'
            '        # ------------------------------------------------------------'
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