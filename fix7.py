#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix7.py — Corrige duplicação nos gauges de pressão e fallback do Last
======================================================================

Alterações em pages/2_🎯_Setup_Abertura.py:

  1. Last (Candle): fallback para WIN_FECHAMENTO_B3 quando WIN_LAST_TICK
     nao existe no unificado (acontece durante o pregao, pois o
     LastTick_Congelado.json so e gravado fora do pregao).

  2. Velocimetros de pressao (Mercado Externo + ADRs): a sub-linha
     mostrava o MESMO valor do ponteiro (redundante). Agora mostra a
     leitura anterior (5 min atras), no padrao "Ant X.XX%".

  3. Bonus: aplica o mesmo fix nos 3 gauges de "Explosao Pos-Abertura"
     (Score, Sum ADRs, Sum Macro) que sofriam do mesmo problema.

Uso:
    python fix7.py --dry-run
    python fix7.py
    python fix7.py --reverter
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("pages/2_🎯_Setup_Abertura.py")


# ============================================================
# PATCHES
# ============================================================
PATCH_1_LAST_FALLBACK = (
    "Last (Candle): fallback WIN_LAST_TICK -> WIN_FECHAMENTO_B3",
    '''    win_last_v = get_p_num("WIN_LAST_TICK")
    win_ajuste_v = get_p_num("WIN_AJUSTE")
    win_fut_v = get_p_num("WIN_FUT")''',
    '''    win_last_v = get_p_num("WIN_LAST_TICK")
    # Fallback: se WIN_LAST_TICK nao existe (durante o pregao, pois o
    # LastTick_Congelado.json so e gravado fora do pregao), usa o fechamento
    # oficial da brapi (WIN_FECHAMENTO_B3), que e o mesmo valor conceitual.
    if win_last_v is None:
        win_last_v = get_p_num("WIN_FECHAMENTO_B3")
    win_ajuste_v = get_p_num("WIN_AJUSTE")
    win_fut_v = get_p_num("WIN_FUT")''',
)


PATCH_2_PRESSAO_MERCADO = (
    "Gauge Mercado Externo: sub-linha mostra 'Ant' em vez de duplicar",
    '''        mini_velocimetro(
            ind_mercado,
            "🌍 Mercado Externo",
            f"{ind_mercado:+.2f}%" if ind_mercado is not None else "",
            inverter=False,
            valor_anterior=pen_m,
            escala=2.0,
        )''',
    '''        mini_velocimetro(
            ind_mercado,
            "🌍 Mercado Externo",
            f"Ant {pen_m:+.2f}%" if pen_m is not None else "",
            inverter=False,
            valor_anterior=pen_m,
            escala=2.0,
        )''',
)


PATCH_3_PRESSAO_ADRS = (
    "Gauge ADRs Brasileiras: sub-linha mostra 'Ant' em vez de duplicar",
    '''        mini_velocimetro(
            ind_adrs,
            "🇧🇷 BR ADRs Brasileiras",
            f"{ind_adrs:+.2f}%" if ind_adrs is not None else "",
            inverter=False,
            valor_anterior=pen_a,
            escala=2.0,
        )''',
    '''        mini_velocimetro(
            ind_adrs,
            "🇧🇷 BR ADRs Brasileiras",
            f"Ant {pen_a:+.2f}%" if pen_a is not None else "",
            inverter=False,
            valor_anterior=pen_a,
            escala=2.0,
        )''',
)


PATCH_4_EXPLOSAO_SCORE = (
    "Gauge Score (explosao): sub-linha mostra 'Ant' em vez de duplicar",
    '''        with e1:
            mini_velocimetro(
                score, "⚡ Score",
                f"{score:+.2f}" if score is not None else "",
                inverter=False,
                valor_anterior=score_ant,
            )''',
    '''        with e1:
            mini_velocimetro(
                score, "⚡ Score",
                f"Ant {score_ant:+.2f}" if score_ant is not None else "",
                inverter=False,
                valor_anterior=score_ant,
            )''',
)


PATCH_5_EXPLOSAO_ADRS = (
    "Gauge Sum ADRs (explosao): sub-linha mostra 'Ant' em vez de duplicar",
    '''        with e2:
            mini_velocimetro(
                ind_adrs, "🇧🇷 Σ ADRs",
                f"{ind_adrs:+.2f}%" if ind_adrs is not None else "",
                inverter=False,
                valor_anterior=ind_adrs_ant,
            )''',
    '''        with e2:
            mini_velocimetro(
                ind_adrs, "🇧🇷 Σ ADRs",
                f"Ant {ind_adrs_ant:+.2f}%" if ind_adrs_ant is not None else "",
                inverter=False,
                valor_anterior=ind_adrs_ant,
            )''',
)


