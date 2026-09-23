"""
fix31b.py — corrige fix31: usar CONFIG global em vez de 'config' inexistente

O fix31 tentou usar config.bias_janela dentro de detectar_bos_choch(),
mas essa funcao nao recebe config — o CONFIG e global no modulo.

Uso:
    python fix31b.py --dry-run
    python fix31b.py
    python fix31b.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

ANTIGO = '''        janela = eventos[-config.bias_janela:] if hasattr(config, "bias_janela") else eventos[-5:]
        votos_alta = sum(1 for e in janela if e.direcao == "ALTA")
        votos_baixa = sum(1 for e in janela if e.direcao == "BAIXA")
        margem = getattr(config, "bias_min_margem", 1)
'''

NOVO = '''        _janela_n = getattr(CONFIG, "bias_janela", 5)
        _margem = getattr(CONFIG, "bias_min_margem", 1)
        janela = eventos[-_janela_n:]
        votos_alta = sum(1 for e in janela if e.direcao == "ALTA")
        votos_baixa = sum(1 for e in janela if e.direcao == "BAIXA")
        margem = _margem
'''

PATCHES = [("usa CONFIG global em vez de config", ANTIGO, NOVO)]


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def aplicar(dry_run: bool) -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []
    for nome, old, new in PATCHES:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] padroes nao encontrados:")
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


def reverter() -> int:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())