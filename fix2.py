#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix2.py — Congela variacao_teorica_pct por dia no CalculadoraEstimativaAbertura.py
====================================================================================

Problema:
  A `variacao_teorica_pct` e recalculada a cada execucao do pipeline, usando
  EWZ/SP500/ADRs/etc. Como esses ativos oscilam durante o dia, a "Abertura
  Teorica WIN" muda a cada ciclo — o que gera confusao operacional (o mesmo
  numero muda sem que nada estrutural tenha mudado).

Solucao:
  Congelar o calculo de `variacao_teorica_pct` na primeira execucao do dia.
  Cache em Coletas/EstimativaAbertura_Cache.json. Cache e invalidado se:
    - data_ref mudar (novo dia)
    - ajuste B3 mudar (ex: pipeline rodando apos publicacao do ajuste)

  Os demais campos (pivots, POC, VWAP, cost of carry) continuam atualizando
  normalmente a cada ciclo.

Uso:
    python fix2.py --dry-run    # simula
    python fix2.py              # aplica
    python fix2.py --reverter   # restaura do backup mais recente
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


ARQUIVO_ALVO = Path("CalculadoraEstimativaAbertura.py")


# ============================================================
# PATCHES
# ============================================================
PATCH_1_CONSTANTE = (
    "Adiciona constante FILE_CACHE_VAR_TEORICA",
    '''FILE_SMC_DADOS = Path(COLETAS_DIR) / "AnaliseGraficaSMC_Regras.json"''',
    '''FILE_SMC_DADOS = Path(COLETAS_DIR) / "AnaliseGraficaSMC_Regras.json"
FILE_CACHE_VAR_TEORICA = Path(COLETAS_DIR) / "EstimativaAbertura_Cache.json"''',
)


PATCH_2_HELPERS = (
    "Adiciona helpers de cache (carregar/salvar/resolver)",
    '''def calcular_abertura_win(ativos_dict: dict, preco_referencia_base: float) -> dict:''',
    '''def _carregar_cache_var() -> dict:
    """Le o cache da variacao teorica, se existir."""
    if not os.path.exists(FILE_CACHE_VAR_TEORICA):
        return {}
    try:
        with open(FILE_CACHE_VAR_TEORICA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_cache_var(payload: dict) -> None:
    """Persiste o cache da variacao teorica."""
    try:
        os.makedirs(os.path.dirname(FILE_CACHE_VAR_TEORICA), exist_ok=True)
        with open(FILE_CACHE_VAR_TEORICA, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[AVISO] Falha ao salvar cache var teorica: {e}")


def _resolver_var_teorica(data_ref: str, ajuste: float, var_teorica_atual: float):
    """
    Resolve a var_teorica_pct a ser usada neste ciclo.

    Retorna (var_final, veio_do_cache, timestamp_cache).
      - Se cache existe e bate (data + ajuste): usa cache
      - Se nao: salva o valor atual no cache e retorna ele

    `timestamp_cache` e None quando recalculado agora.
    """
    cache = _carregar_cache_var()
    ajuste_arredondado = round(float(ajuste or 0.0), 0)

    cache_data = cache.get("data_ref")
    cache_ajuste = cache.get("ajuste")
    if cache_data is not None:
        try:
            cache_ajuste = round(float(cache_ajuste), 0)
        except (TypeError, ValueError):
            cache_ajuste = None

    if cache_data == data_ref and cache_ajuste == ajuste_arredondado:
        var = cache.get("variacao_teorica_pct")
        ts = cache.get("timestamp_geracao")
        if var is not None:
            return float(var), True, ts

    # Cache invalido ou inexistente -> salva o atual
    novo = {
        "data_ref": data_ref,
        "ajuste": ajuste_arredondado,
        "variacao_teorica_pct": float(var_teorica_atual) if var_teorica_atual is not None else 0.0,
        "timestamp_geracao": datetime.now().isoformat(),
    }
    _salvar_cache_var(novo)
    return float(var_teorica_atual) if var_teorica_atual is not None else 0.0, False, None


def calcular_abertura_win(ativos_dict: dict, preco_referencia_base: float) -> dict:''',
)


