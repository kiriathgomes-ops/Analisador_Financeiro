"""
fix38.py — reverte fix31: bias volta a ser eventos[-1].direcao

Contexto:
    O backtest do fix31 (bias_janela=1 vs =5) deu resultado MISTO:
        - 1000 candles, passo 25: 16 -> 14 flips (-12.5%)
        - 2000 candles, passo 50: 17 -> 21 flips (+23.5%)
    Amostras pequenas + sobrepostas = ruido. Sem evidencia de ganho.

Decisao:
    Reverter o fix31 e manter os ganhos claros do fix35 (refator) e
    fix36 (robustez parcial). ConfigSMC.bias_janela/bias_min_margem
    ficam na dataclass (nao atrapalham), mas o comportamento volta ao
    historico: bias = ultimo evento de estrutura.

Uso:
    python fix38.py --dry-run
    python fix38.py
    python fix38.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Motor_SMC_Regras.py"

# Bloco atual (com maioria) -> bloco original (ultimo evento)
ANTIGO = '''    if eventos:
        # Estabilidade: bias por MAIORIA dos ultimos N eventos (fix31).
        # Se empate ou sem maioria clara, usa o ultimo (comportamento
        # historico). Reduz flip-flop em timeframes ruidosos (M1).
        _janela_n = getattr(config, "bias_janela", 5)
        _margem = getattr(config, "bias_min_margem", 1)
        janela = eventos[-_janela_n:]
        votos_alta = sum(1 for e in janela if e.direcao == "ALTA")
        votos_baixa = sum(1 for e in janela if e.direcao == "BAIXA")
        margem = _margem

        if votos_alta >= votos_baixa + margem:
            bias = "ALTA"
        elif votos_baixa >= votos_alta + margem:
            bias = "BAIXA"
        else:
            # Sem maioria clara: mantem o ultimo evento
            bias = eventos[-1].direcao
    return eventos, bias
'''

NOVO = '''    if eventos:
        # Fix38: revertido ao comportamento original (fix31 sem evidencia
        # estatistica de ganho). O bias segue o ultimo evento de estrutura.
        # ConfigSMC.bias_janela/bias_min_margem ficam disponiveis caso
        # a estrategia seja revisitada com mais dados.
        bias = eventos[-1].direcao
    return eventos, bias
'''

PATCHES = [("reverte bias por maioria -> ultimo evento", ANTIGO, NOVO)]


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
        print(f"[ERRO] {ALVO.name} nao encontrado")
        return 1

    conteudo = ALVO.read_text(encoding="utf-8")

    if NOVO in conteudo:
        print("[INFO] ja revertido (bloco NOVO ja esta no arquivo).")
        return 0

    if ANTIGO not in conteudo:
        print("[ABORT] bloco com logica de maioria nao encontrado.")
        print("        Verifique se o fix31 foi aplicado.")
        return 2

    novo = conteudo.replace(ANTIGO, NOVO, 1)

    if dry_run:
        print("  [PATCH OK] reverter bias por maioria -> ultimo evento")
        print("\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"  [PATCH OK] reverter bias por maioria -> ultimo evento")
    print(f"  [BACKUP] {bak.name}")
    ALVO.write_text(novo, encoding="utf-8")
    print(f"  [OK] {ALVO.name} atualizado.")
    return 0


def reverter() -> int:
    """Restaura a versao ANTERIOR (com maioria) — desfaz o fix38."""
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