# ============================================================
# ARQUIVO: v2/core/engines/decision_engine.py
# VERSÃO: 2.1 — Entrada/Stop/Alvo reais usando ajuste + pivôs + gap + SMC
# ============================================================

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from v2.core.contracts.market_context import MarketContext
from v2.core.contracts.decision_context import DecisionContext
# Se DecisionContext estiver em contracts/__init__ ou decision_context.py, ajuste o import


class DecisionEngine:
    def __init__(self, ativo: str = "WIN"):
        self.ativo = ativo

    def _obter_pivots(self, market: MarketContext) -> Dict[str, float]:
        pivots = (market.metadados or {}).get("pivots") or {}
        if pivots and any(v is not None for v in pivots.values()):
            return {k: float(v) for k, v in pivots.items() if v is not None}

        preco = market.win_fut.preco if self.ativo == "WIN" else market.wdo_fut.preco
        ajuste = market.win_ajuste if self.ativo == "WIN" else market.wdo_ajuste
        base = ajuste or preco or 0.0
        return {
            "r2": base + 300,
            "r1": base + 150,
            "pp": base,
            "s1": base - 150,
            "s2": base - 300,
        }

    def _niveis_smc(self, vision) -> Dict[str, Any]:
        """Extrai níveis do VisionContext / Motor SMC Regras se existirem."""
        if vision is None:
            return {}
        return {
            "order_blocks": getattr(vision, "order_blocks", []) or [],
            "fvgs": getattr(vision, "fair_value_gaps", []) or [],
            "suportes": getattr(vision, "suportes", []) or [],
            "resistencias": getattr(vision, "resistencias", []) or [],
            "entrada_sugerida": getattr(vision, "entrada_sugerida", None),
            "stop_sugerido": getattr(vision, "stop_sugerido", None),
            "alvos": getattr(vision, "alvos", []) or [],
        }

    def gerar_decisao(
        self,
        confluence_result: Dict[str, Any],
        market: MarketContext,
        session=None,
        prediction=None,
        vision=None,
    ) -> DecisionContext:

        vies = confluence_result.get("vies", "NEUTRO")
        confianca = int(confluence_result.get("confianca", 0))
        motivos = list(confluence_result.get("motivos", []))
        riscos = list(confluence_result.get("riscos", []))

        pivots = self._obter_pivots(market)
        smc = self._niveis_smc(vision)

        # Referências de preço
        ajuste = market.win_ajuste if self.ativo == "WIN" else market.wdo_ajuste
        last = market.win_fut.preco if self.ativo == "WIN" else market.wdo_fut.preco
        if session and getattr(session, "precos", None):
            if session.precos.last_mt5:
                last = session.precos.last_mt5
            if session.precos.ajuste:
                ajuste = session.precos.ajuste

        gap_pts = None
        if prediction and getattr(prediction, "gap_pontos", None) is not None:
            gap_pts = prediction.gap_pontos
        elif session and getattr(session, "gap", None):
            gap_pts = session.gap.gap_projetado_pts

        # Confiança baixa → sem ordem
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
                metadados={"pivots": pivots, "smc": smc, "gap_pts": gap_pts},
            )

        entrada = stop = alvo1 = alvo2 = None
        invalidacao = "Aguardar definição ou confiança moderada"

        # Preferência: níveis sugeridos pelo SMC/Vision
        if confianca >= 55 and smc.get("entrada_sugerida") and smc.get("stop_sugerido"):
            entrada = float(smc["entrada_sugerida"])
            stop = float(smc["stop_sugerido"])
            alvos = smc.get("alvos") or []
            alvo1 = float(alvos[0]) if len(alvos) > 0 else (entrada + 250 if vies == "COMPRA" else entrada - 250)
            alvo2 = float(alvos[1]) if len(alvos) > 1 else (alvo1 + 250 if vies == "COMPRA" else alvo1 - 250)
            invalidacao = f"Fechamento além do stop {stop:.0f}"
            motivos.append("Níveis SMC/Vision utilizados")

        # Fallback: lógica clássica com pivôs + ajuste
        elif vies == "COMPRA" and confianca >= 55:
            # Entrada preferencialmente no reteste do PP ou R1 próximo
            base = pivots.get("pp") or ajuste or last
            r1 = pivots.get("r1")
            s1 = pivots.get("s1")

            if r1 and last and last > base:
                entrada = round(max(base, r1 * 0.998))
            else:
                entrada = round((base or last) + 30)

            stop = round(s1) if s1 else round(entrada - 180)
            alvo1 = round(pivots.get("r2") or entrada + 250)
            alvo2 = round(alvo1 + 200)
            invalidacao = f"Fechamento abaixo de {stop:.0f}"

            if gap_pts and gap_pts > 150:
                riscos.append(f"Gap projetado alto (+{gap_pts:.0f} pts) — cuidado com preenchimento")

        elif vies == "VENDA" and confianca >= 55:
            base = pivots.get("pp") or ajuste or last
            s1 = pivots.get("s1")
            r1 = pivots.get("r1")

            if s1 and last and last < base:
                entrada = round(min(base, s1 * 1.002))
            else:
                entrada = round((base or last) - 30)

            stop = round(r1) if r1 else round(entrada + 180)
            alvo1 = round(pivots.get("s2") or entrada - 250)
            alvo2 = round(alvo1 - 200)
            invalidacao = f"Fechamento acima de {stop:.0f}"

            if gap_pts and gap_pts < -150:
                riscos.append(f"Gap projetado alto ({gap_pts:.0f} pts) — cuidado com preenchimento")

        return DecisionContext(
            timestamp=datetime.now(),
            ativo=self.ativo,
            vies_final=vies,
            confianca=confianca,
            entrada=round(entrada) if entrada is not None else None,
            stop_loss=round(stop) if stop is not None else None,
            alvo_1=round(alvo1) if alvo1 is not None else None,
            alvo_2=round(alvo2) if alvo2 is not None else None,
            invalidacao=invalidacao,
            motivos=motivos,
            riscos=riscos,
            metadados={
                "pivots": pivots,
                "smc": smc,
                "gap_pts": gap_pts,
                "ajuste": ajuste,
                "last": last,
            },
        )