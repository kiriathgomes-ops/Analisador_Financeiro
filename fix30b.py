"""
fix30b.py — Gerar_Relatorio_Mensagem.py: move derivadas para executar()

Complemento do fix30. O fix30 recarregou as variaveis brutas dentro de
executar(), mas os campos derivados (gatilho, stop, alvos, teorico, etc)
continuam no nivel de modulo — calculados uma unica vez no import.

Este fix move o bloco de derivacoes (linhas 68-107 originais) para dentro
de executar(), garantindo que cada chamada use o estado fresco.

Uso:
    python fix30b.py --dry-run
    python fix30b.py
    python fix30b.py --reverter
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "Gerar_Relatorio_Mensagem.py"

# Bloco que precisa SAIR do nivel modulo
P_BLOCO_ANTIGO = '''# Extração de Decisão e Targets
vies_final = obj_decisao.get("vies_final") or "NEUTRO"
confianca = obj_decisao.get("confianca", 0)
icone_confianca = "🔴" if confianca >= 80 else ("🟡" if confianca >= 50 else "⚪")

gatilho = obj_decisao.get("gatilho") or obj_decisao.get("entrada") or obj_decisao.get("entrada_sugerida") or meta_decisao.get("entrada", 0.0)
stop = obj_decisao.get("stop") or obj_decisao.get("stop_loss") or meta_decisao.get("stop", 0.0)

alvos = obj_decisao.get("alvos") or meta_decisao.get("alvos", [])
alvo_1 = alvos[0] if isinstance(alvos, list) and len(alvos) > 0 else (obj_decisao.get("alvo_1") or 0.0)

# Extração de Estimativas de Abertura & Cost of Carry
win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE") or estimativas.get("estimativa_abertura", {}).get("WIN_FUT") or {}
teorico = win_est.get("abertura_teorica_pontos") or resultado_operacional.get("previsao_abertura", {}).get("teorico_win") or meta_decisao.get("teorico_win", 0.0)
teorico_str = f"{teorico:,.0f} pts" if isinstance(teorico, (int, float)) and teorico > 0 else "—"

coc_dados = win_est.get("cost_of_carry", {})
preco_carregado = coc_dados.get("preco_teorico_carregado", 0.0)
carregado_str = f"{preco_carregado:,.0f} pts" if isinstance(preco_carregado, (int, float)) and preco_carregado > 0 else "—"

var_est = win_est.get("variacao_teorica_pct") or resultado_operacional.get("previsao_abertura", {}).get("variacao_estimada", 0.0)
var_est_str = f"{var_est:+.2f}%"

ajuste = meta_decisao.get("ajuste") or ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)
ajuste_str = f"{ajuste:,.0f} pts" if isinstance(ajuste, (int, float)) and ajuste > 0 else "— pts"

# Pivôs Clássicos e Nivéis Institucionais (SMC)
pivots = estimativas.get("pivot_points", {}).get("WIN_FUT") or meta_decisao.get("pivots") or {}
niveis_inst = smc_dados.get("niveis_institucionais", {}) or estimativas.get("pivots_institucionais", {})
poc_ontem = niveis_inst.get("poc_ontem", 0.0)
vwap_ontem = niveis_inst.get("vwap_ontem", 0.0)

poc_str = f"{poc_ontem:,.0f} pts" if isinstance(poc_ontem, (int, float)) and poc_ontem > 0 else "—"
vwap_str = f"{vwap_ontem:,.1f} pts" if isinstance(vwap_ontem, (int, float)) and vwap_ontem > 0 else "—"

# Termômetro Macro
vix_val = get_preco_str("VIX")
iron_val = get_preco_str("IRON_ORE")
oil_val = get_preco_str("CRUDE_OIL")
di27_val = get_var_str("DI1_2027")
di29_val = get_var_str("DI1_2029")
'''

P_BLOCO_NOVO = '''# Extração de Decisão e Targets
# FIX30b: este bloco agora roda DENTRO de executar() (antes ficava no
# nivel de modulo, congelando os valores do import).
def _calcular_derivados():
    """Calcula todos os campos derivados a partir das vars globais."""
    vies_final = obj_decisao.get("vies_final") or "NEUTRO"
    confianca = obj_decisao.get("confianca", 0)
    icone_confianca = "🔴" if confianca >= 80 else ("🟡" if confianca >= 50 else "⚪")

    gatilho = obj_decisao.get("gatilho") or obj_decisao.get("entrada") or obj_decisao.get("entrada_sugerida") or meta_decisao.get("entrada", 0.0)
    stop = obj_decisao.get("stop") or obj_decisao.get("stop_loss") or meta_decisao.get("stop", 0.0)

    alvos = obj_decisao.get("alvos") or meta_decisao.get("alvos", [])
    alvo_1 = alvos[0] if isinstance(alvos, list) and len(alvos) > 0 else (obj_decisao.get("alvo_1") or 0.0)

    win_est = estimativas.get("estimativa_abertura", {}).get("WIN_INDICE") or estimativas.get("estimativa_abertura", {}).get("WIN_FUT") or {}
    teorico = win_est.get("abertura_teorica_pontos") or resultado_operacional.get("previsao_abertura", {}).get("teorico_win") or meta_decisao.get("teorico_win", 0.0)
    teorico_str = f"{teorico:,.0f} pts" if isinstance(teorico, (int, float)) and teorico > 0 else "—"

    coc_dados = win_est.get("cost_of_carry", {})
    preco_carregado = coc_dados.get("preco_teorico_carregado", 0.0)
    carregado_str = f"{preco_carregado:,.0f} pts" if isinstance(preco_carregado, (int, float)) and preco_carregado > 0 else "—"

    var_est = win_est.get("variacao_teorica_pct") or resultado_operacional.get("previsao_abertura", {}).get("variacao_estimada", 0.0)
    var_est_str = f"{var_est:+.2f}%"

    ajuste = meta_decisao.get("ajuste") or ativos.get("WIN_AJUSTE", {}).get("preco", 0.0)
    ajuste_str = f"{ajuste:,.0f} pts" if isinstance(ajuste, (int, float)) and ajuste > 0 else "— pts"

    pivots = estimativas.get("pivot_points", {}).get("WIN_FUT") or meta_decisao.get("pivots") or {}
    niveis_inst = smc_dados.get("niveis_institucionais", {}) or estimativas.get("pivots_institucionais", {})
    poc_ontem = niveis_inst.get("poc_ontem", 0.0)
    vwap_ontem = niveis_inst.get("vwap_ontem", 0.0)

    poc_str = f"{poc_ontem:,.0f} pts" if isinstance(poc_ontem, (int, float)) and poc_ontem > 0 else "—"
    vwap_str = f"{vwap_ontem:,.1f} pts" if isinstance(vwap_ontem, (int, float)) and vwap_ontem > 0 else "—"

    vix_val = get_preco_str("VIX")
    iron_val = get_preco_str("IRON_ORE")
    oil_val = get_preco_str("CRUDE_OIL")
    di27_val = get_var_str("DI1_2027")
    di29_val = get_var_str("DI1_2029")

    return {
        "vies_final": vies_final,
        "confianca": confianca,
        "icone_confianca": icone_confianca,
        "gatilho": gatilho,
        "stop": stop,
        "alvos": alvos,
        "alvo_1": alvo_1,
        "teorico_str": teorico_str,
        "carregado_str": carregado_str,
        "var_est_str": var_est_str,
        "ajuste_str": ajuste_str,
        "pivots": pivots,
        "poc_str": poc_str,
        "vwap_str": vwap_str,
        "vix_val": vix_val,
        "iron_val": iron_val,
        "oil_val": oil_val,
        "di27_val": di27_val,
        "di29_val": di29_val,
    }
'''

# 2) injeta _calcular_derivados() no inicio de executar()
P_EXEC_ANTIGO = '''def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)

    # --- FIX: carrega JSONs frescos AGORA (nao mais no import) ---
    global ativos, obj_decisao, meta_decisao
    global estimativas, resultado_operacional, smc_dados

    estado = _carregar_estado()
    ativos = estado["ativos"]
    obj_decisao = estado["obj_decisao"]
    meta_decisao = estado["meta_decisao"]
    estimativas = estado["estimativas"]
    resultado_operacional = estado["resultado_operacional"]
    smc_dados = estado["smc_dados"]

    # Recalcula os campos derivados (eram calculados no nivel modulo)
    vies_final = obj_decisao.get("vies_final") or "NEUTRO"
    confianca = obj_decisao.get("confianca", 0)

    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
'''

P_EXEC_NOVO = '''def executar():
    print("=" * 60)
    print("🚀 INICIANDO GERADOR DE RELATÓRIO OPERACIONAL EXECUTIVO (V2)")
    print("=" * 60)

    # --- FIX30 + FIX30b: recarrega estado E recalcula derivados ---
    global ativos, obj_decisao, meta_decisao
    global estimativas, resultado_operacional, smc_dados

    estado = _carregar_estado()
    ativos = estado["ativos"]
    obj_decisao = estado["obj_decisao"]
    meta_decisao = estado["meta_decisao"]
    estimativas = estado["estimativas"]
    resultado_operacional = estado["resultado_operacional"]
    smc_dados = estado["smc_dados"]

    # Recalcula TODOS os derivados (gatilho, stop, alvos, teorico, etc)
    _d = _calcular_derivados()
    vies_final = _d["vies_final"]
    confianca = _d["confianca"]
    icone_confianca = _d["icone_confianca"]
    gatilho = _d["gatilho"]
    stop = _d["stop"]
    alvos = _d["alvos"]
    alvo_1 = _d["alvo_1"]
    teorico_str = _d["teorico_str"]
    carregado_str = _d["carregado_str"]
    var_est_str = _d["var_est_str"]
    ajuste_str = _d["ajuste_str"]
    pivots = _d["pivots"]
    poc_str = _d["poc_str"]
    vwap_str = _d["vwap_str"]
    vix_val = _d["vix_val"]
    iron_val = _d["iron_val"]
    oil_val = _d["oil_val"]
    di27_val = _d["di27_val"]
    di29_val = _d["di29_val"]

    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
'''

PATCHES = [
    ("bloco de derivados -> _calcular_derivados()", P_BLOCO_ANTIGO, P_BLOCO_NOVO),
    ("executar() recalcula derivados frescos", P_EXEC_ANTIGO, P_EXEC_NOVO),
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