# -*- coding: utf-8 -*-
"""
fix51.py - Simplifica minerio de ferro: usa F1 (front) em vez de F2

Contexto:
    O TV scanner nao indexa o continuo do 2o vencimento (SGX:FEF2!).
    Testes em 01/10/2026 mostraram retorno VAZIO para esse ticker.
    F1 (SGX:FEF1!) funciona normalmente e tem liquidez.

Decisao:
    Usar F1 (front month) para o indicador de mercado externo.
    Remove toda a infra de "2o mes" (funcao, constante, mapeamento).

Mudancas:
    A) config.py
       - Remove funcao _ticker_fef2 + TICKER_FEF2
       - Remove TICKER_FEF2 da lista TICKERS_TRADINGVIEW
       - Remove mapeamento SGX:FEF2! -> IRON_ORE_2M

    B) Calculadora.py
       - Consulta IRON_ORE (F1) em vez de IRON_ORE_2M
       - Atualiza comentario e label do print

Uso:
    python fix51.py --dry-run
    python fix51.py
    python fix51.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_CFG = ROOT / "config.py"
ALVO_CALC = ROOT / "Calculadora.py"

# --- PATCH 1: config, remove funcao + constante ---
CFG_FUNC_ANTIGO = (
    'def _ticker_fef2() -> str:\n'
    '    """Min\u00e9rio de ferro 2\u00ba m\u00eas (SGX) \u2014 ano corrente."""\n'
    '    return f"SGX:FEFU{__import__(\'datetime\').datetime.now().year}"\n'
    '\n'
    '\n'
    'TICKER_FEF2 = _ticker_fef2()\n'
    '\n'
    'TICKERS_TRADINGVIEW: List[str] = [\n'
)
CFG_FUNC_NOVO = 'TICKERS_TRADINGVIEW: List[str] = [\n'

# --- PATCH 2: config, remove item da lista ---
CFG_LIST_ANTIGO = (
    '    "SGX:FEF1!",\n'
    '    TICKER_FEF2,\n'
    '    "NYMEX:CL1!",\n'
)
CFG_LIST_NOVO = (
    '    "SGX:FEF1!",\n'
    '    "NYMEX:CL1!",\n'
)

# --- PATCH 3: config, remove mapeamento ---
CFG_MAP_ANTIGO = (
    '    "SGX:FEF1!": "IRON_ORE",\n'
    '    "SGX:FEF2!": "IRON_ORE_2M",\n'
)
CFG_MAP_NOVO = (
    '    "SGX:FEF1!": "IRON_ORE",\n'
)

# --- PATCH 4: calculadora, comentario + lookup ---
CALC_LOOKUP_ANTIGO = (
    '    #    F\u00f3rmula: -(VIX_pct) + CRUDE_OIL_pct + IRON_ORE_2M_pct\n'
)
CALC_LOOKUP_NOVO = (
    '    #    F\u00f3rmula: -(VIX_pct) + CRUDE_OIL_pct + IRON_ORE_pct\n'
    '    #    fix51: usa F1 (front month); F2 nao esta disponivel no TV scanner.\n'
)

CALC_GET_ANTIGO = '    fef2_obj = mapa.get("IRON_ORE_2M", {})\n'
CALC_GET_NOVO = '    fef2_obj = mapa.get("IRON_ORE", {})\n'

# --- PATCH 5: calculadora, label do print ---
CALC_PRINT_ANTIGO = (
    '    print(f"Min\u00e9rio FEF2 (2\u00ba M\u00eas)   : {iron_fef2_close} ({iron_fef2_pct}%)")\n'
)
CALC_PRINT_NOVO = (
    '    print(f"Min\u00e9rio de Ferro (F1)   : {iron_fef2_close} ({iron_fef2_pct}%)")\n'
)

PATCHES = [
    ("config: remove _ticker_fef2 + constante", ALVO_CFG, CFG_FUNC_ANTIGO, CFG_FUNC_NOVO),
    ("config: remove TICKER_FEF2 da lista", ALVO_CFG, CFG_LIST_ANTIGO, CFG_LIST_NOVO),
    ("config: remove mapeamento SGX:FEF2!", ALVO_CFG, CFG_MAP_ANTIGO, CFG_MAP_NOVO),
    ("calculadora: comentario F1", ALVO_CALC, CALC_LOOKUP_ANTIGO, CALC_LOOKUP_NOVO),
    ("calculadora: lookup IRON_ORE_2M -> IRON_ORE", ALVO_CALC, CALC_GET_ANTIGO, CALC_GET_NOVO),
    ("calculadora: label print", ALVO_CALC, CALC_PRINT_ANTIGO, CALC_PRINT_NOVO),
]


def _backup(p):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def aplicar(dry_run):
    mudancas = 0
    faltando = []

    for nome, alvo, antigo, novo in PATCHES:
        if not alvo.exists():
            faltando.append(f"{nome} ({alvo.name} nao existe)")
            continue
        conteudo = alvo.read_text(encoding="utf-8")
        if antigo not in conteudo:
            if novo in conteudo:
                print(f"  [INFO] ja aplicado: {nome}")
                continue
            faltando.append(nome)
            continue

        novo_conteudo = conteudo.replace(antigo, novo, 1)
        if not dry_run:
            bak = _backup(alvo)
            print(f"  [BACKUP] {bak.name}")
            alvo.write_text(novo_conteudo, encoding="utf-8")
        print(f"  [PATCH OK] {nome}")
        mudancas += 1

    if faltando:
        print(f"\n[ABORT] {len(faltando)} patch(es) nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if mudancas == 0:
        print("\n[INFO] nada a fazer.")
        return 0

    if dry_run:
        print(f"\n[DRY-RUN] {mudancas} patch(es) seriam aplicados.")
        return 0

    print(f"\n[OK] {mudancas} patch(es) aplicados.")
    return 0


def reverter():
    for alvo in (ALVO_CFG, ALVO_CALC):
        if not alvo.exists():
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[ERRO] {alvo.name}: sem backup")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} <- {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))