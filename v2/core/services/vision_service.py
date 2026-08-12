from pathlib import Path
from datetime import datetime
from typing import Optional

from ..contracts import VisionContext

class VisionService:
    def __init__(self, market_context=None):
        self.market = market_context

    def get_vision(self, ativo: str = "WIN") -> Optional[VisionContext]:
        if not self.market or not self.market.tendencia_win_padrao:
            return VisionContext(
                timestamp=datetime.now(),
                ativo=ativo,
                direcao_estrutura="NEUTRO",
                bos=False,
                choch=False,
                liquidity_zones=[],
                order_blocks=[],
                fair_value_gaps=[],
                suportes=[],
                resistencias=[],
                entrada_sugerida=None,
                stop_sugerido=None,
                alvos=[],
                confianca_visual=0,
                metadados={"fonte": "sem_dados"}
            )

        padrao = self.market.tendencia_win_padrao
        if padrao == "Alta_E_Alta":
            direcao, bos, choch, conf = "COMPRA", True, False, 80
        elif padrao == "Baixa_E_Baixa":
            direcao, bos, choch, conf = "VENDA", True, False, 80
        elif padrao in ["Alta_E_Estavel", "Estavel_E_Alta"]:
            direcao, bos, choch, conf = "COMPRA", False, False, 50
        elif padrao in ["Baixa_E_Estavel", "Estavel_E_Baixa"]:
            direcao, bos, choch, conf = "VENDA", False, False, 50
        elif "Alta_E_Baixa" in padrao or "Baixa_E_Alta" in padrao:
            direcao, bos, choch, conf = "NEUTRO", False, True, 30
        else:
            direcao, bos, choch, conf = "NEUTRO", False, False, 20

        ajuste = self.market.win_ajuste if ativo == "WIN" else self.market.wdo_ajuste
        suportes = [ajuste - 150, ajuste - 300] if ajuste else []
        resistencias = [ajuste + 150, ajuste + 300] if ajuste else []

        return VisionContext(
            timestamp=datetime.now(),
            ativo=ativo,
            direcao_estrutura=direcao,
            bos=bos,
            choch=choch,
            liquidity_zones=[],
            order_blocks=[],
            fair_value_gaps=[],
            suportes=suportes,
            resistencias=resistencias,
            entrada_sugerida=None,
            stop_sugerido=None,
            alvos=[],
            confianca_visual=conf,
            metadados={"fonte": "tendencia_15min", "padrao": padrao}
        )