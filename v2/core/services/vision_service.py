# ============================================================
# ARQUIVO: v2/core/services/vision_service.py
# VERSÃO: 2.0 — Lê o SMC Real do JSON em vez de adivinhar
# ============================================================

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from ..contracts import VisionContext


class VisionService:
    def __init__(self, market_context=None, coletas_dir: Optional[Path] = None):
        self.market = market_context
        if coletas_dir is None:
            self.coletas_dir = Path(__file__).resolve().parent.parent.parent.parent / "Coletas"
        else:
            self.coletas_dir = Path(coletas_dir)

    def _carregar_json(self, nome: str) -> dict:
        caminho = self.coletas_dir / nome
        if not caminho.exists():
            return {}
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_vision(self, ativo: str = "WIN") -> Optional[VisionContext]:
        # ✅ Lê o resultado do Motor_SMC_Regras em vez de adivinhar pela tendência
        smc = self._carregar_json("AnaliseGraficaSMC_Regras.json")
        
        if not smc:
            return VisionContext(
                timestamp=datetime.now(), ativo=ativo, direcao_estrutura="NEUTRO",
                bos=False, choch=False,
                metadados={"fonte": "smc_ausente"}
            )

        bias = smc.get("bias_direcional", "LATERAL")
        direcao = "COMPRA" if bias == "ALTA" else "VENDA" if bias == "BAIXA" else "NEUTRO"
        
        # Extrai liquidez do JSON
        liq = smc.get("liquidez", {}) or {}
        bsl = liq.get("bsl", [])
        ssl = liq.get("ssl", [])

        return VisionContext(
            timestamp=datetime.now(),
            ativo=ativo,
            direcao_estrutura=direcao,
            bos=smc.get("bos", False),
            choch=smc.get("choch", False),
            liquidity_zones=bsl + ssl,
            order_blocks=smc.get("order_blocks", []),
            fair_value_gaps=smc.get("fair_value_gaps", []),
            entrada_sugerida=smc.get("entrada_sugerida"),
            stop_sugerido=smc.get("stop_sugerido"),
            alvos=smc.get("alvos", []),
            confianca_visual=smc.get("confianca_visual", 0),
            metadados={"fonte": "AnaliseGraficaSMC_Regras.json", "bias_original": bias}
        )