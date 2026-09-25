"""
fix45.py — Restaura variaveis vies/confianca/preco_atual apos fix42

O fix42 removeu o bloco KPI que definia essas 3 variaveis. Mas elas
continuam sendo usadas em blocos posteriores (distancias, niveis
institucionais). Este fix as redefine logo apos o carregamento
dos dados SMC.

Uso:
    python fix45.py --dry-run
    python fix45.py
    python fix45.py --reverter
"""

import argparse
import glob
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(".").resolve()
candidatos = glob.glob("pages/7.1_*.py")
if not candidatos:
    print("[ERRO] pagina nao encontrada")
    sys.exit(1)
ALVO = Path(candidatos[0])

ANCORA = 'dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)'

NOVO = '''dados_smc = carregar_json_defensivo(FILE_SMC_REGRAS)

# fix45: variaveis de conveniencia (removidas pelo fix42)
vies = dados_smc.get("bias_direcional", "LATERAL")
confianca = dados_smc.get("confianca_visual", 0)
preco_atual = dados_smc.get("preco_atual", 0.0)'''


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

    if "vies = dados_smc.get" in conteudo and "# fix45" in conteudo:
        print("[INFO] ja aplicado.")
        return 0

    if ANCORA not in conteudo:
        print("[ABORT] ancora nao encontrada:")
        print(f"  esperado: {ANCORA}")
        return 2

    novo = conteudo.replace(ANCORA, NOVO, 1)

    if dry_run:
        print("  [PATCH OK] restaura vies/confianca/preco_atual")
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print("  [PATCH OK] restaura vies/confianca/preco_atual")
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))
