# ============================================================
# v2_rodar_decisao_completa.py  (raiz do projeto)
# ============================================================

from __future__ import annotations

import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


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

    print()
    print(f"Viés final     : {decisao.get('vies_final')}")
    print(f"Confiança      : {decisao.get('confianca')}%")
    print(f"Entrada        : {decisao.get('entrada')}")
    print(f"Stop           : {decisao.get('stop_loss')}")
    print(f"Alvo 1 / Alvo 2: {decisao.get('alvo_1')} / {decisao.get('alvo_2')}")
    print(f"Invalidação    : {decisao.get('invalidacao')}")

    ctx = resultado.get("contextos") or {}
    print(
        "Contextos      : "
        f"market={ctx.get('market_ok')} pred={ctx.get('prediction_ok')} "
        f"news={ctx.get('news_ok')} vision={ctx.get('vision_ok')} "
        f"session={ctx.get('session_ok')}"
    )
    erros = resultado.get("erros") or []
    if erros:
        print("Avisos:")
        for e in erros:
            print(f"   - {e}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
