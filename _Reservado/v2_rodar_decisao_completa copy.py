# ============================================================
# ARQUIVO: v2_rodar_decisao_completa.py
# Etapa de pipeline — executa o orquestrador V2 completo
# ============================================================

from __future__ import annotations

import sys
from datetime import datetime
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
        return 1

    try:
        resultado = executar_v2(salvar_historico=True)
        decisao = resultado.get("decisao", {})
        print()
        print(f"Viés final     : {decisao.get('vies_final')}")
        print(f"Confiança      : {decisao.get('confianca')}%")
        print(f"Entrada        : {decisao.get('entrada')}")
        print(f"Stop           : {decisao.get('stop_loss')}")
        print(f"Alvo 1 / Alvo 2: {decisao.get('alvo_1')} / {decisao.get('alvo_2')}")
        print(f"Invalidação    : {decisao.get('invalidacao')}")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"❌ Erro na execução V2: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())