"""
fix40.py — SMC_Regras: adiciona gráficos M1 e M15 (multi-timeframe visual)

Objetivo:
    Empilhar 3 gráficos de candlestick na página SMC_Regras (M1 → M5 → M15),
    cada um com as zonas SMC do seu timeframe (OBs, FVGs, liquidez, POC/VWAP,
    swings, eventos). Permite ver visualmente o bias de cada TF, não só texto.

Mudanças:
    A) config.py — adiciona FILE_SMC_M1 e FILE_SMC_M15
    B) pages/7.1_📊_SMC_Regras.py
       - Constantes de candles por TF
       - render_grafico_candles aceita timeframe_min + tf_label
       - Sombreia globais (vies, confianca, preco_atual) com dados do dict
       - Substitui bloco único por loop de 3 charts empilhados

Uso:
    python fix40.py --dry-run
    python fix40.py
    python fix40.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO_CFG = ROOT / "config.py"
ALVO_PG = ROOT / "pages" / "7.1_📊_SMC_Regras.py"

# ===========================================================================
# PATCH config.py
# ===========================================================================
CFG_ANTIGO = (
    'FILE_SMC_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"\n'
    'FILE_SMC_MTF = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"\n'
)

CFG_NOVO = (
    'FILE_SMC_REGRAS = COLETAS_DIR / "AnaliseGraficaSMC_Regras.json"\n'
    'FILE_SMC_MTF = COLETAS_DIR / "AnaliseGraficaSMC_MTF.json"\n'
    'FILE_SMC_M1 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M1.json"\n'
    'FILE_SMC_M15 = COLETAS_DIR / "AnaliseGraficaSMC_Regras_M15.json"\n'
)

PATCHES_CFG = [("adiciona FILE_SMC_M1 + FILE_SMC_M15", CFG_ANTIGO, CFG_NOVO)]

# ===========================================================================
# PATCH page — constants
# ===========================================================================
PG_CONST_ANTIGO = (
    'QTD_CANDLES_PADRAO = 30              # Padrão: 30 candles M5 (~2.5 horas de pregão)\n'
    'OPCOES_CANDLES = [30, 60, 100, 150, 200]\n'
)

PG_CONST_NOVO = '''QTD_CANDLES_PADRAO = 30              # Padrão (compat M5): 30 candles (~2.5h)
OPCOES_CANDLES = [30, 60, 100, 150, 200]

# Defaults por timeframe (fix40 — multi-TF visual)
# chave = timeframe em minutos; valor = quantidade de candles inicial
QTD_CANDLES_POR_TF = {
    1:  60,   # M1:  1h de leitura micro
    5:  30,   # M5:  2.5h (mantém o atual)
    15: 20,   # M15: 5h de leitura macro
}
OPCOES_CANDLES_POR_TF = {
    1:  [30, 60, 120, 180, 240],
    5:  [30, 60, 100, 150, 200],
    15: [10, 20, 40, 60, 80],
}
'''

PATCHES_PG_1 = [("adiciona defaults por TF", PG_CONST_ANTIGO, PG_CONST_NOVO)]

# ===========================================================================
# PATCH page — signature + shadow globals
# ===========================================================================
PG_SIG_ANTIGO = (
    'def render_grafico_candles(dados: dict, qtd_visivel: int = QTD_CANDLES_PADRAO) -> go.Figure:\n'
)

PG_SIG_NOVO = '''def render_grafico_candles(
    dados: dict,
    qtd_visivel: int = QTD_CANDLES_PADRAO,
    timeframe_min: int = 5,
    tf_label: str = "M5",
) -> go.Figure:
    # --- fix40: usa dados do dict, não globais (bug latente corrigido) ---
    vies = dados.get("bias_direcional", "LATERAL")
    confianca = dados.get("confianca_visual", 0)
    preco_atual = dados.get("preco_atual", 0.0)
'''

PATCHES_PG_2 = [("render_grafico_candles parametrizado", PG_SIG_ANTIGO, PG_SIG_NOVO)]

# ===========================================================================
# PATCH page — docstring + hardcode do timeframe
# ===========================================================================
PG_DOC_ANTIGO = (
    '    Parâmetros:\n'
    '        qtd_visivel: número de candles M5 exibidos (foco nas últimas pernadas).\n'
    '    """'
)

PG_DOC_NOVO = (
    '    Parâmetros:\n'
    '        qtd_visivel: número de candles exibidos (foco nas últimas pernadas).\n'
    '        timeframe_min: timeframe em minutos (1, 5, 15).\n'
    '        tf_label: rótulo do TF para título (ex: "M5", "M15").\n'
    '    """'
)

PATCHES_PG_3 = [("docstring explica timeframe", PG_DOC_ANTIGO, PG_DOC_NOVO)]

PG_LOAD_ANTIGO = (
    '    candles, simbolo_ok = carregar_candles_mt5("WIN$", 5, 200)\n'
)

PG_LOAD_NOVO = (
    '    candles, simbolo_ok = carregar_candles_mt5("WIN$", timeframe_min, 200)\n'
)

PATCHES_PG_4 = [("carregar_candles_mt5 usa timeframe_min", PG_LOAD_ANTIGO, PG_LOAD_NOVO)]

# ===========================================================================
# PATCH page — título do chart (M5 hardcoded)
# ===========================================================================
PG_TIT_ANTIGO = (
    '            text=f"<b>WIN M5 — Zonas Institucionais SMC</b> · "\n'
)

PG_TIT_NOVO = (
    '            text=f"<b>WIN {tf_label} — Zonas Institucionais SMC</b> · "\n'
)

