"""
fix33.py — V2: gate duplo de confianca (SMC ajustado + final ponderada)

Contexto:
    Hoje so o SMC ajustado (pos-MTF) passa pelo minimo 55%.
    A confianca FINAL (0.6*SMC + 0.4*NM) nao era testada — podia
    ficar abaixo do minimo e mesmo assim operar=True.

Mudanca:
    Adiciona CONFIANCA_MINIMA_FINAL = 45 no config (mais baixo que o
    do SMC, pra nao bloquear operacoes legitimas com MTF ativo).
    _verificar_confluencia checa esse minimo APOS calcular a final.

    Se confianca_final < CONFIANCA_MINIMA_FINAL:
        retorna NEUTRO (nao opera).

Uso:
    python fix33.py --dry-run
    python fix33.py
    python fix33.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_CONFIG = ROOT / "config.py"
ALVO_ORQ = ROOT / "v2" / "core" / "engines" / "v2_orchestrator.py"

# ---------------------------------------------------------------------------
# PATCH config.py
# ---------------------------------------------------------------------------
CFG_ANTIGO = '''# Modificador de confianca SMC por veredito multi-timeframe.
# Aplicado ANTES de comparar com CONFIANCA_MINIMA_CONFLUENCIA (55).
# Opcao 2: o MTF refina a confianca, nao sobrescreve a direcao.
MODIFICADOR_MTF = {'''

CFG_NOVO = '''# Modificador de confianca SMC por veredito multi-timeframe.
# Aplicado ANTES de comparar com CONFIANCA_MINIMA_CONFLUENCIA (55).
# Opcao 2: o MTF refina a confianca, nao sobrescreve a direcao.
#
# CONFIANCA_MINIMA_FINAL: gate adicional sobre a confianca ponderada
# (0.6*SMC_ajustado + 0.4*NOVO_MOTOR). Mais baixo que o gate do SMC
# para nao bloquear operacoes legitimas quando o MTF derruba o SMC.
CONFIANCA_MINIMA_FINAL = 45.0

MODIFICADOR_MTF = {'''

PATCHES_CONFIG = [
    ("adiciona CONFIANCA_MINIMA_FINAL = 45", CFG_ANTIGO, CFG_NOVO),
]

# ---------------------------------------------------------------------------
# PATCH v2_orchestrator.py
# ---------------------------------------------------------------------------

# 1) Import
ORQ_IMP_ANTIGO = '''from config import (
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_SMC_REGRAS,
    FILE_SMC_MTF,
    MODIFICADOR_MTF,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_NOTICIAS_IMPACTO,
    HISTORICO_DECISOES_V2_DIR,
)
'''

ORQ_IMP_NOVO = '''from config import (
    FILE_DECISAO_V2,
    FILE_UNIFICADO,
    FILE_SMC_REGRAS,
    FILE_SMC_MTF,
    MODIFICADOR_MTF,
    CONFIANCA_MINIMA_FINAL,
    FILE_ESTIMATIVA_ABERTURA,
    FILE_NOTICIAS_IMPACTO,
    HISTORICO_DECISOES_V2_DIR,
)
'''

# 2) Gate apos calcular a confianca_final
ORQ_GATE_ANTIGO = '''        if smc_dir == nm_dir and nm_dir != "NEUTRO":
            confianca_final = (smc_conf * PESO_SMC) + (nm_conf * PESO_NOVO_MOTOR)
            confianca_final = round(min(100.0, confianca_final), 1)
            motivos.append(f"✅ Confluência confirmada em {smc_dir}")
            return True, smc_dir, smc_dir, confianca_final, motivos, riscos
'''

ORQ_GATE_NOVO = '''        if smc_dir == nm_dir and nm_dir != "NEUTRO":
            confianca_final = (smc_conf * PESO_SMC) + (nm_conf * PESO_NOVO_MOTOR)
            confianca_final = round(min(100.0, confianca_final), 1)

            # Gate adicional: confianca FINAL tambem precisa passar o minimo.
            # Com o MTF ativo (pode derrubar SMC em ate -40), o minimo final
            # e mais baixo (CONFIANCA_MINIMA_FINAL=45) para nao bloquear
            # operacoes legitimas que ja passaram no gate do SMC.
            if confianca_final < CONFIANCA_MINIMA_FINAL:
                motivos.append(
                    f"⚠️ Confiança final {confianca_final:.1f}% < "
                    f"mínimo {CONFIANCA_MINIMA_FINAL:.0f}% — não opera"
                )
                return False, "NEUTRO", None, confianca_final, motivos, riscos

            motivos.append(f"✅ Confluência confirmada em {smc_dir}")
            return True, smc_dir, smc_dir, confianca_final, motivos, riscos
'''

PATCHES_ORQ = [
    ("importa CONFIANCA_MINIMA_FINAL", ORQ_IMP_ANTIGO, ORQ_IMP_NOVO),
    ("gate adicional sobre confianca_final", ORQ_GATE_ANTIGO, ORQ_GATE_NOVO),
]

# ---------------------------------------------------------------------------


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
    r1 = _aplicar(ALVO_CONFIG, PATCHES_CONFIG, dry_run)

    print(f"\n[ALVO 2] {ALVO_ORQ.name}")
    r2 = _aplicar(ALVO_ORQ, PATCHES_ORQ, dry_run)

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] fix33 aplicado.")
        return 0
    return max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_CONFIG, ALVO_ORQ):
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