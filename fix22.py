"""
fix22.py — Snapshot ORB ganha consciencia de risco + spot real

Contexto:
    O snapshot de 21/09 10:06 marcou NAO_OCORREU porque WIN_FUT (do
    DadosAtivosUnificados.json) estava defasado. A vela 10:05 ja havia
    rompido o minimo da vela 10:00 (m=187.820). Resultado: sinal
    atrasado + stop do ORB = amplitude completa (540 pts).

Fix:
    1) analisar_rompimento_10h.py
       - Nova funcao _obter_spot_mt5(): last/bid/ask no momento da geracao
       - Novo bloco "BLOCO E.5: RISCO ORB": M, m, stops, alvos, spot real,
         estado do rompimento e alerta de amplitude grande
    2) PromptIA/Prompt_Rompimento_10h.txt
       - Regra 3.5 reescrita: DIVERGENTE nao forca AGUARDAR se o gatilho
         mecanico acabou de disparar; sinaliza risco do stop = amplitude

Uso:
    python fix22.py --dry-run
    python fix22.py
    python fix22.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_PY = ROOT / "analisar_rompimento_10h.py"
ALVO_PROMPT = ROOT / "PromptIA" / "Prompt_Rompimento_10h.txt"

# ---------------------------------------------------------------------------
# PATCHES no analisar_rompimento_10h.py
# ---------------------------------------------------------------------------

# 1) Adiciona _obter_spot_mt5() logo apos _descobrir_contrato_vigente
PY_ANCHOR_FUNC_ANTIGO = (
    '    print(f"[DIAG] Usando fallback estatico: {SIMBOLOS_MT5_FALLBACK}")\n'
    '    return list(SIMBOLOS_MT5_FALLBACK)\n'
)

PY_ANCHOR_FUNC_NOVO = '''    print(f"[DIAG] Usando fallback estatico: {SIMBOLOS_MT5_FALLBACK}")
    return list(SIMBOLOS_MT5_FALLBACK)


def _obter_spot_mt5():
    """
    Le o spot REAL do MT5 no instante da geracao (last/bid/ask).
    Usa o contrato vigente do JSON. Retorna dict ou None.
    Nao deve travar o pipeline: qualquer erro retorna None.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize():
        return None
    try:
        simbolos = _descobrir_contrato_vigente()
        simbolo = simbolos[0] if simbolos else None
        if not simbolo:
            return None
        info = mt5.symbol_info(simbolo)
        if info is None:
            return None
        if not info.visible:
            mt5.symbol_select(simbolo, True)
        tick = mt5.symbol_info_tick(simbolo)
        if tick is None:
            return None
        return {
            "simbolo": simbolo,
            "bid": float(getattr(tick, "bid", 0) or 0),
            "ask": float(getattr(tick, "ask", 0) or 0),
            "last": float(getattr(tick, "last", 0) or 0),
            "time": datetime.fromtimestamp(tick.time).isoformat(),
        }
    except Exception:
        return None
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass
'''

# 2) Adiciona bloco_risco_orb() antes de bloco_decisao
PY_ANCHOR_BLOCO_ANTIGO = (
    '        f"  Volume   : {fmt(vela[\'volume\'], 0)}",\n'
    '    ])\n'
    '\n'
    '\n'
    'def bloco_decisao(dec: dict) -> str:\n'
)

PY_ANCHOR_BLOCO_NOVO = '''        f"  Volume   : {fmt(vela['volume'], 0)}",
    ])


def bloco_risco_orb(vela: dict, spot: dict) -> str:
    """
    Bloco E.5 — Risco do setup ORB.
    Explicita M, m, stops, alvos e o estado REAL do rompimento
    (usando o spot do MT5, nao o WIN_FUT defasado do Bloco A).
    """
    if not vela:
        return "--- BLOCO E.5: RISCO ORB ---\\n  [sem vela 10:00 para calcular]"

    M = float(vela["high"])
    m = float(vela["low"])
    A = M - m

    preco_ref = None
    fonte_ref = "—"
    if spot and spot.get("last", 0) > 0:
        preco_ref = spot["last"]
        fonte_ref = f"MT5 spot ({spot.get('simbolo','?')})"

    linhas = [
        "--- BLOCO E.5: RISCO ORB ---",
        "",
        f"  Gatilho COMPRA (M) : {fmt(M, 0)}",
        f"  Stop  COMPRA       : {fmt(m, 0)}   (risco {fmt(A, 0)} pts)",
        f"  Alvo  COMPRA       : {fmt(M + A, 0)}",
        "",
        f"  Gatilho VENDA  (m) : {fmt(m, 0)}",
        f"  Stop  VENDA        : {fmt(M, 0)}   (risco {fmt(A, 0)} pts)",
        f"  Alvo  VENDA        : {fmt(m - A, 0)}",
        "",
        f"  Preco spot MT5     : {fmt(preco_ref, 0) if preco_ref else '—'}   ({fonte_ref})",
    ]

    if preco_ref:
        if preco_ref > M:
            dist = preco_ref - M
            linhas.append(f"  Rompimento REAL    : ALTA  (dist {fmt(dist, 0)} pts)")
        elif preco_ref < m:
            dist = m - preco_ref
            linhas.append(f"  Rompimento REAL    : BAIXA (dist {fmt(dist, 0)} pts)")
        else:
            linhas.append("  Rompimento REAL    : NAO OCORREU (preco dentro da faixa)")

    if A > 400:
        linhas.append("")
        linhas.append(f"  ALERTA: amplitude {fmt(A, 0)} pts — stop largo.")
        linhas.append(f"  Loss potencial (1 contrato) = {fmt(A, 0)} pts por lado.")

    linhas.append("")
    linhas.append("  NOTA: quando o alinhamento e DIVERGENTE mas o gatilho")
    linhas.append("  mecanico JA disparou ha menos de 150 pts, o setup ORB")
    linhas.append("  segue valido — com confianca reduzida e stop = amplitude.")

    return "\\n".join(linhas)