PATCH_6_EXPLOSAO_MACRO = (
    "Gauge Sum Macro (explosao): sub-linha mostra 'Ant' em vez de duplicar",
    '''        with e3:
            mini_velocimetro(
                ind_ext, "🌍 Σ Macro",
                f"{ind_ext:+.2f}%" if ind_ext is not None else "",
                inverter=False,
                valor_anterior=ind_ext_ant,
            )''',
    '''        with e3:
            mini_velocimetro(
                ind_ext, "🌍 Σ Macro",
                f"Ant {ind_ext_ant:+.2f}%" if ind_ext_ant is not None else "",
                inverter=False,
                valor_anterior=ind_ext_ant,
            )''',
)


PATCHES = [
    PATCH_1_LAST_FALLBACK,
    PATCH_2_PRESSAO_MERCADO,
    PATCH_3_PRESSAO_ADRS,
    PATCH_4_EXPLOSAO_SCORE,
    PATCH_5_EXPLOSAO_ADRS,
    PATCH_6_EXPLOSAO_MACRO,
]


# ============================================================
# LOGICA
# ============================================================
def _backup_mais_recente():
    backups = sorted(
        ARQUIVO_ALVO.parent.glob(f"{ARQUIVO_ALVO.name}.bak_*"),
        reverse=True,
    )
    return backups[0] if backups else None


def reverter() -> int:
    backup = _backup_mais_recente()
    if not backup:
        print(f"[ERRO] Nenhum backup encontrado para {ARQUIVO_ALVO}")
        return 1
    print(f"[INFO] Restaurando de: {backup.name}")
    shutil.copy2(backup, ARQUIVO_ALVO)
    print(f"[OK] {ARQUIVO_ALVO} restaurado")
    return 0


def _validar_sintaxe_py(caminho: Path) -> tuple[bool, str]:
    import ast
    try:
        ast.parse(caminho.read_text(encoding="utf-8"))
        return True, "OK"
    except SyntaxError as e:
        return False, f"SyntaxError linha {e.lineno}: {e.msg}"


def aplicar(dry_run: bool = False) -> int:
    if not ARQUIVO_ALVO.exists():
        print(f"[ERRO] Arquivo nao encontrado: {ARQUIVO_ALVO.resolve()}")
        print("       Rode a partir da raiz do projeto.")
        return 1

    conteudo_original = ARQUIVO_ALVO.read_text(encoding="utf-8")

    faltando = [nome for nome, antigo, _ in PATCHES if antigo not in conteudo_original]
    if faltando:
        print("[FALHA] Os seguintes patches nao encontraram o padrao esperado:")
        for nome in faltando:
            print(f"   - {nome}")
        print("\nNenhuma alteracao foi feita.")
        return 2

    if not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = ARQUIVO_ALVO.with_suffix(f".py.bak_{timestamp}")
        shutil.copy2(ARQUIVO_ALVO, backup_path)
        print(f"[OK] Backup: {backup_path.name}")
    else:
        print("[DRY-RUN] Backup nao sera criado")

    conteudo = conteudo_original
    for i, (nome, antigo, novo) in enumerate(PATCHES, start=1):
        if antigo in conteudo:
            conteudo = conteudo.replace(antigo, novo, 1)
            print(f"[OK] Patch {i}/{len(PATCHES)}: {nome}")
        else:
            print(f"[AVISO] Patch {i}/{len(PATCHES)}: {nome} — nao encontrado apos patch anterior")
            return 3

    if not dry_run:
        ARQUIVO_ALVO.write_text(conteudo, encoding="utf-8")
        ok, msg = _validar_sintaxe_py(ARQUIVO_ALVO)
        if not ok:
            print(f"[ERRO] Sintaxe invalida: {msg}")
            return 4
        print(f"[OK] Sintaxe validada")
        print(f"\n[OK] {ARQUIVO_ALVO} atualizado com sucesso")
        print(f"     {len(PATCHES)} patches aplicados")
    else:
        print(f"\n[DRY-RUN] Simulacao concluida — arquivo NAO foi salvo")
        print(f"          {len(PATCHES)} patches seriam aplicados")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corrige duplicacao nos gauges e fallback do Last"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar")
    parser.add_argument("--reverter", action="store_true", help="Restaura do backup")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix7.py — Gauges de pressao + fallback do Last")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())