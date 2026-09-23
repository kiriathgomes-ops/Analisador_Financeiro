"""
fix32.py — Dashboard_Leilao_AoVivo: card MTF (contexto multi-timeframe)

Adiciona um bloco mostrando os 3 biases (M15/M5/M1) + veredito MTF
abaixo do contexto macro/SMC existente. NAO altera nenhuma decisao
operacional — apenas exibe.

Uso:
    python fix32.py --dry-run
    python fix32.py
    python fix32.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "pages" / "1_⚡_Dashboard_Leilao_AoVivo.py"

# ---------------------------------------------------------------------------
# PATCH 1: caminho do JSON
# ---------------------------------------------------------------------------
P_CAMINHOS_ANTIGO = (
    'ARQUIVO_JSON_SMC = PASTA_COLETAS / "AnaliseGraficaSMC_Regras.json"\n'
    'ARQUIVO_JSON_ESTIMATIVA = PASTA_COLETAS / "EstimativaAbertura.json"\n'
)

P_CAMINHOS_NOVO = (
    'ARQUIVO_JSON_SMC = PASTA_COLETAS / "AnaliseGraficaSMC_Regras.json"\n'
    'ARQUIVO_JSON_MTF = PASTA_COLETAS / "AnaliseGraficaSMC_MTF.json"\n'
    'ARQUIVO_JSON_ESTIMATIVA = PASTA_COLETAS / "EstimativaAbertura.json"\n'
)

# ---------------------------------------------------------------------------
# PATCH 2: carrega MTF dentro do fragment
# ---------------------------------------------------------------------------
P_CARGA_ANTIGO = (
    '    macro_data = carregar_json(ARQUIVO_JSON_MACRO).get("ativos", {})\n'
    '    smc_data = carregar_json(ARQUIVO_JSON_SMC)\n'
    '    estimativa_calc = carregar_estimativa_calculada()\n'
    '    leilao = carregar_leilao_ocr()\n'
)

P_CARGA_NOVO = (
    '    macro_data = carregar_json(ARQUIVO_JSON_MACRO).get("ativos", {})\n'
    '    smc_data = carregar_json(ARQUIVO_JSON_SMC)\n'
    '    smc_mtf = carregar_json(ARQUIVO_JSON_MTF)\n'
    '    estimativa_calc = carregar_estimativa_calculada()\n'
    '    leilao = carregar_leilao_ocr()\n'
)

# ---------------------------------------------------------------------------
# PATCH 3: bloco visual MTF abaixo do Contexto Macro/SMC
# ---------------------------------------------------------------------------
P_BLOCO_ANTIGO = '''    with c_left:
        st.subheader("🌐 Contexto Macro / SMC")
        st.info(f"**Viés Macro:** {vies_macro}")
        st.info(f"**Viés Estrutural SMC:** {vies_smc}")
        st.text(f"Score Macro: {score_macro:+.3f}")
'''

P_BLOCO_NOVO = '''    with c_left:
        st.subheader("🌐 Contexto Macro / SMC")
        st.info(f"**Viés Macro:** {vies_macro}")
        st.info(f"**Viés Estrutural SMC:** {vies_smc}")
        st.text(f"Score Macro: {score_macro:+.3f}")

        # ---------- MTF: contexto multi-timeframe (fix32) ----------
        _conf_mtf = (smc_mtf or {}).get("confluencia") or {}
        if _conf_mtf:
            _ver = _conf_mtf.get("veredito_mtf") or "—"
            _dir = _conf_mtf.get("direcao_dominante") or "—"
            _rac = _conf_mtf.get("racional") or ""
            _b15 = _conf_mtf.get("bias_m15") or "—"
            _b5 = _conf_mtf.get("bias_m5") or "—"
            _b1 = _conf_mtf.get("bias_m1") or "—"
            _c15 = _conf_mtf.get("confianca_m15")
            _c5 = _conf_mtf.get("confianca_m5")
            _c1 = _conf_mtf.get("confianca_m1")

            st.markdown("#### 🧭 Multi-Timeframe (M15 / M5 / M1)")

            _ccols = st.columns(3)
            with _ccols[0]:
                st.metric("M15 (macro)", f"{_b15}",
                          f"{_c15}%" if _c15 is not None else None)
            with _ccols[1]:
                st.metric("M5 (médio)", f"{_b5}",
                          f"{_c5}%" if _c5 is not None else None)
            with _ccols[2]:
                st.metric("M1 (micro)", f"{_b1}",
                          f"{_c1}%" if _c1 is not None else None)

            _msg = f"**{_ver}** — direção dominante: `{_dir}`"
            if _rac:
                _msg += f"\\n\\n{_rac}"

            if _ver == "ALINHADO_FORTE":
                st.success(_msg)
            elif _ver in ("REVERSAO_MICRO_MEDIO", "CONFLITO_MACRO"):
                st.warning(_msg)
            elif _ver == "DIVERGENTE":
                st.error(_msg)
            else:
                st.info(_msg)
        # ---------- fim MTF ----------
'''

PATCHES = [
    ("adiciona ARQUIVO_JSON_MTF", P_CAMINHOS_ANTIGO, P_CAMINHOS_NOVO),
    ("carrega smc_mtf no fragment", P_CARGA_ANTIGO, P_CARGA_NOVO),
    ("insere card MTF no contexto macro/SMC", P_BLOCO_ANTIGO, P_BLOCO_NOVO),
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