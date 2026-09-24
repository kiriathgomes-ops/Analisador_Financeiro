"""
fix43.py — Corrige calculo de confianca do motor SMC

Problemas corrigidos:
    1. Eventos duplicados: o mesmo candle pode gerar 2 BOS no mesmo
       timestamp. Dedup por (idx, tipo, direcao) em detectar_bos_choch.

    2. Coerencia direcional: bos/choch contavam mesmo se apontassem
       direcao OPOSTA ao bias. Ex: bias=ALTA, BOS BAIXA somava 20 pts.

    3. Debug: adiciona _debug_confianca no JSON pra ver o breakdown
       dos 6 criterios a cada run.

Impacto esperado:
    - M5 com pouca estrutura deixa de bater 100%
    - Bias coerente vale mais que eventos opostos

Uso:
    python fix43.py --dry-run
    python fix43.py
    python fix43.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

# --- PATCH 1: dedup em detectar_bos_choch ---
DEDUP_ANTIGO = """    if eventos:
        # Fix38: revertido ao comportamento original (fix31 sem evidencia
        # estatistica de ganho). O bias segue o ultimo evento de estrutura.
        # ConfigSMC.bias_janela/bias_min_margem ficam disponiveis caso
        # a estrategia seja revisitada com mais dados.
        bias = eventos[-1].direcao
    return eventos, bias
"""

DEDUP_NOVO = """    # Fix43: dedup por (idx, tipo, direcao). O mesmo candle pode
    # romper multiplos swings ao mesmo tempo e gerar eventos duplicados
    # no mesmo timestamp — isso inflava contagens e confianca.
    if eventos:
        vistos = set()
        unicos = []
        for e in eventos:
            chave = (e.idx, e.tipo, e.direcao)
            if chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(e)
        eventos = unicos

    if eventos:
        bias = eventos[-1].direcao
    return eventos, bias
"""

# --- PATCH 2: coerencia direcional em analisar_smc ---
BOS_ANTIGO = """    bos = any(e.tipo == "BOS" for e in eventos[-3:])
    choch = any(e.tipo == "CHOCH" for e in eventos[-3:])
"""

BOS_NOVO = """    # Fix43: BOS/CHoCH so contam se apontarem na direcao do bias.
    # Sem isso, um BOS contra-tendencia somava pontos indevidamente.
    _bias_dirs = {"ALTA", "BAIXA"}
    if bias in _bias_dirs:
        bos = any(e.tipo == "BOS" and e.direcao == bias for e in eventos[-3:])
        choch = any(e.tipo == "CHOCH" and e.direcao == bias for e in eventos[-3:])
    else:
        bos = any(e.tipo == "BOS" for e in eventos[-3:])
        choch = any(e.tipo == "CHOCH" for e in eventos[-3:])
"""

# --- PATCH 3: debug no retorno do analisar_smc ---
RET_ANTIGO = """        "metadados": {
            "n_candles": len(candles),
            "n_swings": len(swings),
            "n_fvgs_abertos": len(fvgs_abertos),
            "n_obs": len(obs),
            "filtro_volume_real_aplicado": True,
            "versao_motor": "2.1",
            "config": asdict(config),
        },
"""

RET_NOVO = """        "metadados": {
            "n_candles": len(candles),
            "n_swings": len(swings),
            "n_fvgs_abertos": len(fvgs_abertos),
            "n_obs": len(obs),
            "filtro_volume_real_aplicado": True,
            "versao_motor": "2.1",
            "config": asdict(config),
            # Fix43: breakdown dos 6 criterios de confianca
            "_debug_confianca": {
                "bias_ativo": bias in ("ALTA", "BAIXA"),
                "bos_ativo": bos,
                "choch_ativo": choch,
                "fvg_ativo": bool(fvgs_abertos),
                "ob_ativo": bool(obs),
                "ob_confluente_ativo": ob_confluente,
                "total_eventos": len(eventos),
                "ultimos_3_eventos": [
                    {"tipo": e.tipo, "direcao": e.direcao, "time": e.time}
                    for e in eventos[-3:]
                ],
            },
        },
"""

PATCHES = [
    ("dedup de eventos em detectar_bos_choch", DEDUP_ANTIGO, DEDUP_NOVO),
    ("bos/choch com coerencia direcional", BOS_ANTIGO, BOS_NOVO),
    ("adiciona _debug_confianca no JSON", RET_ANTIGO, RET_NOVO),
]


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
