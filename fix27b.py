"""
fix27b.py — Rodar_SMC_Regras.py: opcao C para CONFLITO_MACRO

Contexto (rodada real de 23/09 11:45):
    M15=ALTA(80%)  M5=BAIXA(85%)  M1=BAIXA(75%)
    Veredito atual: CONFLITO_MACRO -> "Nao operar contra M15"

Mudanca (opcao C - dar mais peso a micro+medio):
    Quando micro e medio concordam contra o macro E a soma das
    confiancas deles >= confianca do M15 * 1.8, muda pra:
        veredito = REVERSAO_MICRO_MEDIO
        direcao_dominante = direcao do M5/M1
    Senao, mantem CONFLITO_MACRO (conservador).

    Tambem expoe dois campos extras no payload de confluencia:
        confianca_micro_medio_soma
        limiar_reversao

Uso:
    python fix27b.py --dry-run
    python fix27b.py
    python fix27b.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Rodar_SMC_Regras.py"

# ---------------------------------------------------------------------------
# PATCH 1: bloco do veredito CONFLITO_MACRO
# ---------------------------------------------------------------------------
P_BLOCO_ANTIGO = (
    '    elif b15 != b5 and b5 == b1 and b5 in ("ALTA", "BAIXA"):\n'
    '        veredito, alinhamento, racional = (\n'
    '            "CONFLITO_MACRO", "MICRO_ALINHADO_CONTRA_MACRO",\n'
    '            f"Micro e médio em {b5}, macro em {b15}. Nao operar contra M15.",\n'
    '        )\n'
)

P_BLOCO_NOVO = '''    elif b15 != b5 and b5 == b1 and b5 in ("ALTA", "BAIXA"):
        # Opcao C: micro+medio contra macro.
        # Se a soma das confiancas do micro+medio supera o macro por um
        # fator (1.8), considera possivel reversao em curso.
        soma_micro_medio = c5 + c1
        limiar_reversao = c15 * 1.8
        if soma_micro_medio >= limiar_reversao:
            veredito, alinhamento, racional = (
                "REVERSAO_MICRO_MEDIO", "MICRO_MEDIO_CONTRA_MACRO",
                f"Micro ({b1}, {c1}%) e medio ({b5}, {c5}%) contra macro "
                f"{b15} ({c15}%). Possivel reversao em curso.",
            )
        else:
            veredito, alinhamento, racional = (
                "CONFLITO_MACRO", "MICRO_ALINHADO_CONTRA_MACRO",
                f"Micro e médio em {b5}, macro em {b15}. Nao operar contra M15.",
            )
'''

# ---------------------------------------------------------------------------
# PATCH 2: direcao_dominante considera o novo veredito
# ---------------------------------------------------------------------------
P_DIR_ANTIGO = (
    "    direcao_dom = b15 if b15 in (\"ALTA\", \"BAIXA\") else (b5 if b5 in (\"ALTA\", \"BAIXA\") else b1)\n"
)

P_DIR_NOVO = (
    "    if veredito == \"REVERSAO_MICRO_MEDIO\":\n"
    "        direcao_dom = b5  # micro+medio mandam no cenario de reversao\n"
    "    elif b15 in (\"ALTA\", \"BAIXA\"):\n"
    "        direcao_dom = b15\n"
    "    elif b5 in (\"ALTA\", \"BAIXA\"):\n"
    "        direcao_dom = b5\n"
    "    else:\n"
    "        direcao_dom = b1\n"
)

# ---------------------------------------------------------------------------
# PATCH 3: expor campos de debug no retorno
# ---------------------------------------------------------------------------
P_RET_ANTIGO = (
    '    return {\n'
    '        "bias_m15": b15,\n'
    '        "bias_m5": b5,\n'
    '        "bias_m1": b1,\n'
    '        "confianca_m15": c15,\n'
    '        "confianca_m5": c5,\n'
    '        "confianca_m1": c1,\n'
    '        "veredito_mtf": veredito,\n'
)

P_RET_NOVO = '''    # Campos auxiliares (apenas para debug/auditoria)
    try:
        soma_micro_medio_dbg = c5 + c1
        limiar_reversao_dbg = round(c15 * 1.8, 1)
    except NameError:
        soma_micro_medio_dbg = None
        limiar_reversao_dbg = None

    return {
        "bias_m15": b15,
        "bias_m5": b5,
        "bias_m1": b1,
        "confianca_m15": c15,
        "confianca_m5": c5,
        "confianca_m1": c1,
        "confianca_micro_medio_soma": soma_micro_medio_dbg,
        "limiar_reversao": limiar_reversao_dbg,
        "veredito_mtf": veredito,
'''

PATCHES = [
    ("bloco CONFLITO_MACRO -> decide reversao", P_BLOCO_ANTIGO, P_BLOCO_NOVO),
    ("direcao_dominante considera REVERSAO_MICRO_MEDIO", P_DIR_ANTIGO, P_DIR_NOVO),
    ("expõe campos confianca_micro_medio_soma e limiar_reversao", P_RET_ANTIGO, P_RET_NOVO),
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
        print(f"[ERRO] {ALVO.name} nao encontrado em {ROOT}")
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
        print("\n[ABORT] padroes nao encontrados:")
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