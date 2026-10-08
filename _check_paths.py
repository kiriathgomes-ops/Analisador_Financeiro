# -*- coding: utf-8 -*-
# _check_paths.py — Verifica se utilitarios tem path baseado em __file__.
import re
from pathlib import Path

CANDIDATOS = [
    "audit_camada1.py", "audit_camada2.py",
    "analisar_divergencia.py", "analisar_historico.py",
    "analisar_historico_v2.py", "analisar_rompimento_10h.py",
    "analise_trilha_c_v2.py", "backtest_bias_estabilidade.py",
    "diag_orb_10h.py", "ver_componentes_hoje.py",
    "gerar_docs.py", "gerar_dump_completo.py",
    "Gerar_Mapa_Fluxo.py", "Gerar_Mapa_Inventario_Tecnico.py",
    "Gerar_Mapa_Projeto.py",
]

TERMOS = [
    "__file__", "parent.parent", "parent.parent.parent",
    "Path.cwd", "os.getcwd", "os.path.dirname(os.path.abspath",
    "BASE_DIR", "RAIZ_PROJETO", "ROOT_DIR",
]

for arq in CANDIDATOS:
    p = Path(arq)
    if not p.exists():
        print(f"=== {arq}: NAO EXISTE ===")
        print()
        continue

    linhas = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    hits = []
    for i, l in enumerate(linhas, 1):
        if any(t in l for t in TERMOS):
            hits.append(f"  {i}: {l.strip()[:120]}")

    print(f"=== {arq} ===")
    if hits:
        for h in hits[:5]:
            print(h)
    else:
        print("  (nenhum path baseado em __file__/cwd — SEGURO MOVER)")
    print()