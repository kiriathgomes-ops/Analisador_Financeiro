"""
fix41.py — Integra cache_candles no motor SMC e na pagina

Uso:
    python fix41.py --dry-run
    python fix41.py
    python fix41.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_RODAR = ROOT / "Rodar_SMC_Regras.py"
ALVO_PAG = ROOT / "pages" / "7.1_📊_SMC_Regras.py"
ALVO_GITIGNORE = ROOT / ".gitignore"

A_IMPORT_ANTIGO = """    print(f"[ERRO] Import Motor_SMC_Regras: {e}")
    sys.exit(1)

if sys.platform == "win32":
"""

A_IMPORT_NOVO = """    print(f"[ERRO] Import Motor_SMC_Regras: {e}")
    sys.exit(1)

from cache_candles import obter_candles_multi_tf

if sys.platform == "win32":
"""

A_CHAMADA_ANTIGO = "        coletas = carregar_multi_mt5(ATIVO, TIMEFRAMES)\n"

A_CHAMADA_NOVO = """        # fix41: usa cache incremental em vez de pull de 300 velas do MT5
        tf_qtd = {
            1:  TIMEFRAMES["1m"]["qtd"],
            5:  TIMEFRAMES["5m"]["qtd"],
            15: TIMEFRAMES["15m"]["qtd"],
        }
        mapa_labels = {1: "1m", 5: "5m", 15: "15m"}

        coletas_por_tf = obter_candles_multi_tf(ATIVO, tf_qtd)

        coletas = {}
        for tf_min, (candles, contrato) in coletas_por_tf.items():
            coletas[mapa_labels[tf_min]] = (candles, contrato)
"""

PATCHES_RODAR = [
    ("importa obter_candles_multi_tf", A_IMPORT_ANTIGO, A_IMPORT_NOVO),
    ("chama cache em vez de carregar_multi_mt5", A_CHAMADA_ANTIGO, A_CHAMADA_NOVO),
]

B_FUNC_ANTIGO = """@st.cache_data(ttl=60, show_spinner=False)  # Reduzido para 60s (sincronizado com autorefresh)
def carregar_candles_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 200):
    \"\"\"Busca candles do MT5. Cache de 60s para alinhar com o autorefresh.\"\"\"
    try:
        from Motor_SMC_Regras import carregar_mt5
        candles, simbolo_ok = carregar_mt5(symbol, timeframe_min, qtd, validar_pregao=False)
        return candles, simbolo_ok
    except Exception as e:
        return [], str(e)
"""

B_FUNC_NOVO = """@st.cache_data(ttl=60, show_spinner=False)
def carregar_candles_mt5(symbol: str = "WIN$", timeframe_min: int = 5, qtd: int = 200):
    \"\"\"
    fix41: usa cache_candles.obter_candles() em vez de puxar tudo do MT5.

    O cache faz fetch incremental dos ultimos candles, entao essa funcao
    fica barata mesmo com TTL de 60s — o M1 atualiza a cada minuto.
    \"\"\"
    try:
        from cache_candles import obter_candles
        candles, contrato = obter_candles(symbol, timeframe_min, qtd)
        return candles, contrato
    except Exception as e:
        return [], str(e)
"""

PATCHES_PAG = [("pagina usa cache_candles.obter_candles", B_FUNC_ANTIGO, B_FUNC_NOVO)]

C_ANTIGO = "# Pasta de limpeza local\nlixeira_analise/\n"

C_NOVO = """# Pasta de limpeza local
lixeira_analise/

# Cache incremental de candles (fix41)
Coletas/cache/
"""

PATCHES_GITIGNORE = [("ignora Coletas/cache/", C_ANTIGO, C_NOVO)]


def _backup(p):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar(alvo, patches, dry_run):
    if not alvo.exists():
        print(f"[ERRO] {alvo.name} nao encontrado")
        return 1

    conteudo = alvo.read_text(encoding="utf-8")
    novo = conteudo
    faltando = []

    for nome, old, new in patches:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] {alvo.name} — padroes nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print(f"  [INFO] {alvo.name}: nada mudou.")
        return 0

    if dry_run:
        print(f"  [DRY-RUN] {alvo.name}: nao salvo.")
        return 0

    bak = _backup(alvo)
    print(f"  [BACKUP] {bak.name}")
    alvo.write_text(novo, encoding="utf-8")
    print(f"  [OK] {alvo.name} atualizado.")
    return 0


def aplicar(dry_run):
    print(f"\n[ALVO 1] {ALVO_RODAR.name}")
    r1 = _aplicar(ALVO_RODAR, PATCHES_RODAR, dry_run)

    print(f"\n[ALVO 2] {ALVO_PAG.name}")
    r2 = _aplicar(ALVO_PAG, PATCHES_PAG, dry_run)

    print(f"\n[ALVO 3] {ALVO_GITIGNORE.name}")
    r3 = _aplicar(ALVO_GITIGNORE, PATCHES_GITIGNORE, dry_run)

    if r1 == 0 and r2 == 0 and r3 == 0:
        print("\n[SUCESSO] fix41 aplicado.")
        return 0
    return max(r1, r2, r3)


def reverter():
    for alvo in (ALVO_RODAR, ALVO_PAG, ALVO_GITIGNORE):
        if not alvo.exists():
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[ERRO] {alvo.name}: nenhum backup.")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} restaurado de {bak.name}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
