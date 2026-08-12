from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class VisionContext:
    timestamp: datetime
    ativo: str
    direcao_estrutura: str
    bos: bool
    choch: bool
    liquidity_zones: List[float] = field(default_factory=list)
    order_blocks: List[Dict[str, float]] = field(default_factory=list)
    fair_value_gaps: List[Dict[str, float]] = field(default_factory=list)
    suportes: List[float] = field(default_factory=list)
    resistencias: List[float] = field(default_factory=list)
    entrada_sugerida: Optional[float] = None
    stop_sugerido: Optional[float] = None
    alvos: List[float] = field(default_factory=list)
    confianca_visual: int = 0
    metadados: Dict = field(default_factory=dict)