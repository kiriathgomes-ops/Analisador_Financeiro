from typing import Dict, Any
from datetime import datetime
from ..contracts import MarketContext, DecisionContext

class DecisionEngine:
    def __init__(self, ativo: str = "WIN"):
        self.ativo = ativo

    def _obter_pivots(self, market: MarketContext) -> Dict[str, float]:
        pivots = market.metadados.get("pivots", {})
        if pivots and any(pivots.values()):
            return pivots
        preco = market.win_fut.preco if self.ativo == "WIN" else market.wdo_fut.preco
        ajuste = market.win_ajuste if self.ativo == "WIN" else market.wdo_ajuste
        return {"r2": preco + 300, "r1": preco + 150, "pp": ajuste, "s1": preco - 150, "s2": preco - 300}

    def gerar_decisao(self, confluence_result: Dict[str, Any], market: MarketContext) -> DecisionContext:
        vies = confluence_result["vies"]
        confianca = confluence_result["confianca"]
        motivos = confluence_result["motivos"]
        riscos = confluence_result["riscos"]
        pivots = self._obter_pivots(market)

        if confianca < 40:
            return DecisionContext(
                timestamp=datetime.now(),
                ativo=self.ativo,
                vies_final=vies,
                confianca=confianca,
                entrada=None,
                stop_loss=None,
                alvo_1=None,
                alvo_2=None,
                invalidacao="Confiança insuficiente (< 40%)",
                motivos=motivos,
                riscos=riscos,
                metadados={"pivots": pivots}
            )

        entrada, stop, alvo1, alvo2, invalidacao = None, None, None, None, None
        if vies == "COMPRA" and confianca >= 60:
            entrada = max(pivots["pp"], pivots["r1"] * 0.99) if pivots["r1"] else pivots["pp"] + 50
            stop = pivots["s1"] or entrada - 150
            alvo1 = pivots["r2"] or entrada + 250
            alvo2 = alvo1 + 250
            invalidacao = f"Fechamento abaixo de {pivots['s1']:.0f}" if pivots["s1"] else "Fechamento abaixo do PP"
        elif vies == "VENDA" and confianca >= 60:
            entrada = min(pivots["pp"], pivots["s1"] * 1.01) if pivots["s1"] else pivots["pp"] - 50
            stop = pivots["r1"] or entrada + 150
            alvo1 = pivots["s2"] or entrada - 250
            alvo2 = alvo1 - 250
            invalidacao = f"Fechamento acima de {pivots['r1']:.0f}" if pivots["r1"] else "Fechamento acima do PP"
        else:
            invalidacao = "Aguardar definição ou confiança baixa"

        return DecisionContext(
            timestamp=datetime.now(),
            ativo=self.ativo,
            vies_final=vies,
            confianca=confianca,
            entrada=round(entrada) if entrada else None,
            stop_loss=round(stop) if stop else None,
            alvo_1=round(alvo1) if alvo1 else None,
            alvo_2=round(alvo2) if alvo2 else None,
            invalidacao=invalidacao,
            motivos=motivos,
            riscos=riscos,
            metadados={"pivots": pivots}
        )