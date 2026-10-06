# -*- coding: utf-8 -*-
# verificar_escrita.py — Pra cada campo suspeito, verifica se HA escrita em algum lugar.
# Detecta 3 padroes de escrita:
#   1. dict literal: "campo": ...
#   2. dict assign:  ["campo"] = ...
#   3. atributo:     .campo = ...  ou  campo: ... (em dataclass)
#
# v2: ignora a pasta ferramentas/ (evita falso positivo dos proprios scripts).

import re
import glob
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Pastas/arquivos a ignorar (fix: inclui ferramentas/)
IGNORAR = [
    "__pycache__", ".git", ".bak", "Historico_",
    "auditoria", "ferramentas",
    "fix", "_grep", "_valida", "_check",
]


def deve_ignorar(p):
    return any(t in str(p).replace("\\", "/") for t in IGNORAR)


def procurar_escrita(campo):
    """Retorna lista de (arquivo, linha, tipo_escrita, texto)."""
    achados = []

    padroes = {
        "dict_literal": re.compile(rf'["\']({re.escape(campo)})["\']\s*:'),
        "dict_assign":  re.compile(rf'\[\s*["\']({re.escape(campo)})["\']\s*\]\s*='),
        "attr_assign":  re.compile(rf'\.\s*({re.escape(campo)})\s*='),
        "dataclass_fd": re.compile(rf'^\s*({re.escape(campo)})\s*:\s*\w'),  # campo: tipo
    }

    for arq in glob.glob(f"{RAIZ}/**/*.py", recursive=True):
        if deve_ignorar(arq):
            continue
        try:
            linhas = open(arq, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            continue
        for i, linha in enumerate(linhas, 1):
            sem = linha.split("#", 1)[0]
            for tipo, pat in padroes.items():
                if pat.search(sem):
                    achados.append({
                        "arquivo": str(Path(arq).relative_to(RAIZ)),
                        "linha": i,
                        "tipo": tipo,
                        "texto": linha.strip()[:150],
                    })
                    break
    return achados


CAMPOS = [
    "teorico_win",
    "analise_operacional",
    "pontos_ajuste_base",
    "preco_carregado_di",
    "relacao_com_ajuste",
    "variacao_estimada",
    "status_geral",
]


for c in CAMPOS:
    escritas = procurar_escrita(c)
    print(f"=== {c} ===")
    if not escritas:
        print("  NENHUMA ESCRITA ENCONTRADA -> BUG REAL (le campo que nunca e produzido)")
    else:
        for a in escritas[:8]:
            print(f"  [{a['tipo']}] {a['arquivo']}:{a['linha']} -> {a['texto'][:120]}")
    print()