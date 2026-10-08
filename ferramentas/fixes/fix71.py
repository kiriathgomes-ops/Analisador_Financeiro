# -*- coding: utf-8 -*-
# fix71.py — Corrige 5 leituras de chaves renomeadas / nunca produzidas.
#
# Bugs (mesma familia: renomeacao nao propagada pro leitor):
#   1. win_session_builder.py:231 -> "estimativas_abertura" (plural)
#      JSON tem "estimativa_abertura" (singular) — coletor_dados.py:43 ja aceita ambos
#   2. win_session_builder.py:235 -> "pontos_ajuste_base"
#      JSON tem "preco_referencia_base" (renomeado)
#   3. Coletor.py:168 -> "contratos"
#      Dados_MT5_v2_2.json tem "contratos_vigentes"
#   4. pages/2:471 -> "opening_scenario"
#      Decisao_V2.json nao tem essa chave — adiciona warning defensivo
#   5. pages/7.2:81 -> "filtro_volume_aplicado"
#      AnaliseGraficaSMC_Regras.json nao tem essa chave — adiciona warning defensivo
#
# Uso:
#   python fix71.py --dry-run
#   python fix71.py
#   python fix71.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

PATCHES = {
    Path("v2/core/services/win_session_builder.py"): [
        {
            "nome": "wsb_estimativa_singular",
            "ancora_antiga": (
                '        win_est = (estimativa.get("estimativas_abertura") or {}).get("WIN_INDICE") or {}'
            ),
            "ancora_nova": (
                '        # fix71: aceita singular e plural (coletor_dados.py ja aceita ambos)\n'
                '        win_est = (\n'
                '            (estimativa.get("estimativa_abertura") or {}).get("WIN_INDICE")\n'
                '            or (estimativa.get("estimativas_abertura") or {}).get("WIN_INDICE")\n'
                '            or {}\n'
                '        )'
            ),
        },
        {
            "nome": "wsb_pontos_ajuste_base_renomeado",
            "ancora_antiga": (
                '        base_ajuste = _float(win_est.get("pontos_ajuste_base"))'
            ),
            "ancora_nova": (
                '        # fix71: JSON grava "preco_referencia_base"; "pontos_ajuste_base" e nome antigo\n'
                '        base_ajuste = _float(\n'
                '            win_est.get("preco_referencia_base")\n'
                '            if win_est.get("preco_referencia_base") is not None\n'
                '            else win_est.get("pontos_ajuste_base")\n'
                '        )'
            ),
        },
    ],
    Path("Coletor.py"): [
        {
            "nome": "coletor_contratos_vigentes",
            "ancora_antiga": (
                '        contratos = dados.get("contratos", {})'
            ),
            "ancora_nova": (
                '        # fix71: JSON MT5 v2.2 grava "contratos_vigentes"; "contratos" era do schema v1\n'
                '        contratos = dados.get("contratos_vigentes") or dados.get("contratos", {})'
            ),
        },
    ],
    Path("pages/2_🎯_Setup_Abertura.py"): [
        {
            "nome": "page2_opening_scenario_defensivo",
            "ancora_antiga": (
                '        cenario = self.decisao_v2_raw.get("opening_scenario") or {}\n'
                '        self.v2_direcao_cenario = cenario.get("direcao_provavel")\n'
                '        rel = cenario.get("relacao_com_ajuste") or {}\n'
                '        self.v2_posicao_ajuste = rel.get("posicao") if isinstance(rel, dict) else None'
            ),
            "ancora_nova": (
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
        },
    ],
    Path("pages/7.2_🤖_IA_SpikeImagem.py"): [
        {
            "nome": "page72_filtro_volume_defensivo",
            "ancora_antiga": (
                '    filtro_vol = meta_regras.get("filtro_volume_aplicado", False)'
            ),
            "ancora_nova": (
                '    # fix71: "filtro_volume_aplicado" nunca e gravado no SMC.\n'
                '    # TODO: Motor_SMC_Regras deve expor esse campo no payload.\n'
                '    filtro_vol = (\n'
                '        meta_regras.get("filtro_volume_aplicado")\n'
                '        or meta_regras.get("filtro_volume")\n'
                '        or False\n'
                '    )'
            ),
        },
    ],
}


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
    for arq in PATCHES.keys():
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

    print("===== fix71: leituras de chaves renomeadas / nunca produzidas =====")
    for arq, patches in PATCHES.items():
        processar(arq, patches, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix71 aplicado em 4 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()