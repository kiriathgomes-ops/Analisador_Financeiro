"""
fix28.py — pages/2_Setup_Abertura.py: card MTF (contexto visual)

Adiciona, logo abaixo da secao SMC V2.6, um bloco que le
AnaliseGraficaSMC_MTF.json e mostra os 3 biases + veredito.

NAO altera nenhuma decisao — apenas exibe.

Uso:
    python fix28.py --dry-run
    python fix28.py
    python fix28.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "pages" / "2_🎯_Setup_Abertura.py"

# ---------------------------------------------------------------------------
# 1) Adiciona o import/carregamento do MTF
# ---------------------------------------------------------------------------
P_CARGA_ANTIGO = (
    '    smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")\n'
)

P_CARGA_NOVO = (
    '    smc_regras, _ = carregar_json_absoluto("AnaliseGraficaSMC_Regras.json")\n'
    '    smc_mtf, _ = carregar_json_absoluto("AnaliseGraficaSMC_MTF.json")\n'
)

# ---------------------------------------------------------------------------
# 2) Insere o bloco visual logo apos o "Filtros e Estruturas de Liquidez Ativas"
# ---------------------------------------------------------------------------
P_BLOCO_ANTIGO = (
    '        st.markdown("### 🧠 Filtros e Estruturas de Liquidez Ativas (SMC V2.6)")\n'
)

P_BLOCO_NOVO = '''        # ---------- MTF: contexto multi-timeframe (fix28) ----------
        if smc_mtf:
            conf = smc_mtf.get("confluencia") or {}
            _ver = conf.get("veredito_mtf") or "—"
            _dir = conf.get("direcao_dominante") or "—"
            _rac = conf.get("racional") or ""
            _b15 = conf.get("bias_m15") or "—"
            _b5 = conf.get("bias_m5") or "—"
            _b1 = conf.get("bias_m1") or "—"
            _c15 = conf.get("confianca_m15")
            _c5 = conf.get("confianca_m5")
            _c1 = conf.get("confianca_m1")

            st.markdown("### 🧭 Contexto Multi-Timeframe (M15 / M5 / M1)")

            _cols = st.columns(3)
            with _cols[0]:
                st.metric("M15 (macro)", f"{_b15}", f"{_c15}%" if _c15 is not None else None)
            with _cols[1]:
                st.metric("M5 (médio)", f"{_b5}", f"{_c5}%" if _c5 is not None else None)
            with _cols[2]:
                st.metric("M1 (micro)", f"{_b1}", f"{_c1}%" if _c1 is not None else None)

            _cor = {
                "ALINHADO_FORTE": "success",
                "PULLBACK": "info",
                "REVERSAO_MICRO_MEDIO": "warning",
                "CONFLITO_MACRO": "warning",
                "DIVERGENTE": "error",
                "NEUTRO": "info",
                "SEM_DIRECAO": "info",
            }.get(_ver, "info")

            _msg = f"**{_ver}** — direção dominante: `{_dir}`"
            if _rac:
                _msg += f"\\n\\n{_rac}"

            if _cor == "success":
                st.success(_msg)
            elif _cor == "warning":
                st.warning(_msg)
            elif _cor == "error":
                st.error(_msg)
            else:
                st.info(_msg)
        # ---------- fim MTF ----------

        st.markdown("### 🧠 Filtros e Estruturas de Liquidez Ativas (SMC V2.6)")
'''

PATCHES = [
    ("carrega smc_mtf", P_CARGA_ANTIGO, P_CARGA_NOVO),
    ("insere card MTF", P_BLOCO_ANTIGO, P_BLOCO_NOVO),
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
        print(f"[ERRO] {ALVO.name} nao encontrado em {ALVO.parent}")
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
        print("\\n[ABORT] padroes nao encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print("[INFO] nada mudou.")
        return 0

    if dry_run:
        print("\\n[DRY-RUN] nada salvo.")
        return 0

    bak = _backup(ALVO)
    print(f"\\n[BACKUP] {bak.name}")
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