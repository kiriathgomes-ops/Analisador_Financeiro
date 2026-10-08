# -*- coding: utf-8 -*-
# fix63.py — Rotula o gap com sua fonte (LEILAO_REAL | TEORICA_FALLBACK | AJUSTE_FALLBACK).
#
# PROBLEMA:
#   Quando o leilao (OCR) esta indisponivel, o coletor preenche
#   abertura_projetada com a TEORICA e a fonte_abertura vira "CALCULADO".
#   O motor_previsao nao distingue isso, calcula gap como se fosse real,
#   e o operador ve "[GAP] +10738 pts (+5.17%) -> EXTREMO" sem saber que
#   esse gap foi fabricado da teorica, nao do leilao.
#
# FIX (opcao B — rotular, nao silenciar):
#   1. ClassificacaoGAP ganha campo "fonte" (default "LEILAO_REAL")
#   2. classificar_gap aceita param "fonte" e propaga
#   3. motor_previsao mapeia fonte_abertura -> gap_fonte e passa
#   4. metadados expoem "gap_fonte" (visivel no payload)
#   5. obter_resultado_json popa e expoe "gap_fonte" no JSON final
#
# Uso:
#   python fix63.py --dry-run
#   python fix63.py
#   python fix63.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ_SCHEMA = Path("NOVO_MOTOR_PREVISAO_ABERTURA/dados/schemas.py")
ARQ_GAP = Path("NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_gap.py")
ARQ_PREV = Path("NOVO_MOTOR_PREVISAO_ABERTURA/core/motor_previsao.py")

# ============================================================
# PATCHES
# ============================================================

PATCHES_SCHEMA = [
    {
        "nome": "schema_classificacao_gap_fonte",
        "ancora_antiga": (
            '    intensidade: str = "NEUTRO"\n'
            '    classificacao: str = ""\n'
        ),
        "ancora_nova": (
            '    intensidade: str = "NEUTRO"\n'
            '    classificacao: str = ""\n'
            '    # fix63: origem do gap — "LEILAO_REAL" | "TEORICA_FALLBACK" | "AJUSTE_FALLBACK"\n'
            '    fonte: str = "LEILAO_REAL"\n'
        ),
    },
]

PATCHES_GAP = [
    {
        "nome": "gap_signature_fonte",
        "ancora_antiga": (
            'def classificar_gap(\n'
            '    preco_abertura: float,\n'
            '    referencia_fechamento: float,\n'
            '    referencia_ajuste: float = None\n'
            ') -> ClassificacaoGAP:'
        ),
        "ancora_nova": (
            'def classificar_gap(\n'
            '    preco_abertura: float,\n'
            '    referencia_fechamento: float,\n'
            '    referencia_ajuste: float = None,\n'
            '    fonte: str = "LEILAO_REAL",\n'
            ') -> ClassificacaoGAP:'
        ),
    },
    {
        "nome": "gap_log_fonte",
        "ancora_antiga": (
            '    print(f"[GAP] {gap_pontos:+.0f} pts ({gap_percentual:+.4f}%) -> {intensidade}")'
        ),
        "ancora_nova": (
            '    print(f"[GAP] {gap_pontos:+.0f} pts ({gap_percentual:+.4f}%) -> {intensidade} [fonte={fonte}]")'
        ),
    },
    {
        "nome": "gap_return_fonte",
        "ancora_antiga": (
            '        intensidade=intensidade,\n'
            '        classificacao=f"GAP {intensidade}"\n'
            '    )'
        ),
        "ancora_nova": (
            '        intensidade=intensidade,\n'
            '        classificacao=f"GAP {intensidade}",\n'
            '        fonte=fonte,\n'
            '    )'
        ),
    },
]

PATCHES_PREV = [
    {
        "nome": "prev_mapa_gap_fonte",
        "ancora_antiga": (
            '        # 1. GAP\n'
            '        gap = classificar_gap(abertura_teorica, fechamento_anterior, ajuste)'
        ),
        "ancora_nova": (
            '        # 1. GAP\n'
            '        # fix63: mapeia a fonte da abertura para a fonte do gap\n'
            '        _mapa_fonte_gap = {\n'
            '            "OCR_LEILAO": "LEILAO_REAL",\n'
            '            "CALCULADO": "TEORICA_FALLBACK",\n'
            '            "AJUSTE": "AJUSTE_FALLBACK",\n'
            '        }\n'
            '        gap_fonte = _mapa_fonte_gap.get(\n'
            '            getattr(self.entrada, "fonte_abertura", None) or "CALCULADO",\n'
            '            "DESCONHECIDO",\n'
            '        )\n'
            '        gap = classificar_gap(abertura_teorica, fechamento_anterior, ajuste, fonte=gap_fonte)'
        ),
    },
    {
        "nome": "prev_metadados_gap_fonte",
        "ancora_antiga": (
            '                "fonte_abertura": self.entrada.fonte_abertura,\n'
            '                "divergencia_direcao": div_flag,'
        ),
        "ancora_nova": (
            '                "fonte_abertura": self.entrada.fonte_abertura,\n'
            '                "gap_fonte": gap_fonte,\n'
            '                "divergencia_direcao": div_flag,'
        ),
    },
    {
        "nome": "prev_json_pop_gap_fonte",
        "ancora_antiga": (
            '        fonte_abertura = metadados.pop("fonte_abertura", "DESCONHECIDA")\n'
            '        divergencia_direcao = metadados.pop("divergencia_direcao", False)'
        ),
        "ancora_nova": (
            '        fonte_abertura = metadados.pop("fonte_abertura", "DESCONHECIDA")\n'
            '        gap_fonte = metadados.pop("gap_fonte", "DESCONHECIDO")\n'
            '        divergencia_direcao = metadados.pop("divergencia_direcao", False)'
        ),
    },
    {
        "nome": "prev_json_output_gap_fonte",
        "ancora_antiga": (
            '            "fonte_abertura": fonte_abertura,\n'
            '            "faixa_provavel": ['
        ),
        "ancora_nova": (
            '            "fonte_abertura": fonte_abertura,\n'
            '            "gap_fonte": gap_fonte,\n'
            '            "faixa_provavel": ['
        ),
    },
]


# ============================================================
# Infra
# ============================================================

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
    for arq in [ARQ_SCHEMA, ARQ_GAP, ARQ_PREV]:
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

    print("===== fix63: rotular gap pela fonte =====")
    processar(ARQ_SCHEMA, PATCHES_SCHEMA, args.dry_run)
    processar(ARQ_GAP, PATCHES_GAP, args.dry_run)
    processar(ARQ_PREV, PATCHES_PREV, args.dry_run)

    if not args.dry_run:
        print("\nOK: fix63 aplicado nos 3 arquivos")
    else:
        print("\n--- DRY-RUN concluido: nada foi salvo ---")


if __name__ == "__main__":
    main()