from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class DecisionContext:
    timestamp: datetime
    ativo: str
    vies_final: str
    confianca: int
    entrada: Optional[float] = None
    stop_loss: Optional[float] = None
    alvo_1: Optional[float] = None
    alvo_2: Optional[float] = None
    invalidacao: Optional[str] = None
    motivos: List[str] = field(default_factory=list)
    riscos: List[str] = field(default_factory=list)
    market_referencia: Optional[Dict] = None
    prediction_referencia: Optional[Dict] = None
    vision_referencia: Optional[Dict] = None
    news_referencia: Optional[Dict] = None
    metadados: Dict = field(default_factory=dict)