# -*- coding: utf-8 -*-
# fix73.py — Page 2 le opening_scenario do Historico_Aberturas (arquivo real).
#
# BUG (pages/2_🎯_Setup_Abertura.py:471-481):
#   Page lia opening_scenario do Decisao_V2.json — arquivo que NUNCA teve
#   esse campo. Resultado: v2_direcao_cenario e v2_posicao_ajuste sempre None.
#
# CAUSA:
#   O cenário é gerado pelo opening_scenario_engine e GRAVADO por
#   v2_gravar_sessao_win.py em Coletas/Historico_Aberturas/<data>.json
#   (campo "ultimo.cenario"). O orchestrator nunca propaga pro Decisao_V2.
#
# FIX (opcao A — page le do arquivo certo):
#   Page 2 agora le de Coletas/Historico_Aberturas/<data>.json primeiro,
#   com fallback pro Decisao_V2 (caso o orchestrator propague no futuro).
#
# Uso:
#   python fix73.py --dry-run
#   python fix73.py
#   python fix73.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/2_🎯_Setup_Abertura.py")

PATCHES = [
    {
        "nome": "page2_le_cenario_historico",
        "ancora_antiga": (
            '        # fix71: "opening_scenario" nunca e gravado no Decisao_V2.json.\n'
            '        # TODO: integrar opening_scenario_engine no payload do orchestrator.\n'
            '        # Por ora, tenta multiplas fontes antes de desistir.\n'
            '        cenario = (\n'
            '            self.decisao_v2_raw.get("opening_scenario")\n'
            '            or self.decisao_v2_raw.get("decisao", {}).get("opening_scenario")\n'
            '            or {}\n'
            '        )\n'
            '        self.v2_direcao_cenario = cenario.get("direcao_provavel")\n'
            '        rel = cenario.get("relacao_com_ajuste") or {}\n'
            '        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else None'
        ),
        "ancora_nova": (
            '        # fix73: opening_scenario vive em Coletas/Historico_Aberturas/<data>.json\n'
            '        # (gravado por v2_gravar_sessao_win.py via session_history_service).\n'
            '        # A page lia do Decisao_V2.json, que nunca teve esse campo.\n'
            '        cenario = {}\n'
            '        try:\n'
            '            from datetime import date as _date\n'
            '            _hoje = _date.today().isoformat()\n'
            '            _hist, _ = carregar_json_absoluto(f"Historico_Aberturas/{_hoje}.json")\n'
            '            if _hist:\n'
            '                _ult = _hist.get("ultimo") or (_hist.get("atualizacoes") or [{}])[-1]\n'
            '                cenario = _ult.get("cenario", {}) or {}\n'
            '        except Exception:\n'
            '            cenario = {}\n'
            '\n'
            '        # Fallback: Decisao_V2 (caso o orchestrator propague no futuro)\n'
            '        if not cenario:\n'
            '            cenario = (\n'
            '                self.decisao_v2_raw.get("opening_scenario")\n'
            '                or self.decisao_v2_raw.get("decisao", {}).get("opening_scenario")\n'
            '                or {}\n'
            '            )\n'
            '        self.v2_direcao_cenario = cenario.get("direcao_provavel")\n'
            '        rel = cenario.get("relacao_com_ajuste") or {}\n'
            '        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else None'
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