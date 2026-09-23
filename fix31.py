"""
fix31.py — Motor_SMC_Regras.py: estabilidade direcional por maioria

Contexto:
    Hoje (23/09) o M1 flipou ALTA->BAIXA em 12 min, causando swing de
    30 pts no delta MTF (-40 -> -10). O bias vem de eventos[-1].direcao
    (ultimo evento), que flipa com o ultimo candle.

Fix:
    bias passa a ser decidido por MAIORIA dos ultimos N eventos de
    estrutura (BOS/CHoCH). Parametrizavel via ConfigSMC.bias_janela.
    Se empate, mantem o ultimo (comportamento atual como fallback).

Adiciona:
    - ConfigSMC.bias_janela: int = 5   (num. de eventos p/ maioria)
    - ConfigSMC.bias_min_margem: int = 1  (min. de votos de diferenca)

Uso:
    python fix31.py --dry-run
    python fix31.py
    python fix31.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

# 1) Adiciona 2 campos em ConfigSMC
CFG_ANTIGO = (
    "    ob_poc_dist_win: float = 300.0\n"
    "    ob_poc_dist_wdo: float = 30.0\n"
)

CFG_NOVO = '''    ob_poc_dist_win: float = 300.0
    ob_poc_dist_wdo: float = 30.0

    # Estabilidade direcional: bias por maioria dos ultimos N eventos
    bias_janela: int = 5
    bias_min_margem: int = 1  # diferenca minima entre votos ALTA/BAIXA
'''

# 2) Substitui a derivacao do bias em detectar_bos_choch
BIAS_ANTIGO = '''    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias
'''

BIAS_NOVO = '''    if eventos:
        # Estabilidade: bias por MAIORIA dos ultimos N eventos (fix31).
        # Se empate ou sem maioria clara, usa o ultimo (comportamento
        # historico). Reduz flip-flop em timeframes ruidosos (M1).
        janela = eventos[-config.bias_janela:] if hasattr(config, "bias_janela") else eventos[-5:]
        votos_alta = sum(1 for e in janela if e.direcao == "ALTA")
        votos_baixa = sum(1 for e in janela if e.direcao == "BAIXA")
        margem = getattr(config, "bias_min_margem", 1)

        if votos_alta >= votos_baixa + margem:
            bias = "ALTA"
        elif votos_baixa >= votos_alta + margem:
            bias = "BAIXA"
        else:
            # Sem maioria clara: mantem o ultimo evento
            bias = eventos[-1].direcao
    return eventos, bias
'''

PATCHES = [
    ("ConfigSMC ganha bias_janela + bias_min_margem", CFG_ANTIGO, CFG_NOVO),
    ("bias por maioria em detectar_bos_choch", BIAS_ANTIGO, BIAS_NOVO),
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