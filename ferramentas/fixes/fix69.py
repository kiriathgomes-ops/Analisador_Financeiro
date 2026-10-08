# -*- coding: utf-8 -*-
# fix69.py — Page 8.1 para de mostrar "FALHA" quando Pipeline_Log.json nao existe.
#
# BUG (pages/8.1_🗺️_Mapa_da_Aplicacao.py:46-52):
#   status_geral = log_pipeline.get("status_geral", "DESCONHECIDO")
#   if status_geral == "SUCESSO": ... else: st.error("FALHA")
#
# Como Pipeline_Log.json NUNCA foi gerado (feature inacabada), o arquivo nao
# existe, log_pipeline={}, status_geral="DESCONHECIDO", e a page mostra
# SEMPRE "❌ FALHA ou INTERROMPIDO" — alarme falso em vermelho.
#
# FIX: distinguir 3 casos:
#   - Arquivo nao existe         -> st.warning (amarelo, nao assusta)
#   - status_geral == SUCESSO    -> st.success
#   - status_geral == FALHA      -> st.error (so quando REALMENTE ha falha)
#   - status_geral == outro      -> st.info
#
# Uso:
#   python fix69.py --dry-run
#   python fix69.py
#   python fix69.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("pages/8.1_🗺️_Mapa_da_Aplicacao.py")

PATCHES = [
    {
        "nome": "page_8_1_status_honesto",
        "ancora_antiga": (
            '# Captura o status da última execução real do pipeline para exibir em tela\n'
            'status_geral = log_pipeline.get("status_geral", "DESCONHECIDO")\n'
            'data_exec = log_pipeline.get("data_execucao", "N/A")\n'
            '\n'
            'if status_geral == "SUCESSO":\n'
            '    st.success(f"✅ **Último Ciclo do Pipeline:** SUCESSO (Executado em {data_exec})")\n'
            'else:\n'
            '    st.error(f"❌ **Último Ciclo do Pipeline:** FALHA ou INTERROMPIDO (Verifique o log em {data_exec})")'
        ),
        "ancora_nova": (
            '# Captura o status da última execução real do pipeline para exibir em tela\n'
            '# fix69: distingue "arquivo ausente" (feature inacabada) de "falha real"\n'
            'if not log_pipeline:\n'
            '    st.warning(\n'
            '        "⚠️ **Log do Pipeline indisponível** — `Pipeline_Log.json` não encontrado. "\n'
            '        "Este arquivo depende de uma feature de logging que ainda não foi implementada."\n'
            '    )\n'
            '    status_geral = "INDISPONIVEL"\n'
            '    data_exec = "N/A"\n'
            'else:\n'
            '    status_geral = log_pipeline.get("status_geral", "DESCONHECIDO")\n'
            '    data_exec = log_pipeline.get("data_execucao", "N/A")\n'
            '    if status_geral == "SUCESSO":\n'
            '        st.success(f"✅ **Último Ciclo do Pipeline:** SUCESSO (Executado em {data_exec})")\n'
            '    elif status_geral in ("FALHA", "INTERROMPIDO", "ERRO"):\n'
            '        st.error(f"❌ **Último Ciclo do Pipeline:** {status_geral} (Executado em {data_exec})")\n'
            '    else:\n'
            '        st.info(f"ℹ️ **Último Ciclo do Pipeline:** {status_geral} (Executado em {data_exec})")'
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