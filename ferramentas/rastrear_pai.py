# -*- coding: utf-8 -*-
# rastrear_pai.py — Rastreia quem escreve a chave PAI do path bugado.

import re
import glob
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IGNORAR = ["__pycache__", ".git", ".bak", "Historico_",
           "auditoria", "fix", "_grep", "_valida", "_check",
           "verificar_", "buscar_", "ver_fantasmas", "investigar_", "rastrear_"]


def deve_ignorar(p):
    return any(t in str(p).replace("\\", "/") for t in IGNORAR)


BUGS = {
    "teorico_win": "previsao_abertura",
    "variacao_estimada": "previsao_abertura",
    "analise_operacional": "analise_operacional",
    "status_geral": "log_pipeline",
}


def buscar_escritas(chave):
    achados = []
    padroes = [
        re.compile(rf'["\']({re.escape(chave)})["\']\s*:'),
        re.compile(rf'\[\s*["\']({re.escape(chave)})["\']\s*\]\s*='),
        re.compile(rf'\b({re.escape(chave)})\s*=\s*'),
    ]
    for arq in glob.glob(f"{RAIZ}/**/*.py", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            linhas = open(arq, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            continue
        for i, linha in enumerate(linhas, 1):
            sem = linha.split("#", 1)[0]
            for pat in padroes:
                if pat.search(sem):
                    achados.append({
                        "arquivo": str(Path(arq).relative_to(RAIZ)),
                        "linha": i,
                        "texto": linha.strip()[:150],
                    })
                    break
    return achados


def buscar_em_json(chave):
    achados = []
    for arq in glob.glob(f"{RAIZ}/Coletas/**/*.json", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            txt = open(arq, encoding="utf-8").read()
        except Exception:
            continue
        if f'"{chave}"' in txt:
            achados.append(str(Path(arq).relative_to(RAIZ)))
    return achados


for bug, pai in BUGS.items():
    print(f"=== {bug} (pai: {pai}) ===")

    escritas = buscar_escritas(pai)
    if escritas:
        print(f"  ESCRITAS de '{pai}':")
        for a in escritas[:6]:
            print(f"    {a['arquivo']}:{a['linha']} → {a['texto'][:130]}")
    else:
        print(f"  Nenhuma escrita de '{pai}' no codigo")

    jsons = buscar_em_json(pai)
    if jsons:
        print(f"  Aparece em {len(jsons)} JSON(s):")
        for j in jsons[:5]:
            print(f"    {j}")
    else:
        print(f"  Nao aparece em nenhum JSON de Coletas/")

    print()