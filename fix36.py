"""
fix36.py — Rodar_SMC_Regras.py: robustez quando algum TF falha

Problema: se o MT5 nao devolve candles para um dos TFs (ex: M1 vazio),
o rodar_smc pula esse TF, mas a logica de confluencia assume 3 TFs:
    - `len(direcoes) == 3` nunca true com 2 TFs
    - Cai no else -> "DIVERGENTE" mesmo se 2/2 concordam

Fix:
    - Detecta TFs presentes (por ter dados no dict `resultados`)
    - Alinhamento passa a ser `n_dir / n_tfs` dinamico
    - Novo campo "parcial": true quando n_tfs < 3
    - Novo campo "timeframes_disponiveis": lista
    - Novo veredito "PARCIAL" para 1-2 TFs divergentes
    - UI consome depois (aviso quando parcial)

Uso:
    python fix36.py --dry-run
    python fix36.py
    python fix36.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Rodar_SMC_Regras.py"

# --- 1) cabecalho da funcao + deteccao de TFs ---
INI_ANTIGO = '''def calcular_confluencia_mtf(
    r15: Dict[str, Any], r5: Dict[str, Any], r1: Dict[str, Any]
) -> Dict[str, Any]:
    b15 = _direcao(r15.get("bias_direcional", "LATERAL"))
    b5 = _direcao(r5.get("bias_direcional", "LATERAL"))
    b1 = _direcao(r1.get("bias_direcional", "LATERAL"))

    c15 = int(r15.get("confianca_visual", 0) or 0)
    c5 = int(r5.get("confianca_visual", 0) or 0)
    c1 = int(r1.get("confianca_visual", 0) or 0)

    direcoes = [b for b in (b15, b5, b1) if b in ("ALTA", "BAIXA")]

    if not direcoes:
        veredito, alinhamento, racional = (
            "NEUTRO", "SEM_DIRECAO",
            "Nenhum dos 3 TFs marcou direcao clara.",
        )
    elif len(set(direcoes)) == 1 and len(direcoes) == 3:
        veredito, alinhamento, racional = (
            "ALINHADO_FORTE", "3/3",
            f"M15, M5 e M1 em {direcoes[0]} — sinal forte.",
        )
    elif b15 == b5 and b5 != b1 and b1 in ("ALTA", "BAIXA"):'''

INI_NOVO = '''def calcular_confluencia_mtf(
    r15: Dict[str, Any], r5: Dict[str, Any], r1: Dict[str, Any]
) -> Dict[str, Any]:
    # Detecta quais TFs realmente retornaram dados (fix36)
    tfs_presentes = []
    if r15 and r15.get("bias_direcional"):
        tfs_presentes.append("15m")
    if r5 and r5.get("bias_direcional"):
        tfs_presentes.append("5m")
    if r1 and r1.get("bias_direcional"):
        tfs_presentes.append("1m")
    n_tfs = len(tfs_presentes)
    parcial = n_tfs < 3

    b15 = _direcao(r15.get("bias_direcional", "LATERAL")) if r15 else "LATERAL"
    b5 = _direcao(r5.get("bias_direcional", "LATERAL")) if r5 else "LATERAL"
    b1 = _direcao(r1.get("bias_direcional", "LATERAL")) if r1 else "LATERAL"

    c15 = int(r15.get("confianca_visual", 0) or 0) if r15 else 0
    c5 = int(r5.get("confianca_visual", 0) or 0) if r5 else 0
    c1 = int(r1.get("confianca_visual", 0) or 0) if r1 else 0

    direcoes = [b for b in (b15, b5, b1) if b in ("ALTA", "BAIXA")]
    n_dir = len(direcoes)

    if n_tfs == 0:
        veredito, alinhamento, racional = (
            "NEUTRO", "SEM_TFS",
            "Nenhum timeframe retornou dados.",
        )
    elif n_dir == 0:
        veredito, alinhamento, racional = (
            "NEUTRO", "SEM_DIRECAO",
            f"Nenhum dos {n_tfs} TFs marcou direcao clara.",
        )
    elif len(set(direcoes)) == 1 and n_dir == n_tfs and n_tfs >= 2:
        veredito, alinhamento, racional = (
            "ALINHADO_FORTE", f"{n_dir}/{n_tfs}",
            f"{', '.join(tfs_presentes)} em {direcoes[0]} — sinal forte"
            + (" (parcial)" if parcial else "") + ".",
        )
    elif n_tfs < 3:
        # Parcial: sem todas as pernas, comportamento conservador
        veredito, alinhamento, racional = (
            "PARCIAL", f"{n_dir}/{n_tfs}",
            f"Parcial: apenas {', '.join(tfs_presentes)} disponiveis. "
            f"Direcao = {direcoes[0] if direcoes else 'NEUTRO'}.",
        )
    elif b15 == b5 and b5 != b1 and b1 in ("ALTA", "BAIXA"):'''

# --- 2) troca a string antiga 'M15, M5 e M1' pelo veredito corrigido ---
# (nenhuma outra mudanca aqui)

# --- 3) adiciona novos campos ao retorno ---
RET_ANTIGO = '''    return {
        "bias_m15": b15,
        "bias_m5": b5,
        "bias_m1": b1,
        "confianca_m15": c15,
        "confianca_m5": c5,
        "confianca_m1": c1,
        "confianca_micro_medio_soma": soma_micro_medio_dbg,
        "limiar_reversao": limiar_reversao_dbg,
        "veredito_mtf": veredito,
        "alinhamento": alinhamento,
        "direcao_dominante": direcao_dom,
        "confianca_ponderada": round(conf_pond, 1),
        "racional": racional,
    }'''

RET_NOVO = '''    return {
        "bias_m15": b15,
        "bias_m5": b5,
        "bias_m1": b1,
        "confianca_m15": c15,
        "confianca_m5": c5,
        "confianca_m1": c1,
        "confianca_micro_medio_soma": soma_micro_medio_dbg,
        "limiar_reversao": limiar_reversao_dbg,
        "veredito_mtf": veredito,
        "alinhamento": alinhamento,
        "direcao_dominante": direcao_dom,
        "confianca_ponderada": round(conf_pond, 1),
        "racional": racional,
        "timeframes_disponiveis": tfs_presentes,
        "n_tfs_disponiveis": n_tfs,
        "parcial": parcial,
    }'''

PATCHES = [
    ("cabecalho detecta TFs presentes + veredito parcial", INI_ANTIGO, INI_NOVO),
    ("retorno ganha timeframes_disponiveis + parcial", RET_ANTIGO, RET_NOVO),
]


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
    novo = conteudo
    faltando = []
    for nome, old, new in PATCHES:
        if old not in novo:
            faltando.append(nome)
            continue
        novo = novo.replace(old, new, 1)
        print(f"  [PATCH OK] {nome}")

    if faltando:
        print(f"\n[ABORT] padroes nao encontrados:")
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


def reverter() -> int:
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