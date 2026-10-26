# ============================================================
# ARQUIVO: v2/config.py
# Centraliza pesos, limiares e configurações dos motores V2.
# ============================================================

# Pesos usados pelo ConfluenceEngine para calcular o voto de cada contexto
PESOS_CONFLUENCE = {
    "market_externo": 1.0,
    "adrs": 0.8,
    "tendencia": 2.0,
    "prediction": 2.5,
    "gap": 0.5,
    "news": 0.6,
    "vision": 1.8,
}

# Limiares em pontos (WIN) para o OpeningScenarioEngine
SCENARIO_LIMIAR_PROXIMO = 50
SCENARIO_LIMIAR_MODERADO = 150
SCENARIO_LIMIAR_DISTANTE = 300