from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

@dataclass
class NewsContext:
    timestamp: datetime
    impacto_total: int
    classificacao_risco: str
    tem_3_estrelas_brasil_0900: bool
    tem_3_estrelas_outros_horarios: bool
    tem_multiplas_2_estrelas_mesmo_horario: bool
    risco_abertura_win: bool
    eventos_3_estrelas: List[Dict] = field(default_factory=list)
    horarios_multiplas_2_estrelas: List[Dict] = field(default_factory=list)
    metadados: Dict = field(default_factory=dict)