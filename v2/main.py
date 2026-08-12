# v2/main.py
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.services.vision_service import VisionService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine

def main():
    print("=" * 60)
    print("🚀 ANALISADOR FINANCEIRO V2 - TESTE")
    print("=" * 60)

    # 1. MarketContext
    print("\n📊 Carregando MarketContext...")
    market_service = MarketService()
    market = market_service.build()
    if not market:
        print("❌ Falha ao carregar MarketContext")
        return
    print(f"✅ WIN: {market.win_fut.preco:.0f} ({market.win_fut.variacao_pct:+.2f}%)")
    print(f"✅ VIX: {market.vix.preco:.2f} ({market.vix.variacao_pct:+.2f}%)")

    # 2. PredictionContext
    print("\n🔮 Carregando PredictionContext...")
    pred_service = PredictionService()
    prediction = pred_service.get_prediction()
    if prediction:
        print(f"✅ Direção: {prediction.direcao_prevista} (score: {prediction.score:.1f})")
    else:
        print("⚠️ Prediction não disponível")

    # 3. NewsContext
    print("\n📰 Carregando NewsContext...")
    news_service = NewsService()
    news = news_service.get_news()
    if news:
        print(f"✅ Risco: {news.classificacao_risco} (impacto: {news.impacto_total})")
    else:
        print("⚠️ News não disponível")

    # 4. VisionContext
    print("\n📈 Carregando VisionContext...")
    vision_service = VisionService(market_context=market)
    vision = vision_service.get_vision()
    if vision:
        print(f"✅ Estrutura: {vision.direcao_estrutura} (conf. {vision.confianca_visual}%)")
    else:
        print("⚠️ Vision não disponível")

    # 5. Confluência
    print("\n⚖️ Executando ConfluenceEngine...")
    engine = ConfluenceEngine()
    resultado = engine.processar(market, prediction, news, vision)
    print(f"✅ Viés: {resultado['vies']} | Confiança: {resultado['confianca']}%")

    # 6. Decisão
    print("\n🎯 Gerando Decisão...")
    dec_engine = DecisionEngine(ativo="WIN")
    decisao = dec_engine.gerar_decisao(resultado, market)
    print(f"✅ Decisão: {decisao.vies_final} (confiança: {decisao.confianca}%)")
    if decisao.entrada:
        print(f"   Entrada: {decisao.entrada:.0f} | Stop: {decisao.stop_loss:.0f} | Alvo1: {decisao.alvo_1:.0f} | Alvo2: {decisao.alvo_2:.0f}")
    else:
        print("   ⏳ Aguardando confirmação")

    print("\n" + "=" * 60)
    print("✅ Teste concluído!")

if __name__ == "__main__":
    main()