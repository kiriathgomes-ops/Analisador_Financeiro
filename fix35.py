"""
fix35.py — Motor_SMC_Regras.py: detectar_bos_choch aceita config

Refatoracao limpa que resolve a causa raiz do crash do fix31:
    - Assinatura passa a aceitar config explicitamente
    - Uso interno troca CONFIG global por config local
    - Call site em analisar_smc passa config

Uso:
    python fix35.py --dry-run
    python fix35.py
    python fix35.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

SIG_ANTIGO = '''def detectar_bos_choch(
    candles: List[Candle], swings: List[Swing]
) -> Tuple[List[EventoEstrutura], str]:'''

SIG_NOVO = '''def detectar_bos_choch(
    candles: List[Candle],
    swings: List[Swing],
    config: ConfigSMC = CONFIG,
) -> Tuple[List[EventoEstrutura], str]:'''

CFG_ANTIGO = '''        _janela_n = getattr(CONFIG, "bias_janela", 5)
        _margem = getattr(CONFIG, "bias_min_margem", 1)'''

CFG_NOVO = '''        _janela_n = getattr(config, "bias_janela", 5)
        _margem = getattr(config, "bias_min_margem", 1)'''

CALL_ANTIGO = '    eventos, bias = detectar_bos_choch(candles, swings)\n'
CALL_NOVO = '    eventos, bias = detectar_bos_choch(candles, swings, config)\n'

PATCHES = [
    ("assinatura aceita config", SIG_ANTIGO, SIG_NOVO),
    ("usa config local em vez de CONFIG global", CFG_ANTIGO, CFG_NOVO),
    ("call site passa config", CALL_ANTIGO, CALL_NOVO),
]


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