from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime

@dataclass
class AtivoSnapshot:
    preco: float
    variacao_pct: float
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None

    def __post_init__(self):
        self.variacao_pct = float(self.variacao_pct)

@dataclass
class MarketContext:
    timestamp: datetime
    win_fut: AtivoSnapshot
    wdo_fut: AtivoSnapshot
    win_ajuste: float
    wdo_ajuste: float
    ptax: float
    sp500: AtivoSnapshot
    nasdaq: AtivoSnapshot
    vix: AtivoSnapshot
    dxy: AtivoSnapshot
    ewz: AtivoSnapshot
    iron_ore: AtivoSnapshot
    crude_oil: AtivoSnapshot
    gold: AtivoSnapshot
    adrs: Dict[str, AtivoSnapshot] = field(default_factory=dict)
    indicador_mercado_externo: Optional[float] = None
    indicador_adrs_brasileiras: Optional[float] = None
    spread_wdo_ptax_pontos: Optional[float] = None
    inclinacao_di_bps: Optional[float] = None
    tendencia_win: Optional[str] = None
    tendencia_win_padrao: Optional[str] = None
    metadados: Dict = field(default_factory=dict)