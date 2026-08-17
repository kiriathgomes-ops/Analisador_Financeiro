# ============================================================
# ARQUIVO: v2_gravar_sessao_win.py
# FASE 5/7 — Etapa do pipeline: grava WinSession + cenário
#
# Uso:
#   1. Rodar isolado:  python v2_gravar_sessao_win.py
#   2. No main_pipeline.py, incluir na lista de etapas, por exemplo:
#      ("10 - V2 SESSAO WINFUT", "v2_gravar_sessao_win.py"),
#
# Não altera a V1. Falhas aqui não devem derrubar o pipeline
# se você preferir: troque raise por log e return.
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
    print(" V2 — Gravação de sessão WINFUT")
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Montando WinSession...")

    try:
        from v2.core.services.win_session_builder import build_win_session
        from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura
        from v2.core.services.session_history import salvar_sessao_hoje
    except ImportError as e:
        print(f"❌ Import V2 falhou: {e}")
        print("   Verifique se a pasta v2/ está na raiz do projeto.")
        return 1

    try:
        session = build_win_session()
        cenario = gerar_cenario_abertura(session)
        session.cenario = cenario

        caminho = salvar_sessao_hoje(session, cenario, tag="pipeline")

        print(f"Contrato     : {session.metadata.contrato_principal}")
        print(f"Ajuste       : {session.precos.ajuste}")
        print(f"Last MT5     : {session.precos.last_mt5}")
        print(f"Distância    : {session.distancias.last_vs_ajuste_pts} pts")
        print(f"Posição      : {cenario.relacao_com_ajuste.posicao}")
        print(f"Direção      : {cenario.direcao_provavel}")
        print(f"Notícias     : {session.noticias.classificacao_risco} "
              f"(impacto={session.noticias.impacto_total})")
        print(f"✅ Histórico  : {caminho}")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"❌ Erro ao gravar sessão V2: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
