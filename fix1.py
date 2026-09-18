#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix1.py — Deduplicacao de OBs por ativo no Motor_SMC_Regras.py
================================================================

Aplica 5 alteracoes cirurgicas no Motor_SMC_Regras.py:
  1. ConfigSMC: adiciona campos dedup_ob_dist e dedup_ob_dist_default
  2. Nova helper _dedup_dist_para() (threshold por ativo)
  3. detectar_order_blocks() recebe `ativo` como parametro
  4. Dedup interno usa threshold dinamico (50 WIN / 5 WDO) + log
  5. Chamada em analisar_smc passa `ativo`

Uso:
    python fix1.py              # aplica patches
    python fix1.py --dry-run    # simula sem salvar
    python fix1.py --reverter   # restaura do backup mais recente

Backup automatico: Motor_SMC_Regras.py.bak_YYYYMMDD_HHMMSS
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("Motor_SMC_Regras.py")


# ============================================================
# PATCHES
# ============================================================
# Cada patch e uma tupla (nome_legivel, texto_antigo, texto_novo).
# O script aborta se QUALQUER texto_antigo nao for encontrado.

PATCH_1_CONFIGSMC = (
    "ConfigSMC: adiciona campos de dedup por ativo",
    """    # Validação de OB
    ob_validacao_janela: int = 40
    ob_min_range: float = 30.0
    ob_fallback_brutos: bool = True""",
    """    # Validação de OB
    ob_validacao_janela: int = 40
    ob_min_range: float = 30.0
    ob_fallback_brutos: bool = True

    # Deduplicação de OBs por ativo (threshold em pontos)
    # WIN tem tick de 5 pts → OBs separados por <50 pts são o mesmo bloco
    # WDO tem tick de 0.5 pts → 5 pts já é generoso
    dedup_ob_dist: Dict[str, float] = field(
        default_factory=lambda: {
            "WIN": 50.0,
            "WDO": 5.0,
        }
    )
    dedup_ob_dist_default: float = 10.0""",
)


PATCH_2_HELPER = (
    "Adiciona helper _dedup_dist_para()",
    '''def _tick_size_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """Retorna o tick size adequado para o ativo."""
    ativo_up = (ativo or "").upper()
    for chave, tick in config.tick_size_map.items():
        if chave in ativo_up:
            return tick
    return config.tick_size_default''',
    '''def _tick_size_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """Retorna o tick size adequado para o ativo."""
    ativo_up = (ativo or "").upper()
    for chave, tick in config.tick_size_map.items():
        if chave in ativo_up:
            return tick
    return config.tick_size_default


def _dedup_dist_para(ativo: str, config: ConfigSMC = CONFIG) -> float:
    """
    Retorna a distancia minima (em pontos) para considerar dois OBs distintos.

    WIN: 50 pts (blocos muito proximos sao o mesmo OB visto de angulos diferentes)
    WDO: 5 pts
    Default: 10 pts
    """
    ativo_up = (ativo or "").upper()
    for chave, dist in config.dedup_ob_dist.items():
        if chave in ativo_up:
            return dist
    return config.dedup_ob_dist_default''',
)


PATCH_3_ASSINATURA = (
    "detectar_order_blocks(): adiciona parametro ativo",
    """def detectar_order_blocks(
    candles: List[Candle],
    swings: List[Swing],
    eventos_estrutura: List[EventoEstrutura],
    config: ConfigSMC = CONFIG,
) -> List[OrderBlock]:""",
    """def detectar_order_blocks(
    candles: List[Candle],
    swings: List[Swing],
    eventos_estrutura: List[EventoEstrutura],
    ativo: str = "WIN",
    config: ConfigSMC = CONFIG,
) -> List[OrderBlock]:""",
)


PATCH_4_DEDUP = (
    "detectar_order_blocks(): dedup com threshold dinamico + log",
    """    # ---- Deduplicação
    unicos: List[OrderBlock] = []
    for ob in obs_validados:
        if not any(abs(ob.preco_ref - u.preco_ref) < 10 and ob.tipo == u.tipo for u in unicos):
            unicos.append(ob)

    return unicos""",
    """    # ---- Deduplicação (threshold por ativo)
    dist_dedup = _dedup_dist_para(ativo, config)
    unicos: List[OrderBlock] = []
    for ob in obs_validados:
        if not any(
            abs(ob.preco_ref - u.preco_ref) < dist_dedup and ob.tipo == u.tipo
            for u in unicos
        ):
            unicos.append(ob)

    # Log diagnostico (ajuda a ver quantos OBs foram consolidados)
    if len(unicos) < len(obs_validados):
        logger.info(
            f"Dedup OB [{ativo}] (thr {dist_dedup:.0f} pts): "
            f"{len(obs_validados)} -> {len(unicos)}"
        )

    return unicos""",
)


