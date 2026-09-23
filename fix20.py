"""
fix20.py — Coletor_MT5_v2_2.py

Problema:
    selecionar_contrato() agora ordena sempre por expiracao (front-month).
    Isso acerta WIN/WDO, mas erra DI1 — no DI a liquidez nao esta no
    vencimento mais proximo (V26), e sim em jan/ano seguinte (F27).

Fix:
    Adiciona campo "criterio" por ativo em ATIVOS:
        WIN/WDO -> "expiracao" (front-month)
        DI1     -> "volume"    (maior liquidez)
    Ajusta selecionar_contrato() p/ ordenar conforme criterio.
    Passa criterio da config p/ selecionar_contrato em coletar_ativo().

Uso:
    python fix20.py --dry-run
    python fix20.py
    python fix20.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Coletor_MT5_v2_2.py"

# ---------------------------------------------------------------------------
# PATCHES
# ---------------------------------------------------------------------------

PATCH_ATIVOS_ANTIGO = '''ATIVOS = {
    "WIN": {
        "prefixo": "WIN",
        "descricao": "Mini Índice B3"
    },

    "WDO": {
        "prefixo": "WDO",
        "descricao": "Mini Dólar B3"
    },

    "DI1": {
        "prefixo": "DI1",
        "descricao": "DI Futuro B3"
    }
}'''

PATCH_ATIVOS_NOVO = '''ATIVOS = {
    "WIN": {
        "prefixo": "WIN",
        "descricao": "Mini Índice B3",
        # "expiracao" = front-month (menor vencimento futuro) — correto p/ WIN/WDO
        # "volume"    = maior liquidez do dia — correto p/ DI1
        "criterio": "expiracao"
    },

    "WDO": {
        "prefixo": "WDO",
        "descricao": "Mini Dólar B3",
        "criterio": "expiracao"
    },

    "DI1": {
        "prefixo": "DI1",
        "descricao": "DI Futuro B3",
        "criterio": "volume"
    }
}'''

PATCH_ASSINATURA_ANTIGO = '''def selecionar_contrato(prefixo):

    contratos = obter_contratos(prefixo)'''

PATCH_ASSINATURA_NOVO = '''def selecionar_contrato(prefixo, criterio="expiracao"):

    contratos = obter_contratos(prefixo)'''

PATCH_SORT_ANTIGO = '''    # Contrato vigente B3 = front-month (menor expiração futura
    # com mercado ativo). Volume do tick é ruído (1 tick a mais
    # num contrato já em rolagem não significa liquidez).
    # Ordena: expiração ascendente → volume descendente (desempate).
    validos.sort(
        key=lambda x: (
            x["expiracao"].timestamp(),
            -x["volume"],
        )
    )'''

PATCH_SORT_NOVO = '''    # Criterio por ativo:
    #   WIN/WDO → front-month (menor expiracao futura), volume desempata.
    #   DI1     → maior volume (liquidez nao esta no vencimento mais
    #             proximo; pula p/ jan. do ano seguinte).
    if criterio == "volume":
        validos.sort(
            key=lambda x: (
                -x["volume"],
                x["expiracao"].timestamp(),
            )
        )
    else:
        validos.sort(
            key=lambda x: (
                x["expiracao"].timestamp(),
                -x["volume"],
            )
        )'''

PATCH_CHAMADA_ANTIGO = '''    principal, contratos = selecionar_contrato(prefixo)'''

PATCH_CHAMADA_NOVO = '''    criterio = configuracao.get("criterio", "expiracao")
    principal, contratos = selecionar_contrato(prefixo, criterio=criterio)'''

PATCHES = [
    ("adiciona criterio em ATIVOS", PATCH_ATIVOS_ANTIGO, PATCH_ATIVOS_NOVO),
    ("assinatura selecionar_contrato aceita criterio", PATCH_ASSINATURA_ANTIGO, PATCH_ASSINATURA_NOVO),
    ("sort respeita criterio (expiracao vs volume)", PATCH_SORT_ANTIGO, PATCH_SORT_NOVO),
    ("coletar_ativo passa criterio da config", PATCH_CHAMADA_ANTIGO, PATCH_CHAMADA_NOVO),
]

IGNORAR = {"fix20.py"}

# ---------------------------------------------------------------------------


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
        print(f"[PATCH OK] {nome}")

    if faltando:
        print("\n[ABORT] Padroes nao encontrados:")
        for f in faltando:
            print(f"  - {f}")
        print("\nNada foi salvo. Confira se o arquivo bate com o esperado.")
        return 2

    if novo == conteudo:
        print("[INFO] Nada mudou.")
        return 0

    if dry_run:
        print("\n[DRY-RUN] Nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"[BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"[OK] {ALVO.name} atualizado.")
    return 0


def reverter() -> int:
    if not ALVO.exists():
        print(f"[ERRO] {ALVO.name} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] Nenhum backup encontrado.")
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