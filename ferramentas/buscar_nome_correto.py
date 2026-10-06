# -*- coding: utf-8 -*-
# buscar_nome_correto.py — Pra cada campo bugado, busca campos similares que SAO escritos.
# Usa heuristica de tokens comuns (split por _).

import re
import glob
from pathlib import Path
from collections import defaultdict

RAIZ = Path(__file__).resolve().parent.parent
IGNORAR = ["__pycache__", ".git", ".bak", "Historico_",
           "auditoria", "fix", "_grep", "_valida", "_check",
           "verificar_escrita", "buscar_nome", "ver_fantasmas",
           "investigar_fantasmas"]

def deve_ignorar(p):
    return any(t in str(p).replace("\\", "/") for t in IGNORAR)


def coletar_escritas():
    """Retorna dict: campo -> lista de (arquivo, linha)."""
    escritas = defaultdict(list)
    padroes = {
        "dict_literal": re.compile(r'["\']([a-z_][a-z0-9_]{3,})["\']\s*:'),
        "attr_assign":  re.compile(r'\.\s*([a-z_][a-z0-9_]{3,})\s*='),
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
                for m in pat.finditer(sem):
                    c = m.group(1)
                    if len(c) < 4:
                        continue
                    escritas[c].append({
                        "arquivo": str(Path(arq).relative_to(RAIZ)),
                        "linha": i,
                        "tipo": tipo,
                        "texto": linha.strip()[:120],
                    })
    return escritas


def tokens(nome):
    return set(nome.lower().split("_"))


def similaridade(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


CAMPOS_BUG = [
    "teorico_win",
    "analise_operacional",
    "preco_carregado_di",
    "variacao_estimada",
    "status_geral",
]


def main():
    print("Coletando escritas no projeto...")
    escritas = coletar_escritas()
    print(f"  {len(escritas)} campos tem alguma escrita\n")

    for bug in CAMPOS_BUG:
        print(f"=== {bug} ===")
        candidatos = []
        for outro, locs in escritas.items():
            if outro == bug:
                continue
            s = similaridade(bug, outro)
            if s >= 0.4:  # pelo menos 40% tokens em comum
                candidatos.append((s, outro, locs))

        candidatos.sort(reverse=True)

        if not candidatos:
            print("  Nenhum campo similar encontrado — bug de nome unico")
        else:
            for s, c, locs in candidatos[:5]:
                print(f"  [{s:.2f}] {c}")
                for l in locs[:3]:
                    print(f"       {l['arquivo']}:{l['linha']} → {l['texto'][:100]}")
        print()


if __name__ == "__main__":
    main()