PATCHES_PG_5 = [("título usa tf_label", PG_TIT_ANTIGO, PG_TIT_NOVO)]

# ===========================================================================
# PATCH page — bloco de render (single → 3 empilhados)
# ===========================================================================
PG_RENDER_ANTIGO = '''fig_smc = render_grafico_candles(dados_smc, qtd_visivel=qtd_visivel)
st.plotly_chart(fig_smc, use_container_width=True, config={"displayModeBar": False})
'''

PG_RENDER_NOVO = '''# ==============================================================================
# MULTI-TIMEFRAME VISUAL (fix40): M1 → M5 → M15 empilhados
# ==============================================================================
def _carregar_dados_tf(tf_min: int) -> dict:
    """Carrega o JSON do SMC correspondente ao timeframe."""
    from config import FILE_SMC_M1, FILE_SMC_M15, FILE_SMC_REGRAS
    mapa = {1: FILE_SMC_M1, 5: FILE_SMC_REGRAS, 15: FILE_SMC_M15}
    return carregar_json_defensivo(mapa.get(tf_min, FILE_SMC_REGRAS))


def _render_bloco_tf(tf_min: int, tf_label: str) -> None:
    """Renderiza header + seletor + gráfico de um timeframe."""
    dados_tf = _carregar_dados_tf(tf_min)

    st.markdown(f"### 🕯️ {tf_label} — Zonas SMC")

    if not dados_tf or "erro" in dados_tf:
        st.warning(
            f"⚠️ Arquivo SMC de {tf_label} não disponível. "
            f"Rode `python Rodar_SMC_Regras.py` pra gerar."
        )
        return

    # Cabeçalho com bias + confiança deste TF
    _bias_tf = dados_tf.get("bias_direcional", "LATERAL")
    _conf_tf = dados_tf.get("confianca_visual", 0)
    _cor = "#00ff88" if _bias_tf == "ALTA" else ("#ff6b6b" if _bias_tf == "BAIXA" else "#ccc")
    st.markdown(
        f"<div style='padding:6px 12px; border-left:4px solid {_cor}; "
        f"background:rgba(255,255,255,0.03); border-radius:6px;'>"
        f"Viés {tf_label}: <b style='color:{_cor};'>{_bias_tf}</b> · "
        f"Confiança: <b>{_conf_tf}%</b></div>",
        unsafe_allow_html=True,
    )

    # Seletor de candles deste TF
    _opcoes = OPCOES_CANDLES_POR_TF.get(tf_min, [30, 60, 100])
    _default = QTD_CANDLES_POR_TF.get(tf_min, 30)
    _qtd = st.selectbox(
        f"Candles visíveis ({tf_label}):",
        options=_opcoes,
        index=_opcoes.index(_default) if _default in _opcoes else 0,
        key=f"smc_qtd_tf_{tf_min}",
    )

    # Renderiza
    fig_tf = render_grafico_candles(
        dados_tf,
        qtd_visivel=_qtd,
        timeframe_min=tf_min,
        tf_label=tf_label,
    )
    st.plotly_chart(
        fig_tf,
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"plot_tf_{tf_min}",
    )


st.markdown("---")
st.markdown("## 📊 Visão Multi-Timeframe (M1 · M5 · M15)")
st.caption(
    "Sequência **micro → médio → macro**. Cada gráfico mostra as zonas SMC "
    "do timeframe correspondente, permitindo leitura visual da confluência."
)

# M1 (micro)
_render_bloco_tf(1, "M1")

st.markdown("<br>", unsafe_allow_html=True)

# M5 (médio — mantém comportamento atual)
_render_bloco_tf(5, "M5")

st.markdown("<br>", unsafe_allow_html=True)

# M15 (macro)
_render_bloco_tf(15, "M15")
'''

PATCHES_PG_6 = [("single chart -> 3 charts empilhados", PG_RENDER_ANTIGO, PG_RENDER_NOVO)]

# ===========================================================================


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
        print(f"[ERRO] {alvo} não encontrado")
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
        print(f"\n[ABORT] {alvo.name} — padrões não encontrados:")
        for f in faltando:
            print(f"    - {f}")
        return 2

    if novo == conteudo:
        print(f"  [INFO] {alvo.name}: nada mudou.")
        return 0

    if dry_run:
        print(f"  [DRY-RUN] {alvo.name}: não salvo.")
        return 0

    bak = _backup(alvo)
    print(f"  [BACKUP] {bak.name}")
    alvo.write_text(novo, encoding="utf-8")
    print(f"  [OK] {alvo.name} atualizado.")
    return 0


def aplicar(dry_run: bool) -> int:
    print(f"\n[ALVO 1] {ALVO_CFG.name}")
    r1 = _aplicar(ALVO_CFG, PATCHES_CFG, dry_run)

    print(f"\n[ALVO 2] {ALVO_PG.name}")
    r2 = _aplicar(ALVO_PG, PATCHES_PG_1, dry_run)
    r2 = max(r2, _aplicar(ALVO_PG, PATCHES_PG_2, dry_run))
    r2 = max(r2, _aplicar(ALVO_PG, PATCHES_PG_3, dry_run))
    r2 = max(r2, _aplicar(ALVO_PG, PATCHES_PG_4, dry_run))
    r2 = max(r2, _aplicar(ALVO_PG, PATCHES_PG_5, dry_run))
    r2 = max(r2, _aplicar(ALVO_PG, PATCHES_PG_6, dry_run))

    if r1 == 0 and r2 == 0:
        print("\n[SUCESSO] fix40 aplicado.")
        return 0
    return max(r1, r2)


def reverter() -> int:
    for alvo in (ALVO_CFG, ALVO_PG):
        if not alvo.exists():
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