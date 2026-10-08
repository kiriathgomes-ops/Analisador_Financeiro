# -*- coding: utf-8 -*-
# fix81.py — Remove fallback legado Dados_MT5.json (schema v1).
#
# MOTIVO:
#   Dados_MT5.json nao e mais gerado (substituido por Dados_MT5_v2_2.json).
#   Manter fallback silencioso mascara problemas: se v2.2 falhar, o sistema
#   tenta ler v1 e pode retornar dado desatualizado sem aviso.
#
# REGRA (usuario): sem fallback. Se nao tem informacao, escreve indisponivel.
#
# PATCHES (6 total):
#   1. Coletor.py — remove import FILE_MT5
#   2. Coletor.py — remove FILE_MT5 = str(FILE_MT5)
#   3. Coletor.py — corrige docstring (sem prioridade 2)
#   4. Coletor.py — corrige msg de erro (sem "tentando formato antigo")
#   5. Coletor.py — remove bloco v1 inteiro
#   6. win_session_builder.py — remove fallback
#   7. config.py — remove FILE_MT5
#
# Uso:
#   python fix81.py --dry-run
#   python fix81.py
#   python fix81.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

PATCHES = {
    Path("Coletor.py"): [
        {
            "nome": "coletor_remove_str_mt5",
            "ancora_antiga": "FILE_MT5 = str(FILE_MT5)\n",
            "ancora_nova": "",
        },
        {
            "nome": "coletor_remove_import_mt5",
            "ancora_antiga": "    FILE_MT5,\n",
            "ancora_nova": "",
        },
        {
            "nome": "coletor_remove_docstring_v1",
            "ancora_antiga": (
                '    Extrai o \'last\' dos contratos principais de WIN e WDO.\n'
                '\n'
                '    Prioridade:\n'
                '      1. Dados_MT5_v2_2.json\n'
                '      2. Dados_MT5.json (legado)\n'
                '    """'
            ),
            "ancora_nova": (
                '    Extrai o \'last\' dos contratos principais de WIN e WDO.\n'
                '\n'
                '    Fonte unica: Dados_MT5_v2_2.json\n'
                '    Sem fallback legado (fix81 — schema v1 removido).\n'
                '    """'
            ),
        },
        {
            "nome": "coletor_remove_msg_formato_antigo",
            "ancora_antiga": (
                '            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}. Tentando formato antigo...")'
            ),
            "ancora_nova": (
                '            print(f"[AVISO] Falha ao ler Dados_MT5_v2_2.json: {e}. MT5 indisponivel.")'
            ),
        },
        {
            "nome": "coletor_remove_bloco_v1",
            "ancora_antiga": (
                '    if not os.path.exists(FILE_MT5):\n'
                '        print("[AVISO] Nenhum arquivo MT5 encontrado (v2.2 nem v1).")\n'
                '        return resultado\n'
                '\n'
                '    try:\n'
                '        with open(FILE_MT5, "r", encoding="utf-8") as f:\n'
                '            dados = json.load(f)\n'
                '\n'
                '        # fix71: JSON MT5 v2.2 grava "contratos_vigentes"; "contratos" era do schema v1\n'
                '        contratos = dados.get("contratos_vigentes") or dados.get("contratos", {})\n'
                '        timestamp = dados.get("timestamp", datetime.now().isoformat())\n'
                '        mapeamento_contratos = {\n'
                '            "WIN": ["WINQ26", "WINV26", "WINZ26"],\n'
                '            "WDO": ["WDOQ26", "WDOV26", "WDOZ26", "WDOU26"],\n'
                '        }\n'
                '\n'
                '        for ativo, lista in mapeamento_contratos.items():\n'
                '            for contrato in lista:\n'
                '                if contrato in contratos:\n'
                '                    info = contratos[contrato]\n'
                '                    last = info.get("last")\n'
                '                    if last is not None and last > 0:\n'
                '                        resultado[ativo] = {\n'
                '                            "contrato": contrato,\n'
                '                            "last": float(last),\n'
                '                            "timestamp": timestamp,\n'
                '                            "fonte": "MT5_v1",\n'
                '                        }\n'
                '                        break\n'
                '\n'
                '        if "WIN" in resultado:\n'
                '            print(\n'
                '                f"   ✅ Last WIN via MT5 v1: "\n'
                '                f"{resultado[\'WIN\'][\'last\']} ({resultado[\'WIN\'][\'contrato\']})"\n'
                '            )\n'
                '        if "WDO" in resultado:\n'
                '            print(\n'
                '                f"   ✅ Last WDO via MT5 v1: "\n'
                '                f"{resultado[\'WDO\'][\'last\']} ({resultado[\'WDO\'][\'contrato\']})"\n'
                '            )\n'
                '        return resultado\n'
                '\n'
                '    except Exception as e:\n'
                '        print(f"[ERRO] Falha ao ler Dados_MT5.json: {e}")\n'
                '        return {}'
            ),
            "ancora_nova": (
                '    # fix81: fallback legado (Dados_MT5.json) removido.\n'
                '    # Se v2.2 nao existir, retorna {} e loga indisponivel.\n'
                '    return resultado'
            ),
        },
    ],
    Path("v2/core/services/win_session_builder.py"): [
        {
            "nome": "wsb_remove_fallback_v1",
            "ancora_antiga": (
                '        # Fallback: se v2.2 não existir, tenta formato antigo\n'
                '        if not mt5:\n'
                '            mt5 = _carregar_json(self.coletas / "Dados_MT5.json")\n'
                '\n'
                '        session = WinSession()'
            ),
            "ancora_nova": (
                '        # fix81: fallback legado removido. Se v2.2 nao existir, mt5=None\n'
                '        # e _preencher_metadata/_preencher_precos tratam graciosamente.\n'
                '\n'
                '        session = WinSession()'
            ),
        },
    ],
    Path("config.py"): [
        {
            "nome": "config_remove_file_mt5",
            "ancora_antiga": 'FILE_MT5 = COLETAS_DIR / "Dados_MT5.json"\n',
            "ancora_nova": "",
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
            print("---primeiras 200 chars da ancora---")
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

    print("===== fix81: remove fallback legado Dados_MT5.json =====")
    for arq, patches in PATCHES.items():
        processar(arq, patches, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix81 aplicado em 3 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()