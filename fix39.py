"""
fix39.py — Remove codigo morto: bias_janela / bias_min_margem do ConfigSMC

Contexto:
    fix31 adicionou bias_janela e bias_min_margem a dataclass ConfigSMC.
    fix38 reverteu a logica de maioria em detectar_bos_choch, mas os
    campos ficaram na dataclass sem uso.

Este fix remove os dois campos.

Uso:
    python fix39.py --dry-run
    python fix39.py
    python fix39.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

ANTIGO = '''    # Estabilidade direcional: bias por maioria dos ultimos N eventos
    bias_janela: int = 5
    bias_min_margem: int = 1  # diferenca minima entre votos ALTA/BAIXA
'''

NOVO = ""


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

    if ANTIGO not in conteudo:
        if "bias_janela" not in conteudo and "bias_min_margem" not in conteudo:
            print("[INFO] Campos ja removidos.")
            return 0
        print("[ABORT] Bloco nao encontrado — verificar manualmente.")
        return 2

    novo = conteudo.replace(ANTIGO, NOVO, 1)

    if dry_run:
        print("  [PATCH OK] remove bias_janela + bias_min_margem")
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print("  [PATCH OK] remove bias_janela + bias_min_margem")
    print(f"  [BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"  [OK] {ALVO.name} atualizado.")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())