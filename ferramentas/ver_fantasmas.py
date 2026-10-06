# -*- coding: utf-8 -*-
# ver_fantasmas.py — Mostra contexto dos 9 TYPO_REAL finais.
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
d = json.load(open(RAIZ / "auditoria" / "relatorio_fantasmas.json", encoding="utf-8"))

campos = [
    "contratos",
    "estimativas_abertura",
    "filtro_volume_aplicado",
    "opening_scenario",
    "pontos_ajuste_base",
    "data_execucao",
    "direcao_provavel",
    "relacao_com_ajuste",
    "preco_carregado_di",
]

for c in campos:
    if c not in d["detalhes"]:
        continue
    info = d["detalhes"][c]
    print(f"=== {c} [{info['status']}] ===")
    for oc in info["ocorrencias"][:8]:
        print(f"  {oc['arquivo']}:{oc['linha']} ({oc.get('tipo_detectado', '?')})")
        print(f"    {oc['texto'][:160]}")
    print()