"""
fix24.py — Alinha referencia de preco (WIN_FUT vs spot MT5)

Contexto (teste 4 IAs, 21/09):
    O template do prompt pedia "Preco atual (WIN_FUT)" — mas a regra
    de referencia mandava usar o spot MT5 do Bloco E.5. Resultado:
    5 das 7 IAs resolveram a divergencia escolhendo o WIN_FUT (defasado)
    e reportaram NAO_OCORREU quando o rompimento ja havia acontecido.

Fix:
    A) analisar_rompimento_10h.py
       bloco_risco_orb() recebe WIN_FUT (Bloco A) e emite alerta
       automatico "DIVERGENCIA DE REFERENCIA" quando |spot - WIN_FUT| > 100.

    B) PromptIA/Prompt_Rompimento_10h.txt
       1) Template: "Preco atual (WIN_FUT)" -> "Preco atual (spot MT5)"
       2) Regra de referencia v2: spot MT5 e primario, WIN_FUT e fallback
       3) Linha do estado do rompimento: usa spot MT5 do E.5

Uso:
    python fix24.py --dry-run
    python fix24.py
    python fix24.py --reverter
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

PY_SIG_ANTIGO = (
    'def bloco_risco_orb(vela: dict, spot: dict, ajuste: float = None) -> str:\n'
)

PY_SIG_NOVO = (
    'def bloco_risco_orb(vela: dict, spot: dict, ajuste: float = None, win_fut: float = None) -> str:\n'
)

PY_DIV_ANTIGO = '''        f"  Preco spot MT5     : {fmt(preco_ref, 0) if preco_ref else '—'}   ({fonte_ref})",
    ]

    if preco_ref:
        if preco_ref > M:
'''

PY_DIV_NOVO = '''        f"  Preco spot MT5     : {fmt(preco_ref, 0) if preco_ref else '—'}   ({fonte_ref})",
    ]

    # --- Alerta automatico de divergencia WIN_FUT vs spot MT5 ---
    if preco_ref and win_fut and abs(preco_ref - win_fut) > 100:
        delta = preco_ref - win_fut
        linhas.append("")
        linhas.append("  DIVERGENCIA DE REFERENCIA:")
        linhas.append(f"    WIN_FUT (Bloco A) : {fmt(win_fut, 0)}")
        linhas.append(f"    Spot MT5 (E.5)    : {fmt(preco_ref, 0)}")
        linhas.append(f"    Delta             : {fmt(delta, 0)} pts")
        linhas.append("    -> Use spot MT5 como verdade. WIN_FUT pode estar defasado.")

    if preco_ref:
        if preco_ref > M:
'''

PY_EXTRACAO_ANTIGO = '''    # Ajuste B3 (para checagem da Regra 10 no Bloco E.5)
    _aj = ((ativos.get("ativos") or {}).get("WIN_AJUSTE") or {}).get("preco")
    try:
        ajuste_b3 = float(_aj) if _aj else None
    except (TypeError, ValueError):
        ajuste_b3 = None
    if ajuste_b3:
        print(f"[DIAG] Ajuste B3: {ajuste_b3}")
'''

PY_EXTRACAO_NOVO = '''    # Ajuste B3 (para checagem da Regra 10 no Bloco E.5)
    _aj = ((ativos.get("ativos") or {}).get("WIN_AJUSTE") or {}).get("preco")
    try:
        ajuste_b3 = float(_aj) if _aj else None
    except (TypeError, ValueError):
        ajuste_b3 = None
    if ajuste_b3:
        print(f"[DIAG] Ajuste B3: {ajuste_b3}")

    # WIN_FUT (Bloco A) — para deteccao de divergencia vs spot MT5 no E.5
    _wf = ((ativos.get("ativos") or {}).get("WIN_FUT") or {}).get("preco")
    try:
        win_fut = float(_wf) if _wf else None
    except (TypeError, ValueError):
        win_fut = None
'''

PY_CALL_ANTIGO = '        bloco_risco_orb(vela, spot, ajuste_b3),\n'
PY_CALL_NOVO = '        bloco_risco_orb(vela, spot, ajuste_b3, win_fut),\n'

PATCHES_PY = [
    ("bloco_risco_orb aceita win_fut", PY_SIG_ANTIGO, PY_SIG_NOVO),
    ("bloco_risco_orb emite alerta de divergencia", PY_DIV_ANTIGO, PY_DIV_NOVO),
    ("montar_snapshot extrai WIN_FUT", PY_EXTRACAO_ANTIGO, PY_EXTRACAO_NOVO),
    ("chama bloco_risco_orb com win_fut", PY_CALL_ANTIGO, PY_CALL_NOVO),
]

# ---------------------------------------------------------------------------
# PATCHES no Prompt_Rompimento_10h.txt
# ---------------------------------------------------------------------------

# P1) Template: WIN_FUT -> spot MT5
P_TEMPLATE_ANTIGO = "Preco atual (WIN_FUT): XXX,XXX\n"
P_TEMPLATE_NOVO = "Preco atual (spot MT5): XXX,XXX\n"

# P2) Linha do estado do rompimento usa spot MT5
P_ESTADO_ANTIGO = (
    "Compare o preco ATUAL (WIN_FUT no Bloco A) com os gatilhos M e m:\n"
)
P_ESTADO_NOVO = (
    "Compare o preco ATUAL (spot MT5 do Bloco E.5) com os gatilhos M e m:\n"
)

# P3) Regra de referencia v2
P_REGRA_ANTIGO = '''**PRECO ATUAL — REGRA DE REFERENCIA:**

Use o campo WIN_FUT (Bloco A) como referencia primaria do "preco atual".
E o preco ao vivo do contrato principal no MT5.

Se WIN_FUT estiver ausente/zerado, use WIN_LAST_TICK como fallback —
mas sinalize no ALERTA que a referencia pode estar defasada.

IGNORE WIN_FECHAMENTO_B3 (e apenas o fechamento oficial do dia anterior).
'''

P_REGRA_NOVO = '''**PRECO ATUAL — REGRA DE REFERENCIA (v2):**

Fonte PRIMARIA: "Preco spot MT5" do BLOCO E.5 (lido no instante
da geracao do snapshot). Este e o preco vivo no momento da analise.

Fonte SECUNDARIA: WIN_FUT (Bloco A) — pode estar defasado em ate
5 minutos porque vem do DadosAtivosUnificados.json.

Regra:
  - Se os dois divergirem <= 100 pts: use o spot MT5.
  - Se os dois divergirem > 100 pts: o proprio BLOCO E.5 emite um
    alerta "DIVERGENCIA DE REFERENCIA". Nesse caso, use o spot MT5
    como verdade e sinalize em ALERTAS.
  - Se spot MT5 estiver ausente/zerado: use WIN_FUT como fallback
    e sinalize em ALERTAS que a referencia pode estar defasada.

IGNORE WIN_FECHAMENTO_B3 (e apenas o fechamento oficial do dia anterior).
'''

PATCHES_PROMPT = [
    ("template: Preco atual (spot MT5)", P_TEMPLATE_ANTIGO, P_TEMPLATE_NOVO),
    ("estado do rompimento usa spot MT5", P_ESTADO_ANTIGO, P_ESTADO_NOVO),
    ("regra de referencia v2", P_REGRA_ANTIGO, P_REGRA_NOVO),
]

IGNORAR = {"fix24.py"}

# ---------------------------------------------------------------------------


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

    print(f"\n[ALVO 2] {ALVO_PROMPT.name}")
    r2 = _aplicar_patches(ALVO_PROMPT, PATCHES_PROMPT, dry_run)

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] Todos os patches aplicados.")
        return 0
    return max(r1, r2)


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