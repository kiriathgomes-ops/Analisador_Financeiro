# -*- coding: utf-8 -*-
"""
fix56.py - Reagenda o Agendador para :05 segundos + disparos especiais

Mudancas:
    A) Disparos regulares: a cada 5 min no segundo :05
       (00:05, 05:05, 10:05, ..., 55:05) — 5s apos o candle fechar
    B) Disparos especiais adicionais: 08:59:05 e 09:59:05
       (1 min antes da abertura B3 e do ORB 10:00)
    C) Banner mostra a grade + os especiais
    D) Logica de calculo do proximo ciclo baseada em lista ordenada
       (substitui a formula aritmetica antiga)

Uso:
    python fix56.py --dry-run
    python fix56.py
    python fix56.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Agendador.py"

# --- Patch 1: substitui bloco de calculo ---
CALC_ANTIGO = '''def calcular_segundos_ate_proximo_ciclo():
    """Calcula quantos segundos faltam até o próximo minuto terminado em 4 ou 9."""
    agora = datetime.now()
    minuto_atual = agora.minute
    segundo_atual = agora.second
    microsegundo_atual = agora.microsecond

    # Calcula os minutos necessários até o próximo múltiplo de 5 vindo do :04
    # Os minutos de disparo são: 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59
    minutos_para_esperar = (4 - (minuto_atual % 5)) % 5

    # Se já passou do segundo 0 do minuto exato de execução, espera o próximo ciclo de 5 min
    if minutos_para_esperar == 0 and (
        segundo_atual > 0 or microsegundo_atual > 0
    ):
        minutos_para_esperar = 5

    # Converte tudo para segundos exatos
    segundos_restantes = (
        (minutos_para_esperar * 60)
        - segundo_atual
        - (microsegundo_atual / 1_000_000.0)
    )
    return max(0.0, segundos_restantes)
'''

CALC_NOVO = '''# Segundos de delay apos o minuto redondo (seguranca pra candle fechar no MT5)
SEGUNDO_DISPARO = 5

# Disparos regulares: a cada 5 min no segundo :05
DISPAROS_REGULARES = [
    h * 3600 + m * 60 + SEGUNDO_DISPARO
    for h in range(24)
    for m in range(0, 60, 5)
]

# Disparos especiais (adicionais): 1 min antes da abertura B3 e do ORB
DISPAROS_ESPECIAIS = [
    8 * 3600 + 59 * 60 + SEGUNDO_DISPARO,   # 08:59:05
    9 * 3600 + 59 * 60 + SEGUNDO_DISPARO,   # 09:59:05
]

# Grade consolidada (ordenada, dedupada)
DISPAROS = sorted(set(DISPAROS_REGULARES + DISPAROS_ESPECIAIS))


def calcular_segundos_ate_proximo_ciclo():
    """Calcula quantos segundos faltam ate o proximo disparo (grade + especiais)."""
    agora = datetime.now()
    agora_seg = (
        agora.hour * 3600
        + agora.minute * 60
        + agora.second
        + agora.microsecond / 1_000_000.0
    )

    for t in DISPAROS:
        if t > agora_seg:
            return max(0.0, t - agora_seg)

    # Passou de todos hoje -> pega o primeiro de amanha
    return max(0.0, 86400 - agora_seg + DISPAROS[0])
'''

# --- Patch 2: banner atualizado ---
BANNER_ANTIGO = '''    print("============================================================")
    print("⏰ AGENDADOR SINCRONIZADO INICIADO")
    print("🎯 PONTOS DE EXECUÇÃO: :04 | :09 | :14 | :19 | :24 | :29 ...")
    print("============================================================")
'''

BANNER_NOVO = '''    print("============================================================")
    print("⏰ AGENDADOR SINCRONIZADO INICIADO")
    print(f"🎯 REGULAR: a cada 5 min no segundo :{SEGUNDO_DISPARO:02d}")
    print(f"   Ex: 00:05 | 05:05 | 10:05 | ... | 55:05")
    print(f"🎯 ESPECIAIS: 08:59:{SEGUNDO_DISPARO:02d} | 09:59:{SEGUNDO_DISPARO:02d}")
    print("============================================================")
    print()
    print("📅 Proximos 5 disparos:")
    agora = datetime.now()
    agora_seg = (
        agora.hour * 3600 + agora.minute * 60 + agora.second
        + agora.microsecond / 1_000_000.0
    )
    contador = 0
    for t in DISPAROS:
        if t > agora_seg and contador < 5:
            h, rem = divmod(int(t), 3600)
            m, s = divmod(rem, 60)
            print(f"   {h:02d}:{m:02d}:{s:02d}")
            contador += 1
    print()
'''

PATCHES = [
    ("substitui calculo por grade + especiais", CALC_ANTIGO, CALC_NOVO),
    ("banner com grade + proximos disparos", BANNER_ANTIGO, BANNER_NOVO),
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
            if new.split("\n")[0] in novo:
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