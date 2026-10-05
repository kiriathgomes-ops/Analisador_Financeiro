# -*- coding: utf-8 -*-
"""
fix57.py - Instrumenta orquestrador V2 com dados de confluencia

Objetivo:
    Gravar no Decisao_V2.json os componentes que entram no calculo da
    confianca (SMC bruto, delta MTF, SMC ajustado, NM, pesos, gates).
    Viabiliza backtest contrafactual dos pesos 0.60/0.40.

Estrategia:
    Nao altera assinatura nem retorno de _verificar_confluencia.
    Guarda os componentes em self._debug_confluencia durante a execucao,
    e o payload final le desse atributo. Patch 100% aditivo.

Mudancas (5 patches):
    1. __init__: inicializa self._debug_confluencia = {}
    2. _verificar_confluencia: inicializa debug apos calcular smc_conf
    3. _verificar_confluencia: guarda nm_conf apos ler do novo_motor
    4. _verificar_confluencia: guarda confianca_final no branch de sucesso
    5. payload_decisao: adiciona bloco "confluencia" em metadados

Uso:
    python fix57.py --dry-run
    python fix57.py
    python fix57.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "v2" / "core" / "engines" / "v2_orchestrator.py"

# --- Patch 1: __init__ ganha atributo ---
P1_OLD = (
    '    def __init__(self):\n'
    '        self.timestamp_inicio = time.time()\n'
    '        self.erros_acumulados = []\n'
)
P1_NEW = (
    '    def __init__(self):\n'
    '        self.timestamp_inicio = time.time()\n'
    '        self.erros_acumulados = []\n'
    '        # fix57: componentes da confluencia (debug/backtest)\n'
    '        self._debug_confluencia = {}\n'
)

# --- Patch 2: inicializa debug apos calcular smc_conf ---
P2_OLD = (
    '        smc_conf = max(0.0, min(100.0, smc_conf_bruta + _delta_mtf))\n'
)
P2_NEW = (
    '        smc_conf = max(0.0, min(100.0, smc_conf_bruta + _delta_mtf))\n'
    '\n'
    '        # fix57: inicializa debug da confluencia (preenchido adiante)\n'
    '        self._debug_confluencia = {\n'
    '            "smc_conf_bruto": float(smc_conf_bruta),\n'
    '            "mtf_veredito": smc.get("veredito_mtf"),\n'
    '            "mtf_delta": float(_delta_mtf),\n'
    '            "smc_conf_ajustado": float(smc_conf),\n'
    '            "nm_conf": None,\n'
    '            "peso_smc": float(PESO_SMC),\n'
    '            "peso_nm": float(PESO_NOVO_MOTOR),\n'
    '            "confianca_final": None,\n'
    '            "passou_gate_confluencia": (\n'
    '                smc_conf >= CONFIANCA_MINIMA_CONFLUENCIA\n'
    '            ),\n'
    '            "passou_gate_final": False,\n'
    '        }\n'
)

# --- Patch 3: guarda nm_conf ---
P3_OLD = (
    '        nm_conf = novo_motor["confianca"]\n'
)
P3_NEW = (
    '        nm_conf = novo_motor["confianca"]\n'
    '        # fix57: guarda nm_conf pro payload\n'
    '        self._debug_confluencia["nm_conf"] = float(nm_conf)\n'
)

# --- Patch 4: guarda confianca_final ---
P4_OLD = (
    '            confianca_final = (smc_conf * PESO_SMC) + (nm_conf * PESO_NOVO_MOTOR)\n'
    '            confianca_final = round(min(100.0, confianca_final), 1)\n'
)
P4_NEW = (
    '            confianca_final = (smc_conf * PESO_SMC) + (nm_conf * PESO_NOVO_MOTOR)\n'
    '            confianca_final = round(min(100.0, confianca_final), 1)\n'
    '            # fix57: guarda confianca_final e gate\n'
    '            self._debug_confluencia["confianca_final"] = float(confianca_final)\n'
    '            self._debug_confluencia["passou_gate_final"] = (\n'
    '                confianca_final >= CONFIANCA_MINIMA_FINAL\n'
    '            )\n'
)

# --- Patch 5: payload ganha bloco confluencia ---
P5_OLD = (
    '                    "novo_motor": novo_motor or {},\n'
    '                    "precificacao_teorica": {\n'
)
P5_NEW = (
    '                    "novo_motor": novo_motor or {},\n'
    '                    # fix57: componentes da confluencia (backtest)\n'
    '                    "confluencia": getattr(self, "_debug_confluencia", {}),\n'
    '                    "precificacao_teorica": {\n'
)

PATCHES = [
    ("__init__ inicializa _debug_confluencia", P1_OLD, P1_NEW),
    ("_verificar_confluencia inicializa debug", P2_OLD, P2_NEW),
    ("_verificar_confluencia guarda nm_conf", P3_OLD, P3_NEW),
    ("_verificar_confluencia guarda confianca_final", P4_OLD, P4_NEW),
    ("payload adiciona bloco confluencia", P5_OLD, P5_NEW),
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
        print(f"[ERRO] {ALVO} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []

    for nome, old, new in PATCHES:
        if old not in novo:
            if new.split("\n")[0] in novo and "fix57" in novo:
                print(f"  [INFO] ja aplicado: {nome}")
                continue
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {len(faltando)} patch(es) nao encontrados:")
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
    print(f"[OK] {ALVO} atualizado.")
    return 0


def reverter():
    if not ALVO.exists():
        print(f"[ERRO] {ALVO} nao encontrado.")
        return 1
    bak = _ultimo_backup(ALVO)
    if not bak:
        print("[ERRO] nenhum backup.")
        return 1
    shutil.copy2(bak, ALVO)
    print(f"[REVERTER] {ALVO} restaurado de {bak.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    sys.exit(reverter() if args.reverter else aplicar(dry_run=args.dry_run))