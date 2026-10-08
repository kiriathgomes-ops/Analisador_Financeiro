# -*- coding: utf-8 -*-
"""
fix59.py - Usa session_volume (liquidez do dia) no criterio "volume"

Contexto (05/10/2026):
    O coletor escolheu DI1F37 (jan/2037, contrato quase morto) como
    principal do DI1, em vez do DI1F27 (jan/2027, liquido). Causa:
    o criterio "volume" usa tick.volume (volume do ultimo negocio),
    que e ruido em ativos com negociacao esparsa.

    O MT5 expoe session_volume no symbol_info() - volume total do dia,
    6 ordens de magnitude maior. E o criterio correto.

Mudancas:
    A) _monta_info: captura session_volume alem de volume
    B) selecionar_contrato: criterio "volume" usa session_volume
       (fallback pra tick.volume se session_volume = 0)

Nota: WIN/WDO continuam usando criterio "expiracao" - nao sao afetados.

Uso:
    python fix59.py --dry-run
    python fix59.py
    python fix59.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Coletor_MT5_v2_2.py"

# --- Patch 1: _monta_info captura session_volume ---
P1_OLD = (
    '        tick = mt5.symbol_info_tick(nome)\n'
    '        if tick:\n'
    '            volume = float(getattr(tick, "volume", 0) or 0)\n'
    '            bid = float(getattr(tick, "bid", 0) or 0)\n'
    '            ask = float(getattr(tick, "ask", 0) or 0)\n'
    '            last = float(getattr(tick, "last", 0) or 0)\n'
    '        else:\n'
    '            volume = bid = ask = last = 0.0\n'
    '\n'
    '        return {\n'
    '            "nome": nome,\n'
    '            "simbolo": s,\n'
    '            "expiracao": data_expiracao,\n'
    '            "volume": volume,\n'
    '            "bid": bid,\n'
    '            "ask": ask,\n'
    '            "last": last,\n'
    '        }\n'
)
P1_NEW = (
    '        tick = mt5.symbol_info_tick(nome)\n'
    '        if tick:\n'
    '            volume = float(getattr(tick, "volume", 0) or 0)\n'
    '            bid = float(getattr(tick, "bid", 0) or 0)\n'
    '            ask = float(getattr(tick, "ask", 0) or 0)\n'
    '            last = float(getattr(tick, "last", 0) or 0)\n'
    '        else:\n'
    '            volume = bid = ask = last = 0.0\n'
    '\n'
    '        # fix59: session_volume = volume total do dia (liquidez real).\n'
    '        # Melhor que tick.volume para ativos com negociacao esparsa (DI1).\n'
    '        session_volume = float(getattr(s, "session_volume", 0) or 0)\n'
    '\n'
    '        return {\n'
    '            "nome": nome,\n'
    '            "simbolo": s,\n'
    '            "expiracao": data_expiracao,\n'
    '            "volume": volume,\n'
    '            "session_volume": session_volume,\n'
    '            "bid": bid,\n'
    '            "ask": ask,\n'
    '            "last": last,\n'
    '        }\n'
)

# --- Patch 2: selecionar_contrato usa session_volume ---
P2_OLD = (
    '    if criterio == "volume":\n'
    '        validos.sort(\n'
    '            key=lambda x: (\n'
    '                -x["volume"],\n'
    '                x["expiracao"].timestamp(),\n'
    '            )\n'
    '        )\n'
    '    else:\n'
    '        validos.sort(\n'
    '            key=lambda x: (\n'
    '                x["expiracao"].timestamp(),\n'
    '                -x["volume"],\n'
    '            )\n'
    '        )\n'
)
P2_NEW = (
    '    # fix59: usa session_volume (liquidez do dia) com fallback pra\n'
    '    # tick.volume. Para DI1, tick.volume e ruido (poucos negocios).\n'
    '    def _volume_efetivo(c):\n'
    '        return c.get("session_volume") or c["volume"]\n'
    '\n'
    '    if criterio == "volume":\n'
    '        validos.sort(\n'
    '            key=lambda x: (\n'
    '                -_volume_efetivo(x),\n'
    '                x["expiracao"].timestamp(),\n'
    '            )\n'
    '        )\n'
    '    else:\n'
    '        validos.sort(\n'
    '            key=lambda x: (\n'
    '                x["expiracao"].timestamp(),\n'
    '                -_volume_efetivo(x),\n'
    '            )\n'
    '        )\n'
)

PATCHES = [
    ("_monta_info captura session_volume", P1_OLD, P1_NEW),
    ("selecionar_contrato usa session_volume no criterio volume", P2_OLD, P2_NEW),
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
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []

    for nome, old, new in PATCHES:
        if old not in novo:
            if "fix59" in novo:
                print(f"  [INFO] ja aplicado: {nome}")
                continue
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {len(faltando)} patch(es) nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print("[INFO] nada mudou.")
        return 0

    if dry_run:
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"\n[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter():
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] nenhum backup.")
        return 1
    shutil.copy2(bak, ALVO)
    print(f"[REVERTER] {ALVO.name} restaurado de {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))