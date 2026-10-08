# -*- coding: utf-8 -*-
# fix83.py — Integra OpeningScenario no payload do Decisao_V2.json.
#
# DEBITO (TODO do fix71):
#   O opening_scenario_engine gera OpeningScenario, mas o resultado so vai
#   pro Historico_Aberturas (via v2_gravar_sessao_win). O orchestrator nao
#   propaga pro Decisao_V2.json, forcando a page 2 a ler 2 arquivos.
#
# FIX:
#   1. Orchestrator importa build_win_session + gerar_cenario_abertura
#   2. No consolidar_decisao, apos _verificar_confluencia:
#      - Monta session + gera cenario
#      - Guarda em self._cenario_abertura
#   3. Payload ganha metadados.opening_scenario
#   4. Page 2 le do Decisao_V2 primeiro, fallback Historico_Aberturas
#
# SEGURO: se build_win_session ou engine falhar, usa None (nao quebra payload).
#
# Uso:
#   python fix83.py --dry-run
#   python fix83.py
#   python fix83.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

PATCHES = {
    Path("v2/core/engines/v2_orchestrator.py"): [
        # ---- 1. Import do engine no topo ----
        {
            "nome": "orq_import_engine",
            "ancora_antiga": (
                'from config import (\n'
                '    FILE_DECISAO_V2,'
            ),
            "ancora_nova": (
                '# fix83: import do opening_scenario_engine\n'
                'from v2.core.services.win_session_builder import build_win_session\n'
                'from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura\n'
                '\n'
                'from config import (\n'
                '    FILE_DECISAO_V2,'
            ),
        },
        # ---- 2. Chamar engine no consolidar_decisao ----
        {
            "nome": "orq_gerar_cenario",
            "ancora_antiga": (
                '        operar, vies_final, direcao_motores, confianca, motivos, riscos = \\\n'
                '            self._verificar_confluencia(smc, novo_motor)\n'
                '\n'
                '        entrada = None'
            ),
            "ancora_nova": (
                '        operar, vies_final, direcao_motores, confianca, motivos, riscos = \\\n'
                '            self._verificar_confluencia(smc, novo_motor)\n'
                '\n'
                '        # fix83: gera OpeningScenario (direcao provavel + relacao com ajuste)\n'
                '        self._cenario_abertura = None\n'
                '        try:\n'
                '            _session = build_win_session()\n'
                '            self._cenario_abertura = gerar_cenario_abertura(_session)\n'
                '        except Exception as _e:\n'
                '            print(f"[AVISO] fix83: falha ao gerar cenario: {_e}")\n'
                '\n'
                '        entrada = None'
            ),
        },
        # ---- 3. Adicionar opening_scenario no payload ----
        {
            "nome": "orq_payload_cenario",
            "ancora_antiga": (
                '                    "gap_pts": gap_pts,\n'
                '                    "ajuste": win_ajuste,\n'
                '                    "last": float(win_last or 0.0),\n'
                '                },'
            ),
            "ancora_nova": (
                '                    "gap_pts": gap_pts,\n'
                '                    "ajuste": win_ajuste,\n'
                '                    "last": float(win_last or 0.0),\n'
                '                    # fix83: OpeningScenario (movido do Historico_Aberturas)\n'
                '                    "opening_scenario": self._serializar_cenario(),\n'
                '                },'
            ),
        },
        # ---- 4. Helper de serializacao (metodo novo na classe) ----
        {
            "nome": "orq_helper_serializar",
            "ancora_antiga": (
                '    # ------------------------------------------------------------\n'
                '    # Consolidação principal\n'
                '    # ------------------------------------------------------------\n'
                '    def consolidar_decisao(self) -> dict:'
            ),
            "ancora_nova": (
                '    # ------------------------------------------------------------\n'
                '    # fix83: serializa OpeningScenario pro payload\n'
                '    # ------------------------------------------------------------\n'
                '    def _serializar_cenario(self) -> Optional[Dict[str, Any]]:\n'
                '        c = getattr(self, "_cenario_abertura", None)\n'
                '        if not c:\n'
                '            return None\n'
                '        try:\n'
                '            rel = getattr(c, "relacao_com_ajuste", None)\n'
                '            return {\n'
                '                "direcao_provavel": c.direcao_provavel,\n'
                '                "probabilidade_direcao": c.probabilidade_direcao,\n'
                '                "confianca_geral": c.confianca_geral,\n'
                '                "relacao_com_ajuste": {\n'
                '                    "posicao": rel.posicao if rel else None,\n'
                '                    "cenario_principal": rel.cenario_principal if rel else None,\n'
                '                    "probabilidade_cenario": rel.probabilidade_cenario if rel else None,\n'
                '                },\n'
                '                "cenario_alternativo": c.cenario_alternativo,\n'
                '                "niveis_observacao": c.niveis_observacao or {},\n'
                '                "contexto_resumo": c.contexto_resumo or [],\n'
                '            }\n'
                '        except Exception as e:\n'
                '            print(f"[AVISO] fix83: falha ao serializar cenario: {e}")\n'
                '            return None\n'
                '\n'
                '    # ------------------------------------------------------------\n'
                '    # Consolidação principal\n'
                '    # ------------------------------------------------------------\n'
                '    def consolidar_decisao(self) -> dict:'
            ),
        },
    ],
    Path("pages/2_🎯_Setup_Abertura.py"): [
        # ---- 5. Page 2 le do Decisao_V2 primeiro, fallback Historico ----
        {
            "nome": "page2_le_payload_primeiro",
            "ancora_antiga": (
                '        # fix73: opening_scenario vive em Coletas/Historico_Aberturas/<data>.json\n'
                '        # (gravado por v2_gravar_sessao_win.py via session_history_service).\n'
                '        # A page lia do Decisao_V2.json, que nunca teve esse campo.\n'
                '        cenario = {}\n'
                '        try:\n'
                '            from datetime import date as _date\n'
                '            _hoje = _date.today().isoformat()\n'
                '            _hist, _ = carregar_json_absoluto(f"Historico_Aberturas/{_hoje}.json")\n'
                '            if _hist:\n'
                '                # fix79: "cenario" vive em atualizacoes[-1].cenario.\n'
                '                # "ultimo" e um resumo achatado SEM "cenario" (bug fix73).\n'
                '                _atu = _hist.get("atualizacoes") or []\n'
                '                if _atu:\n'
                '                    cenario = (_atu[-1].get("cenario") or {})\n'
                '                if not cenario:\n'
                '                    # fallback: tentar "ultimo" (caso o schema mude)\n'
                '                    _ult = _hist.get("ultimo") or {}\n'
                '                    cenario = _ult.get("cenario", {}) or {}\n'
                '        except Exception:\n'
                '            cenario = {}\n'
                '\n'
                '        # Fallback: Decisao_V2 (caso o orchestrator propague no futuro)\n'
                '        if not cenario:\n'
                '            cenario = (\n'
                '                self.decisao_v2_raw.get("opening_scenario")\n'
                '                or self.decisao_v2_raw.get("decisao", {}).get("opening_scenario")\n'
                '                or {}\n'
                '            )'
            ),
            "ancora_nova": (
                '        # fix83: opening_scenario agora vive no Decisao_V2.json\n'
                '        # (metadados.opening_scenario). Historico_Aberturas fica como fallback.\n'
                '        cenario = (\n'
                '            self.decisao_v2_raw.get("decisao", {})\n'
                '                .get("metadados", {})\n'
                '                .get("opening_scenario")\n'
                '            or self.decisao_v2_raw.get("opening_scenario")\n'
                '            or {}\n'
                '        )\n'
                '\n'
                '        # Fallback legado: Historico_Aberturas (fix73/79)\n'
                '        if not cenario:\n'
                '            try:\n'
                '                from datetime import date as _date\n'
                '                _hoje = _date.today().isoformat()\n'
                '                _hist, _ = carregar_json_absoluto(f"Historico_Aberturas/{_hoje}.json")\n'
                '                if _hist:\n'
                '                    _atu = _hist.get("atualizacoes") or []\n'
                '                    if _atu:\n'
                '                        cenario = (_atu[-1].get("cenario") or {})\n'
                '            except Exception:\n'
                '                cenario = {}'
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
            print("---primeiras 200 chars---")
            print(antiga[:200])
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

    print("===== fix83: OpeningScenario no payload do orchestrator =====")
    for arq, patches in PATCHES.items():
        processar(arq, patches, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix83 aplicado em 2 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()