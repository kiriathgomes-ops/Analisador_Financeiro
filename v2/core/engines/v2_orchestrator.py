# ============================================================
# v2/core/engines/v2_orchestrator.py
# Orquestrador V2 — alinhado às assinaturas reais do projeto
#
# MarketService(coletas_dir=None)  → build()
# PredictionService()              → get_prediction()   # SEM argumentos
# NewsService(coletas_dir=None)    → get_news()
# VisionService(market_context=)   → get_vision()
# ConfluenceEngine()               → processar(market, prediction, news, vision)
# DecisionEngine(ativo="WIN")      → gerar_decisao(confluence, market, session=, prediction=, vision=)
# build_win_session(coletas_dir) / gerar_cenario_abertura(session)
# ============================================================

from __future__ import annotations

import json
import traceback
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _raiz() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _coletas() -> Path:
    return _raiz() / "Coletas"


def _to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


class V2Orchestrator:
    def __init__(self, coletas_dir: Optional[Path] = None):
        self.coletas_dir = Path(coletas_dir) if coletas_dir else _coletas()
        self.coletas_dir.mkdir(parents=True, exist_ok=True)

        from v2.core.services.market_service import MarketService
        from v2.core.services.prediction_service import PredictionService
        from v2.core.services.news_service import NewsService
        from v2.core.services.vision_service import VisionService
        from v2.core.engines.confluence_engine import ConfluenceEngine
        from v2.core.engines.decision_engine import DecisionEngine

        self.market_service = MarketService(self.coletas_dir)
        # IMPORTANT: PredictionService NÃO aceita argumentos
        self.prediction_service = PredictionService()
        self.news_service = NewsService(self.coletas_dir)
        self.vision_service = VisionService()  # market_context setado depois
        self.confluence = ConfluenceEngine()
        self.decision = DecisionEngine(ativo="WIN")

    def executar(self, salvar_historico: bool = True) -> Dict[str, Any]:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] V2 Orchestrator — iniciando...")
        erros = []

        # 1) Market
        market = self.market_service.build()
        if market is None:
            raise RuntimeError(
                "MarketContext indisponível. Rode o pipeline "
                "(DadosAtivosUnificados.json / Metricas_Calculadas.json)."
            )

        # 2) Prediction (sem args no construtor)
        prediction = None
        try:
            prediction = self.prediction_service.get_prediction()
        except Exception as e:
            erros.append(f"PredictionService: {e}")
            print(f"⚠️ PredictionService: {e}")

        # 3) News
        news = None
        try:
            news = self.news_service.get_news()
        except Exception as e:
            erros.append(f"NewsService: {e}")
            print(f"⚠️ NewsService: {e}")

        # 4) Vision — recebe market_context, NÃO coletas_dir
        vision = None
        try:
            self.vision_service.market = market
            vision = self.vision_service.get_vision(ativo="WIN")
        except Exception as e:
            erros.append(f"VisionService: {e}")
            print(f"⚠️ VisionService: {e}")

        # 5) WinSession + OpeningScenario
        session = None
        cenario = None
        try:
            from v2.core.services.win_session_builder import build_win_session
            from v2.core.engines.opening_scenario_engine import gerar_cenario_abertura

            session = build_win_session(self.coletas_dir)
            cenario = gerar_cenario_abertura(session)
            try:
                session.cenario = cenario
            except Exception:
                pass
        except Exception as e:
            erros.append(f"WinSession/OpeningScenario: {e}")
            print(f"⚠️ WinSession/OpeningScenario: {e}")

        # 6) Confluence
        try:
            confluence_result = self.confluence.processar(
                market=market,
                prediction=prediction,
                news=news,
                vision=vision,
            )
        except Exception as e:
            erros.append(f"ConfluenceEngine: {e}")
            print(f"⚠️ ConfluenceEngine: {e}")
            confluence_result = {
                "vies": "NEUTRO",
                "confianca": 0,
                "motivos": [],
                "riscos": [str(e)],
            }

        # 7) Decision (assinatura atual aceita session/prediction/vision)
        try:
            decisao = self.decision.gerar_decisao(
                confluence_result=confluence_result,
                market=market,
                session=session,
                prediction=prediction,
                vision=vision,
            )
        except TypeError:
            # fallback se versão antiga só aceitar (confluence, market)
            decisao = self.decision.gerar_decisao(confluence_result, market)
        except Exception as e:
            erros.append(f"DecisionEngine: {e}")
            raise

        # 8) Resultado unificado
        resultado = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "versao": "V2.2",
                "fonte": "v2_orchestrator",
            },
            "win_session": _to_dict(session),
            "opening_scenario": _to_dict(cenario),
            "confluence": _to_dict(confluence_result),
            "decisao": _to_dict(decisao),
            "contextos": {
                "market_ok": market is not None,
                "prediction_ok": prediction is not None,
                "news_ok": news is not None,
                "vision_ok": vision is not None,
                "session_ok": session is not None,
            },
            "erros": erros,
        }

        # 9) Persistência — Decisao_V2.json (página 1 lê este arquivo)
        caminho = self.coletas_dir / "Decisao_V2.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ Decisão V2 salva em: {caminho}")

        vies = getattr(decisao, "vies_final", None) or (resultado.get("decisao") or {}).get("vies_final")
        conf = getattr(decisao, "confianca", None) or (resultado.get("decisao") or {}).get("confianca")
        print(f"   Viés: {vies} | Confiança: {conf}%")
        entrada = getattr(decisao, "entrada", None)
        if entrada:
            print(
                f"   Entrada: {entrada:.0f} | Stop: {getattr(decisao, 'stop_loss', None)} "
                f"| Alvo1: {getattr(decisao, 'alvo_1', None)} | Alvo2: {getattr(decisao, 'alvo_2', None)}"
            )

        # 10) Histórico de sessão
        if salvar_historico and session is not None:
            try:
                from v2.core.services.session_history import salvar_sessao_hoje
                caminho_hist = salvar_sessao_hoje(session, cenario, tag="v2_orquestrador")
                print(f"✅ Histórico de sessão: {caminho_hist}")
            except Exception as e:
                print(f"⚠️ Falha ao gravar histórico de sessão: {e}")
                erros.append(f"Historico: {e}")

        # 11) Histórico de decisões V2
        if salvar_historico:
            try:
                hist = self.coletas_dir / "Historico_Decisoes_V2"
                hist.mkdir(parents=True, exist_ok=True)
                nome = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
                with open(hist / nome, "w", encoding="utf-8") as f:
                    json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)
            except Exception as e:
                print(f"⚠️ Histórico decisões: {e}")

        return resultado


def executar_v2(salvar_historico: bool = True) -> Dict[str, Any]:
    return V2Orchestrator().executar(salvar_historico=salvar_historico)


if __name__ == "__main__":
    executar_v2()