def bloco_decisao(dec: dict) -> str:
'''

# 3) Chama _obter_spot_mt5() em montar_snapshot
PY_ANCHOR_SPOT_ANTIGO = (
    '    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")\n'
    '\n'
    '    # Le o prompt do arquivo (se existir)\n'
)

PY_ANCHOR_SPOT_NOVO = '''    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Spot real do MT5 no instante da geracao (contorna defasagem do Bloco A)
    spot = _obter_spot_mt5()
    if spot:
        print(f"[DIAG] Spot MT5: {spot['simbolo']} last={spot['last']} "
              f"bid={spot['bid']} ask={spot['ask']}")

    # Le o prompt do arquivo (se existir)
'''

# 4) Insere bloco E.5 no output entre vela10 e decisao
PY_ANCHOR_OUT_ANTIGO = (
    '        bloco_vela10(vela),\n'
    '        "",\n'
    '        bloco_decisao(decisao),\n'
)

PY_ANCHOR_OUT_NOVO = '''        bloco_vela10(vela),
        "",
        bloco_risco_orb(vela, spot),
        "",
        bloco_decisao(decisao),
'''

# ---------------------------------------------------------------------------
# PATCH no Prompt_Rompimento_10h.txt
# ---------------------------------------------------------------------------

PROMPT_ANTIGO = (
    'Se ALINHAMENTO = DIVERGENTE, VIES FINAL deve ser AGUARDAR (regra 3).\n'
)

PROMPT_NOVO = '''Se ALINHAMENTO = DIVERGENTE:
    - Se o preco esta DENTRO da faixa ORB (sem gatilho): VIES FINAL = AGUARDAR.
    - Se o preco JA ROMPEU e a distancia do gatilho > 150 pts:
      VIES FINAL = AGUARDAR (entrada tardia inviavel).
    - Se o preco ACABOU de romper (distancia < 150 pts do gatilho):
      o gatilho mecanico ORB permanece VALIDO. Reporte com confianca
      reduzida em 40% e sinalize em ALERTAS que o stop = amplitude da
      vela 10:00 (R:R ≈ 1 por design). Nao force AGUARDAR.
'''

# ---------------------------------------------------------------------------

PATCHES_PY = [
    ("adiciona _obter_spot_mt5()", PY_ANCHOR_FUNC_ANTIGO, PY_ANCHOR_FUNC_NOVO),
    ("adiciona bloco_risco_orb()", PY_ANCHOR_BLOCO_ANTIGO, PY_ANCHOR_BLOCO_NOVO),
    ("chama _obter_spot_mt5() em montar_snapshot", PY_ANCHOR_SPOT_ANTIGO, PY_ANCHOR_SPOT_NOVO),
    ("insere E.5 entre vela10 e decisao", PY_ANCHOR_OUT_ANTIGO, PY_ANCHOR_OUT_NOVO),
]

PATCHES_PROMPT = [
    ("reescreve regra 3.5 (divergencia nao forca AGUARDAR)", PROMPT_ANTIGO, PROMPT_NOVO),
]

IGNORAR = {"fix22.py"}


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar_patches(alvo: Path, patches, dry_run: bool) -> int:
    if not alvo.exists():
        print(f"[ERRO] {alvo.name} nao encontrado em {alvo.parent}")
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


def aplicar(dry_run: bool) -> int:
    print(f"\n[ALVO 1] {ALVO_PY.name}")
    r1 = _aplicar_patches(ALVO_PY, PATCHES_PY, dry_run)

    print(f"\n[ALVO 2] {ALVO_PROMPT}")
    r2 = _aplicar_patches(ALVO_PROMPT, PATCHES_PROMPT, dry_run)

    return 0 if (r1 == 0 and r2 == 0) else max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_PY, ALVO_PROMPT):
        if not alvo.exists():
            print(f"[ERRO] {alvo.name} nao encontrado.")
            continue
        bak = _ultimo_backup(alvo)
        if not bak:
            print(f"[ERRO] {alvo.name}: nenhum backup.")
            continue
        shutil.copy2(bak, alvo)
        print(f"[REVERTER] {alvo.name} restaurado de {bak.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reverter", action="store_true")
    args = ap.parse_args()
    return reverter() if args.reverter else aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())