PATCH_3_APLICAR_CONGELAMENTO = (
    "Aplica congelamento em processar_calculos_operacionais()",
    '''    win_metrics = calcular_abertura_win(ativos_dict, preco_base)
    win_metrics["contexto_janela"] = contexto_janela''',
    '''    win_metrics = calcular_abertura_win(ativos_dict, preco_base)
    win_metrics["contexto_janela"] = contexto_janela

    # ---- CONGELA variacao_teorica_pct por dia (data + ajuste) ----
    var_teorica_calculada = win_metrics.get("variacao_teorica_pct")
    var_teorica_final, do_cache, ts_cache = _resolver_var_teorica(
        data_ref=datetime.now().date().isoformat(),
        ajuste=preco_base,
        var_teorica_atual=var_teorica_calculada,
    )

    # Recalcula a abertura teorica com a var congelada
    abertura_congelada = round(preco_base * (1 + var_teorica_final / 100), 0) if preco_base > 0 else 0.0

    win_metrics["variacao_teorica_pct"] = round(var_teorica_final, 4)
    win_metrics["abertura_teorica_pontos"] = abertura_congelada
    win_metrics["var_teorica_congelada"] = True
    win_metrics["var_teorica_do_cache"] = bool(do_cache)
    win_metrics["var_teorica_timestamp_cache"] = ts_cache
    win_metrics["var_teorica_calculada_agora"] = (
        round(var_teorica_calculada, 4) if var_teorica_calculada is not None else None
    )''',
)


PATCH_4_PAYLOAD = (
    "Adiciona flags de cache no metadata do payload",
    '''    payload = {
        "metadata_calculo": {
            "timestamp_calculo": datetime.now().isoformat(),
            "janela_ativa": contexto_janela
        },''',
    '''    payload = {
        "metadata_calculo": {
            "timestamp_calculo": datetime.now().isoformat(),
            "janela_ativa": contexto_janela,
            "var_teorica_congelada": win_metrics.get("var_teorica_congelada", False),
            "var_teorica_do_cache": win_metrics.get("var_teorica_do_cache", False),
            "var_teorica_timestamp_cache": win_metrics.get("var_teorica_timestamp_cache"),
        },''',
)


PATCH_5_CONSOLE = (
    "Console: avisa quando var teorica vem do cache",
    '''    print(f" Variação Teórica (Delta) : {win_metrics['variacao_teorica_pct']}%")
    print(f" Abertura Teórica WIN     : {win_metrics['abertura_teorica_pontos']} pts")''',
    '''    if win_metrics.get("var_teorica_do_cache"):
        ts_cache = win_metrics.get("var_teorica_timestamp_cache") or "?"
        ts_curto = ts_cache[11:19] if len(ts_cache) >= 19 else ts_cache
        origem_var = f"🔒 CONGELADA (do cache, gerada {ts_curto})"
    else:
        origem_var = "🆕 RECALCULADA AGORA (primeira vez hoje ou ajuste mudou)"

    print(f" Variação Teórica (Delta) : {win_metrics['variacao_teorica_pct']}%")
    print(f"   └─ Origem              : {origem_var}")
    print(f" Abertura Teórica WIN     : {win_metrics['abertura_teorica_pontos']} pts")''',
)


PATCHES = [
    PATCH_1_CONSTANTE,
    PATCH_2_HELPERS,
    PATCH_3_APLICAR_CONGELAMENTO,
    PATCH_4_PAYLOAD,
    PATCH_5_CONSOLE,
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
            print(f"[AVISO] Patch {i}/{len(PATCHES)}: {nome} — padrao nao encontrado apos patch anterior")
            return 3

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
        description="Congela variacao_teorica_pct por dia no CalculadoraEstimativaAbertura.py"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar")
    parser.add_argument("--reverter", action="store_true", help="Restaura do backup mais recente")
    args = parser.parse_args()

    print("=" * 60)
    print(" fix2.py — Congela var_teorica_pct por dia")
    print("=" * 60)

    if args.reverter:
        return reverter()
    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())