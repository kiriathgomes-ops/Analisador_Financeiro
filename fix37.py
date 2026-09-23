"""
fix37.py — B) PARCIAL no MODIFICADOR_MTF + C) clareza no alinhamento

B) config.py:
   Adiciona "PARCIAL": -15 no MODIFICADOR_MTF. Quando o MTF tem so
   1 ou 2 TFs disponiveis, a confianca do SMC e reduzida.

C) Rodar_SMC_Regras.py:
   No veredito PARCIAL, o campo "alinhamento" era "N/N" (ambiguo —
   parecia dizer "concordam" quando na verdade era so "N direcoes
   definidas"). Substitui por:
       - PARCIAL_ALINHADO      (2+ TFs concordam)
       - PARCIAL_DIVERGENTE    (2+ TFs divergem)
       - PARCIAL_INDEFINIDO    (1 TF so, ou nenhuma direcao)
   Adiciona tambem campo explicito "direcoes_concordam": bool.

Uso:
    python fix37.py --dry-run
    python fix37.py
    python fix37.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_CONFIG = ROOT / "config.py"
ALVO_RODAR = ROOT / "Rodar_SMC_Regras.py"

# --- PATCH config.py: B ---
CFG_ANTIGO = '''MODIFICADOR_MTF = {
    "ALINHADO_FORTE": +10,
    "PULLBACK": 0,
    "REVERSAO_MICRO_MEDIO": -10,
    "CONFLITO_MACRO": -25,
    "DIVERGENTE": -40,
    "NEUTRO": -15,
}
'''

CFG_NOVO = '''MODIFICADOR_MTF = {
    "ALINHADO_FORTE": +10,
    "PULLBACK": 0,
    "REVERSAO_MICRO_MEDIO": -10,
    "CONFLITO_MACRO": -25,
    "DIVERGENTE": -40,
    "NEUTRO": -15,
    "PARCIAL": -15,   # apenas 1-2 TFs disponiveis (analise incompleta)
}
'''

PATCHES_CFG = [("adiciona PARCIAL=-15 no MODIFICADOR_MTF", CFG_ANTIGO, CFG_NOVO)]

# --- PATCH Rodar_SMC_Regras.py: C ---
RODAR_ANTIGO = '''    elif n_tfs < 3:
        # Parcial: sem todas as pernas, comportamento conservador
        veredito, alinhamento, racional = (
            "PARCIAL", f"{n_dir}/{n_tfs}",
            f"Parcial: apenas {', '.join(tfs_presentes)} disponiveis. "
            f"Direcao = {direcoes[0] if direcoes else 'NEUTRO'}.",
        )
'''

RODAR_NOVO = '''    elif n_tfs < 3:
        # Parcial: sem todas as pernas. Alinhamento passa a refletir
        # se as direcoes disponiveis concordam ou divergem (fix37c).
        _dirs_unicas = set(direcoes)
        if len(_dirs_unicas) >= 2:
            _alinh = "PARCIAL_DIVERGENTE"
        elif len(_dirs_unicas) == 1:
            _alinh = "PARCIAL_ALINHADO"
        else:
            _alinh = "PARCIAL_INDEFINIDO"
        veredito, alinhamento, racional = (
            "PARCIAL", _alinh,
            f"Parcial: apenas {', '.join(tfs_presentes)} disponiveis. "
            f"Direcao = {direcoes[0] if direcoes else 'NEUTRO'}.",
        )
'''

# --- PATCH retorno: adiciona direcoes_concordam ---
RET_ANTIGO = '''        "timeframes_disponiveis": tfs_presentes,
        "n_tfs_disponiveis": n_tfs,
        "parcial": parcial,
    }
'''

RET_NOVO = '''        "timeframes_disponiveis": tfs_presentes,
        "n_tfs_disponiveis": n_tfs,
        "parcial": parcial,
        "direcoes_concordam": (len(set(direcoes)) == 1) if len(direcoes) >= 2 else None,
    }
'''

PATCHES_RODAR = [
    ("PARCIAL reflete divergencia no alinhamento", RODAR_ANTIGO, RODAR_NOVO),
    ("retorno ganha direcoes_concordam", RET_ANTIGO, RET_NOVO),
]


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar(alvo: Path, patches, dry_run: bool) -> int:
    if not alvo.exists():
        print(f"[ERRO] {alvo} nao encontrado")
        return 1

    conteudo = alvo.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []
    for nome, old, new in patches:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {alvo.name} — padroes nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print(f"  [INFO] {alvo.name}: nada mudou.")
        return 0

    if dry_run:
        print(f"  [DRY-RUN] {alvo.name}: nao salvo.")
        return 0

    bak = _backup(alvo)
    print(f"  [BACKUP] {bak.name}")
    alvo.write_text(novo, encoding="utf-8")
    print(f"  [OK] {alvo.name} atualizado.")
    return 0


def aplicar(dry_run: bool) -> int:
    print(f"\n[ALVO 1] {ALVO_CONFIG.name}")
    r1 = _aplicar(ALVO_CONFIG, PATCHES_CFG, dry_run)

    print(f"\n[ALVO 2] {ALVO_RODAR.name}")
    r2 = _aplicar(ALVO_RODAR, PATCHES_RODAR, dry_run)

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] fix37 aplicado.")
        return 0
    return max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_CONFIG, ALVO_RODAR):
        if not alvo.exists():
            print(f"[ERRO] {alvo.name} nao encontrado.")
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[ERRO] {alvo.name}: nenhum backup.")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} restaurado de {bak.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())