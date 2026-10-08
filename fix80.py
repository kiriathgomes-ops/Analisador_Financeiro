# -*- coding: utf-8 -*-
# fix80.py — Adiciona Bloco 4 (schemas JSON) e Bloco 5 (funcoes criticas)
# ao Temp_Validacao_Smoke.py.
#
# PROBLEMA:
#   O smoke atual valida apenas "o arquivo importa?" — nao valida logica.
#   Bug do fix73 (lia ultimo.cenario em vez de atualizacoes[-1].cenario)
#   passou pelo smoke sem ser detectado.
#
# FIX:
#   Bloco 4 — valida que os JSONs criticos tem os paths que as pages leem
#   Bloco 5 — testa funcoes criticas com dados reais (leitura de cenario,
#             coerencia canonicos vs aliases)
#
#   Ambos com SKIP GRACIOSO: se JSON nao existe, pula (nao falha).
#
# Uso:
#   python fix80.py --dry-run
#   python fix80.py
#   python fix80.py --reverter

import sys
import shutil
import argparse
import difflib
from pathlib import Path
from datetime import datetime

ARQ = Path("Temp_Validacao_Smoke.py")

NOVO_BLOCO = '''    print("-" * 60)

    # 4. VALIDACAO DE SCHEMAS JSON (fix80)
    print("\\U0001F50D BLOCO 4: SCHEMAS DOS JSONs CRITICOS")
    import json as _json
    from datetime import date as _date

    def _ler_json(path):
        try:
            with open(path, encoding="utf-8") as f:
                return _json.load(f)
        except Exception:
            return None

    hoje = _date.today().isoformat()
    hist_path = f"Coletas/Historico_Aberturas/{hoje}.json"

    schemas_criticos = [
        ("Coletas/DadosAtivosUnificados.json",
         lambda d: isinstance(d.get("ativos"), dict)
                   and len(d["ativos"]) >= 30
                   and all(isinstance(v, dict) and v.get("fonte")
                           for v in d["ativos"].values()),
         "33+ ativos com 'fonte' (fix76)"),
        ("Coletas/Dados_Validados.json",
         lambda d: isinstance(d.get("ativos_validados"), list)
                   and len(d["ativos_validados"]) >= 30
                   and all(a.get("fonte") for a in d["ativos_validados"]),
         "33+ validados com 'fonte'"),
        ("Coletas/Decisao_V2.json",
         lambda d: (d.get("decisao", {})
                     .get("metadados", {})
                     .get("confluencia", {})
                     .get("score_magnitude")) is not None,
         "confluencia.score_magnitude preenchido (fix75)"),
        ("Coletas/Metricas_Calculadas.json",
         lambda d: d.get("indicadores_compostos", {})
                    .get("indicador_adrs_brasileiras") is not None,
         "indicador_adrs_brasileiras presente"),
    ]

    if Path(hist_path).exists():
        schemas_criticos.append(
            (hist_path,
             lambda d: bool(((d.get("atualizacoes") or [{}])[-1]
                             .get("cenario", {}) or {})
                            .get("direcao_provavel")),
             "atualizacoes[-1].cenario.direcao_provavel (fix73/79)")
        )

    for arq, validador, descricao in schemas_criticos:
        d = _ler_json(arq)
        if d is None:
            print(f"   \\u23ED\\uFE0F  SCHEMA: {arq:<38} -> [SKIP: sem arquivo]")
            continue
        try:
            if validador(d):
                print(f"   \\u2705 SCHEMA: {arq:<38} -> [OK]")
            else:
                print(f"   \\u274C SCHEMA: {arq:<38} -> [FALHA: {descricao}]")
                falhas += 1
        except Exception as e:
            print(f"   \\u274C SCHEMA: {arq:<38} -> [ERRO: {e}]")
            falhas += 1

    print("-" * 60)

    # 5. VALIDACAO FUNCIONAL (fix80)
    print("\\U0001F50D BLOCO 5: FUNCOES CRITICAS")

    # Teste A: leitura de cenario do Historico_Aberturas (replica fix73/79)
    if Path(hist_path).exists():
        try:
            d = _ler_json(hist_path)
            atu = d.get("atualizacoes") or []
            if atu:
                cen = atu[-1].get("cenario") or {}
                if cen.get("direcao_provavel"):
                    print(f"   \\u2705 FUNC: cenario Historico_Aberturas -> [OK: {cen['direcao_provavel']}]")
                else:
                    print(f"   \\u274C FUNC: cenario Historico_Aberturas -> [direcao_provavel vazio]")
                    falhas += 1
        except Exception as e:
            print(f"   \\u274C FUNC: cenario -> [ERRO: {e}]")
            falhas += 1
    else:
        print(f"   \\u23ED\\uFE0F  FUNC: cenario -> [SKIP: {hist_path} nao existe]")

    # Teste B: canonicos == aliases no payload (fix75)
    try:
        d = _ler_json("Coletas/Decisao_V2.json")
        if d:
            c = (d.get("decisao", {}).get("metadados", {})
                  .get("confluencia", {}))
            if (c.get("score_magnitude") == c.get("nm_magnitude")
                and c.get("score_direcao") == c.get("nm_direcao_score")):
                print(f"   \\u2705 FUNC: canonicos == aliases (fix75) -> [OK]")
            else:
                print(f"   \\u274C FUNC: canonicos != aliases -> [FALHA]")
                falhas += 1
        else:
            print(f"   \\u23ED\\uFE0F  FUNC: canonicos -> [SKIP: sem Decisao_V2.json]")
    except Exception as e:
        print(f"   \\u274C FUNC: canonicos vs aliases -> [ERRO: {e}]")
        falhas += 1

    print("-" * 60)

    # --- RELATÓRIO FINAL ---'''

PATCHES = [
    {
        "nome": "smoke_adiciona_blocos_4_5",
        "ancora_antiga": (
            '        print(f"❌ [FALHA CRÍTICA] Erro na malha interna de contratos V2 (v2/): {e}")\n'
            '        falhas += 1\n'
            '\n'
            '    # --- RELATÓRIO FINAL ---'
        ),
        "ancora_nova": (
            '        print(f"❌ [FALHA CRÍTICA] Erro na malha interna de contratos V2 (v2/): {e}")\n'
            '        falhas += 1\n'
            '\n'
            + NOVO_BLOCO
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
    print("\n--- DRY-RUN: diff (resumido, primeiras 60 linhas) ---")
    linhas_diff = list(difflib.unified_diff(
        antes.splitlines(), depois.splitlines(),
        lineterm="", fromfile="antes", tofile="depois",
    ))
    for linha in linhas_diff[:60]:
        print(linha)
    if len(linhas_diff) > 60:
        print(f"... +{len(linhas_diff) - 60} linhas")
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