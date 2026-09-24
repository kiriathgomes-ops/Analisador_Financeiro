"""
fix42.py — Remove blocos redundantes da pagina SMC_Regras (por linhas)
"""

import glob
from datetime import datetime
from pathlib import Path
import shutil
import sys

alvos = glob.glob("pages/7.1_*.py")
if not alvos:
    print("[ERRO] pagina nao encontrada")
    sys.exit(1)
ALVO = Path(alvos[0])

BLOCO_A_INI = 125
BLOCO_A_FIM = 187
BLOCO_B_INI = 533
BLOCO_B_FIM = 562


def aplicar(dry_run: bool):
    linhas = ALVO.read_text(encoding="utf-8").splitlines(keepends=True)
    total_antes = len(linhas)

    l_a_ini = linhas[BLOCO_A_INI - 1].strip()
    l_a_fim = linhas[BLOCO_A_FIM - 1].strip()
    l_a_prox = linhas[BLOCO_A_FIM].strip()  # linha 188
    l_b_ini = linhas[BLOCO_B_INI - 1].strip()
    l_b_fim = linhas[BLOCO_B_FIM - 1].strip()
    l_b_prox = linhas[BLOCO_B_FIM].strip()  # linha 563

    print(f"Bloco A ini (L{BLOCO_A_INI}): {l_a_ini[:70]}")
    print(f"Bloco A fim (L{BLOCO_A_FIM}): {l_a_fim[:70]!r}")
    print(f"Bloco A prox (L{BLOCO_A_FIM+1}): {l_a_prox[:70]}")
    print(f"Bloco B ini (L{BLOCO_B_INI}): {l_b_ini[:70]}")
    print(f"Bloco B fim (L{BLOCO_B_FIM}): {l_b_fim[:70]!r}")
    print(f"Bloco B prox (L{BLOCO_B_FIM+1}): {l_b_prox[:70]}")

    # Check A: ini comeca com '# ===', fim vazio, prox comeca com '# ==='
    ok_a = l_a_ini.startswith("# ===") and l_a_fim == "" and l_a_prox.startswith("# ===")
    # Check B: idem
    ok_b = l_b_ini.startswith("# ===") and l_b_fim == "" and l_b_prox.startswith("# ===")

    if not ok_a:
        print("\n[ABORT] Bloco A nao bate")
        return 2
    if not ok_b:
        print("\n[ABORT] Bloco B nao bate")
        return 2

    parte1 = linhas[:BLOCO_A_INI - 1]
    parte2 = linhas[BLOCO_A_FIM:BLOCO_B_INI - 1]
    parte3 = linhas[BLOCO_B_FIM:]

    novo = "".join(parte1 + parte2 + parte3)
    total_depois = len(novo.splitlines())

    print(f"\nLinhas antes:  {total_antes}")
    print(f"Linhas depois: {total_depois}")
    print(f"Removidas:     {total_antes - total_depois}")

    if dry_run:
        print("\n[DRY-RUN] Nada salvo.")
        return 0

    bak = ALVO.with_suffix(ALVO.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(ALVO, bak)
    ALVO.write_text(novo, encoding="utf-8")
    print(f"\n[BACKUP] {bak.name}")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter():
    baks = sorted(ALVO.parent.glob(ALVO.name + ".bak_*"))
    if not baks:
        print("[ERRO] nenhum backup")
        return 1
    shutil.copy2(baks[-1], ALVO)
    print(f"[REVERTER] {ALVO.name} restaurado de {baks[-1].name}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))
