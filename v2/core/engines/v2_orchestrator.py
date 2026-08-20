# ============================================================
# ARQUIVO: v2/core/engines/v2_orchestrator.py
# OBJETIVO: Orquestrador completo da arquitetura V2
#           Gera WinSession + OpeningScenario + DecisionContext
# ============================================================

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from v2.core.services.market_service import MarketService
from v2.core.services.prediction_service import PredictionService
from v2.core.services.news_service import NewsService
from v2.core.services.vision_service import VisionService
from v2.core.engines.confluence_engine import ConfluenceEngine
from v2.core.engines.decision_engine import DecisionEngine
from v2.core.services.win_session_builder import build_win_session
from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura
from v2.core.services.session_history import salvar_sessao_hoje


def _to_dict(obj: Any) -> Any:
    """Serializa dataclass / objetos simples para JSON."""
    if obj is None:
        return None
    if is_dataclass(obj):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):  # date
        return obj.isoformat()
    return obj


class V2Orchestrator:
    """
    Ponto único de execução da V2.
    Não altera a V1. Gera Decisao_V2.json + histórico de sessão.
    """

    def __init__(self, coletas_dir: Optional[Path] = None):
        if coletas_dir is None:
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = Path(coletas_dir)

        self.market_service = MarketService(self.coletas_dir)
        self.prediction_service = PredictionService()
        self.news_service = NewsService(self.coletas_dir)
        self.vision_service = VisionService(self.coletas_dir)
        self.confluence = ConfluenceEngine()
        self.decision = DecisionEngine(ativo="WIN")

    def executar(self, salvar_historico: bool = True) -> Dict[str, Any]:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] V2 Orchestrator — iniciando...")

        # 1. Contextos
        market = self.market_service.build()
        prediction = self.prediction_service.get_prediction()
        news = self.news_service.get_news()
        
        # Define o contexto de mercado no VisionService
        self.vision_service.market = market
        vision = self.vision_service.get_vision()
        

        # 2. WinSession + Cenário de Abertura
        session = build_win_session(self.coletas_dir)
        cenario = gerar_cenario_abertura(session)
        session.cenario = cenario

        # 3. Confluência
        confluence_result = self.confluence.processar(
            market=market,
            prediction=prediction,
            news=news,
            vision=vision,
        )

        # 4. Decisão operacional (entrada / stop / alvos)
        decisao = self.decision.gerar_decisao(
            confluence_result=confluence_result,
            market=market,
            session=session,          # novo parâmetro (ver DecisionEngine abaixo)
            prediction=prediction,
            vision=vision,
        )

        # 5. Montagem do resultado unificado
        resultado = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "versao": "V2.1",
                "fonte": "v2_orchestrator",
            },
            "win_session": _to_dict(session),
            "opening_scenario": _to_dict(cenario),
            "confluence": confluence_result,
            "decisao": _to_dict(decisao),
            "contextos": {
                "market_ok": market is not None,
                "prediction_ok": prediction is not None,
                "news_ok": news is not None,
                "vision_ok": vision is not None,
            },
        }

        # 6. Persistência
        caminho_decisao = self.coletas_dir / "Decisao_V2.json"
        with open(caminho_decisao, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)

        print(f"✅ Decisão V2 salva em: {caminho_decisao}")
        print(f"   Viés: {decisao.vies_final} | Confiança: {decisao.confianca}%")
        if decisao.entrada:
            print(f"   Entrada: {decisao.entrada:.0f} | Stop: {decisao.stop_loss:.0f} "
                  f"| Alvo1: {decisao.alvo_1:.0f} | Alvo2: {decisao.alvo_2:.0f}")

        if salvar_historico:
            try:
                caminho_hist = salvar_sessao_hoje(session, cenario, tag="v2_orquestrador")
                print(f"✅ Histórico de sessão: {caminho_hist}")
            except Exception as e:
                print(f"⚠️ Falha ao gravar histórico de sessão: {e}")

        return resultado


def executar_v2(salvar_historico: bool = True) -> Dict[str, Any]:
    """Função de conveniência para o pipeline."""
    return V2Orchestrator().executar(salvar_historico=salvar_historico)


if __name__ == "__main__":
    executar_v2()