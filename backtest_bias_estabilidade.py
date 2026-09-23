"""
backtest_bias_estabilidade.py

Compara estabilidade do bias SMC com bias_janela=1 (comportamento antigo)
vs bias_janela=5 (fix31) sobre candles historicos M1 do MT5.

Estrategia:
    1. Baixa N candles M1 do MT5 (default 1000 = ~16h)
    2. Para cada sub-janela deslizante (passo = 25 candles):
       roda analisar_smc 2x com configs diferentes
    3. Conta "flips" do bias entre janelas consecutivas

Interpretacao:
    - flips_janela1 = comportamento anterior (bias = ultimo evento)
    - flips_janela5 = comportamento atual (bias = maioria de 5)
    - Se flips_janela5 < flips_janela1, o fix31 ajudou.

Uso:
    python backtest_bias_estabilidade.py
    python backtest_bias_estabilidade.py --qtd 2000 --passo 50
"""

import argparse
from dataclasses import replace
from typing import List

from Motor_SMC_Regras import carregar_mt5, analisar_smc, CONFIG


def rodar_slices(candles_all, cfg, passo: int, min_candles: int = 200) -> List[str]:
    biases = []
    n = len(candles_all)
    for k in range(min_candles, n + 1, passo):
        sub = candles_all[:k]
        try:
            r = analisar_smc(sub, ativo="WIN$", timeframe="1m", config=cfg)
            b = r.get("bias_direcional") or "LATERAL"
            biases.append(b)
        except Exception:
            biases.append("ERRO")
    return biases


def contar_flips(seq: List[str]) -> int:
    if len(seq) < 2:
        return 0
    return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qtd", type=int, default=1000,
                    help="Candles M1 a baixar (default 1000)")
    ap.add_argument("--passo", type=int, default=25,
                    help="Passo entre slices (default 25 candles)")
    args = ap.parse_args()

    print("=" * 62)
    print(" BACKTEST: Estabilidade do bias SMC (fix31)")
    print("=" * 62)

    print(f"\n-> Baixando {args.qtd} candles M1 do MT5...")
    try:
        candles, simbolo = carregar_mt5("WIN$", timeframe_min=1, qtd=args.qtd)
    except Exception as e:
        print(f"[ERRO] Falha MT5: {e}")
        return 1

    if not candles:
        print("[ERRO] Nenhum candle retornado.")
        return 1

    print(f"   [OK] {len(candles)} candles de {simbolo}")

    # Config A: comportamento antigo (janela=1, sem margem)
    cfg_antigo = replace(CONFIG, bias_janela=1, bias_min_margem=0)
    # Config B: atual (janela=5, margem=1)
    cfg_novo = replace(CONFIG, bias_janela=5, bias_min_margem=1)

    print(f"\n-> Rodando {len(range(200, len(candles) + 1, args.passo))} slices "
          f"com passo={args.passo}...")

    biases_antigo = rodar_slices(candles, cfg_antigo, args.passo)
    biases_novo = rodar_slices(candles, cfg_novo, args.passo)

    flips_antigo = contar_flips(biases_antigo)
    flips_novo = contar_flips(biases_novo)

    print("\n" + "-" * 62)
    print(" RESULTADOS")
    print("-" * 62)
    print(f"  Slices rodados        : {len(biases_antigo)}")
    print(f"  bias_janela=1 (antigo): {flips_antigo} flips")
    print(f"  bias_janela=5 (atual) : {flips_novo} flips")
    print(f"  Reducao               : {flips_antigo - flips_novo} flips "
          f"({(1 - flips_novo / max(flips_antigo, 1)) * 100:.1f}%)")
    print()

    # Distribuicao de biases
    from collections import Counter
    print("  Distribuicao antigo   :", dict(Counter(biases_antigo)))
    print("  Distribuicao novo     :", dict(Counter(biases_novo)))
    print("=" * 62)

    if flips_novo < flips_antigo:
        print("✅ fix31 REDUZIU flips — filtro de maioria esta funcionando.")
    elif flips_novo == flips_antigo:
        print("⚪ Empate — filtro nao muda neste periodo. Ver com mais dados.")
    else:
        print("⚠️ fix31 AUMENTOU flips — investigar. Talvez janela muito curta.")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())