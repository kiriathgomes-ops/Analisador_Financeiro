# test_phase1.py
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    import config
    print("✅ config.py carregado")

    required = [
        "COLETAS_DIR", "FILE_UNIFICADO", "FILE_ROM0",
        "JANELA_AJUSTE_INICIO", "JANELA_AJUSTE_FIM",
        "TICKERS_TRADINGVIEW", "ATIVOS_FINNHUB", "MAPEAMENTO_TICKERS",
        "PESOS_ESTIMATIVA_ABERTURA", "PESOS_NOVO_MOTOR",
        "MAX_TENTATIVAS_MT5", "TICK_STALE_SEG"
    ]
    for attr in required:
        if hasattr(config, attr):
            print(f"   ✅ {attr} presente")
        else:
            print(f"   ⚠️ {attr} não encontrado")

    from Coletor import executar_pipeline_coleta
    print("✅ Coletor importado")

    from Calculadora import calcular_metricas
    print("✅ Calculadora importada")

    from CalculadoraEstimativaAbertura import processar_calculos
    print("✅ CalculadoraEstimativaAbertura importada")

    from v2.core.services.win_session_builder import build_win_session
    print("✅ win_session_builder importado (V2)")

    print("\n🎉 FASE 1 - VALIDAÇÃO CONCLUÍDA SEM ERROS!")
    print("👉 Todos os módulos principais carregaram usando config.")

except Exception as e:
    print(f"❌ ERRO NA VALIDAÇÃO: {e}")