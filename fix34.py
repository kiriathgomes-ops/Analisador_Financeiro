"""
fix34.py — Colore cards MTF (ALTA verde / BAIXA vermelho)

Altera as duas paginas que receberam o card MTF:
    - pages/2_🎯_Setup_Abertura.py              (fix28)
    - pages/1_⚡_Dashboard_Leilao_AoVivo.py     (fix32)

Substitui os st.metric() do bloco MTF por st.markdown com HTML colorido:
    ALTA / COMPRA / BULL  -> verde   (#22c55e)
    BAIXA / VENDA / BEAR  -> vermelho (#ef4444)
    outros                -> cinza   (#a3a3a3)

Uso:
    python fix34.py --dry-run
    python fix34.py
    python fix34.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_SETUP = ROOT / "pages" / "2_🎯_Setup_Abertura.py"
ALVO_DASH = ROOT / "pages" / "1_⚡_Dashboard_Leilao_AoVivo.py"

# ===========================================================================
# PATCH A — Setup_Abertura.py
# ===========================================================================
SETUP_ANTIGO = '''            _cols = st.columns(3)
            with _cols[0]:
                st.metric("M15 (macro)", f"{_b15}", f"{_c15}%" if _c15 is not None else None)
            with _cols[1]:
                st.metric("M5 (médio)", f"{_b5}", f"{_c5}%" if _c5 is not None else None)
            with _cols[2]:
                st.metric("M1 (micro)", f"{_b1}", f"{_c1}%" if _c1 is not None else None)
'''

SETUP_NOVO = '''            def _cor_bias(_b):
                _s = str(_b or "").upper()
                if "ALTA" in _s or "COMPRA" in _s or "BULL" in _s:
                    return "#22c55e"
                if "BAIXA" in _s or "VENDA" in _s or "BEAR" in _s:
                    return "#ef4444"
                return "#a3a3a3"

            def _card_bias(col, label, bias, conf):
                _cor = _cor_bias(bias)
                _conf = f"{conf}%" if conf is not None else "—"
                with col:
                    st.markdown(
                        f"<div style='padding:10px 14px;border-radius:8px;"
                        f"background:rgba(255,255,255,0.03);"
                        f"border-left:3px solid {_cor};'>"
                        f"<div style='font-size:0.85rem;color:#9ca3af;'>{label}</div>"
                        f"<div style='font-size:1.5rem;font-weight:700;color:{_cor};"
                        f"line-height:1.2;margin-top:2px;'>{bias}</div>"
                        f"<div style='font-size:0.8rem;color:#6b7280;margin-top:2px;'>"
                        f"Confiança: {_conf}</div></div>",
                        unsafe_allow_html=True,
                    )

            _cols = st.columns(3)
            _card_bias(_cols[0], "M15 (macro)", _b15, _c15)
            _card_bias(_cols[1], "M5 (médio)", _b5, _c5)
            _card_bias(_cols[2], "M1 (micro)", _b1, _c1)
'''

# ===========================================================================
# PATCH B — Dashboard_Leilao_AoVivo.py
# ===========================================================================
DASH_ANTIGO = '''            _ccols = st.columns(3)
            with _ccols[0]:
                st.metric("M15 (macro)", f"{_b15}",
                          f"{_c15}%" if _c15 is not None else None)
            with _ccols[1]:
                st.metric("M5 (médio)", f"{_b5}",
                          f"{_c5}%" if _c5 is not None else None)
            with _ccols[2]:
                st.metric("M1 (micro)", f"{_b1}",
                          f"{_c1}%" if _c1 is not None else None)
'''

DASH_NOVO = '''            def _cor_bias(_b):
                _s = str(_b or "").upper()
                if "ALTA" in _s or "COMPRA" in _s or "BULL" in _s:
                    return "#22c55e"
                if "BAIXA" in _s or "VENDA" in _s or "BEAR" in _s:
                    return "#ef4444"
                return "#a3a3a3"

            def _card_bias(col, label, bias, conf):
                _cor = _cor_bias(bias)
                _conf = f"{conf}%" if conf is not None else "—"
                with col:
                    st.markdown(
                        f"<div style='padding:10px 14px;border-radius:8px;"
                        f"background:rgba(255,255,255,0.03);"
                        f"border-left:3px solid {_cor};'>"
                        f"<div style='font-size:0.85rem;color:#9ca3af;'>{label}</div>"
                        f"<div style='font-size:1.5rem;font-weight:700;color:{_cor};"
                        f"line-height:1.2;margin-top:2px;'>{bias}</div>"
                        f"<div style='font-size:0.8rem;color:#6b7280;margin-top:2px;'>"
                        f"Confiança: {_conf}</div></div>",
                        unsafe_allow_html=True,
                    )

            _ccols = st.columns(3)
            _card_bias(_ccols[0], "M15 (macro)", _b15, _c15)
            _card_bias(_ccols[1], "M5 (médio)", _b5, _c5)
            _card_bias(_ccols[2], "M1 (micro)", _b1, _c1)
'''

PATCHES_SETUP = [("Setup_Abertura: colore cards MTF", SETUP_ANTIGO, SETUP_NOVO)]
PATCHES_DASH = [("Dashboard_Leilao: colore cards MTF", DASH_ANTIGO, DASH_NOVO)]


def _backup(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".bak_{ts}")
    shutil.copy2(p, bak)
    return bak


def _ultimo_backup(p: Path):
    baks = sorted(p.parent.glob(p.name + ".bak_*"))
    return baks[-1] if baks else None


def _aplicar(alvo: Path, patches, dry_run: bool) -> int:
    if not alvo.exists():
        print(f"[ERRO] {alvo} nao encontrado")
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
    print(f"\n[ALVO 1] {ALVO_SETUP.name}")
    r1 = _aplicar(ALVO_SETUP, PATCHES_SETUP, dry_run)

    print(f"\n[ALVO 2] {ALVO_DASH.name}")
    r2 = _aplicar(ALVO_DASH, PATCHES_DASH, dry_run)

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] fix34 aplicado.")
        return 0
    return max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_SETUP, ALVO_DASH):
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