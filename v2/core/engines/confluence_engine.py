from typing import Dict, Any, Optional
from ..contracts import MarketContext, PredictionContext, NewsContext, VisionContext

class ConfluenceEngine:
    def __init__(self, pesos: Optional[Dict[str, float]] = None):
        self.pesos = pesos or {
            "market_externo": 1.0,
            "adrs": 0.8,
            "tendencia": 2.0,
            "prediction": 2.5,
            "gap": 0.5,
            "news": 0.6,
            "vision": 1.8,
        }

    def _normalizar_direcao(self, direcao: str) -> int:
        return 1 if direcao.upper() == "COMPRA" else -1 if direcao.upper() == "VENDA" else 0

    def _peso_do_score(self, score: float) -> float:
        if score >= 80: return 2.0
        elif score >= 60: return 1.5
        elif score >= 40: return 1.0
        elif score >= 20: return 0.5
        return 0.0

    def processar(self, market: MarketContext, prediction: Optional[PredictionContext] = None,
                  news: Optional[NewsContext] = None, vision: Optional[VisionContext] = None) -> Dict[str, Any]:
        motivos, riscos, votos = [], [], {"COMPRA": 0.0, "VENDA": 0.0}
        confianca_total, peso_total = 0.0, 0.0

        # Market Externo
        if market.indicador_mercado_externo is not None:
            v = market.indicador_mercado_externo
            p = self.pesos["market_externo"]
            if v > 0.5:
                votos["COMPRA"] += 1.0 * p; motivos.append(f"Mercado Externo: {v:+.2f}% (COMPRA)")
            elif v < -0.5:
                votos["VENDA"] += 1.0 * p; motivos.append(f"Mercado Externo: {v:+.2f}% (VENDA)")
            else:
                motivos.append(f"Mercado Externo: {v:+.2f}% (NEUTRO)")
            confianca_total += 0.5 * p; peso_total += p

        # ADRs
        if market.indicador_adrs_brasileiras is not None:
            v = market.indicador_adrs_brasileiras
            p = self.pesos["adrs"]
            if v > 0.5:
                votos["COMPRA"] += 0.8 * p; motivos.append(f"ADRs: {v:+.2f}% (COMPRA)")
            elif v < -0.5:
                votos["VENDA"] += 0.8 * p; motivos.append(f"ADRs: {v:+.2f}% (VENDA)")
            else:
                motivos.append(f"ADRs: {v:+.2f}% (NEUTRO)")
            confianca_total += 0.4 * p; peso_total += p

        # Tendência
        if market.tendencia_win:
            p = self.pesos["tendencia"]
            if market.tendencia_win == "SUBIU":
                votos["COMPRA"] += 1.2 * p; motivos.append(f"Tendência: {market.tendencia_win_padrao} (COMPRA)")
            elif market.tendencia_win == "DESCEU":
                votos["VENDA"] += 1.2 * p; motivos.append(f"Tendência: {market.tendencia_win_padrao} (VENDA)")
            else:
                motivos.append(f"Tendência: {market.tendencia_win_padrao} (NEUTRO)")
            confianca_total += 0.6 * p; peso_total += p

        # VIX (risco)
        if market.vix and market.vix.variacao_pct and market.vix.variacao_pct > 3.0:
            riscos.append(f"VIX em alta: {market.vix.variacao_pct:+.2f}%")
            votos["COMPRA"] -= 0.3; votos["VENDA"] -= 0.3

        # Prediction
        if prediction:
            p = self.pesos["prediction"]
            direcao = self._normalizar_direcao(prediction.direcao_prevista)
            fator = self._peso_do_score(prediction.score)
            if direcao == 1 and fator > 0.5:
                votos["COMPRA"] += fator * p; motivos.append(f"Predição: COMPRA (score {prediction.score:.1f})")
            elif direcao == -1 and fator > 0.5:
                votos["VENDA"] += fator * p; motivos.append(f"Predição: VENDA (score {prediction.score:.1f})")
            else:
                motivos.append(f"Predição: NEUTRO/baixa confiança (score {prediction.score:.1f})")
            confianca_total += fator * p; peso_total += p
            if prediction.gap_intensidade in ("FORTE", "EXTREMO"):
                riscos.append(f"GAP {prediction.gap_intensidade} ({prediction.gap_pontos:+.0f} pts)")
                if prediction.gap_pontos > 0:
                    votos["COMPRA"] += 0.5 * self.pesos["gap"]
                elif prediction.gap_pontos < 0:
                    votos["VENDA"] += 0.5 * self.pesos["gap"]

        # News
        if news:
            if news.classificacao_risco in ("EXTREMO", "ALTO"):
                riscos.append(f"Risco de notícias: {news.classificacao_risco}")
                if news.tem_3_estrelas_brasil_0900:
                    riscos.append("Notícia 3★ Brasil 09:00")
                    confianca_total *= 0.7
            if news.tem_multiplas_2_estrelas_mesmo_horario:
                riscos.append("Múltiplas notícias ⭐⭐ no mesmo horário")

        # Vision
        if vision and vision.direcao_estrutura != "NEUTRO":
            p = self.pesos["vision"]
            if vision.direcao_estrutura == "COMPRA":
                votos["COMPRA"] += 1.0 * p; motivos.append(f"Visão SMC: Estrutura de COMPRA (conf. {vision.confianca_visual}%)")
            elif vision.direcao_estrutura == "VENDA":
                votos["VENDA"] += 1.0 * p; motivos.append(f"Visão SMC: Estrutura de VENDA (conf. {vision.confianca_visual}%)")
            confianca_total += 0.5 * p; peso_total += p

        # Decisão final
        total_c = votos["COMPRA"]; total_v = votos["VENDA"]
        vies = "COMPRA" if total_c > total_v + 0.5 else "VENDA" if total_v > total_c + 0.5 else "NEUTRO"
        confianca = 0 if peso_total == 0 else min(100, max(0, int((confianca_total / peso_total) * 100)))
        if riscos:
            confianca = max(0, confianca - len(riscos) * 5)

        return {"vies": vies, "confianca": confianca, "motivos": motivos, "riscos": riscos, "votos": votos}