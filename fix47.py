# -*- coding: utf-8 -*-
"""
fix47.py - Corrige timezone do MT5 (wall-clock BRT em vez de UTC)

Problema:
    O MT5 da Genial devolve o campo `time` como wall-clock do servidor
    (que ja esta em BRT). O codigo atual interpreta como UTC real e
    subtrai 3h, resultando em timestamps 3h atrasados.

    Evidencia: ultimo tick de sexta (25/09) veio como 15:31 no cache,
    mas o horario real era 18:31 BRT.

Fix:
    Em vez de `.astimezone(BRT)` (que subtrai 3h), usar `.replace(tzinfo=BRT)`
    (que preserva o valor wall-clock como BRT).

Alvos (3 ocorrencias):
    - cache_candles.py:42
    - Motor_SMC_Regras.py:1302
    - Rodar_SMC_Regras.py:124

Uso:
    python fix47.py --dry-run
    python fix47.py
    python fix47.py --reverter
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ALVOS = [
    ROOT / "cache_candles.py",
    ROOT / "Motor_SMC_Regras.py",
    ROOT / "Rodar_SMC_Regras.py",
]

# Regex que casa: datetime.fromtimestamp(QUALQUER["time"], tz=timezone.utc).astimezone(BRT)
PADRAO = re.compile(
    r'(datetime\.fromtimestamp\((\w+)\["time"\],\s*tz=timezone\.utc\))\.astimezone\(BRT\)'
)

# Substituicao: preserva o miolo, troca .astimezone(BRT) por .replace(tzinfo=BRT)
def _substituir(match):
    return f'{match.group(1)}.replace(tzinfo=BRT)'


def _backup(p):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def aplicar(dry_run):
    total_mudancas = 0
    arquivos_modificados = []

    for alvo in ALVOS:
        if not alvo.exists():
            print(f"  [SKIP] {alvo.name} nao existe")
            continue

        conteudo = alvo.read_text(encoding="utf-8")
        novo, n = PADRAO.subn(_substituir, conteudo)

        if n == 0:
            if ".replace(tzinfo=BRT)" in conteudo:
                print(f"  [INFO] {alvo.name}: ja aplicado")
            else:
                print(f"  [SKIP] {alvo.name}: padrao nao encontrado")
            continue

        print(f"  [PATCH] {alvo.name}: {n} ocorrencia(s)")

        if not dry_run:
            bak = _backup(alvo)
            print(f"          [BACKUP] {bak.name}")
            alvo.write_text(novo, encoding="utf-8")
            print(f"          [OK] atualizado")

        total_mudancas += n
        arquivos_modificados.append(alvo.name)

    print()
    print(f"Total de mudancas: {total_mudancas}")
    print(f"Arquivos: {arquivos_modificados}")

    if dry_run:
        print("\n[DRY-RUN] nada salvo.")
    return 0


def reverter():
    for alvo in ALVOS:
        if not alvo.exists():
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"  [SKIP] {alvo.name}: sem backup")
            continue
        shutil.copy2(bak, alvo)
        print(f"  [REVERTER] {alvo.name} <- {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))