PATCH_5_CHAMADA = (
    "analisar_smc(): passa ativo para detectar_order_blocks",
    """    swings = detectar_swings(candles, config.swing_left, config.swing_right)
    eventos, bias = detectar_bos_choch(candles, swings)
    fvgs = detectar_fvg(candles, config)
    obs = detectar_order_blocks(candles, swings, eventos, config)
    liq = detectar_liquidez(swings, config.eq_tol_pontos)""",
    """    swings = detectar_swings(candles, config.swing_left, config.swing_right)
    eventos, bias = detectar_bos_choch(candles, swings)
    fvgs = detectar_fvg(candles, config)
    obs = detectar_order_blocks(candles, swings, eventos, ativo, config)
    liq = detectar_liquidez(swings, config.eq_tol_pontos)""",
)


PATCHES = [
    PATCH_1_CONFIGSMC,
    PATCH_2_HELPER,
    PATCH_3_ASSINATURA,
    PATCH_4_DEDUP,
    PATCH_5_CHAMADA,
]


# ============================================================
# LOGICA
# ============================================================
def _backup_mais_recente() -> Path | None:
    """Retorna o backup mais recente do arquivo alvo, ou None."""
    backups = sorted(
        ARQUIVO_ALVO.parent.glob(f"{ARQUIVO_ALVO.name}.bak_*"),
        reverse=True,
    )
    return backups[0] if backups else None


def reverter() -> int:
    """Restaura o arquivo alvo do backup mais recente."""
    backup = _backup_mais_recente()
    if not backup:
        print(f"[ERRO] Nenhum backup encontrado para {ARQUIVO_ALVO}")
        return 1

    print(f"[INFO] Restaurando de: {backup.name}")
    shutil.copy2(backup, ARQUIVO_ALVO)
    print(f"[OK] {ARQUIVO_ALVO} restaurado")
    return 0


def aplicar(dry_run: bool = False) -> int:
    if not ARQUIVO_ALVO.exists():
        print(f"[ERRO] Arquivo nao encontrado: {ARQUIVO_ALVO.resolve()}")
        print("       Rode a partir da raiz do projeto.")
        return 1

    conteudo_original = ARQUIVO_ALVO.read_text(encoding="utf-8")

    # ---- Pre-validacao: todos os textos_antigos existem? ----
    faltando = []
    for nome, antigo, novo in PATCHES:
        if antigo not in conteudo_original:
            faltando.append(nome)

    if faltando:
        print("[FALHA] Os seguintes patches nao encontraram o padrao esperado:")
        for nome in faltando:
            print(f"   - {nome}")
        print()
        print("Isso geralmente significa que o arquivo ja foi modificado por")
        print("outro fix ou que o conteudo diverge do esperado.")
        print("Nenhuma alteracao foi feita.")
        return 2

    # ---- Backup ----
    if not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = ARQUIVO_ALVO.with_suffix(f".py.bak_{timestamp}")
        shutil.copy2(ARQUIVO_ALVO, backup_path)
        print(f"[OK] Backup: {backup_path.name}")
    else:
        print("[DRY-RUN] Backup nao sera criado")

    # ---- Aplicar patches sequencialmente ----
    conteudo = conteudo_original
    for i, (nome, antigo, novo) in enumerate(PATCHES, start=1):
        if antigo in conteudo:
            conteudo = conteudo.replace(antigo, novo, 1)
            print(f"[OK] Patch {i}/{len(PATCHES)}: {nome}")
        else:
            print(f"[AVISO] Patch {i}/{len(PATCHES)}: {nome} — padrao nao encontrado apos patch anterior")
            return 3

    # ---- Salvar ----
    if not dry_run:
        ARQUIVO_ALVO.write_text(conteudo, encoding="utf-8")
        print(f"\n[OK] {ARQUIVO_ALVO} atualizado com sucesso")
        print(f"     {len(PATCHES)} patches aplicados")
    else:
        print(f"\n[DRY-RUN] Simulacao concluida — arquivo NAO foi salvo")
        print(f"          {len(PATCHES)} patches seriam aplicados")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aplica patches no Motor_SMC_Regras.py (dedup OB por ativo)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula sem salvar o arquivo",
    )
    parser.add_argument(
        "--reverter",
        action="store_true",
        help="Restaura do backup mais recente",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" fix1.py — Dedup OB por ativo")
    print("=" * 60)

    if args.reverter:
        return reverter()

    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())