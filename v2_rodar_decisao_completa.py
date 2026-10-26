# ============================================================
# v2_rodar_decisao_completa.py  (raiz do projeto)
# ============================================================
# Launcher do V2 — reflete a decisão do V3.3-Pepita.
#
# IMPORTANTE (v3.3):
#   O veto da Pepita (SMC conf >= 85%) agora vive DENTRO do orquestrador
#   (v2_orchestrator._verificar_confluencia), ANTES de persistir o histórico.
#   Este launcher apenas REPORTA o resultado — não decide nada.
#
#   O guard antigo checava decisao["confianca"] (confiança FINAL ponderada
#   60/40), o que era INCORRETO: bloqueava casos em que o SMC era >= 85%
#   mas o NOVO_MOTOR derrubava a média final (ex.: 90*0.6 + 50*0.4 = 74%).
#   A Pepita é sobre o SMC, não sobre a confluência final.
#   Por isso o launcher lê:
#       decisao.metadados.confluencia.pepita_passou
#       decisao.metadados.confluencia.motivo_saida
# ============================================================

from __future__ import annotations

import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

CONFIANCA_MINIMA_SMC_PEPITA = 85.0  # apenas informativo (espelha o orquestrador)


def main() -> int:
    print("=" * 60)
    print(" V2 — Decisão Completa (Confluence + Decision + Session)")
    print("=" * 60)

    try:
        from v2.core.engines.v2_orchestrator import executar_v2
    except ImportError as e:
        print(f"❌ Import V2 falhou: {e}")
        traceback.print_exc()
        return 1

    try:
        resultado = executar_v2(salvar_historico=True)
    except Exception as e:
        print(f"❌ Erro na execução V2: {e}")
        traceback.print_exc()
        return 1

    decisao = resultado.get("decisao") or {}
    if not isinstance(decisao, dict):
        decisao = {}

    metadados = decisao.get("metadados") or {}
    confluencia = metadados.get("confluencia") or {}

    print()
    print(f"Viés final        : {decisao.get('vies_final')}")
    print(f"Confiança (final) : {decisao.get('confianca')}%")
    print(f"Entrada           : {decisao.get('entrada')}")
    print(f"Stop              : {decisao.get('stop_loss')}")
    print(f"Alvo 1 / Alvo 2   : {decisao.get('alvo_1')} / {decisao.get('alvo_2')}")
    print(f"Invalidação       : {decisao.get('invalidacao')}")

    print()
    print("--- Pepita (SMC) ---")
    print(f"SMC conf. bruta   : {confluencia.get('pepita_smc_conf_bruto')}")
    print(f"SMC conf. ajustada: {confluencia.get('pepita_smc_conf_ajustado')}")
    print(f"MTF veredito/delta: {confluencia.get('mtf_veredito')} / {confluencia.get('mtf_delta')}")
    print(f"Mínimo Pepita     : {confluencia.get('pepita_minimo', CONFIANCA_MINIMA_SMC_PEPITA)}")
    print(f"Passou Pepita?    : {confluencia.get('pepita_passou')}")
    print(f"Motivo de saída   : {confluencia.get('motivo_saida')}")

    ctx = resultado.get("contextos") or {}
    print()
    print(
        "Contextos         : "
        f"market={ctx.get('market_ok')} pred={ctx.get('prediction_ok')} "
        f"news={ctx.get('news_ok')} vision={ctx.get('vision_ok')} "
        f"session={ctx.get('session_ok')}"
    )
    erros = resultado.get("erros") or []
    if erros:
        print("Avisos:")
        for e in erros:
            print(f"   - {e}")

    # ---------- Exit code refletindo o resultado ----------
    motivo_saida = confluencia.get("motivo_saida")
    vies_final = decisao.get("vies_final")

    if motivo_saida == "pepita_smc_abaixo_minimo":
        print()
        print(
            f"🚫 VETO PEPITA: SMC conf. ajustada "
            f"{confluencia.get('pepita_smc_conf_ajustado')}% < "
            f"{CONFIANCA_MINIMA_SMC_PEPITA:.0f}%."
        )
        print("   Operação IGNORADA (hard block). Exit code = 2.")
        print("=" * 60)
        return 2

    if vies_final == "NEUTRO":
        print()
        print(f"⏸️  Sem operação. Motivo: {motivo_saida or 'não especificado'}. Exit code = 2.")
        print("=" * 60)
        return 2

    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())