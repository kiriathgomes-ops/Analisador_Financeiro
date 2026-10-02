# -*- coding: utf-8 -*-
"""
fix53.py - Remove referencias remanescentes a IRON_ORE_2M

Contexto:
    fix51 removeu a infra do minerio 2o mes (config/Calculadora/Coletor),
    mas 8 consumidores a jusante continuavam lendo IRON_ORE_2M do
    Dados_Validados.json. Como o ativo nao existe mais, ficam com None
    silencioso.

Mudancas (6 patches em 5 arquivos):
    A) analisar_rompimento_10h.py - linha() usa IRON_ORE
    B) pages/2_Setup_Abertura.py - _get_var_rom5 usa IRON_ORE
    C) pages/3_Monitor_Abertura_Leilao.py - idem
    D) pages/5_Ativos_Monitorados.py - remove IRON_ORE_2M da lista
    E) v2/core/contracts/win_session.py - remove campo iron_ore_2m
    F) v2/core/services/win_session_builder.py - remove build do campo

Nao mexe (ja funciona por fallback):
    - v2/core/services/market_service.py (tem "or get_ativo IRON_ORE")
    - v2/pages/2_analise_detalhada.py (tem fallback)

Uso:
    python fix53.py --dry-run
    python fix53.py
    python fix53.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Patch 1: analisar_rompimento_10h.py
ARQ1 = ROOT / "analisar_rompimento_10h.py"
P1_OLD = '        linha("IRON_ORE_2M"),\n'
P1_NEW = '        linha("IRON_ORE"),\n'

# Patch 2: pages/2_Setup_Abertura.py
import glob as _glob
_pages = _glob.glob(str(ROOT / "pages" / "2_*.py"))
ARQ2 = Path(_pages[0]) if _pages else ROOT / "pages" / "2_x.py"
P2_OLD = '    iron = _get_var_rom5(rom5, "IRON_ORE_2M")\n'
P2_NEW = '    iron = _get_var_rom5(rom5, "IRON_ORE")\n'

# Patch 3: pages/3_Monitor_Abertura_Leilao.py
_pages3 = _glob.glob(str(ROOT / "pages" / "3_*.py"))
ARQ3 = Path(_pages3[0]) if _pages3 else ROOT / "pages" / "3_x.py"
P3_OLD = '    iron = _get_var_rom5(rom5, "IRON_ORE_2M")\n'
P3_NEW = '    iron = _get_var_rom5(rom5, "IRON_ORE")\n'

# Patch 4: pages/5_Ativos_Monitorados.py
_pages5 = _glob.glob(str(ROOT / "pages" / "5_*.py"))
ARQ5 = Path(_pages5[0]) if _pages5 else ROOT / "pages" / "5_x.py"
P5_OLD = '    "\U0001fab5 Commodities C\u00edclicas": ["IRON_ORE", "IRON_ORE_2M", "CRUDE_OIL", "GOLD"],\n'
P5_NEW = '    "\U0001fab5 Commodities C\u00edclicas": ["IRON_ORE", "CRUDE_OIL", "GOLD"],\n'

# Patch 5: v2/core/contracts/win_session.py
ARQ6 = ROOT / "v2" / "core" / "contracts" / "win_session.py"
P6_OLD = '    iron_ore_2m: SnapshotSimples = field(default_factory=SnapshotSimples)\n'
P6_NEW = ''

# Patch 6: v2/core/services/win_session_builder.py
ARQ7 = ROOT / "v2" / "core" / "services" / "win_session_builder.py"
P7_OLD = '            iron_ore_2m=_snap(ativos, "IRON_ORE_2M"),\n'
P7_NEW = ''

PATCHES = [
    ("analisar_rompimento_10h: linha IRON_ORE", ARQ1, P1_OLD, P1_NEW),
    ("pages/2: _get_var_rom5 IRON_ORE", ARQ2, P2_OLD, P2_NEW),
    ("pages/3: _get_var_rom5 IRON_ORE", ARQ3, P3_OLD, P3_NEW),
    ("pages/5: remove IRON_ORE_2M da lista", ARQ5, P5_OLD, P5_NEW),
    ("win_session: remove campo iron_ore_2m", ARQ6, P6_OLD, P6_NEW),
    ("win_session_builder: remove build iron_ore_2m", ARQ7, P7_OLD, P7_NEW),
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

    for nome, alvo, old, new in PATCHES:
        if not alvo.exists():
            faltando.append(f"{nome} (arquivo nao existe: {alvo})")
            continue
        conteudo = alvo.read_text(encoding="utf-8")
        if old not in conteudo:
            if new and new in conteudo:
                print(f"  [INFO] ja aplicado: {nome}")
                continue
            faltando.append(f"{nome} (ancora nao encontrada)")
            continue
        novo = conteudo.replace(old, new, 1)
        if not dry_run:
            bak = _backup(alvo)
            print(f"  [BACKUP] {bak.name}")
            alvo.write_text(novo, encoding="utf-8")
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
    for nome, alvo, old, new in PATCHES:
        if not alvo.exists():
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[SKIP] {alvo.name}: sem backup")
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